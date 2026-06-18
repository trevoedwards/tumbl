"""Flask application for viewing Tumblr backup archives."""

from __future__ import annotations
import logging
import os
import random
import threading
from calendar import month_name
from dataclasses import dataclass
from pathlib import Path
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename
from app.date_archive import (
    archive_heading,
    build_archive_index,
    sorted_months,
    sorted_years,
)
from app.index_progress import (
    mark_complete,
    mark_error,
    progress_callback,
    reset,
    snapshot,
)
from app.open_graph import preview_description, preview_image_url
from app.parser import PostMeta, get_or_build_index
from app.post_filters import VALID_POST_TYPES, apply_filters
from app.security import (
    PUBLIC_INDEX_ERROR,
    apply_security_headers,
    clamp_query,
    is_path_under,
    is_safe_http_url,
    is_valid_post_id,
    is_valid_tag,
    resolve_allowed_file,
)
from app.tag_index import build_tag_counts
from app.timestamp_parse import month_label

POSTS_PER_PAGE = 20
GITHUB_REPO_URL = "https://github.com/trevoedwards/tumbl"
logger = logging.getLogger(__name__)
_index_lock = threading.Lock()
_posts_index: list[PostMeta] | None = None
_index_error: str | None = None


@dataclass
class FeedContext:

    posts: list[PostMeta]
    page: int
    total_pages: int
    total_posts: int
    active_tag: str | None = None
    active_type: str | None = None
    search_query: str | None = None
    archive_year: int | None = None
    archive_month: int | None = None
    feed_title: str | None = None


def _load_dotenv() -> None:

    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def warm_index(archive_path: Path, cache_path: Path) -> None:
    """Build or load the post index. Safe to call from a background thread."""
    global _posts_index, _index_error
    try:
        if not archive_path.is_dir():
            raise FileNotFoundError(f"Archive directory not found: {archive_path}")
        reset()
        logger.info("Loading archive from %s", archive_path)
        posts = get_or_build_index(
            archive_path,
            cache_root=cache_path,
            on_progress=progress_callback(),
        )
        with _index_lock:
            _posts_index = posts
        mark_complete()
        logger.info("Archive ready with %s posts", len(posts))
    except Exception as exc:  # noqa: BLE001 - surface startup errors in UI
        logger.exception("Failed to build archive index")
        with _index_lock:
            _index_error = str(exc)
        mark_error()


def start_index_warmup(archive_path: Path, cache_path: Path) -> None:
    """Start index loading in a background thread so HTTP can respond immediately."""
    thread = threading.Thread(
        target=warm_index,
        args=(archive_path, cache_path),
        name="index-warmup",
        daemon=True,
    )
    thread.start()


