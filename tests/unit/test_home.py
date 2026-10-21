import os
import tempfile
import unittest
from pathlib import Path

from jobpilot import home, sitecards


class HomeTest(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("JOBPILOT_HOME")
        os.environ["JOBPILOT_HOME"] = tempfile.mkdtemp()

    def tearDown(self):
        if self.old:
            os.environ["JOBPILOT_HOME"] = self.old
        else:
            os.environ.pop("JOBPILOT_HOME", None)

    def test_run_dir_stays_inside(self):
        d = home.run_dir("../../evil")
        root = (Path(os.environ["JOBPILOT_HOME"]) / "runs").resolve()
        self.assertTrue(str(d).startswith(str(root)))

    def test_sitecard_rejects_traversal(self):
        with self.assertRaises(ValueError):
            sitecards.load("../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
