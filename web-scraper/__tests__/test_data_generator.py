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
        post_incomplete = {
            "full_text": "Վաճառվում է 3 սենյականոց բնակարան Կենտրոնում: Շատ լավ վիճակում:",
            "property_category": "Apartment",
            "listing_type": "Sale"
        }
        
        post_complete = {
            "full_text": "Վաճառվում է 3 սենյականոց բնակարան Կենտրոնում: Շատ լավ վիճակում:",
            "property_category": "Apartment",
            "listing_type": "Sale",
            "price_usd": 100000,            # Normalized key used by completeness score
            "phone": "+374 77 000 000",     # Normalized key used by completeness score
            "location_en": "Kentron"        # Additional structured data
        }
        
        merged = merge_duplicate_listings([post_incomplete, post_complete])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["price_usd"], 100000)

if __name__ == "__main__":
    unittest.main()