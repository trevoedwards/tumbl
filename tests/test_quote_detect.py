"""Tests for legacy quote detection and normalization."""

from __future__ import annotations

import textwrap
import unittest

from bs4 import BeautifulSoup

from app.parsers.quote_detect import infer_is_quote, normalize_quote_html


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


class QuoteDetectTests(unittest.TestCase):
    def test_infer_plain_caption_quote(self) -> None:
        body_html = textwrap.dedent(
            """\
            Directly, or indirectly, everything we write is for someone.
            <div class="caption">&mdash; (via <a class="tumblr_blog" href="http://example.tumblr.com/">example</a>)</div>
            """
        )
        soup = _soup(f"<html><body>{body_html}</body></html>")
        self.assertTrue(
            infer_is_quote(soup, body_html=body_html, tags=["quotes"])
        )

    def test_infer_rejects_photo_with_caption(self) -> None:
        body_html = (
            '<img src="/media/1.jpg"/>'
            '<div class="caption"><p>A photo post</p></div>'
        )
        soup = _soup(f"<html><body>{body_html}</body></html>")
        self.assertFalse(infer_is_quote(soup, body_html=body_html))

    def test_infer_rejects_submission(self) -> None:
        body_html = (
            '<blockquote><p>Quoted</p></blockquote>'
            '<p>Author</p>'
        )
        soup = _soup(f"<html><body>{body_html}</body></html>")
        self.assertFalse(
            infer_is_quote(soup, body_html=body_html, is_submission=True)
        )

    def test_infer_rejects_reblog_parent(self) -> None:
        body_html = (
            '<blockquote><p>Quoted</p></blockquote>'
            '<p>Author</p>'
        )
        soup = _soup(f"<html><body>{body_html}</body></html>")
        self.assertFalse(
            infer_is_quote(
                soup,
                body_html=body_html,
                reblog_parent_url="https://other.tumblr.com/post/123/456",
            )
        )

    def test_normalize_plain_caption_quote(self) -> None:
        body_html = textwrap.dedent(
            """\
            Stay curious.
            <div class="caption">&mdash; Ada Lovelace</div>
            """
        )
        normalized = normalize_quote_html(body_html)
        self.assertIn('<blockquote class="quote-text">', normalized)
        self.assertIn("Stay curious.", normalized)
        self.assertIn('<cite class="quote-source">— Ada Lovelace</cite>', normalized)

    def test_normalize_blockquote_quote(self) -> None:
        body_html = (
            "<blockquote><p>Stay curious.</p></blockquote>"
            "<p>Ada Lovelace</p>"
        )
        normalized = normalize_quote_html(body_html)
        self.assertIn('<blockquote class="quote-text"><p>Stay curious.</p></blockquote>', normalized)
        self.assertIn('<cite class="quote-source">— Ada Lovelace</cite>', normalized)

    def test_infer_article_class_quote(self) -> None:
        html = textwrap.dedent(
            """\
            <html><body>
            <article class="quote">
              <blockquote><p>Quoted</p></blockquote>
              <p>Source</p>
            </article>
            </body></html>
            """
        )
        soup = _soup(html)
        article = soup.find("article")
        body_html = article.decode_contents()
        self.assertTrue(
            infer_is_quote(soup, body_html=body_html, article=article)
        )
        normalized = normalize_quote_html(body_html, article=article)
        self.assertNotIn("<header", normalized)
        self.assertIn('<cite class="quote-source">— Source</cite>', normalized)


if __name__ == "__main__":
    unittest.main()
