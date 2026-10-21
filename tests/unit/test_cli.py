import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from jobpilot import values as values_mod
from jobpilot.cli import main

ROOT = Path(__file__).resolve().parent.parent.parent


def values_missing(doc):
    return values_mod.missing(doc)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        os.environ["JOBPILOT_HOME"] = self.home

    def run_cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_doctor_json(self):
        code, out = self.run_cli("doctor", "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("python", data)
        self.assertTrue(data["home_writable"])

    def test_init_demo_writes_600(self):
        code, out = self.run_cli("init", "--demo")
        self.assertEqual(code, 0)
        values = Path(self.home) / "values.json"
        self.assertTrue(values.exists())
        mode = stat.S_IMODE(values.stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_init_questions(self):
        code, out = self.run_cli("init", "--questions")
        self.assertEqual(code, 0)
        rounds = json.loads(out)
        self.assertEqual(len(rounds), 4)
        self.assertEqual(sum(len(r) for r in rounds), 12)

    def test_init_answers(self):
        answers = {
            "education.0.level": "硕士", "education.0.school": "示例学院",
            "education.0.major": "统计", "education.0.grad_date": "2027-06",
            "intent.directions": "风险,数据", "intent.cities": "北京,上海",
            "intent.salary_min": "20", "person.english_level": "CET6",
            "flags.fresh_grad": "是", "intent.employer_types": "银行,券商",
            "intent.exclude": "", "intent.available_from": "2027-07",
        }
        path = Path(self.home) / "answers.json"
        path.write_text(json.dumps(answers), encoding="utf-8")
        code, out = self.run_cli("init", "--answers", str(path))
        self.assertEqual(code, 0)
        data = json.loads((Path(self.home) / "values.json").read_text(encoding="utf-8"))
        self.assertEqual(data["education"][0]["level"]["v"], "硕士")
        self.assertEqual(data["intent"]["directions"]["v"], ["风险", "数据"])
        self.assertEqual(data["intent"]["salary_min"]["v"], "20")
        self.assertEqual(data["person"]["english_level"]["v"], "CET6")
        self.assertIs(data["flags"]["fresh_grad"]["v"], True)
        # 首建不问身份信息，等填网申再问
        self.assertNotIn("name", data["person"])
        self.assertNotIn("phone", data.get("contact", {}))
        self.assertEqual(values_missing(data), [])

    def test_demo_end_to_end(self):
        code, out = self.run_cli("demo")
        self.assertEqual(code, 0)
        self.assertIn("演示完成", out)
        self.assertTrue((Path(self.home) / "exports" / "填写稿.md").exists())

    def test_plan_review_sheet(self):
        self.run_cli("demo")
        plan_path = Path(self.home) / "plan.json"
        code, out = self.run_cli("plan", "--form", str(ROOT / "tests/fixtures/element-ui.form.json"),
                                 "--out", str(plan_path))
        self.assertEqual(code, 0)
        self.assertTrue(plan_path.exists())

        code, out = self.run_cli("review", str(plan_path))
        self.assertEqual(code, 0)
        self.assertIn("停在提交前", out)

        code, out = self.run_cli("sheet", str(plan_path), "--out", str(Path(self.home) / "s.md"))
        self.assertEqual(code, 0)
        self.assertIn("姓名", (Path(self.home) / "s.md").read_text(encoding="utf-8"))

    def test_run_fake(self):
        self.run_cli("demo")
        plan_path = Path(self.home) / "plan.json"
        self.run_cli("plan", "--form", str(ROOT / "tests/fixtures/element-ui.form.json"),
                     "--out", str(plan_path))

        # 必填没补齐：拒绝开始，并说清差什么
        code, out = self.run_cli("run", str(plan_path), "--backend", "fake")
        self.assertEqual(code, 2)
        self.assertIn("必填", out)
        self.assertIn("身高", out)

        # 一次补两题，写完再填
        answers = Path(self.home) / "answers.json"
        answers.write_text(json.dumps({"person.height": "180", "intent.adjust": "是"}),
                           encoding="utf-8")
        code, out = self.run_cli("values", "set-many", "--file", str(answers))
        self.assertEqual(code, 0)
        self.assertIn("记下了 2 项", out)

        # 旧计划还是旧的：先提示重新生成
        code, out = self.run_cli("run", str(plan_path), "--backend", "fake")
        self.assertEqual(code, 2)
        self.assertIn("重新生成", out)

        # 重新生成后就能填了
        self.run_cli("plan", "--form", str(ROOT / "tests/fixtures/element-ui.form.json"),
                     "--out", str(plan_path))
        code, out = self.run_cli("run", str(plan_path), "--backend", "fake")
        self.assertEqual(code, 0)
        self.assertIn("停在提交前", out)

    def test_set_many_rejects_bad_value(self):
        self.run_cli("init", "--demo")
        answers = Path(self.home) / "bad.json"
        answers.write_text(json.dumps({"person.height": "很高"}), encoding="utf-8")
        code, out = self.run_cli("values", "set-many", "--file", str(answers))
        self.assertEqual(code, 2)
        self.assertIn("数字", out)

    def test_fields_add_and_map(self):
        self.run_cli("init", "--demo")
        code, out = self.run_cli("fields", "add", "--label", "GRE", "--value", "320",
                                 "--aliases", "GRE成绩")
        self.assertEqual(code, 0)
        data = json.loads((Path(self.home) / "values.json").read_text(encoding="utf-8"))
        self.assertEqual(data["custom_fields"]["gre"]["label"], "GRE")
        self.assertEqual(data["custom"]["gre"]["v"], "320")

        code, out = self.run_cli("fields", "map", "--label", "最高学历学校",
                                 "--path", "education.0.school")
        self.assertEqual(code, 0)
        data = json.loads((Path(self.home) / "values.json").read_text(encoding="utf-8"))
        self.assertEqual(data["aliases"]["最高学历学校"], "education.0.school")

        code, out = self.run_cli("fields", "list")
        self.assertIn("GRE", out)
        self.assertIn("最高学历学校", out)

    def test_values_skip(self):
        self.run_cli("init", "--demo")
        code, out = self.run_cli("values", "skip", "narratives.hobby")
        self.assertEqual(code, 0)
        self.assertIn("不再问", out)
        data = json.loads((Path(self.home) / "values.json").read_text(encoding="utf-8"))
        self.assertIn("narratives.hobby", data["skipped"])

    def test_ledger_and_export(self):
        self.assertEqual(self.run_cli("ledger", "add", "--company", "甲", "--position", "岗")[0], 0)
        self.assertEqual(self.run_cli("ledger", "add", "--company", "甲", "--position", "岗")[0], 0)
        code, out = self.run_cli("ledger", "list")
        self.assertEqual(code, 0)
        code, out = self.run_cli("ledger", "export")
        self.assertEqual(code, 0)
        self.assertTrue((Path(self.home) / "exports" / "投递记录.csv").exists())

    def test_privacy_clean(self):
        code, out = self.run_cli("privacy", "scan")
        self.assertEqual(code, 0, out)

    def test_cards_validate(self):
        code, out = self.run_cli("cards", "validate")
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
