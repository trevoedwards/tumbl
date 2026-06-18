"""Tests for Tumblr URL and reblog metadata extraction."""

from __future__ import annotations

import textwrap
import unittest
import xml.etree.ElementTree as ET

from app.post_metadata import (
    blog_name_from_url,
    extract_from_body_html,
    extract_from_xml_post,
    local_post_id_from_url,
    merge_metadata,
)


class PostMetadataTests(unittest.TestCase):
    def test_local_post_id_from_url(self) -> None:
        self.assertEqual(
            local_post_id_from_url("https://example.tumblr.com/post/123456/slug"),
            "123456",
        )

    def test_blog_name_from_url(self) -> None:
        self.assertEqual(
            blog_name_from_url("https://example-blog.tumblr.com/post/1/x"),
            "example-blog",
        )

    def test_extract_from_body_html_finds_reblog_context(self) -> None:
        body = (
            '<p>reblogged from <a href="https://one.tumblr.com/post/100/a">one</a></p>'
            '<p><a href="https://two.tumblr.com/post/200/b">mine</a></p>'
        )
        url, parent_url, parent_name = extract_from_body_html(body)
        self.assertEqual(parent_url, "https://one.tumblr.com/post/100/a")
        self.assertEqual(url, "https://two.tumblr.com/post/200/b")
        self.assertEqual(parent_name, "one")

    def test_extract_from_xml_post_reads_url_attribute(self) -> None:
        xml = textwrap.dedent(
            """\
            <post id="100" url="https://mine.tumblr.com/post/100/hello" type="regular">
              <regular-body><![CDATA[<p>Hello</p>]]></regular-body>
            </post>
            """
        )
        post_el = ET.fromstring(xml)
        url, parent_url, parent_name = extract_from_xml_post(post_el)
        self.assertEqual(url, "https://mine.tumblr.com/post/100/hello")
        self.assertIsNone(parent_url)
        self.assertIsNone(parent_name)

    def test_merge_metadata_prefers_xml_values(self) -> None:
        url, parent_url, parent_name = merge_metadata(
            tumblr_url="https://mine.tumblr.com/post/1/a",
            reblog_parent_url="https://parent.tumblr.com/post/2/b",
            reblog_parent_name="parent",
            body_html='<a href="https://ignored.tumblr.com/post/3/c">x</a>',
        )
        self.assertEqual(url, "https://mine.tumblr.com/post/1/a")
        self.assertEqual(parent_url, "https://parent.tumblr.com/post/2/b")
        self.assertEqual(parent_name, "parent")


if __name__ == "__main__":
    unittest.main()
