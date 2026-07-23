#!/usr/bin/env python3
"""Export corrected post tags for updating an existing WordPress site via REST API.

Uses tumbl's rebuilt index (legacy HTML / tumblr-utils). After fixing reblog footer
tag parsing, run this to generate a JSON patch and apply with
``apply_wordpress_tags_patch.py``.

Usage:

  python scripts/export_wordpress_tags_patch.py
  python scripts/export_wordpress_tags_patch.py --ids 123456789012 --limit 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.exporters.wordpress_wxr import post_slug
from app.parser import get_or_build_index
from app.tag_overrides import apply_tag_overrides, load_tag_overrides


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


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
        default=Path("wordpress-tags-patch.json"),
        help="Patch JSON path (default: wordpress-tags-patch.json)",
    )
    parser.add_argument(
        "--ids",
        nargs="*",
        default=None,
        help="Optional Tumblr post IDs to include (default: all posts)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after N posts (smoke test)",
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

    site_url = os.environ.get("WORDPRESS_EXPORT_SITE_URL", "").strip().rstrip("/")
    only_ids = set(args.ids) if args.ids else None
    cache_dir = Path(os.environ.get("CACHE_DIR", ".cache"))

    posts = get_or_build_index(archive_root, cache_root=cache_dir)
    overrides = load_tag_overrides(cache_dir)
    apply_tag_overrides(posts, overrides)
    patch_posts = []
    for post in posts:
        if only_ids is not None and post.id not in only_ids:
            continue
        patch_posts.append(
            {
                "id": post.id,
                "slug": post_slug(post.id, minimal=args.minimal),
                "tags": post.tags,
            }
        )
        if args.limit is not None and len(patch_posts) >= args.limit:
            break

    payload = {
        "site_url": site_url or None,
        "minimal": bool(args.minimal),
        "post_count": len(patch_posts),
        "posts": patch_posts,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(patch_posts)} posts → {args.output.resolve()}")
    if patch_posts:
        example = patch_posts[0]
        print(f"Example slug={example['slug']} tags={example['tags']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
