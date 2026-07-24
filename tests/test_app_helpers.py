import unittest
from datetime import datetime
from unittest.mock import patch

import app


class DatePromptTests(unittest.TestCase):
    def test_today_cst_label_uses_runtime_date(self):
        dt = datetime(2026, 7, 23, 8, 30, 0, tzinfo=app.CST)

        self.assertEqual(app._today_cst_label(now=dt), "2026年7月23日")


class WechatUrlTests(unittest.TestCase):
    def test_resolve_wechat_url_keeps_direct_mp_links(self):
        url = "https://mp.weixin.qq.com/s/abc123"

        self.assertEqual(app._resolve_wechat_url(url), url)

    def test_resolve_wechat_url_follows_sogou_redirect(self):
        sogou = "https://weixin.sogou.com/link?url=token&type=2"
        final = "https://mp.weixin.qq.com/s/final123"

        with patch("app._urlopen_final_url", return_value=final):
            self.assertEqual(app._resolve_wechat_url(sogou), final)


class ArticleImportClassificationTests(unittest.TestCase):
    def test_classify_raw_content_as_manual_import(self):
        result = app._classify_article_import("", "正文" * 80)

        self.assertEqual(result["mode"], "raw_content")
        self.assertEqual(result["recommendation"], "rewrite_directly")

    def test_classify_sogou_wechat_link_as_resolve_first(self):
        result = app._classify_article_import("https://weixin.sogou.com/link?url=token", "")

        self.assertEqual(result["mode"], "wechat_sogou_redirect")
        self.assertEqual(result["recommendation"], "resolve_then_fetch")

    def test_classify_direct_wechat_link_as_fetch_or_paste(self):
        result = app._classify_article_import("https://mp.weixin.qq.com/s/abc", "")

        self.assertEqual(result["mode"], "wechat_direct")
        self.assertEqual(result["recommendation"], "fetch_or_paste")


class QualityFilterTests(unittest.TestCase):
    def test_quality_filter_removes_items_without_keyword_relevance(self):
        results = [
            {
                "title": "诺基亚二季度净销售额增长9%",
                "url": "https://36kr.com/newsflashes/3907773824701575",
                "source": "36氪",
                "snippet": "通信设备业务增长",
            },
            {
                "title": "独立站运营增长：AI正在改变出海品牌转化路径",
                "url": "https://36kr.com/p/3907773824701575",
                "source": "36氪",
                "snippet": "跨境电商卖家通过独立站提升复购率",
            },
        ]

        filtered = app._filter_quality_results(results, keyword="独立站 运营 增长")

        self.assertEqual([r["title"] for r in filtered], [results[1]["title"]])


class RequestLoggingTests(unittest.TestCase):
    def test_request_log_preview_redacts_long_article_fields(self):
        payload = {
            "url": "https://mp.weixin.qq.com/s/abc",
            "raw_content": "这是一段需要保护的公众号全文" * 20,
            "original_title": "测试标题",
        }

        preview = app._request_log_preview(payload)

        self.assertIn('"raw_content": "[redacted chars=', preview)
        self.assertIn('"url": "https://mp.weixin.qq.com/s/abc"', preview)
        self.assertNotIn("需要保护的公众号全文", preview)


class FlaskSmokeTests(unittest.TestCase):
    def test_health_endpoint_returns_ok(self):
        client = app.app.test_client()

        response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")


