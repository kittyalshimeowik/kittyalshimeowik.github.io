import os
import json
import re
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime

# --- File Paths & Directories (UPDATED FOR MODULAR STRUCTURE) ---
# SCRIPT_DIR is: scrapers/processors/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# SCRAPERS_ROOT is: scrapers/
SCRAPERS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

# Anchors master output and by_location summary files in the processors directory
MASTER_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "master_listings_json")
os.makedirs(MASTER_OUTPUT_DIR, exist_ok=True)
LOC_SUMMARY_DIR = os.path.join(MASTER_OUTPUT_DIR, "by_location")
os.makedirs(LOC_SUMMARY_DIR, exist_ok=True)

# Define where to look for raw data input from ALL sites
RAW_DATA_INPUT_FOLDER = SCRAPERS_ROOT

# Standard Exchange Rate (AMD per 1 USD)
EXCHANGE_RATE_AMD_PER_USD = 364.18


def extract_canonical_post_id(url, post_id=None):
    """
    Extracts the unique numeric Facebook ID without altering the original URL format.
    Handles /posts/<id>, /permalink/<id>, and query parameter formats.
    """
    if post_id:
        return str(post_id)
        
    if not url:
        return None

    path_match = re.search(r'/(?:posts|permalink|multi_permalink|story\.php)/(\d+)', url)
    if path_match:
        return path_match.group(1)

    query_match = re.search(r'(?:story_fbid|fbid)=(\d+)', url)
    if query_match:
        return query_match.group(1)

    return None


def normalize_and_convert_prices(prices):
    """Normalizes raw price entries and provides both AMD and USD values."""
    converted_prices = []
    if not prices or not isinstance(prices, list):
        return converted_prices
    
    for p in prices:
        amount = p.get("amount", 0)
        # Ensure amount is a numeric float or int
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            continue

        curr = str(p.get("currency", "AMD")).upper()
        
        # Determine amounts based on parsed currency type
        if curr == "USD":
            amt_usd = amount
            amt_amd = round(amount * EXCHANGE_RATE_AMD_PER_USD)
        else: # Default or AMD
            amt_amd = amount
            amt_usd = round(amount / EXCHANGE_RATE_AMD_PER_USD, 2)
            
        converted_prices.append({
            "original_amount": amount,
            "original_currency": curr,
            "amount_amd": amt_amd,
            "amount_usd": amt_usd,
            "raw_text": p.get("raw_text", str(amount))
        })
    return converted_prices


