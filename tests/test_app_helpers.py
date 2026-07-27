import unittest
import subprocess
import sys
from zipfile import ZipFile
from base64 import b64decode
from io import BytesIO
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


class ImageGenerationTests(unittest.TestCase):
    def test_select_image_sections_returns_requested_count_from_short_blocks(self):
        content = "\n\n".join([
            "# 标题",
            "## 一、背景",
            "短段落。",
            "| 类型 | 风险 |",
            "| --- | --- |",
            "| A | 高 |",
            "企业需要检查供应商资质、合同条款、发票流向和物流单证，避免退税链路被异常上游拖累。",
            "结尾建议建立月度复盘清单。",
        ])

        sections = app._select_image_sections(content, count=3)

        self.assertEqual(len(sections), 3)
        self.assertTrue(all(section.strip() for section in sections))
        self.assertEqual(len(set(sections)), 3)

    def test_generate_image_keeps_failed_slot_visible(self):
        client = app.app.test_client()
        article = "\n\n".join([
            "第一段正文说明供应商异常会影响退税申报，需要企业在交易前核验基础资料。",
            "第二段正文说明函调流程会拉长资金周转周期，财务团队要准备现金流预案。",
            "第三段正文说明合同、发票、物流和付款记录需要保持一致，方便后续核查。",
        ])
        calls = []

        def fake_image(prompt, size="body", n=1):
            calls.append(prompt)
            if len(calls) == 2:
                return []
            return ["https://example.com/image-%d.png" % len(calls)]

        with patch("app._build_image_prompt", side_effect=lambda text, image_type="body": "prompt:" + text[:8]), \
             patch("app._generate_ark_image", side_effect=fake_image), \
             patch("app._download_image", return_value=False):
            response = client.post("/api/generate-image", json={
                "article_content": article,
                "count": 3,
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["images"]), 3)
        self.assertEqual(data["images"][1]["status"], "failed")
        self.assertIn("未返回图片", data["images"][1]["error"])
        self.assertEqual(data["images"][0]["status"], "ok")
        self.assertEqual(data["images"][2]["status"], "ok")


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
        self.assertIn("2026年7月15日", data["fact_warnings_initial"])
        self.assertIn("37%", data["fact_warnings_initial"])
        self.assertEqual([], data["fact_warnings"])
        self.assertNotIn("2026年7月15日", data["rewritten_markdown"])
        self.assertNotIn("37%", data["rewritten_markdown"])

    def test_rewrite_fact_guard_can_retry_twice_until_clean(self):
        client = app.app.test_client()
        calls = []

        def fake_llm(**kwargs):
            calls.append(kwargs["user"])
            if len(calls) == 1:
                return "# 标题\n\n原文提到退税周期为3-6个月，新增利润下降37%。"
            if len(calls) == 2:
                return "# 标题\n\n原文提到退税周期为3-6个月，建议关注2个风险。"
            return "# 标题\n\n原文提到退税周期为3-6个月，建议关注供应商合规。"

        with patch("app.llm_chat_text", side_effect=fake_llm):
            response = client.post("/api/rewrite", json={
                "raw_content": "原文只提到退税周期为3-6个月，企业需要关注供应商合规。" * 30,
                "style": "b2b",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["fact_guard_retry_count"], 2)
        self.assertIn("37%", data["fact_warnings_initial"])
        self.assertEqual([], data["fact_warnings"])
        self.assertNotIn("2个", data["rewritten_markdown"])

    def test_rewrite_neutralizes_soft_claims_that_remain_after_retries(self):
        client = app.app.test_client()

        def fake_llm(**kwargs):
            return "# 标题\n\n核心原因并非系统故障，而是供应商合规异常直接冲击现金流。"

        with patch("app.llm_chat_text", side_effect=fake_llm):
            response = client.post("/api/rewrite", json={
                "raw_content": "原文提到退税周期可能延长到3-6个月，企业需要关注供应商合规。" * 30,
                "style": "b2b",
                "rewrite_mode": "recompose",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(2, data["fact_guard_retry_count"])
        self.assertEqual([], data["soft_claim_warnings"])
        self.assertNotIn("核心原因", data["rewritten_markdown"])
        self.assertNotIn("直接冲击", data["rewritten_markdown"])

    def test_rewrite_removes_hard_fact_sentences_that_remain_after_retries(self):
        client = app.app.test_client()

        def fake_llm(**kwargs):
            return "# 标题\n\n原文提到视同内销会按13%增值税处理。以单笔出口额100万元、毛利率15%的订单为例，补税13万元。"

        with patch("app.llm_chat_text", side_effect=fake_llm):
            response = client.post("/api/rewrite", json={
                "raw_content": "原文提到视同内销会按13%增值税处理。" * 30,
                "style": "b2b",
                "rewrite_mode": "recompose",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual([], data["fact_warnings"])
        self.assertIn("13%增值税", data["rewritten_markdown"])
        self.assertNotIn("100万元", data["rewritten_markdown"])
        self.assertNotIn("15%", data["rewritten_markdown"])
        self.assertNotIn("13万元", data["rewritten_markdown"])

    def test_rewrite_retries_when_generated_text_has_unsupported_soft_claims(self):
        client = app.app.test_client()
        calls = []

        def fake_llm(**kwargs):
            calls.append(kwargs["user"])
            if len(calls) == 1:
                return "# 标题\n\n税务部门近期发布的说明释放出明确信号，退税周期延长的底层逻辑是监管升级，直接冲击卖家现金流。"
            return "# 标题\n\n原文提到退税周期可能延长到3-6个月，企业需要关注供应商合规。"

        with patch("app.llm_chat_text", side_effect=fake_llm):
            response = client.post("/api/rewrite", json={
                "raw_content": "原文提到退税周期可能延长到3-6个月，企业需要关注供应商合规。" * 30,
                "style": "b2b",
                "rewrite_mode": "recompose",
                "temperature": 0.9,
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["fact_guard_retry_count"], 1)
        self.assertTrue(any("近期发布" in item for item in data["soft_claim_warnings_initial"]))
        self.assertTrue(any("底层逻辑" in item for item in data["soft_claim_warnings_initial"]))
        self.assertEqual([], data["soft_claim_warnings"])
        self.assertIn("未支持判断", calls[1])
        self.assertNotIn("近期发布", data["rewritten_markdown"])

    def test_rewrite_recompose_mode_uses_higher_temperature_and_restructure_prompt(self):
        client = app.app.test_client()
        captured = {}

        def fake_llm(**kwargs):
            captured.update(kwargs)
            return "# 新标题\n\n这是重新编写后的正文。"

        with patch("app.llm_chat_text", side_effect=fake_llm):
            response = client.post("/api/rewrite", json={
                "raw_content": "原文提到退税周期为3-6个月，企业需要关注供应商合规。" * 30,
                "style": "b2b",
                "rewrite_mode": "recompose",
                "temperature": 0.82,
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["temperature"], 0.82)
        self.assertEqual(data["rewrite_mode"], "recompose")
        self.assertEqual(data["rewrite_temperature"], 0.82)
        self.assertIn("重新编写", captured["user"])
        self.assertIn("不要沿用原文段落顺序", captured["user"])
        self.assertIn("不得逐句改写", captured["user"])
        self.assertIn("B2B风格执行清单", captured["user"])
        self.assertIn("行业分析师", captured["user"])

    def test_rewrite_retries_when_output_copies_source_too_much(self):
        client = app.app.test_client()
        source = (
            "跨境卖家在准备出口退税资料时，应核对发票、报关单、物流凭证和收汇资料之间的一致性，"
            "避免因为上游供应商异常导致退税流程卡住。企业还需要建立供应商准入和单证复核机制。"
        ) * 6
        calls = []

        def fake_llm(**kwargs):
            calls.append(kwargs["user"])
            if len(calls) == 1:
                return "# 标题\n\n" + source[:180]
            return "# 标题\n\n如果退税周期和供应商合规挂钩，卖家需要把发票、报关单、物流凭证和收汇资料放到同一张核查表里。"

        with patch("app.llm_chat_text", side_effect=fake_llm):
            response = client.post("/api/rewrite", json={
                "raw_content": source,
                "style": "b2b",
                "rewrite_mode": "recompose",
                "temperature": 0.85,
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["originality_retry_count"], 1)
        self.assertFalse(data["originality_report_initial"]["acceptable"])
        self.assertTrue(data["originality_report"]["acceptable"])
        self.assertIn("照搬率过高", calls[1])
        self.assertNotIn(source[:70], data["rewritten_markdown"])


class FrontendRewriteUiTests(unittest.TestCase):
    def test_rewrite_bar_has_recompose_button_and_temperature_control(self):
        html = (app.FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
        js = (app.FRONTEND_DIR / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="btn-recompose"', html)
        self.assertIn('id="rewrite-temperature"', html)
        self.assertIn("rewrite_mode", js)
        self.assertIn("rewrite_temperature", js)

    def test_rewrite_style_active_button_remains_visible(self):
        css = (app.FRONTEND_DIR / "style.css").read_text(encoding="utf-8")

        self.assertIn(".rewrite-style-btn.active", css)
        self.assertIn("opacity: 1", css)
        self.assertIn("box-shadow", css)


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


class ImageEmbeddingTests(unittest.TestCase):
    def test_wechat_html_embeds_body_image_object_url(self):
        html = app._markdown_to_wechat_html(
            "第一段内容。\n\n第二段内容。\n\n第三段内容。\n\n第四段内容。\n\n第五段内容。",
            images={
                "cover": "/api/generated-image?file=cover.png",
                "0": {
                    "url": "/api/generated-image?file=body.png",
                    "section_excerpt": "第二段内容",
                },
            },
        )

        self.assertIn('src="/api/generated-image?file=cover.png"', html)
        self.assertIn('src="/api/generated-image?file=body.png"', html)
        self.assertNotIn("{'url':", html)

    def test_export_docx_accepts_local_output_image_url(self):
        client = app.app.test_client()
        image_dir = app.OUTPUT_DIR / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "unit_test_docx_image.png"
        image_path.write_bytes(b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
            "/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
        ))

        response = client.post("/api/export-docx", json={
            "title": "测试文档",
            "content": "## 小标题\n\n这是一段用于导出的正文。",
            "images": {
                "cover": "/api/generated-image?file=unit_test_docx_image.png",
                "0": {
                    "url": "/api/generated-image?file=unit_test_docx_image.png",
                    "section_excerpt": "用于导出的正文",
                },
            },
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.mimetype,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertGreater(len(response.data), 1000)
        with ZipFile(BytesIO(response.data)) as docx_zip:
            media_files = [
                name for name in docx_zip.namelist()
                if name.startswith("word/media/")
            ]
        self.assertGreaterEqual(len(media_files), 1)

    def test_export_docx_does_not_hang_on_h1_heading(self):
        script = """
import app
client = app.app.test_client()
response = client.post('/api/export-docx', json={
    'title': 'H1 hang test',
    'content': '# 文章标题\\n\\n正文内容',
    'images': {},
})
raise SystemExit(0 if response.status_code == 200 else 1)
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(app.BASE_DIR),
            timeout=8,
        )

        self.assertEqual(result.returncode, 0)


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
