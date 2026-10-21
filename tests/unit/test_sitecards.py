import json
import tempfile
import unittest
from pathlib import Path

from jobpilot import sitecards


class SiteCardTest(unittest.TestCase):
    def test_default_is_generic(self):
        card = sitecards.load("_generic")
        self.assertEqual(card["id"], "_generic")
        self.assertTrue(card["quirks"]["real_keys"])

    def test_nothing_shipped_for_specific_sites(self):
        self.assertEqual(sitecards.all_cards(), [])

    def test_unknown_falls_back_to_generic(self):
        self.assertEqual(sitecards.detect("https://example.org/apply"), "_generic")

    def test_local_card_overrides(self):
        tmp = Path(tempfile.mkdtemp())
        card = {
            "schema_version": 1, "id": "my-bank", "kind": "site",
            "match": {"url_patterns": ["my-bank.example"], "widgets": []},
            "fields": {"自定义栏": "person.height"},
            "quirks": {"real_keys": True, "false_save_error": "boom", "back_blank": True},
        }
        (tmp / "my-bank.json").write_text(json.dumps(card), encoding="utf-8")
        self.assertEqual(sitecards.detect("https://my-bank.example/apply", extra_dir=tmp), "my-bank")
        merged = sitecards.load("my-bank", extra_dir=tmp)
        self.assertEqual(merged["fields"]["自定义栏"], "person.height")
        self.assertEqual(merged["quirks"]["false_save_error"], "boom")
        self.assertIn("save", merged)

    def test_template_is_skipped(self):
        names = [name for name, _ in sitecards.all_cards()]
        self.assertFalse(any("_template" in n for n in names))

    def test_validate(self):
        self.assertEqual(sitecards.validate(sitecards.load("_generic")), [])


if __name__ == "__main__":
    unittest.main()
