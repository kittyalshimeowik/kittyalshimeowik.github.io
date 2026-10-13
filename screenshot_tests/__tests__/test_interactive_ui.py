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
        """Verifies clicking on Location link opens the interactive Google Maps modal and decluttered map button does not exist."""
        # Check decluttered .map-btn no longer exists
        self.assertEqual(
            self.page.locator(".property-card .map-btn").count(), 
            0, 
            "Redundant footer map button should be decluttered."
        )

        # Check location button exists and is clickable
        loc_map_btn = self.page.locator(".property-card .map-link-btn").first
        self.assertTrue(loc_map_btn.is_visible(), "Property card should have a location map link button.")

        modal = self.page.locator("#map-modal")
        self.assertEqual(modal.get_attribute("aria-hidden"), "true", "Modal should initially be hidden.")

        # Click the location map button
        loc_map_btn.click()
        time.sleep(0.3)

        # Modal should now be active and visible
        self.assertEqual(modal.get_attribute("aria-hidden"), "false", "Modal should be active after clicking location button.")
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

    def test_google_maps_exact_coordinates_resolution(self):
        """Verifies that posts with coordinates or exact street addresses resolve to exact Google Maps locations."""
        # 1. Post with explicit coordinates in text
        post_coords = {
            "property_category": "Land",
            "listing_type": "Sale",
            "full_text": "Վաճառվում է հողատարածք Գառնիում: Coordinates: 40.140146, 44.739168",
            "locations": ["Garni / Geghadir"]
        }
        info = self.page.evaluate("item => window.buildGoogleMapsInfo(item)", post_coords)
        self.assertEqual(info["query"], "40.140146,44.739168")
        self.assertIn("40.140146", info["embedUrl"])
        self.assertIn("44.739168", info["embedUrl"])
        self.assertIn("40.140146", info["externalUrl"])
        self.assertIn("40.1401", info["displaySubtitle"])

        # 2. Post with List.am Location: lat, lng header
        post_listam = {
            "property_category": "House",
            "listing_type": "Sale",
            "full_text": "Price: $75,000\nLocation: 40.521412, 44.71768, Կոտայքի մարզ",
            "locations": ["Kotayk"]
        }
        info_listam = self.page.evaluate("item => window.buildGoogleMapsInfo(item)", post_listam)
        self.assertEqual(info_listam["query"], "40.521412,44.717680")
        self.assertIn("40.521412", info_listam["embedUrl"])
        self.assertIn("44.717680", info_listam["embedUrl"])

        # 3. Post with exact street and building number
        post_street = {
            "property_category": "Apartment",
            "listing_type": "Rent",
            "full_text": "Վարդանանց 32 հասցեյում վարձակալության է տրվում 1 սենյականոց բնակարան",
            "locations": ["Kentron / Center"]
        }
        info_street = self.page.evaluate("item => window.buildGoogleMapsInfo(item)", post_street)
        self.assertIn("32 Vardanants St", info_street["query"])
        self.assertIn("32 Vardanants St", info_street["displaySubtitle"])

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

    def test_card_with_photos_height_and_aspect_ratio_consistency(self):
        """Verifies cards with photos maintain strict height consistency and layout alignment across aspect ratios."""
        # Inject diverse aspect ratios into cards (landscape, portrait, ultrawide, square)
        test_ratios = [
            ("16:9 Landscape", "800", "450", 5),
            ("9:16 Tall Portrait", "600", "1200", 3),
            ("1:2 Extreme Smartphone Portrait", "400", "800", 12),
            ("21:9 Ultrawide Panorama", "1200", "514", 2),
            ("1:1 Square", "600", "600", 1),
        ]
        
        metrics = self.page.evaluate("""(ratios) => {
            const cards = Array.from(document.querySelectorAll('.property-card:not(.skeleton-card)'));
            // Keep card 0 as baseline fallback
            const baselineCard = cards[0];
            const baselineH = Math.round(baselineCard.getBoundingClientRect().height);

            const results = [];
            ratios.forEach(([name, w, h, count], idx) => {
                const targetCard = cards[idx + 1];
                if (!targetCard) return;

                const media = targetCard.querySelector('.card-media');
                const badgeHtml = count > 1 ? `<span class="photo-count-badge">📷 ${count}</span>` : '';
                media.innerHTML = `
                    <img class="card-media-img" src="data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}'%3E%3Crect width='100%25' height='100%25' fill='%231e3a5f'/%3E%3C/svg%3E" alt="Test ${name}">
                    ${badgeHtml}
                `;

                const cardRect = targetCard.getBoundingClientRect();
                const mediaRect = media.getBoundingClientRect();
                const img = media.querySelector('.card-media-img');
                const imgRect = img ? img.getBoundingClientRect() : null;
                const imgStyle = img ? window.getComputedStyle(img) : null;

                results.push({
                    name,
                    cardH: Math.round(cardRect.height),
                    mediaH: Math.round(mediaRect.height),
                    mediaW: Math.round(mediaRect.width),
                    imgH: imgRect ? Math.round(imgRect.height) : 0,
                    imgW: imgRect ? Math.round(imgRect.width) : 0,
                    isAbsolute: imgStyle ? imgStyle.position === 'absolute' : false,
                    objectFit: imgStyle ? imgStyle.objectFit : null,
                    hasBadge: targetCard.querySelector('.photo-count-badge') !== null
                });
            });

            return { baselineH, results };
        }""", test_ratios)

        baseline_height = metrics["baselineH"]
        for res in metrics["results"]:
            # 1. Image must use position absolute and object-fit cover to prevent grid track ballooning
            self.assertTrue(res["isAbsolute"], f"{res['name']} image must have position: absolute")
            self.assertEqual(res["objectFit"], "cover", f"{res['name']} image must use object-fit: cover")

            # 2. Card height must stay consistent with the baseline row (within +/- 45px) and never balloon to 500px+
            self.assertLessEqual(
                abs(res["cardH"] - baseline_height), 
                45, 
                f"{res['name']} card height ({res['cardH']}px) should remain closely consistent with baseline ({baseline_height}px)"
            )
            self.assertLess(res["cardH"], 360, f"{res['name']} card height must not blow up beyond reasonable card bounds")

            # 3. Media column on desktop must be 260px wide and match the card's inner height
            self.assertEqual(res["mediaW"], 260, f"{res['name']} media column must be exactly 260px on desktop")
            self.assertEqual(res["mediaH"], res["imgH"], f"{res['name']} image should fully fill media container height")

    def test_card_with_photos_responsive_layout(self):
        """Verifies photo cards behave properly across tablet and mobile viewport breakpoints."""
        # Test mobile viewport (375x812)
        self.page.set_viewport_size({"width": 375, "height": 812})
        time.sleep(0.3)

        mobile_metrics = self.page.evaluate("""() => {
            const card = document.querySelector('.property-card:not(.skeleton-card)');
            const media = card.querySelector('.card-media');
            // Ensure card has photo
            media.innerHTML = `
                <img class="card-media-img" src="data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='600' height='1200'%3E%3Crect width='100%25' height='100%25' fill='%231e3a5f'/%3E%3C/svg%3E" alt="Mobile Photo">
                <span class="photo-count-badge">📷 6</span>
            `;

            const cardRect = card.getBoundingClientRect();
            const mediaRect = media.getBoundingClientRect();
            const bodyScrollWidth = document.documentElement.scrollWidth;

            return {
                cardW: Math.round(cardRect.width),
                mediaW: Math.round(mediaRect.width),
                mediaH: Math.round(mediaRect.height),
                bodyScrollW: bodyScrollWidth,
                aspectRatioCalc: mediaRect.width / (mediaRect.height || 1)
            };
        }""")

        # Zero horizontal page overflow
        self.assertLessEqual(mobile_metrics["bodyScrollW"], 375, "No horizontal overflow on mobile")
        # Media width should occupy full card width on mobile (within 1px border on each side)
        self.assertAlmostEqual(mobile_metrics["cardW"], mobile_metrics["mediaW"], delta=2)
        # Media aspect ratio should approximate 16:9 (1.77 +/- 0.1)
        self.assertAlmostEqual(mobile_metrics["aspectRatioCalc"], 16 / 9, delta=0.2)

        # Restore desktop viewport
        self.page.set_viewport_size({"width": 1440, "height": 900})
        time.sleep(0.3)

    def test_card_photo_error_fallback(self):
        """Verifies that when a listing photo fails to load, it gracefully falls back to SVG graphic without breaking layout."""
        fallback_metrics = self.page.evaluate("""() => {
            const card = document.querySelector('.property-card:not(.skeleton-card)');
            const media = card.querySelector('.card-media');
            // Ensure fallback exists in media container
            if (!media.querySelector('.card-media-fallback')) {
                const fb = document.createElement('div');
                fb.className = 'card-media-fallback cat-apartment';
                fb.innerHTML = '<div class="fallback-graphic"><svg class="fallback-svg"></svg></div>';
                media.prepend(fb);
            }
            // Simulate broken image triggering safe removal onerror handler
            const img = document.createElement('img');
            img.className = 'card-media-img';
            img.src = 'https://invalid-nonexistent-domain.xyz/photo.jpg';
            img.onerror = function() {
                this.remove();
                this.parentElement?.querySelector('.photo-count-badge')?.remove();
            };
            media.appendChild(img);
            // Fire onerror
            img.dispatchEvent(new Event('error'));

            const fallback = media.querySelector('.card-media-fallback');
            const cardRect = card.getBoundingClientRect();

            return {
                hasFallback: Boolean(fallback),
                cardH: Math.round(cardRect.height)
            };
        }""")

        self.assertTrue(fallback_metrics["hasFallback"], "OnError should keep .card-media-fallback visible")
        self.assertGreater(fallback_metrics["cardH"], 200, "Card height remains valid and non-zero")

    def test_card_with_photo_grid_alignment_and_no_stray_text(self):
        """Verifies that cards with photos have clean DOM, no leaked characters/strings, and side-by-side row alignment on desktop."""
        card_metrics = self.page.evaluate("""() => {
            // Find a card with a real or simulated photo
            const cards = Array.from(document.querySelectorAll('.property-card:not(.skeleton-card)'));
            const photoCard = cards.find(c => c.querySelector('.card-media-img')) || cards[0];
            if (!photoCard) return null;

            // Check direct child nodes of photoCard for any non-empty text nodes
            const strayTextNodes = Array.from(photoCard.childNodes)
                .filter(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0)
                .map(node => node.textContent.trim());

            const media = photoCard.querySelector('.card-media');
            const info = photoCard.querySelector('.property-info');

            const mediaRect = media ? media.getBoundingClientRect() : null;
            const infoRect = info ? info.getBoundingClientRect() : null;

            return {
                strayTexts: strayTextNodes,
                hasMedia: Boolean(media),
                hasInfo: Boolean(info),
                mediaTop: mediaRect ? Math.round(mediaRect.top) : 0,
                infoTop: infoRect ? Math.round(infoRect.top) : 0,
                mediaBottom: mediaRect ? Math.round(mediaRect.bottom) : 0,
                infoLeft: infoRect ? Math.round(infoRect.left) : 0,
                mediaRight: mediaRect ? Math.round(mediaRect.right) : 0,
            };
        }""")

        self.assertIsNotNone(card_metrics, "Property card should be present")
        self.assertEqual(len(card_metrics["strayTexts"]), 0, f"Found stray text nodes in card: {card_metrics['strayTexts']}")
        self.assertTrue(card_metrics["hasMedia"], "Card must have .card-media")
        self.assertTrue(card_metrics["hasInfo"], "Card must have .property-info")
        # On desktop (viewport 1440x900), .property-info must be side-by-side with .card-media, not pushed below
        self.assertAlmostEqual(card_metrics["mediaTop"], card_metrics["infoTop"], delta=3,
                               msg="property-info top must align with card-media top in desktop grid")
        self.assertGreaterEqual(card_metrics["infoLeft"], card_metrics["mediaRight"] - 1,
                                msg="property-info must be positioned to the right of card-media")

    def test_description_show_more_toggle(self):
        """Verifies that listings with long descriptions render a Show more toggle that cleanly expands/collapses."""
        expand_btns = self.page.locator(".description-expand-btn")
        self.assertGreater(expand_btns.count(), 0, "There should be listings with long descriptions offering Show more toggle.")

        first_expand = expand_btns.first
        parent_container = first_expand.locator("xpath=ancestor::div[contains(@class, 'description-container')]")
        snippet = parent_container.locator(".description-snippet")

        # Initially not expanded
        self.assertFalse("is-expanded" in (snippet.get_attribute("class") or ""))
        self.assertEqual(first_expand.get_attribute("aria-expanded"), "false")
        self.assertIn("Show more", first_expand.inner_text())

        # Click to expand
        first_expand.click()
        time.sleep(0.2)
        self.assertTrue("is-expanded" in (snippet.get_attribute("class") or ""))
        self.assertEqual(first_expand.get_attribute("aria-expanded"), "true")
        self.assertIn("Show less", first_expand.inner_text())

        # Click to collapse again
        first_expand.click()
        time.sleep(0.2)
        self.assertFalse("is-expanded" in (snippet.get_attribute("class") or ""))
        self.assertEqual(first_expand.get_attribute("aria-expanded"), "false")
        self.assertIn("Show more", first_expand.inner_text())

    def test_mobile_row_actions_layout(self):
        """Verifies that on mobile viewport, card footer actions are concise and horizontally arranged without excessive height."""
        self.page.set_viewport_size({"width": 375, "height": 812})
        time.sleep(0.3)

        footer_metrics = self.page.evaluate("""() => {
            const card = document.querySelector('.property-card:not(.skeleton-card)');
            const footer = card.querySelector('.card-footer');
            const viewBtn = footer.querySelector('.view-btn');
            const shareBtn = footer.querySelector('.share-btn');
            const mapBtn = footer.querySelector('.map-btn');

            const footerRect = footer.getBoundingClientRect();
            const footerStyle = window.getComputedStyle(footer);
            const shareStyle = window.getComputedStyle(shareBtn);

            return {
                footerH: Math.round(footerRect.height),
                flexDirection: footerStyle.flexDirection,
                hasMapBtn: Boolean(mapBtn),
                shareWidth: Math.round(shareBtn.getBoundingClientRect().width),
                shareHeight: Math.round(shareBtn.getBoundingClientRect().height),
                viewHeight: Math.round(viewBtn.getBoundingClientRect().height)
            };
        }""")

        self.assertFalse(footer_metrics["hasMapBtn"], "Map button should not exist on mobile footer.")
        self.assertEqual(footer_metrics["flexDirection"], "row", "Footer buttons should be arranged horizontally on mobile.")
        self.assertLessEqual(footer_metrics["footerH"], 52, "Mobile footer height must be concise, not 100px+ stacked.")
        self.assertLessEqual(footer_metrics["shareWidth"], 42, "Mobile share button should be a compact icon target.")


if __name__ == "__main__":
    unittest.main()


