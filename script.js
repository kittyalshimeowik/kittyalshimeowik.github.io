document.addEventListener("DOMContentLoaded", () => {
    console.log("Armenia Real Estate Hub initialized.");

    const translations = window.TRANSLATIONS || {};
    const locationTranslations = window.LOCATION_TRANSLATIONS || {};
    let currentLanguage = localStorage.getItem("preferredLanguage") || "en";

    const gridContainer = document.getElementById("listings-grid");
    const resultCount = document.getElementById("result-count");
    const locationOptions = document.getElementById("location-options");
    const resetFilters = document.getElementById("reset-filters");
    const toggleFilters = document.getElementById("toggle-filters");
    const catalogLayout = document.querySelector(".catalog-layout");
    const keywordSearch = document.getElementById("keyword-search");
    const paginationWrap = document.getElementById("pagination-wrap");
    const paginationInfo = document.getElementById("pagination-info");
    const loadMoreBtn = document.getElementById("load-more-btn");
    const activeFilterChips = document.getElementById("active-filter-chips");

    function updateHeaderHeight() {
        const header = document.querySelector("header");
        if (header) {
            const h = header.getBoundingClientRect().height;
            if (h > 0) {
                document.documentElement.style.setProperty("--header-height", `${Math.ceil(h)}px`);
            }
        }
    }

    updateHeaderHeight();
    window.addEventListener("resize", updateHeaderHeight);
    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(updateHeaderHeight);
    }

    function syncCurrencyWithLanguage() {
        const currSelect = document.getElementById("currency-filter");
        if (currSelect) {
            currSelect.value = (currentLanguage === "en") ? "USD" : "AMD";
        }
    }

    syncCurrencyWithLanguage();

    function text(key) {
        return (translations[currentLanguage] && translations[currentLanguage][key]) || key;
    }

    function translateLocation(location) {
        return currentLanguage === "hy" ? (locationTranslations[location] || location) : location;
    }

    function applyLanguage() {
        document.documentElement.lang = currentLanguage;
        syncCurrencyWithLanguage();
        document.querySelectorAll("[data-i18n]").forEach(element => {
            const key = element.dataset.i18n;
            element.textContent = text(key);
        });
        document.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
            const key = element.dataset.i18nPlaceholder;
            element.placeholder = text(key);
        });
        document.querySelectorAll(".language-btn").forEach(button => {
            button.classList.toggle("active", button.dataset.language === currentLanguage);
        });
        updateFilterToggle();
        updateHeaderHeight();

        locationOptions.querySelectorAll("label").forEach(label => {
            const input = label.querySelector("input");
            if (input && label.lastChild) {
                label.lastChild.textContent = ` ${translateLocation(input.value)}`;
            }
        });

        if (allListings.length > 0) {
            renderActiveFilterChips();
            updatePaginationInfo();
        }
    }

    function updateFilterToggle() {
        const isCollapsed = catalogLayout.classList.contains("filters-collapsed");
        const label = isCollapsed
            ? (currentLanguage === "hy" ? "Բացել զտիչները" : "Expand filters")
            : (currentLanguage === "hy" ? "Փակել զտիչները" : "Collapse filters");
        toggleFilters.setAttribute("aria-expanded", String(!isCollapsed));
        toggleFilters.setAttribute("aria-label", label);
        toggleFilters.title = label;
    }

    document.querySelectorAll(".language-btn").forEach(button => {
        button.addEventListener("click", () => {
            currentLanguage = button.dataset.language;
            localStorage.setItem("preferredLanguage", currentLanguage);
            // Automatically synchronize currency with selected language
            const currSelect = document.getElementById("currency-filter");
            if (currSelect) {
                currSelect.value = (currentLanguage === "en") ? "USD" : "AMD";
            }
            applyLanguage();
            if (allListings.length > 0) {
                applyFilters();
            }
        });
    });

    let allListings = [];
    let currentFilteredListings = [];
    let renderedCount = 0;
    const PAGE_SIZE = 24;

    function renderSkeletons() {
        gridContainer.innerHTML = Array.from({ length: 6 }).map(() => `
            <article class="property-card skeleton-card">
                <div class="skeleton-image"></div>
                <div class="property-info">
                    <div class="skeleton-line skeleton-header"></div>
                    <div class="skeleton-line skeleton-price"></div>
                    <div class="skeleton-line skeleton-details"></div>
                    <div class="skeleton-line skeleton-location"></div>
                    <div class="skeleton-line skeleton-snippet"></div>
                </div>
            </article>
        `).join("");
    }

    renderSkeletons();

    function isValidListingUrl(url) {
        if (!url || typeof url !== "string") return false;
        const trimmed = url.trim();
        if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) return false;
        if (trimmed.includes("123456") || trimmed.includes("example.com") || trimmed.includes("localhost")) {
            return false;
        }
        try {
            const parsed = new URL(trimmed);
            const host = parsed.hostname.toLowerCase();
            if (!host.includes("facebook.com") && !host.includes("fb.com") && !host.includes("list.am")) {
                return false;
            }
            if (host.includes("list.am") && !/\/item\/\d+/.test(parsed.pathname)) {
                return false;
            }
            if ((host.includes("facebook.com") || host.includes("fb.com")) && (!parsed.pathname || parsed.pathname.length < 5)) {
                return false;
            }
            return true;
        } catch {
            return false;
        }
    }

    fetch("scrapers/processors/master_listings_json/all_for_sale_rent.json")
        .then(response => {
            if (!response.ok) throw new Error("Failed to load listings data.");
            return response.json();
        })
        .then(data => {
            allListings = data.filter(item => 
                item.property_category && 
                item.property_category !== "General / Unclassified" && 
                item.property_category !== "Media-Only" &&
                isValidListingUrl(item.url)
            );

            populateLocations();
            applyLanguage();
            applyFilters();
            initInfiniteScroll();
        })
        .catch(error => {
            console.error("Error loading JSON:", error);
            gridContainer.innerHTML = `<p class="empty-state error-state">${text("failedLoad")}</p>`;
        });

    function populateLocations() {
        const locations = [...new Set(allListings.flatMap(item => item.locations || []))]
            .filter(Boolean)
            .sort((a, b) => a.localeCompare(b));

        const locationSearchInput = document.getElementById("location-search");
        if (locationSearchInput) {
            locationSearchInput.addEventListener("input", (e) => {
                const query = e.target.value.toLowerCase().trim();
                const labels = locationOptions.querySelectorAll("label");
                labels.forEach(label => {
                    const textContent = label.textContent.toLowerCase();
                    label.style.display = textContent.includes(query) ? "" : "none";
                });
            });
        }

        locationOptions.innerHTML = "";
        locations.forEach(location => {
            const label = document.createElement("label");
            label.innerHTML = `<input type="checkbox" name="location-filter" value="${escapeHtml(location)}"> ${escapeHtml(translateLocation(location))}`;
            locationOptions.appendChild(label);
        });
    }

    function getFirstPrice(item) {
        if (!item.prices || item.prices.length === 0) return null;
        const p = item.prices[0];
        const currencyChoice = document.getElementById("currency-filter").value;
        
        let val = null;
        if (currencyChoice === "USD") {
            val = p.amount_usd !== undefined ? Number(p.amount_usd) : Number(p.amount) / 364.18;
        } else {
            val = p.amount_amd !== undefined ? Number(p.amount_amd) : Number(p.amount);
        }
        return Number.isFinite(val) ? val : null;
    }

    function getFirstSize(item) {
        const size = item.sizes_sqm && item.sizes_sqm.length > 0 ? Number(item.sizes_sqm[0]) : NaN;
        return Number.isFinite(size) ? size : null;
    }

    function matchesSelection(value, selectedValues, mode) {
        if (selectedValues.length === 0) return true;
        return mode === "exclude" ? !selectedValues.includes(value) : selectedValues.includes(value);
    }

    const WB_L = '(?<![\\p{L}\\p{N}])';
    const WB_R = '(?![\\p{L}\\p{N}])';

    const PARK_NEGATIVE_REGEX = new RegExp(
        WB_L + '(?:զբոսայգ(?:ի|ու|ում|ով|իներ)|մանկական\\s+այգ(?:ի|ու|ում|ով|իներ)|սիրահարների\\s+այգ(?:ի|ու|ում|ով|իներ)|օղակաձև\\s+այգ(?:ի|ու|ում|ով|իներ)|պարկ|park)' + WB_R,
        'iu'
    );

    const AGRICULTURAL_REGEX = new RegExp(
        WB_L + '(?:գյուղատնտեսական|գյուղնշանակության|գյուղատնտեսության|գյուղատնտեսականի|գյուղ\\s*նշանակության)' + WB_R + '|' +
        WB_L + '(?:գյուղ\\.\\s*նշանակության)' + WB_R + '|' +
        WB_L + '(?:պտղատու|խաղողի|ծիրանի|խնձորի|ընկույզի|բալի)\\s+(?:այգ(?:ի|ու|ում|ով|իներ|իներով)?|ծառեր)' + WB_R + '|' +
        WB_L + '(?:այգետարածք|այգեգործական|վարելահող|խոտհարք|արոտավայր|ջերմոց|ջերմոցային|ֆերմա|անասնագոմ|դաշտավայր)' + WB_R + '|' +
        WB_L + '(?:сельхоз\\p{L}*|сельскохозяйственн\\p{L}*|пашն\\p{L}*|пашն\\p{L}*|ферм\\p{L}*|виноградник\\p{L}*|теплиц\\p{L}*)' + WB_R + '|' +
        WB_L + '(?:agricultural|farmland|farming|orchard|vineyard|greenhouse)' + WB_R,
        'iu'
    );

    const RESIDENTIAL_HOUSING_REGEX = new RegExp(
        WB_L + '(?:տնամերձ|բնակելի|բնակավայրերի|բնակավայրի|բնակելի\\s+կառուցապատման|տուն\\s+կառուցելու|տան\\s+համար|բնակարանաշինության|բնակելի\\s+տարածք)' + WB_R + '|' +
        WB_L + '(?:под\\s+застройку|под\\s+жилую\\s+застройку|ижс|жилое|приусадебный|для\\s+строительства\\s+дома)' + WB_R + '|' +
        WB_L + '(?:residential|homestead|housing|for\\s+living|residential\\s+building)' + WB_R,
        'iu'
    );

    function getListingZoning(item) {
        if (Array.isArray(item.zoning) && item.zoning.length > 0) {
            return item.zoning;
        }
        const textStr = item.full_text || "";
        const cleanText = textStr.replace(PARK_NEGATIVE_REGEX, " [PARK] ");
        const zonings = [];
        const isAgri = AGRICULTURAL_REGEX.test(cleanText);
        let isHousing = false;

        if (item.property_category === "Apartment" || item.property_category === "House") {
            isHousing = true;
        } else if (RESIDENTIAL_HOUSING_REGEX.test(cleanText)) {
            isHousing = true;
        }

        if (isHousing) zonings.push("Housing");
        if (isAgri) zonings.push("Agricultural");
        return zonings;
    }

    function applyFilters() {
        const selectedTypes = [...document.querySelectorAll("input[name='listing-type']:checked")].map(input => input.value);
        const selectedPropertyTypes = [...document.querySelectorAll("input[name='property-type']:checked")].map(input => input.value);
        const selectedZonings = [...document.querySelectorAll("input[name='property-zoning']:checked")].map(input => input.value);
        const listingTypeMode = document.getElementById("listing-type-mode").value;
        const propertyTypeMode = document.getElementById("property-type-mode").value;
        const propertyZoningMode = document.getElementById("property-zoning-mode") ? document.getElementById("property-zoning-mode").value : "include";
        const selectedLocations = [...document.querySelectorAll("input[name='location-filter']:checked")].map(input => input.value);
        const locationMode = document.getElementById("location-mode").value;
        const selectedSource = document.getElementById("source-filter").value;
        const minPrice = Number(document.getElementById("min-price").value) || 0;
        const maxPrice = Number(document.getElementById("max-price").value) || Infinity;
        const minimumRooms = Number(document.getElementById("rooms-filter").value) || 0;
        const query = keywordSearch ? keywordSearch.value.trim().toLowerCase() : "";

        currentFilteredListings = allListings.filter(item => {
            const itemPrice = getFirstPrice(item);
            const itemZonings = getListingZoning(item);
            const sourceMatches = selectedSource === "All" || item.source === selectedSource || (selectedSource === "Facebook" && (!item.source || item.source === "Facebook"));
            const typeMatches = matchesSelection(item.listing_type, selectedTypes, listingTypeMode);
            const propertyTypeMatches = matchesSelection(item.property_category, selectedPropertyTypes, propertyTypeMode);
            const zoningMatches = selectedZonings.length === 0 || (propertyZoningMode === "exclude"
                ? !selectedZonings.some(z => itemZonings.includes(z))
                : selectedZonings.some(z => itemZonings.includes(z)));
            const locationMatches = selectedLocations.length === 0 || (locationMode === "exclude"
                ? !(item.locations || []).some(location => selectedLocations.includes(location))
                : (item.locations || []).some(location => selectedLocations.includes(location)));
            const priceMatches = itemPrice === null ? minPrice === 0 : itemPrice >= minPrice && itemPrice <= maxPrice;
            const roomMatches = minimumRooms === 0 || (item.rooms || []).some(room => Number(room) >= minimumRooms);

            let queryMatches = true;
            if (query) {
                const searchCorpus = [
                    item.full_text || "",
                    (item.locations || []).join(" "),
                    item.property_category || "",
                    itemZonings.join(" "),
                    item.canonical_id || "",
                    item.author || ""
                ].join(" ").toLowerCase();
                queryMatches = query.split(/\s+/).every(token => searchCorpus.includes(token));
            }

            return sourceMatches && typeMatches && propertyTypeMatches && zoningMatches && locationMatches && priceMatches && roomMatches && queryMatches;
        });

        const sortFilter = document.getElementById("sort-filter");
        const sortOrder = sortFilter ? sortFilter.value : "newest";

        currentFilteredListings.sort((first, second) => {
            const p1 = getFirstPrice(first);
            const p2 = getFirstPrice(second);
            const s1 = getFirstSize(first);
            const s2 = getFirstSize(second);
            const t1 = first.creation_timestamp || 0;
            const t2 = second.creation_timestamp || 0;

            if (sortOrder === "price-asc") {
                // Primary: Price Low to High
                if (p1 !== null && p2 !== null && p1 !== p2) return p1 - p2;
                if (p1 === null && p2 !== null) return 1;
                if (p1 !== null && p2 === null) return -1;
                // Tie-breaker: Newest date
                if (t1 !== t2) return t2 - t1;
                // Secondary tie-breaker: Larger size
                return (s2 || 0) - (s1 || 0);
            }

            if (sortOrder === "price-desc") {
                // Primary: Price High to Low
                if (p1 !== null && p2 !== null && p1 !== p2) return p2 - p1;
                if (p1 === null && p2 !== null) return 1;
                if (p1 !== null && p2 === null) return -1;
                // Tie-breaker: Newest date
                if (t1 !== t2) return t2 - t1;
                // Secondary tie-breaker: Larger size
                return (s2 || 0) - (s1 || 0);
            }

            if (sortOrder === "size-desc") {
                // Primary: Size Large to Small
                if (s1 !== null && s2 !== null && s1 !== s2) return s2 - s1;
                if (s1 === null && s2 !== null) return 1;
                if (s1 !== null && s2 === null) return -1;
                // Tie-breaker: Lower price
                if (p1 !== null && p2 !== null && p1 !== p2) return p1 - p2;
                // Secondary tie-breaker: Newest date
                return t2 - t1;
            }

            if (sortOrder === "size-asc") {
                // Primary: Size Small to Large
                if (s1 !== null && s2 !== null && s1 !== s2) return s1 - s2;
                if (s1 === null && s2 !== null) return 1;
                if (s1 !== null && s2 === null) return -1;
                // Tie-breaker: Lower price
                if (p1 !== null && p2 !== null && p1 !== p2) return p1 - p2;
                // Secondary tie-breaker: Newest date
                return t2 - t1;
            }

            // Default: Newest date descending
            if (t1 !== t2) return t2 - t1;
            // Tie-breaker: Lower price
            if (p1 !== null && p2 !== null && p1 !== p2) return p1 - p2;
            return 0;
        });

        renderActiveFilterChips();
        resetAndRenderListings();
    }

    function resetAndRenderListings() {
        gridContainer.innerHTML = "";
        renderedCount = 0;
        resultCount.textContent = translations[currentLanguage].listingCount(currentFilteredListings.length);

        if (currentFilteredListings.length === 0) {
            gridContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon-wrap">
                        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="11" cy="11" r="8"></circle>
                            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                            <line x1="8" y1="11" x2="14" y2="11"></line>
                        </svg>
                    </div>
                    <p class="empty-title">${text("noMatches")}</p>
                    <p class="empty-desc">${text("noMatchesDesc")}</p>
                    <button class="reset-filter-btn" type="button" id="empty-reset-btn">${text("reset")}</button>
                </div>
            `;
            const emptyResetBtn = document.getElementById("empty-reset-btn");
            if (emptyResetBtn) {
                emptyResetBtn.addEventListener("click", () => resetFilters.click());
            }
            if (paginationWrap) paginationWrap.style.display = "none";
            return;
        }

        renderNextBatch();
    }

    function formatRelativeTime(ts) {
        if (!ts) return null;
        const now = Math.floor(Date.now() / 1000);
        const diff = now - Number(ts);
        if (diff < 3600) return currentLanguage === "hy" ? "Հենց նոր" : "Just now";
        if (diff < 86400) {
            const h = Math.floor(diff / 3600);
            return currentLanguage === "hy" ? `${h} ժ առաջ` : `${h}h ago`;
        }
        const d = Math.floor(diff / 86400);
        if (d < 30) {
            return currentLanguage === "hy" ? `${d} օր առաջ` : `${d}d ago`;
        }
        const dateObj = new Date(Number(ts) * 1000);
        return dateObj.toLocaleDateString(currentLanguage === "hy" ? "hy-AM" : "en-US", { month: "short", day: "numeric" });
    }

    const CATEGORY_SVGS = {
        Apartment: `
            <svg class="fallback-svg" viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="35" y="25" width="90" height="85" rx="3" fill="#1e293b" stroke="#3b82f6" stroke-width="2"/>
                <rect x="48" y="38" width="16" height="18" rx="2" fill="#60a5fa" opacity="0.85"/>
                <rect x="72" y="38" width="16" height="18" rx="2" fill="#93c5fd" opacity="0.6"/>
                <rect x="96" y="38" width="16" height="18" rx="2" fill="#60a5fa" opacity="0.85"/>
                <rect x="48" y="65" width="16" height="18" rx="2" fill="#93c5fd" opacity="0.6"/>
                <rect x="72" y="65" width="16" height="18" rx="2" fill="#60a5fa" opacity="0.85"/>
                <rect x="96" y="65" width="16" height="18" rx="2" fill="#93c5fd" opacity="0.6"/>
                <rect x="70" y="93" width="20" height="17" fill="#2563eb"/>
                <line x1="20" y1="110" x2="140" y2="110" stroke="#475569" stroke-width="2"/>
            </svg>
        `,
        House: `
            <svg class="fallback-svg" viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
                <polygon points="80,18 25,60 135,60" fill="#10b981" opacity="0.25" stroke="#10b981" stroke-width="2"/>
                <rect x="38" y="60" width="84" height="48" fill="#1e293b" stroke="#10b981" stroke-width="2"/>
                <rect x="52" y="70" width="16" height="16" rx="2" fill="#34d399" opacity="0.8"/>
                <rect x="92" y="70" width="16" height="16" rx="2" fill="#6ee7b7" opacity="0.7"/>
                <rect x="72" y="80" width="16" height="28" fill="#059669"/>
                <polygon points="105,32 105,22 115,22 115,40" fill="#047857"/>
                <line x1="20" y1="108" x2="140" y2="108" stroke="#475569" stroke-width="2"/>
            </svg>
        `,
        Land: `
            <svg class="fallback-svg" viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M20,95 Q50,60 90,85 T145,90 L145,110 L20,110 Z" fill="#15803d" opacity="0.3"/>
                <path d="M15,100 Q60,75 100,90 T145,100 L145,110 L15,110 Z" fill="#16a34a" opacity="0.4"/>
                <circle cx="80" cy="55" r="20" fill="#84cc16" opacity="0.2" stroke="#84cc16" stroke-width="2" stroke-dasharray="4 3"/>
                <path d="M80,45 L80,65 M70,55 L90,55" stroke="#a3e635" stroke-width="2"/>
                <path d="M42,75 L48,60 L54,75 Z" fill="#22c55e"/>
                <path d="M110,78 L116,64 L122,78 Z" fill="#22c55e"/>
                <line x1="15" y1="108" x2="145" y2="108" stroke="#334155" stroke-width="2"/>
            </svg>
        `,
        General: `
            <svg class="fallback-svg" viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="30" y="35" width="100" height="75" rx="3" fill="#1e293b" stroke="#818cf8" stroke-width="2"/>
                <rect x="42" y="48" width="22" height="20" rx="2" fill="#818cf8" opacity="0.7"/>
                <rect x="70" y="48" width="22" height="20" rx="2" fill="#a5b4fc" opacity="0.6"/>
                <rect x="98" y="48" width="20" height="20" rx="2" fill="#818cf8" opacity="0.7"/>
                <rect x="68" y="80" width="24" height="30" fill="#6366f1"/>
                <line x1="20" y1="110" x2="140" y2="110" stroke="#475569" stroke-width="2"/>
            </svg>
        `
    };

    const STREET_PATTERNS = [
        { name: "Mashtots Ave", regex: /(?:մաշտոց|маштоц|mashtots)/i },
        { name: "Komitas Ave", regex: /(?:կոմիտաս|комитас|komitas)/i },
        { name: "Baghramyan Ave", regex: /(?:բաղրամյան|баграмян|baghramyan|bagramyan)/i },
        { name: "Sayat-Nova Ave", regex: /(?:սայաթ[\s-]նովա|саят[\s-]нова|sayat[\s-]nova)/i },
        { name: "Northern Ave", regex: /(?:հյուսիսային|северный|northern\s*ave)/i },
        { name: "Tumanyan St", regex: /(?:թումանյան|туманян|tumanyan)/i },
        { name: "Amiryan St", regex: /(?:ամիրյան|амирян|amiryan)/i },
        { name: "Nalbandyan St", regex: /(?:նալբանդյան|налбандян|nalbandyan)/i },
        { name: "Abovyan St", regex: /(?:աբովյան\s*(?:փողոց|փող|փ\.|st|street)?|абовян|abovyan)/i },
        { name: "Tigran Mets Ave", regex: /(?:տիգրան\s+մեծ|тигран\s+мец|tigran\s+mets)/i },
        { name: "Khanjyan St", regex: /(?:խանջյան|ханджян|khanjyan)/i },
        { name: "Vardanants St", regex: /(?:վարդանանց|вардананц|vardanants)/i },
        { name: "Charents St", regex: /(?:չարենց|чаренц|charents)/i },
        { name: "Pushkin St", regex: /(?:պուշկին|пушкин|pushkin)/i },
        { name: "Arami St", regex: /(?:արամի\s*(?:փողոց|փ\.|st)?|арами|arami)/i },
        { name: "Isahakyan St", regex: /(?:իսահակյան|исаакян|isahakyan)/i },
        { name: "Moskovyan St", regex: /(?:մոսկովյան|московян|moskovyan)/i },
        { name: "Kasyan St", regex: /(?:կասյան|касьян|kasyan)/i },
        { name: "Vagharshyan St", regex: /(?:վաղարշյան|вагаршян|vagharshyan)/i },
        { name: "Gulbenkian St", regex: /(?:գյուլբենկյան|гюльбенкян|gulbenkian|gyulbenkyan)/i },
        { name: "Azatutyan Ave", regex: /(?:ազատության|азатутян|azatutyan)/i },
        { name: "Davit Anhaght St", regex: /(?:դավիթ\s+անհաղթ|давид\s+анахт|davit\s+anhaght)/i },
        { name: "Sebastia St", regex: /(?:սեբաստիա|себастия|sebastia)/i },
        { name: "Gai Ave", regex: /(?:գայի\s+(?:պող|պողոտա)|gai\s+ave)/i },
        { name: "Rubinyants St", regex: /(?:ռուբինյանց|рубинянц|rubinyants)/i }
    ];

    function buildGoogleMapsInfo(item) {
        const textStr = (item.full_text || "") + " " + (item.title || "");
        let detectedStreet = null;
        for (const sp of STREET_PATTERNS) {
            if (sp.regex.test(textStr)) {
                detectedStreet = sp.name;
                break;
            }
        }

        const locList = Array.isArray(item.locations) && item.locations.length > 0 
            ? [...new Set(item.locations.map(translateLocation).filter(Boolean))] 
            : [];
        const primaryLoc = locList[0] || "";
        const formattedLoc = locList.join(", ") || text("armenia");

        let mapQuery = "";
        let displaySubtitle = "";

        if (detectedStreet) {
            const locPart = primaryLoc ? `${primaryLoc}, ` : "";
            mapQuery = `${detectedStreet}, ${locPart}Yerevan, Armenia`;
            displaySubtitle = `${detectedStreet}, ${formattedLoc}`;
        } else if (locList.length > 0) {
            mapQuery = `${locList.join(", ")}, Armenia`;
            displaySubtitle = formattedLoc;
        } else {
            mapQuery = "Yerevan, Armenia";
            displaySubtitle = text("armenia");
        }

        const propCat = translations[currentLanguage].propertyTypes[item.property_category] || text("property");
        const listType = translations[currentLanguage].listingTypes[item.listing_type] || item.listing_type || "";
        const displayTitle = (listType && item.listing_type !== "Unknown") ? `${propCat} • ${listType}` : propCat;

        return {
            query: mapQuery,
            displayTitle: displayTitle,
            displaySubtitle: displaySubtitle,
            embedUrl: `https://maps.google.com/maps?q=${encodeURIComponent(mapQuery)}&output=embed`,
            externalUrl: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(mapQuery)}`
        };
    }

    const mapModal = document.getElementById("map-modal");
    const mapModalTitle = document.getElementById("map-modal-title");
    const mapModalSubtitle = document.getElementById("map-modal-subtitle");
    const mapModalIframe = document.getElementById("map-modal-iframe");
    const mapModalExternalLink = document.getElementById("map-modal-external-link");
    const mapModalClose = document.getElementById("map-modal-close");
    const mapLoadingIndicator = document.getElementById("map-loading-indicator");

    function openMapModal(item) {
        if (!mapModal) return;
        const mapsInfo = buildGoogleMapsInfo(item);
        if (mapModalTitle) mapModalTitle.textContent = mapsInfo.displayTitle;
        if (mapModalSubtitle) mapModalSubtitle.textContent = mapsInfo.displaySubtitle;
        if (mapModalExternalLink) mapModalExternalLink.href = mapsInfo.externalUrl;

        if (mapLoadingIndicator) mapLoadingIndicator.style.display = "flex";
        if (mapModalIframe) {
            mapModalIframe.onload = () => {
                if (mapLoadingIndicator) mapLoadingIndicator.style.display = "none";
            };
            mapModalIframe.src = mapsInfo.embedUrl;
        }

        mapModal.classList.add("active");
        mapModal.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        if (mapModalClose) mapModalClose.focus();
    }

    function closeMapModal() {
        if (!mapModal) return;
        mapModal.classList.remove("active");
        mapModal.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
        if (mapModalIframe) {
            mapModalIframe.src = "about:blank";
        }
    }

    if (mapModalClose) {
        mapModalClose.addEventListener("click", closeMapModal);
    }
    if (mapModal) {
        mapModal.addEventListener("click", (e) => {
            if (e.target === mapModal) {
                closeMapModal();
            }
        });
    }
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && mapModal && mapModal.classList.contains("active")) {
            closeMapModal();
        }
    });

    function renderNextBatch() {
        const nextBatch = currentFilteredListings.slice(renderedCount, renderedCount + PAGE_SIZE);
        if (nextBatch.length === 0) return;

        const currencyChoice = document.getElementById("currency-filter").value;
        const fragment = document.createDocumentFragment();

        nextBatch.forEach(item => {
            const card = document.createElement("article");
            card.className = "property-card";

            let primaryPriceText = text("priceUponRequest");
            let pricePerSqmText = "";

            if (item.prices && item.prices.length > 0) {
                const p = item.prices[0];
                const amtAmd = p.amount_amd !== undefined ? p.amount_amd : p.original_amount;
                const amtUsd = p.amount_usd !== undefined ? p.amount_usd : Math.round(amtAmd / 364.18);

                if (amtAmd > 0 || amtUsd > 0) {
                    if (currencyChoice === "USD") {
                        primaryPriceText = `$${Number(amtUsd).toLocaleString()} USD`;
                    } else {
                        primaryPriceText = `${Number(amtAmd).toLocaleString()} ֏`;
                    }

                    if (item.sizes_sqm && Number(item.sizes_sqm[0]) > 0) {
                        const sqm = Number(item.sizes_sqm[0]);
                        if (currentLanguage === "en" || currencyChoice === "USD") {
                            const sqmRate = Math.round(amtUsd / sqm);
                            if (sqmRate > 0) pricePerSqmText = `$${sqmRate.toLocaleString()}/m²`;
                        } else {
                            const sqmRate = Math.round(amtAmd / sqm);
                            if (sqmRate > 0) pricePerSqmText = `${sqmRate.toLocaleString()} ֏${text("perSqm")}`;
                        }
                    }
                }
            }

            const listingType = item.listing_type || "Unknown";
            const listingTypeLabel = translations[currentLanguage].listingTypes[listingType] || listingType;
            let typeTagClass = "sale";
            if (listingType === "Rent") typeTagClass = "rent";

            const sourceName = item.source || "Facebook";
            let sourceClass = "fb";
            let sourceDisplay = "FB";
            if (sourceName === "List.am") {
                sourceClass = "listam";
                sourceDisplay = "List.am";
            }

            const relativeTimeStr = formatRelativeTime(item.creation_timestamp);

            const locList = Array.isArray(item.locations) && item.locations.length > 0
                ? [...new Set(item.locations.map(translateLocation).filter(Boolean))]
                : [];
            const locationText = locList.length > 0
                ? locList.join(", ")
                : text("armenia");

            // Specs badges
            let specsBadges = [];
            const zonings = getListingZoning(item);
            if (zonings.includes("Agricultural")) {
                specsBadges.push(`<span class="spec-pill zoning-agri">🌱 ${text("zoningAgriculturalBadge")}</span>`);
            }
            if (zonings.includes("Housing") && item.property_category === "Land") {
                specsBadges.push(`<span class="spec-pill zoning-housing">🏡 ${text("zoningHousingBadge")}</span>`);
            }
            if (item.rooms && item.rooms.length > 0 && Number(item.rooms[0]) > 0) {
                specsBadges.push(`<span class="spec-pill">🛏️ ${translations[currentLanguage].roomLabel(Number(item.rooms[0]))}</span>`);
            }
            if (item.sizes_sqm && item.sizes_sqm.length > 0 && Number(item.sizes_sqm[0]) > 0) {
                specsBadges.push(`<span class="spec-pill">📐 ${item.sizes_sqm[0]} m²</span>`);
            }
            if (pricePerSqmText) {
                specsBadges.push(`<span class="spec-pill sqm-rate">${pricePerSqmText}</span>`);
            }

            const propCategory = translations[currentLanguage].propertyTypes[item.property_category] || text("property");

            const phoneBtnHtml = (item.phone_numbers && item.phone_numbers.length > 0 && item.phone_numbers[0].trim().length >= 6)
                ? `<a href="tel:${escapeHtml(item.phone_numbers[0].replace(/\s+/g, ''))}" class="phone-link" title="${escapeHtml(item.phone_numbers.join(', '))}">📞 ${escapeHtml(item.phone_numbers[0])}</a>`
                : '';

            // Media / Visuals
            const categoryKey = item.property_category || "General";
            const fallbackClass = categoryKey === "Apartment" ? "cat-apartment" : (categoryKey === "House" ? "cat-house" : (categoryKey === "Land" ? "cat-land" : "cat-general"));
            const categorySvg = CATEGORY_SVGS[categoryKey] || CATEGORY_SVGS.General;
            const firstImage = (item.images && item.images.length > 0) ? item.images[0] : null;
            const imageCount = (item.images && item.images.length) || 0;

            let mediaHtml = "";
            if (firstImage) {
                const photoBadge = imageCount > 1 
                    ? `<span class="photo-count-badge">📷 ${imageCount}</span>` 
                    : '';
                mediaHtml = `
                    <div class="card-media">
                        <img class="card-media-img" src="${escapeHtml(firstImage)}" alt="${escapeHtml(propCategory)}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling?.remove();this.parentElement.innerHTML='<div class=\\'card-media-fallback ${fallbackClass}\\'><div class=\\'fallback-graphic\\'>${categorySvg.replace(/'/g, "\\'")}</div></div>';">
                        ${photoBadge}
                    </div>
                `;
            } else {
                mediaHtml = `
                    <div class="card-media">
                        <div class="card-media-fallback ${fallbackClass}">
                            <div class="fallback-graphic">
                                ${categorySvg}
                            </div>
                        </div>
                    </div>
                `;
            }

            const typeBadgeHtml = (listingType === "Sale" || listingType === "Rent")
                ? `<span class="source-tag ${typeTagClass}">${escapeHtml(listingTypeLabel)}</span>`
                : '';

            card.innerHTML = `
                ${mediaHtml}
                <div class="property-info">
                    <div class="listing-topline">
                        <div class="tags-container">
                            <span class="source-tag ${sourceClass}">${escapeHtml(sourceDisplay)}</span>
                            ${typeBadgeHtml}
                            <span class="category-tag">${escapeHtml(propCategory)}</span>
                        </div>
                        ${relativeTimeStr ? `<span class="time-tag">📅 ${escapeHtml(relativeTimeStr)}</span>` : ''}
                    </div>

                    <div class="price-row">
                        <h3 class="price">${escapeHtml(primaryPriceText)}</h3>
                    </div>

                    ${specsBadges.length > 0 ? `<div class="specs-row">${specsBadges.join("")}</div>` : ''}

                    <div class="location-container">
                        <button type="button" class="map-link-btn" title="${text("viewOnMap")}">
                            <span class="pin-icon">📍</span>
                            <span class="loc-text">${escapeHtml(locationText)}</span>
                        </button>
                    </div>
                    
                    ${(item.full_text && item.full_text.trim().length > 0) ? `<p class="description-snippet">${escapeHtml(item.full_text.trim())}</p>` : ''}

                    <div class="card-footer">
                        ${phoneBtnHtml}
                        <button type="button" class="map-btn" title="${text("viewOnMap")}">
                            <span class="map-btn-icon">🗺️</span>
                            <span>${text("map")}</span>
                        </button>
                        <button type="button" class="share-btn" title="${text("shareLink")}">
                            <svg class="share-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="18" cy="5" r="3"></circle>
                                <circle cx="6" cy="12" r="3"></circle>
                                <circle cx="18" cy="19" r="3"></circle>
                                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                            </svg>
                            <span>${text("shareLink")}</span>
                        </button>
                        <a href="${escapeHtml(item.url)}" class="view-btn" target="_blank" rel="noopener noreferrer">
                            ${text("viewOriginal")} <span class="arrow">↗</span>
                        </a>
                    </div>
                </div>
            `;

            // Map button interactions
            const mapBtns = card.querySelectorAll(".map-link-btn, .map-btn");
            mapBtns.forEach(btn => {
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    openMapModal(item);
                });
            });

            // Share button copy interaction
            const shareBtn = card.querySelector(".share-btn");
            if (shareBtn) {
                shareBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const urlToShare = item.url || window.location.href;
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(urlToShare)
                            .then(() => showToast(text("linkCopied")))
                            .catch(() => showToast(text("linkCopied")));
                    } else {
                        showToast(text("linkCopied"));
                    }
                });
            }

            // Entire row is clickable to go to the post
            card.setAttribute("role", "link");
            card.setAttribute("tabindex", "0");
            card.addEventListener("click", (e) => {
                if (e.target.closest(".phone-link, .share-btn, .view-btn, .map-btn, .map-link-btn")) return;
                const selection = window.getSelection();
                if (selection && selection.toString().trim().length > 0) return;
                if (item.url) {
                    window.open(item.url, "_blank", "noopener,noreferrer");
                }
            });

            card.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    if (e.target.closest(".phone-link, .share-btn, .view-btn, .map-btn, .map-link-btn")) return;
                    e.preventDefault();
                    if (item.url) {
                        window.open(item.url, "_blank", "noopener,noreferrer");
                    }
                }
            });

            fragment.appendChild(card);
        });

        gridContainer.appendChild(fragment);
        renderedCount += nextBatch.length;
        updatePaginationInfo();
    }

    function updatePaginationInfo() {
        if (!paginationWrap) return;
        if (currentFilteredListings.length === 0) {
            paginationWrap.style.display = "none";
            return;
        }

        paginationWrap.style.display = "flex";
        paginationInfo.textContent = translations[currentLanguage].showingCount(renderedCount, currentFilteredListings.length);

        if (renderedCount >= currentFilteredListings.length) {
            loadMoreBtn.style.display = "none";
        } else {
            loadMoreBtn.style.display = "inline-block";
            loadMoreBtn.textContent = text("loadMore");
        }
    }

    if (loadMoreBtn) {
        loadMoreBtn.addEventListener("click", () => renderNextBatch());
    }

    function initInfiniteScroll() {
        if (!("IntersectionObserver" in window) || !loadMoreBtn) return;
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && renderedCount < currentFilteredListings.length) {
                renderNextBatch();
            }
        }, { rootMargin: "300px" });

        observer.observe(loadMoreBtn);
    }

    function showToast(message) {
        const toastContainer = document.getElementById("toast-container");
        if (!toastContainer) return;
        const toast = document.createElement("div");
        toast.className = "toast-message";
        toast.innerHTML = `<span class="toast-icon">✓</span> <span>${escapeHtml(message)}</span>`;
        toastContainer.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add("visible"));
        setTimeout(() => {
            toast.classList.remove("visible");
            toast.classList.add("fade-out");
            setTimeout(() => toast.remove(), 300);
        }, 2200);
    }

    function initScrollFeatures() {
        const backToTopBtn = document.getElementById("back-to-top");
        const header = document.querySelector("header");

        window.addEventListener("scroll", () => {
            const currentScrollY = window.scrollY || document.documentElement.scrollTop;
            if (backToTopBtn) {
                backToTopBtn.classList.toggle("visible", currentScrollY > 300);
            }
            if (header) {
                header.classList.toggle("is-scrolled", currentScrollY > 15);
            }
        }, { passive: true });

        if (backToTopBtn) {
            backToTopBtn.addEventListener("click", () => {
                window.scrollTo({ top: 0, behavior: "smooth" });
            });
        }
    }
    initScrollFeatures();

    function renderActiveFilterChips() {
        if (!activeFilterChips) return;
        activeFilterChips.innerHTML = "";

        const chips = [];
        const query = keywordSearch ? keywordSearch.value.trim() : "";
        if (query) {
            chips.push({ label: `"${query}"`, clear: () => { keywordSearch.value = ""; applyFilters(); } });
        }

        const sourceVal = document.getElementById("source-filter").value;
        if (sourceVal !== "All") {
            chips.push({ label: `Source: ${sourceVal}`, clear: () => { document.getElementById("source-filter").value = "All"; applyFilters(); } });
        }

        document.querySelectorAll("input[name='listing-type']:checked").forEach(cb => {
            chips.push({ label: `${cb.value}`, clear: () => { cb.checked = false; applyFilters(); } });
        });

        document.querySelectorAll("input[name='property-type']:checked").forEach(cb => {
            chips.push({ label: `${cb.value}`, clear: () => { cb.checked = false; applyFilters(); } });
        });

        document.querySelectorAll("input[name='property-zoning']:checked").forEach(cb => {
            const labelText = cb.value === "Housing" ? text("zoningHousing") : text("zoningAgricultural");
            chips.push({ label: `${labelText}`, clear: () => { cb.checked = false; applyFilters(); } });
        });

        document.querySelectorAll("input[name='location-filter']:checked").forEach(cb => {
            chips.push({ label: `📍 ${translateLocation(cb.value)}`, clear: () => { cb.checked = false; applyFilters(); } });
        });

        const minP = document.getElementById("min-price").value;
        const maxP = document.getElementById("max-price").value;
        if (minP || maxP) {
            const curr = document.getElementById("currency-filter").value;
            chips.push({
                label: `${minP || 0} - ${maxP || '∞'} ${curr}`,
                clear: () => {
                    document.getElementById("min-price").value = "";
                    document.getElementById("max-price").value = "";
                    applyFilters();
                }
            });
        }

        const roomsVal = document.getElementById("rooms-filter").value;
        if (roomsVal !== "All") {
            chips.push({ label: `${roomsVal}+ Rooms`, clear: () => { document.getElementById("rooms-filter").value = "All"; applyFilters(); } });
        }

        const sortFilter = document.getElementById("sort-filter");
        if (sortFilter && sortFilter.value !== "newest") {
            const sortTextMap = {
                "price-asc": text("priceLowHigh"),
                "price-desc": text("priceHighLow"),
                "size-desc": text("sizeLargeSmall"),
                "size-asc": text("sizeSmallLarge")
            };
            const sortLabel = sortTextMap[sortFilter.value] || sortFilter.value;
            chips.push({
                label: `${text("sort")}: ${sortLabel}`,
                clear: () => {
                    sortFilter.value = "newest";
                    applyFilters();
                }
            });
        }

        if (chips.length === 0) {
            activeFilterChips.style.display = "none";
            return;
        }

        activeFilterChips.style.display = "flex";
        chips.forEach(c => {
            const chip = document.createElement("span");
            chip.className = "filter-chip";
            chip.innerHTML = `${escapeHtml(c.label)} <button class="chip-remove" type="button" aria-label="Remove filter">&times;</button>`;
            chip.querySelector(".chip-remove").addEventListener("click", c.clear);
            activeFilterChips.appendChild(chip);
        });
    }

    let debounceTimer = null;
    function handleFilterChange(event) {
        if (event.target.matches("#keyword-search, #min-price, #max-price")) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => applyFilters(), 180);
            return;
        }

        if (event.target.matches(".filter-control, .sort-select, .mode-control, input[name='listing-type'], input[name='property-type'], input[name='property-zoning'], input[name='location-filter'], #sort-filter")) {
            applyFilters();
        }
    }

    document.addEventListener("input", handleFilterChange);
    document.addEventListener("change", handleFilterChange);

    toggleFilters.addEventListener("click", () => {
        catalogLayout.classList.toggle("filters-collapsed");
        updateFilterToggle();
    });

    resetFilters.addEventListener("click", () => {
        if (keywordSearch) keywordSearch.value = "";
        document.querySelectorAll("input[type='checkbox']").forEach(input => input.checked = false);
        document.getElementById("source-filter").value = "All";
        syncCurrencyWithLanguage();
        document.getElementById("listing-type-mode").value = "include";
        document.getElementById("property-type-mode").value = "include";
        const zoningMode = document.getElementById("property-zoning-mode");
        if (zoningMode) zoningMode.value = "include";
        document.querySelectorAll("input[name='property-zoning']").forEach(input => input.checked = false);
        document.querySelectorAll("input[name='location-filter']").forEach(input => input.checked = false);
        document.getElementById("location-mode").value = "include";
        document.getElementById("min-price").value = "";
        document.getElementById("max-price").value = "";
        document.getElementById("rooms-filter").value = "All";
        
        const sortFilter = document.getElementById("sort-filter");
        if (sortFilter) sortFilter.value = "newest";
        
        const locationSearchInput = document.getElementById("location-search");
        if (locationSearchInput) {
            locationSearchInput.value = "";
            locationOptions.querySelectorAll("label").forEach(label => label.style.display = "");
        }

        applyFilters();
    });

    function escapeHtml(str) {
        if (typeof str !== "string") return String(str || "");
        return str.replace(/[&<>'"]/g, 
            tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
        );
    }
});
