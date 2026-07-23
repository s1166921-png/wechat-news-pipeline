import unittest

from pipeline_core.extractors import (
    article_failure,
    article_success,
    normalize_article_result,
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


if __name__ == "__main__":
    unittest.main()
