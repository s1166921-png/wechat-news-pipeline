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

    def test_large_api_payload_returns_json_413(self):
        client = app.app.test_client()
        old_limit = app.app.config.get("MAX_CONTENT_LENGTH")
        app.app.config["MAX_CONTENT_LENGTH"] = 1024
        try:
            response = client.post("/api/to-wechat-html", json={
                "content": "过大的正文" * 500,
            })
        finally:
            app.app.config["MAX_CONTENT_LENGTH"] = old_limit

        self.assertEqual(response.status_code, 413)
        self.assertIn("请求内容过大", response.get_json()["error"])


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

    def test_select_image_sections_samples_across_article(self):
        content = "\n\n".join([
            "第一部分：开头背景说明，介绍为什么这件事值得关注，避免只看标题。",
            "第二部分：政策或事件本身的核心信息，说明主要变化和直接对象。",
            "第三部分：企业经营影响，讨论成本、流程、审核和组织协同。",
            "第四部分：风险拆解，分别说明供应商、资金流和单证资料的问题。",
            "第五部分：行动建议，给出检查清单、负责人和时间安排。",
            "第六部分：结尾复盘，提示后续跟踪事项和下一步观察重点。",
        ])

        sections = app._select_image_sections(content, count=3)

        self.assertEqual(len(sections), 3)
        self.assertTrue("第一部分" in sections[0] or "第二部分" in sections[0])
        self.assertTrue("第三部分" in sections[1] or "第四部分" in sections[1])
        self.assertIn("第五部分", sections[2])

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
            if len(calls) in (2, 3):
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

    def test_generate_image_retries_failed_slot_with_safe_prompt(self):
        client = app.app.test_client()
        calls = []

        def fake_image(prompt, size="body", n=1):
            calls.append(prompt)
            if len(calls) == 1:
                return []
            return ["https://example.com/safe.png"]

        with patch("app._generate_ark_image", side_effect=fake_image), \
             patch("app._download_image", return_value=False):
            response = client.post("/api/generate-image", json={
                "custom_prompts": [{
                    "prompt": "可能触发审核的详细 Prompt",
                    "section_excerpt": "这是第一段正文对应内容",
                    "index": 0,
                }],
                "count": 1,
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["images"][0]["status"], "ok")
        self.assertEqual(data["images"][0]["retry_used"], True)
        self.assertEqual(data["images"][0]["section_excerpt"], "这是第一段正文对应内容")
        self.assertEqual(data["images"][0]["index"], 0)
        self.assertIn("企业合规流程场景插画", data["images"][0]["prompt"])
        self.assertIn("无文字无数字", data["images"][0]["prompt"])

    def test_custom_prompt_string_remains_backward_compatible(self):
        client = app.app.test_client()

        with patch("app._generate_ark_image", return_value=["https://example.com/custom.png"]), \
             patch("app._download_image", return_value=False):
            response = client.post("/api/generate-image", json={
                "custom_prompts": ["自定义配图 Prompt"],
                "count": 1,
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["images"][0]["status"], "ok")
        self.assertEqual(data["images"][0]["section_excerpt"], "自定义配图 Prompt")


class GenerateArticleFactGuardTests(unittest.TestCase):
    def test_generate_article_removes_unsupported_fact_tokens(self):
        client = app.app.test_client()
        generated = (
            "# 标题\n\n"
            "2026年8月1日，美客多面向墨西哥、巴西、智利、阿根廷四国开放海外仓本土卖家服务。\n\n"
            "据行业估算，申诉周期可从7-15个工作日压缩到3-5个工作日，合规成本约占8%-12%。\n\n"
            "卖家需要关注账号健康度和库存绩效。"
        )

        with patch("app._fetch_general_article", return_value=("", "https://example.com/news")), \
             patch("app.llm_chat_text", return_value=generated):
            response = client.post("/api/generate-article", json={
                "news_item": {
                    "title": "美客多四国海外仓服务开放",
                    "url": "https://example.com/news",
                    "source": "亿邦动力",
                    "date": "2026-08-01",
                    "snippet": "美客多宣布自2026年8月1日起，面向墨西哥、巴西、智利、阿根廷四国开放海外仓本土卖家服务。",
                },
                "style": "b2b",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertIn("2026年8月1日", data["content"])
        self.assertNotIn("7-15个工作日", data["content"])
        self.assertNotIn("3-5个工作日", data["content"])
        self.assertNotIn("8%-12%", data["content"])
        self.assertTrue(data["fact_guard_applied"])
        self.assertIn("3-5个工作日", data["fact_warnings_initial"])
        self.assertIn("8%-12%", data["fact_warnings_initial"])

    def test_article_prompt_bans_industry_estimate_fillers(self):
        prompt = app._build_article_prompt({
            "title": "测试新闻",
            "snippet": "原文只提到平台开放新服务。",
            "source": "测试来源",
        }, style="b2b")

        self.assertIn("不要使用\"据行业估算\"", prompt)
        self.assertIn("不要为了满足标题、开头、表格或数据密度要求而新增来源中没有的数字", prompt)

    def test_fact_guard_does_not_trust_ai_topic_suggestions(self):
        source = app._build_fact_guard_source({
            "title": "美客多海外仓服务开放",
            "snippet": "原文只提到美客多开放海外仓服务。",
            "suggested_topic": "48小时送达背后的海外仓机会",
            "article_summary": "AI摘要声称48小时送达。",
        })
        output = "# 标题\n\n美客多海外仓48小时送达带来新机会。"

        warnings = app._core_facts.find_unsupported_fact_tokens(output, source)

        self.assertIn("48小时", warnings)


class WechatHtmlTemplateTests(unittest.TestCase):
    def test_part_heading_uses_fixed_wechat_template(self):
        html = app._markdown_to_wechat_html(
            "# 标题\n\n## PART 1 — 2R是什么\n\n正文内容",
            title="标题",
            accent_color="#ff8a45",
        )

        self.assertIn("PART 1", html)
        self.assertIn("2R是什么", html)
        self.assertIn("linear-gradient", html)
        self.assertIn("max-width:320px", html)


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


class SearchFreshnessRankingTests(unittest.TestCase):
    def test_multi_engine_can_call_baidu_and_zhihu_sources(self):
        with patch("app._search_baidu", return_value=[{
            "title": "warehouse trend baidu fresh article",
            "url": "https://example.com/baidu",
            "source": "Baidu",
            "date": "",
            "source_type": "baidu",
            "snippet": "warehouse trend",
        }]), patch("app._search_zhihu", return_value=[{
            "title": "warehouse trend zhihu analysis",
            "url": "https://www.zhihu.com/question/1",
            "source": "Zhihu",
            "date": "",
            "source_type": "zhihu",
            "snippet": "warehouse trend",
        }]):
            results = app._search_multi_engine("warehouse trend", max_per_source=1, engines=["baidu", "zhihu"])

        source_types = {r["source_type"] for r in results}
        self.assertIn("baidu", source_types)
        self.assertIn("zhihu", source_types)

    def test_api_search_respects_selected_engines_from_ui(self):
        client = app.app.test_client()
        calls = []

        def fake_search(query, max_per_source=5, engines=None):
            calls.append((query, engines))
            return [{
                "title": "warehouse trend selected baidu result",
                "url": "https://example.com/selected",
                "source": "Baidu",
                "date": "2026-08-01",
                "source_type": "baidu",
                "snippet": "warehouse trend selected result",
            }]

        with patch("app._build_search_queries", return_value=[
            ("warehouse trend", None),
            ("warehouse trend news", ["google_news"]),
        ]), patch("app._search_multi_engine", side_effect=fake_search), \
             patch("app._enrich_news_with_topics", side_effect=lambda results, limit: results[:limit]), \
             patch("random.randint", return_value=0):
            response = client.post("/api/search", json={
                "keyword": "warehouse trend",
                "max_results": 5,
                "engines": ["baidu"],
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, [("warehouse trend", ["baidu"])])

    def test_frontend_exposes_baidu_zhihu_and_wechat_sources(self):
        with open("frontend/index.html", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('data-engine="baidu"', html)
        self.assertIn('data-engine="zhihu"', html)
        self.assertIn('data-engine="wechat"', html)

    def test_trend_keyword_expands_to_recent_entity_queries(self):
        queries = app._build_search_queries("海外仓 趋势")
        query_texts = [q for q, _ in queries]

        self.assertIn("海外仓 最新", query_texts)
        self.assertIn("海外仓 动态", query_texts)
        self.assertIn("海外仓 2026", query_texts)

    def test_quality_filter_removes_baidu_seo_aggregation_pages(self):
        results = [
            {
                "title": "海外仓趋势 _海外网红营销_跨境电商出口海外仓-雨果跨境",
                "url": "https://www.cifnews.com/tags/1",
                "source": "雨果跨境",
                "source_type": "baidu",
                "snippet": "海外仓 趋势",
            },
            {
                "title": "利好本土店！美客多拉美四国海外仓本土卖家服务全面开放",
                "url": "https://www.ebrun.com/20260801.html",
                "source": "亿邦动力",
                "source_type": "ebrun",
                "snippet": "海外仓 服务开放",
            },
        ]

        filtered = app._filter_quality_results(results, keyword="海外仓 趋势")

        self.assertEqual([r["title"] for r in filtered], [results[1]["title"]])
    def test_tax_delay_keyword_expands_to_business_queries(self):
        queries = app._build_search_queries("出口退税慢")
        query_texts = [q for q, _ in queries]

        self.assertEqual(query_texts[0], "出口退税慢")
        self.assertIn("出口退税 办理", query_texts[:3])
        self.assertIn("出口退税 申报", query_texts[:3])

    def test_recent_articles_outrank_old_keyword_matches(self):
        client = app.app.test_client()
        mocked_results = [
            {
                "title": "2021海外仓趋势深度报告：海外仓增长路径复盘",
                "url": "https://old.example.com/2021",
                "source": "行业报告",
                "date": "2021-09-01",
                "snippet": "海外仓 趋势 海外仓 趋势 海外仓 趋势",
                "source_type": "bing",
            },
            {
                "title": "海外仓趋势更新：拉美平台调整卖家履约策略",
                "url": "https://news.example.com/2026",
                "source": "跨境新闻",
                "date": "2026-08-01",
                "snippet": "海外仓趋势正在影响跨境卖家的备货和发货安排。",
                "source_type": "360search",
            },
            {
                "title": "2023海外仓趋势观察",
                "url": "https://old.example.com/2023",
                "source": "行业报告",
                "date": "2023-06-01",
                "snippet": "海外仓趋势旧资料。",
                "source_type": "bing",
            },
            {
                "title": "海外仓服务商发布旺季备货提醒",
                "url": "https://news2.example.com/2026",
                "source": "行业新闻",
                "date": "2026-07-28",
                "snippet": "海外仓卖家需要关注旺季库存。",
                "source_type": "sogou_news",
            },
            {
                "title": "2020海外仓趋势白皮书",
                "url": "https://old.example.com/2020",
                "source": "白皮书",
                "date": "2020-01-01",
                "snippet": "海外仓 趋势",
                "source_type": "bing",
            },
            {
                "title": "海外仓政策动态",
                "url": "https://news3.example.com/2026",
                "source": "行业新闻",
                "date": "2026-07-20",
                "snippet": "海外仓相关政策动态。",
                "source_type": "360search",
            },
        ]

        with patch("app._build_search_queries", return_value=[("海外仓 趋势", ["360search"])]), \
             patch("app._search_multi_engine", return_value=mocked_results), \
             patch("app._enrich_news_with_topics", side_effect=lambda results, limit: list(reversed(results[:limit]))), \
             patch("random.randint", return_value=0):
            response = client.post("/api/search", json={
                "keyword": "海外仓 趋势",
                "max_results": 6,
                "engines": ["360search"],
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        titles = [r["title"] for r in data["results"]]
        self.assertIn("海外仓趋势更新：拉美平台调整卖家履约策略", titles[:2])
        self.assertNotIn("2021海外仓趋势深度报告：海外仓增长路径复盘", titles[:2])
        self.assertEqual(data["results"][0]["freshness_label"], "近7天")

    def test_parse_search_age_days_reads_chinese_and_absolute_dates(self):
        now = datetime(2026, 8, 3, 12, 0, tzinfo=app.CST)

        self.assertLess(app._parse_search_age_days("2026-08-01", now=now), 3)
        self.assertLess(app._parse_search_age_days("8月1日", now=now), 3)
        self.assertGreater(app._parse_search_age_days("2021-09-01", now=now), 1000)
        self.assertGreater(app._parse_search_age_days("2026-11-01", now=now), 1000)

    def test_internal_wechat_links_are_rescored_after_discovery(self):
        client = app.app.test_client()
        base_results = [
            {
                "title": "warehouse trend entry article",
                "url": "https://mp.weixin.qq.com/s/base",
                "source": "公众号",
                "date": "2026-07-01",
                "snippet": "warehouse trend entry.",
                "source_type": "wechat",
            },
            {
                "title": "warehouse trend evergreen unknown-date explainer",
                "url": "https://old.example.com/unknown",
                "source": "亿邦动力",
                "date": "",
                "snippet": "warehouse trend older reference.",
                "source_type": "ebrun",
            },
        ]
        internal = [{
            "title": "warehouse trend weekly update recent service change",
            "url": "https://mp.weixin.qq.com/s/recent",
            "source": "公众号",
            "date": "2026-08-01",
            "snippet": "warehouse trend recent update.",
            "source_type": "wechat",
        }]

        with patch("app._build_search_queries", return_value=[("warehouse trend", ["wechat"])]), \
             patch("app._search_multi_engine", return_value=base_results), \
             patch("app._extract_internal_links", return_value=internal), \
             patch("app._enrich_news_with_topics", side_effect=lambda results, limit: results[:limit]), \
             patch("random.randint", return_value=0):
            response = client.post("/api/search", json={
                "keyword": "warehouse trend",
                "max_results": 5,
                "engines": ["wechat"],
            })

        data = response.get_json()
        titles = [r["title"] for r in data["results"]]
        self.assertLess(
            titles.index("warehouse trend weekly update recent service change"),
            titles.index("warehouse trend evergreen unknown-date explainer"),
        )
        recent = next(r for r in data["results"] if r["url"].endswith("/recent"))
        self.assertEqual(recent["freshness_label"], "近7天")


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

    def test_wechat_html_places_body_images_after_matching_sections(self):
        html = app._markdown_to_wechat_html(
            "# 标题\n\n"
            "开头摘要，说明整体背景。\n\n"
            "供应商异常会导致退税申报进入函调流程，企业要提前核验资质。\n\n"
            "资金周转会受到影响，财务团队需要准备现金流预案。\n\n"
            "合同、发票、物流和付款记录需要保持一致。",
            images={
                "0": {
                    "url": "/api/generated-image?file=supplier.png",
                    "section_excerpt": "供应商异常会导致退税申报进入函调流程",
                },
                "1": {
                    "url": "/api/generated-image?file=cashflow.png",
                    "section_excerpt": "资金周转会受到影响，财务团队需要准备现金流预案",
                },
            },
        )

        supplier_text_pos = html.index("供应商异常会导致退税申报进入函调流程")
        supplier_img_pos = html.index("supplier.png")
        cashflow_text_pos = html.index("资金周转会受到影响")
        cashflow_img_pos = html.index("cashflow.png")
        records_text_pos = html.index("合同、发票、物流")

        self.assertGreater(supplier_img_pos, supplier_text_pos)
        self.assertLess(supplier_img_pos, cashflow_text_pos)
        self.assertGreater(cashflow_img_pos, cashflow_text_pos)
        self.assertLess(cashflow_img_pos, records_text_pos)

    def test_wechat_html_fallback_distributes_unmatched_body_images(self):
        html = app._markdown_to_wechat_html(
            "# 标题\n\n"
            "第一段：开头背景。\n\n"
            "第二段：基础信息。\n\n"
            "第三段：业务影响。\n\n"
            "第四段：风险拆解。\n\n"
            "第五段：行动建议。\n\n"
            "第六段：结尾复盘。",
            images={
                "0": "/api/generated-image?file=body-a.png",
                "1": "/api/generated-image?file=body-b.png",
                "2": "/api/generated-image?file=body-c.png",
            },
        )

        self.assertGreater(html.index("body-a.png"), html.index("第二段"))
        self.assertGreater(html.index("body-b.png"), html.index("第三段"))
        self.assertGreater(html.index("body-c.png"), html.index("第五段"))

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
