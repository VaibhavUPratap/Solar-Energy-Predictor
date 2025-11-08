/**
 * Karnataka Hotspots - Aurora UI edition
 * Manages map rendering, API polling, and interactive city cards.
 */

let karnatakaMap;
let cityMarkers = [];
let updateInterval;

const REFRESH_INTERVAL_MS = 60 * 60 * 1000; // 1 hour

document.addEventListener('DOMContentLoaded', () => {
    initializeKarnatakaMap();
    setupRefreshHandler();
    loadKarnatakaData({ initial: true });

    updateInterval = setInterval(() => loadKarnatakaData({ silent: true }), REFRESH_INTERVAL_MS);
});

/**
 * Initialise the Leaflet map centered on Karnataka.
 */
function initializeKarnatakaMap() {
    karnatakaMap = L.map('karnatakaMap').setView([15.3173, 75.7139], 7);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(karnatakaMap);

    console.log('✓ Karnataka map initialised');
}

/**
 * Attach behaviour to the manual refresh button.
 */
function setupRefreshHandler() {
    const refreshBtn = document.getElementById('refreshBtn');
    refreshBtn.addEventListener('click', () => {
        loadKarnatakaData({ manual: true });
    });
}

/**
 * Fetch Karnataka predictions from the backend.
 * @param {Object} options - Flags controlling UI behaviour.
 */
async function loadKarnatakaData(options = {}) {
    const { initial = false, manual = false, silent = false } = options;
    const loadingOverlay = document.getElementById('loadingOverlay');

    if (initial) {
        loadingOverlay.classList.remove('hidden');
    }

    if (manual) {
        setRefreshingState(true);
    }

    try {
    clearHotspotError();
    console.log('[refresh] Fetching Karnataka predictions...');

        const response = await fetch('/api/karnataka-predictions');
        const payload = await response.json();

        if (!response.ok || !payload.success) {
            throw new Error(payload.message || 'Failed to load predictions');
        }

        const predictions = Array.isArray(payload.predictions) ? payload.predictions : [];
        console.log(`✓ Received ${predictions.length} Karnataka predictions`);

        displayKarnatakaData(predictions);
        updateMap(predictions);
        updateStatistics(predictions);
        stampLastUpdated();
    } catch (error) {
        console.error('✗ Karnataka predictions error:', error);
        showHotspotError(error.message || 'Unable to load Karnataka predictions. Please try again.');
    } finally {
        if (initial) {
            loadingOverlay.classList.add('hidden');
        }
        if (manual) {
            setRefreshingState(false);
        }
        if (!initial && !manual && !silent) {
            loadingOverlay.classList.add('hidden');
        }
    }
}

/**
 * Populate the city list panel.
 * @param {Array<Object>} predictions - City-level prediction data.
 */
function displayKarnatakaData(predictions) {
    const citiesGrid = document.getElementById('citiesGrid');

    if (!predictions.length) {
        citiesGrid.innerHTML = '<p class="card-subtitle">No hotspot data available. Try refreshing in a moment.</p>';
        return;
    }

    const sorted = [...predictions].sort((a, b) => Number(b.predicted_power) - Number(a.predicted_power));

    citiesGrid.innerHTML = sorted.map(prediction => {
        const tier = getPowerTier(Number(prediction.predicted_power));
        const powerDisplay = formatPower(prediction.predicted_power);
        const temperature = safeNumeric(prediction.temperature).toFixed(1);
        const windSpeed = safeNumeric(prediction.wind_speed).toFixed(1);
        const clouds = safeNumeric(prediction.clouds).toFixed(0);
        const humidity = safeNumeric(prediction.humidity).toFixed(0);

        return `
            <div class="hotspot-card hotspot-card--${tier}" data-lat="${prediction.latitude}" data-lon="${prediction.longitude}">
                <div class="hotspot-card__header">
                    <span class="hotspot-city">${prediction.city}</span>
                    <span class="hotspot-power">${powerDisplay}</span>
                </div>
                <div class="hotspot-meta">
                    <span>&#127777;&#65039; ${temperature}°C</span>
                    <span>&#128246; ${humidity}%</span>
                </div>
                <div class="hotspot-meta">
                    <span>&#128168; ${windSpeed} m/s</span>
                    <span>&#9729;&#65039; ${clouds}%</span>
                </div>
            </div>
        `;
    }).join('');

    bindCityCardHandlers();
}

/**
 * Attach click handlers to each city card.
 */
function bindCityCardHandlers() {
    document.querySelectorAll('.hotspot-card').forEach(card => {
        card.addEventListener('click', () => {
            const lat = parseFloat(card.dataset.lat);
            const lon = parseFloat(card.dataset.lon);
            focusOnCity(lat, lon);
        });
    });
}

/**
 * Push markers to the map for each city.
 */
