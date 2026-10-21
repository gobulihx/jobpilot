import unittest

from jobpilot import sitecards


class SiteCardTest(unittest.TestCase):
    def test_load_element_ui(self):
        card = sitecards.load("element-ui")
        self.assertEqual(card["id"], "element-ui")
        self.assertTrue(card["quirks"]["real_keys"])
        self.assertTrue(card["quirks"]["back_blank"])

    def test_layer_override(self):
        card = sitecards.load("nbcb")
        self.assertIn("学校名称（限20字）", card["fields"])
        self.assertEqual(card["quirks"]["false_save_error"], "commitOthers is not a function")

    def test_detect_by_url(self):
        self.assertEqual(sitecards.detect("https://zhaopin.nbcb.com.cn/#/x"), "nbcb")
        self.assertEqual(sitecards.detect("https://xiaoyuan.zhaopin.com/x"), "zhaopin")

    def test_validate(self):
        self.assertEqual(sitecards.validate(sitecards.load("element-ui")), [])


if __name__ == "__main__":
    unittest.main()
