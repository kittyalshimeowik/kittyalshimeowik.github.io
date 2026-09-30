import os
import sys
import json
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.env_utils import ensure_utf8_output
from scrapers.processors.dedup_utils import (
    is_ghost_record,
    is_valid_display_listing,
    compute_record_score,
    get_content_signature,
    normalize_listing_text as normalize_text
)

ensure_utf8_output()

DEFAULT_TARGET_FILE = os.path.join(SCRIPT_DIR, "master_listings_json", "all_for_sale_rent.json")


def deduplicate_records(listings, filter_unclassified=False):
    """Merges duplicate listings and optionally filters out unclassified/ghost entries."""
    seen_signatures = {}
    print(f"🔍 Starting deduplication on {len(listings)} records...")

    valid_listings = []
    dropped_count = 0
    for item in listings:
        if is_ghost_record(item):
            dropped_count += 1
            continue
        if filter_unclassified and not is_valid_display_listing(item):
            dropped_count += 1
            continue
        valid_listings.append(item)

    if dropped_count > 0:
        print(f"👻 Discarded {dropped_count} ghost/unclassified records.")

    for item in valid_listings:
        sig = get_content_signature(item)
        score = compute_record_score(item)

        if not sig:
            # Preserve items with unique fallback IDs
            item_id = item.get("id") or item.get("canonical_id") or id(item)
            seen_signatures[f"unmatched_{item_id}"] = (score, item)
            continue

        if sig in seen_signatures:
            existing_score, _ = seen_signatures[sig]
            if score > existing_score:
                seen_signatures[sig] = (score, item)
        else:
            seen_signatures[sig] = (score, item)

    cleaned_listings = [item for _, item in seen_signatures.values()]
    print(f"✨ Removed {len(listings) - len(cleaned_listings)} duplicates/ghosts. Total unique: {len(cleaned_listings)}")

    return cleaned_listings


def run_cleanup(filepath=None, output_filepath=None, filter_unclassified=False):
    target_path = filepath or DEFAULT_TARGET_FILE
    out_path = output_filepath or target_path

    if not os.path.exists(target_path):
        print(f"❌ Target file not found: {target_path}")
        return

    print(f"[INFO] Reading listings file: {target_path}")
    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned_data = deduplicate_records(data, filter_unclassified=filter_unclassified)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, separators=(',', ':'))

    # Keep meta.json synchronized with actual cleaned count
    meta_path = os.path.join(os.path.dirname(out_path), "meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as mf:
                meta = json.load(mf)
            meta["total_listings_count"] = len(cleaned_data)
            with open(meta_path, "w", encoding="utf-8") as mf:
                json.dump(meta, mf, indent=2)
        except Exception:
            pass

    print(f"💾 Clean dataset saved successfully to {out_path} (compact JSON: {os.path.getsize(out_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up duplicate entries in master listing JSONs.")
    parser.add_argument("-f", "--file", help="Path to specific target JSON file")
    parser.add_argument("-o", "--out", help="Output path (prevents overwriting input)")
    args = parser.parse_args()

    run_cleanup(args.file, args.out)