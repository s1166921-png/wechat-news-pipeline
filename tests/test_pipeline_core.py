import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from pipeline_core.importing import (
    classify_article_import,
    resolve_wechat_url,
    today_cst_label,
)
from pipeline_core.quality import filter_quality_results, has_keyword_relevance


class ImportingModuleTests(unittest.TestCase):
    def test_today_cst_label_formats_runtime_date(self):
        cst = timezone(timedelta(hours=8))
        now = datetime(2026, 7, 23, 9, 15, tzinfo=cst)

        self.assertEqual(today_cst_label(now=now), "2026年7月23日")

    def test_resolve_wechat_url_returns_direct_mp_url(self):
        url = "https://mp.weixin.qq.com/s/direct"

        self.assertEqual(resolve_wechat_url(url), url)

    def test_resolve_wechat_url_follows_sogou_redirect(self):
        sogou = "https://weixin.sogou.com/link?url=token&type=2"
        final = "https://mp.weixin.qq.com/s/final"

        with patch("pipeline_core.importing.urlopen_final_url", return_value=final):
            self.assertEqual(resolve_wechat_url(sogou), final)

    def test_classify_article_import_prefers_raw_content(self):
        info = classify_article_import("https://mp.weixin.qq.com/s/abc", "正文" * 80)

        self.assertEqual(info["mode"], "raw_content")
        self.assertEqual(info["recommendation"], "rewrite_directly")


class QualityModuleTests(unittest.TestCase):
    def test_has_keyword_relevance_ignores_generic_only_match(self):
        item = {
            "title": "诺基亚二季度净销售额增长9%",
            "snippet": "通信设备业务增长",
            "source": "36氪",
        }

        self.assertFalse(has_keyword_relevance(item, "独立站 运营 增长"))

    def test_filter_quality_results_keeps_specific_match(self):
        bad = {
            "title": "诺基亚二季度净销售额增长9%",
            "url": "https://36kr.com/newsflashes/3907773824701575",
            "source": "36氪",
            "snippet": "通信设备业务增长",
        }
        good = {
            "title": "独立站运营增长：AI正在改变出海品牌转化路径",
            "url": "https://36kr.com/p/3907773824701575",
            "source": "36氪",
            "snippet": "跨境电商卖家通过独立站提升复购率",
        }

        self.assertEqual(filter_quality_results([bad, good], keyword="独立站 运营 增长"), [good])


if __name__ == "__main__":
    unittest.main()
