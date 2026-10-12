#!/usr/bin/env python3
"""
CLI Runner for Website Screenshot Testing and Visual Regression.
Usage:
    python run_screenshot_tests.py                       # Run tests against baselines
    python run_screenshot_tests.py --update-baselines    # Capture & update golden baselines
    python run_screenshot_tests.py --scenarios desktop_home,mobile_view
    python run_screenshot_tests.py --list
"""

import argparse
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.env_utils import ensure_utf8_output, get_venv_python

ensure_utf8_output()


def main():
    parser = argparse.ArgumentParser(
        description="Visual Screenshot Testing and Regression Suite for Armenia Real Estate Hub."
    )
    parser.add_argument(
        "--update-baselines", "-u",
        action="store_true",
        help="Update or generate golden baseline screenshot images from the current run.",
    )
    parser.add_argument(
        "--scenarios", "-s",
        type=str,
        default=None,
        help="Comma-separated list of scenario IDs to run (e.g., --scenarios desktop_home,mobile_view).",
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.1,
        help="Allowed pixel mismatch threshold percentage before failing (default: 0.1%%).",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=10,
        help="Per-channel color tolerance for antialiasing noise (default: 10).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Launch browser in headed mode for visual observation (default: headless).",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Custom output directory for current screenshots and report (default: test_output/screenshots).",
    )
    parser.add_argument(
        "--baselines-dir", "-b",
        type=str,
        default=None,
        help="Custom directory for golden baseline screenshots (default: screenshot_tests/baselines).",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all registered test scenarios and exit.",
    )

    args = parser.parse_args()

    from screenshot_tests.scenarios import SCENARIOS
    from screenshot_tests.runner import ScreenshotTestRunner

    if args.list:
        print("=" * 65)
        print(" 📋 Available Screenshot Test Scenarios:")
        print("=" * 65)
        for s in SCENARIOS:
            vp = f"{s.viewport[0]}x{s.viewport[1]}"
            full = " (Full Page)" if s.full_page else ""
            elem = f" (Element: {s.element_selector})" if s.element_selector else ""
            mob = " [Mobile]" if s.is_mobile else ""
            print(f"  • {s.id:<25} {vp}{full}{elem}{mob}")
            print(f"    └─ {s.description}")
        print("=" * 65)
        sys.exit(0)

    scenario_ids = [sid.strip() for sid in args.scenarios.split(",") if sid.strip()] if args.scenarios else None

    runner = ScreenshotTestRunner(
        root_dir=PROJECT_ROOT,
        output_dir=args.output_dir,
        baselines_dir=args.baselines_dir,
        update_baselines=args.update_baselines,
        threshold_percent=args.threshold,
        color_tolerance=args.tolerance,
        headless=not args.headed,
    )

    summary = runner.run(scenario_ids=scenario_ids)

    if summary["success"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    proj_py = get_venv_python(__file__)
    if os.path.abspath(sys.executable).lower() != os.path.abspath(proj_py).lower():
        import subprocess
        result = subprocess.run([proj_py] + sys.argv, check=False)
        sys.exit(result.returncode)
    main()
