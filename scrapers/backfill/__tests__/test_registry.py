# scrapers/backfill/__tests__/test_registry.py

import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.backfill.base import BasePlatformBackfiller
from scrapers.backfill.registry import (
    get_platform_backfiller,
    get_all_platform_backfillers,
    list_supported_platforms,
    register_platform_backfiller
)


class DummyCustomBackfiller(BasePlatformBackfiller):
    @property
    def platform_name(self) -> str:
        return "Telegram"

    def get_pending_photos_count(self, storage, active_only: bool = True) -> int:
        return 0

    def get_pending_translations_count(self, storage, active_only: bool = True) -> int:
        return 0

    def backfill_photos(self, storage, limit=None, headless=True, active_only=True):
        return {"processed": 0, "photos_found": 0}


class TestBackfillRegistry(unittest.TestCase):

    def test_default_platforms_registered(self):
        platforms = list_supported_platforms()
        self.assertIn("facebook", platforms)
        self.assertIn("listam", platforms)

    def test_get_platform_backfiller(self):
        fb = get_platform_backfiller("facebook")
        self.assertIsNotNone(fb)
        self.assertEqual(fb.platform_name, "Facebook")

        listam = get_platform_backfiller("listam")
        self.assertIsNotNone(listam)
        self.assertEqual(listam.platform_name, "List.am")

    def test_extensibility_register_new_platform(self):
        register_platform_backfiller("telegram", DummyCustomBackfiller())
        tg = get_platform_backfiller("telegram")
        self.assertIsNotNone(tg)
        self.assertEqual(tg.platform_name, "Telegram")
        self.assertIn("telegram", list_supported_platforms())


if __name__ == "__main__":
    unittest.main()
