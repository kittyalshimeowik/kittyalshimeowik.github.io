# scrapers/processors/clean_stray_photos.py

import os
import sys
import json
import collections
from typing import Dict, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.env_utils import ensure_utf8_output
ensure_utf8_output()

from scrapers.utilities.storage import ListingsStorage, compute_record_completeness
from scrapers.facebook.utilities.fb_utils import is_valid_fb_photo_url
from scrapers.processors.generate_site_data import generate_site_data


def extract_photo_signature(url: str) -> str:
    """Extracts the core filename / photo ID signature from a Facebook CDN URL."""
    if not url:
        return ""
    import re
    m = re.search(r'/([^/?]+\.(?:jpg|jpeg|png|webp))', url)
    if m:
        return m.group(1)
    return url.split("?")[0]


KNOWN_STRAY_PATTERNS = [
    "840663935_10246288876459731",  # Stray political photo (Armenian official)
]


def purge_invalid_and_stray_photos(storage: ListingsStorage) -> Dict[str, Any]:
    """
    Identifies and purges stray non-listing photos:
    1. Removes external link previews (OpenGraph thumbnails like t39.99422, safe_image.php).
    2. Identifies and removes photos repeated across 3 or more distinct Facebook posts
       (stray feed/sidebar images incorrectly scraped during single-post visits),
       matching on filename/photo ID signature to account for varying CDN subdomains.
    3. Purges known stray non-property photos.
    4. Updates SQLite listings and recomputes completeness scores.
    """
    cur = storage.conn.cursor()
    cur.execute("""
        SELECT canonical_id, source, images_json 
        FROM listings 
        WHERE source = 'Facebook' 
          AND images_json IS NOT NULL 
          AND length(images_json) > 2
    """)
    rows = cur.fetchall()

    # Step 1: Detect duplicate photos across Facebook posts by image signature
    sig_to_posts = collections.defaultdict(list)
    for r in rows:
        cid = r["canonical_id"]
        try:
            images = json.loads(r["images_json"] or "[]")
        except Exception:
            images = []
        for img in images:
            sig = extract_photo_signature(img)
            sig_to_posts[sig].append(cid)

    # Images occurring across >= 3 distinct posts are stray page elements, not real listing photos
    stray_duplicates = {sig for sig, posts in sig_to_posts.items() if len(posts) >= 3}

    purged_listings = 0
    total_images_purged = 0

    with storage.conn:
        for r in rows:
            cid = r["canonical_id"]
            try:
                images = json.loads(r["images_json"] or "[]")
            except Exception:
                images = []

            clean_images = []
            for img in images:
                sig = extract_photo_signature(img)
                if not is_valid_fb_photo_url(img):
                    total_images_purged += 1
                    continue
                if sig in stray_duplicates:
                    total_images_purged += 1
                    continue
                if any(bad in img for bad in KNOWN_STRAY_PATTERNS):
                    total_images_purged += 1
                    continue
                clean_images.append(img)

            if len(clean_images) != len(images):
                # Update listing with clean images
                storage.update_listing_images(cid, clean_images, checked=True)
                purged_listings += 1

    return {
        "purged_listings_count": purged_listings,
        "total_images_purged": total_images_purged,
        "stray_duplicate_urls_count": len(stray_duplicates)
    }


def run_photo_cleanup(regenerate: bool = True):
    print("=" * 65)
    print("🧹 Cleaning Stray & Invalid Facebook Listing Photos...")
    print("=" * 65)

    with ListingsStorage() as storage:
        stats = purge_invalid_and_stray_photos(storage)
        print(f"✅ Found and purged {stats['stray_duplicate_urls_count']} stray repeated images.")
        print(f"🗑️ Cleaned {stats['total_images_purged']} invalid image references across {stats['purged_listings_count']} listings.")

    if regenerate:
        print("\n🔄 Regenerating public website master listings JSON feeds...")
        generate_site_data()
        print("✅ Master listings feeds synchronized.")


if __name__ == "__main__":
    run_photo_cleanup(regenerate=True)
