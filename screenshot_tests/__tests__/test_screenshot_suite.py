"""
Unit Test Suite for Screenshot Testing Components.
Validates server lifecycle, image comparison mathematics, diff image creation,
HTML report generation, and scenario definitions.
"""

import os
import tempfile
import unittest
import urllib.request
from PIL import Image

from screenshot_tests.server import LocalSiteServer
from screenshot_tests.comparator import ImageComparator
from screenshot_tests.scenarios import SCENARIOS, TestScenario
from screenshot_tests.reporter import generate_html_report


class TestScreenshotSuite(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_local_site_server_lifecycle(self):
        """Verifies LocalSiteServer binds to ephemeral port, serves files, and shuts down."""
        # Create a dummy test file in temp dir
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Armenia Hub Server OK")

        with LocalSiteServer(root_dir=self.test_dir) as server:
            self.assertIsNotNone(server.port)
            self.assertTrue(server.port > 0)
            url = server.get_url("test.txt")
            with urllib.request.urlopen(url, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                body = resp.read().decode("utf-8")
                self.assertEqual(body, "Armenia Hub Server OK")

        # After exiting with block, server should be stopped
        self.assertIsNone(server.port)

    def test_image_comparator_identical_match(self):
        """Identical images must yield MATCH with 0.0% diff."""
        img_path = os.path.join(self.test_dir, "base.png")
        Image.new("RGB", (100, 100), (200, 200, 200)).save(img_path)

        comparator = ImageComparator(mismatch_threshold_percent=0.1)
        res = comparator.compare(
            scenario_id="test_id",
            current_path=img_path,
            baseline_path=img_path,
        )

        self.assertEqual(res.status, "MATCH")
        self.assertTrue(res.is_match)
        self.assertEqual(res.diff_percent, 0.0)
        self.assertEqual(res.diff_pixels, 0)

    def test_image_comparator_diff_detection_and_image(self):
        """Different images must yield MISMATCH and generate diff highlight image."""
        base_path = os.path.join(self.test_dir, "base.png")
        curr_path = os.path.join(self.test_dir, "curr.png")
        diff_path = os.path.join(self.test_dir, "diff.png")

        b_img = Image.new("RGB", (50, 50), (255, 255, 255))
        c_img = Image.new("RGB", (50, 50), (255, 255, 255))
        # Modify 25 pixels (5x5 square) = 1% of 2500 total pixels
        for x in range(5):
            for y in range(5):
                c_img.putpixel((x, y), (0, 0, 0))

        b_img.save(base_path)
        c_img.save(curr_path)

        comparator = ImageComparator(mismatch_threshold_percent=0.01, color_tolerance=10)
        res = comparator.compare(
            scenario_id="diff_test",
            current_path=curr_path,
            baseline_path=base_path,
            diff_output_path=diff_path,
        )

        self.assertEqual(res.status, "MISMATCH")
        self.assertFalse(res.is_match)
        self.assertEqual(res.diff_pixels, 25)
        self.assertAlmostEqual(res.diff_percent, 1.0, places=1)
        self.assertTrue(os.path.exists(diff_path))

    def test_image_comparator_missing_baseline(self):
        """Missing baseline should return NEW_BASELINE status cleanly."""
        curr_path = os.path.join(self.test_dir, "curr.png")
        Image.new("RGB", (80, 80), (100, 100, 100)).save(curr_path)

        comparator = ImageComparator()
        res = comparator.compare(
            scenario_id="new_test",
            current_path=curr_path,
            baseline_path=None,
        )

        self.assertEqual(res.status, "NEW_BASELINE")
        self.assertTrue(res.is_match)
        self.assertEqual(res.diff_percent, 0.0)

    def test_image_comparator_size_mismatch(self):
        """Images with different dimensions must report SIZE_MISMATCH."""
        base_path = os.path.join(self.test_dir, "base_wide.png")
        curr_path = os.path.join(self.test_dir, "curr_narrow.png")

        Image.new("RGB", (100, 100), (255, 255, 255)).save(base_path)
        Image.new("RGB", (100, 120), (255, 255, 255)).save(curr_path)

        comparator = ImageComparator()
        res = comparator.compare(
            scenario_id="size_test",
            current_path=curr_path,
            baseline_path=base_path,
        )

        self.assertEqual(res.status, "SIZE_MISMATCH")
        self.assertFalse(res.is_match)
        self.assertEqual(res.baseline_size, (100, 100))
        self.assertEqual(res.current_size, (100, 120))

    def test_html_reporter_generates_valid_html(self):
        """generate_html_report should produce an interactive HTML file with stats."""
        report_file = os.path.join(self.test_dir, "report.html")

        img_path = os.path.join(self.test_dir, "test.png")
        Image.new("RGB", (50, 50), (255, 255, 255)).save(img_path)

        comparator = ImageComparator()
        comp_res = comparator.compare(
            scenario_id="desktop_home",
            current_path=img_path,
            baseline_path=img_path,
        )

        out_path = generate_html_report(
            results=[comp_res],
            scenarios=[SCENARIOS[0]],
            report_output_path=report_file,
            output_dir=self.test_dir,
            baselines_dir=self.test_dir,
            duration_seconds=1.23,
        )

        self.assertTrue(os.path.exists(out_path))
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Visual Screenshot Test Report", content)
            self.assertIn("desktop_home", content)
            self.assertIn("PASSED (MATCH)", content)

    def test_scenarios_registry_validity(self):
        """All registered scenarios must have unique IDs and positive viewports."""
        ids = set()
        for s in SCENARIOS:
            self.assertNotIn(s.id, ids, f"Duplicate scenario ID: {s.id}")
            ids.add(s.id)
            self.assertTrue(s.viewport[0] > 0 and s.viewport[1] > 0)
            self.assertTrue(len(s.title) > 0)
            self.assertTrue(len(s.description) > 0)


if __name__ == "__main__":
    unittest.main()
