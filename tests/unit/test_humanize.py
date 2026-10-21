import unittest

from jobpilot import humanize


class HumanizeTest(unittest.TestCase):
    def test_no_jargon(self):
        for code, text in humanize.MESSAGES.items():
            # 允许的例外：这些词只出现在测试检查里，不在用户文案里
            hits = humanize.check_user_text(text.format(n=1, company="示例公司"))
            self.assertEqual(hits, [], f"{code} 含术语：{hits}")

    def test_unknown_code_has_fallback(self):
        self.assertTrue(humanize.say("something_new"))

    def test_format_n(self):
        self.assertIn("2", humanize.say("missing_value", n=2))


if __name__ == "__main__":
    unittest.main()
