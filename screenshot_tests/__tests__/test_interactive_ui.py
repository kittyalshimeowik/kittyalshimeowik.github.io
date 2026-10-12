"""
Interactive UI & Browser Tests for Armenia Real Estate Hub.
Verifies scrolling functionality, back-to-top button, infinite scroll,
filter collapse button, reset button, language toggle, and card buttons.
"""

import time
import unittest
from playwright.sync_api import sync_playwright

from screenshot_tests.server import LocalSiteServer


class TestInteractiveUIFeatures(unittest.TestCase):
    """E2E browser tests for user interactions, scrolling, and buttons."""

    @classmethod
    def setUpClass(cls):
        cls.server = LocalSiteServer()
        cls.server.start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1440, "height": 900})
        self.page.goto(self.server.get_url("index.html"))
        # Wait for listings to load and render
        self.page.wait_for_selector(".property-card:not(.skeleton-card)", timeout=10000)

    def tearDown(self):
        self.page.close()

    def test_scrolling_and_back_to_top_button(self):
        """Verifies scroll detection, back-to-top visibility, and smooth return to top."""
        back_to_top = self.page.locator("#back-to-top")
        self.assertTrue(back_to_top.is_visible())
        
        # Initially at top (scrollY = 0), button should not have 'visible' class
        has_visible = self.page.evaluate("() => document.getElementById('back-to-top').classList.contains('visible')")
        self.assertFalse(has_visible, "Back-to-top should not have .visible at page top.")

        # Header should not have .is-scrolled at top
        header_scrolled = self.page.evaluate("() => document.querySelector('header').classList.contains('is-scrolled')")
        self.assertFalse(header_scrolled, "Header should not have .is-scrolled initially.")

        # Scroll down 800px
        self.page.evaluate("() => window.scrollTo(0, 800)")
        time.sleep(0.3)

        # Back-to-top should now have .visible
        has_visible_scrolled = self.page.evaluate("() => document.getElementById('back-to-top').classList.contains('visible')")
        self.assertTrue(has_visible_scrolled, "Back-to-top should have .visible class after scrolling down.")

        header_scrolled_now = self.page.evaluate("() => document.querySelector('header').classList.contains('is-scrolled')")
        self.assertTrue(header_scrolled_now, "Header should have .is-scrolled class after scrolling.")

        # Click the Back-to-Top button
        back_to_top.click()
        # Give smooth scroll time to reach top
        time.sleep(0.6)

        final_scroll_y = self.page.evaluate("() => window.scrollY")
        self.assertLessEqual(final_scroll_y, 50, "Clicking back-to-top should scroll viewport back to top.")

    def test_filter_collapse_button(self):
        """Tests the filter collapse toggle button (< and >) and layout class."""
        toggle_btn = self.page.locator("#toggle-filters")
        catalog_layout = self.page.locator(".catalog-layout")

        # Initially expanded
        self.assertNotIn("filters-collapsed", catalog_layout.get_attribute("class") or "")
        self.assertEqual(toggle_btn.get_attribute("aria-expanded"), "true")

        # Click to collapse
        toggle_btn.click()
        time.sleep(0.2)
        self.assertIn("filters-collapsed", catalog_layout.get_attribute("class") or "")
        self.assertEqual(toggle_btn.get_attribute("aria-expanded"), "false")

        # Click again to expand
        toggle_btn.click()
        time.sleep(0.2)
        self.assertNotIn("filters-collapsed", catalog_layout.get_attribute("class") or "")
        self.assertEqual(toggle_btn.get_attribute("aria-expanded"), "true")

    def test_language_toggle_buttons(self):
        """Tests switching between English and Armenian localization."""
        hy_btn = self.page.locator(".language-btn[data-language='hy']")
        en_btn = self.page.locator(".language-btn[data-language='en']")

        # Switch to Armenian
        hy_btn.click()
        time.sleep(0.3)

        doc_lang = self.page.evaluate("() => document.documentElement.lang")
        self.assertEqual(doc_lang, "hy")

        reset_label = self.page.locator("#reset-filters").inner_text()
        self.assertEqual(reset_label, "Մաքրել")

        # Switch back to English
        en_btn.click()
        time.sleep(0.3)

        doc_lang = self.page.evaluate("() => document.documentElement.lang")
        self.assertEqual(doc_lang, "en")
        reset_label = self.page.locator("#reset-filters").inner_text()
        self.assertEqual(reset_label, "Reset")

    def test_reset_filters_button(self):
        """Tests that Reset button restores all inputs, search bar, and selections."""
        search_input = self.page.locator("#keyword-search")
        search_input.fill("Kentron")
        search_input.dispatch_event("input")
        time.sleep(0.3)

        # Ensure filter chip appeared
        self.assertTrue(self.page.locator(".filter-chip").first.is_visible())

        # Click reset
        reset_btn = self.page.locator("#reset-filters")
        reset_btn.click()
        time.sleep(0.3)

        # Verify search input is cleared
        self.assertEqual(search_input.input_value(), "")
        # Filter chips should be hidden
        chips_visible = self.page.locator(".filter-chip").count()
        self.assertEqual(chips_visible, 0)

    def test_card_share_button_and_toast(self):
        """Tests the Share button on a property card and verifies toast appearance."""
        first_card = self.page.locator(".property-card:not(.skeleton-card)").first
        share_btn = first_card.locator(".share-btn")
        self.assertTrue(share_btn.is_visible())

        # Click share button
        share_btn.click()
        time.sleep(0.3)

        # Toast notification should appear in #toast-container
        toast = self.page.locator(".toast-message").first
        self.assertTrue(toast.is_visible())
        self.assertIn("copied", toast.inner_text().lower())

    def test_infinite_scroll_load_more(self):
        """Tests that scrolling down loads additional listing cards."""
        initial_card_count = self.page.locator(".property-card:not(.skeleton-card)").count()
        self.assertEqual(initial_card_count, 24)

        # Scroll to bottom to trigger load more
        self.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.8)

        # Load more button or intersection observer should load next batch
        new_card_count = self.page.locator(".property-card:not(.skeleton-card)").count()
        self.assertGreater(new_card_count, initial_card_count)


if __name__ == "__main__":
    unittest.main()
