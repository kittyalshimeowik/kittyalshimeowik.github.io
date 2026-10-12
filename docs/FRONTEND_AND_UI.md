# 🎨 Frontend & Web Application Architecture

This document covers the client-side architecture, DOM structure, styling system, interactive features, filtering engine, and internationalization of the **Armenia Real Estate Hub**.

---

## 🏛️ Design Philosophy

The frontend is built using **Vanilla HTML5, modern CSS3, and native JavaScript (ES2022)** without heavyweight frameworks. This provides:
- **Instantaneous Load Speed**: Zero build-step overhead and sub-second First Contentful Paint (FCP).
- **Sub-5ms Filtering**: All filtering and multi-attribute sorting occur directly in browser memory over the dataset.
- **Progressive Enhancement**: Clean skeleton loading, responsive layouts, and full accessibility support.

---

## 💎 Design System & Styling (`style.css`)

### Color Palette & Tokens
The application utilizes a curated, accessible color palette defined in `:root`:

```css
:root {
    --bg-app: #f8fafc;           /* Crisp light background */
    --surface: #ffffff;          /* Card & panel surfaces */
    --brand-primary: #0f172a;    /* Deep slate header */
    --brand-accent: #2563eb;     /* Modern interactive blue */
    --price-green: #059669;      /* Emerald pricing typography */
    
    /* Armenian National Palette Accents */
    --am-red: #d90012;
    --am-blue: #0033a0;
    --am-orange: #f2a800;

    /* Platform & Status Badges */
    --badge-fb: #1877f2;         /* Facebook gradient */
    --badge-listam: #f97316;     /* List.am gradient */
    --badge-sale: #059669;       /* For Sale emerald */
    --badge-rent: #7c3aed;       /* For Rent purple */
}
```

### Key UI Features

1. **Sticky Glassmorphic Header**:
   - Features a subtle gradient with a live status indicator (`.live-pill` with pulsing green dot).
   - On scrolling down (`window.scrollY > 15px`), adds `.is-scrolled` to activate `backdrop-filter: blur(16px)` and deep shadow.

2. **Collapsible Filter Drawer**:
   - Desktop: 2-column layout (`300px` filter sidebar + flexible listings grid).
   - Collapse button (`#toggle-filters`) rotates an SVG chevron and compresses sidebar to `56px`, maximizing listings view space.
   - Mobile: Responsive accordion drawer that collapses vertically.

3. **Elevated Property Cards**:
   - Subtle borders with multi-layer shadows (`--card-shadow`).
   - Smooth hover elevation: `transform: translateY(-3px)` with ambient blue border highlight.
   - Clean specifications pills (area in m², price per m², room count, agricultural/residential badges).

4. **Floating Back-to-Top Button (`#back-to-top`)**:
   - Appears smoothly with fade and scale animation when the user scrolls past `300px`.
   - Smoothly scrolls viewport back to the top (`window.scrollTo({ top: 0, behavior: 'smooth' })`).

5. **Visual Property Media & Photo Badges (`.card-media`)**:
   - Displays real listing photography scraped from List.am and Facebook attachments with `loading="lazy"`.
   - Photo counter badge (`📷 N`) showing total available images.
   - Vector fallback: When photos are absent or fail to load, renders custom category-themed SVG graphics (Apartment, House, Land, Commercial) against subtle radial gradients.

6. **Interactive Google Maps Modal (`#map-modal`)**:
   - Zero-key embedded Google Maps preview triggered from either the card location link (`.map-link-btn`) or the footer map action (`.map-btn`).
   - Automatically detects recognized Yerevan streets (Mashtots, Komitas, Baghramyan, Northern Ave, Tumanyan, Amiryan, Nalbandyan, etc.) or falls back to community/district level.
   - Includes live loading spinner, interactive preview iframe, and direct "Open in Google Maps ↗" external navigation button.
   - Full keyboard accessibility (Escape to dismiss, focus trap handling, outside backdrop click).

7. **Toast Notification System (`#toast-container`)**:
   - Centered floating toast notifications for copy-to-clipboard interactions.
   - Smooth enter/exit transition with green checkmark indicator.

---

## ⚡ Client-Side State & Logic (`script.js`)

### 1. In-Memory Data Store & Pipeline
On load, `fetch()` retrieves `all_for_sale_rent.json`:
1. Excludes unclassified or media-only records.
2. Extracts and sorts unique locations for the location filter list.
3. Renders the initial page of listings (`PAGE_SIZE = 24`).
4. Observes the `#load-more-btn` via `IntersectionObserver` to trigger smooth infinite scrolling.

### 2. Multi-Criteria Filtering Engine (`applyFilters`)
The filtering engine handles multiple criteria with sub-millisecond execution:

```javascript
currentFilteredListings = allListings.filter(item => {
    // 1. Source (Facebook, List.am, All)
    // 2. Listing Type (Sale, Rent) with Include / Exclude mode
    // 3. Property Category (Apartment, House, Land) with Include / Exclude mode
    // 4. Zoning (Residential, Agricultural) with contextual keyword analysis
    // 5. Locations (Multi-select with live search)
    // 6. Price Range (Dynamic USD or AMD conversion)
    // 7. Minimum Bedroom / Room count
    // 8. Keyword search across text, locations, ID, and author
});
```

### 3. Multi-Tier Sorting Algorithms
Users can sort listings by:
- **Newest** (creation timestamp descending, tie-breaker: lower price)
- **Price: Low to High** (tie-breaker: newest date, then larger size)
- **Price: High to Low** (tie-breaker: newest date, then larger size)
- **Size: Large to Small** (tie-breaker: lower price, then newest date)
- **Size: Small to Large** (tie-breaker: lower price, then newest date)

### 4. Card Action Handlers
- **Map Buttons (`.map-link-btn`, `.map-btn`)**: Opens the Google Maps modal with resolved street/location query and live embed preview.
- **Phone Button**: Direct `tel:` link with formatted Armenian number.
- **Share Button**: Copies permalink to system clipboard and triggers toast notification.
- **View Original Button**: Opens origin source on Facebook or List.am in a new tab.
- **Card Click**: Clicking anywhere on the card opens the listing while respecting text selection.

---

## 🌍 Internationalization (`translations.js`)

The application supports real-time language toggling between **English (`en`)** and **Armenian (`hy`)**:
- All UI strings, placeholders, badges, and counters update dynamically without page reloads.
- Geographic locations are bilingual (e.g., *Kentron / Center* ↔ *Կենտրոն*, *Arabkir* ↔ *Արաբկիր*).
- Currency defaults align with language selection (USD for English, AMD for Armenian).
- User's selected language is persisted in `localStorage`.
