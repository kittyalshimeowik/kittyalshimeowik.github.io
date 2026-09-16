document.addEventListener("DOMContentLoaded", () => {
    console.log("Armenia Real Estate Hub initialized.");

    const translations = {
        en: {
            siteTitle: "🇦🇲 Armenia Real Estate Hub", siteSubtitle: "Scraped & Aggregated Listings from FB & Local Sites", hide: "Hide", show: "Show",
            searchListings: "Search listings", filterResults: "Filter results", reset: "Reset", source: "Source",
            allSources: "All sources", currencyLabel: "Currency", listingType: "Listing type", propertyType: "Property type", include: "Include", exclude: "Exclude",
            forSale: "For sale", forRent: "For rent", apartment: "Apartment", house: "House", land: "Land", location: "Location",
            minPrice: "Min price", maxPrice: "Max price", any: "Any", priceHint: "Price matching uses the first parsed price.",
            rooms: "Rooms", anyNumber: "Any number", onePlusRooms: "1+ rooms", twoPlusRooms: "2+ rooms", threePlusRooms: "3+ rooms",
            fourPlusRooms: "4+ rooms", fivePlusRooms: "5+ rooms", propertyFeed: "Armenia property feed", availableListings: "Available listings",
            sort: "Sort", newest: "Newest", priceLowHigh: "Price: low to high", priceHighLow: "Price: high to low",
            sizeSmallLarge: "Size: small to large", sizeLargeSmall: "Size: large to small", footer: "© 2026 Armenia Real Estate Scraper Hub",
            priceUponRequest: "Price upon request", property: "Property", armenia: "Armenia", viewOriginal: "View original post",
            noMatches: "No listings match these filters.", failedLoad: "Failed to load property data. Make sure you are running a local server to allow JSON fetching.",
            listingCount: count => `${count} listing${count === 1 ? "" : "s"}`, roomLabel: count => `${count} room${count === 1 ? "" : "s"}`,
            listingTypes: { Sale: "Sale", Rent: "Rent", Unknown: "Unknown" }, propertyTypes: { Apartment: "Apartment", House: "House", Land: "Land" }
        },
        hy: {
            siteTitle: "🇦🇲 Հայաստանի անշարժ գույքի հարթակ", siteSubtitle: "Հայտարարություններ Facebook-ից և տեղական կայքերից", hide: "Թաքցնել", show: "Ցուցադրել",
            searchListings: "Որոնել հայտարարություններ", filterResults: "Զտել արդյունքները", reset: "Մաքրել", source: "Աղբյուր",
            allSources: "Բոլոր աղբյուրները", currencyLabel: "Արժույթ", listingType: "Գործարքի տեսակ", propertyType: "Գույքի տեսակ", include: "Ներառել", exclude: "Բացառել",
            forSale: "Վաճառք", forRent: "Վարձակալություն", apartment: "Բնակարան", house: "Տուն", land: "Հողատարածք", location: "Տեղադրություն",
            minPrice: "Նվազագույն գին", maxPrice: "Առավելագույն գին", any: "Ցանկացած", priceHint: "Գնի զտումը օգտագործում է առաջին հասանելի գինը։",
            rooms: "Սենյակներ", anyNumber: "Ցանկացած քանակ", onePlusRooms: "1 և ավելի սենյակ", twoPlusRooms: "2 և ավելի սենյակ", threePlusRooms: "3 և ավելի սենյակ",
            fourPlusRooms: "4 և ավելի սենյակ", fivePlusRooms: "5 և ավելի սենյակ", propertyFeed: "Հայաստանի անշարժ գույքի հոսք", availableListings: "Հասանելի հայտարարություններ",
            sort: "Դասավորել", newest: "Նորագույնները", priceLowHigh: "Գին՝ ցածրից բարձր", priceHighLow: "Գին՝ բարձրից ցածր",
            sizeSmallLarge: "Մակերես՝ փոքրից մեծ", sizeLargeSmall: "Մակերես՝ մեծից փոքր", footer: "© 2026 Հայաստանի անշարժ գույքի հարթակ",
            priceUponRequest: "Գինը՝ հարցումով", property: "Գույք", armenia: "Հայաստան", viewOriginal: "Դիտել սկզբնական հայտարարությունը",
            noMatches: "Այս զտիչներին համապատասխան հայտարարություններ չկան։", failedLoad: "Չհաջողվեց բեռնել գույքի տվյալները։ Գործարկեք կայքը տեղական սերվերով։",
            listingCount: count => `${count} հայտարարություն`, roomLabel: count => `${count} սենյակ`,
            listingTypes: { Sale: "Վաճառք", Rent: "Վարձակալություն", Unknown: "Անհայտ" }, propertyTypes: { Apartment: "Բնակարան", House: "Տուն", Land: "Հողատարածք" }
        }
    };

    let currentLanguage = localStorage.getItem("preferredLanguage") || "en";

    const locationTranslations = {
        // Yerevan Districts
        "Ajapnyak": "Աջափնյակ",
        "Arabkir": "Արաբկիր",
        "Avan": "Ավան",
        "Davtashen": "Դավթաշեն",
        "Erebuni": "Էրեբունի",
        "Kentron / Center": "Կենտրոն",
        "Malatia-Sebastia": "Մալաթիա-Սեբաստիա",
        "Nor Nork / Massiv": "Նոր Նորք / Մասիվ",
        "Nork-Marash": "Նորք-Մարաշ",
        "Nubarashen": "Նուբարաշեն",
        "Shengavit": "Շենգավիթ",
        "Zeytun / Kanaker": "Զեյթուն / Քանաքեռ",

        // Kotayk Province & Suburbs
        "Abovyan": "Աբովյան",
        "Arinj": "Առինջ",
        "Jrvezh / Dzoraghbyur": "Ջրվեժ / Ձորաղբյուր",
        "Kasagh / Proshyan": "Քասախ / Պրոշյան",
        "Nor Gyugh": "Նոր Գյուղ",
        "Tsaghkadzor": "Ծաղկաձոր",
        "Yeghvard": "Եղվարդ",

        // Ararat & Armavir Suburbs
        "Artashat": "Արտաշատ",
        "Ashtarak": "Աշտարակ",
        "Vagharshapat / Etchmiadzin": "Էջմիածին / Վաղարշապատ",
        "Vedi": "Վեդի",

        // Extended Regions & Cities
        "Dilijan": "Դիլիջան",
        "Goris": "Գորիս",
        "Gyumri": "Գյումրի",
        "Sevan": "Սևան",
        "Vanadzor": "Վանաձոր"
    };

    const gridContainer = document.getElementById("listings-grid");
    const resultCount = document.getElementById("result-count");
    const locationOptions = document.getElementById("location-options");
    const resetFilters = document.getElementById("reset-filters");
    const toggleFilters = document.getElementById("toggle-filters");
    const catalogLayout = document.querySelector(".catalog-layout");

    function text(key) {
        return translations[currentLanguage][key] || key;
    }

    function translateLocation(location) {
        return currentLanguage === "hy" ? (locationTranslations[location] || location) : location;
    }

    function applyLanguage() {
        document.documentElement.lang = currentLanguage;
        document.querySelectorAll("[data-i18n]").forEach(element => element.textContent = text(element.dataset.i18n));
        document.querySelectorAll("[data-i18n-placeholder]").forEach(element => element.placeholder = text(element.dataset.i18nPlaceholder));
        document.querySelectorAll(".language-btn").forEach(button => button.classList.toggle("active", button.dataset.language === currentLanguage));
        updateFilterToggle();
        locationOptions.querySelectorAll("label").forEach(label => {
            const input = label.querySelector("input");
            if (input && label.lastChild) label.lastChild.textContent = ` ${translateLocation(input.value)}`;
        });
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

    document.querySelectorAll(".language-btn").forEach(button => button.addEventListener("click", () => {
        currentLanguage = button.dataset.language;
        localStorage.setItem("preferredLanguage", currentLanguage);
        applyLanguage();
        if (allListings.length > 0) applyFilters();
    }));
    applyLanguage();

    let allListings = [];

    fetch("scrapers/processors/master_listings_json/all_for_sale_rent.json")
        .then(response => {
            if (!response.ok) {
                throw new Error("Failed to load listings data.");
            }
            return response.json();
        })
        .then(data => {
            allListings = data.filter(item => 
                item.property_category && 
                item.property_category !== "General / Unclassified" && 
                item.property_category !== "Media-Only"
            );
            
            populateLocations();
            applyFilters();
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
        
        if (locations.length > 10 && locationSearchInput) {
            locationSearchInput.style.display = "block";
            
            locationSearchInput.addEventListener("input", (e) => {
                const query = e.target.value.toLowerCase().trim();
                const labels = locationOptions.querySelectorAll("label");
                
                labels.forEach(label => {
                    const textContent = label.textContent.toLowerCase();
                    label.style.display = textContent.includes(query) ? "" : "none";
                });
            });
        }

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

    function applyFilters() {
        const selectedTypes = [...document.querySelectorAll("input[name='listing-type']:checked")].map(input => input.value);
        const selectedPropertyTypes = [...document.querySelectorAll("input[name='property-type']:checked")].map(input => input.value);
        const listingTypeMode = document.getElementById("listing-type-mode").value;
        const propertyTypeMode = document.getElementById("property-type-mode").value;
        const selectedLocations = [...document.querySelectorAll("input[name='location-filter']:checked")].map(input => input.value);
        const locationMode = document.getElementById("location-mode").value;
        const selectedSource = document.getElementById("source-filter").value;
        const minPrice = Number(document.getElementById("min-price").value) || 0;
        const maxPrice = Number(document.getElementById("max-price").value) || Infinity;
        const minimumRooms = Number(document.getElementById("rooms-filter").value) || 0;
        const sortOrder = document.getElementById("sort-filter").value;

        const filteredListings = allListings.filter(item => {
            const itemPrice = getFirstPrice(item);
            const sourceMatches = selectedSource === "All" || item.source === selectedSource || (selectedSource === "Facebook" && (!item.source || item.source === "Facebook"));
            const typeMatches = matchesSelection(item.listing_type, selectedTypes, listingTypeMode);
            const propertyTypeMatches = matchesSelection(item.property_category, selectedPropertyTypes, propertyTypeMode);
            const locationMatches = selectedLocations.length === 0 || (locationMode === "exclude"
                ? !(item.locations || []).some(location => selectedLocations.includes(location))
                : (item.locations || []).some(location => selectedLocations.includes(location)));
            const priceMatches = itemPrice === null ? minPrice === 0 : itemPrice >= minPrice && itemPrice <= maxPrice;
            const roomMatches = minimumRooms === 0 || (item.rooms || []).some(room => Number(room) >= minimumRooms);

            return sourceMatches && typeMatches && propertyTypeMatches && locationMatches && priceMatches && roomMatches;
        });

        filteredListings.sort((first, second) => {
            if (sortOrder === "price-asc") return (getFirstPrice(first) ?? Infinity) - (getFirstPrice(second) ?? Infinity);
            if (sortOrder === "price-desc") return (getFirstPrice(second) ?? -Infinity) - (getFirstPrice(first) ?? -Infinity);
            if (sortOrder === "size-asc") return (getFirstSize(first) ?? Infinity) - (getFirstSize(second) ?? Infinity);
            if (sortOrder === "size-desc") return (getFirstSize(second) ?? -Infinity) - (getFirstSize(first) ?? -Infinity);
            return (second.creation_timestamp || 0) - (first.creation_timestamp || 0);
        });

        displayListings(filteredListings);
    }

    function displayListings(listings) {
        gridContainer.innerHTML = "";
        resultCount.textContent = translations[currentLanguage].listingCount(listings.length);

        if (listings.length === 0) {
            gridContainer.innerHTML = `<p class="empty-state">${text("noMatches")}</p>`;
            return;
        }

        const currencyChoice = document.getElementById("currency-filter").value;

        listings.forEach(item => {
            const card = document.createElement("article");
            card.className = "property-card";

            let priceText = text("priceUponRequest");
            if (item.prices && item.prices.length > 0) {
                const p = item.prices[0];
                if (currencyChoice === "USD") {
                    const valUSD = p.amount_usd !== undefined ? p.amount_usd : Math.round(p.amount_amd / 364.18);
                    priceText = `$${Number(valUSD).toLocaleString()} USD`;
                } else {
                    const valAMD = p.amount_amd !== undefined ? p.amount_amd : p.original_amount;
                    priceText = `${Number(valAMD).toLocaleString()} ֏`;
                }
            }

            let detailsArr = [];
            if (item.rooms && item.rooms.length > 0) {
                detailsArr.push(translations[currentLanguage].roomLabel(Number(item.rooms[0])));
            }
            if (item.sizes_sqm && item.sizes_sqm.length > 0) {
                detailsArr.push(`${item.sizes_sqm[0]} m²`);
            }
            const detailsText = detailsArr.length > 0 ? detailsArr.join(" • ") : (translations[currentLanguage].propertyTypes[item.property_category] || text("property"));

            const locationText = item.locations && item.locations.length > 0
                ? item.locations.map(translateLocation).join(", ")
                : text("armenia");

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

            card.innerHTML = `
                <div class="property-info">
                    <div class="listing-topline">
                        <div class="tags-container">
                            <span class="source-tag ${sourceClass}">${escapeHtml(sourceDisplay)}</span>
                            <span class="source-tag ${typeTagClass}">${escapeHtml(listingTypeLabel)}</span>
                        </div>
                        <span class="property-type">${escapeHtml(translations[currentLanguage].propertyTypes[item.property_category] || text("property"))}</span>
                    </div>
                    <h3 class="price">${escapeHtml(priceText)}</h3>
                    <p class="details">${escapeHtml(detailsText)}</p>
                    <p class="location">${escapeHtml(locationText)}</p>
                    <p class="description-snippet">${escapeHtml(item.full_text || '')}</p>
                    <a href="${item.url}" class="view-btn" target="_blank">${text("viewOriginal")}</a>
                </div>
            `;
            gridContainer.appendChild(card);
        });
    }

    function handleFilterChange(event) {
        if (event.target.matches(".filter-control, .mode-control, input[name='listing-type'], input[name='property-type'], input[name='location-filter']")) {
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
        document.querySelectorAll("input[type='checkbox']").forEach(input => input.checked = false);
        document.getElementById("source-filter").value = "All";
        document.getElementById("currency-filter").value = "AMD";
        document.getElementById("listing-type-mode").value = "include";
        document.getElementById("property-type-mode").value = "include";
        document.querySelectorAll("input[name='location-filter']").forEach(input => input.checked = false);
        document.getElementById("location-mode").value = "include";
        document.getElementById("min-price").value = "";
        document.getElementById("max-price").value = "";
        document.getElementById("rooms-filter").value = "All";
        document.getElementById("sort-filter").value = "newest";
        
        const locationSearchInput = document.getElementById("location-search");
        if (locationSearchInput) {
            locationSearchInput.value = "";
            locationOptions.querySelectorAll("label").forEach(label => label.style.display = "");
        }

        applyFilters();
    });

    function escapeHtml(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
        );
    }
});