#!/usr/bin/env python3
"""Apply wordpress-tags-patch.json to an existing WordPress site via REST API.

Replaces post_tag terms on each post (by slug). Requires a WordPress Application Password.

  set WP_URL=https://blog.example.com
  set WP_USER=your_admin_username
  set WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

  python scripts/apply_wordpress_tags_patch.py --dry-run --limit 1
  python scripts/apply_wordpress_tags_patch.py
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _basic_auth_header(user: str, app_password: str) -> str:
    token = base64.b64encode(f"{user}:{app_password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _request_json(
    method: str,
    url: str,
    *,
    auth: str,
    body: dict | None = None,
) -> tuple[int, object]:
    data = None
    headers = {
        "Authorization": auth,
        "Accept": "application/json",
        "User-Agent": "tumbl-wordpress-tags-patch/1.0",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {"message": str(exc)}
        except json.JSONDecodeError:
            payload = {"message": raw or str(exc)}
        return exc.code, payload


def _find_post_id(api_base: str, slug: str, auth: str) -> int | None:
    query = urllib.parse.urlencode({"slug": slug, "per_page": 1, "status": "any"})
    status, payload = _request_json("GET", f"{api_base}/wp/v2/posts?{query}", auth=auth)
    if status != 200 or not isinstance(payload, list) or not payload:
        return None
    post_id = payload[0].get("id")
    return int(post_id) if post_id is not None else None


class _TagResolver:
    def __init__(self, api_base: str, auth: str) -> None:
        self.api_base = api_base
        self.auth = auth
        self._cache: dict[str, int] = {}

    def resolve_ids(self, names: list[str]) -> list[int]:
        ids: list[int] = []
        for name in names:
            tag_id = self._resolve_one(name)
            if tag_id is not None:
                ids.append(tag_id)
        return ids

    def _resolve_one(self, name: str) -> int | None:
        key = name.strip().lower()
        if not key:
            return None
        if key in self._cache:
            return self._cache[key]

        query = urllib.parse.urlencode({"search": name, "per_page": 100})
        status, payload = _request_json(
            "GET", f"{self.api_base}/wp/v2/tags?{query}", auth=self.auth
        )
        if status == 200 and isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                item_name = str(item.get("name", "")).strip().lower()
                if item_name == key:
                    tag_id = int(item["id"])
                    self._cache[key] = tag_id
                    return tag_id

        status, created = _request_json(
            "POST",
            f"{self.api_base}/wp/v2/tags",
            auth=self.auth,
            body={"name": name.strip()},
        )
        if status in {200, 201} and isinstance(created, dict) and created.get("id") is not None:
            tag_id = int(created["id"])
            self._cache[key] = tag_id
            return tag_id
        return None


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--patch",
        type=Path,
        default=Path("wordpress-tags-patch.json"),
        help="Patch JSON from export_wordpress_tags_patch.py",
    )
    parser.add_argument(
        "--wp-url",
        default=os.environ.get("WP_URL") or os.environ.get("WORDPRESS_EXPORT_SITE_URL", ""),
        help="WordPress site root (WP_URL or WORDPRESS_EXPORT_SITE_URL)",
    )
    parser.add_argument("--user", default=os.environ.get("WP_USER", ""), help="WP username")
    parser.add_argument(
        "--app-password",
        default=os.environ.get("WP_APP_PASSWORD", ""),
        help="WP Application Password",
    )
    parser.add_argument("--dry-run", action="store_true", help="Lookup posts but do not update")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N patch posts")
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip first N patch posts (resume after interruption)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.15,
        help="Seconds between updates (default 0.15; raise if rate-limited)",
    )
    args = parser.parse_args()

    if not args.patch.is_file():
        print(f"Patch file not found: {args.patch}", file=sys.stderr)
        return 1
    if not args.wp_url or not args.user or not args.app_password:
        print(
            "Need --wp-url / --user / --app-password (or WP_URL, WP_USER, WP_APP_PASSWORD).",
            file=sys.stderr,
        )
        return 1

    payload = json.loads(args.patch.read_text(encoding="utf-8"))
    posts = payload.get("posts") or []
    if args.offset:
        posts = posts[args.offset :]
    if args.limit is not None:
        posts = posts[: args.limit]

    api_base = args.wp_url.rstrip("/") + "/wp-json"
    auth = _basic_auth_header(args.user, args.app_password.replace(" ", ""))
    tag_resolver = _TagResolver(api_base, auth)

    status, me = _request_json("GET", f"{api_base}/wp/v2/users/me", auth=auth)
    if status != 200:
        print(f"Auth failed ({status}): {me}", file=sys.stderr)
        return 1
    print(f"Authenticated as {(me or {}).get('name') or (me or {}).get('slug')}")

    updated = 0
    missing = 0
    failed = 0
    for index, item in enumerate(posts, start=1):
        slug = item["slug"]
        tags = item.get("tags") or []
        wp_id = _find_post_id(api_base, slug, auth)
        if wp_id is None:
            missing += 1
            print(f"[{index}/{len(posts)}] MISSING slug={slug}")
            continue

        tag_ids = tag_resolver.resolve_ids(tags)

        if args.dry_run:
            updated += 1
            print(
                f"[{index}/{len(posts)}] DRY-RUN would set id={wp_id} slug={slug} "
                f"tags={tags!r} -> ids={tag_ids}"
            )
            continue

        status, result = _request_json(
            "POST",
            f"{api_base}/wp/v2/posts/{wp_id}",
            auth=auth,
            body={"tags": tag_ids},
        )
        if status in {200, 201}:
            updated += 1
            print(f"[{index}/{len(posts)}] OK id={wp_id} slug={slug} tags={tags!r}")
        else:
            failed += 1
            print(f"[{index}/{len(posts)}] FAIL id={wp_id} slug={slug} ({status}): {result}")

        if args.sleep > 0:
            time.sleep(args.sleep)

    print(
        f"Done. updated={updated} missing={missing} failed={failed} "
        f"dry_run={args.dry_run}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
