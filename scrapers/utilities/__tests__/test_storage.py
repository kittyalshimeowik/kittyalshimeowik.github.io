# scrapers/utilities/__tests__/test_storage.py
import os
import sys
import tempfile
import shutil
import unittest
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.storage import ListingsStorage, compute_record_completeness


class TestListingsStorage(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_listings.db")
        self.storage = ListingsStorage(self.db_path)

    def tearDown(self):
        self.storage.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_upsert_single_listing(self):
        record = {
            "canonical_id": "test_post_1",
            "source": "Facebook",
            "url": "https://facebook.com/groups/123/posts/1",
            "property_category": "Apartment",
            "listing_type": "Sale",
            "full_text": "Sunny 2-room apartment in Arabkir",
            "prices": [{"amount_usd": 65000}],
            "sizes_sqm": [60],
            "rooms": [2],
            "locations": ["Arabkir"],
            "phone_numbers": ["+374 91 112233"],
            "creation_timestamp": int(time.time())
        }

        action = self.storage.upsert_listing(record)
        self.assertEqual(action, "inserted")
        self.assertEqual(self.storage.count_listings(), 1)

        listings = self.storage.get_all_listings()
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0]["canonical_id"], "test_post_1")
        self.assertEqual(listings[0]["property_category"], "Apartment")
        self.assertEqual(listings[0]["rooms"], [2])
        self.assertEqual(listings[0]["prices"], [{"amount_usd": 65000}])

    def test_upsert_enhances_existing_record_with_richer_data(self):
        # 1. Insert minimal record
        record_basic = {
            "canonical_id": "item_100",
            "source": "List.am",
            "url": "https://list.am/item/100",
            "property_category": "Apartment",
            "full_text": "Short desc",
            "creation_timestamp": int(time.time())
        }
        self.storage.upsert_listing(record_basic)

        # 2. Update with richer metadata
        record_rich = {
            "canonical_id": "item_100",
            "source": "List.am",
            "url": "https://list.am/item/100",
            "property_category": "Apartment",
            "listing_type": "Sale",
            "full_text": "Detailed description with lots of information",
            "prices": [{"amount_usd": 85000}],
            "rooms": [3],
            "sizes_sqm": [75],
            "locations": ["Kentron"],
            "phone_numbers": ["+374 77 123456"],
            "creation_timestamp": int(time.time())
        }
        action = self.storage.upsert_listing(record_rich)
        self.assertEqual(action, "updated")

        listings = self.storage.get_all_listings()
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0]["rooms"], [3])
        self.assertEqual(listings[0]["locations"], ["Kentron"])

    def test_batch_upsert(self):
        batch = [
            {
                "canonical_id": f"batch_{i}",
                "source": "Facebook",
                "url": f"https://fb.com/{i}",
                "property_category": "House",
                "listing_type": "Sale",
                "prices": [{"amount_usd": 120000 + i}],
                "creation_timestamp": int(time.time())
            }
            for i in range(10)
        ]
        result = self.storage.batch_upsert_listings(batch)
        self.assertEqual(result["inserted"], 10)
        self.assertEqual(self.storage.count_listings(), 10)

    def test_prune_stale_listings_ttl(self):
        now = int(time.time())
        old_ts = now - (90 * 86400) # 90 days ago
        fresh_ts = now - (5 * 86400) # 5 days ago

        old_record = {
            "canonical_id": "old_listing",
            "source": "List.am",
            "url": "https://list.am/old",
            "creation_timestamp": old_ts
        }
        fresh_record = {
            "canonical_id": "fresh_listing",
            "source": "List.am",
            "url": "https://list.am/fresh",
            "creation_timestamp": fresh_ts
        }

        self.storage.upsert_listing(old_record)
        self.storage.upsert_listing(fresh_record)

        self.assertEqual(self.storage.count_listings(active_only=True), 2)

        # Prune listings older than 60 days
        pruned_count = self.storage.prune_stale_listings(max_age_days=60)
        self.assertEqual(pruned_count, 1)
        self.assertEqual(self.storage.count_listings(active_only=True), 1)

        active = self.storage.get_all_listings(active_only=True)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["canonical_id"], "fresh_listing")

    def test_completeness_scoring(self):
        score_low = compute_record_completeness({})
        score_high = compute_record_completeness({
            "created_at": "2026-10-01",
            "creation_timestamp": 1234567,
            "prices": [1],
            "sizes_sqm": [50],
            "rooms": [2],
            "locations": ["Yerevan"],
            "phone_numbers": ["123"],
            "images": ["https://s.list.am/g/1/1.jpg"],
            "property_category": "Apartment",
            "full_text": "Good apartment"
        })
        self.assertGreater(score_high, score_low)

    def test_upsert_and_retrieve_with_images(self):
        record = {
            "canonical_id": "photo_listing_1",
            "source": "List.am",
            "url": "https://list.am/item/9999",
            "property_category": "Apartment",
            "images": [
                "https://s.list.am/g/123/456.jpg",
                "https://s.list.am/g/123/457.jpg"
            ],
            "creation_timestamp": int(time.time())
        }
        self.storage.upsert_listing(record)
        listings = self.storage.get_all_listings()
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0]["images"], [
            "https://s.list.am/g/123/456.jpg",
            "https://s.list.am/g/123/457.jpg"
        ])


if __name__ == "__main__":
    unittest.main()