class RewriteEndpointTests(unittest.TestCase):
    def test_rewrite_raw_content_reports_extraction_metadata(self):
        client = app.app.test_client()

        with patch("app.llm_chat_text", return_value="# 改写标题\n\n这是改写后的正文内容。"):
            response = client.post("/api/rewrite", json={
                "raw_content": "原文内容" * 80,
                "original_title": "原始标题",
                "style": "b2p",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["extraction_method"], "raw_input")
        self.assertEqual(data["source_url"], "")

    def test_rewrite_url_content_reports_resolved_source_url(self):
        client = app.app.test_client()

        with patch("app._fetch_article_content", return_value={
            "ok": True,
            "status": "ok",
            "title": "原始标题",
            "author": "作者",
            "content": "原文内容" * 80,
            "char_count": 320,
            "source_url": "https://mp.weixin.qq.com/s/final",
            "extraction_method": "beautifulsoup",
            "quality": {"usable": True, "needs_fallback": False, "reasons": [], "char_count": 320},
        }), patch("app.llm_chat_text", return_value="# 改写标题\n\n这是改写后的正文内容。"):
            response = client.post("/api/rewrite", json={
                "url": "https://weixin.sogou.com/link?url=token&type=2",
                "style": "b2p",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["extraction_method"], "beautifulsoup")
        self.assertEqual(data["source_url"], "https://mp.weixin.qq.com/s/final")
        self.assertEqual(data["source_quality"]["usable"], True)

    def test_rewrite_prefers_url_when_raw_content_is_too_short(self):
        client = app.app.test_client()

        with patch("app._fetch_article_content", return_value={
            "ok": True,
            "status": "ok",
            "title": "原始标题",
            "author": "作者",
            "content": "完整原文内容" * 80,
            "char_count": 480,
            "source_url": "https://mp.weixin.qq.com/s/final",
            "extraction_method": "beautifulsoup",
            "quality": {"usable": True, "needs_fallback": False, "reasons": [], "char_count": 480},
        }) as fetch_article, patch("app.llm_chat_text", return_value="# 改写标题\n\n这是改写后的正文内容。"):
            response = client.post("/api/rewrite", json={
                "url": "https://mp.weixin.qq.com/s/final",
                "raw_content": "只有四十九个字左右的残留短文本，不应该被当成完整原文。",
                "style": "b2p",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        fetch_article.assert_called_once()
        self.assertEqual(data["original_char_count"], len("完整原文内容" * 80))
        self.assertEqual(data["extraction_method"], "beautifulsoup")

    def test_rewrite_rejects_short_raw_content_without_url(self):
        client = app.app.test_client()

        with patch("app.llm_chat_text") as llm:
            response = client.post("/api/rewrite", json={
                "raw_content": "太短的原文",
                "style": "b2p",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("原文内容太短", data["error"])
        llm.assert_not_called()

    def test_rewrite_prompt_contains_strict_fact_boundary(self):
        client = app.app.test_client()
        captured = {}

        def fake_llm(**kwargs):
            captured["user"] = kwargs["user"]
            return "# 改写标题\n\n这是改写后的正文内容。"

        with patch("app.llm_chat_text", side_effect=fake_llm):
            response = client.post("/api/rewrite", json={
                "raw_content": "这是足够长的原文内容。" * 80,
                "style": "b2p",
            })

        self.assertEqual(response.status_code, 200)
        self.assertIn("不得编造", captured["user"])
        self.assertIn("原文没有的信息", captured["user"])

    def test_rewrite_retries_when_generated_text_has_unsupported_fact_tokens(self):
        client = app.app.test_client()
        calls = []

        def fake_llm(**kwargs):
            calls.append(kwargs["user"])
            if len(calls) == 1:
                return "# 标题\n\n2026年7月15日，企业利润下降37%。原文提到退税周期为3-6个月。"
            return "# 标题\n\n原文提到退税周期为3-6个月，企业需要关注供应商合规。"

        with patch("app.llm_chat_text", side_effect=fake_llm):
            response = client.post("/api/rewrite", json={
                "raw_content": "原文只提到退税周期为3-6个月，企业需要关注供应商合规。" * 30,
                "style": "b2p",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["fact_guard_retry_count"], 1)
        self.assertIn("2026年7月15日", data["fact_warnings"])
        self.assertIn("37%", data["fact_warnings"])
        self.assertNotIn("2026年7月15日", data["rewritten_markdown"])


class VerifyWechatLinksEndpointTests(unittest.TestCase):
    def test_verify_wechat_links_returns_summaries_without_content(self):
        client = app.app.test_client()

        with patch("app._fetch_article_content", return_value={
            "ok": True,
            "status": "ok",
            "title": "原始标题",
            "author": "作者",
            "content": "这段正文不应该出现在响应里",
            "char_count": 320,
            "source_url": "https://mp.weixin.qq.com/s/final",
            "extraction_method": "beautifulsoup",
            "quality": {"usable": True, "needs_fallback": False, "reasons": [], "char_count": 320},
        }):
            response = client.post("/api/verify-wechat-links", json={
                "urls": ["https://mp.weixin.qq.com/s/final"],
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["usable_count"], 1)
        self.assertNotIn("content", data["results"][0])
        self.assertEqual(data["results"][0]["quality"]["usable"], True)


class FetchArticleEndpointTests(unittest.TestCase):
    def test_fetch_article_wechat_failure_returns_structured_manual_import_hint(self):
        client = app.app.test_client()

        with patch("app._fetch_article_content", return_value=None):
            response = client.post("/api/fetch-article", json={
                "url": "https://mp.weixin.qq.com/s/blocked",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(data["status"], "extract_failed")
        self.assertTrue(data["manual_import_recommended"])
        self.assertIn("error_hint", data)


class FetchArticleFunctionTests(unittest.TestCase):
    def test_fetch_article_content_returns_standardized_result_from_trafilatura(self):
        html = "<html><head><title>标题</title></head><body><article><p>正文</p></article></body></html>".encode("utf-8")

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return html

        def fake_extract(*args, **kwargs):
            if kwargs.get("output_format") == "json":
                return '{"title":"标题","author":"作者"}'
            return "---\ntitle: 标题\nurl: https://mp.weixin.qq.com/s/abc\n---\n\n" + ("正文内容" * 180)

        with patch("app.urllib.request.urlopen", return_value=FakeResponse()), \
             patch("trafilatura.extract", side_effect=fake_extract):
            article = app._fetch_article_content("https://mp.weixin.qq.com/s/abc")

        self.assertTrue(article["ok"])
        self.assertEqual(article["status"], "ok")
        self.assertEqual(article["extraction_method"], "trafilatura")
        self.assertNotIn("title:", article["content"])


if __name__ == "__main__":
    unittest.main()
