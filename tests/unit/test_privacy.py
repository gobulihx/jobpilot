import tempfile
import unittest
from pathlib import Path

from jobpilot import privacy


class PrivacyTest(unittest.TestCase):
    def test_mask_id(self):
        self.assertEqual(privacy.mask_id("110101199901011234"), "110101********1234")

    def test_mask_phone(self):
        self.assertEqual(privacy.mask_phone("13800001234"), "138****1234")

    def test_mask_email(self):
        self.assertEqual(privacy.mask_email("zhangsan@example.com"), "zha***@example.com")

    def test_scan_text(self):
        hits = privacy.scan_text("身份证 110101199901011234 手机 13800001234 邮箱 a@b.com")
        self.assertEqual(set(hits), {"身份证号", "手机号", "邮箱"})

    def test_scan_secrets(self):
        self.assertIn("GitHub Token", privacy.scan_secrets("ghp_" + "a" * 36))
        self.assertIn("Private Key", privacy.scan_secrets("-----BEGIN RSA PRIVATE KEY-----"))
        self.assertEqual(privacy.scan_secrets("sk-short"), [])

    def test_scan_repo_finds_leak(self):
        root = Path(tempfile.mkdtemp())
        (root / "notes.md").write_text("身份证 110101199901011234", encoding="utf-8")
        hits = privacy.scan_repo(root)
        self.assertEqual(hits[0][0], "notes.md")

    def test_allow_marker(self):
        root = Path(tempfile.mkdtemp())
        (root / "demo.py").write_text("# jobpilot-privacy-allow\n身份证 110101199901011234",
                                      encoding="utf-8")
        self.assertEqual(privacy.scan_repo(root), [])


if __name__ == "__main__":
    unittest.main()
