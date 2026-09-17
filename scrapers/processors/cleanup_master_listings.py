import os
import sys
import json
import io
import argparse
import unicodedata

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGET_FILE = os.path.join(SCRIPT_DIR, "master_listings_json", "all_for_sale_rent.json")

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def compute_record_score(item):
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
    full_text = item.get("full_text") or ""
    score += len(full_text) / 100.0
    return score

def normalize_text(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFC', text).lower().strip()
    return " ".join(text.split())

def get_content_signature(item):
    phones = sorted(list(set(item.get("phone_numbers") or [])))
    
    prices = tuple(sorted([str(p.get("amount_amd")) for p in item.get("prices", []) if p.get("amount_amd")]))
    sizes = tuple(sorted([str(s) for s in (item.get("sizes_sqm") or [])]))
    rooms = tuple(sorted([str(r) for r in (item.get("rooms") or [])]))
    locs = tuple(sorted([str(l) for l in (item.get("locations") or [])]))
    
    text_key = normalize_text(item.get("full_text"))

    # Case A: Matches by Phone + Specs
    if phones and (prices or sizes or rooms):
        return f"phone_spec:{phones}|{prices}|{sizes}|{rooms}|{locs}"
    
    # Case B: Direct Text Hash/String Match
    if text_key and len(text_key) > 20:
        return f"text:{text_key}"

    return None

def deduplicate_records(listings):
    seen_signatures = {}
    print(f"🔍 Starting deduplication on {len(listings)} records...")

    for item in listings:
        sig = get_content_signature(item)
        score = compute_record_score(item)

        if not sig:
            # Preserve items with unique fallback IDs
            item_id = item.get("id") or id(item)
            seen_signatures[f"unmatched_{item_id}"] = (score, item)
            continue

        if sig in seen_signatures:
            existing_score, _ = seen_signatures[sig]
            if score > existing_score:
                seen_signatures[sig] = (score, item)
        else:
            seen_signatures[sig] = (score, item)

    cleaned_listings = [item for _, item in seen_signatures.values()]
    print(f"✨ Removed {len(listings) - len(cleaned_listings)} duplicates. Total unique: {len(cleaned_listings)}")

    return cleaned_listings

def run_cleanup(filepath=None, output_filepath=None):
    target_path = filepath or DEFAULT_TARGET_FILE
    out_path = output_filepath or target_path

    if not os.path.exists(target_path):
        print(f"❌ Target file not found: {target_path}")
        return

    print(f"[INFO] Reading listings file: {target_path}")
    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned_data = deduplicate_records(data)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print(f"💾 Clean dataset saved successfully to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up duplicate entries in master listing JSONs.")
    parser.add_argument("-f", "--file", help="Path to specific target JSON file")
    parser.add_argument("-o", "--out", help="Output path (prevents overwriting input)")
    args = parser.parse_args()

    run_cleanup(args.file, args.out)