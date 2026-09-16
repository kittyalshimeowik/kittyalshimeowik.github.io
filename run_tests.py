import unittest
import sys
import os

def run_all_tests():
    # Ensure current working directory / project root is in Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    print("=" * 60)
    print(" 🧪 Running Unit Test Suites Across All Modules")
    print("=" * 60)

    loader = unittest.TestLoader()
    
    # Explicitly discover test suites inside both __tests__ subdirectories
    fb_tests = loader.discover(
        start_dir=os.path.join(project_root, "scrapers", "facebook", "__tests__"),
        pattern="test_*.py",
        top_level_dir=project_root
    )
    
    processor_tests = loader.discover(
        start_dir=os.path.join(project_root, "scrapers", "processors", "__tests__"),
        pattern="test_*.py",
        top_level_dir=project_root
    )

    # Combine into a single test suite
    master_suite = unittest.TestSuite([fb_tests, processor_tests])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(master_suite)

    print("=" * 60)
    if result.wasSuccessful():
        print(" SUCCESS: All test suites passed cleanly!")
        sys.exit(0)
    else:
        print(f"❌ FAILURE: {len(result.failures)} test(s) failed, {len(result.errors)} error(s).")
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()