import json
import tempfile
import unittest
from pathlib import Path

from jobpilot import formmodel, plan, profile, sitecards, values
from jobpilot.execute import FakeBackend, run_plan

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "element-ui.form.json"


def make_plan(vals=None):
    form = formmodel.normalize(json.loads(FIX.read_text(encoding="utf-8")))
    vals = vals or profile._seed_values(profile.DEMO_PROFILE)
    return plan.compile_plan(form, vals, sitecards.load("_generic")), vals


class ExecuteTest(unittest.TestCase):
    def test_fills_all(self):
        p, vals = make_plan()
        backend = FakeBackend()
        result = run_plan(p, vals, backend)
        self.assertTrue(result["ok"], result["failed"])
        self.assertEqual(result["done"], 11)
        self.assertEqual(len(backend.page), 11)

    def test_dry_run_does_not_save(self):
        p, vals = make_plan()
        p = plan.compile_plan(formmodel.normalize(json.loads(FIX.read_text(encoding="utf-8"))),
                              vals, sitecards.load("_generic"), save=True)
        backend = FakeBackend()
        run_plan(p, vals, backend, dry_run=True)
        self.assertFalse(any(item["op"] == "save_draft" for item in backend.log))

    def test_save_action_with_null_expect(self):
        p, vals = make_plan()
        p = plan.compile_plan(formmodel.normalize(json.loads(FIX.read_text(encoding="utf-8"))),
                              vals, sitecards.load("_generic"), save=True)
        backend = FakeBackend()
        result = run_plan(p, vals, backend, dry_run=False)
        self.assertTrue(result["ok"], result["failed"])
        self.assertEqual(result["filled"], 11)
        self.assertTrue(any(item["op"] == "save_draft" for item in backend.log))

    def test_stale_plan_stops(self):
        p, vals = make_plan()
        values.set_value(vals, "person.name", "李四")
        result = run_plan(p, vals, FakeBackend())
        self.assertFalse(result["ok"])
        self.assertEqual(result["failed"][0]["code"], "stale_plan")
        self.assertIn("旧", result["failed"][0]["message"])

    def test_fail_fast_and_resume(self):
        p, vals = make_plan()
        first_aid = p["steps"][0]["actions"][4]["aid"]
        state = Path(tempfile.mkdtemp()) / "state.json"
        r1 = run_plan(p, vals, FakeBackend(fail_on={first_aid}), state_path=state)
        self.assertFalse(r1["ok"])
        self.assertEqual(r1["done"], 4)

        backend = FakeBackend()
        r2 = run_plan(p, vals, backend, state_path=state)
        self.assertTrue(r2["ok"], r2["failed"])
        self.assertEqual(r2["done"], 11)
        # 已经完成的 4 个不会重复操作
        self.assertEqual(len(backend.log), 7)

    def test_failure_carries_gap(self):
        p, vals = make_plan()
        aid = p["steps"][0]["actions"][0]["aid"]
        result = run_plan(p, vals, FakeBackend(fail_on={aid}))
        self.assertFalse(result["ok"])
        gap = result["failed"][0]["gap"]
        self.assertTrue(gap["label"])
        self.assertTrue(gap["reason"])

    def test_missing_value_stops(self):
        p, vals = make_plan()
        values.delete_path(vals, "person.name")
        result = run_plan(p, vals, FakeBackend())
        self.assertFalse(result["ok"])
        self.assertEqual(result["failed"][0]["code"], "missing_value")

    def test_bool_string_matches(self):
        from jobpilot import formmodel as _fm
        from jobpilot import sitecards as _sc
        raw = {"url": "x", "module": "基本信息",
               "controls": [{"label": "是否服从调剂", "kind": "bool", "required": True}]}
        vals = profile._seed_values(profile.DEMO_PROFILE)
        values.set_value(vals, "intent.adjust", "是", type_="bool")
        p = plan.compile_plan(_fm.normalize(raw), vals, _sc.load("_generic"))
        result = run_plan(p, vals, FakeBackend())
        self.assertTrue(result["ok"], result["failed"])

    def test_plan_value_must_match_values(self):
        p, vals = make_plan()
        p["steps"][0]["actions"][0]["value"] = "假名字"
        result = run_plan(p, vals, FakeBackend())
        self.assertFalse(result["ok"])
        self.assertEqual(result["failed"][0]["code"], "stale_plan")
        self.assertIn("旧", result["failed"][0]["message"])


if __name__ == "__main__":
    unittest.main()
