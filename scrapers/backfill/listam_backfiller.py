# scrapers/backfill/listam_backfiller.py

import os
import re
import time
import random
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

from scrapers.backfill.base import BasePlatformBackfiller
from scrapers.listam.utilities.listam_utils import extract_listing_images, human_scroll
from scrapers.utilities.logger import get_logger

logger = get_logger("listam_backfill")


def clean_listam_images(raw_images):
    """Filters out avatars, advertisements, and tracking icons from List.am photos."""
    clean = []
    seen = set()
    for img in raw_images:
        if not img or not isinstance(img, str) or not img.startswith("http"):
            continue
        low = img.lower()
        if "avatar" in low or "listcamp" in low or "icon" in low or "logo" in low or "star" in low:
            continue
        # Deduplicate by base path
        base = img.split("?")[0]
        if base in seen:
            continue
        seen.add(base)
        clean.append(img)
    return clean[:5]


def check_listam_rate_limit_or_challenge(driver) -> Dict[str, Any]:
    """Detects Cloudflare challenge loops, 403 blocks, or 429 rate limits."""
    try:
        title = (driver.title or "").lower()
        source_sample = driver.page_source[:2500].lower()
        if "cf-turnstile" in source_sample or "just a moment..." in title or "attention required! | cloudflare" in title:
            return {"blocked": True, "reason": "cloudflare_challenge", "message": "Cloudflare Turnstile challenge screen"}
        if "403 forbidden" in title or "access denied" in title or "error 1020" in source_sample:
            return {"blocked": True, "reason": "cloudflare_403", "message": "Cloudflare 403 Forbidden / Access Denied"}
        if "too many requests" in title or "429" in title:
            return {"blocked": True, "reason": "rate_limit_429", "message": "List.am 429 Too Many Requests"}
    except Exception:
        pass
    return {"blocked": False, "reason": None, "message": ""}


