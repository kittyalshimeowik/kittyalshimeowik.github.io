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

    def test_logo_and_tab_bar_favicons_rendered(self):
        """Verifies logo image in header and favicon links in head for browser tabs."""
        logo_img = self.page.locator(".brand-logo")
        self.assertTrue(logo_img.is_visible(), "Brand logo must be visible in header.")

        # Ensure image has loaded successfully
        is_loaded = self.page.evaluate("""() => {
            const img = document.querySelector('.brand-logo');
            return img && img.complete && img.naturalWidth > 0;
        }""")
        self.assertTrue(is_loaded, "Brand logo image must load without errors.")

        # Verify browser tab favicon tags
        favicon_svg = self.page.locator("link[rel='icon'][type='image/svg+xml']")
        self.assertTrue(favicon_svg.count() > 0, "SVG favicon link must exist in head for browser tab bar.")

        apple_icon = self.page.locator("link[rel='apple-touch-icon']")
        self.assertTrue(apple_icon.count() > 0, "Apple touch icon link must exist in head for mobile bookmarks.")

        manifest = self.page.locator("link[rel='manifest']")
        self.assertTrue(manifest.count() > 0, "Manifest link must exist in head for mobile web apps.")

    def test_mobile_viewport_and_header_logo(self):
        """Verifies mobile responsiveness (375x812), logo display, touch layout, and zero overflow."""
        mobile_page = self.browser.new_page(
            viewport={"width": 375, "height": 812},
            is_mobile=True,
            has_touch=True,
        )
        try:
            mobile_page.goto(self.server.get_url("index.html"))
            mobile_page.wait_for_selector(".property-card:not(.skeleton-card)", timeout=10000)

            # Logo must be visible and properly proportioned on mobile
            logo = mobile_page.locator(".brand-logo")
            self.assertTrue(logo.is_visible(), "Logo must be visible on mobile.")
            logo_box = logo.bounding_box()
            self.assertIsNotNone(logo_box)
            self.assertLessEqual(logo_box["width"], 42, "Logo should be compact on mobile.")
            self.assertGreaterEqual(logo_box["width"], 30, "Logo should remain prominent on mobile.")

            # No horizontal overflow on mobile
            has_horizontal_overflow = mobile_page.evaluate("""() => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            }""")
            self.assertFalse(has_horizontal_overflow, "Mobile page must not have horizontal scroll/overflow.")

            # Language toggle must work on mobile touch
            hy_btn = mobile_page.locator(".language-btn[data-language='hy']")
            hy_btn.tap()
            time.sleep(0.3)
            doc_lang = mobile_page.evaluate("() => document.documentElement.lang")
            self.assertEqual(doc_lang, "hy", "Language switch to Armenian should work on mobile.")

            # Filter collapse button must work on mobile
            toggle_btn = mobile_page.locator("#toggle-filters")
            toggle_btn.tap()
            time.sleep(0.3)
            is_collapsed = mobile_page.evaluate("() => document.querySelector('.catalog-layout').classList.contains('filters-collapsed')")
            self.assertTrue(is_collapsed, "Filters should collapse on mobile touch.")
        finally:
            mobile_page.close()

    def test_compact_mobile_viewport_360px(self):
        """Verifies ultra-compact mobile viewport (360x640) for no overflow and readable branding."""
        compact_page = self.browser.new_page(
            viewport={"width": 360, "height": 640},
            is_mobile=True,
            has_touch=True,
        )
        try:
            compact_page.goto(self.server.get_url("index.html"))
            compact_page.wait_for_selector(".property-card:not(.skeleton-card)", timeout=10000)

            # Check no overflow on 360px screen
            overflow = compact_page.evaluate("""() => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            }""")
            self.assertFalse(overflow, "360px compact mobile screen should not overflow.")

            # Logo and title should both be visible
            self.assertTrue(compact_page.locator(".brand-logo").is_visible())
            self.assertTrue(compact_page.locator("h1.logo").is_visible())
        finally:
            compact_page.close()

    def test_card_media_and_visuals_rendered(self):
        """Verifies that all property cards render visual media (photos or styled SVG graphics)."""
        cards = self.page.locator(".property-card")
        card_count = cards.count()
        self.assertGreater(card_count, 0, "At least one card should be rendered.")

        # Inspect first 5 cards
        for i in range(min(5, card_count)):
            card = cards.nth(i)
            media = card.locator(".card-media")
            self.assertTrue(media.is_visible(), f"Card {i} must render .card-media visual.")
            
            # Must contain either an img.card-media-img or .card-media-fallback
            has_img = media.locator(".card-media-img").count() > 0
            has_fallback = media.locator(".card-media-fallback").count() > 0
            self.assertTrue(has_img or has_fallback, f"Card {i} must render an image or a styled fallback graphic.")

    def test_google_maps_modal_interaction(self):
        """Verifies clicking on Map button opens the interactive Google Maps modal."""
        # Check map button exists
        map_btn = self.page.locator(".property-card .map-btn").first
        self.assertTrue(map_btn.is_visible(), "Property card should have a map button.")

        modal = self.page.locator("#map-modal")
        self.assertEqual(modal.get_attribute("aria-hidden"), "true", "Modal should initially be hidden.")

        # Click the map button
        map_btn.click()
        time.sleep(0.3)

        # Modal should now be active and visible
        self.assertEqual(modal.get_attribute("aria-hidden"), "false", "Modal should be active after clicking map button.")
        self.assertIn("active", modal.get_attribute("class") or "")

        # Check iframe src is set to Google Maps embed
        iframe_src = self.page.locator("#map-modal-iframe").get_attribute("src") or ""
        self.assertIn("maps.google.com/maps", iframe_src, "Iframe src should point to Google Maps embed.")
        self.assertIn("output=embed", iframe_src)

        # Check external link is populated
        ext_link = self.page.locator("#map-modal-external-link").get_attribute("href") or ""
        self.assertIn("google.com/maps/search", ext_link)

        # Click close button
        close_btn = self.page.locator("#map-modal-close")
        close_btn.click()
        time.sleep(0.2)

        # Modal should now be closed
        self.assertEqual(modal.get_attribute("aria-hidden"), "true", "Modal should close upon clicking close button.")
        self.assertNotIn("active", modal.get_attribute("class") or "")

    def test_card_content_minimal_and_non_redundant(self):
        """Verifies listing cards are minimal: no duplicate category/map words, working URLs, no Unknown tags."""
        cards = self.page.locator(".property-card:not(.skeleton-card)")
        card_count = cards.count()
        self.assertGreater(card_count, 0)

        for i in range(min(10, card_count)):
            card = cards.nth(i)

            # Check view original link is a working URL
            view_link = card.locator(".view-btn").get_attribute("href") or ""
            self.assertTrue(view_link.startswith("http"), f"Card {i} must have working http link: {view_link}")
            self.assertNotIn("123456", view_link, f"Card {i} must not have placeholder url")

            # Check no duplicate fallback badge on photo
            self.assertEqual(card.locator(".fallback-badge").count(), 0, f"Card {i} should not have redundant fallback-badge on photo")

            # Check map badge is not duplicated on location row
            self.assertEqual(card.locator(".location-container .map-badge").count(), 0, f"Card {i} should not duplicate map badge in location row")

            # Check no 'Unknown' tag displayed
            tags = card.locator(".source-tag, .category-tag").all_text_contents()
            for t in tags:
                self.assertNotIn("Unknown", t, f"Card {i} should not display uninformative 'Unknown' badge: {t}")
                self.assertNotIn("Անհայտ", t, f"Card {i} should not display uninformative 'Անհայտ' badge: {t}")


if __name__ == "__main__":
    unittest.main()

