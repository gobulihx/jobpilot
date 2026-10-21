import json
import unittest
from pathlib import Path

from jobpilot import formmodel

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "element-ui.form.json"


class FormModelTest(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads(FIX.read_text(encoding="utf-8"))

    def test_normalize_assigns_cids(self):
        form = formmodel.normalize(self.raw)
        self.assertEqual(len(form["controls"]), 13)
        self.assertTrue(all(c["cid"] for c in form["controls"]))
        self.assertEqual(len({c["cid"] for c in form["controls"]}), 13)

    def test_fingerprint_stable(self):
        a = formmodel.normalize(self.raw)["dom_fingerprint"]
        b = formmodel.normalize(self.raw)["dom_fingerprint"]
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)

    def test_fingerprint_changes_with_structure(self):
        a = formmodel.normalize(self.raw)["dom_fingerprint"]
        changed = json.loads(json.dumps(self.raw))
        changed["controls"].pop()
        b = formmodel.normalize(changed)["dom_fingerprint"]
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
