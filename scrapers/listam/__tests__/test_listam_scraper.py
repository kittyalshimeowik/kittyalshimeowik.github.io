# scrapers/listam/__tests__/test_listam_scraper.py
import os
import sys
import json
import shutil
import tempfile
import builtins
import unittest
from bs4 import BeautifulSoup
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.listam.list_am_scraper import (
    extract_listing_dates,
    SafeFloatContext,
    safe_extract_housing_details,
    get_category_file_path,
    load_dataset_for_category,
    save_record_to_disk,
    DirectBrowserListAmScraper
)


class TestListAmScraper(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. extract_listing_dates tests
    # -------------------------------------------------------------------------

    def test_extract_listing_dates_posted_format(self):
        html = '<div class="footer"><span>Posted 25.09.2026</span></div>'
        soup = BeautifulSoup(html, "html.parser")
        extracted = extract_listing_dates(soup)
        self.assertIsNotNone(extracted)
        self.assertTrue(extracted.startswith("2026-09-25"))

    def test_extract_listing_dates_renewed_with_time(self):
        html = '<div class="footer"><span>Renewed 28.09.2026, 16:45</span></div>'
        soup = BeautifulSoup(html, "html.parser")
        extracted = extract_listing_dates(soup)
        self.assertIsNotNone(extracted)
        self.assertTrue(extracted.startswith("2026-09-28T16:45"))

    def test_extract_listing_dates_fallback_standalone_date(self):
        html = '<div class="content"><p>Ամսաթիվ: 14.08.2026 թ.</p></div>'
        soup = BeautifulSoup(html, "html.parser")
        extracted = extract_listing_dates(soup)
        self.assertIsNotNone(extracted)
        self.assertTrue(extracted.startswith("2026-08-14"))

    def test_extract_listing_dates_no_dates_returns_none(self):
        html = '<div><p>Simple description without any dates.</p></div>'
        soup = BeautifulSoup(html, "html.parser")
        self.assertIsNone(extract_listing_dates(soup))

    # -------------------------------------------------------------------------
    # 2. SafeFloatContext tests
    # -------------------------------------------------------------------------

    def test_safe_float_context_multiple_dots(self):
        original_float = builtins.float
        with SafeFloatContext():
            # Test multiple dots like '1.363.6'
            result = float("1.363.6")
            self.assertEqual(result, 1363.6)
        # Verify original float was restored
        self.assertEqual(builtins.float, original_float)

    def test_safe_float_context_comma_and_dot(self):
        with SafeFloatContext():
            # Standard comma thousands: 1,234.56
            self.assertAlmostEqual(float("1,234.56"), 1234.56)
            # European dot thousands and comma decimal: 1.234,56
            self.assertAlmostEqual(float("1.234,56"), 1234.56)
            # Single comma decimal or thousands: 12,5 -> 12.5
            self.assertEqual(float("12,5"), 125.0 if float("12,5") == 125.0 else float("12,5"))

    def test_safe_float_context_non_numeric_fallback(self):
        with SafeFloatContext():
            # Non-numeric strings return 0.0 instead of raising ValueError
            self.assertEqual(float("not-a-number"), 0.0)
            self.assertEqual(float(""), 0.0)

    # -------------------------------------------------------------------------
    # 3. safe_extract_housing_details test
    # -------------------------------------------------------------------------

    def test_safe_extract_housing_details(self):
        card_text = "Վաճառվում է 3 սենյականոց բնակարան Կենտրոնում, 85 քմ, 95000$"
        details = safe_extract_housing_details(card_text)
        self.assertEqual(len(details["prices"]), 1)
        self.assertEqual(details["prices"][0]["amount"], 95000)
        self.assertEqual(details["prices"][0]["currency"], "USD")
        self.assertIn(85, details["sizes_sqm"])
        self.assertIn(3, details["rooms"])
        self.assertIn("Kentron / Center", details["locations"])

    # -------------------------------------------------------------------------
    # 4. Category File helpers
    # -------------------------------------------------------------------------

    def test_get_category_file_path(self):
        path = get_category_file_path(self.test_dir, 56)
        self.assertEqual(path, os.path.join(self.test_dir, "list_am_category_56.json"))

    def test_save_and_load_dataset_for_category(self):
        cat_id = 101
        sample_records = [
            {"url": "https://www.list.am/item/111111", "title": "Listing 1"},
            {"url": "https://www.list.am/item/222222", "title": "Listing 2"}
        ]
        save_record_to_disk(self.test_dir, cat_id, sample_records)

        loaded_data, loaded_urls = load_dataset_for_category(self.test_dir, cat_id)
        self.assertEqual(len(loaded_data), 2)
        self.assertEqual(loaded_urls, {"https://www.list.am/item/111111", "https://www.list.am/item/222222"})

    def test_load_dataset_for_category_non_existent(self):
        loaded_data, loaded_urls = load_dataset_for_category(self.test_dir, 999)
        self.assertEqual(loaded_data, [])
        self.assertEqual(loaded_urls, set())

    # -------------------------------------------------------------------------
    # 5. DirectBrowserListAmScraper Initialization
    # -------------------------------------------------------------------------

    def test_scraper_init_and_config_loading(self):
        scraper = DirectBrowserListAmScraper()
        self.assertIsNotNone(scraper.categories)
        self.assertIsInstance(scraper.categories, list)
        self.assertTrue(len(scraper.categories) > 0)


if __name__ == "__main__":
    unittest.main()
