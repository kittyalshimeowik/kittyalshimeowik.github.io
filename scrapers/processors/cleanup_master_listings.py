import os
import json
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGET_FILE = os.path.join(SCRIPT_DIR, "master_listings_json", "all_for_sale_rent.json")

def compute_record_score(item):
    """
    Calculates a completeness score to keep the richest 
    listing when duplicate matches are found.
    """
    score = 0
    if item.get("prices"):
        score += 3
    if item.get("sizes_sqm"):
        score += 2
    if item.get("rooms"):
        score += 2
    if item.get("locations"):
        score += 2
    if item.get("phone_numbers") or item.get("phone"):
        score += 3
    if item.get("full_text"):
        score += len(item["full_text"]) / 100.0
    return score

def get_content_signature(item):
    """
    Creates a robust property signature independent of post author or URL.
    """
    # 1. Primary identifier: Normalized phone numbers
    phones = sorted(list(set(item.get("phone_numbers") or [])))
    
    # 2. Key property specifications
    prices = tuple(sorted([p.get("amount_amd") for p in item.get("prices", []) if p.get("amount_amd")]))
    sizes = tuple(sorted(item.get("sizes_sqm") or []))
    rooms = tuple(sorted(item.get("rooms") or []))
    locs = tuple(sorted(item.get("locations") or []))
    category = item.get("property_category", "")
    
    # Extract exact clean text if available
    text_key = (item.get("full_text") or "").strip().lower()

    # Case A: If phone numbers and core specs match, it's the exact same property
    if phones and (prices or sizes or rooms):
        return f"phone_spec:{phones}|{prices}|{sizes}|{rooms}|{locs}"
    
    # Case B: Standard text content match (ignoring empty strings)
    if text_key:
        return f"text:{text_key}"

    # Case C: Media-only or textless duplicates in identical locations
    if sizes or prices or rooms:
        return f"spec:{category}|{prices}|{sizes}|{rooms}|{locs}"
        
    return None

def deduplicate_records(listings):
    seen_signatures = {}
    
    print(f"🔍 Starting deduplication on {len(listings)} records...")

    for item in listings:
        sig = get_content_signature(item)
        score = compute_record_score(item)

        if not sig:
            # Keep items with insufficient data for cross-matching
            seen_signatures[id(item)] = (score, item)
            continue

        if sig in seen_signatures:
            existing_score, existing_item = seen_signatures[sig]
            if score > existing_score:
                seen_signatures[sig] = (score, item)
        else:
            seen_signatures[sig] = (score, item)

    cleaned_listings = [item for _, item in seen_signatures.values()]
    removed_count = len(listings) - len(cleaned_listings)
    
    print(f"✨ Deduplication complete! Removed {removed_count} duplicate record(s).")
    print(f"📊 Clean total: {len(cleaned_listings)} unique listings remaining.")

    return cleaned_listings

def run_cleanup(filepath=None):
    target_path = filepath or DEFAULT_TARGET_FILE

    if not os.path.exists(target_path):
        print(f"❌ Target file not found: {target_path}")
        return

    print(f"📖 Reading listings file: {target_path}")
    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned_data = deduplicate_records(data)

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print(f"💾 Clean dataset saved successfully to {target_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up duplicate entries in master listing JSONs.")
    parser.add_argument("-f", "--file", help="Path to specific target JSON file")
    args = parser.parse_args()

    run_cleanup(args.file)