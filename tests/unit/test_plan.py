import json
import unittest
from pathlib import Path

from jobpilot import formmodel, plan, profile, sitecards, values

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "element-ui.form.json"


def build(vals=None, card="_generic", form=None, **kw):
    raw = json.loads(FIX.read_text(encoding="utf-8")) if form is None else form
    form = formmodel.normalize(raw)
    vals = vals or profile._seed_values(profile.DEMO_PROFILE)
    return plan.compile_plan(form, vals, sitecards.load(card), **kw)


class PlanTest(unittest.TestCase):
    def test_counts(self):
        p = build()
        self.assertEqual(p["stats"]["actions"], 11)
        self.assertEqual(p["stats"]["unmapped"], 2)
        self.assertEqual(p["guards"]["submit"], "blocked")
        self.assertEqual(p["dom_fingerprint"], build()["dom_fingerprint"])

    def test_every_action_has_source(self):
        p = build()
        for step in p["steps"]:
            for a in step["actions"]:
                self.assertTrue(a.get("value_ref"), a)
                self.assertTrue(a.get("target", {}).get("cid"))

    def test_select_uses_option(self):
        p = build()
        acts = [a for s in p["steps"] for a in s["actions"]]
        degree = [a for a in acts if a["target"]["label"] == "最高学历"][0]
        self.assertEqual(degree["op"], "select")
        self.assertEqual(degree["value"], "硕士")
        self.assertEqual(degree["match"], "exact")

    def test_missing_required_goes_to_unmapped(self):
        p = build()
        labels = [u["label"] for u in p["unmapped"]]
        self.assertIn("身高（cm）", labels)
        self.assertIn("是否服从调剂", labels)

    def test_blocking_lists_required_gaps(self):
        p = build()
        self.assertEqual(len(p["blocking"]), 2)
        self.assertEqual({b["label"] for b in p["blocking"]}, {"身高（cm）", "是否服从调剂"})
        self.assertTrue(all(b["reason"] for b in p["blocking"]))
        self.assertEqual(p["optional_missing"], [])

    def test_optional_missing_is_not_blocking(self):
        raw = json.loads(FIX.read_text(encoding="utf-8"))
        raw["controls"] = [{"label": "爱好", "kind": "text", "required": False}]
        p = build(form=raw)
        self.assertEqual(p["blocking"], [])
        self.assertEqual(len(p["optional_missing"]), 1)

    def test_long_value_uses_short_alias(self):
        vals = profile._seed_values(profile.DEMO_PROFILE)
        values.set_value(vals, "education.0.school", "这是一个特别特别特别特别特别长的学校名字用来测试")
        entry = values.get_entry(vals, "education.0.school")
        entry["aliases"] = ["短名"]
        p = build(vals=vals)
        acts = [a for s in p["steps"] for a in s["actions"]]
        school = [a for a in acts if a["target"]["label"] == "学校名称"][0]
        self.assertEqual(school["value"], "短名")
        self.assertTrue(any("短名" in w for w in p["warnings"]))

    def test_no_option_goes_to_unmapped(self):
        vals = profile._seed_values(profile.DEMO_PROFILE)
        values.set_value(vals, "education.0.level", "大专")
        p = build(vals=vals)
        labels = [u["label"] for u in p["unmapped"]]
        self.assertIn("最高学历", labels)

    def test_hash_stable(self):
        self.assertEqual(plan.plan_hash(build()), plan.plan_hash(build()))

    def test_golden_hash(self):
        expected = (Path(__file__).resolve().parent.parent / "golden" / "element-ui.plan.sha")
        self.assertEqual(plan.plan_hash(build()), expected.read_text().strip())

    def test_hash_ignores_run_id(self):
        a = build()
        b = build(run_id="another")
        self.assertEqual(plan.plan_hash(a), plan.plan_hash(b))

    def test_save_action_only_when_asked(self):
        p = build(save=True)
        ops = [a["op"] for s in p["steps"] for a in s["actions"]]
        self.assertIn("save_draft", ops)
        self.assertNotIn("submit", ops)

    def test_bool_with_options_becomes_select(self):
        raw = json.loads(FIX.read_text(encoding="utf-8"))
        raw["controls"] = [{"label": "是否服从调剂", "kind": "bool", "required": True,
                            "options": ["是", "否"]}]
        vals = profile._seed_values(profile.DEMO_PROFILE)
        values.set_value(vals, "intent.adjust", "是", type_="bool")
        p = build(vals=vals, form=raw)
        act = p["steps"][0]["actions"][0]
        self.assertEqual(act["op"], "select")
        self.assertEqual(act["value"], "是")

    def test_explain_is_readable(self):
        lines = plan.explain(build())
        self.assertTrue(any("最高学历" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
