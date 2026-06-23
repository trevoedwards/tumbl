"""Resolve local media files for Tumblr archive posts."""

from __future__ import annotations

import re
from pathlib import Path

MEDIA_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".mp3", ".m4a")

IMG_SRC_RE = re.compile(
    r"""src=(["']?)(/media/([^"'>\s]+))\1""",
    re.IGNORECASE,
)


def _post_id_from_media_name(name: str) -> str | None:
    path = Path(name)
    if path.suffix.lower() not in MEDIA_EXTENSIONS:
        return None
    stem = path.stem
    if not stem:
        return None
    return stem.rsplit("_", 1)[0] if "_" in stem else stem


def _dedupe_media_paths(candidates: list[Path]) -> list[Path]:
    deduped: list[Path] = []
    seen_stems: set[str] = set()
    for path in sorted(candidates, key=lambda item: item.name):
        stem = path.stem
        if "_" in stem:
            suffix = stem.rsplit("_", 1)[-1]
            if suffix.isdigit() and int(suffix) % 2 == 1:
                continue
        if stem in seen_stems:
            continue
        seen_stems.add(stem)
        deduped.append(path)
    return deduped


def build_media_index(media_dir: Path) -> dict[str, list[Path]]:
    """Scan ``media_dir`` once and group files by post id."""
    index: dict[str, list[Path]] = {}
    if not media_dir.is_dir():
        return index

    for path in media_dir.iterdir():
        if not path.is_file():
            continue
        post_id = _post_id_from_media_name(path.name)
        if post_id is None:
            continue
        index.setdefault(post_id, []).append(path)

    return index


def find_local_media(
    media_dir: Path,
    post_id: str,
    *,
    media_index: dict[str, list[Path]] | None = None,
) -> list[Path]:
    """Return media files in ``media_dir`` that belong to ``post_id``."""
    if media_index is not None:
        return _dedupe_media_paths(media_index.get(post_id, []))

    if not media_dir.is_dir():
        return []

    candidates: list[Path] = []
    for path in media_dir.iterdir():
        if not path.is_file():
            continue
        name = path.name
        if name == f"{post_id}{path.suffix}":
            candidates.append(path)
        elif name.startswith(f"{post_id}_") and path.suffix.lower() in MEDIA_EXTENSIONS:
            candidates.append(path)

    return _dedupe_media_paths(candidates)


def media_url(path: Path) -> str:
    return f"/media/{path.name}"


def resolve_post_media_refs(
    body_html: str,
    post_id: str,
    media_dir: Path,
    *,
    media_index: dict[str, list[Path]] | None = None,
) -> str:
    """Prefer post-specific local media when HTML img refs point elsewhere."""
    local_files = find_local_media(media_dir, post_id, media_index=media_index)
    if not local_files:
        return body_html

    local_names = [path.name for path in local_files]
    local_name_set = set(local_names)
    local_urls = [media_url(path) for path in local_files]

    matches = list(IMG_SRC_RE.finditer(body_html))
    if not matches:
        return body_html

    ref_names = [match.group(3) for match in matches]
    if all(name in local_name_set for name in ref_names):
        return body_html

    local_idx = 0

    def replacer(match: re.Match[str]) -> str:
        nonlocal local_idx
        quote = match.group(1) or '"'
        name = match.group(3)
        if name in local_name_set:
            return match.group(0)
        if local_urls:
            url = local_urls[local_idx % len(local_urls)]
            local_idx += 1
            return f"src={quote}{url}{quote}"
        return match.group(0)

    return IMG_SRC_RE.sub(replacer, body_html)
