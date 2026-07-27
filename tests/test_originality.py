import unittest

from pipeline_core.originality import assess_rewrite_originality


class OriginalityTests(unittest.TestCase):
    def test_assess_rewrite_originality_flags_long_copied_passages(self):
        source = (
            "跨境卖家在准备出口退税资料时，应核对发票、报关单、物流凭证和收汇资料之间的一致性，"
            "避免因为上游供应商异常导致退税流程卡住。企业还需要建立供应商准入和单证复核机制。"
        )
        output = (
            "跨境卖家在准备出口退税资料时，应核对发票、报关单、物流凭证和收汇资料之间的一致性，"
            "避免因为上游供应商异常导致退税流程卡住。"
        )

        report = assess_rewrite_originality(output, source)

        self.assertFalse(report["acceptable"])
        self.assertGreaterEqual(report["max_copied_run"], 40)
        self.assertTrue(report["copied_passages"])

    def test_assess_rewrite_originality_allows_restructured_copy_with_shared_terms(self):
        source = "原文提到退税周期可能延长到3-6个月，企业需要关注供应商合规和单证一致性。"
        output = "如果退税周期拉长到3-6个月，卖家要把供应商合规和单证一致性前置到采购环节。"

        report = assess_rewrite_originality(output, source)

        self.assertTrue(report["acceptable"])
        self.assertLess(report["max_copied_run"], 24)

    def test_assess_rewrite_originality_rejects_34_character_copied_run(self):
        source = "上游供应商一个异常即可导致整单业务被视同内销，直接承受13%增值税成本。"
        output = "分析结论是：上游供应商一个异常即可导致整单业务被视同内销，直接承受13%增值税成本。"

        report = assess_rewrite_originality(output, source)

        self.assertFalse(report["acceptable"])

    def test_assess_rewrite_originality_allows_exact_policy_titles_and_fact_tokens(self):
        source = "国家税务总局2026年第5号公告《出口业务增值税和消费税退（免）税管理办法》已于2026年1月1日起施行。"
        output = "国家税务总局2026年第5号公告《出口业务增值税和消费税退（免）税管理办法》已于2026年1月1日起施行。企业应关注第五十三条。"

        report = assess_rewrite_originality(output, source)

        self.assertTrue(report["acceptable"])
