# scrapers/facebook/__tests__/test_backfill_fb_photos.py

import os
import sys
import unittest
import tempfile
import shutil
import time
from unittest.mock import MagicMock

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.storage import ListingsStorage
from scrapers.facebook.backfill_fb_photos import (
    get_fb_posts_to_backfill,
    find_chrome_executable,
    extract_post_photos_from_page
)


class TestBackfillFbPhotos(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_backfill.db")
        self.storage = ListingsStorage(self.db_path)

    def tearDown(self):
        self.storage.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_fb_posts_to_backfill_filters_correctly(self):
        # 1. Post needing backfill (Facebook, active, empty images)
        self.storage.upsert_listing({
            "canonical_id": "fb_need_backfill_1",
            "source": "Facebook",
            "url": "https://www.facebook.com/groups/1/posts/1",
            "property_category": "Apartment",
            "listing_type": "Sale",
            "images": [],
            "creation_timestamp": int(time.time())
        })

        # 2. Post already having images
        self.storage.upsert_listing({
            "canonical_id": "fb_has_images",
            "source": "Facebook",
            "url": "https://www.facebook.com/groups/1/posts/2",
            "property_category": "House",
            "listing_type": "Rent",
            "images": ["https://scontent.xx.fbcdn.net/v/photo.jpg"],
            "creation_timestamp": int(time.time())
        })

        # 3. List.am post (should be excluded)
        self.storage.upsert_listing({
            "canonical_id": "listam_post",
            "source": "List.am",
            "url": "https://www.list.am/item/3",
            "property_category": "Land",
            "listing_type": "Sale",
            "images": [],
            "creation_timestamp": int(time.time())
        })

        targets = get_fb_posts_to_backfill(self.storage, active_only=True)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["canonical_id"], "fb_need_backfill_1")

    def test_get_fb_posts_to_backfill_limit(self):
        for i in range(5):
            self.storage.upsert_listing({
                "canonical_id": f"fb_post_{i}",
                "source": "Facebook",
                "url": f"https://www.facebook.com/groups/1/posts/{i}",
                "property_category": "Apartment",
                "images": [],
                "creation_timestamp": int(time.time()) - i
            })

        targets = get_fb_posts_to_backfill(self.storage, active_only=True, limit=3)
        self.assertEqual(len(targets), 3)

    def test_extract_post_photos_from_page_mock(self):
        mock_page = MagicMock()
        mock_page.evaluate.return_value = [
            "https://scontent.xx.fbcdn.net/v/t39.30808-6/photo1.jpg",
            "https://scontent.xx.fbcdn.net/v/t39.30808-6/photo2.jpg"
        ]

        photos = extract_post_photos_from_page(mock_page, "123456", max_photos=5)
        self.assertEqual(len(photos), 2)
        self.assertEqual(photos[0], "https://scontent.xx.fbcdn.net/v/t39.30808-6/photo1.jpg")

    def test_is_valid_fb_photo_url_filters_external_previews_and_avatars(self):
        from scrapers.facebook.utilities.fb_utils import is_valid_fb_photo_url

        # Genuine user post photo
        self.assertTrue(is_valid_fb_photo_url("https://scontent-sjc6-1.xx.fbcdn.net/v/t39.30808-6/123_456_n.jpg"))

        # External OpenGraph article link previews (e.g. news photos of politicians)
        self.assertFalse(is_valid_fb_photo_url("https://scontent.xx.fbcdn.net/v/t39.99422-6/preview.jpg"))
        self.assertFalse(is_valid_fb_photo_url("https://external.xx.fbcdn.net/safe_image.php?d=AQ..."))

        # User profile avatars
        self.assertFalse(is_valid_fb_photo_url("https://scontent.xx.fbcdn.net/v/t39.30808-1/avatar.jpg"))
        self.assertFalse(is_valid_fb_photo_url("https://scontent.xx.fbcdn.net/v/t1.30497-1/avatar.jpg"))

        # Video reels thumbnails
        self.assertFalse(is_valid_fb_photo_url("https://scontent.xx.fbcdn.net/v/t15.5256-10/reel.jpg"))
        self.assertFalse(is_valid_fb_photo_url("https://scontent.xx.fbcdn.net/v/t39.25447-2/reel.jpg"))

        # Static assets / emojis
        self.assertFalse(is_valid_fb_photo_url("https://static.xx.fbcdn.net/rsrc.php/v3/y1/r/icon.png"))
        self.assertFalse(is_valid_fb_photo_url("https://static.xx.fbcdn.net/images/emoji.php/v9/t51/1/16/smile.png"))

    def test_extract_photo_signature_unifies_cdn_hosts(self):
        from scrapers.processors.clean_stray_photos import extract_photo_signature

        url_sjc = "https://scontent-sjc6-1.xx.fbcdn.net/v/t39.30808-6/840663935_10246288876459731_7503090554602015664_n.jpg?stp=dst-jpg"
        url_iad = "https://scontent-iad3-2.xx.fbcdn.net/v/t39.30808-6/840663935_10246288876459731_7503090554602015664_n.jpg?stp=dst-jpg&oh=123"

        self.assertEqual(extract_photo_signature(url_sjc), "840663935_10246288876459731_7503090554602015664_n.jpg")
        self.assertEqual(extract_photo_signature(url_sjc), extract_photo_signature(url_iad))


if __name__ == "__main__":
    unittest.main()
