import argparse
import subprocess
import sys
import os
from datetime import datetime

from scrapers.utilities.env_utils import ensure_utf8_output, get_venv_python
from scrapers.utilities.logger import get_logger, print_log_diagnostic_report

ensure_utf8_output()
logger = get_logger("pipeline")

# Define core processing scripts
BACKFILL_SCRIPT = "run_backfill.py"
GENERATOR_SCRIPT = os.path.join("scrapers", "processors", "generate_site_data.py")
CLEANUP_SCRIPT = os.path.join("scrapers", "processors", "cleanup_master_listings.py")

from scrapers.platforms.registry import get_all_platforms, get_platform, list_supported_platforms

def run_step(script_path, description, extra_args=None):
    """Helper function to run a script using the virtual environment or current Python."""
    cmd = [get_venv_python(), script_path]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'='*50}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] STARTING: {description}")
    print(f"Executing: {' '.join(cmd)}")
    print(f"{'='*50}\n")
    logger.info(f"Starting step: {description} | Executing: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True, text=True)
        print(f"\n[SUCCESS] {description} completed successfully.")
        logger.info(f"Step '{description}' completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] {description} failed with exit code {e.returncode}.", file=sys.stderr)
        logger.error(f"Step '{description}' failed with exit code {e.returncode}.")
        return False
    except FileNotFoundError:
        print(f"\n[ERROR] Could not find the script at: {script_path}", file=sys.stderr)
        logger.error(f"Could not find script at: {script_path}")
        return False

def manage_pipeline_storage():
    """Consolidates newly scraped data into SQLite, archives transient JSONs, and optimizes storage."""
    print(f"\n{'='*50}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] STARTING: Storage Management & Database Optimization")
    print(f"{'='*50}\n")
    try:
        from scrapers.utilities.storage import ListingsStorage
        import zipfile

        with ListingsStorage() as storage:
            # Ingest any loose JSON files created during scraping into SQLite
            stats = storage.migrate_from_json_directories()
            if stats.get("records_migrated", 0) > 0:
                print(f"📥 Ingested {stats['records_migrated']} records from {stats['files_processed']} loose JSON files into SQLite.")

            # Archive and clean transient loose JSON files to prevent disk clutter
            zip_path = os.path.join("scrapers", "data", "raw_json_legacy_archive.zip")
            os.makedirs(os.path.dirname(zip_path), exist_ok=True)
            loose_files = []
            for root, _, files in os.walk("scrapers"):
                if "housing_posts_data" in root:
                    for f in files:
                        if f.endswith(".json"):
                            loose_files.append(os.path.join(root, f))
            if os.path.exists(os.path.join("scrapers", "processors", "dedup_cache.json")):
                loose_files.append(os.path.join("scrapers", "processors", "dedup_cache.json"))

            if loose_files:
                mode = 'a' if os.path.exists(zip_path) else 'w'
                with zipfile.ZipFile(zip_path, mode, zipfile.ZIP_DEFLATED) as zf:
                    existing_names = set(zf.namelist())
                    for fp in loose_files:
                        arcname = os.path.relpath(fp, "scrapers").replace("\\", "/")
                        if arcname not in existing_names:
                            zf.write(fp, arcname)
                        try:
                            os.remove(fp)
                        except OSError:
                            pass
                print(f"📦 Archived and cleaned {len(loose_files)} transient JSON files into {zip_path}.")

            # Optimize database query planner
            storage.optimize_db()
            total_active = storage.count_listings(active_only=True)
            db_size_kb = os.path.getsize(storage.db_path) / 1024 if os.path.exists(storage.db_path) else 0
            print(f"💾 Storage Status: SQLite Database healthy ({total_active} active listings, {db_size_kb:.1f} KB).")
        return True
    except Exception as e:
        print(f"⚠️ Storage management warning: {e}", file=sys.stderr)
        return False


def auto_git_push(commit_message="Auto-update listings and site data"):
    """Helper function to stage, commit, and push changes to GitHub."""
    print(f"\n{'='*50}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] STARTING: Git Sync")
    try:
        # Stage master output files and tracked public website assets
        subprocess.run(["git", "add", "scrapers/processors/master_listings_json/"], check=True)
        for asset in ["index.html", "script.js", "style.css", "translations.js", "docs", "README.md", ".gitignore", "run_pipeline.py", "scrapers/"]:
            if os.path.exists(asset):
                subprocess.run(["git", "add", asset], check=False)
        
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        if not status.stdout.strip():
            print("ℹ️ No changes to commit.")
            return True

        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push"], check=True)
        print("\n[SUCCESS] Git repository synced and pushed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Git automation failed with exit code {e.returncode}.", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Run the Armenia Real Estate Data Pipeline.")
    parser.add_argument(
        "-t", "--time-limit", 
        type=float, 
        default=None, 
        help="Max scraping time allowed per group/category (in minutes)."
    )
    parser.add_argument(
        "-ns", "--no-scrape",
        action="store_true",
        help="Skip scraping phase and directly run site data generation, re-parsing, and cleanup."
    )
    parser.add_argument(
        "-np", "--no-push",
        action="store_true",
        help="Skip staging, committing, and pushing changes to GitHub."
    )
    parser.add_argument(
        "-p", "--platform",
        type=str,
        default="all",
        help=f"Target platform: {list_supported_platforms() + ['all']} (default: all)"
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Run full backfill (photos + translations) across platforms."
    )
    parser.add_argument(
        "--backfill-photos", "--backfill-fb-photos",
        action="store_true",
        dest="backfill_photos",
        help="Run photo backfill across platforms."
    )
    parser.add_argument(
        "--backfill-translations",
        action="store_true",
        help="Run English translation backfill for listings lacking translation."
    )
    parser.add_argument(
        "-s", "--scrape",
        action="store_true",
        help="Explicitly run scraping phase even when backfill flags are specified."
    )
    parser.add_argument(
        "--status", "--audit",
        action="store_true",
        dest="show_status",
        help="Display real-time completeness and backfill status dashboard."
    )
    parser.add_argument(
        "--logs", "--analyze-logs",
        action="store_true",
        dest="show_logs",
        help="Analyze recent system logs for errors, rate limits, and common issues."
    )
    args = parser.parse_args()

    if args.show_logs:
        print_log_diagnostic_report()
        return

    if args.show_status:
        from scrapers.processors.track_backfills import print_dashboard
        print_dashboard()
        return

    is_backfill_mode = bool(args.backfill or args.backfill_photos or args.backfill_translations)
    should_scrape = (not args.no_scrape) and (args.scrape or not is_backfill_mode)

    start_time = datetime.now()
    logger.info(f"Pipeline started: scrape={should_scrape}, backfill={is_backfill_mode}, platform={args.platform}")
    print("🚀 Starting Armenia Real Estate Data Pipeline...")

    # Step 1: Run Scrapers (skipped if in decoupled backfill mode or --no-scrape)
    if should_scrape:
        if args.time_limit:
            print(f"⏱️ Time limit configured: {args.time_limit} minutes max per target.")
        else:
            print("⏱️ Using default config settings for scraping duration.")

        scraper_args = []
        if args.time_limit:
            scraper_args.extend(["--time-limit", str(args.time_limit)])

        # Determine target platforms dynamically
        all_platforms = get_all_platforms()
        if args.platform.lower() == "all":
            target_platforms = list(all_platforms.values())
        else:
            plat = get_platform(args.platform)
            if not plat:
                print(f"❌ Unknown platform '{args.platform}'. Supported: {list_supported_platforms()}", file=sys.stderr)
                sys.exit(1)
            target_platforms = [plat]

        for plat in target_platforms:
            script_path = plat.scraper_script_relpath
            if script_path and os.path.exists(script_path):
                success = run_step(script_path, f"{plat.display_name} Scraper", extra_args=scraper_args)
                if not success:
                    print(f"\n❌ Pipeline aborted due to {plat.display_name} scraper failure.", file=sys.stderr)
                    sys.exit(1)
            else:
                print(f"ℹ️ Platform '{plat.display_name}' has no active scraper script registered, skipping.")

    else:
        if is_backfill_mode:
            print("⏩ Decoupled Backfill Mode: Skipping scraping phase because backfill was requested.")
            print("   (Scraping takes longer; backfills operate directly on the database & target listings.)")
        else:
            print("⏩ Skipping scraping phase (--no-scrape requested).")

    # Step 1c: Optional Multi-Platform Backfills
    if args.backfill:
        bf_args = ["--skip-site-gen"]
        if args.platform != "all":
            bf_args.extend(["--platform", args.platform])
        run_step(BACKFILL_SCRIPT, "Unified Multi-Platform Backfill", extra_args=bf_args)
    else:
        if args.backfill_photos:
            bf_args = ["--photos", "--skip-site-gen"]
            if args.platform != "all":
                bf_args.extend(["--platform", args.platform])
            run_step(BACKFILL_SCRIPT, "Photos Backfill", extra_args=bf_args)

        if args.backfill_translations:
            bf_args = ["--translations", "--skip-site-gen"]
            if args.platform != "all":
                bf_args.extend(["--platform", args.platform])
            run_step(BACKFILL_SCRIPT, "Translations Backfill", extra_args=bf_args)

    # Step 2: Run the Modular Website Data Generator
    generator_success = run_step(GENERATOR_SCRIPT, "Website Listings Data Generator")
    if not generator_success:
        print("\n❌ Pipeline aborted due to data generation failure.", file=sys.stderr)
        sys.exit(1)
    
    # Step 3: Run Post-Processing Cleanup
    cleanup_success = run_step(CLEANUP_SCRIPT, "Post-Processing Cleanup")
    if not cleanup_success:
        print("\n❌ Pipeline aborted due to cleanup failure.", file=sys.stderr)
        sys.exit(1)
    
    # Step 4: Storage Management & SQLite Optimization
    manage_pipeline_storage()

    # Step 5: Auto Git Push (skipped if --no-push flag is provided)
    if not args.no_push:
        git_success = auto_git_push()
        if not git_success:
            print("\n⚠️ Pipeline finished, but Git push failed.", file=sys.stderr)
    else:
        print("\n⏩ Skipping Git sync (--no-push requested).")
        
    elapsed = datetime.now() - start_time
    logger.info(f"Pipeline finished successfully in {elapsed.total_seconds():.2f} seconds.")
    print(f"\n✨ Pipeline finished successfully in {elapsed.total_seconds():.2f} seconds!")
    print("🌐 Your website data is now updated and ready to display.")

if __name__ == "__main__":
    main()