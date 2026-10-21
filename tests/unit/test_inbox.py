# jobpilot-privacy-allow
import json
import unittest
from pathlib import Path

from jobpilot import inbox

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "mails.json"


class InboxTest(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(inbox.classify("笔试通知"), "written_test")
        self.assertEqual(inbox.classify("面试邀请"), "interview")
        self.assertEqual(inbox.classify("录用意向书"), "offer")
        self.assertEqual(inbox.classify("感谢信"), "closed")
        self.assertIsNone(inbox.classify("本周资讯"))

    def test_propose_matches_company(self):
        mails = json.loads(FIX.read_text(encoding="utf-8"))
        apps = [{"id": "a1", "company": "示例银行"}]
        proposals = inbox.propose(mails, apps)
        first = proposals[0]
        self.assertEqual(first["kind"], "written_test")
        self.assertEqual(first["app_id"], "a1")
        self.assertGreaterEqual(first["confidence"], 0.8)

    def test_unmatched_is_question(self):
        mails = [{"msgid": "m9", "from": "hr@x.com", "subject": "面试邀请", "snippet": ""}]
        proposals = inbox.propose(mails, [])
        self.assertEqual(proposals[0]["confidence"], 0.4)
        self.assertTrue(proposals[0]["note"])


if __name__ == "__main__":
    unittest.main()
