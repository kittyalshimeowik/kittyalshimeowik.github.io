# scrapers/facebook/__tests__/test_fb_utils.py
import os
import sys
import base64
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.facebook.utilities.fb_utils import (
    extract_canonical_post_id,
    normalize_url,
    extract_post_id,
    decode_facebook_id
)


class TestFbUtils(unittest.TestCase):

    # -------------------------------------------------------------------------
    # 1. extract_canonical_post_id
    # -------------------------------------------------------------------------

    def test_extract_canonical_post_id_with_direct_id(self):
        self.assertEqual(extract_canonical_post_id("https://facebook.com", post_id=123456), "123456")
        self.assertEqual(extract_canonical_post_id(None, post_id="789012"), "789012")

    def test_extract_canonical_post_id_from_url_paths(self):
        url_posts = "https://www.facebook.com/groups/yerevanhousing/posts/10158493029104820/"
        url_permalink = "https://www.facebook.com/groups/12345/permalink/987654321/"
        url_multi = "https://www.facebook.com/groups/12345/multi_permalink/1122334455/"
        url_story = "https://www.facebook.com/groups/12345/story.php/9988776655/"

        self.assertEqual(extract_canonical_post_id(url_posts), "10158493029104820")
        self.assertEqual(extract_canonical_post_id(url_permalink), "987654321")
        self.assertEqual(extract_canonical_post_id(url_multi), "1122334455")
        self.assertEqual(extract_canonical_post_id(url_story), "9988776655")

    def test_extract_canonical_post_id_from_query_params(self):
        url_query_fbid = "https://www.facebook.com/permalink.php?story_fbid=5544332211&id=100054"
        url_fbid_only = "https://www.facebook.com/photo.php?fbid=8877665544&set=pcb.123"

        self.assertEqual(extract_canonical_post_id(url_query_fbid), "5544332211")
        self.assertEqual(extract_canonical_post_id(url_fbid_only), "8877665544")

    def test_extract_canonical_post_id_none_or_unmatched(self):
        self.assertIsNone(extract_canonical_post_id(None))
        self.assertIsNone(extract_canonical_post_id(""))
        self.assertIsNone(extract_canonical_post_id("https://www.facebook.com/groups/yerevanhousing/"))

    # -------------------------------------------------------------------------
    # 2. normalize_url
    # -------------------------------------------------------------------------

    def test_normalize_url_strips_query_and_trailing_slash(self):
        url = "https://www.facebook.com/groups/123/posts/456/?comment_id=789&reply=true/"
        normalized = normalize_url(url)
        self.assertEqual(normalized, "https://www.facebook.com/groups/123/posts/456")

    def test_normalize_url_replaces_permalink_with_posts(self):
        url = "https://www.facebook.com/groups/123/permalink/456"
        normalized = normalize_url(url)
        self.assertEqual(normalized, "https://www.facebook.com/groups/123/posts/456")

    def test_normalize_url_prepends_domain_to_relative_paths(self):
        url = "/groups/123/posts/456"
        normalized = normalize_url(url)
        self.assertEqual(normalized, "https://www.facebook.com/groups/123/posts/456")

    def test_normalize_url_empty_or_none(self):
        self.assertEqual(normalize_url(None), "")
        self.assertEqual(normalize_url(""), "")

    # -------------------------------------------------------------------------
    # 3. extract_post_id
    # -------------------------------------------------------------------------

    def test_extract_post_id_standard_and_fallback(self):
        url = "https://www.facebook.com/groups/123/posts/456789"
        self.assertEqual(extract_post_id(url), "456789")

        url_permalink = "https://www.facebook.com/groups/123/permalink/987654"
        self.assertEqual(extract_post_id(url_permalink), "987654")

        fallback_url = "https://www.facebook.com/about"
        self.assertEqual(extract_post_id(fallback_url), fallback_url)

    # -------------------------------------------------------------------------
    # 4. decode_facebook_id
    # -------------------------------------------------------------------------

    def test_decode_facebook_id_numeric_string(self):
        self.assertEqual(decode_facebook_id("1000123456789"), "1000123456789")
        self.assertEqual(decode_facebook_id(1000123456789), "1000123456789")

    def test_decode_facebook_id_base64_encoded_composite(self):
        # Colon-separated string e.g. "feedback:9988776655"
        raw_composite = "feedback:9988776655"
        b64_encoded = base64.b64encode(raw_composite.encode('utf-8')).decode('utf-8')
        decoded = decode_facebook_id(b64_encoded)
        self.assertEqual(decoded, "9988776655")

    def test_decode_facebook_id_unpadded_base64(self):
        raw_composite = "node:item:11223344"
        b64_unpadded = base64.b64encode(raw_composite.encode('utf-8')).decode('utf-8').rstrip("=")
        decoded = decode_facebook_id(b64_unpadded)
        self.assertEqual(decoded, "11223344")

    def test_decode_facebook_id_none_or_empty(self):
        self.assertIsNone(decode_facebook_id(None))
        self.assertIsNone(decode_facebook_id(""))


if __name__ == "__main__":
    unittest.main()
