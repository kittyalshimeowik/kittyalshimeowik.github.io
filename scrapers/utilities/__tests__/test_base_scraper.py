# scrapers/utilities/__tests__/test_base_scraper.py
import os
import sys
import json
import shutil
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.base_scraper import BaseScraper


class ConcreteTestScraper(BaseScraper):
    """Concrete implementation of BaseScraper for testing abstract base functionality."""
    def run(self, **kwargs):
        return kwargs


class TestBaseScraper(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. normalize_price_amount
    # -------------------------------------------------------------------------

    def test_normalize_price_amount_standard_and_symbols(self):
        self.assertEqual(BaseScraper.normalize_price_amount("100,000"), 100000)
        self.assertEqual(BaseScraper.normalize_price_amount("$85.000"), 85000)
        self.assertEqual(BaseScraper.normalize_price_amount("120 000 AMD"), 120000)
        self.assertEqual(BaseScraper.normalize_price_amount("֏ 500000"), 500000)

    def test_normalize_price_amount_invalid_and_empty(self):
        self.assertIsNone(BaseScraper.normalize_price_amount(None))
        self.assertIsNone(BaseScraper.normalize_price_amount(""))
        self.assertIsNone(BaseScraper.normalize_price_amount("no digits here"))

    # -------------------------------------------------------------------------
    # 2. sanitize_area_size
    # -------------------------------------------------------------------------

    def test_sanitize_area_size_numbers_and_units(self):
        self.assertEqual(BaseScraper.sanitize_area_size("85"), 85.0)
        self.assertEqual(BaseScraper.sanitize_area_size("120.5"), 120.5)
        self.assertEqual(BaseScraper.sanitize_area_size("65 sq.m."), 65.0)
        self.assertEqual(BaseScraper.sanitize_area_size("150 քմ"), 150.0)

    def test_sanitize_area_size_invalid_and_empty(self):
        self.assertIsNone(BaseScraper.sanitize_area_size(None))
        self.assertIsNone(BaseScraper.sanitize_area_size(""))
        self.assertIsNone(BaseScraper.sanitize_area_size("text without digits"))

    # -------------------------------------------------------------------------
    # 3. load_existing_dataset and save_final_results
    # -------------------------------------------------------------------------

    def test_load_existing_dataset_missing_file(self):
        scraper = ConcreteTestScraper(output_subdir="test_output")
        data, urls = scraper.load_existing_dataset("non_existent_file.json")
        self.assertEqual(data, [])
        self.assertEqual(urls, set())

    def test_load_and_save_dataset_roundtrip(self):
        scraper = ConcreteTestScraper(output_subdir="test_output_roundtrip")
        filename = "test_posts.json"
        
        sample_posts = [
            {"url": "https://example.com/item/1", "title": "Post 1"},
            {"url": "https://example.com/item/2", "title": "Post 2"},
            {"title": "Post without url"}
        ]
        
        try:
            scraper.save_final_results(filename, sample_posts)
            loaded_data, loaded_urls = scraper.load_existing_dataset(filename)
            
            self.assertEqual(len(loaded_data), 3)
            self.assertEqual(loaded_urls, {"https://example.com/item/1", "https://example.com/item/2"})
        finally:
            # Clean up test output directory
            if os.path.exists(scraper.OUTPUT_DIR):
                shutil.rmtree(scraper.OUTPUT_DIR, ignore_errors=True)

    def test_load_existing_dataset_corrupted_json(self):
        scraper = ConcreteTestScraper(output_subdir="test_output_corrupted")
        filename = "corrupt.json"
        file_path = os.path.join(scraper.OUTPUT_DIR, filename)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("INVALID JSON CONTENT { [")
                
            data, urls = scraper.load_existing_dataset(filename)
            self.assertEqual(data, [])
            self.assertEqual(urls, set())
        finally:
            if os.path.exists(scraper.OUTPUT_DIR):
                shutil.rmtree(scraper.OUTPUT_DIR, ignore_errors=True)

    def test_scraper_initialization_with_metadata_subdir(self):
        scraper = ConcreteTestScraper(output_subdir="test_out", metadata_subdir="test_meta")
        self.assertIsNotNone(scraper.METADATA_DIR)
        self.assertTrue(os.path.exists(scraper.OUTPUT_DIR))
        self.assertTrue(os.path.exists(scraper.METADATA_DIR))
        self.assertEqual(scraper.run(foo="bar"), {"foo": "bar"})

        # Clean up
        shutil.rmtree(scraper.OUTPUT_DIR, ignore_errors=True)
        shutil.rmtree(scraper.METADATA_DIR, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
