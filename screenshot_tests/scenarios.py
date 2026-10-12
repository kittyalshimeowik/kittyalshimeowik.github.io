"""
Test Scenarios for Website Screenshot Verification.
Defines viewports, user interactions, selectors, and assertions across desktop, tablet,
and mobile devices.
"""

from dataclasses import dataclass, field
import time
from typing import Callable, Dict, Optional, Tuple
from playwright.sync_api import Page, Locator


@dataclass
class TestScenario:
    id: str
    title: str
    description: str
    viewport: Tuple[int, int]  # (width, height)
    is_mobile: bool = False
    has_touch: bool = False
    full_page: bool = False
    element_selector: Optional[str] = None
    setup_action: Optional[Callable[[Page], None]] = None


def _wait_for_site_ready(page: Page, timeout_ms: int = 10000):
    """Waits for listings data and web fonts to fully render."""
    page.wait_for_selector(".property-card:not(.skeleton-card)", timeout=timeout_ms)
    # Ensure Google Fonts (Inter) have loaded cleanly
    page.evaluate("() => document.fonts.ready")
    # Brief settle period for CSS transitions/skeletons to fade
    time.sleep(0.3)


# --- Setup Actions for Scenarios ---

def _setup_desktop_home(page: Page):
    _wait_for_site_ready(page)


def _setup_desktop_full_page(page: Page):
    _wait_for_site_ready(page)
    # Scroll slightly to trigger any lazy loading, then back to top
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(0.2)
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.2)


def _setup_armenian_language(page: Page):
    _wait_for_site_ready(page)
    # Click Armenian language button
    hy_btn = page.locator(".language-btn[data-language='hy']")
    hy_btn.click()
    page.wait_for_function("() => document.documentElement.lang === 'hy'")
    time.sleep(0.3)


def _setup_filters_collapsed(page: Page):
    _wait_for_site_ready(page)
    toggle_btn = page.locator("#toggle-filters")
    toggle_btn.click()
    page.wait_for_selector(".catalog-layout.filters-collapsed", timeout=5000)
    time.sleep(0.3)


def _setup_keyword_search(page: Page):
    _wait_for_site_ready(page)
    search_input = page.locator("#keyword-search")
    search_input.fill("Kentron")
    search_input.dispatch_event("input")
    page.wait_for_selector(".active-filter-chips .filter-chip", timeout=5000)
    time.sleep(0.3)


def _setup_property_type_rent(page: Page):
    _wait_for_site_ready(page)
    # Select For Rent
    rent_checkbox = page.locator("input[name='listing-type'][value='Rent']")
    rent_checkbox.check()
    # Select Apartment
    apt_checkbox = page.locator("input[name='property-type'][value='Apartment']")
    apt_checkbox.check()
    time.sleep(0.4)


def _setup_currency_amd(page: Page):
    _wait_for_site_ready(page)
    curr_select = page.locator("#currency-filter")
    curr_select.select_option("AMD")
    time.sleep(0.3)


def _setup_tablet_view(page: Page):
    _wait_for_site_ready(page)


def _setup_mobile_view(page: Page):
    _wait_for_site_ready(page)


def _setup_mobile_filters_collapsed(page: Page):
    _wait_for_site_ready(page)
    toggle_btn = page.locator("#toggle-filters")
    toggle_btn.click()
    page.wait_for_selector(".catalog-layout.filters-collapsed", timeout=5000)
    time.sleep(0.3)


def _setup_component_card(page: Page):
    _wait_for_site_ready(page)


# Master registry of test scenarios
SCENARIOS = [
    TestScenario(
        id="desktop_home",
        title="Desktop Home & Catalogs",
        description="Desktop default view showing branding header, full filter sidebar, and active listing grid.",
        viewport=(1440, 900),
        setup_action=_setup_desktop_home,
    ),
    TestScenario(
        id="desktop_full_page",
        title="Desktop Full Page Layout",
        description="Complete desktop page from top header down through filters, cards, and footer.",
        viewport=(1440, 900),
        full_page=True,
        setup_action=_setup_desktop_full_page,
    ),
    TestScenario(
        id="desktop_armenian_lang",
        title="Desktop Armenian Localization",
        description="Armenian language switch with AMD currency formatting, Armenian headers, and translated labels.",
        viewport=(1440, 900),
        setup_action=_setup_armenian_language,
    ),
    TestScenario(
        id="desktop_filters_collapsed",
        title="Desktop Filters Collapsed",
        description="Filter sidebar collapsed to maximize listings grid viewport width.",
        viewport=(1440, 900),
        setup_action=_setup_filters_collapsed,
    ),
    TestScenario(
        id="desktop_keyword_search",
        title="Desktop Keyword Search Filter",
        description="Search filter applied ('Kentron') with active filter chips and dynamic result counter.",
        viewport=(1440, 900),
        setup_action=_setup_keyword_search,
    ),
    TestScenario(
        id="desktop_filters_applied",
        title="Desktop Multi-Facet Filter (Rent Apartments)",
        description="Facet filters for 'Rent' and 'Apartment' active with badge synchronization.",
        viewport=(1440, 900),
        setup_action=_setup_property_type_rent,
    ),
    TestScenario(
        id="desktop_currency_amd",
        title="Desktop AMD Currency View",
        description="Explicit currency conversion to Armenian Dram (֏) across catalog pricing tags.",
        viewport=(1440, 900),
        setup_action=_setup_currency_amd,
    ),
    TestScenario(
        id="tablet_view",
        title="Tablet Responsive Layout",
        description="iPad/tablet viewport (768x1024) verifying responsive toolbar and grid scaling.",
        viewport=(768, 1024),
        setup_action=_setup_tablet_view,
    ),
    TestScenario(
        id="mobile_view",
        title="Mobile Portrait View",
        description="iPhone mobile viewport (375x812) verifying header stacking, single column cards, and touch targets.",
        viewport=(375, 812),
        is_mobile=True,
        has_touch=True,
        setup_action=_setup_mobile_view,
    ),
    TestScenario(
        id="mobile_filters_collapsed",
        title="Mobile Filters Collapsed View",
        description="Mobile view with filter accordion collapsed, giving full vertical clearance to listings.",
        viewport=(375, 812),
        is_mobile=True,
        has_touch=True,
        setup_action=_setup_mobile_filters_collapsed,
    ),
    TestScenario(
        id="component_card_detail",
        title="Single Property Card Component",
        description="High-resolution element capture of a listing card to verify typography, badges, and action buttons.",
        viewport=(1440, 900),
        element_selector=".property-card:first-of-type",
        setup_action=_setup_component_card,
    ),
    TestScenario(
        id="header_branding_logo",
        title="Header Branding & Logo Component",
        description="High-resolution element capture of header brand logo, title, and live indicator.",
        viewport=(1440, 900),
        element_selector="header",
        setup_action=_wait_for_site_ready,
    ),
    TestScenario(
        id="mobile_compact_360",
        title="Compact Mobile Screen (360x640)",
        description="Android/compact smartphone viewport (360x640) validating logo proportions, stacked header, and filter touch targets.",
        viewport=(360, 640),
        is_mobile=True,
        has_touch=True,
        setup_action=_setup_mobile_view,
    ),
]
