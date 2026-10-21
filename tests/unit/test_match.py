import unittest

from jobpilot import schema
from jobpilot.match import match_control


class MatchTest(unittest.TestCase):
    def setUp(self):
        self.idx = schema.alias_index()

    def m(self, label, module="基本信息"):
        return match_control({"label": label, "kind": "text", "module": module}, None, self.idx)

    def test_exact(self):
        self.assertEqual(self.m("姓名")["canonical"], "person.name")
        self.assertGreaterEqual(self.m("姓名")["confidence"], 0.8)

    def test_alias_with_prefix(self):
        self.assertEqual(self.m("请输入姓名")["canonical"], "person.name")

    def test_degree(self):
        self.assertEqual(self.m("最高学历")["canonical"], "education.level")

    def test_long_alias_not_confused(self):
        self.assertEqual(self.m("最高学历")["canonical"], "education.level")

    def test_family_context_wins(self):
        r = match_control({"label": "姓名", "kind": "text", "module": "家庭主要成员"}, None, self.idx)
        self.assertEqual(r["canonical"], "family.name")

    def test_unknown(self):
        self.assertIsNone(self.m("火星文栏目")["canonical"])

    def test_sitecard_override(self):
        card = {"fields": {"自定义栏": "person.height"}}
        r = match_control({"label": "自定义栏", "kind": "text", "module": "基本信息"}, card, self.idx)
        self.assertEqual(r["canonical"], "person.height")
        self.assertEqual(r["confidence"], 0.99)


if __name__ == "__main__":
    unittest.main()
