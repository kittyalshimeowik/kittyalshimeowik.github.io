import unittest
import sys
import os

# Ensure current working directory / project root is in Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scrapers.utilities.env_utils import ensure_utf8_output, get_venv_python

ensure_utf8_output()

def run_all_tests():
    print("=" * 65)
    print(" 🧪 Running Comprehensive Unit Test Suites Across All Modules")
    print("=" * 65)

    loader = unittest.TestLoader()
    test_suites = []

    # Dynamically discover all '__tests__' directories under project root
    discovered_dirs = []
    for root, dirs, files in os.walk(os.path.join(project_root, "scrapers")):
        if os.path.basename(root) == "__tests__":
            discovered_dirs.append(root)

    discovered_dirs.sort()

    print(f"📦 Discovered {len(discovered_dirs)} test suites:")
    for test_dir in discovered_dirs:
        rel_path = os.path.relpath(test_dir, project_root)
        suite = loader.discover(
            start_dir=test_dir,
            pattern="test_*.py",
            top_level_dir=project_root
        )
        test_suites.append(suite)
        print(f"  • {rel_path} ({suite.countTestCases()} test cases)")

    # Combine into a single master test suite
    master_suite = unittest.TestSuite(test_suites)
    total_count = master_suite.countTestCases()
    print("-" * 65)
    print(f"🚀 Executing {total_count} total tests...")
    print("-" * 65)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(master_suite)

    print("=" * 65)
    if result.wasSuccessful():
        print(f"✅ SUCCESS: All {total_count} tests across all modules passed cleanly!")
        sys.exit(0)
    else:
        print(f"❌ FAILURE: {len(result.failures)} test(s) failed, {len(result.errors)} error(s).")
        sys.exit(1)


if __name__ == "__main__":
    proj_py = get_venv_python(__file__)
    if os.path.abspath(sys.executable).lower() != os.path.abspath(proj_py).lower():
        import subprocess
        result = subprocess.run([proj_py] + sys.argv, check=False)
        sys.exit(result.returncode)
    run_all_tests()