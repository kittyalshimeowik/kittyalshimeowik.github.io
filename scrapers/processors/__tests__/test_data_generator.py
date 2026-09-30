import os
import sys
import json
import shutil
import tempfile
import unittest
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.processors.generate_site_data import (
    normalize_and_convert_prices,
    extract_canonical_post_id,
    normalize_listing_text,
    merge_duplicate_listings,
    sanitize_filename,
    normalize_timestamp,
    get_phone_spec_signature,
    listing_completeness_score,
    listing_content_key,
    prune_for_display,
    compute_listing_hash,
    categorize_and_save_master_files,
    MASTER_OUTPUT_DIR,
    LOC_SUMMARY_DIR
)


class TestDataGenerator(unittest.TestCase):

    # -------------------------------------------------------------------------
    # 1. Price conversion & sanitization tests
    # -------------------------------------------------------------------------

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

    def test_price_conversion_boundary_zero_and_negative(self):
        prices_zero = [{"amount": 0, "currency": "USD"}]
        converted_zero = normalize_and_convert_prices(prices_zero)
        self.assertEqual(converted_zero[0]["amount_usd"], 0)
        self.assertEqual(converted_zero[0]["amount_amd"], 0)

        prices_invalid = [{"amount": "N/A", "currency": "USD"}]
        converted_invalid = normalize_and_convert_prices(prices_invalid)
        self.assertEqual(len(converted_invalid), 0)

    def test_sanitize_filename_special_characters(self):
        raw_location = "Kentron / Yerevan #1!"
        clean_location = sanitize_filename(raw_location)
        self.assertEqual(clean_location, "kentron_yerevan_1")

        self.assertEqual(sanitize_filename(""), "unknown")
        self.assertEqual(sanitize_filename(None), "unknown")

    # -------------------------------------------------------------------------
    # 2. normalize_timestamp tests
    # -------------------------------------------------------------------------

    def test_normalize_timestamp_from_integer_or_float(self):
        post_int = {"creation_timestamp": 1790766000}
        self.assertEqual(normalize_timestamp(post_int), 1790766000)

        post_float = {"creation_timestamp": 1790766000.5}
        self.assertEqual(normalize_timestamp(post_float), 1790766000)

    def test_normalize_timestamp_from_iso_string(self):
        post_iso = {"created_at": "2026-09-30T12:00:00Z"}
        ts = normalize_timestamp(post_iso)
        self.assertGreater(ts, 1700000000)

        post_space = {"created_at": "2026-09-30 12:00:00"}
        ts_space = normalize_timestamp(post_space)
        self.assertGreater(ts_space, 1700000000)

    def test_normalize_timestamp_from_date_format(self):
        post_date = {"created_at": "30.09.2026"}
        ts = normalize_timestamp(post_date)
        self.assertGreater(ts, 1700000000)

    def test_normalize_timestamp_fallback_and_invalid(self):
        post_ext = {"extracted_at": "2026-09-30T10:00:00Z"}
        self.assertGreater(normalize_timestamp(post_ext), 1700000000)

        self.assertEqual(normalize_timestamp({}), 0)
        self.assertEqual(normalize_timestamp({"created_at": "invalid_date_format"}), 0)

    # -------------------------------------------------------------------------
    # 3. get_phone_spec_signature tests
    # -------------------------------------------------------------------------

    def test_get_phone_spec_signature_matches_and_differentiates(self):
        post1 = {
            "phone_numbers": ["+374 77 111 222"],
            "prices": [{"amount_amd": 50000000}],
            "sizes_sqm": [80],
            "rooms": [3],
            "locations": ["Kentron"]
        }
        post2 = {
            "phone_numbers": ["+374 77 111 222"],
            "prices": [{"amount_amd": 50000000}],
            "sizes_sqm": [80],
            "rooms": [3],
            "locations": ["Kentron"]
        }
        sig1 = get_phone_spec_signature(post1)
        sig2 = get_phone_spec_signature(post2)
        self.assertIsNotNone(sig1)
        self.assertEqual(sig1, sig2)

        # Different phone
        post3 = dict(post1, phone_numbers=["+374 99 999 999"])
        self.assertNotEqual(sig1, get_phone_spec_signature(post3))

        # Missing phone or specs
        self.assertIsNone(get_phone_spec_signature({}))
        self.assertIsNone(get_phone_spec_signature({"phone_numbers": ["+374 77 111 222"]}))

    # -------------------------------------------------------------------------
    # 4. listing_completeness_score & listing_content_key
    # -------------------------------------------------------------------------

    def test_listing_completeness_score_counts(self):
        self.assertEqual(listing_completeness_score({}), 0)
        full_post = {
            "full_text": "Sample",
            "prices": [1],
            "sizes_sqm": [1],
            "rooms": [1],
            "locations": [1],
            "phone_numbers": [1],
            "creation_timestamp": 12345
        }
        self.assertEqual(listing_completeness_score(full_post), 7)

    def test_listing_content_key_threshold(self):
        # Short text < 80 chars
        self.assertIsNone(listing_content_key({"full_text": "Short text"}))

        # Long text >= 80 chars
        long_post = {
            "full_text": "This is a long description about a real estate property for sale in central Yerevan Armenia." * 2,
            "property_category": "Apartment",
            "listing_type": "Sale"
        }
        key = listing_content_key(long_post)
        self.assertIsNotNone(key)
        self.assertIn("Apartment", key)
        self.assertIn("Sale", key)

    # -------------------------------------------------------------------------
    # 5. prune_for_display tests
    # -------------------------------------------------------------------------

    def test_prune_for_display_field_retention_and_truncation(self):
        heavy_post = {
            "url": "https://example.com/post/1",
            "canonical_id": "item_1",
            "source": "List.am",
            "property_category": "Apartment",
            "listing_type": "Sale",
            "prices": [{"amount_usd": 100000}],
            "sizes_sqm": [90],
            "rooms": [3],
            "locations": ["Kentron"],
            "phone_numbers": ["+374 77 000 000"],
            "created_at": "2026-09-30",
            "creation_timestamp": 1790766000,
            "raw_node": {"heavy": "data"},
            "is_media_only": False,
            "has_text": True,
            "floor_info": {"floor": 3},
            "full_text": "X" * 600  # Over 500 characters
        }

        pruned = prune_for_display(heavy_post)

        # Unused heavy fields must be stripped
        self.assertNotIn("raw_node", pruned)
        self.assertNotIn("is_media_only", pruned)
        self.assertNotIn("has_text", pruned)
        self.assertNotIn("floor_info", pruned)

        # Essential fields retained
        self.assertEqual(pruned["source"], "List.am")
        self.assertEqual(pruned["canonical_id"], "item_1")
        self.assertEqual(pruned["creation_timestamp"], 1790766000)

        # Text truncated to 500 characters with "..."
        self.assertEqual(len(pruned["full_text"]), 500)
        self.assertTrue(pruned["full_text"].endswith("..."))

    # -------------------------------------------------------------------------
    # 6. compute_listing_hash test
    # -------------------------------------------------------------------------

    def test_compute_listing_hash(self):
        post = {"full_text": "Test listing", "property_category": "House", "listing_type": "Sale"}
        h1 = compute_listing_hash(post)
        h2 = compute_listing_hash(post)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 32)  # MD5 hex digest length

    # -------------------------------------------------------------------------
    # 7. Fuzzy deduplication completeness
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # 8. Master files generation tests
    # -------------------------------------------------------------------------

    def test_categorize_and_save_master_files_filters_ghosts_and_unclassified(self):
        temp_dir = tempfile.mkdtemp()
        try:
            import scrapers.processors.generate_site_data as gsd
            original_dir = gsd.MASTER_OUTPUT_DIR
            original_loc_dir = gsd.LOC_SUMMARY_DIR
            gsd.MASTER_OUTPUT_DIR = temp_dir
            gsd.LOC_SUMMARY_DIR = os.path.join(temp_dir, "by_location")

            posts = [
                {"canonical_id": "ghost_1", "full_text": "", "property_category": "General / Unclassified", "listing_type": "Sale"},
                {"canonical_id": "unc_1", "full_text": "Long enough text about an unclassified post without category", "property_category": "General / Unclassified", "listing_type": "Sale"},
                {"canonical_id": "media_1", "full_text": "Long enough text", "property_category": "Media-Only", "listing_type": "Sale"},
                {
                    "canonical_id": "valid_1",
                    "full_text": "Վաճառվում է բնակարան Երևանում շատ լավ վիճակում",
                    "property_category": "Apartment",
                    "listing_type": "Sale",
                    "prices": [{"amount_usd": 80000, "amount_amd": 29000000}],
                    "locations": ["Kentron"]
                }
            ]

            categorize_and_save_master_files(posts)

            all_path = os.path.join(temp_dir, "all_for_sale_rent.json")
            self.assertTrue(os.path.exists(all_path))
            with open(all_path, "r", encoding="utf-8") as f:
                all_data = json.load(f)

            # Only valid_1 should be in all_for_sale_rent.json
            self.assertEqual(len(all_data), 1)
            self.assertEqual(all_data[0]["canonical_id"], "valid_1")

            # by_location directory should not exist
            self.assertFalse(os.path.exists(os.path.join(temp_dir, "by_location")))
        finally:
            gsd.MASTER_OUTPUT_DIR = original_dir
            gsd.LOC_SUMMARY_DIR = original_loc_dir
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()