import os
import sys
import unittest

# Add parent directory to python path so we can import the scraper script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fb_in_feed_tab_scraper import (
    extract_housing_details,
    normalize_price_amount,
    normalize_phone_number,
    extract_property_category,
    extract_negotiation_status,
)


class TestHousingExtractor(unittest.TestCase):

    # -------------------------------------------------------------------------
    # 1. PRICE & CURRENCY EXTRACTION TESTS
    # -------------------------------------------------------------------------

    def test_standard_usd_price(self):
        text = "Վաճառվում է 3 սենյականոց բնակարան: Գինը` 93000$"
        details = extract_housing_details(text)
        self.assertEqual(len(details["prices"]), 1)
        self.assertEqual(details["prices"][0]["amount"], 93000)
        self.assertEqual(details["prices"][0]["currency"], "USD")

    def test_failing_case_dot_separator_and_value_keyword(self):
        text = "🏷️ Արժեքը` 93.000$"
        details = extract_housing_details(text)
        self.assertEqual(len(details["prices"]), 1)
        self.assertEqual(details["prices"][0]["amount"], 93000)
        self.assertEqual(details["prices"][0]["currency"], "USD")

    def test_amd_price_with_commas(self):
        text = "Վարձով է տրվում բնակարան Կենտրոնում, 350,000 dram"
        details = extract_housing_details(text)
        self.assertEqual(len(details["prices"]), 1)
        self.assertEqual(details["prices"][0]["amount"], 350000)
        self.assertEqual(details["prices"][0]["currency"], "AMD")

    def test_unspecified_currency_high_amount_defaults_to_amd(self):
        text = "Գինը 45000000"
        details = extract_housing_details(text)
        self.assertEqual(len(details["prices"]), 1)
        self.assertEqual(details["prices"][0]["amount"], 45000000)
        self.assertEqual(details["prices"][0]["currency"], "AMD")

    def test_year_filtering_false_positive(self):
        text = "Կապիտալ վերանորոգվել է 2024 թվականին:"
        details = extract_housing_details(text)
        self.assertEqual(len(details["prices"]), 0)

    def test_143k_usd_price_extraction(self):
        text = "Վաճառվում է բնակարան: Գինը` 143,000$"
        details = extract_housing_details(text)
        self.assertEqual(len(details["prices"]), 1)
        self.assertEqual(details["prices"][0]["amount"], 143000)
        self.assertEqual(details["prices"][0]["currency"], "USD")

    def test_space_separated_prices(self):
        text = "Գինը` 120 000 $"
        details = extract_housing_details(text)
        self.assertEqual(details["prices"][0]["amount"], 120000)
        self.assertEqual(details["prices"][0]["currency"], "USD")

    def test_property_code_noise_suppression(self):
        text = "Բնակարան Կենտրոնում, Կոդ: 854921, Գինը` 110000$"
        details = extract_housing_details(text)
        self.assertEqual(len(details["prices"]), 1)
        self.assertEqual(details["prices"][0]["amount"], 110000)

    # -------------------------------------------------------------------------
    # 2. PHONE NUMBER NORMALIZATION TESTS
    # -------------------------------------------------------------------------

    def test_armenian_local_phone_formatting(self):
        self.assertEqual(normalize_phone_number("077099497"), "+374 77 099 497")
        self.assertEqual(normalize_phone_number("+37498522055"), "+374 98 522 055")

    def test_phone_extraction_from_post_text(self):
        text = "Զանգահարել 077-099-497 կամ 098 522 055"
        details = extract_housing_details(text)
        self.assertIn("+374 77 099 497", details["phone_numbers"])
        self.assertIn("+374 98 522 055", details["phone_numbers"])

    # -------------------------------------------------------------------------
    # 3. SIZE & ROOM EXTRACTION TESTS
    # -------------------------------------------------------------------------

    def test_size_sqm_extraction(self):
        text = "Մակերես` 55 քմ, 3 սենյակ"
        details = extract_housing_details(text)
        self.assertIn(55, details["sizes_sqm"])
        self.assertIn(3, details["rooms"])

    def test_size_sqm_thousands_separators(self):
        # Testing comma as thousands separator (e.g., 1,500 sq.m)
        text_comma = "Բնակարանի մակերեսը՝ 1,500 քմ"
        details_comma = extract_housing_details(text_comma)
        self.assertIn(1500, details_comma["sizes_sqm"])

        # Testing dot as thousands separator (e.g., 2.400 sq.m)
        text_dot = "Վաճառվում է 2.400 քմ հողատարածք"
        details_dot = extract_housing_details(text_dot)
        self.assertIn(2400, details_dot["sizes_sqm"])

        # Testing space as thousands separator (e.g., 3 500 sq.m)
        text_space = "Մակերեսը 3 500 քմ"
        details_space = extract_housing_details(text_space)
        self.assertIn(3500, details_space["sizes_sqm"])

    def test_room_count_variations(self):
        text_arm = "3 սենյականոց բնակարան"
        text_ru = "2 комн квартира"
        text_en = "4 bedrooms apartment"

        self.assertEqual(extract_housing_details(text_arm)["rooms"], [3])
        self.assertEqual(extract_housing_details(text_ru)["rooms"], [2])
        self.assertEqual(extract_housing_details(text_en)["rooms"], [4])

    # -------------------------------------------------------------------------
    # 4. FLOOR INFO EXTRACTION TESTS
    # -------------------------------------------------------------------------

    def test_floor_parsing(self):
        text = "Հարկ` 3/2 (3-րդ հարկ 2 հարկանի շենքում)"
        details = extract_housing_details(text)
        self.assertIsNotNone(details["floor_info"])
        self.assertEqual(details["floor_info"]["floor"], 3)
        self.assertEqual(details["floor_info"]["total_floors"], 2)

    # -------------------------------------------------------------------------
    # 5. LOCATION & CATEGORY EXTRACTION TESTS
    # -------------------------------------------------------------------------

    def test_location_dictionary_matching(self):
        text = "Բնակարան Կոմիտասում, Արաբկիր վարչական շրջան"
        details = extract_housing_details(text)
        self.assertIn("Arabkir", details["locations"])

    def test_property_category_classification(self):
        self.assertEqual(extract_property_category("Վաճառվում է բնակարան"), "Apartment")
        self.assertEqual(extract_property_category("Վաճառվում է առանձնատուն"), "House")
        self.assertEqual(extract_property_category("Վաճառվում է հողատարածք"), "Land")
        self.assertEqual(extract_property_category("", is_media_only=True), "Media-Only")

    def test_negotiable_status(self):
        self.assertTrue(extract_negotiation_status("Գինը սակարկելի"))
        self.assertFalse(extract_negotiation_status("Վերջնական գին, առանց տորգի"))
        self.assertEqual(extract_negotiation_status("Պարզապես տեքստ"), "Unknown")

    def test_rental_vs_sale_conflict(self):
        text = "Վաճառվում է կամ տրվում է վարձով 3 սենյականոց բնակարան"
        details = extract_housing_details(text)
        self.assertEqual(details["listing_type"], "Sale")

    # -------------------------------------------------------------------------
    # 6. Dynamic Scrolling
    # -------------------------------------------------------------------------

    def test_calculate_dynamic_runtime_corrupted_benchmarks(self):
        # Test fallback behavior when scroll_benchmarks is empty or missing
        from fb_in_feed_tab_scraper import calculate_dynamic_runtime
        metadata_empty = {"scroll_benchmarks": []}
        runtime = calculate_dynamic_runtime(metadata_empty, default_runtime=300)
        self.assertEqual(runtime, 300)

    def test_calculate_dynamic_runtime_valid_benchmarks(self):
        from fb_in_feed_tab_scraper import calculate_dynamic_runtime
        metadata_valid = {
            "scroll_benchmarks": {
                "2026-09-14": {"scroll_duration_seconds": 120.0},
                "2026-09-15": {"scroll_duration_seconds": 150.0},
                "2026-09-16": {"scroll_duration_seconds": 180.0}
            }
        }
        runtime = calculate_dynamic_runtime(metadata_valid, default_runtime=300)
        self.assertGreater(runtime, 0)


if __name__ == "__main__":
    unittest.main()