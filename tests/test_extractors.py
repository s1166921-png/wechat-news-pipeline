import unittest

from pipeline_core.extractors import (
    article_failure,
    article_success,
    is_usable_article_content,
    normalize_article_result,
    assess_article_quality,
    strip_extractor_metadata,
)


class ArticleResultTests(unittest.TestCase):
    def test_article_success_adds_standard_fields(self):
        result = article_success(
            title="标题",
            content="正文内容" * 20,
            source_url="https://example.com/a",
            extraction_method="beautifulsoup",
            author="作者",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["title"], "标题")
        self.assertEqual(result["char_count"], len("正文内容" * 20))
        self.assertFalse(result["manual_import_recommended"])
        self.assertEqual(result["error_hint"], "")

    def test_article_failure_recommends_manual_import_for_wechat(self):
        result = article_failure(
            "https://mp.weixin.qq.com/s/abc",
            status="blocked",
            error_hint="服务器无法直接访问公众号文章",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["manual_import_recommended"])
        self.assertIn("公众号", result["error_hint"])

    def test_normalize_existing_article_result_fills_missing_fields(self):
        result = normalize_article_result({
            "title": "标题",
            "content": "正文",
            "source_url": "https://example.com/a",
            "extraction_method": "legacy",
        })

        self.assertTrue(result["ok"])
        self.assertEqual(result["char_count"], 2)
        self.assertEqual(result["status"], "ok")

    def test_strip_extractor_metadata_removes_yaml_front_matter(self):
        content = """---
title: 标题
author: 作者
url: https://mp.weixin.qq.com/s/abc
---

这里才是正文第一段。

这里是正文第二段。"""

        cleaned = strip_extractor_metadata(content)

        self.assertNotIn("title:", cleaned)
        self.assertNotIn("url:", cleaned)
        self.assertTrue(cleaned.startswith("这里才是正文第一段。"))

    def test_wechat_content_short_after_cleanup_is_not_usable(self):
        content = "✅ 1、国家统一政策\n\n微信扫一扫关注该公众号\n微信扫一扫可打开此内容，使用完整服务"

        self.assertFalse(is_usable_article_content(content, "https://mp.weixin.qq.com/s/abc"))

    def test_wechat_content_long_body_is_usable(self):
        content = "很多刚开通进出口权限的外贸老板都有同一个疑惑。" * 40

        self.assertTrue(is_usable_article_content(content, "https://mp.weixin.qq.com/s/abc"))

    def test_assess_article_quality_reports_wechat_restricted_tail(self):
        content = "正文" * 120 + "\n微信扫一扫可打开此内容，使用完整服务"

        quality = assess_article_quality(content, "https://mp.weixin.qq.com/s/abc")

        self.assertFalse(quality["usable"])
        self.assertTrue(quality["needs_fallback"])
        self.assertIn("wechat_restricted_tail", quality["reasons"])

    def test_article_success_includes_quality_report(self):
        result = article_success(
            title="标题",
            content="很多刚开通进出口权限的外贸老板都有同一个疑惑。" * 40,
            source_url="https://mp.weixin.qq.com/s/abc",
            extraction_method="beautifulsoup",
        )

        self.assertIn("quality", result)
        self.assertTrue(result["quality"]["usable"])


if __name__ == "__main__":
    unittest.main()
