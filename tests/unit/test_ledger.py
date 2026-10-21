import tempfile
import unittest
from pathlib import Path

from jobpilot.ledger import Ledger


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.db = Ledger(Path(tempfile.mkdtemp()) / "ledger.db")

    def tearDown(self):
        self.db.close()

    def test_idempotent(self):
        a, created1 = self.db.add("示例银行", "风险岗", "杭州", "2027")
        b, created2 = self.db.add("示例 银行", "风险岗", "杭州", "2027")
        self.assertEqual(a, b)
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(len(self.db.list()), 1)

    def test_status_from_event(self):
        app_id, _ = self.db.add("示例银行", "风险岗", "杭州", "2027")
        self.db.add_event(app_id, "submitted", "投了")
        self.db.add_event(app_id, "written_test", "笔试通知")
        app = self.db.get(app_id)
        self.assertEqual(app["status"], "written_test")
        self.assertTrue(app["applied_at"])
        self.assertEqual(len(self.db.events(app_id)), 3)

    def test_find_all(self):
        self.db.add("示例银行", "风险岗", "杭州", "2027")
        self.assertEqual(len(self.db.find_all("示例 银行", "风险岗")), 1)
        self.assertEqual(self.db.find_all("示例银行", "别的岗"), [])
        self.assertEqual(len(self.db.find_all("示例银行")), 1)

    def test_add_updates_status(self):
        app_id, _ = self.db.add("示例银行", "风险岗", "杭州", "2027")
        self.assertEqual(self.db.get(app_id)["status"], "draft")
        self.db.add("示例银行", "风险岗", "杭州", "2027", status="submitted")
        self.assertEqual(self.db.get(app_id)["status"], "submitted")
        self.assertTrue(self.db.get(app_id)["applied_at"])
        self.assertEqual(len(self.db.events(app_id)), 2)

    def test_funnel(self):
        a, _ = self.db.add("甲", "岗一", "杭州", "2027", status="submitted")
        b, _ = self.db.add("乙", "岗二", "上海", "2027", status="interview")
        self.db.add("丙", "岗三", "北京", "2027", status="draft")
        stats = self.db.funnel()
        self.assertEqual(stats["总数"], 3)
        self.assertEqual(stats["已投递"], 2)
        self.assertEqual(stats["面试"], 1)

    def test_rows(self):
        self.db.add("示例银行", "风险岗", "杭州", "2027", status="submitted")
        rows = self.db.rows()
        self.assertEqual(rows[0]["公司"], "示例银行")
        self.assertEqual(rows[0]["状态"], "已投递")

    def test_mail_dedupe(self):
        self.assertTrue(self.db.remember_mail("m1", "", "a@b.c", "笔试", "", "", "written_test"))
        self.assertFalse(self.db.remember_mail("m1", "", "a@b.c", "笔试", "", "", "written_test"))

    def test_unknown_status(self):
        with self.assertRaises(ValueError):
            self.db.add("甲", "岗", "", "", status="可以试试")


if __name__ == "__main__":
    unittest.main()