def create_app() -> Flask:

    _load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = Flask(__name__)
    app_root = Path(__file__).resolve().parent.parent
    archive_path = Path(os.environ.get("ARCHIVE_PATH", ".tumblrbackup")).resolve()
    default_cache = Path(__file__).resolve().parent.parent / ".cache"
    cache_path = Path(os.environ.get("CACHE_DIR", str(default_cache))).resolve()
    blog_title = os.environ.get("BLOG_TITLE", "MyBlog")
    background_image_env = os.environ.get("BACKGROUND_IMAGE", "").strip()
    background_image_path: Path | None = None
    background_image_url = ""
    if background_image_env.startswith(("http://", "https://")):
        if is_safe_http_url(background_image_env):
            background_image_url = background_image_env
        else:
            logger.warning(
                "Ignoring invalid BACKGROUND_IMAGE URL: %s", background_image_env
            )
    elif background_image_env:
        background_image_path = resolve_allowed_file(
            background_image_env,
            [archive_path, app_root],
        )
    app.config["ARCHIVE_PATH"] = archive_path
    app.config["CACHE_DIR"] = cache_path
    app.config["BLOG_TITLE"] = blog_title
    app.config["POSTS_PER_PAGE"] = POSTS_PER_PAGE
    app.config["BACKGROUND_IMAGE_PATH"] = background_image_path
    app.config["BACKGROUND_IMAGE_URL"] = background_image_url

    @app.after_request
    def _add_security_headers(response):
        return apply_security_headers(response)

    @app.context_processor
    def inject_globals() -> dict:
        default_bg = background_image_url
        if background_image_path and not default_bg:
            default_bg = url_for("background_image")
        active_type = None
        if request.endpoint == "type_feed":
            active_type = (
                request.view_args.get("post_type") if request.view_args else None
            )
        return {
            "blog_title": blog_title,
            "default_background_image": default_bg,
            "github_repo_url": GITHUB_REPO_URL,
            "post_types": ["audio", "photo", "text", "video"],
            "nav_active_type": active_type,
        }

    def _get_index() -> list[PostMeta]:
        if _index_error:
            abort(500, description=PUBLIC_INDEX_ERROR)
        if _posts_index is None:
            abort(503, description="Archive index is still loading. Please refresh.")
        return _posts_index

    def _paginate(posts: list[PostMeta], page: int) -> tuple[list[PostMeta], int, int]:
        per_page = POSTS_PER_PAGE
        total = len(posts)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = start + per_page
        return posts[start:end], page, total_pages

    def _loading_or_ready():
        if _index_error:
            abort(500, description=PUBLIC_INDEX_ERROR)
        if _posts_index is None:
            return render_template("loading.html")
        return None

    def _render_post_cards(posts: list[PostMeta]) -> str:
        return "".join(render_template("post_card.html", post=post) for post in posts)

    def _build_feed_context(
        posts: list[PostMeta],
        page: int,
        *,
        active_tag: str | None = None,
        active_type: str | None = None,
        search_query: str | None = None,
        archive_year: int | None = None,
        archive_month: int | None = None,
        feed_title: str | None = None,
    ) -> FeedContext:
        page_posts, page, total_pages = _paginate(posts, page)
        return FeedContext(
            posts=page_posts,
            page=page,
            total_pages=total_pages,
            total_posts=len(posts),
            active_tag=active_tag,
            active_type=active_type,
            search_query=search_query,
            archive_year=archive_year,
            archive_month=archive_month,
            feed_title=feed_title,
        )

    def _render_feed(ctx: FeedContext) -> str:
        return render_template(
            "feed.html",
            posts=ctx.posts,
            page=ctx.page,
            total_pages=ctx.total_pages,
            total_posts=ctx.total_posts,
            active_tag=ctx.active_tag,
            active_type=ctx.active_type,
            search_query=ctx.search_query,
            archive_year=ctx.archive_year,
            archive_month=ctx.archive_month,
            feed_title=ctx.feed_title,
        )

    def _filtered_posts(
        *,
        tag: str | None = None,
        post_type: str | None = None,
        search: str | None = None,
        year: int | None = None,
        month: int | None = None,
    ) -> list[PostMeta]:
        return apply_filters(
            _get_index(),
            tag=tag,
            post_type=post_type,
            search=search,
            year=year,
            month=month,
        )

    @app.route("/")
    def feed() -> str:
        loading = _loading_or_ready()
        if loading:
            return loading
        page = request.args.get("page", 1, type=int)
        ctx = _build_feed_context(_get_index(), page)
        return _render_feed(ctx)

    @app.route("/search")
    def search() -> str:
        loading = _loading_or_ready()
        if loading:
            return loading
        query = clamp_query(request.args.get("q", ""))
        page = request.args.get("page", 1, type=int)
        posts = _filtered_posts(search=query) if query else []
        title = f'Search: "{query}"' if query else "Search"
        ctx = _build_feed_context(
            posts,
            page,
            search_query=query or None,
            feed_title=title,
        )
        return _render_feed(ctx)

    @app.route("/tags")
    def tags() -> str:
        loading = _loading_or_ready()
        if loading:
            return loading
        tag_counts = build_tag_counts(_get_index())
        return render_template("tags.html", tag_counts=tag_counts)

    @app.route("/tag/<tag>")
    def tag_feed(tag: str) -> str:
        loading = _loading_or_ready()
        if loading:
            return loading
        if not is_valid_tag(tag):
            abort(404)
        page = request.args.get("page", 1, type=int)
        posts = _filtered_posts(tag=tag)
        ctx = _build_feed_context(
            posts,
            page,
            active_tag=tag,
            feed_title=f"#{tag}",
        )
        return _render_feed(ctx)

    @app.route("/type/<post_type>")
    def type_feed(post_type: str) -> str:
        loading = _loading_or_ready()
        if loading:
            return loading
        if post_type not in VALID_POST_TYPES:
            abort(404)
        page = request.args.get("page", 1, type=int)
        posts = _filtered_posts(post_type=post_type)
        ctx = _build_feed_context(
            posts,
            page,
            active_type=post_type,
            feed_title=post_type.title(),
        )
        return _render_feed(ctx)

    @app.route("/archive")
    def archive_index() -> str:
        loading = _loading_or_ready()
        if loading:
            return loading
        archive = build_archive_index(_get_index())
        years = [(year, sum(archive[year].values())) for year in sorted_years(archive)]
        return render_template("archive.html", years=years, active_year=None)

    @app.route("/archive/<int:year>")
    def archive_year(year: int) -> str:
        loading = _loading_or_ready()
        if loading:
            return loading
        archive = build_archive_index(_get_index())
        if year not in archive:
            abort(404)
        months = [
            (month, count, month_label(year, month))
            for month, count in sorted_months(archive[year])
        ]
        return render_template(
            "archive.html",
            years=None,
            active_year=year,
            months=months,
            year_total=sum(archive[year].values()),
        )

    @app.route("/archive/<int:year>/<int:month>")
    def archive_month(year: int, month: int) -> str:
        loading = _loading_or_ready()
        if loading:
            return loading
        if month < 1 or month > 12:
            abort(404)
        page = request.args.get("page", 1, type=int)
        posts = _filtered_posts(year=year, month=month)
        if not posts:
            abort(404)
        ctx = _build_feed_context(
            posts,
            page,
            archive_year=year,
            archive_month=month,
            feed_title=archive_heading(year, month),
        )
        return _render_feed(ctx)

    @app.route("/settings")
    def settings() -> str:
        loading = _loading_or_ready()
        if loading:
            return loading
        return render_template("settings.html")

    @app.route("/api/posts")
    def api_posts():
        loading = _loading_or_ready()
        if loading:
            return jsonify({"error": "Archive is still loading"}), 503
        tag = request.args.get("tag")
        if tag and not is_valid_tag(tag):
            return jsonify({"error": "Invalid tag"}), 400
        post_type = request.args.get("type")
        if post_type and post_type not in VALID_POST_TYPES:
            return jsonify({"error": f"Invalid post type: {post_type}"}), 400
        search = clamp_query(request.args.get("q", "")) or None
        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)
        page = request.args.get("page", 1, type=int)
        posts = _filtered_posts(
            tag=tag,
            post_type=post_type,
            search=search,
            year=year,
            month=month,
        )
        page_posts, page, total_pages = _paginate(posts, page)
        return jsonify(
            {
                "html": _render_post_cards(page_posts),
                "page": page,
                "total_pages": total_pages,
                "has_more": page < total_pages,
            }
        )

    @app.route("/post/<post_id>")
    def single_post(post_id: str) -> str:
        loading = _loading_or_ready()
        if loading:
            return loading
        if not is_valid_post_id(post_id):
            abort(404)
        posts = _get_index()
        post = next((item for item in posts if item.id == post_id), None)
        if not post:
            abort(404)
        share_url = url_for("single_post", post_id=post.id, _external=True)
        page_title = post.timestamp or f"Post {post.id}"
        og_image = preview_image_url(
            post,
            absolute_media_url=lambda name: url_for(
                "media", filename=name, _external=True
            ),
        )
        og_description = preview_description(post)
        return render_template(
            "post.html",
            post=post,
            share_url=share_url,
            page_title=page_title,
            og_image=og_image,
            og_description=og_description,
        )

    @app.route("/random")
    def random_post():
        loading = _loading_or_ready()
        if loading:
            return loading
        posts = _get_index()
        if not posts:
            abort(404)
        post = random.choice(posts)
        return redirect(url_for("single_post", post_id=post.id))

    @app.route("/healthz")
    def healthz():
        with _index_lock:
            if _index_error:
                return jsonify({"status": "error", "error": PUBLIC_INDEX_ERROR}), 503
            if _posts_index is None:
                progress = snapshot()
                return jsonify({"status": "loading", **progress}), 503
            post_count = len(_posts_index)
        return jsonify({"status": "ready", "posts": post_count}), 200

    @app.route("/api/index-status")
    def index_status():
        with _index_lock:
            if _index_error:
                return jsonify({"ready": False, "error": PUBLIC_INDEX_ERROR}), 500
            if _posts_index is None:
                progress = snapshot()
                return jsonify({"ready": False, **progress}), 200
            post_count = len(_posts_index)
        return jsonify({"ready": True, "posts": post_count}), 200

    @app.route("/background")
    def background_image() -> object:
        bg_path = app.config.get("BACKGROUND_IMAGE_PATH")
        if not bg_path or not bg_path.is_file():
            abort(404)
        return send_from_directory(bg_path.parent, bg_path.name)

    @app.route("/media/<path:filename>")
    def media(filename: str) -> object:
        safe_name = secure_filename(filename)
        if not safe_name or safe_name != Path(filename).name:
            abort(404)
        media_dir = archive_path / "media"
        if not media_dir.is_dir():
            abort(404)
        media_root = media_dir.resolve()
        resolved = (media_dir / safe_name).resolve()
        if not resolved.is_file() or not is_path_under(resolved, media_root):
            lower_name = safe_name.lower()
            for candidate in media_dir.iterdir():
                if candidate.is_file() and candidate.name.lower() == lower_name:
                    resolved = candidate.resolve()
                    break
            else:
                abort(404)
        if not is_path_under(resolved, media_root):
            abort(404)
        return send_from_directory(resolved.parent, resolved.name)

    @app.template_filter("tag_url")
    def tag_url_filter(tag: str) -> str:
        return url_for("tag_feed", tag=tag)

    @app.template_filter("month_name")
    def month_name_filter(month: int) -> str:
        return month_name[month]

    start_index_warmup(archive_path, cache_path)
    return app


app = create_app()
