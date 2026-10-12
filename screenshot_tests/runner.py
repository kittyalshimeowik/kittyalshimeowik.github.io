"""
Test Runner Orchestrator for Visual Screenshot Testing.
Manages server lifecycle, Playwright browser execution, image captures, baseline comparisons,
and report generation.
"""

import os
import shutil
import time
from typing import Dict, List, Optional
from playwright.sync_api import sync_playwright

from .server import LocalSiteServer
from .comparator import ImageComparator, ComparisonResult
from .scenarios import SCENARIOS, TestScenario
from .reporter import generate_html_report


class ScreenshotTestRunner:
    """Executes visual screenshot test suite across all configured scenarios."""

    def __init__(
        self,
        root_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        baselines_dir: Optional[str] = None,
        update_baselines: bool = False,
        threshold_percent: float = 0.1,
        color_tolerance: int = 10,
        headless: bool = True,
        scenarios: Optional[List[TestScenario]] = None,
    ):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.root_dir = os.path.abspath(root_dir or base_dir)
        self.output_dir = os.path.abspath(
            output_dir or os.path.join(self.root_dir, "test_output", "screenshots")
        )
        self.baselines_dir = os.path.abspath(
            baselines_dir or os.path.join(os.path.dirname(__file__), "baselines")
        )
        self.update_baselines = update_baselines
        self.threshold_percent = threshold_percent
        self.color_tolerance = color_tolerance
        self.headless = headless
        self.scenarios = scenarios or SCENARIOS

        self.current_dir = os.path.join(self.output_dir, "current")
        self.diff_dir = os.path.join(self.output_dir, "diff")
        self.report_path = os.path.join(self.output_dir, "report.html")

        self.comparator = ImageComparator(
            mismatch_threshold_percent=self.threshold_percent,
            color_tolerance=self.color_tolerance,
        )

    def run(self, scenario_ids: Optional[List[str]] = None) -> Dict:
        """
        Executes screenshot tests.
        :param scenario_ids: Optional list of scenario IDs to filter by.
        :return: Dict containing summary metrics and list of ComparisonResult objects.
        """
        t0 = time.time()
        os.makedirs(self.current_dir, exist_ok=True)
        os.makedirs(self.diff_dir, exist_ok=True)
        os.makedirs(self.baselines_dir, exist_ok=True)

        # Filter scenarios if requested
        active_scenarios = self.scenarios
        if scenario_ids:
            active_scenarios = [s for s in self.scenarios if s.id in scenario_ids]
            if not active_scenarios:
                raise ValueError(f"No scenarios matched requested filter: {scenario_ids}")

        print("=" * 70)
        print(" 📸 Running Visual Screenshot Test Suite")
        print(f" 📂 Root: {self.root_dir}")
        print(f" 📁 Output: {self.output_dir}")
        print(f" 🎯 Scenarios: {len(active_scenarios)}")
        print(f" ⚙️ Update baselines: {self.update_baselines} | Threshold: {self.threshold_percent}%")
        print("=" * 70)

        results: List[ComparisonResult] = []

        # 1. Start ephemeral web server
        server = LocalSiteServer(root_dir=self.root_dir)
        server.start()
        print(f"🌐 Local test server active on {server.base_url}")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)

                for idx, scenario in enumerate(active_scenarios, 1):
                    print(f"[{idx}/{len(active_scenarios)}] Running '{scenario.title}' (#{scenario.id})...", end="", flush=True)
                    s_t0 = time.time()

                    # Set up isolated browser context for each scenario
                    context = browser.new_context(
                        viewport={"width": scenario.viewport[0], "height": scenario.viewport[1]},
                        is_mobile=scenario.is_mobile,
                        has_touch=scenario.has_touch,
                    )
                    page = context.new_page()

                    try:
                        page.goto(server.get_url("index.html"), wait_until="domcontentloaded")

                        if scenario.setup_action:
                            scenario.setup_action(page)

                        current_png = os.path.join(self.current_dir, f"{scenario.id}.png")
                        baseline_png = os.path.join(self.baselines_dir, f"{scenario.id}.png")
                        diff_png = os.path.join(self.diff_dir, f"{scenario.id}_diff.png")

                        if scenario.element_selector:
                            element = page.locator(scenario.element_selector)
                            element.screenshot(path=current_png)
                        elif scenario.full_page:
                            page.screenshot(path=current_png, full_page=True)
                        else:
                            page.screenshot(path=current_png)

                        # If user requested to update baselines or baseline doesn't exist yet, save copy
                        if self.update_baselines:
                            shutil.copyfile(current_png, baseline_png)

                        # Compare against baseline
                        comp_res = self.comparator.compare(
                            scenario_id=scenario.id,
                            current_path=current_png,
                            baseline_path=baseline_png if os.path.exists(baseline_png) else None,
                            diff_output_path=diff_png,
                        )

                        results.append(comp_res)
                        elapsed = time.time() - s_t0

                        if comp_res.status == "MATCH":
                            print(f" ✅ PASS ({elapsed:.2f}s, diff: {comp_res.diff_percent:.3f}%)")
                        elif comp_res.status == "NEW_BASELINE":
                            print(f" 🆕 NEW BASELINE ({elapsed:.2f}s)")
                        elif comp_res.status == "SIZE_MISMATCH":
                            print(f" ⚠️ SIZE MISMATCH ({elapsed:.2f}s) - {comp_res.message}")
                        else:
                            print(f" ❌ MISMATCH ({elapsed:.2f}s) - diff: {comp_res.diff_percent:.3f}% ({comp_res.diff_pixels:,} px)")

                    except Exception as ex:
                        print(f" ❌ ERROR: {ex}")
                        results.append(
                            ComparisonResult(
                                scenario_id=scenario.id,
                                status="ERROR",
                                is_match=False,
                                diff_percent=100.0,
                                diff_pixels=0,
                                total_pixels=0,
                                message=str(ex),
                            )
                        )
                    finally:
                        page.close()
                        context.close()

                browser.close()

        finally:
            server.stop()
            print("🛑 Local test server stopped.")

        total_duration = time.time() - t0

        # Generate HTML visual test report
        generate_html_report(
            results=results,
            scenarios=active_scenarios,
            report_output_path=self.report_path,
            output_dir=self.output_dir,
            baselines_dir=self.baselines_dir,
            duration_seconds=total_duration,
        )

        # Calculate metrics
        passed = sum(1 for r in results if r.status in ("MATCH", "NEW_BASELINE"))
        failed = sum(1 for r in results if r.status in ("MISMATCH", "SIZE_MISMATCH", "ERROR"))
        new_baselines = sum(1 for r in results if r.status == "NEW_BASELINE")

        print("=" * 70)
        print(f"🏁 Visual Screenshot Testing Complete in {total_duration:.2f}s")
        print(f"  • Total: {len(results)}")
        print(f"  • Passed: {passed}")
        print(f"  • New Baselines: {new_baselines}")
        print(f"  • Failed: {failed}")
        print(f"📊 Visual Report: file:///{self.report_path.replace(os.sep, '/')}")
        print("=" * 70)

        success = (failed == 0)
        return {
            "success": success,
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "new_baselines": new_baselines,
            "report_path": self.report_path,
            "results": results,
            "duration": total_duration,
        }
