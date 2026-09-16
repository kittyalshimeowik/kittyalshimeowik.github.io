# scrapers/facebook/metadata_storage.py

import os
import json
import random
from datetime import datetime
from scrapers.facebook.utilities.fb_utils import normalize_url, extract_post_id

CATEGORY_TRANSLATION_MAP = {
    "Apartment": "Apartment",
    "House": "House",
    "Land": "Land",
    "Media-Only": "Media-Only",
    "General / Unclassified": "General"
}

LISTING_TRANSLATION_MAP = {
    "Rent": "Rent",
    "Sale": "Sale",
    "Unknown": "General"
}


def get_group_metadata_file_path(metadata_dir, group_id):
    return os.path.join(metadata_dir, f"groups_metadata_{group_id}.json")


def get_group_file_path(output_dir, group_id):
    return os.path.join(output_dir, f"extracted_housing_posts_{group_id}.json")


def load_target_groups(groups_config_file, metadata_dir):
    if not os.path.exists(groups_config_file):
        default_groups = ["445452547795422"]
        with open(groups_config_file, "w", encoding="utf-8") as f:
            json.dump(default_groups, f, indent=4)
    
    group_ids = []
    try:
        with open(groups_config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                group_ids = [str(item) for item in data]
    except Exception:
        group_ids = ["445452547795422"]

    structured_groups = []
    for g_id in group_ids:
        meta_path = get_group_metadata_file_path(metadata_dir, g_id)
        g_meta = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    g_meta = json.load(f)
            except Exception:
                pass

        structured_groups.append({
            "id": g_id,
            "name": g_meta.get("name", f"Group {g_id}"),
            "last_scraped": g_meta.get("last_scraped", None),
            "total_collected": g_meta.get("total_collected", 0)
        })
    return structured_groups


def update_group_config_status(metadata_dir, group_id, new_posts_count):
    meta_path = get_group_metadata_file_path(metadata_dir, group_id)
    metadata = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            pass

    metadata["last_scraped"] = datetime.now().isoformat()
    metadata["total_collected"] = metadata.get("total_collected", 0) + new_posts_count

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)


def calculate_dynamic_runtime(metadata_dir_or_meta, group_id=None, default_runtime=180.0):
    max_group_limit_sec = float(random.randint(720, 900))
    default_fallback_sec = min(default_runtime, max_group_limit_sec)

    # Support passing the metadata dict directly as the first argument (for unit testing)
    if isinstance(metadata_dir_or_meta, dict):
        group_meta = metadata_dir_or_meta
    elif group_id is not None:
        meta_path = get_group_metadata_file_path(metadata_dir_or_meta, str(group_id))
        if not os.path.exists(meta_path):
            return default_fallback_sec, 3
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                group_meta = json.load(f)
        except Exception:
            return default_fallback_sec, 3
    else:
        # If metadata_dir_or_meta is actually used as group_id_or_meta in old tests
        if isinstance(metadata_dir_or_meta, dict):
            group_meta = metadata_dir_or_meta
        else:
            return default_fallback_sec, 3

    benchmarks = group_meta.get("scroll_benchmarks", {})
    if not benchmarks:
        return default_fallback_sec, 3

    durations = [b.get("scroll_duration_seconds", 0) for b in benchmarks.values() if isinstance(b, dict)]
    if durations:
        avg_dur = sum(durations) / len(durations)
        return min(max(avg_dur, 45.0), max_group_limit_sec), 3

    return default_fallback_sec, 3

def score_post_data(post):
    score = 0
    if post.get("created_at"): score += 10
    if post.get("creation_timestamp"): score += 10
    score += len(post.get("prices", [])) * 5
    score += len(post.get("sizes_sqm", [])) * 5
    score += len(post.get("rooms", [])) * 5
    score += len(post.get("locations", [])) * 5
    score += len(post.get("phone_numbers", [])) * 5
    if post.get("property_category") in ["Apartment", "House", "Land"]:
        score += 15
    score += len(post.get("full_text", "")) / 100 
    return score


def load_dataset_for_group(output_dir, group_id):
    file_path = get_group_file_path(output_dir, group_id)
    if not os.path.exists(file_path):
        return [], set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        posts_by_id = {}
        for post in data:
            post["url"] = normalize_url(post.get("url", ""))
            post_id = extract_post_id(post["url"])
            if post_id not in posts_by_id:
                posts_by_id[post_id] = []
            posts_by_id[post_id].append(post)

        unique_by_id = []
        for post_id, post_group in posts_by_id.items():
            post_group.sort(key=score_post_data, reverse=True)
            unique_by_id.append(post_group[0])

        urls = set(item["url"] for item in unique_by_id)
        return unique_by_id, urls
    except Exception:
        return [], set()


