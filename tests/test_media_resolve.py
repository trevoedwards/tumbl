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

    def test_unreferenced_local_media_lists_missing_refs(self) -> None:
        from app.media_resolve import unreferenced_local_media

        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            kept = media_dir / "12345.jpg"
            missing = media_dir / "12345_0.png"
            kept.write_bytes(b"j")
            missing.write_bytes(b"p")
            body = '<img src="/media/12345.jpg" alt="">'
            result = unreferenced_local_media(body, [kept, missing])
            self.assertEqual([path.name for path in result], ["12345_0.png"])

    def test_resolve_post_media_refs_injects_image_when_html_has_no_img(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "123456789012.jpg").write_bytes(b"j")
            body = (
                '<a href="https://www.instagram.com/p/BcIVWKhFY-0/ "></a>'
                '<div class="caption"><p>Scored these three bad boys for $6.</p></div>'
            )
            fixed = resolve_post_media_refs(body, "123456789012", media_dir)
            self.assertTrue(fixed.startswith('<img src="/media/123456789012.jpg"'))
            self.assertIn("instagram.com", fixed)

    def test_resolve_post_media_refs_injects_photoset_when_html_has_no_img(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "100110448605_0.gif").write_bytes(b"a")
            (media_dir / "100110448605_1.gif").write_bytes(b"b")
            body = '<div class="caption"><p>Two photos</p></div>'
            fixed = resolve_post_media_refs(body, "100110448605", media_dir)
            self.assertIn('src="/media/100110448605_0.gif"', fixed)
            self.assertIn('src="/media/100110448605_1.gif"', fixed)

    def test_resolve_post_media_refs_does_not_duplicate_existing_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "12345.jpg").write_bytes(b"j")
            body = '<img src="/media/12345.jpg" alt=""><div class="caption"><p>Hi</p></div>'
            fixed = resolve_post_media_refs(body, "12345", media_dir)
            self.assertEqual(fixed.count('src="/media/12345.jpg"'), 1)

    def test_resolve_post_media_refs_does_not_duplicate_existing_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "33641710510.mp3").write_bytes(b"a")
            body = '<audio controls preload="metadata" src="/media/33641710510.mp3"></audio>'
            fixed = resolve_post_media_refs(body, "33641710510", media_dir)
            self.assertEqual(fixed.count('src="/media/33641710510.mp3"'), 1)

    def test_resolve_post_media_refs_injects_audio_when_html_has_embed_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "33641710510.mp3").write_bytes(b"a")
            body = '<div class="caption"><p>Track title</p></div>'
            fixed = resolve_post_media_refs(body, "33641710510", media_dir)
            self.assertIn('<audio controls preload="metadata" src="/media/33641710510.mp3">', fixed)

    def test_legacy_parser_injects_local_media_when_html_has_no_img(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_root = Path(tmp)
            html_dir = archive_root / "posts" / "html"
            html_dir.mkdir(parents=True)
            (archive_root / "media").mkdir()
            (archive_root / "media" / "123456789012.jpg").write_bytes(b"j")
            (html_dir / "123456789012.html").write_text(
                textwrap.dedent(
                    """\
                    <!DOCTYPE HTML>
                    <html><body>
                    <a href="https://www.instagram.com/p/BcIVWKhFY-0/ "></a>
                    <div class="caption"><p>Scored these three bad boys for $6.</p></div>
                    <div id="footer"><span id="timestamp">Nov 30 2017</span></div>
                    </body></html>
                    """
                ),
                encoding="utf-8",
            )

            post = parse_post_file(html_dir / "123456789012.html", archive_root)
            assert post is not None
            self.assertIn('src="/media/123456789012.jpg"', post.body_html)
            self.assertEqual(post.post_type, "photo")

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
