import unittest

from jobpilot import schema


class SchemaTest(unittest.TestCase):
    def test_l0_is_twelve(self):
        self.assertEqual(len(schema.L0), 12)

    def test_ids_unique(self):
        ids = [f.id for f in schema.FIELDS.values()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_normalize_label(self):
        self.assertEqual(schema.normalize_label("请输入姓名："), "姓名")
        self.assertEqual(schema.normalize_label(" 最高学历 * "), "最高学历")

    def test_repeat_fields(self):
        self.assertTrue(schema.FIELDS["education.school"].repeat)
        self.assertFalse(schema.FIELDS["person.name"].repeat)

    def test_field_for_indexed_path(self):
        self.assertEqual(schema.field_for("education.0.school").id, "education.school")
        self.assertEqual(schema.label_for("education.0.school"), "学校名称")


if __name__ == "__main__":
    unittest.main()
