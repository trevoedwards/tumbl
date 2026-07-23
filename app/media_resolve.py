"""Resolve local media files for Tumblr archive posts."""

from __future__ import annotations

import re
from pathlib import Path

MEDIA_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".mp3", ".m4a")
AUDIO_EXTENSIONS = (".mp3", ".m4a")
VIDEO_EXTENSIONS = (".mp4", ".mov")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

IMG_SRC_RE = re.compile(
    r"""src=(["']?)(/media/([^"'>\s]+))\1""",
    re.IGNORECASE,
)
MEDIA_REF_RE = re.compile(r"/media/([^\"'>\s]+)", re.IGNORECASE)


def _post_id_from_media_name(name: str) -> str | None:
    path = Path(name)
    if path.suffix.lower() not in MEDIA_EXTENSIONS:
        return None
    stem = path.stem
    if not stem:
        return None
    return stem.rsplit("_", 1)[0] if "_" in stem else stem


def _media_name_belongs_to_post(name: str, post_id: str) -> bool:
    path = Path(name)
    if path.suffix.lower() not in MEDIA_EXTENSIONS:
        return False
    stem = path.stem
    return stem == post_id or stem.startswith(f"{post_id}_")


def _dedupe_media_paths(candidates: list[Path]) -> list[Path]:
    deduped: list[Path] = []
    seen_names: set[str] = set()
    for path in sorted(candidates, key=lambda item: item.name):
        if path.name in seen_names:
            continue
        seen_names.add(path.name)
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


def _referenced_media_names(body_html: str) -> set[str]:
    return {match.group(1) for match in MEDIA_REF_RE.finditer(body_html)}


def _render_media_markup(path: Path) -> str:
    url = media_url(path)
    suffix = path.suffix.lower()
    if suffix in AUDIO_EXTENSIONS:
        return f'<audio controls preload="metadata" src="{url}"></audio>'
    if suffix in VIDEO_EXTENSIONS:
        return (
            f'<div class="video-embed">'
            f'<video controls preload="metadata" src="{url}"></video>'
            f"</div>"
        )
    return f'<img src="{url}" alt="">'


def unreferenced_local_media(body_html: str, local_files: list[Path]) -> list[Path]:
    """Return local media files not already referenced as ``/media/...`` in HTML."""
    referenced = _referenced_media_names(body_html)
    return [path for path in local_files if path.name not in referenced]


def _inject_unreferenced_media(body_html: str, local_files: list[Path]) -> str:
    blocks = [_render_media_markup(path) for path in unreferenced_local_media(body_html, local_files)]
    if not blocks:
        return body_html
    prefix = "\n".join(blocks)
    if body_html.strip():
        return f"{prefix}\n{body_html}"
    return prefix


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
    if matches:
        ref_names = [match.group(3) for match in matches]

        def _ref_is_valid(name: str) -> bool:
            if name in local_name_set:
                return True
            if not _media_name_belongs_to_post(name, post_id):
                return False
            candidate = media_dir / name
            if candidate.is_file():
                return True
            if media_dir.is_dir():
                return any(
                    path.is_file() and path.name.lower() == name.lower()
                    for path in media_dir.iterdir()
                )
            return False

        if not all(_ref_is_valid(name) for name in ref_names):
            local_idx = 0

            def replacer(match: re.Match[str]) -> str:
                nonlocal local_idx
                quote = match.group(1) or '"'
                name = match.group(3)
                if _ref_is_valid(name):
                    return match.group(0)
                if local_urls:
                    url = local_urls[local_idx % len(local_urls)]
                    local_idx += 1
                    return f"src={quote}{url}{quote}"
                return match.group(0)

            body_html = IMG_SRC_RE.sub(replacer, body_html)

    return _inject_unreferenced_media(body_html, local_files)
