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
from scrapers.utilities.translator import is_genuine_translation

STATUS_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "scrapers", "data", "backfill_status.json")
MASTER_DIR = os.path.join(SCRIPT_DIR, "master_listings_json")


def format_progress_bar(percentage, length=20):
    """Generates a text progress bar."""
    filled = int(length * (percentage / 100.0))
    return f"[{'#' * filled}{'.' * (length - filled)}] {percentage:5.1f}%"


def generate_backfill_report(export_json=True):
    with ListingsStorage() as storage:
        cur = storage.conn.cursor()

        # Query all records with statuses
        cur.execute("""
            SELECT canonical_id, source, url, is_active,
                   photo_status, translation_status,
                   (CASE WHEN images_json IS NOT NULL AND length(images_json) > 2 THEN 1 ELSE 0 END) as has_photos,
                   (CASE WHEN photos_checked_at IS NOT NULL THEN 1 ELSE 0 END) as photos_checked,
                   full_text, full_text_en
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
                "photo_states": {"SUCCESS": 0, "NO_PHOTO": 0, "RATE_LIMITED": 0, "ERROR": 0, "PENDING": 0},
                "trans_states": {"SUCCESS": 0, "NOT_NEEDED": 0, "RATE_LIMITED": 0, "ERROR": 0, "PENDING": 0},
                "with_photos_active": 0,
                "with_translation_active": 0,
                "retry_photos_active": 0,
                "retry_translation_active": 0
            }

        s = stats_by_source[src]
        s["total"] += 1
        is_act = (r["is_active"] == 1)
        if is_act:
            s["active"] += 1

            p_st = r["photo_status"] or ("SUCCESS" if r["has_photos"] else ("NO_PHOTO" if r["photos_checked"] else "PENDING"))
            t_st = r["translation_status"] or ("SUCCESS" if is_genuine_translation(r["full_text"], r["full_text_en"]) else "PENDING")

            s["photo_states"][p_st] = s["photo_states"].get(p_st, 0) + 1
            s["trans_states"][t_st] = s["trans_states"].get(t_st, 0) + 1

            if p_st == "SUCCESS":
                s["with_photos_active"] += 1
            elif p_st in ["PENDING", "RATE_LIMITED", "ERROR"]:
                s["retry_photos_active"] += 1
                leftovers_photos.append({"id": r["canonical_id"], "source": src, "url": r["url"], "status": p_st})

            if t_st == "SUCCESS":
                s["with_translation_active"] += 1
            elif t_st in ["PENDING", "RATE_LIMITED", "ERROR"]:
                s["retry_translation_active"] += 1
                leftovers_translations.append({"id": r["canonical_id"], "source": src, "url": r["url"], "status": t_st})

    # Website master feeds check (1:1 with website UI)
    website_stats = {}
    feed_files = [
        "all_for_sale_rent.json",
        "apartments_for_sale.json",
        "houses_for_sale.json",
        "land_for_sale.json",
        "apartments_for_rent.json",
        "houses_for_rent.json"
    ]
    for fname in feed_files:
        fpath = os.path.join(MASTER_DIR, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    feed_data = json.load(f)
                    total_feed = len(feed_data)
                    feed_photos = sum(1 for item in feed_data if item.get("images") and len(item["images"]) > 0 and item["images"][0].strip())
                    feed_trans = sum(1 for item in feed_data if is_genuine_translation(item.get("full_text"), item.get("full_text_en")))
                    feed_both = sum(1 for item in feed_data if (item.get("images") and len(item["images"]) > 0 and item["images"][0].strip()) and is_genuine_translation(item.get("full_text"), item.get("full_text_en")))
                    website_stats[fname] = {
                        "count": total_feed,
                        "with_photos": feed_photos,
                        "with_translation": feed_trans,
                        "with_both": feed_both,
                        "photo_pct": round(feed_photos / total_feed * 100.0, 1) if total_feed else 0,
                        "trans_pct": round(feed_trans / total_feed * 100.0, 1) if total_feed else 0,
                        "both_pct": round(feed_both / total_feed * 100.0, 1) if total_feed else 0
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

    print("\n" + "=" * 75)
    print("  📊 ARMENIA REAL ESTATE HUB - DATA COMPLETENESS & BACKFILL TRACKER")
    print(f"  🕒 Status generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 75)

    print("\n📦 [1] SQLite Database Inventory & States (All 2,608 Active Records):")
    print("-" * 75)
    print(f" {'Source':<10} | {'Active':<6} | {'Photos (OK / None / Retry)':<28} | {'Translations (OK / Skip / Retry)':<28}")
    print("-" * 75)

    total_active = 0
    total_photos_ok = 0
    total_photos_none = 0
    total_photos_retry = 0

    total_trans_ok = 0
    total_trans_skip = 0
    total_trans_retry = 0

    for src, data in db_sources.items():
        act = data["active"]
        total_active += act

        p_st = data["photo_states"]
        p_ok = p_st.get("SUCCESS", 0)
        p_none = p_st.get("NO_PHOTO", 0)
        p_retry = p_st.get("PENDING", 0) + p_st.get("RATE_LIMITED", 0) + p_st.get("ERROR", 0)

        total_photos_ok += p_ok
        total_photos_none += p_none
        total_photos_retry += p_retry

        t_st = data["trans_states"]
        t_ok = t_st.get("SUCCESS", 0)
        t_skip = t_st.get("NOT_NEEDED", 0)
        t_retry = t_st.get("PENDING", 0) + t_st.get("RATE_LIMITED", 0) + t_st.get("ERROR", 0)

        total_trans_ok += t_ok
        total_trans_skip += t_skip
        total_trans_retry += t_retry

        p_str = f"{p_ok} OK | {p_none} NoImg | {p_retry} Retry"
        t_str = f"{t_ok} OK | {t_skip} N/A | {t_retry} Retry"

        print(f" {src:<10} | {act:<6} | {p_str:<28} | {t_str:<28}")

    print("-" * 75)
    ov_p_str = f"{total_photos_ok} OK | {total_photos_none} NoImg | {total_photos_retry} Retry"
    ov_t_str = f"{total_trans_ok} OK | {total_trans_skip} N/A | {total_trans_retry} Retry"
    print(f" {'OVERALL':<10} | {total_active:<6} | {ov_p_str:<28} | {ov_t_str:<28}")

    main_feed = web_feeds.get("all_for_sale_rent.json")
    if main_feed:
        print("\n🌐 [2] Website Public Catalog (`all_for_sale_rent.json` - 1:1 Match with Web UI):")
        print("-" * 75)
        m_count = main_feed["count"]
        m_p = main_feed["with_photos"]
        m_t = main_feed["with_translation"]
        m_both = main_feed["with_both"]
        print(f" • Total Catalog Listings : {m_count} (active verified classified listings)")
        print(f" • 📷 Listings With Photos  : {m_p} / {m_count} ({main_feed['photo_pct']:.1f}%)")
        print(f" • 🌐 Listings Translated   : {m_t} / {m_count} ({main_feed['trans_pct']:.1f}%)")
        print(f" • 📷+🌐 Both Photos & Trans : {m_both} / {m_count} ({main_feed['both_pct']:.1f}%)")

        sub_feeds = [k for k in web_feeds.keys() if k != "all_for_sale_rent.json"]
        if sub_feeds:
            print("\n   Category Sub-Feeds Breakdown:")
            for fname in sub_feeds:
                fstats = web_feeds[fname]
                f_cnt = fstats["count"]
                f_p = fstats["with_photos"]
                f_t = fstats["with_translation"]
                print(f"   • {fname:<25}: {f_cnt:<4} | 📸 {f_p}/{f_cnt} ({fstats['photo_pct']:.0f}%) | 🌐 {f_t}/{f_cnt} ({fstats['trans_pct']:.0f}%)")

    print("\n🎯 [3] Leftovers Requiring Backfill (Pending / Errored / Rate-Limited):")
    print("-" * 75)
    for src_name, src_stats in db_sources.items():
        if src_name == "Unknown":
            continue
        p_st = src_stats["photo_states"]
        t_st = src_stats["trans_states"]
        p_pend = p_st.get("PENDING", 0)
        p_rl = p_st.get("RATE_LIMITED", 0)
        p_err = p_st.get("ERROR", 0)
        p_retry_tot = p_pend + p_rl + p_err

        t_pend = t_st.get("PENDING", 0)
        t_rl = t_st.get("RATE_LIMITED", 0)
        t_err = t_st.get("ERROR", 0)
        t_retry_tot = t_pend + t_rl + t_err

        print(f" • {src_name:<12} Photos To Fetch: {p_retry_tot:<5} ({p_pend} new, {p_rl} rate-limited, {p_err} errored)")
        print(f"              Translations To Fetch: {t_retry_tot:<5} ({t_pend} new, {t_rl} rate-limited, {t_err} errored)")

    print("\n🛠️ [4] Unified Multi-Platform Backfill Commands:")
    print("-" * 75)
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
    print("=" * 75 + "\n")


if __name__ == "__main__":
    print_dashboard()
