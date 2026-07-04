"""Tests for local media resolution helpers."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from app.media_resolve import build_media_index, find_local_media, resolve_post_media_refs
from app.parsers.legacy_html import parse_post_file


class MediaResolveTests(unittest.TestCase):
    def test_find_local_media_matches_exact_and_variant_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "12345.jpg").write_bytes(b"j")
            (media_dir / "12345_0.png").write_bytes(b"p")
            (media_dir / "12345_1.png").write_bytes(b"skip")
            (media_dir / "99999.png").write_bytes(b"x")

            found = find_local_media(media_dir, "12345")
            self.assertEqual([path.name for path in found], ["12345.jpg", "12345_0.png", "12345_1.png"])

    def test_build_media_index_groups_files_by_post_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "12345.jpg").write_bytes(b"j")
            (media_dir / "12345_0.png").write_bytes(b"p")
            (media_dir / "309396265.png").write_bytes(b"x")

            index = build_media_index(media_dir)
            self.assertEqual(
                [path.name for path in find_local_media(media_dir, "12345", media_index=index)],
                ["12345.jpg", "12345_0.png"],
            )

    def test_find_local_media_avoids_numeric_prefix_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "309396265.png").write_bytes(b"p")

            self.assertEqual(find_local_media(media_dir, "30939626"), [])
            self.assertEqual(
                [path.name for path in find_local_media(media_dir, "309396265")],
                ["309396265.png"],
            )

    def test_resolve_post_media_refs_replaces_stale_html_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "152638647575.jpg").write_bytes(b"j")
            body = '<img src="/media/309396265.png" alt="">'
            fixed = resolve_post_media_refs(body, "152638647575", media_dir)
            self.assertIn('src="/media/152638647575.jpg"', fixed)
            self.assertNotIn("309396265.png", fixed)

    def test_resolve_post_media_refs_keeps_correct_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "309396265.png").write_bytes(b"p")
            body = '<img src="/media/309396265.png" alt="">'
            fixed = resolve_post_media_refs(body, "309396265", media_dir)
            self.assertEqual(fixed, body)

    def test_resolve_post_media_refs_handles_unquoted_src(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "152638647575.jpg").write_bytes(b"j")
            body = '<img src=/media/309396265.png alt="">'
            fixed = resolve_post_media_refs(body, "152638647575", media_dir)
            self.assertIn('src="/media/152638647575.jpg"', fixed)

    def test_resolve_post_media_refs_keeps_photoset_indices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            for idx in range(4):
                (media_dir / f"100110448605_{idx}.gif").write_bytes(b"x")
            body = "".join(
                f'<img src="/media/100110448605_{idx}.gif" alt="">'
                for idx in range(4)
            )
            fixed = resolve_post_media_refs(body, "100110448605", media_dir)
            self.assertEqual(fixed, body)

    def test_resolve_post_media_refs_cycles_through_local_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "119248693340_0.gif").write_bytes(b"a")
            (media_dir / "119248693340_1.gif").write_bytes(b"a1")
            (media_dir / "119248693340_2.gif").write_bytes(b"b")
            (media_dir / "119248693340_3.gif").write_bytes(b"b1")
            (media_dir / "119248693340_4.gif").write_bytes(b"c")
            (media_dir / "119248693340_5.gif").write_bytes(b"c1")
            body = "".join(
                f'<img src="/media/309396265.png" alt="">' for _ in range(6)
            )
            fixed = resolve_post_media_refs(body, "119248693340", media_dir)
            self.assertNotIn("309396265.png", fixed)
            self.assertEqual(fixed.count('src="/media/119248693340_0.gif"'), 1)
            self.assertEqual(fixed.count('src="/media/119248693340_1.gif"'), 1)
            self.assertEqual(fixed.count('src="/media/119248693340_2.gif"'), 1)
            self.assertEqual(fixed.count('src="/media/119248693340_3.gif"'), 1)
            self.assertEqual(fixed.count('src="/media/119248693340_4.gif"'), 1)
            self.assertEqual(fixed.count('src="/media/119248693340_5.gif"'), 1)

    def test_legacy_parser_rewrites_wrong_export_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_root = Path(tmp)
            html_dir = archive_root / "posts" / "html"
            html_dir.mkdir(parents=True)
            (archive_root / "media").mkdir()
            (archive_root / "media" / "12345.jpg").write_bytes(b"j")
            (archive_root / "media" / "309396265.png").write_bytes(b"p")
            (html_dir / "12345.html").write_text(
                textwrap.dedent(
                    """\
                    <!DOCTYPE HTML>
                    <html><body>
                    <img src="../../media/309396265.png"/>
                    <div id="footer"><span id="timestamp">Jan 1 2020</span></div>
                    </body></html>
                    """
                ),
                encoding="utf-8",
            )

            post = parse_post_file(html_dir / "12345.html", archive_root)
            assert post is not None
            self.assertIn('src="/media/12345.jpg"', post.body_html)
            self.assertNotIn("309396265.png", post.body_html)


if __name__ == "__main__":
    unittest.main()
