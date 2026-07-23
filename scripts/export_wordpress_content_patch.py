#!/usr/bin/env python3
"""Export a content patch for WordPress posts that were missing local media.

Identifies legacy / tumblr-utils posts that had ``media/{postId}.*`` on disk but
no ``/media/`` reference in the original HTML, then writes fixed post HTML
(matching the WXR wrapper + absolute media URLs) for a targeted WordPress update.

Usage (from repo root, Python 3.12+ or Docker):

  python scripts/export_wordpress_content_patch.py
  python scripts/export_wordpress_content_patch.py --limit 1 --ids 123456789012

Output: wordpress-content-patch.json (gitignored path under repo root by default)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow ``python scripts/...`` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bs4 import BeautifulSoup

from app.exporters.wordpress_theme import ThemeStyles, fetch_theme_styles
from app.exporters.wordpress_wxr import (
    post_slug,
    rewrite_media_urls,
    wrap_post_html,
)
from app.html_sanitize import sanitize_post_html
from app.media_resolve import (
    build_media_index,
    find_local_media,
    unreferenced_local_media,
)
from app.parsers.legacy_html import _process_body_html, discover_post_files, parse_post_file


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _body_before_media_resolve(html_path: Path) -> str | None:
    try:
        raw = html_path.read_text(encoding="utf-8")
    except OSError:
        return None
    soup = BeautifulSoup(raw, "lxml")
    body = soup.find("body")
    if not body:
        return None
    footers = body.find_all("div", id="footer")
    if footers:
        footers[-1].decompose()
    return _process_body_html(body.decode_contents())


def _collect_affected_posts(
    archive_root: Path,
    *,
    only_ids: set[str] | None,
    limit: int | None,
) -> list:
    media_dir = archive_root / "media"
    media_index = build_media_index(media_dir)
    paths = discover_post_files(archive_root)
    affected = []

    for path in paths:
        post_id = path.stem
        if only_ids is not None and post_id not in only_ids:
            continue

        local_files = find_local_media(media_dir, post_id, media_index=media_index)
        if not local_files:
            continue

        body_before = _body_before_media_resolve(path)
        if body_before is None:
            continue
        if not unreferenced_local_media(body_before, local_files):
            continue

        post = parse_post_file(path, archive_root, media_index=media_index)
        if post is None:
            continue
        post.body_html = sanitize_post_html(post.body_html)
        affected.append((post, [path.name for path in local_files]))
        if limit is not None and len(affected) >= limit:
            break

    return affected


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path(os.environ.get("ARCHIVE_PATH", ".tumblrbackup")),
        help="Tumblr archive root (default: ARCHIVE_PATH or .tumblrbackup)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("wordpress-content-patch.json"),
        help="Patch JSON path (default: wordpress-content-patch.json)",
    )
    parser.add_argument(
        "--ids",
        nargs="*",
        default=None,
        help="Optional Tumblr post IDs to include (default: all affected)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after N affected posts (useful for a smoke test)",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        default=_env_flag("WORDPRESS_EXPORT_MINIMAL"),
        help="Use post-{id} slugs (WORDPRESS_EXPORT_MINIMAL)",
    )
    args = parser.parse_args()

    archive_root = args.archive.resolve()
    if not archive_root.is_dir():
        print(f"Archive not found: {archive_root}", file=sys.stderr)
        return 1

    media_base = os.environ.get("WORDPRESS_EXPORT_MEDIA_BASE_URL", "").strip().rstrip("/")
    if not media_base:
        print(
            "WORDPRESS_EXPORT_MEDIA_BASE_URL is required so patched HTML uses absolute media URLs.",
            file=sys.stderr,
        )
        return 1

    site_url = os.environ.get("WORDPRESS_EXPORT_SITE_URL", "").strip().rstrip("/")
    match_theme = _env_flag("WORDPRESS_EXPORT_MATCH_THEME")
    theme_styles: ThemeStyles | None = None
    if match_theme and site_url:
        theme_styles = fetch_theme_styles(site_url)

    only_ids = set(args.ids) if args.ids else None
    affected = _collect_affected_posts(
        archive_root,
        only_ids=only_ids,
        limit=args.limit,
    )

    patch_posts = []
    for post, media_names in affected:
        body_html = rewrite_media_urls(post.body_html, media_base)
        content = wrap_post_html(body_html, post.id, theme_styles)
        patch_posts.append(
            {
                "id": post.id,
                "slug": post_slug(post.id, minimal=args.minimal),
                "content": content,
                "media": media_names,
            }
        )

    payload = {
        "site_url": site_url or None,
        "media_base_url": media_base,
        "minimal": bool(args.minimal),
        "post_count": len(patch_posts),
        "posts": patch_posts,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(patch_posts)} posts → {args.output.resolve()}")
    if patch_posts:
        print(f"Example slug: {patch_posts[0]['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
