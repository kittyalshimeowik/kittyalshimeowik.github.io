# scrapers/platforms/__tests__/test_platforms_registry.py

import unittest
from scrapers.platforms.base import BasePlatform
from scrapers.platforms.registry import (
    register_platform,
    get_platform,
    get_platform_for_url,
    list_supported_platforms,
    get_all_platforms
)
from scrapers.processors.dedup_utils import (
    is_valid_listing_url,
    extract_canonical_post_id
)


class MockTelegramPlatform(BasePlatform):
    @property
    def key(self) -> str:
        return "mock_telegram"

    @property
    def display_name(self) -> str:
        return "Telegram"

    @property
    def source_aliases(self):
        return ["Telegram", "tg"]

    @property
    def url_domains(self):
        return ["t.me", "telegram.me"]


class TestPlatformsRegistry(unittest.TestCase):
    def test_default_platforms_registered(self):
        platforms = list_supported_platforms()
        self.assertIn("facebook", platforms)
        self.assertIn("listam", platforms)

    def test_get_platform_by_key_and_alias(self):
        self.assertIsNotNone(get_platform("facebook"))
        self.assertIsNotNone(get_platform("fb"))
        self.assertIsNotNone(get_platform("Facebook"))

        self.assertIsNotNone(get_platform("listam"))
        self.assertIsNotNone(get_platform("List.am"))

    def test_get_platform_for_url(self):
        fb_plat = get_platform_for_url("https://www.facebook.com/groups/123/posts/456")
        self.assertIsNotNone(fb_plat)
        self.assertEqual(fb_plat.key, "facebook")

        listam_plat = get_platform_for_url("https://www.list.am/item/19543210")
        self.assertIsNotNone(listam_plat)
        self.assertEqual(listam_plat.key, "listam")

    def test_dynamic_platform_registration(self):
        mock_tg = MockTelegramPlatform()
        register_platform(mock_tg)
        
        self.assertIn("mock_telegram", list_supported_platforms())
        found = get_platform("tg")
        self.assertIsNotNone(found)
        self.assertEqual(found.display_name, "Telegram")

    def test_generic_url_validation(self):
        # List.am valid vs invalid
        self.assertTrue(is_valid_listing_url("https://www.list.am/item/1234567"))
        self.assertFalse(is_valid_listing_url("https://www.list.am/category/56"))

        # Facebook valid vs invalid
        self.assertTrue(is_valid_listing_url("https://www.facebook.com/groups/123/posts/456"))
        self.assertFalse(is_valid_listing_url("https://www.facebook.com/"))

        # Generic / Future platforms
        self.assertTrue(is_valid_listing_url("https://estate.am/property/98765"))
        self.assertTrue(is_valid_listing_url("https://t.me/yerevan_rent/54321"))
        self.assertFalse(is_valid_listing_url("http://example.com/item/123"))
        self.assertFalse(is_valid_listing_url("not_a_url"))

    def test_generic_canonical_id_extraction(self):
        # List.am item ID
        self.assertEqual(extract_canonical_post_id("https://www.list.am/item/19543210"), "19543210")

        # Facebook post ID
        self.assertEqual(extract_canonical_post_id("https://www.facebook.com/groups/123/posts/99887766"), "99887766")

        # Telegram message ID
        self.assertEqual(extract_canonical_post_id("https://t.me/yerevan_rent/12345"), "12345")

        # Generic property path
        self.assertEqual(extract_canonical_post_id("https://estate.am/property/554433"), "554433")

        # Query param ID
        self.assertEqual(extract_canonical_post_id("https://somerealty.am/view?id=778899"), "778899")

        # Trailing numeric ID
        self.assertEqual(extract_canonical_post_id("https://arbitrarysite.com/listings/123456.html"), "123456")

        # No ID returns None
        self.assertIsNone(extract_canonical_post_id("https://arbitrarysite.com/luxury-villa-ararat"))


if __name__ == "__main__":
    unittest.main()
