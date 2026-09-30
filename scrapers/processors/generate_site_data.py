import os
import sys
import json
import re
import hashlib
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime

# --- Resolve Project Root so 'scrapers' imports work from anywhere ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.housing_parser import extract_housing_details

# --- File Paths & Directories ---
SCRAPERS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

MASTER_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "master_listings_json")
os.makedirs(MASTER_OUTPUT_DIR, exist_ok=True)
LOC_SUMMARY_DIR = os.path.join(MASTER_OUTPUT_DIR, "by_location")

CACHE_FILE_PATH = os.path.join(SCRIPT_DIR, "dedup_cache.json")
RAW_DATA_INPUT_FOLDER = SCRAPERS_ROOT
EXCHANGE_RATE_AMD_PER_USD = 364.18


def print_progress(current, total, prefix='Progress', suffix='Complete', length=40):
    """Prints a dynamic console progress bar."""
    percent = f"{100 * (current / float(total)):.1f}" if total else "100.0"
    filled_len = int(length * current // total) if total else length
    bar = '=' * filled_len + '-' * (length - filled_len)
    sys.stdout.write(f'\r{prefix} [{bar}] {percent}% {suffix}')
    sys.stdout.flush()
    if current == total:
        sys.stdout.write('\n')


def load_dedup_cache():
    """Loads previously processed listing signatures."""
    if os.path.exists(CACHE_FILE_PATH):
        try:
            with open(CACHE_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"\n[WARNING] Failed to load dedup cache: {e}")
            return {}
    return {}


def save_dedup_cache(cache):
    """Persists processed listing signatures to disk."""
    try:
        with open(CACHE_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception as e:
        print(f"\n[WARNING] Failed to save dedup cache: {e}")


from scrapers.processors.dedup_utils import (
    DEFAULT_EXCHANGE_RATE_AMD_PER_USD,
    is_ghost_record,
    is_valid_display_listing,
    normalize_listing_text,
    listing_completeness_score,
    get_phone_spec_signature,
    listing_content_key,
    compute_listing_hash,
    extract_canonical_post_id,
    sanitize_filename,
    normalize_timestamp,
    normalize_and_convert_prices
)

EXCHANGE_RATE_AMD_PER_USD = DEFAULT_EXCHANGE_RATE_AMD_PER_USD


def load_json_file(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"\n[WARNING] Error loading {file_path}: {e}")
        return None


def merge_duplicate_listings(posts):
    unique_posts = []
    exact_matches = {}

    print("[INFO] Step 1/2: Performing exact content and phone+specs deduplication...")
    for post in posts:
        content_key = listing_content_key(post)
        phone_key = get_phone_spec_signature(post)
        matched_idx = None

        if content_key and content_key in exact_matches:
            matched_idx = exact_matches[content_key]
        elif phone_key and phone_key in exact_matches:
            matched_idx = exact_matches[phone_key]

        if matched_idx is not None:
            if listing_completeness_score(post) > listing_completeness_score(unique_posts[matched_idx]):
                unique_posts[matched_idx] = post
            continue

        new_idx = len(unique_posts)
        if content_key:
            exact_matches[content_key] = new_idx
        if phone_key:
            exact_matches[phone_key] = new_idx
        unique_posts.append(post)

    print("[INFO] Step 2/2: Performing bucketed fuzzy duplicate matching...")
    
    # Bucket listings by property category + primary location to eliminate cross-group O(N^2) checks
    buckets = {}
    for post in unique_posts:
        cat = post.get("property_category") or "Unknown"
        locs = post.get("locations") or ["Unknown"]
        primary_loc = locs[0] if locs else "Unknown"
        bucket_key = f"{cat}_{primary_loc}"
        
        buckets.setdefault(bucket_key, []).append(post)

    final_posts = []
    total_processed = 0
    total_items = len(unique_posts)

    for bucket_key, bucket_posts in buckets.items():
        fingerprints = []
        for post in bucket_posts:
            total_processed += 1
            if total_processed % 10 == 0 or total_processed == total_items:
                print_progress(total_processed, total_items, prefix='Fuzzy Matching:', suffix=f'({total_processed}/{total_items})')

            text = normalize_listing_text(post.get("full_text", ""))
            if len(text) < 120:
                final_posts.append(post)
                continue

            comparison_text = text[:250]
            duplicate_index = None

            for index, fingerprint in enumerate(fingerprints):
                # Pre-filter by length variance before engaging SequenceMatcher
                if abs(len(comparison_text) - len(fingerprint["text_sample"])) > 40:
                    continue

                # Use quick_ratio() first to fail early on non-matches
                matcher = SequenceMatcher(None, comparison_text, fingerprint["text_sample"])
                if matcher.quick_ratio() >= 0.90 and matcher.ratio() >= 0.94:
                    duplicate_index = index
                    break

            if duplicate_index is None:
                fingerprints.append({
                    "text_sample": comparison_text,
                    "post_ref": post
                })
                final_posts.append(post)
            else:
                # Keep the post with richer attribute metadata
                if listing_completeness_score(post) > listing_completeness_score(fingerprints[duplicate_index]["post_ref"]):
                    idx_in_final = final_posts.index(fingerprints[duplicate_index]["post_ref"])
                    final_posts[idx_in_final] = post
                    fingerprints[duplicate_index]["post_ref"] = post

    return final_posts





def get_unique_listings_from_all_groups():
    all_unique_posts_by_id = {}
    json_files = []

    print(f"\n[INFO] Discovering input JSON files under: '{RAW_DATA_INPUT_FOLDER}/'...")

    if not os.path.exists(RAW_DATA_INPUT_FOLDER):
        print(f"[ERROR] Root scrapers directory '{RAW_DATA_INPUT_FOLDER}' not found.")
        return []

    for site_dirname in os.listdir(RAW_DATA_INPUT_FOLDER):
        site_path = os.path.join(RAW_DATA_INPUT_FOLDER, site_dirname)
        if not os.path.isdir(site_path) or site_dirname == "processors":
            continue

        for subdir in ["housing_posts_data", "raw_data"]:
            input_subdir_path = os.path.join(site_path, subdir)
            if os.path.exists(input_subdir_path):
                for filename in os.listdir(input_subdir_path):
                    if filename.endswith(".json"):
                        json_files.append(os.path.join(input_subdir_path, filename))

    total_files = len(json_files)
    print(f"[INFO] Found {total_files} JSON data files to parse.")

    for idx, file_path in enumerate(json_files):
        print_progress(idx + 1, total_files, prefix='Parsing JSONs:', suffix=f'({idx + 1}/{total_files})')
        group_posts = load_json_file(file_path)

        if group_posts and isinstance(group_posts, list):
            for post in group_posts:
                # Pre-filter empty ghost records before heavy parsing
                raw_text = (post.get("full_text") or post.get("text") or "").strip()
                has_initial_attrs = bool(
                    post.get("prices") or post.get("sizes_sqm") or 
                    post.get("rooms") or post.get("phone_numbers")
                )
                if len(raw_text) < 15 and not has_initial_attrs:
                    continue

                # Normalize source
                if not post.get("source"):
                    post["source"] = "List.am" if "list.am" in str(post.get("url") or "").lower() else "Facebook"

                if post.get("full_text"):
                    reparsed_details = extract_housing_details(
                        post["full_text"],
                        is_media_only=post.get("is_media_only", False)
                    )
                    post["locations"] = reparsed_details.get("locations") or post.get("locations", [])

                    # Preserve existing valid category if re-parser yielded General/Unclassified/Media-Only
                    reparsed_cat = reparsed_details.get("property_category")
                    if reparsed_cat and reparsed_cat not in ["General / Unclassified", "Media-Only"]:
                        post["property_category"] = reparsed_cat
                    elif not post.get("property_category"):
                        post["property_category"] = reparsed_cat or "General / Unclassified"

                    # Preserve existing valid listing type if re-parser yielded Unknown
                    reparsed_type = reparsed_details.get("listing_type")
                    if reparsed_type and reparsed_type != "Unknown":
                        post["listing_type"] = reparsed_type
                    elif not post.get("listing_type"):
                        post["listing_type"] = reparsed_type or "Unknown"

                    post["rooms"] = reparsed_details.get("rooms") or post.get("rooms", [])
                    post["sizes_sqm"] = reparsed_details.get("sizes_sqm") or post.get("sizes_sqm", [])
                    post["phone_numbers"] = reparsed_details.get("phone_numbers") or post.get("phone_numbers", [])
                    if reparsed_details.get("prices"):
                        post["prices"] = reparsed_details.get("prices")
                    post["zoning"] = reparsed_details.get("zoning") or post.get("zoning", [])

                # Verify post has meaningful text or extracted attributes post-parsing
                text = (post.get("full_text") or "").strip()
                has_attrs = bool(
                    post.get("prices") or post.get("sizes_sqm") or 
                    post.get("rooms") or post.get("phone_numbers")
                )
                if len(text) < 15 and not has_attrs:
                    continue

                if "prices" in post:
                    post["prices"] = normalize_and_convert_prices(post.get("prices"))

                # Standardize creation timestamp
                post["creation_timestamp"] = normalize_timestamp(post)

                # Clean any temporary scraper artifacts
                post.pop("raw_node", None)

                post_url = post.get("url")
                canonical_id = post.get("canonical_id") or extract_canonical_post_id(post_url)
                if canonical_id:
                    post["canonical_id"] = canonical_id

                dedup_key = canonical_id or post_url
                if dedup_key:
                    if dedup_key not in all_unique_posts_by_id:
                        all_unique_posts_by_id[dedup_key] = post
                    else:
                        existing_post = all_unique_posts_by_id[dedup_key]
                        if listing_completeness_score(post) > listing_completeness_score(existing_post):
                            all_unique_posts_by_id[dedup_key] = post

    id_unique_posts = list(all_unique_posts_by_id.values())
    content_unique_posts = merge_duplicate_listings(id_unique_posts)

    print(f"[SUCCESS] Processed {total_files} files across all scraper modules.")
    print(f"[SUCCESS] Retained {len(content_unique_posts)} unique listings post-deduplication.")
    return content_unique_posts


def prune_for_display(post):
    """Retains essential fields for the website feed to minimize payload bandwidth."""
    text = post.get("full_text") or ""
    if len(text) > 500:
        text = text[:497] + "..."
    return {
        "url": post.get("url"),
        "canonical_id": post.get("canonical_id"),
        "source": post.get("source") or "Facebook",
        "property_category": post.get("property_category"),
        "listing_type": post.get("listing_type"),
        "prices": post.get("prices", []),
        "sizes_sqm": post.get("sizes_sqm", []),
        "rooms": post.get("rooms", []),
        "locations": post.get("locations", []),
        "phone_numbers": post.get("phone_numbers", []),
        "zoning": post.get("zoning", []),
        "full_text": text,
        "created_at": post.get("created_at"),
        "creation_timestamp": post.get("creation_timestamp") or 0
    }


def categorize_and_save_master_files(all_posts):
    master_categories = {
        "apartments_for_sale.json": {"type": "Sale", "category": "Apartment"},
        "houses_for_sale.json":    {"type": "Sale", "category": "House"},
        "land_for_sale.json":      {"type": "Sale", "category": "Land"},
        "apartments_for_rent.json": {"type": "Rent", "category": "Apartment"},
        "houses_for_rent.json":    {"type": "Rent", "category": "House"},
        "all_for_sale_rent.json":   {"type": "Any", "category": "Any"}
    }

    print(f"\n[INFO] Generating master category files...")

    for file_name, filters in master_categories.items():
        filtered_posts = []

        for post in all_posts:
            p_type = post.get("listing_type")
            p_cat = post.get("property_category")

            # Drop ghost records if any slipped through
            text = (post.get("full_text") or "").strip()
            has_attrs = bool(post.get("prices") or post.get("sizes_sqm") or post.get("rooms") or post.get("phone_numbers"))
            if len(text) < 15 and not has_attrs:
                continue

            # For all_for_sale_rent.json, only include verified, classified displayable listings
            if file_name == "all_for_sale_rent.json":
                if not p_cat or p_cat in ["General / Unclassified", "Media-Only"]:
                    continue

            is_match = (
                (filters["type"] == "Any" and filters["category"] == "Any") or
                (p_type == filters["type"] and filters["category"] == "Any") or
                (p_type == filters["type"] and p_cat == filters["category"])
            )

            if is_match:
                filtered_posts.append(post)

        display_posts = [prune_for_display(p) for p in filtered_posts]
        display_posts.sort(key=lambda x: x.get("creation_timestamp") or 0, reverse=True)
        output_path = os.path.join(MASTER_OUTPUT_DIR, file_name)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(display_posts, f, ensure_ascii=False, separators=(',', ':'))
        print(f"  [OK] Saved '{file_name}' ({len(display_posts)} records, {os.path.getsize(output_path) / 1024:.1f} KB)")

    # Clean up obsolete by_location directory if present
    if os.path.exists(LOC_SUMMARY_DIR):
        try:
            import shutil
            shutil.rmtree(LOC_SUMMARY_DIR, ignore_errors=True)
            print("[INFO] Pruned obsolete 'by_location/' directory.")
        except Exception:
            pass

    print(f"\n[SUCCESS] Master output created in '{MASTER_OUTPUT_DIR}/'.")


def generate_site_data():
    print("=" * 60)
    print("Starting Master JSON Generation for Website Visualization")
    print("=" * 60)

    dedup_cache = load_dedup_cache()
    all_unique_data = get_unique_listings_from_all_groups()

    if all_unique_data:
        processed_listings = []
        for post in all_unique_data:
            l_hash = compute_listing_hash(post)
            post_id = post.get("canonical_id") or post.get("url")
            
            # Check if listing contents match an existing record signature
            if post_id in dedup_cache and dedup_cache[post_id] == l_hash:
                post["is_previously_seen"] = True
            else:
                post["is_previously_seen"] = False
                dedup_cache[post_id] = l_hash
            
            processed_listings.append(post)

        categorize_and_save_master_files(processed_listings)
        save_dedup_cache(dedup_cache)

        meta_file_path = os.path.join(MASTER_OUTPUT_DIR, "meta.json")
        build_meta = {
            "last_build": datetime.now().isoformat(),
            "total_listings_count": len(processed_listings),
            "source_project": "fb_housing_scraper_armenia"
        }
        with open(meta_file_path, 'w', encoding='utf-8') as f:
            json.dump(build_meta, f, indent=2)
        print(f"[INFO] Meta metadata stored: '{meta_file_path}'")
    else:
        print("[WARNING] No data processed.")

    print("=" * 60)
    print("Build Process Finished.")
    print("=" * 60)


if __name__ == "__main__":
    generate_site_data()