class ListAmBackfiller(BasePlatformBackfiller):
    @property
    def platform_name(self) -> str:
        return "List.am"

    def get_pending_photos_count(self, storage, active_only: bool = True) -> int:
        cur = storage.conn.cursor()
        query = """
            SELECT COUNT(*) FROM listings
            WHERE source = 'List.am'
              AND (images_json IS NULL OR images_json = '[]' OR length(images_json) <= 2)
              AND (photo_status IN ('PENDING', 'RATE_LIMITED', 'ERROR') OR (photos_checked_at IS NULL AND photo_status != 'NO_PHOTO'))
        """
        if active_only:
            query += " AND is_active = 1"
        cur.execute(query)
        return cur.fetchone()[0]

    def get_pending_translations_count(self, storage, active_only: bool = True) -> int:
        cur = storage.conn.cursor()
        query = """
            SELECT COUNT(*) FROM listings
            WHERE source = 'List.am'
              AND full_text IS NOT NULL AND length(trim(full_text)) > 5
              AND (translation_status IN ('PENDING', 'RATE_LIMITED', 'ERROR') OR translation_status IS NULL)
        """
        if active_only:
            query += " AND is_active = 1"
        cur.execute(query)
        return cur.fetchone()[0]

    def get_pending_listings(self, storage, active_only: bool = True, limit: Optional[int] = None):
        cur = storage.conn.cursor()
        query = """
            SELECT canonical_id, url, property_category, listing_type
            FROM listings
            WHERE source = 'List.am'
              AND (images_json IS NULL OR images_json = '[]' OR length(images_json) <= 2)
              AND (photo_status IN ('PENDING', 'RATE_LIMITED', 'ERROR') OR (photos_checked_at IS NULL AND photo_status != 'NO_PHOTO'))
        """
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY is_active DESC, creation_timestamp DESC"
        if limit is not None and limit > 0:
            query += f" LIMIT {int(limit)}"

        cur.execute(query)
        return [dict(r) for r in cur.fetchall()]

    def backfill_photos(
        self,
        storage,
        limit: Optional[int] = None,
        headless: bool = True,
        active_only: bool = True
    ) -> Dict[str, Any]:
        targets = self.get_pending_listings(storage, active_only=active_only, limit=limit)
        total_targets = len(targets)

        if total_targets == 0:
            print("✅ All List.am listings already have photos stored or have been verified!")
            return {"processed": 0, "photos_found": 0, "remaining_in_db": 0}

        print(f"🚀 Commencing List.am photo backfill for {total_targets} listings...")
        logger.info(f"Starting List.am photo backfill: {total_targets} target listings (limit={limit}, active_only={active_only})")

        from scrapers.listam.list_am_scraper import DirectBrowserListAmScraper
        scraper = DirectBrowserListAmScraper()
        driver = scraper.init_driver()

        processed_count = 0
        photos_found_count = 0
        posts_with_photos = 0
        blocked_count = 0
        run_start = time.time()

        try:
            for idx, item in enumerate(targets):
                cid = item["canonical_id"]
                url = item["url"]

                remaining_in_run = total_targets - (idx + 1)
                pct = ((idx + 1) / total_targets) * 100.0
                elapsed_sec = time.time() - run_start
                rate = (idx + 1) / elapsed_sec if elapsed_sec > 0 else 0
                eta_sec = remaining_in_run / rate if rate > 0 else 0

                print(f"[{idx + 1}/{total_targets}] ({pct:5.1f}%) Fetching List.am listing: {url}")
                try:
                    time.sleep(random.uniform(2.0, 3.5))
                    driver.get(url)
                    scraper.handle_cloudflare_loop()

                    cf_status = check_listam_rate_limit_or_challenge(driver)
                    if cf_status["blocked"]:
                        scraper.handle_cloudflare_loop()
                        cf_status = check_listam_rate_limit_or_challenge(driver)
                        if cf_status["blocked"]:
                            blocked_count += 1
                            storage.update_photo_status(cid, "RATE_LIMITED")
                            logger.warning(f"List.am rate limit / Cloudflare block for {cid} ({url}): {cf_status['message']}")
                            print(f"  ⚠️ List.am / Cloudflare block: {cf_status['message']} (marked RATE_LIMITED in DB)")
                            print("  ⏳ Skipping listing, backing off for 25s...")
                            time.sleep(25.0)
                            continue

                    human_scroll(driver, is_category_page=False)

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    raw_images = extract_listing_images(soup)
                    images = clean_listam_images(raw_images)

                    if images:
                        storage.update_listing_images(cid, images, status="SUCCESS")
                        photos_found_count += len(images)
                        posts_with_photos += 1
                        logger.info(f"Extracted {len(images)} photos for {cid}")
                        print(f"  📸 Found {len(images)} photos -> Stored in database (SUCCESS).")
                    else:
                        storage.update_listing_images(cid, [], status="NO_PHOTO")
                        logger.info(f"No property photos found for {cid} (marked NO_PHOTO)")
                        print("  ℹ️ No property photos found (marked NO_PHOTO in database).")

                    processed_count += 1
                    print(f"  📊 Run stats: Photos found: {photos_found_count} | Posts with photos: {posts_with_photos} | Remaining: {remaining_in_run} | Elapsed: {elapsed_sec:.1f}s (ETA: {eta_sec:.0f}s)")

                except Exception as ex:
                    logger.error(f"Error fetching {cid} ({url}): {ex}", exc_info=True)
                    print(f"  ❌ Error fetching {url}: {ex}")
                    try:
                        storage.update_photo_status(cid, "ERROR")
                    except Exception:
                        pass

                # Rest break every 25 listings
                if (idx + 1) % 25 == 0 and (idx + 1) < total_targets:
                    rest_sec = random.uniform(12.0, 22.0)
                    print(f"\n☕ Emulating user break ({rest_sec:.1f}s)...")
                    time.sleep(rest_sec)

        finally:
            try:
                driver.quit()
            except Exception:
                pass

        total_elapsed = time.time() - run_start
        pending_remaining = self.get_pending_photos_count(storage, active_only=active_only)

        logger.info(
            f"List.am photo backfill completed: processed={processed_count}/{total_targets}, "
            f"photos_found={photos_found_count}, posts_with_photos={posts_with_photos}, "
            f"blocked={blocked_count}, remaining={pending_remaining}, elapsed={total_elapsed:.1f}s"
        )
        print("\n" + "=" * 65)
        print("List.am Photo Backfill Run Summary")
        print(f"Total Targets In Run: {total_targets}")
        print(f"Successfully Checked: {processed_count}")
        print(f"Posts With Photos:    {posts_with_photos}")
        print(f"Total Photos Saved:   {photos_found_count}")
        print(f"Rate-Limited/Blocked: {blocked_count}")
        print(f"Remaining in DB:      {pending_remaining}")
        print(f"Execution Time:       {total_elapsed:.1f}s")
        print("=" * 65 + "\n")

        return {
            "processed": processed_count,
            "posts_with_photos": posts_with_photos,
            "photos_found": photos_found_count,
            "blocked_count": blocked_count,
            "remaining_in_db": pending_remaining,
            "elapsed_seconds": total_elapsed
        }
