# scrapers/processors/__tests__/test_dedup_utils.py
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.processors.dedup_utils import (
    is_ghost_record,
    is_valid_display_listing,
    normalize_listing_text,
    listing_completeness_score,
    compute_record_score,
    get_phone_spec_signature,
    listing_content_key,
    compute_listing_hash,
    extract_canonical_post_id,
    sanitize_filename,
    normalize_timestamp,
    normalize_and_convert_prices
)


class TestDedupUtils(unittest.TestCase):

    def test_is_ghost_record(self):
        self.assertTrue(is_ghost_record(None))
        self.assertTrue(is_ghost_record("not a dict"))
        self.assertTrue(is_ghost_record({}))
        self.assertTrue(is_ghost_record({"full_text": "short text"}))
        # Long text is not a ghost
        self.assertFalse(is_ghost_record({"full_text": "This is a sufficiently long text description of a home"}))
        # Short text with attributes is not a ghost
        self.assertFalse(is_ghost_record({"full_text": "Short", "prices": [{"amount": 1000}]}))
        self.assertFalse(is_ghost_record({"full_text": "Short", "rooms": [2]}))
        self.assertFalse(is_ghost_record({"full_text": "Short", "phone_numbers": ["099123456"]}))

    def test_is_valid_display_listing(self):
        self.assertFalse(is_valid_display_listing({}))
        self.assertFalse(is_valid_display_listing({
            "full_text": "Valid length listing text but no category",
            "property_category": ""
        }))
        self.assertFalse(is_valid_display_listing({
            "full_text": "Valid length listing text but unclassified",
            "property_category": "General / Unclassified"
        }))
        self.assertFalse(is_valid_display_listing({
            "full_text": "Valid length listing text but media only",
            "property_category": "Media-Only"
        }))
        self.assertTrue(is_valid_display_listing({
            "full_text": "Valid length listing text with apartment category",
            "property_category": "Apartment"
        }))

    def test_normalize_listing_text(self):
        self.assertEqual(normalize_listing_text(None), "")
        self.assertEqual(normalize_listing_text(""), "")
        text = "  Բարև, տեսեք https://example.com/item/123 !  Արժեքը 100$ ...  "
        norm = normalize_listing_text(text)
        self.assertNotIn("http", norm)
        self.assertIn("տեսեք", norm)
        self.assertIn("արժեքը", norm)
        self.assertNotIn("!", norm)

    def test_listing_completeness_score(self):
        self.assertEqual(listing_completeness_score(None), 0)
        self.assertEqual(listing_completeness_score({}), 0)
        full_item = {
            "full_text": "Description",
            "prices": [1],
            "sizes_sqm": [50],
            "rooms": [2],
            "locations": ["Kentron"],
            "phone_numbers": ["099"],
            "creation_timestamp": 123456
        }
        self.assertEqual(listing_completeness_score(full_item), 7)

    def test_compute_record_score(self):
        self.assertEqual(compute_record_score(None), 0.0)
        self.assertEqual(compute_record_score({}), 0.0)
        item = {
            "prices": [{"amount_amd": 1000}],
            "sizes_sqm": [60],
            "rooms": [2],
            "locations": ["Arabkir"],
            "phone_numbers": ["099"],
            "full_text": "A" * 100
        }
        # 3 + 2 + 2 + 2 + 3 + 1.0 = 13.0
        self.assertAlmostEqual(compute_record_score(item), 13.0)

    def test_get_phone_spec_signature(self):
        self.assertIsNone(get_phone_spec_signature(None))
        self.assertIsNone(get_phone_spec_signature({}))

        item_with_phone = {
            "phone_numbers": ["099123456"],
            "rooms": [2],
            "sizes_sqm": [55],
            "locations": ["Kentron"],
            "prices": [{"amount_amd": 20000000}]
        }
        sig = get_phone_spec_signature(item_with_phone)
        self.assertIsNotNone(sig)
        self.assertTrue(sig.startswith("phone_spec:"))
        self.assertIn("099123456", sig)

        item_fallback_text = {
            "full_text": "A very long detailed listing text without phone numbers to test fallback signature"
        }
        sig_text = get_phone_spec_signature(item_fallback_text)
        self.assertIsNotNone(sig_text)
        self.assertTrue(sig_text.startswith("text:"))

    def test_listing_content_key(self):
        short_item = {"full_text": "Short"}
        self.assertIsNone(listing_content_key(short_item))

        long_item = {
            "full_text": "This is a very long description text that easily exceeds eighty characters in total length for key generation.",
            "property_category": "House",
            "listing_type": "Sale"
        }
        key = listing_content_key(long_item)
        self.assertIsNotNone(key)
        self.assertIn("house", key.lower())
        self.assertIn("sale", key.lower())

    def test_compute_listing_hash(self):
        post1 = {"full_text": "Same text", "property_category": "Apartment", "listing_type": "Sale"}
        post2 = {"full_text": "Same text", "property_category": "Apartment", "listing_type": "Sale"}
        post3 = {"full_text": "Different text", "property_category": "Apartment", "listing_type": "Sale"}
        self.assertEqual(compute_listing_hash(post1), compute_listing_hash(post2))
        self.assertNotEqual(compute_listing_hash(post1), compute_listing_hash(post3))

    def test_extract_canonical_post_id(self):
        self.assertEqual(extract_canonical_post_id(None, post_id="999888"), "999888")
        self.assertEqual(extract_canonical_post_id("https://www.facebook.com/groups/123/posts/456789/"), "456789")
        self.assertEqual(extract_canonical_post_id("https://www.facebook.com/permalink.php?story_fbid=987654&id=321"), "987654")
        self.assertEqual(extract_canonical_post_id("https://www.list.am/item/11223344"), "11223344")
        self.assertIsNone(extract_canonical_post_id("https://example.com/no/id"))

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename(None), "unknown")
        self.assertEqual(sanitize_filename(""), "unknown")
        self.assertEqual(sanitize_filename("Hello World! 2026"), "hello_world_2026")

    def test_normalize_timestamp(self):
        # Direct epoch
        self.assertEqual(normalize_timestamp({"creation_timestamp": 1700000000}), 1700000000)
        # ISO string
        self.assertGreater(normalize_timestamp({"created_at": "2026-05-15T12:00:00Z"}), 0)
        # Date string
        self.assertGreater(normalize_timestamp({"created_at": "15.05.2026"}), 0)
        # Fallback to extracted_at
        self.assertGreater(normalize_timestamp({"extracted_at": "2026-05-15T14:30:00+00:00"}), 0)
        # Empty
        self.assertEqual(normalize_timestamp({}), 0)

    def test_normalize_and_convert_prices(self):
        self.assertEqual(normalize_and_convert_prices(None), [])
        self.assertEqual(normalize_and_convert_prices([]), [])

        prices = [
            {"amount": 1000, "currency": "USD"},
            {"amount": 364180, "currency": "AMD"},
            {"amount": "invalid"}  # Should be skipped
        ]
        res = normalize_and_convert_prices(prices, exchange_rate=364.18)
        self.assertEqual(len(res), 2)
        # USD to AMD
        self.assertEqual(res[0]["original_currency"], "USD")
        self.assertEqual(res[0]["amount_usd"], 1000)
        self.assertEqual(res[0]["amount_amd"], 364180)
        # AMD to USD
        self.assertEqual(res[1]["original_currency"], "AMD")
        self.assertEqual(res[1]["amount_amd"], 364180)
        self.assertEqual(res[1]["amount_usd"], 1000.0)


if __name__ == "__main__":
    unittest.main()
