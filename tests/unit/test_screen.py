import json
import unittest
from pathlib import Path

from jobpilot import screen

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "candidates.json"
PROFILE = {"degree": "硕士", "grad_date": "2026-11", "major": "金融科技",
           "cities": ["杭州", "上海"], "salary_min": 20, "english": "CET6"}


class ScreenTest(unittest.TestCase):
    def setUp(self):
        self.candidates = json.loads(FIX.read_text(encoding="utf-8"))

    def test_tiers(self):
        results = screen.evaluate_many(self.candidates, PROFILE)
        tiers = {r["company"]: r["tier"] for r in results}
        self.assertEqual(tiers["示例银行"], "推荐投")
        self.assertEqual(tiers["示例券商"], "不投")
        self.assertIn(tiers["示例消金"], ("备选", "不投"))

    def test_unknown_salary_is_backup(self):
        c = {"company": "甲", "position": "风控", "degree": "硕士", "major_req": ["金融科技"]}
        r = screen.evaluate(c, PROFILE)
        self.assertEqual(r["tier"], "备选")
        self.assertIn("薪资", "、".join(r["unknown"]))

    def test_major_mismatch_not_recommended(self):
        c = {"company": "甲", "position": "统计岗", "degree": "硕士", "major_req": ["统计学"],
             "salary_low": 30, "salary_high": 40, "salary_sources": 2}
        r = screen.evaluate(c, PROFILE)
        self.assertEqual(r["tier"], "备选")

    def test_never_vague(self):
        results = screen.evaluate_many(self.candidates, PROFILE)
        for r in results:
            self.assertIn(r["tier"], screen.TIERS)

    def test_string_numbers_are_tolerated(self):
        c = {"company": "甲", "position": "岗", "degree": "硕士", "major_req": ["金融科技"],
             "salary_low": "30", "salary_high": "40", "salary_sources": 2}
        r = screen.evaluate(c, PROFILE)
        self.assertEqual(r["tier"], "推荐投")

    def test_exclude_list_is_hard_fail(self):
        c = {"company": "某外包公司", "position": "风控", "degree": "硕士",
             "major_req": ["金融科技"], "salary_low": 30, "salary_high": 40,
             "salary_sources": 2}
        r = screen.evaluate(c, {**PROFILE, "exclude": ["外包"]})
        self.assertEqual(r["tier"], "不投")
        self.assertTrue(any("排除" in f for f in r["fails"]))

    def test_degree_fail(self):
        c = {"company": "甲", "position": "岗", "degree": "博士", "major_req": ["金融科技"],
             "salary_low": 30, "salary_high": 40, "salary_sources": 2}
        r = screen.evaluate(c, PROFILE)
        self.assertEqual(r["tier"], "不投")
        self.assertTrue(any("博士" in f for f in r["fails"]))


if __name__ == "__main__":
    unittest.main()
