import argparse
import subprocess
import sys
import os
from datetime import datetime

# Fix for Windows console encoding issues with emojis
if os.name == 'nt':
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

# Define paths to your scripts relative to the project root directory
FB_SCRAPER_SCRIPT = os.path.join("scrapers", "facebook", "fb_scraper.py")
LIST_AM_SCRAPER_SCRIPT = os.path.join("scrapers", "listam", "list_am_scraper.py") # Updated folder name here
GENERATOR_SCRIPT = os.path.join("scrapers", "processors", "generate_site_data.py")
CLEANUP_SCRIPT = os.path.join("scrapers", "processors", "cleanup_master_listings.py")

def run_step(script_path, description, extra_args=None):
    """Helper function to run a script using the current Python environment."""
    cmd = [sys.executable, script_path]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'='*50}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] STARTING: {description}")
    print(f"Executing: {' '.join(cmd)}")
    print(f"{'='*50}\n")

    try:
        subprocess.run(cmd, check=True, text=True)
        print(f"\n[SUCCESS] {description} completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] {description} failed with exit code {e.returncode}.", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"\n[ERROR] Could not find the script at: {script_path}", file=sys.stderr)
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
    args = parser.parse_args()

    start_time = datetime.now()
    print("🚀 Starting Armenia Real Estate Data Pipeline...")

    # Step 1: Run Scrapers (skipped if --no-scrape flag is provided)
    if not args.no_scrape:
        if args.time_limit:
            print(f"⏱️ Time limit configured: {args.time_limit} minutes max per target.")
        else:
            print("⏱️ Using default config settings for scraping duration.")

        scraper_args = []
        if args.time_limit:
            scraper_args.extend(["--time-limit", str(args.time_limit)])

        # 1a. Run List.am Scraper
        list_am_success = run_step(LIST_AM_SCRAPER_SCRIPT, "List.am Scraper", extra_args=scraper_args)
        if not list_am_success:
            print("\n❌ Pipeline aborted due to List.am scraper failure.", file=sys.stderr)
            sys.exit(1)

        # 1b. Run Facebook Scraper
        fb_success = run_step(FB_SCRAPER_SCRIPT, "Facebook Feed Scraper", extra_args=scraper_args)
        if not fb_success:
            print("\n❌ Pipeline aborted due to Facebook scraper failure.", file=sys.stderr)
            sys.exit(1)
            
    else:
        print("⏩ Skipping scraping phase (--no-scrape requested).")

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
        
    elapsed = datetime.now() - start_time
    print(f"\n✨ Pipeline finished successfully in {elapsed.total_seconds():.2f} seconds!")
    print("🌐 Your website data is now updated and ready to display.")

if __name__ == "__main__":
    main()