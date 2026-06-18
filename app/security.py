"""Security helpers for path validation, identifiers, and HTTP headers."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from flask import Response

logger = logging.getLogger(__name__)

POST_ID_RE = re.compile(r"^\d+$")
PUBLIC_INDEX_ERROR = "Archive index could not be built. Check server logs for details."

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' https: data:; "
    "media-src 'self' https:; "
    "frame-src https:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'self'"
)


def is_valid_post_id(post_id: str) -> bool:
    return bool(POST_ID_RE.fullmatch(post_id))


def is_path_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def resolve_allowed_file(path_value: str, allowed_roots: list[Path]) -> Path | None:
    """Resolve a filesystem path only when it is a regular file under allowed roots."""
    candidate = Path(path_value)
    if not candidate.is_file():
        return None
    resolved = candidate.resolve()
    for root in allowed_roots:
        if is_path_under(resolved, root):
            return resolved
    logger.warning("Rejected file path outside allowed directories: %s", resolved)
    return None


def is_safe_http_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def apply_security_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    return response