def save_post_to_memory_and_disk(output_dir, group_id, all_posts, processed_urls, post_record):
    norm_url = normalize_url(post_record["url"])
    post_record["url"] = norm_url
    
    existing_idx = None
    for i, p in enumerate(all_posts):
        if p["url"] == norm_url:
            existing_idx = i
            break
    
    file_path = get_group_file_path(output_dir, group_id)
    if existing_idx is None:
        processed_urls.add(norm_url)
        all_posts.append(post_record)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=4)
        return "new"
    else:
        if score_post_data(post_record) > score_post_data(all_posts[existing_idx]):
            all_posts[existing_idx] = post_record
            processed_urls.add(norm_url)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(all_posts, f, ensure_ascii=False, indent=4)
            return "updated"
    return None


def update_group_metadata(metadata_dir, group_id, group_name, session_posts, session_duration_sec):
    meta_path = get_group_metadata_file_path(metadata_dir, group_id)
    metadata = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    metadata = loaded
        except Exception:
            pass

    metadata["name"] = group_name
    metadata.pop("categories", None)
    metadata.pop("listing_types", None)
    
    if "summary_title" not in metadata:
        metadata["summary_title"] = f"Group {group_id}"
    if "primary_focus" not in metadata:
        metadata["primary_focus"] = {"listing_type": "Unknown", "property_category": "General", "percentage": 0.0}
    if "avg_scroll_time_1_day_sec" not in metadata:
        metadata["avg_scroll_time_1_day_sec"] = 180.0

    distributions = metadata.get("distributions", {})

    for post in session_posts:
        cat = post.get("property_category", "General / Unclassified")
        l_type = post.get("listing_type", "Unknown")
        combo_key = f"{l_type} - {cat}"
        distributions[combo_key] = distributions.get(combo_key, 0) + 1

    metadata["distributions"] = distributions

    total_posts_counted = sum(distributions.values())
    if total_posts_counted > 0:
        sorted_combos = sorted(distributions.items(), key=lambda x: x[1], reverse=True)
        top_combo_name, top_count = sorted_combos[0]
        
        for combo_name, count in sorted_combos:
            if "General / Unclassified" not in combo_name and "Media-Only" not in combo_name and "Unknown" not in combo_name:
                top_combo_name = combo_name
                top_count = count
                break

        pct = round((top_count / total_posts_counted) * 100, 1)
        
        parts = top_combo_name.split(" - ")
        raw_l_type = parts[0] if len(parts) > 0 else "Unknown"
        raw_cat = parts[1] if len(parts) > 1 else "General"
        
        l_type_val = LISTING_TRANSLATION_MAP.get(raw_l_type, raw_l_type)
        cat_val = CATEGORY_TRANSLATION_MAP.get(raw_cat, raw_cat)

        metadata["primary_focus"] = {
            "listing_type": l_type_val,
            "property_category": cat_val,
            "percentage": pct
        }
        
        if l_type_val != "General" and cat_val != "General" and cat_val != "Media-Only":
            metadata["summary_title"] = f"{cat_val}s for {l_type_val}" if not cat_val.endswith("s") else f"{cat_val} for {l_type_val}"
        else:
            metadata["summary_title"] = f"Group {group_id} Activity"

    today_str = datetime.now().strftime("%Y-%m-%d")
    benchmarks = metadata.get("scroll_benchmarks", {})
    
    now_ts = datetime.now().timestamp()
    valid_ages_hours = []
    for p in session_posts:
        ts = p.get("creation_timestamp")
        if ts and ts <= now_ts:
            age_hrs = (now_ts - ts) / 3600.0
            if 0 <= age_hrs <= 720:
                valid_ages_hours.append(age_hrs)

    if valid_ages_hours:
        valid_ages_hours.sort(reverse=True)
        idx = int(len(valid_ages_hours) * 0.10) if len(valid_ages_hours) >= 10 else 0
        effective_oldest_age = valid_ages_hours[idx]

        benchmarks[today_str] = {
            "scroll_duration_seconds": session_duration_sec,
            "oldest_post_age_hours": round(effective_oldest_age, 2),
            "posts_scanned": len(session_posts)
        }

    if len(benchmarks) > 3:
        sorted_dates = sorted(benchmarks.keys())
        while len(sorted_dates) > 3:
            oldest_key = sorted_dates.pop(0)
            benchmarks.pop(oldest_key, None)

    metadata["scroll_benchmarks"] = benchmarks

    calculated_1_day_times = []
    for b in benchmarks.values():
        duration = b.get("scroll_duration_seconds", 0)
        age_hrs = b.get("oldest_post_age_hours", 0)
        if age_hrs > 0:
            one_day_normalized = (duration / age_hrs) * 24
            calculated_1_day_times.append(one_day_normalized)

    if calculated_1_day_times:
        metadata["avg_scroll_time_1_day_sec"] = round(sum(calculated_1_day_times) / len(calculated_1_day_times), 1)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)