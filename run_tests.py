import unittest
import sys
import os

# Fix for Windows console encoding issues with emojis
if os.name == 'nt':
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

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

def get_project_python():
    """Returns the project virtual environment Python if available, else current sys.executable."""
    proj_root = os.path.dirname(os.path.abspath(__file__))
    venv_py_win = os.path.join(proj_root, ".venv", "Scripts", "python.exe")
    venv_py_nix = os.path.join(proj_root, ".venv", "bin", "python")
    if os.name == 'nt' and os.path.isfile(venv_py_win):
        return venv_py_win
    elif os.path.isfile(venv_py_nix):
        return venv_py_nix
    return sys.executable

if __name__ == "__main__":
    proj_py = get_project_python()
    if os.path.abspath(sys.executable).lower() != os.path.abspath(proj_py).lower():
        import subprocess
        result = subprocess.run([proj_py] + sys.argv, check=False)
        sys.exit(result.returncode)
    run_all_tests()