def load_json_file(file_path):
    """Safely loads and returns data from a JSON file."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[WARNING] Error loading {file_path}: {e}")
        return None


def sanitize_filename(text):
    """Converts text into a safe filename."""
    if not text:
        return "unknown"
    cleaned = "".join([c for c in text if c.isalnum() or c in (' ', '-', '_')]).strip().replace(" ", "_").lower()
    return re.sub(r'_+', '_', cleaned)


def normalize_listing_text(text):
    """Normalize post text so reposts with formatting changes share a fingerprint."""
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    normalized = re.sub(r"https?://\S+|www\.\S+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
    return re.sub(r"\s+", " ", normalized).strip()


def listing_content_key(post):
    text = normalize_listing_text(post.get("full_text", ""))
    if len(text) < 80:
        return None
    return "|".join([
        text,
        str(post.get("property_category") or ""),
        str(post.get("listing_type") or "")
    ])


def merge_duplicate_listings(posts):
    unique_posts = []
    exact_matches = {}

    for post in posts:
        content_key = listing_content_key(post)
        if content_key and content_key in exact_matches:
            existing_index = exact_matches[content_key]
            if listing_completeness_score(post) > listing_completeness_score(unique_posts[existing_index]):
                unique_posts[existing_index] = post
            continue
        if content_key:
            exact_matches[content_key] = len(unique_posts)
        unique_posts.append(post)

    final_posts = []
    fingerprints = []
    for post in unique_posts:
        text = normalize_listing_text(post.get("full_text", ""))
        if len(text) < 120:
            final_posts.append(post)
            continue

        duplicate_index = None
        for index, fingerprint in enumerate(fingerprints):
            if post.get("property_category") != fingerprint["category"]:
                continue
            if SequenceMatcher(None, text, fingerprint["text"]).ratio() >= 0.94:
                duplicate_index = index
                break

        if duplicate_index is None:
            fingerprints.append({
                "text": text,
                "category": post.get("property_category")
            })
            final_posts.append(post)
        elif listing_completeness_score(post) > listing_completeness_score(final_posts[duplicate_index]):
            final_posts[duplicate_index] = post

    return final_posts


def listing_completeness_score(post):
    return sum([
        bool(post.get("full_text")),
        bool(post.get("prices")),
        bool(post.get("sizes_sqm")),
        bool(post.get("rooms")),
        bool(post.get("locations")),
        bool(post.get("phone_numbers")),
        bool(post.get("creation_timestamp"))
    ])


def get_unique_listings_from_all_groups():
    """
    Iterates through all scraper directories under RAW_DATA_INPUT_FOLDER,
    deduplicates posts based on canonical_id / URL, normalizes prices,
    and returns unique posts.
    """
    all_unique_posts_by_id = {}
    total_files_processed = 0

    print(f"\n[INFO] Aggregating raw data from modules under: '{RAW_DATA_INPUT_FOLDER}/'...")

    if not os.path.exists(RAW_DATA_INPUT_FOLDER):
        print(f"[ERROR] Root scrapers directory '{RAW_DATA_INPUT_FOLDER}' not found.")
        return []

    # Iterate through each module under scrapers/ (e.g., facebook, site_a, etc.)
    for site_dirname in os.listdir(RAW_DATA_INPUT_FOLDER):
        site_path = os.path.join(RAW_DATA_INPUT_FOLDER, site_dirname)
        
        # Skip non-directories or the processors module itself
        if not os.path.isdir(site_path) or site_dirname == "processors":
            continue

        print(f"  > Scanning module: {site_dirname}")
        
        # Look for standard output folders inside each site scraper folder
        potential_data_subdirs = ["housing_posts_data", "raw_data"]
        data_found = False

        for subdir in potential_data_subdirs:
            input_subdir_path = os.path.join(site_path, subdir)
            if not os.path.exists(input_subdir_path):
                continue
            
            data_found = True
            for filename in os.listdir(input_subdir_path):
                if filename.endswith(".json"):
                    file_path = os.path.join(input_subdir_path, filename)
                    # print(f"    - Reading file: {filename}")
                    group_posts = load_json_file(file_path)
                    
                    if group_posts and isinstance(group_posts, list):
                        total_files_processed += 1
                        for post in group_posts:
                            # Apply price conversion & normalization
                            if "prices" in post:
                                post["prices"] = normalize_and_convert_prices(post.get("prices"))
                                
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

        if not data_found:
            print(f"    ! Warning: No data directory (housing_posts_data/raw_data) found for module '{site_dirname}'")

    id_unique_posts = list(all_unique_posts_by_id.values())
    content_unique_posts = merge_duplicate_listings(id_unique_posts)
    print(f"\n[SUCCESS] Processed {total_files_processed} files across all scraper modules.")
    print(f"[SUCCESS] Found {len(content_unique_posts)} unique listings after content deduplication.")
    return content_unique_posts


def categorize_and_save_master_files(all_posts):
    """
    Takes a list of posts, organizes them into categories, and saves master JSON files.
    """
    master_categories = {
        "apartments_for_sale.json": {"type": "Sale", "category": "Apartment"},
        "houses_for_sale.json":    {"type": "Sale", "category": "House"},
        "land_for_sale.json":      {"type": "Sale", "category": "Land"},
        "apartments_for_rent.json": {"type": "Rent", "category": "Apartment"},
        "houses_for_rent.json":    {"type": "Rent", "category": "House"},
        "all_for_sale_rent.json":   {"type": "Any", "category": "Any"}
    }

    for filename in master_categories.keys():
        file_path = os.path.join(MASTER_OUTPUT_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    print(f"\n[INFO] Saving master listings to '{MASTER_OUTPUT_DIR}/'...")

    location_organized_listings = {}
    
    for file_name, filters in master_categories.items():
        filtered_posts = []
        
        for post in all_posts:
            p_type = post.get("listing_type")
            p_cat = post.get("property_category")

            is_match = False
            if filters["type"] == "Any" and filters["category"] == "Any":
                is_match = True
            elif p_type == filters["type"] and filters["category"] == "Any":
                is_match = True
            elif p_type == filters["type"] and p_cat == filters["category"]:
                is_match = True

            if is_match:
                filtered_posts.append(post)
                
                locations = post.get("locations", [])
                if not locations: locations = ["Unknown Location"]
                
                for loc in locations:
                    clean_loc = sanitize_filename(loc)
                    if clean_loc not in location_organized_listings:
                        location_organized_listings[clean_loc] = []
                    
                    if not any(existing.get('url') == post.get('url') for existing in location_organized_listings[clean_loc]):
                        location_organized_listings[clean_loc].append({
                            "url": post.get("url"),
                            "canonical_id": post.get("canonical_id"),
                            "title": f"{p_cat} in {loc}",
                            "price": post.get("prices"),
                            "category": p_cat,
                            "location": loc,
                            "rooms": post.get("rooms"),
                            "size": post.get("sizes_sqm")
                        })
        
        filtered_posts.sort(key=lambda x: x.get("creation_timestamp") or 0, reverse=True)
        
        output_path = os.path.join(MASTER_OUTPUT_DIR, file_name)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(filtered_posts, f, ensure_ascii=False, separators=(',', ':'))
            print(f"  [OK] Created '{file_name}' ({len(filtered_posts)} listings)")
        except IOError as e:
            print(f"  [ERROR] Error saving '{file_name}': {e}")

    print("\n[INFO] Saving location-specific summary files for visualization...")
    
    for clean_loc, listings_data in location_organized_listings.items():
        loc_file_name = f"{clean_loc}.json"
        loc_file_path = os.path.join(LOC_SUMMARY_DIR, loc_file_name)
        
        try:
            listings_data.sort(key=lambda x: x.get("size")[0] if x.get("size") else 0, reverse=True)
            
            with open(loc_file_path, 'w', encoding='utf-8') as f:
                json.dump(listings_data, f, ensure_ascii=False, separators=(',', ':'))
        except IOError as e:
            print(f"  [ERROR] Error saving location file '{loc_file_name}': {e}")

    print(f"\n[SUCCESS] All master and location files generated successfully in '{MASTER_OUTPUT_DIR}/'.")


def generate_site_data():
    """Main function to orchestrate data consolidation."""
    print("="*60)
    print("Starting Master JSON Generation for Website Visualization")
    print("="*60)
    
    all_unique_data = get_unique_listings_from_all_groups()
    
    if all_unique_data:
        categorize_and_save_master_files(all_unique_data)
        
        meta_file_path = os.path.join(MASTER_OUTPUT_DIR, "meta.json")
        build_meta = {
            "last_build": datetime.now().isoformat(),
            "total_listings_count": len(all_unique_data),
            "source_project": "fb_housing_scraper_armenia"
        }
        with open(meta_file_path, 'w', encoding='utf-8') as f:
            json.dump(build_meta, f, indent=2)
        print(f"\n[INFO] Meta file created: '{meta_file_path}'")

    else:
        print("[WARNING] No data found to consolidate. Ensure the scrapers have run successfully.")

    print("="*60)
    print("Build Process Finished.")
    print("="*60)


if __name__ == "__main__":
    generate_site_data()