# scrapers/utilities/backfill_translations.py

import os
import sys
import json
import time
import argparse
from datetime import datetime

# Resolve Project Root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.env_utils import ensure_utf8_output
from scrapers.utilities.logger import get_logger
ensure_utf8_output()
logger = get_logger("translations_backfill")

from scrapers.utilities.storage import ListingsStorage, compute_record_completeness
from scrapers.utilities.translator import (
    TranslationCache,
    batch_translate_texts,
    translate_single_text,
    is_already_english,
    is_genuine_translation,
    is_recently_rate_limited
)


def get_listings_missing_translation(storage, source=None, active_only=True, limit=None):
    """Retrieves listings that lack an English translation (pending, rate-limited, or errored)."""
    cur = storage.conn.cursor()
    query = """
        SELECT canonical_id, source, url, property_category, listing_type, 
               full_text, full_text_en, is_active
        FROM listings
        WHERE full_text IS NOT NULL 
          AND length(trim(full_text)) > 5
          AND (translation_status IN ('PENDING', 'RATE_LIMITED', 'ERROR') OR translation_status IS NULL)
    """
    params = []

    if active_only:
        query += " AND is_active = 1"

    if source and source.lower() != "all":
        query += " AND source = ?"
        params.append(source)

    query += " ORDER BY is_active DESC, creation_timestamp DESC"

    cur.execute(query, params)
    rows = cur.fetchall()

    missing = []
    for r in rows:
        d = dict(r)
        if not is_genuine_translation(d.get("full_text"), d.get("full_text_en")):
            missing.append(d)
            if limit is not None and limit > 0 and len(missing) >= limit:
                break

    return missing


def run_translation_backfill(
    source=None,
    limit=None,
    active_only=True,
    batch_size=10,
    regenerate_site_data=True
):
    print("=" * 65)
    print("Listing English Translation Backfill Utility")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    with ListingsStorage() as storage:
        targets = get_listings_missing_translation(
            storage,
            source=source,
            active_only=active_only,
            limit=limit
        )

        total_targets = len(targets)
        if total_targets == 0:
            print("✅ All matching listings already have English translations!")
            return {"processed": 0, "translated": 0}

        print(f"📋 Found {total_targets} listings missing English translation.\n")
        logger.info(f"Starting translation backfill: {total_targets} listings (source={source}, limit={limit}, active_only={active_only}, batch_size={batch_size})")

        cache = TranslationCache()
        print(f"💾 Loaded translation cache ({len(cache)} entries).")

        texts = [t["full_text"] for t in targets]
        translated_count = 0
        run_start = datetime.now()

        # Process in batches
        for i in range(0, total_targets, batch_size):
            chunk = targets[i:i + batch_size]
            chunk_texts = [item["full_text"] for item in chunk]

            translated_batch = batch_translate_texts(
                chunk_texts,
                target_lang="en",
                batch_size=min(5, len(chunk_texts)),
                cache=cache
            )

            batch_saved = 0
            for item, en_text in zip(chunk, translated_batch):
                cid = item["canonical_id"]
                orig_text = item.get("full_text") or ""
                if en_text and en_text.strip() and is_genuine_translation(orig_text, en_text):
                    storage.update_listing_translation(cid, en_text.strip(), status="SUCCESS")
                    translated_count += 1
                    batch_saved += 1
                else:
                    curr_st = "RATE_LIMITED" if is_recently_rate_limited() else "ERROR"
                    storage.update_translation_status(cid, curr_st)
                    if curr_st == "RATE_LIMITED":
                        logger.warning(f"Translation rate limited (HTTP 429) for {cid}")
                    else:
                        logger.warning(f"Translation error/failed validation for {cid}")

            cache.save()

            processed_so_far = min(i + batch_size, total_targets)
            pct = (processed_so_far / total_targets) * 100.0
            elapsed = (datetime.now() - run_start).total_seconds()
            rate = processed_so_far / elapsed if elapsed > 0 else 0
            remaining_run = total_targets - processed_so_far
            eta_sec = remaining_run / rate if rate > 0 else 0

            print(f"[{processed_so_far}/{total_targets}] ({pct:5.1f}%) | Batch: {batch_saved}/{len(chunk)} translated | Total this run: {translated_count} | Remaining in run: {remaining_run} | Elapsed: {elapsed:.1f}s (ETA: {eta_sec:.0f}s)")

            time.sleep(0.5)

        cache.save()

        # Query remaining in database after backfill
        remaining_in_db = len(get_listings_missing_translation(
            storage,
            source=source,
            active_only=active_only
        ))

    total_elapsed = (datetime.now() - run_start).total_seconds()
    logger.info(
        f"Translation backfill completed: processed={total_targets}, translated={translated_count}, "
        f"remaining_in_db={remaining_in_db}, elapsed={total_elapsed:.1f}s"
    )
    print("\n" + "=" * 65)
    print("Translation Backfill Run Summary")
    print(f"Processed In Run:     {total_targets}")
    print(f"Successfully Saved:   {translated_count}")
    print(f"Remaining in DB:      {remaining_in_db}")
    print(f"Execution Time:       {total_elapsed:.1f}s")
    print("=" * 65 + "\n")

    if regenerate_site_data:
        print("[INFO] Regenerating website public feeds via generate_site_data()...")
        from scrapers.processors.generate_site_data import generate_site_data as run_generator
        run_generator()
        print("✅ Website JSON feeds successfully updated with English translations!")

    return {
        "processed": total_targets,
        "translated": translated_count,
        "remaining_in_db": remaining_in_db,
        "elapsed_seconds": total_elapsed
    }


def main():
    parser = argparse.ArgumentParser(description="Backfill English translations for listings")
    parser.add_argument("-n", "--limit", type=int, default=None, help="Maximum number of listings to translate")
    parser.add_argument("-s", "--source", type=str, default="all", choices=["Facebook", "List.am", "all"], help="Filter by source")
    parser.add_argument("--all", action="store_true", help="Include inactive listings")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for processing")
    parser.add_argument("--skip-site-gen", action="store_true", help="Skip regenerating website master JSON feeds")

    args = parser.parse_args()

    run_translation_backfill(
        source=args.source if args.source != "all" else None,
        limit=args.limit,
        active_only=not args.all,
        batch_size=args.batch_size,
        regenerate_site_data=not args.skip_site_gen
    )


if __name__ == "__main__":
    main()
