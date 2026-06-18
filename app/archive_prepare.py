"""Prepare archive directories before format detection and indexing."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path, PurePosixPath

logger = logging.getLogger(__name__)

# Large Tumblr exports can exceed 5 GB and 15k files when uncompressed.
MAX_ZIP_FILES = 100_000
MAX_ZIP_UNCOMPRESSED_BYTES = 10 * 1024 * 1024 * 1024


def _is_safe_zip_member(name: str, destination: Path) -> bool:
    if not name or name.startswith("/") or PurePosixPath(name).is_absolute():
        return False
    if ".." in PurePosixPath(name).parts:
        return False
    target = (destination / name).resolve()
    dest_root = destination.resolve()
    return target == dest_root or dest_root in target.parents


def _validate_zip_archive(archive: zipfile.ZipFile, destination: Path) -> None:
    total_uncompressed = 0
    file_count = 0
    for info in archive.infolist():
        file_count += 1
        if file_count > MAX_ZIP_FILES:
            raise ValueError(f"Zip archive exceeds {MAX_ZIP_FILES} files")
        if not _is_safe_zip_member(info.filename, destination):
            raise ValueError(f"Unsafe zip entry path: {info.filename!r}")
        if info.is_dir():
            continue
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_ZIP_UNCOMPRESSED_BYTES:
            raise ValueError(
                f"Zip archive exceeds {MAX_ZIP_UNCOMPRESSED_BYTES} bytes uncompressed"
            )


def _extract_zip(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        _validate_zip_archive(archive, destination)
        archive.extractall(destination)
    logger.info("Extracted %s to %s", zip_path.name, destination)


def prepare_archive(archive_root: Path) -> None:
    """Auto-extract Tumblr export zips when posts have not been unpacked yet."""
    if not archive_root.is_dir():
        return

    posts_dir = archive_root / "posts"
    posts_xml = posts_dir / "posts.xml"
    nested_posts_zip = posts_dir / "posts.zip"

    root_zip = archive_root / "posts.zip"
    if root_zip.is_file() and not posts_dir.is_dir():
        _extract_zip(root_zip, posts_dir)
    elif root_zip.is_file() and posts_dir.is_dir() and not posts_xml.is_file():
        if not any(posts_dir.iterdir()):
            _extract_zip(root_zip, posts_dir)
        elif nested_posts_zip.is_file() and not posts_xml.is_file():
            _extract_zip(nested_posts_zip, posts_dir)
    elif nested_posts_zip.is_file() and not posts_xml.is_file():
        _extract_zip(nested_posts_zip, posts_dir)
