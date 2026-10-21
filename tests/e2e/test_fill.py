"""端到端：验证「直接赋值不生效、真实键盘输入才生效」。
没有装 playwright 或浏览器时自动跳过。"""

import functools
import http.server
import json
import threading
import unittest
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
    HAS_PW = True
except ImportError:
    HAS_PW = False

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES = ROOT / "fixtures"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _serve():
    handler = functools.partial(_Handler, directory=str(FIXTURES))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, httpd.server_address[1]


@unittest.skipUnless(HAS_PW, "没装 playwright")
class FillE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd, port = _serve()
        cls.url = f"http://127.0.0.1:{port}/element-ui.html"
        cls.pw = sync_playwright().start()
        try:
            try:
                cls.browser = cls.pw.chromium.launch(channel="chrome")
            except Exception:
                cls.browser = cls.pw.chromium.launch()
        except Exception as exc:  # noqa: BLE001
            cls.pw.stop()
            cls.httpd.shutdown()
            cls.httpd.server_close()
            raise unittest.SkipTest(f"浏览器没装好：{exc}")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.goto(self.url)

    def tearDown(self):
        self.page.close()

    def test_probe_finds_controls(self):
        js = (ROOT / "runner" / "probe.js").read_text(encoding="utf-8")
        data = self.page.evaluate(js)
        labels = [c["label"] for c in data["controls"]]
        self.assertIn("姓名", labels)
        self.assertIn("最高学历", labels)
        self.assertEqual(len(data["controls"]), 3)

    def test_direct_assignment_does_not_persist(self):
        self.page.evaluate("document.querySelector('[name=name]').value = '假名字'")
        self.page.click("#save")
        saved = json.loads(self.page.text_content("#saved") or "{}")
        self.assertEqual(saved, {})

    def test_real_typing_persists(self):
        self.page.locator("[name=name]").fill("张三")
        self.page.locator("[name=phone]").fill("13800000000")
        self.page.select_option("[name=degree]", label="硕士")
        self.page.click("#save")
        saved = json.loads(self.page.text_content("#saved") or "{}")
        self.assertEqual(saved.get("name"), "张三")
        self.assertEqual(saved.get("phone"), "13800000000")
        self.assertEqual(saved.get("degree"), "硕士")

    def test_false_save_error_is_shown(self):
        self.page.click("#save")
        self.assertIn("commitOthers", self.page.text_content("#err"))

    def test_executor_fills_and_verifies(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from jobpilot import formmodel, plan, profile, sitecards, verify
        from jobpilot.backends.cdp import CdpBackend
        from jobpilot.execute import run_plan

        js = (ROOT / "runner" / "probe.js").read_text(encoding="utf-8")
        form = formmodel.normalize(self.page.evaluate(js))
        vals = profile._seed_values(profile.DEMO_PROFILE)
        compiled = plan.compile_plan(form, vals, sitecards.load("element-ui"))
        self.assertEqual(compiled["stats"]["actions"], 3)

        backend = CdpBackend(page=self.page)
        result = run_plan(compiled, vals, backend, dry_run=True)
        self.assertTrue(result["ok"], result["failed"])
        recon = verify.reconcile(compiled, backend.readback())
        self.assertTrue(recon["ok"], recon)
        # 演练模式不应该点保存
        self.assertEqual(self.page.text_content("#saved"), "")


if __name__ == "__main__":
    unittest.main()
