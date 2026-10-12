"""
Unit tests for the translator module (scrapers/utilities/translator.py).
Tests caching, English detection, hashing, batch translation, and listing enrichment.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.translator import (
    text_hash,
    is_already_english,
    TranslationCache,
    translate_single_text,
    batch_translate_texts,
    enrich_listings_with_translations
)


class TestTranslatorModule(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.test_dir, "test_cache.json")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_text_hash_consistency(self):
        text1 = "Վաճառվում է բնակարան"
        text2 = "  Վաճառվում է բնակարան  "
        self.assertEqual(text_hash(text1), text_hash(text2))
        self.assertEqual(len(text_hash(text1)), 32)
        self.assertNotEqual(text_hash(text1), text_hash("Different text"))

    def test_is_already_english(self):
        self.assertTrue(is_already_english("For sale 3-room apartment in Arabkir"))
        self.assertTrue(is_already_english("Luxury villa with pool and garden, $250,000"))
        self.assertTrue(is_already_english(""))
        self.assertTrue(is_already_english(None))

        # Armenian text
        self.assertFalse(is_already_english("Վաճառվում է 3 սենյականոց բնակարան"))
        # Russian text
        self.assertFalse(is_already_english("Продаётся квартира в центре Еревана"))
        # Mixed with Armenian
        self.assertFalse(is_already_english("For sale բնակարան in Yerevan"))

    def test_translation_cache_crud(self):
        cache = TranslationCache(self.cache_file)
        self.assertEqual(len(cache), 0)

        # Set and get
        sample_text = "Վաճառվում է տուն"
        sample_trans = "House for sale"
        cache.set(sample_text, sample_trans)
        self.assertEqual(cache.get(sample_text), sample_trans)
        self.assertIsNone(cache.get("Non-existent text"))

        # Save to disk and reload
        cache.save()
        self.assertTrue(os.path.exists(self.cache_file))

        loaded_cache = TranslationCache(self.cache_file)
        self.assertEqual(len(loaded_cache), 1)
        self.assertEqual(loaded_cache.get(sample_text), sample_trans)

    def test_translate_single_text_already_english(self):
        cache = TranslationCache(self.cache_file)
        eng_text = "Beautiful apartment for rent in Center"
        res = translate_single_text(eng_text, cache=cache)
        self.assertEqual(res, eng_text)

    def test_translate_single_text_cached(self):
        cache = TranslationCache(self.cache_file)
        orig = "Վաճառվում է հողատարածք"
        trans = "Land for sale"
        cache.set(orig, trans)

        # Should return cached without network call
        with patch("scrapers.utilities.translator._request_google_translate") as mock_api:
            res = translate_single_text(orig, cache=cache)
            self.assertEqual(res, trans)
            mock_api.assert_not_called()

    @patch("scrapers.utilities.translator._request_google_translate")
    def test_translate_single_text_api_call(self, mock_api):
        mock_api.return_value = "Cozy apartment for rent"
        cache = TranslationCache(self.cache_file)
        orig = "Վարձով է տրվում հարմարավետ բնակարան"

        res = translate_single_text(orig, cache=cache)
        self.assertEqual(res, "Cozy apartment for rent")
        self.assertEqual(cache.get(orig), "Cozy apartment for rent")

    @patch("scrapers.utilities.translator._request_google_translate")
    def test_batch_translate_texts(self, mock_api):
        mock_api.return_value = "Apartment 1\n===__DELIM__===\nApartment 2"
        cache = TranslationCache(self.cache_file)
        texts = [
            "Բնակարան 1",
            "Բնակարան 2"
        ]

        results = batch_translate_texts(texts, cache=cache, batch_size=5)
        self.assertEqual(results, ["Apartment 1", "Apartment 2"])
        self.assertEqual(cache.get("Բնակարան 1"), "Apartment 1")
        self.assertEqual(cache.get("Բնակարան 2"), "Apartment 2")

    @patch("scrapers.utilities.translator._request_google_translate")
    def test_enrich_listings_with_translations(self, mock_api):
        mock_api.return_value = "Nice house for sale"
        cache = TranslationCache(self.cache_file)

        listings = [
            {"full_text": "Վաճառվում է գեղեցիկ տուն", "full_text_en": None},
            {"full_text": "Already English house", "full_text_en": None},
            {"full_text": "Another post", "full_text_en": "Pre-existing translation"}
        ]

        enriched = enrich_listings_with_translations(listings, cache=cache, show_progress=False)

        self.assertEqual(enriched[0]["full_text_en"], "Nice house for sale")
        self.assertEqual(enriched[1]["full_text_en"], "Already English house")
        self.assertEqual(enriched[2]["full_text_en"], "Pre-existing translation")


if __name__ == "__main__":
    unittest.main()
