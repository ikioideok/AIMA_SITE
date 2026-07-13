#!/usr/bin/env python3

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shinpo_queue
from shinpo_publish import (
    is_recommended_title_length,
    is_valid_title_length,
    normalize_category,
    update_sitemap_contents,
)
from shinpo_watch import is_ai_related
from shinpo_x_watch import XWatchError, parse_hermes_result


class HermesParserTest(unittest.TestCase):
    def test_accepts_only_cited_x_post(self):
        url = "https://x.com/OpenAI/status/1234567890"
        raw = json.dumps(
            {
                "success": True,
                "degraded": False,
                "answer": json.dumps(
                    [
                        {
                            "url": url,
                            "handle": "OpenAI",
                            "posted_at": "2026-07-10T12:00:00Z",
                            "title": "OpenAIが新機能を発表",
                            "summary": "公式発表の要約",
                        }
                    ]
                ),
                "citations": [url],
                "inline_citations": [],
            }
        )
        items = parse_hermes_result(raw)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], url)
        self.assertTrue(items[0]["official"])
        self.assertTrue(items[0]["verification_required"])

    def test_rejects_degraded_result(self):
        raw = json.dumps(
            {
                "success": True,
                "degraded": True,
                "degraded_reason": "no citations",
                "answer": "https://x.com/OpenAI/status/999",
                "citations": [],
            }
        )
        with self.assertRaises(XWatchError):
            parse_hermes_result(raw)

    def test_maps_internal_citation_to_official_answer_url(self):
        official_url = "https://x.com/NVIDIAAI/status/2222222222"
        raw = json.dumps(
            {
                "success": True,
                "degraded": False,
                "answer": json.dumps(
                    [
                        {
                            "url": official_url,
                            "title": "NVIDIAがAI研究を発表",
                            "summary": "公式発表の要約",
                        }
                    ]
                ),
                "citations": [],
                "inline_citations": [{"url": "https://x.com/i/status/2222222222"}],
            }
        )
        items = parse_hermes_result(raw)
        self.assertEqual([item["url"] for item in items], [official_url])


class QueueTest(unittest.TestCase):
    def test_mark_by_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue_path = Path(tmp) / "queue.json"
            queue_path.write_text(
                json.dumps({"items": [{"url": "https://example.com", "status": "new"}]})
            )
            with patch.object(shinpo_queue, "QUEUE_PATH", queue_path):
                changed = shinpo_queue.mark_by_url(
                    "https://example.com", "drafted", "shinpo/drafts/test.json"
                )
                self.assertTrue(changed)
                item = json.loads(queue_path.read_text())["items"][0]
                self.assertEqual(item["status"], "drafted")
                self.assertEqual(item["draft_path"], "shinpo/drafts/test.json")


class KeywordTest(unittest.TestCase):
    def test_ai_is_matched_as_a_word(self):
        self.assertTrue(is_ai_related("AMD Ryzen AI Halo review"))
        self.assertFalse(is_ai_related("Snails' teeth beats spider silk"))


class CategoryTest(unittest.TestCase):
    def test_normalizes_legacy_categories(self):
        self.assertEqual(normalize_category("企業"), "企業動向")
        self.assertEqual(normalize_category("製品"), "プロダクト")
        self.assertEqual(normalize_category("モデル"), "生成AI")

    def test_keeps_public_categories(self):
        self.assertEqual(normalize_category("セキュリティ"), "セキュリティ")
        self.assertEqual(normalize_category("お知らせ"), "お知らせ")


class TitleLengthTest(unittest.TestCase):
    def test_accepts_publishable_title_range(self):
        self.assertTrue(is_valid_title_length("あ" * 20))
        self.assertTrue(is_valid_title_length("あ" * 64))

    def test_rejects_titles_outside_publishable_range(self):
        self.assertFalse(is_valid_title_length("あ" * 19))
        self.assertFalse(is_valid_title_length("あ" * 65))

    def test_recommends_compact_titles(self):
        self.assertTrue(is_recommended_title_length("あ" * 30))
        self.assertTrue(is_recommended_title_length("あ" * 50))
        self.assertFalse(is_recommended_title_length("あ" * 29))
        self.assertFalse(is_recommended_title_length("あ" * 51))


class SitemapTest(unittest.TestCase):
    def test_adds_article_once_and_updates_home_lastmod(self):
        source = """<urlset>
  <url>
    <loc>https://ai-and-marketing.jp/shinpo/</loc>
    <lastmod>2026-07-01</lastmod>
  </url>
</urlset>"""
        url = "https://ai-and-marketing.jp/shinpo/2026-07-12-example.html"
        updated = update_sitemap_contents(source, url, "2026-07-12")
        updated_again = update_sitemap_contents(updated, url, "2026-07-12")
        self.assertIn("<lastmod>2026-07-12</lastmod>", updated)
        self.assertEqual(updated_again.count(url), 1)


if __name__ == "__main__":
    unittest.main()
