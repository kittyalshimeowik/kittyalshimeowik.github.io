# scrapers/utilities/env_utils.py
import os
import sys
import io
import platform
import subprocess

CURRENT_OS = platform.system().lower()


def ensure_utf8_output():
    """Configures stdout and stderr to use UTF-8 encoding across Windows, Linux, and macOS."""
    if CURRENT_OS == "windows":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    else:
        if hasattr(sys.stdout, "buffer") and (not getattr(sys.stdout, "encoding", None) or sys.stdout.encoding.lower() != 'utf-8'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if hasattr(sys.stderr, "buffer") and (not getattr(sys.stderr, "encoding", None) or sys.stderr.encoding.lower() != 'utf-8'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def get_project_root(start_file=None):
    """Finds project root by looking for .venv or run_tests.py upwards."""
    cur = os.path.abspath(os.path.dirname(start_file)) if start_file else os.path.abspath(os.getcwd())
    while True:
        if os.path.isdir(os.path.join(cur, ".venv")) or os.path.isfile(os.path.join(cur, "run_tests.py")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(os.path.dirname(start_file)) if start_file else os.path.abspath(os.getcwd())


def get_venv_python(start_file=None):
    """Returns the project virtual environment Python path if available, else current sys.executable."""
    proj_root = get_project_root(start_file)
    venv_py_win = os.path.join(proj_root, ".venv", "Scripts", "python.exe")
    venv_py_nix = os.path.join(proj_root, ".venv", "bin", "python")
    if os.name == "nt" and os.path.isfile(venv_py_win):
        return venv_py_win
    elif os.path.isfile(venv_py_nix):
        return venv_py_nix
    return sys.executable


def ensure_virtualenv(script_file):
    """
    Checks if a local virtual environment (.venv) exists. If running outside of it,
    re-launches the current script inside the virtual environment Python interpreter.
    """
    # Guard against re-executing during test runners
    if any("unittest" in arg or "pytest" in arg for arg in sys.argv):
        return
    target_py = get_venv_python(script_file)
    if target_py and os.path.abspath(sys.executable).lower() != os.path.abspath(target_py).lower():
        res = subprocess.run([target_py] + sys.argv, check=False)
        sys.exit(res.returncode)

