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

    function text(key) {
        return (translations[currentLanguage] && translations[currentLanguage][key]) || key;
    }

    function translateLocation(location) {
        return currentLanguage === "hy" ? (locationTranslations[location] || location) : location;
    }

    function applyLanguage() {
        document.documentElement.lang = currentLanguage;
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

    fetch("scrapers/processors/master_listings_json/all_for_sale_rent.json")
        .then(response => {
            if (!response.ok) throw new Error("Failed to load listings data.");
            return response.json();
        })
        .then(data => {
            allListings = data.filter(item => 
                item.property_category && 
                item.property_category !== "General / Unclassified" && 
                item.property_category !== "Media-Only"
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
                    <p class="empty-title">${text("noMatches")}</p>
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

                if (currencyChoice === "USD") {
                    primaryPriceText = `$${Number(amtUsd).toLocaleString()} USD`;
                } else {
                    primaryPriceText = `${Number(amtAmd).toLocaleString()} ֏`;
                }

                if (item.sizes_sqm && item.sizes_sqm[0] > 0) {
                    const sqm = Number(item.sizes_sqm[0]);
                    if (sqm > 0) {
                        if (currentLanguage === "en" || currencyChoice === "USD") {
                            const sqmRate = Math.round(amtUsd / sqm);
                            pricePerSqmText = `$${sqmRate.toLocaleString()}/m²`;
                        } else {
                            const sqmRate = Math.round(amtAmd / sqm);
                            pricePerSqmText = `${sqmRate.toLocaleString()} ֏${text("perSqm")}`;
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

            const locationText = item.locations && item.locations.length > 0
                ? item.locations.map(translateLocation).join(", ")
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
            if (item.rooms && item.rooms.length > 0) {
                specsBadges.push(`<span class="spec-pill">🛏️ ${translations[currentLanguage].roomLabel(Number(item.rooms[0]))}</span>`);
            }
            if (item.sizes_sqm && item.sizes_sqm.length > 0) {
                specsBadges.push(`<span class="spec-pill">📐 ${item.sizes_sqm[0]} m²</span>`);
            }
            if (pricePerSqmText) {
                specsBadges.push(`<span class="spec-pill sqm-rate">${pricePerSqmText}</span>`);
            }

            const propCategory = translations[currentLanguage].propertyTypes[item.property_category] || text("property");

            const phoneBtnHtml = item.phone_numbers && item.phone_numbers.length > 0
                ? `<a href="tel:${escapeHtml(item.phone_numbers[0].replace(/\s+/g, ''))}" class="phone-link" title="${escapeHtml(item.phone_numbers.join(', '))}">📞 ${escapeHtml(item.phone_numbers[0])}</a>`
                : '';

            card.innerHTML = `
                <div class="property-info">
                    <div class="listing-topline">
                        <div class="tags-container">
                            <span class="source-tag ${sourceClass}">${escapeHtml(sourceDisplay)}</span>
                            <span class="source-tag ${typeTagClass}">${escapeHtml(listingTypeLabel)}</span>
                            <span class="category-tag">${escapeHtml(propCategory)}</span>
                        </div>
                        ${relativeTimeStr ? `<span class="time-tag">📅 ${escapeHtml(relativeTimeStr)}</span>` : ''}
                    </div>

                    <div class="price-row">
                        <h3 class="price">${escapeHtml(primaryPriceText)}</h3>
                    </div>

                    ${specsBadges.length > 0 ? `<div class="specs-row">${specsBadges.join("")}</div>` : ''}

                    <p class="location"><span class="pin-icon">📍</span> ${escapeHtml(locationText)}</p>
                    
                    ${item.full_text ? `<p class="description-snippet">${escapeHtml(item.full_text)}</p>` : ''}

                    <div class="card-footer">
                        ${phoneBtnHtml}
                        <a href="${escapeHtml(item.url)}" class="view-btn" target="_blank" rel="noopener noreferrer">
                            ${text("viewOriginal")} <span class="arrow">↗</span>
                        </a>
                    </div>
                </div>
            `;

            // Entire row is clickable to go to the post
            card.setAttribute("role", "link");
            card.setAttribute("tabindex", "0");
            card.addEventListener("click", (e) => {
                if (e.target.closest(".phone-link")) return;
                const selection = window.getSelection();
                if (selection && selection.toString().trim().length > 0) return;
                if (e.target.closest(".view-btn")) return;
                if (item.url) {
                    window.open(item.url, "_blank", "noopener,noreferrer");
                }
            });

            card.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    if (e.target.closest(".phone-link")) return;
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
        document.getElementById("currency-filter").value = "AMD";
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
