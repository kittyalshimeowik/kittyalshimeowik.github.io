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


def get_installed_chrome_major_version():
    """
    Detects the major version of Google Chrome installed on the host system.
    Supports Windows (Registry, PowerShell, Executable), Linux, and macOS.
    Returns an int (e.g., 154) or None if cannot be determined.
    """
    import re
    # 1. Windows Registry detection
    if CURRENT_OS == "windows":
        try:
            import winreg
            reg_paths = [
                r"SOFTWARE\Google\Chrome\BLBeacon",
                r"SOFTWARE\Wow6432Node\Google\Chrome\BLBeacon",
            ]
            for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for path in reg_paths:
                    try:
                        with winreg.OpenKey(root, path) as key:
                            val, _ = winreg.QueryValueEx(key, "version")
                            if val:
                                m = re.search(r"^(\d+)", str(val).strip())
                                if m:
                                    return int(m.group(1))
                    except (FileNotFoundError, OSError):
                        pass
        except Exception:
            pass

    # 2. Try undetected_chromedriver or standard executable discovery
    exe = None
    try:
        import undetected_chromedriver as uc
        exe = uc.find_chrome_executable()
    except Exception:
        pass

    if not exe and CURRENT_OS == "windows":
        default_paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for p in default_paths:
            if os.path.isfile(p):
                exe = p
                break

    if exe and os.path.isfile(exe):
        if CURRENT_OS == "windows":
            try:
                cmd = ["powershell", "-NoProfile", "-Command", f'(Get-Item "{exe}").VersionInfo.ProductVersion']
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                m = re.search(r"^(\d+)", out)
                if m:
                    return int(m.group(1))
            except Exception:
                pass
        else:
            try:
                out = subprocess.check_output([exe, "--version"], text=True, stderr=subprocess.DEVNULL).strip()
                m = re.search(r"(\d+)\.\d+\.\d+", out)
                if m:
                    return int(m.group(1))
            except Exception:
                pass

    # 3. Unix CLI fallback
    if CURRENT_OS in ("linux", "darwin"):
        commands = [
            ["google-chrome", "--version"],
            ["google-chrome-stable", "--version"],
            ["chromium", "--version"],
            ["chromium-browser", "--version"],
        ]
        if CURRENT_OS == "darwin":
            commands.insert(0, ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"])

        for cmd in commands:
            try:
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                m = re.search(r"(\d+)\.\d+\.\d+", out)
                if m:
                    return int(m.group(1))
            except Exception:
                pass

    return None


