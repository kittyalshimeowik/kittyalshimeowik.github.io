# scrapers/utilities/__tests__/test_backfill_translations.py

import os
import sys
import unittest
import tempfile
import shutil
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.storage import ListingsStorage
from scrapers.utilities.backfill_translations import get_listings_missing_translation


class TestBackfillTranslations(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_trans_backfill.db")
        self.storage = ListingsStorage(self.db_path)

    def tearDown(self):
        self.storage.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_listings_missing_translation_filters(self):
        # 1. Missing translation with valid text
        self.storage.upsert_listing({
            "canonical_id": "item_needs_trans",
            "source": "Facebook",
            "url": "https://facebook.com/1",
            "full_text": "Վաճառվում է բնակարան Երևանում",
            "full_text_en": None,
            "creation_timestamp": int(time.time())
        })

        # 2. Already translated
        self.storage.upsert_listing({
            "canonical_id": "item_already_translated",
            "source": "Facebook",
            "url": "https://facebook.com/2",
            "full_text": "Վաճառվում է բնակարան",
            "full_text_en": "Apartment for sale in Yerevan",
            "creation_timestamp": int(time.time())
        })

        # 3. Empty text (should be excluded)
        self.storage.upsert_listing({
            "canonical_id": "item_empty_text",
            "source": "Facebook",
            "url": "https://facebook.com/3",
            "full_text": "",
            "full_text_en": None,
            "creation_timestamp": int(time.time())
        })

        targets = get_listings_missing_translation(self.storage, active_only=True)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["canonical_id"], "item_needs_trans")

    def test_get_listings_missing_translation_by_source(self):
        self.storage.upsert_listing({
            "canonical_id": "fb_1",
            "source": "Facebook",
            "url": "https://facebook.com/1",
            "full_text": "Վաճառվում է հողատարածք",
            "full_text_en": None,
            "creation_timestamp": int(time.time())
        })
        self.storage.upsert_listing({
            "canonical_id": "listam_1",
            "source": "List.am",
            "url": "https://list.am/1",
            "full_text": "Վաճառվում է ավտոտնակ",
            "full_text_en": None,
            "creation_timestamp": int(time.time())
        })

        fb_targets = get_listings_missing_translation(self.storage, source="Facebook")
        self.assertEqual(len(fb_targets), 1)
        self.assertEqual(fb_targets[0]["canonical_id"], "fb_1")

        listam_targets = get_listings_missing_translation(self.storage, source="List.am")
        self.assertEqual(len(listam_targets), 1)
        self.assertEqual(listam_targets[0]["canonical_id"], "listam_1")


if __name__ == "__main__":
    unittest.main()
