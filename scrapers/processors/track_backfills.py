# scrapers/processors/track_backfills.py

import os
import sys
import json
from datetime import datetime

# Resolve Project Root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.env_utils import ensure_utf8_output
ensure_utf8_output()

from scrapers.utilities.storage import ListingsStorage

STATUS_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "scrapers", "data", "backfill_status.json")
MASTER_DIR = os.path.join(SCRIPT_DIR, "master_listings_json")


def format_progress_bar(percentage, length=20):
    """Generates a text progress bar."""
    filled = int(length * (percentage / 100.0))
    return f"[{'#' * filled}{'.' * (length - filled)}] {percentage:5.1f}%"


def generate_backfill_report(export_json=True):
    with ListingsStorage() as storage:
        cur = storage.conn.cursor()

        # Query all records
        cur.execute("""
            SELECT canonical_id, source, url, is_active,
                   (CASE WHEN images_json IS NOT NULL AND length(images_json) > 2 THEN 1 ELSE 0 END) as has_photos,
                   (CASE WHEN photos_checked_at IS NOT NULL THEN 1 ELSE 0 END) as photos_checked,
                   (CASE WHEN full_text_en IS NOT NULL AND length(trim(full_text_en)) > 5 THEN 1 ELSE 0 END) as has_translation,
                   (CASE WHEN full_text IS NOT NULL AND length(trim(full_text)) > 5 THEN 1 ELSE 0 END) as has_text
            FROM listings
        """)
        rows = cur.fetchall()

    stats_by_source = {}
    leftovers_photos = []
    leftovers_translations = []

    for r in rows:
        src = r["source"] or "Unknown"
        if src in ["Unknown", "unknown", ""] and r["url"]:
            url_low = str(r["url"]).lower()
            if "facebook.com" in url_low or "fb.com" in url_low:
                src = "Facebook"
            elif "list.am" in url_low:
                src = "List.am"

        if src not in stats_by_source:
            stats_by_source[src] = {
                "total": 0,
                "active": 0,
                "with_photos": 0,
                "with_photos_active": 0,
                "with_translation": 0,
                "with_translation_active": 0,
                "missing_photos_active": 0,
                "unchecked_photos_active": 0,
                "missing_translation_active": 0
            }

        s = stats_by_source[src]
        s["total"] += 1
        is_act = (r["is_active"] == 1)
        if is_act:
            s["active"] += 1

        if r["has_photos"]:
            s["with_photos"] += 1
            if is_act: s["with_photos_active"] += 1
        elif is_act:
            s["missing_photos_active"] += 1
            if not r["photos_checked"]:
                s["unchecked_photos_active"] += 1
                leftovers_photos.append({"id": r["canonical_id"], "source": src, "url": r["url"]})

        if r["has_translation"]:
            s["with_translation"] += 1
            if is_act: s["with_translation_active"] += 1
        elif is_act and r["has_text"]:
            s["missing_translation_active"] += 1
            leftovers_translations.append({"id": r["canonical_id"], "source": src, "url": r["url"]})

    # Website master feeds check
    website_stats = {}
    feed_files = ["all_for_sale_rent.json", "apartments_for_sale.json", "houses_for_sale.json", "land_for_sale.json"]
    for fname in feed_files:
        fpath = os.path.join(MASTER_DIR, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    feed_data = json.load(f)
                    total_feed = len(feed_data)
                    feed_photos = sum(1 for item in feed_data if item.get("images"))
                    feed_trans = sum(1 for item in feed_data if item.get("full_text_en"))
                    website_stats[fname] = {
                        "count": total_feed,
                        "with_photos": feed_photos,
                        "with_translation": feed_trans,
                        "photo_pct": round(feed_photos / total_feed * 100.0, 1) if total_feed else 0,
                        "trans_pct": round(feed_trans / total_feed * 100.0, 1) if total_feed else 0
                    }
            except Exception:
                pass

    report = {
        "timestamp": datetime.now().isoformat(),
        "database_by_source": stats_by_source,
        "website_feeds": website_stats,
        "leftovers_summary": {
            "total_active_missing_photos": len(leftovers_photos),
            "total_active_missing_translations": len(leftovers_translations),
        },
        "leftovers_sample": {
            "missing_photos": leftovers_photos[:50],
            "missing_translations": leftovers_translations[:50]
        }
    }

    if export_json:
        os.makedirs(os.path.dirname(STATUS_OUTPUT_PATH), exist_ok=True)
        with open(STATUS_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def print_dashboard():
    report = generate_backfill_report(export_json=True)
    db_sources = report["database_by_source"]
    web_feeds = report["website_feeds"]

    print("\n" + "=" * 70)
    print("  📊 ARMENIA REAL ESTATE HUB - DATA COMPLETENESS & BACKFILL TRACKER")
    print(f"  🕒 Status generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    print("\n📦 [1] SQLite Database Completeness (Active Listings):")
    print("-" * 70)
    print(f" {'Source':<12} | {'Active':<6} | {'Photos':<18} | {'Translations':<18}")
    print("-" * 70)

    total_active = 0
    total_photos = 0
    total_trans = 0

    for src, data in db_sources.items():
        act = data["active"]
        p_act = data["with_photos_active"]
        t_act = data["with_translation_active"]

        total_active += act
        total_photos += p_act
        total_trans += t_act

        p_pct = (p_act / act * 100.0) if act else 0.0
        t_pct = (t_act / act * 100.0) if act else 0.0

        p_bar = f"{p_act}/{act} ({p_pct:.0f}%)"
        t_bar = f"{t_act}/{act} ({t_pct:.0f}%)"

        print(f" {src:<12} | {act:<6} | {p_bar:<18} | {t_bar:<18}")

    print("-" * 70)
    overall_p_pct = (total_photos / total_active * 100.0) if total_active else 0.0
    overall_t_pct = (total_trans / total_active * 100.0) if total_active else 0.0
    print(f" {'OVERALL':<12} | {total_active:<6} | {total_photos}/{total_active} ({overall_p_pct:.0f}%)    | {total_trans}/{total_active} ({overall_t_pct:.0f}%)")

    if web_feeds:
        print("\n🌐 [2] Public Website Feeds (`master_listings_json/`):")
        print("-" * 70)
        for fname, fstats in web_feeds.items():
            print(f" • {fname:<25}: {fstats['count']} listings | 📸 Photos: {format_progress_bar(fstats['photo_pct'])} | 🌐 EN: {format_progress_bar(fstats['trans_pct'])}")

    print("\n🎯 [3] Leftovers Requiring Backfill (By Platform):")
    print("-" * 70)
    for src_name, src_stats in db_sources.items():
        if src_name == "Unknown":
            continue
        missing_p = src_stats.get("missing_photos_active", 0)
        unchecked_p = src_stats.get("unchecked_photos_active", 0)
        missing_t = src_stats.get("missing_translation_active", 0)
        print(f" • {src_name:<16} Unchecked Photos: {unchecked_p:<6} (Total without photos: {missing_p}) | Missing Translation: {missing_t:<6}")

    print("\n🛠️ [4] Unified Multi-Platform Backfill Commands:")
    print("-" * 70)
    print(" • Run Backfill (Photos & Translations, All Platforms):")
    print("     python run_backfill.py")
    print(" • Backfill Photos Only Across All Platforms:")
    print("     python run_backfill.py --photos")
    print(" • Backfill Translations Only Across All Platforms:")
    print("     python run_backfill.py --translations")
    print(" • Backfill Specific Platform (e.g., Facebook or List.am):")
    print("     python run_backfill.py --platform facebook")
    print("     python run_backfill.py --platform listam")
    print(" • Check Data Completeness & Leftovers:")
    print("     python run_backfill.py --status")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print_dashboard()
