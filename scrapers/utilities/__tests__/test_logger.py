# scrapers/utilities/__tests__/test_logger.py
import os
import sys
import shutil
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.logger import (
    get_logger,
    analyze_logs,
    print_log_diagnostic_report,
    DIAGNOSTIC_PATTERNS
)


class TestLogger(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_logger_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_logger_basic(self):
        logger = get_logger("test_module", log_file="test_mod.log", logs_dir=self.test_dir)
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "test_module")
        logger.info("This is an info message from test_module.")

        mod_log_path = os.path.join(self.test_dir, "test_mod.log")
        combined_path = os.path.join(self.test_dir, "combined.log")

        self.assertTrue(os.path.isfile(mod_log_path))
        self.assertTrue(os.path.isfile(combined_path))

        with open(mod_log_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("This is an info message from test_module.", content)

    def test_analyze_logs_clean_directory(self):
        report = analyze_logs(logs_dir=self.test_dir)
        self.assertEqual(report["files_scanned"], 0)
        self.assertEqual(report["total_errors"], 0)
        for cat in DIAGNOSTIC_PATTERNS:
            self.assertEqual(report["patterns_detected"][cat], 0)

    def test_analyze_logs_pattern_detection(self):
        sample_log_path = os.path.join(self.test_dir, "sample.log")
        with open(sample_log_path, "w", encoding="utf-8") as f:
            f.write("2026-10-12 12:00:00 [INFO] Starting scraper\n")
            f.write("2026-10-12 12:00:05 [WARNING] Hit HTTP 429 Too Many Requests\n")
            f.write("2026-10-12 12:00:10 [WARNING] Detected cf-turnstile Cloudflare Challenge\n")
            f.write("2026-10-12 12:00:15 [ERROR] sqlite3.OperationalError: database is locked\n")
            f.write("2026-10-12 12:00:20 [ERROR] Connection timed out after 30 seconds\n")
            f.write("2026-10-12 12:00:25 [ERROR] JSONDecodeError: Expecting value: line 1 column 1\n")

        report = analyze_logs(logs_dir=self.test_dir)
        self.assertEqual(report["files_scanned"], 1)
        self.assertEqual(report["total_errors"], 3)
        self.assertEqual(report["total_warnings"], 2)

        self.assertGreaterEqual(report["patterns_detected"]["Rate Limiting"], 1)
        self.assertGreaterEqual(report["patterns_detected"]["Bot Checkpoints & Challenges"], 1)
        self.assertGreaterEqual(report["patterns_detected"]["Database & Storage Locks"], 1)
        self.assertGreaterEqual(report["patterns_detected"]["Network & Navigation Timeouts"], 1)
        self.assertGreaterEqual(report["patterns_detected"]["Data Parsing & Deserialization"], 1)
        self.assertGreaterEqual(len(report["recent_errors"]), 3)

    def test_print_log_diagnostic_report_runs(self):
        # Should execute cleanly without raising exceptions
        report = print_log_diagnostic_report(logs_dir=self.test_dir)
        self.assertIsInstance(report, dict)
        self.assertIn("patterns_detected", report)


if __name__ == "__main__":
    unittest.main()
