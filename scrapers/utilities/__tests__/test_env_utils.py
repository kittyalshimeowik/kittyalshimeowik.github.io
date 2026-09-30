# scrapers/utilities/__tests__/test_env_utils.py
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.env_utils import (
    ensure_utf8_output,
    get_project_root,
    get_venv_python,
    ensure_virtualenv
)


class TestEnvUtils(unittest.TestCase):

    def test_ensure_utf8_output_runs_safely(self):
        # Should execute without throwing exceptions across platforms
        ensure_utf8_output()
        self.assertTrue(True)

    def test_get_project_root(self):
        root = get_project_root(__file__)
        self.assertTrue(os.path.isdir(root))
        self.assertTrue(os.path.isfile(os.path.join(root, "run_tests.py")))

    def test_get_venv_python(self):
        py_exe = get_venv_python(__file__)
        self.assertTrue(os.path.isfile(py_exe) or py_exe == sys.executable)

    def test_ensure_virtualenv_in_test_environment(self):
        # Should gracefully return without recursion or re-launch because unittest is in sys.argv
        ensure_virtualenv(__file__)
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
