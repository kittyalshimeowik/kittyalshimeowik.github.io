import os
import json
import re
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime

# --- File Paths & Directories ---
# Point directly to the folders present in your web-scraper directory
OUTPUT_DIR = "housing_posts_data"
METADATA_DIR = "groups_metadata"
MASTER_OUTPUT_DIR = "master_listings_json" 

# Ensure the master output directory exists
os.makedirs(MASTER_OUTPUT_DIR, exist_ok=True)

def load_json_file(file_path):
    """Safely loads and returns data from a JSON file."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️ Error loading {file_path}: {e}")
        return None

def sanitize_filename(text):
    """Converts text into a safe filename."""
    if not text:
        return "unknown"
    return "".join([c for c in text if c.isalnum() or c in (' ', '-', '_')]).strip().replace(" ", "_").lower()

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
    Iterates through all extracted files in the OUTPUT_DIR,
    deduplicates posts based on URL, and returns a list of all unique posts.
    """
    all_unique_posts_by_url = {}
    total_files_processed = 0

    if not os.path.exists(OUTPUT_DIR):
        print(f"❌ Input directory '{OUTPUT_DIR}' not found. Run scraper first.")
        return []

    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(OUTPUT_DIR, filename)
            print(f"📄 Reading file: {filename}")
            group_posts = load_json_file(file_path)
            
            if group_posts and isinstance(group_posts, list):
                total_files_processed += 1
                for post in group_posts:
                    post_url = post.get("url")
                    if post_url:
                        # Use URL as the primary deduplication key.
                        # If we see this URL again, we only keep it if it has more data (e.g., text was extracted later).
                        if post_url not in all_unique_posts_by_url:
                            all_unique_posts_by_url[post_url] = post
                        else:
                            # Simple check to keep the 'fuller' version of a post if available
                            existing_post = all_unique_posts_by_url[post_url]
                            if (not existing_post.get("has_text") and post.get("has_text")) or \
                               (not existing_post.get("creation_timestamp") and post.get("creation_timestamp")):
                                all_unique_posts_by_url[post_url] = post

    url_unique_posts = list(all_unique_posts_by_url.values())
    content_unique_posts = merge_duplicate_listings(url_unique_posts)
    print(f"✅ Processed {total_files_processed} files. Found {len(content_unique_posts)} unique listings after content deduplication.")
    return content_unique_posts

def categorize_and_save_master_files(all_posts):
    """
    Takes a list of posts, organizes them into categories (Apartments, Houses, Land, Rentals),
    and saves each category to a master JSON file.
    """
    master_categories = {
        "apartments_for_sale.json": {"type": "Sale", "category": "Apartment"},
        "houses_for_sale.json":    {"type": "Sale", "category": "House"},
        "land_for_sale.json":      {"type": "Sale", "category": "Land"},
        "apartments_for_rent.json": {"type": "Rent", "category": "Apartment"},
        "houses_for_rent.json":    {"type": "Rent", "category": "House"},
        "all_for_sale_rent.json":   {"type": "Any", "category": "Any"} # Special file with everything
    }

    # Clear previous master files
    for filename in master_categories.keys():
        file_path = os.path.join(MASTER_OUTPUT_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    print(f"\n💾 Saving master listings to '{MASTER_OUTPUT_DIR}/'...")

    # Organize posts by location
    location_organized_listings = {}
    
    for file_name, filters in master_categories.items():
        filtered_posts = []
        
        # Apply filters (Rent/Sale and Category)
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
                
                # Collect locations for site filtering
                locations = post.get("locations", [])
                if not locations: locations = ["Unknown Location"]
                
                for loc in locations:
                    clean_loc = sanitize_filename(loc)
                    if clean_loc not in location_organized_listings:
                        location_organized_listings[clean_loc] = []
                    
                    # Add post to location list if not already there
                    if not any(existing['url'] == post['url'] for existing in location_organized_listings[clean_loc]):
                         location_organized_listings[clean_loc].append({
                            "url": post.get("url"),
                            "title": f"{p_cat} in {loc}",
                            "price": post.get("prices"),
                            "category": p_cat,
                            "location": loc,
                            "rooms": post.get("rooms"),
                            "size": post.get("sizes_sqm")
                         })
        
        # Sort posts by date (newest first)
        filtered_posts.sort(key=lambda x: x.get("creation_timestamp") or 0, reverse=True)
        
        # Save the filtered category file
        output_path = os.path.join(MASTER_OUTPUT_DIR, file_name)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # Use compact JSON format for web performance
                json.dump(filtered_posts, f, ensure_ascii=False, separators=(',', ':'))
            print(f"  ✅ Created '{file_name}' ({len(filtered_posts)} listings)")
        except IOError as e:
             print(f"  ❌ Error saving '{file_name}': {e}")

    # --- Generate location-specific files for the frontend ---
    print("\n💾 Saving location-specific summary files for visualization...")
    
    loc_summary_dir = os.path.join(MASTER_OUTPUT_DIR, "by_location")
    os.makedirs(loc_summary_dir, exist_ok=True)

    for clean_loc, listings_data in location_organized_listings.items():
        loc_file_name = f"{clean_loc}.json"
        loc_file_path = os.path.join(loc_summary_dir, loc_file_name)
        
        try:
             # Safely sort by size checking if list has items to prevent IndexError
            listings_data.sort(key=lambda x: x.get("size")[0] if x.get("size") else 0, reverse=True)
            
            with open(loc_file_path, 'w', encoding='utf-8') as f:
                json.dump(listings_data, f, ensure_ascii=False, separators=(',', ':'))
        except IOError as e:
            print(f"  ❌ Error saving location file '{loc_file_name}': {e}")

    print(f"\n🎉 All master and location files generated successfully in '{MASTER_OUTPUT_DIR}/'.")

def generate_site_data():
    """Main function to orchestrate data consolidation."""
    print("="*60)
    print("🚀 Starting Master JSON Generation for Kitty's Visualization")
    print("="*60)
    
    all_unique_data = get_unique_listings_from_all_groups()
    
    if all_unique_data:
        categorize_and_save_master_files(all_unique_data)
        
        # Generate a metadata file with the build time
        meta_file_path = os.path.join(MASTER_OUTPUT_DIR, "meta.json")
        build_meta = {
            "last_build": datetime.now().isoformat(),
            "total_listings_count": len(all_unique_data),
            "source_project": "fb_housing_scraper_armenia"
        }
        with open(meta_file_path, 'w', encoding='utf-8') as f:
            json.dump(build_meta, f, indent=2)
        print(f"\nℹ️ Meta file created: '{meta_file_path}'")

    else:
        print("⚠️ No data found to consolidate. Ensure the scraper has run successfully.")

    print("="*60)
    print("✅ Build Process Finished.")
    print("="*60)

if __name__ == "__main__":
    generate_site_data()