"""
Screenshot Testing Suite for Armenia Real Estate Hub.
Provides visual regression, responsive viewport captures, and HTML reporting.
"""

from .server import LocalSiteServer
from .comparator import ImageComparator, ComparisonResult
from .scenarios import SCENARIOS, TestScenario
from .runner import ScreenshotTestRunner

__all__ = [
    "LocalSiteServer",
    "ImageComparator",
    "ComparisonResult",
    "SCENARIOS",
    "TestScenario",
    "ScreenshotTestRunner",
]