function updateMap(predictions) {
    cityMarkers.forEach(entry => karnatakaMap.removeLayer(entry.marker));
    cityMarkers = [];

    predictions.forEach(prediction => {
        const tier = getPowerTier(Number(prediction.predicted_power));
        const markerColor = getMarkerColor(tier);
        const magnitude = Math.max(10, Math.min(26, Number(prediction.predicted_power) / 35));

        const marker = L.circleMarker([prediction.latitude, prediction.longitude], {
            radius: magnitude,
            fillColor: markerColor,
            color: '#f8fafc',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
        }).addTo(karnatakaMap);

        marker.bindPopup(`
            <div style="text-align:center;">
                <h3 style="margin-bottom:0.35rem;">${prediction.city}</h3>
                <p style="font-weight:600; margin-bottom:0.35rem;">${formatPower(prediction.predicted_power)}</p>
                <p style="margin:0;">&#127777;&#65039; ${safeNumeric(prediction.temperature).toFixed(1)}°C · &#128168; ${safeNumeric(prediction.wind_speed).toFixed(1)} m/s</p>
                <p style="margin:0.2rem 0 0;">&#9729;&#65039; ${safeNumeric(prediction.clouds).toFixed(0)}% · ${prediction.weather_description || ''}</p>
            </div>
        `);

        cityMarkers.push({ marker, lat: prediction.latitude, lon: prediction.longitude });
    });
}

/**
 * Update stats summary cards.
 */
function updateStatistics(predictions) {
    const totalCitiesEl = document.getElementById('totalCities');
    const avgPowerEl = document.getElementById('avgPower');
    const maxPowerEl = document.getElementById('maxPower');
    const bestCityEl = document.getElementById('bestCity');

    if (!predictions.length) {
        totalCitiesEl.textContent = '--';
        avgPowerEl.textContent = '--';
        maxPowerEl.textContent = '--';
        bestCityEl.textContent = '--';
        return;
    }

    const total = predictions.length;
    const powers = predictions.map(p => Number(p.predicted_power) || 0);
    const average = powers.reduce((sum, value) => sum + value, 0) / total;
    const max = Math.max(...powers);
    const best = predictions.find(p => Number(p.predicted_power) === max);

    totalCitiesEl.textContent = String(total);
    avgPowerEl.textContent = `${Math.round(average)} W`;
    maxPowerEl.textContent = `${Math.round(max)} W`;
    bestCityEl.textContent = best ? best.city : '--';
}

/**
 * Focus the map on a specific city marker.
 */
function focusOnCity(lat, lon) {
    if (Number.isFinite(lat) && Number.isFinite(lon)) {
        karnatakaMap.setView([lat, lon], 10);
        const entry = cityMarkers.find(item => Math.abs(item.lat - lat) < 1e-6 && Math.abs(item.lon - lon) < 1e-6);
        if (entry) {
            entry.marker.openPopup();
        }
    }
}

/**
 * Display an error banner specific to the hotspots page.
 */
function showHotspotError(message) {
    const banner = document.getElementById('hotspotError');
    banner.textContent = `⚠️ ${message}`;
    banner.classList.remove('hidden');
}

/**
 * Clear any displayed error banner.
 */
function clearHotspotError() {
    const banner = document.getElementById('hotspotError');
    banner.classList.add('hidden');
    banner.textContent = '';
}

/**
 * Toggle manual refresh button state.
 */
function setRefreshingState(isRefreshing) {
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshLoader = document.getElementById('refreshLoader');
    const refreshLabel = refreshBtn.querySelector('.refresh-label');

    refreshBtn.disabled = isRefreshing;
    if (isRefreshing) {
        refreshLabel.textContent = 'Refreshing...';
        refreshLoader.classList.remove('hidden');
    } else {
        refreshLabel.textContent = 'Refresh Predictions';
        refreshLoader.classList.add('hidden');
    }
}

/**
 * Update the "last updated" timestamp chip.
 */
function stampLastUpdated() {
    const lastUpdated = document.getElementById('lastUpdated');
    const now = new Date();
    lastUpdated.textContent = now.toLocaleString();
}

/**
 * Return power tier string for styling hooks.
 */
function getPowerTier(power) {
    if (power >= 500) return 'high';
    if (power >= 300) return 'medium';
    return 'low';
}

/**
 * Map tier to marker colour.
 */
function getMarkerColor(tier) {
    switch (tier) {
        case 'high':
            return '#22d3ee';
        case 'medium':
            return '#a855f7';
        case 'low':
        default:
            return '#f97316';
    }
}

/**
 * Format wattage values for display.
 */
function formatPower(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return '--';
    }
    const rounded = Math.round(numeric);
    return `${rounded.toLocaleString()} W`;
}

/**
 * Coerce API values to numbers with graceful fallback.
 */
function safeNumeric(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : 0;
}

// Cleanup interval on navigation away
window.addEventListener('beforeunload', () => {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});
