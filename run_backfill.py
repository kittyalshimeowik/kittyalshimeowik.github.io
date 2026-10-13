#!/usr/bin/env python3
"""
Unified Multi-Platform Backfiller for Armenia Real Estate Hub.
Supports photo & translation backfilling across all platforms (Facebook, List.am, and future extensions).

Usage:
    python run_backfill.py                   # Full backfill (photos + translations, all platforms)
    python run_backfill.py --photos          # Backfill photos only across all platforms
    python run_backfill.py --translations    # Backfill translations only across all platforms
    python run_backfill.py --platform fb     # Backfill only Facebook
    python run_backfill.py --platform listam # Backfill only List.am
    python run_backfill.py --status          # Display data completeness dashboard
    python run_backfill.py --limit 25        # Process up to 25 items per platform
"""

import os
import sys
import argparse
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.env_utils import ensure_utf8_output
from scrapers.utilities.logger import get_logger, print_log_diagnostic_report
ensure_utf8_output()
logger = get_logger("backfill")

from scrapers.utilities.storage import ListingsStorage
from scrapers.backfill.registry import (
    get_all_platform_backfillers,
    get_platform_backfiller,
    list_supported_platforms
)
from scrapers.utilities.backfill_translations import run_translation_backfill
from scrapers.processors.track_backfills import print_dashboard
from scrapers.processors.generate_site_data import generate_site_data


def main():
    parser = argparse.ArgumentParser(
        description="Unified Multi-Platform Backfill Utility (Photos & Translations)"
    )
    parser.add_argument(
        "-p", "--platform",
        type=str,
        default="all",
        help=f"Target platform: {list_supported_platforms() + ['all']} (default: all)"
    )
    parser.add_argument(
        "--photos",
        action="store_true",
        help="Run photo backfill only"
    )
    parser.add_argument(
        "--translations",
        action="store_true",
        help="Run translation backfill only"
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=None,
        help="Maximum number of items to process per platform"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include inactive listings in backfill (default: active display listings only)"
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run browser visibly (not headless)"
    )
    parser.add_argument(
        "--status", "--audit",
        action="store_true",
        dest="show_status",
        help="Display data completeness & leftovers dashboard and exit"
    )
    parser.add_argument(
        "--logs", "--analyze-logs",
        action="store_true",
        dest="show_logs",
        help="Analyze recent system logs for errors, rate limits, and common issues"
    )
    parser.add_argument(
        "--skip-site-gen",
        action="store_true",
        help="Skip regenerating website JSON feeds after backfill"
    )

    args = parser.parse_args()

    # If --logs requested, print diagnostics and exit
    if args.show_logs:
        print_log_diagnostic_report()
        return

    # If --status requested, print dashboard and return
    if args.show_status:
        print_dashboard()
        return

    start_time = datetime.now()
    logger.info(f"Backfill runner initiated: platform={args.platform}, photos={args.photos}, translations={args.translations}, limit={args.limit}")
    print("=" * 70)
    print("🚀 UNIFIED MULTI-PLATFORM BACKFILL RUNNER")
    print(f"🕒 Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📦 Supported platforms: {', '.join(list_supported_platforms())}")
    print("=" * 70)

    # Determine tasks to execute
    do_photos = True
    do_translations = True
    if args.photos and not args.translations:
        do_translations = False
    elif args.translations and not args.photos:
        do_photos = False

    # Determine target platforms
    selected_platform = args.platform.lower().replace(".", "").replace("-", "")
    all_backfillers = get_all_platform_backfillers()

    targets = {}
    if selected_platform in ["all", "any"]:
        targets = all_backfillers
    else:
        for key, backfiller in all_backfillers.items():
            if selected_platform in key or key in selected_platform:
                targets[key] = backfiller
        if not targets:
            print(f"❌ Unknown platform '{args.platform}'. Supported: {list_supported_platforms()}")
            sys.exit(1)

    print(f"🎯 Selected Platforms: {', '.join(b.platform_name for b in targets.values())}")
    print(f"📋 Mode: Photos={do_photos}, Translations={do_translations}")
    if args.limit:
        print(f"⏱️ Limit per platform: {args.limit} items")
    print("-" * 70)

    run_stats = {
        "photos": {},
        "translations": {}
    }

    with ListingsStorage() as storage:
        # Self-healing: ensure all legacy or unclassified records are properly tagged
        storage.normalize_unclassified_sources()

        # Phase 1: Photo Backfill
        if do_photos:
            print("\n📷 [Phase 1/2] Photo Backfill Phase")
            for key, backfiller in targets.items():
                p_name = backfiller.platform_name
                pending_count = backfiller.get_pending_photos_count(storage, active_only=not args.all)
                print(f"\n--- Platform: {p_name} ({pending_count} pending photos) ---")

                if pending_count > 0:
                    res = backfiller.backfill_photos(
                        storage=storage,
                        limit=args.limit,
                        headless=not args.visible,
                        active_only=not args.all
                    )
                    run_stats["photos"][p_name] = res
                else:
                    print(f"✅ {p_name} has no listings missing photos.")
                    run_stats["photos"][p_name] = {"processed": 0, "photos_found": 0, "remaining_in_db": 0}

        # Phase 2: Translation Backfill
        if do_translations:
            print("\n🌐 [Phase 2/2] English Translation Backfill Phase")
            for key, backfiller in targets.items():
                p_name = backfiller.platform_name
                pending_trans = backfiller.get_pending_translations_count(storage, active_only=not args.all)
                print(f"\n--- Platform: {p_name} ({pending_trans} pending translations) ---")

                if pending_trans > 0:
                    res = run_translation_backfill(
                        source=p_name,
                        limit=args.limit,
                        active_only=not args.all,
                        regenerate_site_data=False
                    )
                    run_stats["translations"][p_name] = res
                else:
                    print(f"✅ {p_name} has no listings missing English translation.")
                    run_stats["translations"][p_name] = {"processed": 0, "translated": 0, "remaining_in_db": 0}

    # Phase 3: Regenerate public website feeds
    if not args.skip_site_gen:
        print("\n" + "=" * 70)
        print("🔄 [Phase 3/3] Synchronizing Website Public Feeds...")
        print("=" * 70)
        generate_site_data()

    elapsed = datetime.now() - start_time
    print("\n" + "=" * 70)
    print("📋 BACKFILL EXECUTION SUMMARY (COMPLETED VS REMAINING)")
    print(f"⏱️ Total Execution Time: {elapsed.total_seconds():.1f}s")
    print("-" * 70)

    if do_photos and run_stats["photos"]:
        print("📸 Photos Backfill Completed This Run:")
        for p_name, r in run_stats["photos"].items():
            processed = r.get("processed", 0)
            photos = r.get("photos_found", 0)
            blocked = r.get("blocked_count", 0)
            remaining = r.get("remaining_in_db", "N/A")
            print(f"  • {p_name:<10}: {processed} processed | {photos} photos found | {blocked} rate-limited/blocked | Left in DB: {remaining}")

    if do_translations and run_stats["translations"]:
        print("\n🌐 Translations Backfill Completed This Run:")
        for p_name, r in run_stats["translations"].items():
            processed = r.get("processed", 0)
            trans = r.get("translated", 0)
            remaining = r.get("remaining_in_db", "N/A")
            print(f"  • {p_name:<10}: {processed} processed | {trans} translated | Left in DB: {remaining}")

    print("=" * 70)

    logger.info(f"Backfill run completed in {elapsed.total_seconds():.1f}s | Stats: {run_stats}")
    # Print summary dashboard
    print_dashboard()


if __name__ == "__main__":
    main()
