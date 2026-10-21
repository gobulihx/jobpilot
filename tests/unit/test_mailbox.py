import json
import tempfile
import unittest
from pathlib import Path

from jobpilot import mailbox

FIX = Path(__file__).resolve().parent.parent / "fixtures"


class MailboxTest(unittest.TestCase):
    def test_eml_decodes_subject(self):
        mails = mailbox.load(FIX / "mail.eml")
        self.assertEqual(len(mails), 1)
        self.assertEqual(mails[0]["subject"], "示例银行笔试通知")
        self.assertIn("10 月 25 日", mails[0]["snippet"])
        self.assertEqual(mails[0]["msgid"], "<m1@example-bank.com>")

    def test_mbox(self):
        mails = mailbox.load(FIX / "mail.mbox")
        self.assertEqual(len(mails), 2)
        self.assertEqual(mails[1]["subject"], "面试邀请")

    def test_json_aliases(self):
        data = [{
            "id": "x1", "subject": "笔试通知",
            "from": {"name": "HR", "addr": "hr@example.com"},
            "preview": "<p>请参加笔试</p>", "date": "2026-10-20",
        }]
        path = Path(tempfile.mkdtemp()) / "mails.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        mails = mailbox.load(path)
        self.assertEqual(mails[0]["from"], "hr@example.com")
        self.assertEqual(mails[0]["snippet"], "请参加笔试")
        self.assertEqual(mails[0]["msgid"], "x1")

    def test_json_envelopes_key(self):
        data = {"envelopes": [{"id": "e1", "subject": "笔试", "from": "hr@example.com"}]}
        path = Path(tempfile.mkdtemp()) / "m.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(len(mailbox.load(path)), 1)

    def test_jsonl(self):
        path = Path(tempfile.mkdtemp()) / "m.jsonl"
        path.write_text('{"id":"l1","subject":"面试"}\n{"id":"l2","subject":"笔试"}\n',
                        encoding="utf-8")
        self.assertEqual(len(mailbox.load(path)), 2)

    def test_directory_and_dedupe(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "a.eml").write_text((FIX / "mail.eml").read_text(encoding="utf-8"),
                                   encoding="utf-8")
        (tmp / "b.eml").write_text((FIX / "mail.eml").read_text(encoding="utf-8"),
                                   encoding="utf-8")
        self.assertEqual(len(mailbox.load(tmp)), 1)

    def test_unknown_file(self):
        path = Path(tempfile.mkdtemp()) / "x.txt"
        path.write_text("not mail", encoding="utf-8")
        with self.assertRaises(ValueError):
            mailbox.load(path)


if __name__ == "__main__":
    unittest.main()
