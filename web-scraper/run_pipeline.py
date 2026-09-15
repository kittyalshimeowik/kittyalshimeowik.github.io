import argparse
import subprocess
import sys
import os
from datetime import datetime

# Define paths to your scripts relative to the root directory
SCRAPER_SCRIPT = os.path.join("web-scraper", "fb_in_feed_tab_scraper.py")
GENERATOR_SCRIPT = os.path.join("web-scraper", "generate_site_data.py")

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
    # Set up argument parsing for command-line control
    parser = argparse.ArgumentParser(description="Run the Armenia Real Estate Data Pipeline.")
    parser.add_argument(
        "-t", "--time-limit", 
        type=int, 
        default=None, 
        help="Max scraping time allowed per Facebook group (in minutes). Uses default config if omitted."
    )
    args = parser.parse_args()

    start_time = datetime.now()
    print("🚀 Starting Armenia Real Estate Data Pipeline...")
    
    if args.time_limit:
        print(f"⏱️ Time limit configured: {args.time_limit} minutes max per group.")
    else:
        print("⏱️ Using default config settings for scraping duration.")

    # Prepare extra arguments for the scraper script if passed
    scraper_args = []
    if args.time_limit:
        # Assuming your scraper script accepts '--time-limit' or similar flag. 
        # Adjust '--time-limit' below if your scraper uses a different argument name (e.g., '--duration').
        scraper_args.extend(["--time-limit", str(args.time_limit)])

    # Step 1: Run the Facebook In-Feed Scraper
    scraper_success = run_step(SCRAPER_SCRIPT, "Facebook Feed Scraper", extra_args=scraper_args)
    if not scraper_success:
        print("\n❌ Pipeline aborted due to scraper failure.", file=sys.stderr)
        sys.exit(1)

    # Step 2: Run the Website Data Generator
    generator_success = run_step(GENERATOR_SCRIPT, "Website Listings Data Generator")
    if not generator_success:
        print("\n❌ Pipeline aborted due to data generation failure.", file=sys.stderr)
        sys.exit(1)

    elapsed = datetime.now() - start_time
    print(f"\n✨ Pipeline finished successfully in {elapsed.total_seconds():.2f} seconds!")
    print("🌐 Your website data is now updated and ready to display.")

if __name__ == "__main__":
    main()