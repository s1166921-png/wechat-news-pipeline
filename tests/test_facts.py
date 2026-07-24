import unittest

from pipeline_core.facts import (
    extract_fact_tokens,
    find_unsupported_fact_tokens,
)


class FactTokenTests(unittest.TestCase):
    def test_extract_fact_tokens_finds_dates_numbers_and_policy_ids(self):
        text = "国家税务总局2026年第5号公告第五十三条自2026年1月1日起施行，退税周期可能延长到3-6个月，税率13%。"

        tokens = extract_fact_tokens(text)

        self.assertIn("2026年第5号公告", tokens)
        self.assertIn("第五十三条", tokens)
        self.assertIn("2026年1月1日", tokens)
        self.assertIn("3-6个月", tokens)
        self.assertIn("13%", tokens)
        self.assertNotIn("2026年", tokens)
        self.assertNotIn("1月", tokens)
        self.assertNotIn("1日", tokens)

    def test_find_unsupported_fact_tokens_flags_hallucinated_date(self):
        source = "原文只说退税周期可能延长到3-6个月。"
        output = "2026年7月15日，退税新规落地，退税周期可能延长到3-6个月。"

        unsupported = find_unsupported_fact_tokens(output, source)

        self.assertIn("2026年7月15日", unsupported)
        self.assertNotIn("3-6个月", unsupported)

    def test_find_unsupported_fact_tokens_flags_hallucinated_percent(self):
        source = "原文提到供应商异常会影响退税。"
        output = "供应商异常会让企业利润下降37%，这是最大风险。"

        unsupported = find_unsupported_fact_tokens(output, source)

        self.assertIn("37%", unsupported)
