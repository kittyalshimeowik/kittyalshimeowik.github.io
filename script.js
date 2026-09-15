document.addEventListener("DOMContentLoaded", () => {
    console.log("Armenia Real Estate Hub initialized.");

    const gridContainer = document.getElementById("listings-grid");
    const filterButtons = document.querySelectorAll(".filter-btn");

    let allListings = [];

    // Fetch the JSON data output file
    fetch("all_for_sale_rent.json")
        .then(response => {
            if (!response.ok) {
                throw new Error("Failed to load listings data.");
            }
            return response.json();
        })
        .then(data => {
            // Keep only legitimate real estate categories from the scraper data
            allListings = data.filter(item => 
                item.property_category && 
                item.property_category !== "General / Unclassified" && 
                item.property_category !== "Media-Only"
            );
            
            displayListings(allListings);
        })
        .catch(error => {
            console.error("Error loading JSON:", error);
            gridContainer.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: #d32f2f;">Failed to load property data. Make sure you're running a local server (e.g., Live Server in VS Code) to allow JSON fetching.</p>`;
        });

    // Render listings cards into DOM
    function displayListings(listings) {
        gridContainer.innerHTML = "";

        if (listings.length === 0) {
            gridContainer.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: #666;">No listings found for this location filter.</p>`;
            return;
        }

        listings.forEach(item => {
            const card = document.createElement("div");
            card.className = "property-card";

            // Format price extraction safely
            let priceText = "Price Upon Request";
            if (item.prices && item.prices.length > 0) {
                const p = item.prices[0];
                priceText = `${p.raw_text || p.amount} ${p.currency !== "Unspecified Currency" ? p.currency : ''}`.trim();
            }

            // Format rooms & sizes metadata
            let detailsArr = [];
            if (item.rooms && item.rooms.length > 0) {
                detailsArr.push(`${item.rooms.join(', ')} Room${item.rooms[0] > 1 ? 's' : ''}`);
            }
            if (item.sizes_sqm && item.sizes_sqm.length > 0) {
                detailsArr.push(`${item.sizes_sqm[0]} m²`);
            }
            const detailsText = detailsArr.length > 0 ? detailsArr.join(" • ") : item.property_category;

            // Format location string
            const locationText = item.locations && item.locations.length > 0 
                ? `📍 ${item.locations.join(', ')}` 
                : "📍 Armenia";

            // Listing type tag handling (Sale vs Rent)
            const listingType = item.listing_type || "Unknown";
            let typeTagClass = "sale";
            if (listingType === "Rent") typeTagClass = "rent";

            card.innerHTML = `
                <div class="tags-container">
                    <span class="source-tag fb">FB</span>
                    <span class="source-tag ${typeTagClass}">${listingType}</span>
                </div>
                <div class="property-img-placeholder">📸 ${item.property_category || 'Property'}</div>
                <div class="property-info">
                    <h3 class="price">${priceText}</h3>
                    <p class="details">${detailsText}</p>
                    <p class="location">${locationText}</p>
                    <p class="description-snippet">${escapeHtml(item.full_text || '')}</p>
                    <a href="${item.url}" class="view-btn" target="_blank">View Original Post</a>
                </div>
            `;
            gridContainer.appendChild(card);
        });
    }

    // Filter interaction handling
    filterButtons.forEach(button => {
        button.addEventListener("click", () => {
            filterButtons.forEach(btn => btn.classList.remove("active"));
            button.classList.add("active");

            const selectedLocation = button.getAttribute("data-location");

            if (selectedLocation === "All") {
                displayListings(allListings);
            } else {
                const filtered = allListings.filter(item => 
                    item.locations && item.locations.some(loc => loc.includes(selectedLocation))
                );
                displayListings(filtered);
            }
        });
    });

    // Helper to escape special HTML characters safely in snippets
    function escapeHtml(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
        );
    }
});