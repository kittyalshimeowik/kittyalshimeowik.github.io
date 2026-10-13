# scrapers/utilities/logger.py
"""
Centralized logging framework and log analysis toolkit for Armenia Real Estate Hub.
Provides UTF-8 safe rotating file logging for all scrapers, processors, and pipelines,
as well as automated pattern detection and diagnostic analysis.
"""

import os
import sys
import re
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, Dict, Any, List

# Anchor Project Root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_INITIALIZED_LOGGERS = set()


def get_logger(
    name: str = "app",
    log_file: Optional[str] = None,
    console: bool = False,
    level: int = logging.INFO,
    logs_dir: Optional[str] = None
) -> logging.Logger:
    """
    Returns a configured, UTF-8 thread-safe logger with rotating file handlers.
    
    Handlers attached:
      1. Specific module log file: logs/{name}.log (10MB max, 5 backups)
      2. Central unified log file: logs/combined.log (15MB max, 5 backups)
      3. Console handler (if console=True)
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    logger_key = f"{name}_{logs_dir or LOGS_DIR}"
    if logger_key in _INITIALIZED_LOGGERS:
        return logger

    target_dir = logs_dir or LOGS_DIR
    os.makedirs(target_dir, exist_ok=True)

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DATE_FORMAT)

    # 1. Module-specific rotating file handler
    target_filename = log_file or f"{name}.log"
    target_filepath = os.path.join(target_dir, target_filename)
    try:
        file_handler = RotatingFileHandler(
            target_filepath,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"[WARNING] Could not attach file handler to {target_filepath}: {e}", file=sys.stderr)

    # 2. Central unified combined log
    combined_filepath = os.path.join(target_dir, "combined.log")
    try:
        combined_handler = RotatingFileHandler(
            combined_filepath,
            maxBytes=15 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        combined_handler.setLevel(level)
        combined_handler.setFormatter(formatter)
        logger.addHandler(combined_handler)
    except Exception:
        pass

    # 3. Optional console stream
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    _INITIALIZED_LOGGERS.add(logger_key)
    return logger


# Pre-defined diagnostic patterns
DIAGNOSTIC_PATTERNS = {
    "Rate Limiting": [
        re.compile(r"429|too many requests", re.I),
        re.compile(r"rate limit|action block|we limit how often|temporarily blocked", re.I),
        re.compile(r"Google Translate Rate Limit", re.I),
    ],
    "Bot Checkpoints & Challenges": [
        re.compile(r"checkpoint|login_challenge", re.I),
        re.compile(r"cloudflare|turnstile|challenge_running|cf-browser-verification", re.I),
        re.compile(r"session expired|login required", re.I),
    ],
    "Network & Navigation Timeouts": [
        re.compile(r"TimeoutError|timeout|timed out|Navigation failed|Target closed", re.I),
        re.compile(r"ConnectionRefused|ConnectionReset|HTTPError 50\d", re.I),
    ],
    "Database & Storage Locks": [
        re.compile(r"sqlite3\.OperationalError|database is locked|disk I/O error", re.I),
    ],
    "Data Parsing & Deserialization": [
        re.compile(r"JSONDecodeError|Expecting value|invalid \w+ format", re.I),
    ]
}


def analyze_logs(logs_dir: Optional[str] = None, max_lines: int = 5000) -> Dict[str, Any]:
    """
    Scans recent log files for errors, warnings, and recurring failure patterns.
    Returns a structured diagnostic dictionary and prints a formatted report.
    """
    target_dir = logs_dir or LOGS_DIR
    if not os.path.exists(target_dir):
        return {"status": "no_logs_found", "files_scanned": 0, "issues": {}}

    log_files = [f for f in os.listdir(target_dir) if f.endswith(".log")]
    summary: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "files_scanned": len(log_files),
        "total_errors": 0,
        "total_warnings": 0,
        "patterns_detected": {category: 0 for category in DIAGNOSTIC_PATTERNS},
        "file_breakdown": {},
        "recent_errors": []
    }

    for fname in log_files:
        fpath = os.path.join(target_dir, fname)
        file_errors = 0
        file_warnings = 0

        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-max_lines:]

            for line in lines:
                is_err = " [ERROR] " in line or " [CRITICAL] " in line
                is_warn = " [WARNING] " in line

                if is_err:
                    file_errors += 1
                    summary["total_errors"] += 1
                    if len(summary["recent_errors"]) < 15:
                        summary["recent_errors"].append({
                            "file": fname,
                            "line": line.strip()
                        })
                elif is_warn:
                    file_warnings += 1
                    summary["total_warnings"] += 1

                for category, regex_list in DIAGNOSTIC_PATTERNS.items():
                    if any(rx.search(line) for rx in regex_list):
                        summary["patterns_detected"][category] += 1

            summary["file_breakdown"][fname] = {
                "errors": file_errors,
                "warnings": file_warnings,
                "lines_scanned": len(lines)
            }
        except Exception as e:
            summary["file_breakdown"][fname] = {"error": str(e)}

    return summary


def print_log_diagnostic_report(summary: Optional[Dict[str, Any]] = None, logs_dir: Optional[str] = None) -> Dict[str, Any]:
    """Prints a human-readable diagnostic analysis of log files."""
    data = summary or analyze_logs(logs_dir=logs_dir)

    print("\n" + "=" * 75)
    print("  📋 SYSTEM LOGS DIAGNOSTIC & PATTERN ANALYSIS")
    print(f"  🕒 Analyzed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Directory: logs/")
    print("=" * 75)

    scanned = data.get("files_scanned", 0)
    if scanned == 0:
        print("  ℹ️ No log files found in logs/ directory. Run a script first.")
        print("=" * 75 + "\n")
        return data

    print(f"\n📂 Files Scanned: {scanned}")
    print(f" • Total Errors Logged:   {data.get('total_errors', 0)}")
    print(f" • Total Warnings Logged: {data.get('total_warnings', 0)}")

    print("\n🔍 Failure Pattern Frequencies:")
    print("-" * 75)
    patterns = data.get("patterns_detected", {})
    for category, count in patterns.items():
        icon = "⚠️" if count > 0 else "✅"
        print(f"  {icon} {category:<32}: {count:>4} occurrences")

    print("\n📊 Log Files Breakdown:")
    print("-" * 75)
    print(f" {'Log File':<28} | {'Errors':<8} | {'Warnings':<10} | {'Lines Scanned':<12}")
    print("-" * 75)
    for fname, fstats in data.get("file_breakdown", {}).items():
        errs = fstats.get("errors", 0)
        warns = fstats.get("warnings", 0)
        lines = fstats.get("lines_scanned", 0)
        print(f" {fname:<28} | {errs:<8} | {warns:<10} | {lines:<12}")

    recent = data.get("recent_errors", [])
    if recent:
        print("\n🚨 Recent Error Samples (Latest):")
        print("-" * 75)
        for idx, item in enumerate(recent[:5], 1):
            print(f" [{idx}] ({item['file']}) {item['line']}")

    print("=" * 75 + "\n")
    return data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Log Diagnostics & Analysis Utility")
    parser.add_argument("--analyze", action="store_true", help="Print log diagnostics report")
    args = parser.parse_args()
    print_log_diagnostic_report()
