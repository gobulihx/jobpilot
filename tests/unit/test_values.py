import unittest

from jobpilot import profile, values


class ValuesTest(unittest.TestCase):
    def setUp(self):
        self.v = profile._seed_values(profile.DEMO_PROFILE)

    def test_demo_has_no_missing(self):
        self.assertEqual(values.missing(self.v), [])

    def test_repeat_path_without_index(self):
        self.assertEqual(values.get_value(self.v, "education.school"), "示例大学")

    def test_set_get(self):
        values.set_value(self.v, "person.height", "180", type_="number")
        self.assertEqual(values.get_value(self.v, "person.height"), "180")

    def test_missing_when_empty(self):
        values.delete_path(self.v, "intent.salary_min")
        self.assertIn("intent.salary_min", values.missing(self.v))

    def test_max_length(self):
        values.set_value(self.v, "education.0.school", "这是一个特别特别特别特别特别长的学校名称用来测试超长校验")
        issues = values.validate(self.v)
        self.assertTrue(any("超过" in i for i in issues))

    def test_flat_masks(self):
        rows = values.flat(self.v, mask=True)
        id_row = [r for r in rows if r["path"] == "person.id_no"][0]
        self.assertNotIn("199901011234", str(id_row["value"]))

    def test_check_value(self):
        self.assertIsNone(values.check_value("person.height", "180"))
        self.assertIsNotNone(values.check_value("person.height", "高"))
        self.assertIsNone(values.check_value("person.birth_date", "2002-02-15"))
        self.assertIsNotNone(values.check_value("person.birth_date", "2002/02/15"))
        self.assertIsNotNone(values.check_value("education.0.school", "字" * 30))
        self.assertIsNone(values.check_value("intent.adjust", "是"))
        self.assertIsNotNone(values.check_value("intent.adjust", "也许"))

    def test_coerce_natural_input(self):
        self.assertEqual(values.coerce("education.0.grad_date", "2026年11月"), "2026-11")
        self.assertEqual(values.coerce("person.birth_date", "2002/2/15"), "2002-02-15")
        self.assertEqual(values.coerce("person.height", "18,0"), "180")
        self.assertIs(values.coerce("flags.fresh_grad", "是"), True)
        self.assertIs(values.coerce("flags.fresh_grad", "否"), False)

    def test_custom_field(self):
        path = values.add_custom(self.v, "GRE", value="320", aliases=["GRE成绩"])
        self.assertEqual(path, "custom.gre")
        self.assertEqual(values.get_value(self.v, path), "320")
        self.assertEqual(values.label_of(self.v, path), "GRE")
        self.assertEqual(values.custom_alias_index(self.v)["GRE成绩"], ("custom.gre",))
        self.assertIsNone(values.check_value(path, "325", self.v))

    def test_custom_field_type_check(self):
        path = values.add_custom(self.v, "托福", value="105", type_="number")
        self.assertIsNone(values.check_value(path, "110", self.v))
        self.assertIsNotNone(values.check_value(path, "很高", self.v))

    def test_skip_memory(self):
        values.skip(self.v, "narratives.hobby")
        self.assertIn("narratives.hobby", values.skipped(self.v))
        values.skip(self.v, "narratives.hobby", on=False)
        self.assertNotIn("narratives.hobby", values.skipped(self.v))

    def test_validate_flags_bad_date(self):
        values.set_value(self.v, "person.birth_date", "1999/01/01", type_="date")
        issues = values.validate(self.v)
        self.assertTrue(any("出生日期" in i or "person.birth_date" in i for i in issues))


if __name__ == "__main__":
    unittest.main()
