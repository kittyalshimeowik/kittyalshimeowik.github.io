import os
import sys
import unittest

# Add parent directory to python path so we can import the scraper script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from generate_site_data import (
    normalize_and_convert_prices,
    extract_canonical_post_id,
    normalize_listing_text,
    merge_duplicate_listings
)

class TestDataGenerator(unittest.TestCase):

    def test_price_conversion_usd_and_amd(self):
        prices = [{"amount": 1000, "currency": "USD"}]
        converted = normalize_and_convert_prices(prices)
        self.assertEqual(converted[0]["amount_usd"], 1000)
        self.assertEqual(converted[0]["amount_amd"], 364180)

    def test_canonical_id_extraction_variations(self):
        url1 = "https://www.facebook.com/groups/12345/posts/987654321/"
        url2 = "https://www.facebook.com/permalink.php?story_fbid=987654321&id=1000"
        self.assertEqual(extract_canonical_post_id(url1), "987654321")
        self.assertEqual(extract_canonical_post_id(url2), "987654321")

    def test_fuzzy_deduplication_completeness(self):
        sample_text = (
            "Վաճառվում է 3 սենյականոց բնակարան Կենտրոնում: Շատ լավ վիճակում, "
            "ապահովված է մշտական ջրով և գազով: Մոտակայքում կան խանութներ, "
            "դպրոց և կանգառ: Գինը պայմանագրային:"
        )
        post_incomplete = {
            "full_text": sample_text,
            "property_category": "Apartment",
            "listing_type": "Sale"
        }
        
        post_complete = {
            "full_text": sample_text,
            "property_category": "Apartment",
            "listing_type": "Sale",
            "prices": [{"amount": 100000, "currency": "USD"}],
            "phone_numbers": ["+374 77 000 000"],
            "locations": ["Kentron"]
        }
        
        merged = merge_duplicate_listings([post_incomplete, post_complete])
        self.assertEqual(len(merged), 1)
        self.assertTrue(bool(merged[0].get("prices")))
    
    def test_price_conversion_boundary_zero_and_negative(self):
        from generate_site_data import normalize_and_convert_prices
        # Test $0 price
        prices_zero = [{"amount": 0, "currency": "USD"}]
        converted_zero = normalize_and_convert_prices(prices_zero)
        self.assertEqual(converted_zero[0]["amount_usd"], 0)
        self.assertEqual(converted_zero[0]["amount_amd"], 0)

        # Test invalid string/non-numeric amount handling
        prices_invalid = [{"amount": "N/A", "currency": "USD"}]
        converted_invalid = normalize_and_convert_prices(prices_invalid)
        self.assertEqual(len(converted_invalid), 0)

    def test_sanitize_filename_special_characters(self):
        from generate_site_data import sanitize_filename
        # Ensure non-ASCII, spaces, and path injection characters are sanitized cleanly
        raw_location = "Kentron / Yerevan #1!"
        clean_location = sanitize_filename(raw_location)
        self.assertEqual(clean_location, "kentron_yerevan_1")

if __name__ == "__main__":
    unittest.main()