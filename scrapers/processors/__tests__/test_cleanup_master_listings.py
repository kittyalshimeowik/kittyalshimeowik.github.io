# scrapers/processors/__tests__/test_cleanup_master_listings.py
import os
import sys
import json
import shutil
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.processors.cleanup_master_listings import (
    compute_record_score,
    normalize_text,
    get_content_signature,
    deduplicate_records,
    run_cleanup
)


class TestCleanupMasterListings(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. compute_record_score
    # -------------------------------------------------------------------------

    def test_compute_record_score_weights(self):
        empty_item = {}
        self.assertEqual(compute_record_score(empty_item), 0.0)

        item = {
            "prices": [{"amount_amd": 50000000}],  # +3
            "sizes_sqm": [75],                     # +2
            "rooms": [3],                          # +2
            "locations": ["Kentron"],              # +2
            "phone_numbers": ["+374 77 123 456"],  # +3
            "full_text": "A" * 150                 # +1.5
        }
        self.assertEqual(compute_record_score(item), 3 + 2 + 2 + 2 + 3 + 1.5)

    # -------------------------------------------------------------------------
    # 2. normalize_text
    # -------------------------------------------------------------------------

    def test_normalize_text(self):
        self.assertEqual(normalize_text(None), "")
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(
            normalize_text("  ԲԱՐԵՎ   ձեզ   \n աշխարհ   "),
            "բարեվ ձեզ աշխարհ"
        )

    # -------------------------------------------------------------------------
    # 3. get_content_signature
    # -------------------------------------------------------------------------

    def test_get_content_signature_phone_and_specs(self):
        item = {
            "phone_numbers": ["+374 77 123 456"],
            "prices": [{"amount_amd": 40000000}],
            "sizes_sqm": [60],
            "rooms": [2],
            "locations": ["Arabkir"],
            "full_text": "Short"
        }
        sig = get_content_signature(item)
        self.assertIsNotNone(sig)
        self.assertTrue(sig.startswith("phone_spec:"))
        self.assertIn("+374 77 123 456", sig)
        self.assertIn("40000000", sig)

    def test_get_content_signature_text_match_fallback(self):
        item = {
            "full_text": "Վաճառվում է բնակարան Երևանի կենտրոնում, շատ լավ վիճակում:"
        }
        sig = get_content_signature(item)
        self.assertIsNotNone(sig)
        self.assertTrue(sig.startswith("text:"))

    def test_get_content_signature_none_for_short_or_empty(self):
        self.assertIsNone(get_content_signature({}))
        self.assertIsNone(get_content_signature({"full_text": "Short"}))

    # -------------------------------------------------------------------------
    # 4. deduplicate_records
    # -------------------------------------------------------------------------

    def test_deduplicate_records_merges_and_keeps_highest_score(self):
        post_low = {
            "id": 1,
            "phone_numbers": ["+374 91 000 000"],
            "rooms": [2],
            "sizes_sqm": [65],
            "locations": ["Kentron"],
            "prices": [{"amount_amd": 20000000}],
            "full_text": "A" * 30
        }
        post_high = {
            "id": 2,
            "phone_numbers": ["+374 91 000 000"],
            "rooms": [2],
            "sizes_sqm": [65],
            "locations": ["Kentron"],
            "prices": [{"amount_amd": 20000000}],
            "full_text": "A" * 150
        }

        listings = [post_low, post_high]
        cleaned = deduplicate_records(listings)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]["id"], 2)

    def test_deduplicate_records_preserves_unmatched(self):
        unmatched_1 = {"id": "unmatched_1", "full_text": "Valid unmatched listing description 1"}
        unmatched_2 = {"id": "unmatched_2", "full_text": "Valid unmatched listing description 2"}
        cleaned = deduplicate_records([unmatched_1, unmatched_2])
        self.assertEqual(len(cleaned), 2)

    def test_deduplicate_records_drops_ghost_records(self):
        ghost_post_1 = {"id": "ghost_1", "full_text": ""}
        ghost_post_2 = {"id": "ghost_2", "full_text": "Short", "property_category": "General / Unclassified"}
        valid_post = {
            "id": "valid_1",
            "full_text": "Valid apartment listing in Kentron center with description",
            "property_category": "Apartment",
            "prices": [{"amount_amd": 25000000}]
        }
        cleaned = deduplicate_records([ghost_post_1, ghost_post_2, valid_post])
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]["id"], "valid_1")

    def test_deduplicate_records_filters_unclassified(self):
        unclassified = {
            "id": "unc_1",
            "full_text": "Some text that is long enough to pass length check",
            "property_category": "General / Unclassified"
        }
        apartment = {
            "id": "apt_1",
            "full_text": "Some text that is long enough for an apartment",
            "property_category": "Apartment"
        }
        cleaned = deduplicate_records([unclassified, apartment], filter_unclassified=True)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]["id"], "apt_1")

    # -------------------------------------------------------------------------
    # 5. run_cleanup end-to-end
    # -------------------------------------------------------------------------

    def test_run_cleanup_file_flow(self):
        target_file = os.path.join(self.test_dir, "listings.json")
        out_file = os.path.join(self.test_dir, "cleaned.json")
        meta_file = os.path.join(self.test_dir, "meta.json")

        initial_data = [
            {"id": "a1", "phone_numbers": ["+374 99 111 222"], "rooms": [1], "sizes_sqm": [45], "full_text": "Text 1"},
            {"id": "a2", "phone_numbers": ["+374 99 111 222"], "rooms": [1], "sizes_sqm": [45], "full_text": "Text 1 longer text here"},
            {"id": "b1", "phone_numbers": ["+374 99 333 444"], "rooms": [3], "sizes_sqm": [90], "full_text": "Text 2"}
        ]
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({"total_listings_count": 3}, f)

        run_cleanup(filepath=target_file, output_filepath=out_file)

        self.assertTrue(os.path.exists(out_file))
        with open(out_file, "r", encoding="utf-8") as f:
            cleaned_data = json.load(f)
        self.assertEqual(len(cleaned_data), 2)

        with open(meta_file, "r", encoding="utf-8") as f:
            meta_data = json.load(f)
        self.assertEqual(meta_data["total_listings_count"], 2)


if __name__ == "__main__":
    unittest.main()
