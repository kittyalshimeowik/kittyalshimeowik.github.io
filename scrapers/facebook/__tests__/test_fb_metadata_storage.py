# scrapers/facebook/__tests__/test_fb_metadata_storage.py
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

from scrapers.facebook.utilities.fb_metadata_storage import (
    score_post_data,
    calculate_dynamic_runtime,
    load_target_groups,
    update_group_config_status,
    load_dataset_for_group,
    save_post_to_memory_and_disk,
    update_group_metadata,
    get_group_metadata_file_path,
    get_group_file_path
)


class TestFbMetadataStorage(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.meta_dir = os.path.join(self.test_dir, "metadata")
        self.out_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.meta_dir, exist_ok=True)
        os.makedirs(self.out_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. score_post_data
    # -------------------------------------------------------------------------

    def test_score_post_data_weights(self):
        # Empty post
        empty_score = score_post_data({})
        self.assertEqual(empty_score, 0)

        # Post with dates and details
        post = {
            "created_at": "2026-09-30T10:00:00",
            "creation_timestamp": 1790766000,
            "prices": [{"amount": 1000}],
            "sizes_sqm": [80],
            "rooms": [3],
            "locations": ["Kentron"],
            "phone_numbers": ["+374 77 000 000"],
            "property_category": "Apartment",
            "full_text": "A" * 200
        }
        # Expected: 10 (created_at) + 10 (creation_timestamp) + 5*5 (attributes) + 15 (Apartment) + 200/100 (text) = 62.0
        expected = 10 + 10 + 25 + 15 + 2.0
        self.assertEqual(score_post_data(post), expected)

    # -------------------------------------------------------------------------
    # 2. calculate_dynamic_runtime
    # -------------------------------------------------------------------------

    def test_calculate_dynamic_runtime_from_dict_and_fallback(self):
        # Fallback when empty
        dur, days = calculate_dynamic_runtime({}, default_runtime=120)
        self.assertEqual(dur, 120)

        # Average from benchmarks
        benchmarks = {
            "scroll_benchmarks": {
                "day1": {"scroll_duration_seconds": 60.0},
                "day2": {"scroll_duration_seconds": 120.0}
            }
        }
        dur, days = calculate_dynamic_runtime(benchmarks)
        self.assertEqual(dur, 90.0)

    def test_calculate_dynamic_runtime_clamping(self):
        # Clamps to min 45.0
        low_benchmarks = {
            "scroll_benchmarks": {
                "day1": {"scroll_duration_seconds": 10.0}
            }
        }
        dur, days = calculate_dynamic_runtime(low_benchmarks)
        self.assertEqual(dur, 45.0)

    # -------------------------------------------------------------------------
    # 3. load_target_groups and update_group_config_status
    # -------------------------------------------------------------------------

    def test_load_target_groups_missing_config_creates_default(self):
        config_path = os.path.join(self.test_dir, "groups.json")
        groups = load_target_groups(config_path, self.meta_dir)
        self.assertTrue(os.path.exists(config_path))
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["id"], "445452547795422")

    def test_update_group_config_status_records_counts(self):
        group_id = "test_group_1"
        update_group_config_status(self.meta_dir, group_id, 15)
        meta_file = get_group_metadata_file_path(self.meta_dir, group_id)
        self.assertTrue(os.path.exists(meta_file))

        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["total_collected"], 15)
        self.assertIn("last_scraped", data)

        # Increment again
        update_group_config_status(self.meta_dir, group_id, 10)
        with open(meta_file, "r", encoding="utf-8") as f:
            data2 = json.load(f)
        self.assertEqual(data2["total_collected"], 25)

    # -------------------------------------------------------------------------
    # 4. load_dataset_for_group and save_post_to_memory_and_disk
    # -------------------------------------------------------------------------

    def test_load_dataset_for_group_non_existent(self):
        posts, urls = load_dataset_for_group(self.out_dir, "non_existent_group")
        self.assertEqual(posts, [])
        self.assertEqual(urls, set())

    def test_save_post_new_and_update(self):
        group_id = "123456"
        all_posts = []
        processed_urls = set()

        post1 = {
            "url": "https://facebook.com/groups/123456/posts/100",
            "property_category": "Apartment",
            "prices": []
        }
        res1 = save_post_to_memory_and_disk(self.out_dir, group_id, all_posts, processed_urls, post1)
        self.assertEqual(res1, "new")
        self.assertEqual(len(all_posts), 1)

        # Attempt to save duplicate post with same or lower score
        res_dup = save_post_to_memory_and_disk(self.out_dir, group_id, all_posts, processed_urls, dict(post1))
        self.assertIsNone(res_dup)

        # Save duplicate post with higher score (richer details)
        richer_post = {
            "url": "https://facebook.com/groups/123456/posts/100",
            "property_category": "Apartment",
            "prices": [{"amount": 100000}],
            "sizes_sqm": [90],
            "locations": ["Kentron"]
        }
        res_update = save_post_to_memory_and_disk(self.out_dir, group_id, all_posts, processed_urls, richer_post)
        self.assertEqual(res_update, "updated")
        self.assertEqual(len(all_posts), 1)
        self.assertEqual(len(all_posts[0]["prices"]), 1)

    # -------------------------------------------------------------------------
    # 5. update_group_metadata
    # -------------------------------------------------------------------------

    def test_update_group_metadata_focus_and_benchmarks(self):
        group_id = "888888"
        group_name = "Yerevan Real Estate Hub"

        now_ts = datetime.now().timestamp()
        session_posts = [
            {
                "property_category": "Apartment",
                "listing_type": "Rent",
                "creation_timestamp": now_ts - 7200  # 2 hours ago
            },
            {
                "property_category": "Apartment",
                "listing_type": "Rent",
                "creation_timestamp": now_ts - 3600  # 1 hour ago
            },
            {
                "property_category": "House",
                "listing_type": "Sale",
                "creation_timestamp": now_ts - 10800 # 3 hours ago
            }
        ]

        update_group_metadata(self.meta_dir, group_id, group_name, session_posts, session_duration_sec=120)

        meta_file = get_group_metadata_file_path(self.meta_dir, group_id)
        self.assertTrue(os.path.exists(meta_file))

        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        self.assertEqual(metadata["name"], group_name)
        self.assertEqual(metadata["primary_focus"]["property_category"], "Apartment")
        self.assertEqual(metadata["primary_focus"]["listing_type"], "Rent")
        self.assertAlmostEqual(metadata["primary_focus"]["percentage"], 66.7, places=1)
        self.assertIn("Apartment", metadata["summary_title"])
        self.assertTrue(len(metadata["scroll_benchmarks"]) > 0)


if __name__ == "__main__":
    unittest.main()
