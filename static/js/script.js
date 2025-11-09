/**
 * Solar Energy Predictor - Frontend JavaScript
 * Handles form submission, API calls, map rendering, and UI updates
 */

// Initialize map
let map;
let marker;

document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    setupFormHandler();
});

/**
 * Initialize Leaflet map with default view
 */
function initializeMap() {
    // Create map centered on world view
    map = L.map('map').setView([20, 0], 2);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    console.log('✓ Map initialized');
}

/**
 * Setup form submission handler
 */
function setupFormHandler() {
    const form = document.getElementById('predictionForm');
    const cityInput = document.getElementById('cityInput');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const city = cityInput.value.trim();
        
        if (!city) {
            showError('Please enter a city name');
            return;
        }

        await makePrediction(city);
    });
}

/**
 * Make prediction API call
 * @param {string} city - City name to predict for
 */
async function makePrediction(city) {
    const predictBtn = document.getElementById('predictBtn');
    const btnText = document.getElementById('btnText');
    const btnLoader = document.getElementById('btnLoader');
    const resultsSection = document.getElementById('resultsSection');
    const errorMessage = document.getElementById('errorMessage');

    try {
        // Show loading state
        predictBtn.disabled = true;
        btnText.classList.add('hidden');
        btnLoader.classList.remove('hidden');
        errorMessage.classList.add('hidden');
        resultsSection.classList.add('hidden');

        console.log(`🔍 Fetching prediction for: ${city}`);

        // Make API request
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ city: city })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'Prediction failed');
        }

        if (data.success) {
            console.log('✓ Prediction successful:', data);
            displayResults(data);
            updateMap(data);
        } else {
            throw new Error('Invalid response from server');
        }

    } catch (error) {
        console.error('✗ Prediction error:', error);
        showError(error.message || 'Failed to get prediction. Please try again.');
    } finally {
        // Reset button state
        predictBtn.disabled = false;
        btnText.classList.remove('hidden');
        btnLoader.classList.add('hidden');
    }
}

/**
 * Display prediction results in UI
 * @param {Object} data - Prediction response data
 */
function displayResults(data) {
    const resultsSection = document.getElementById('resultsSection');
    
    const isNight = Boolean(data.prediction && data.prediction.is_night);
    const nightMessage = (data.prediction && data.prediction.night_message) || '';

    // Update result values
    const predictedPowerDisplay = formatMetric(data.prediction.predicted_power, { decimals: 0, suffix: ' W' });
    const predictedPowerEl = document.getElementById('predictedPower');
    predictedPowerEl.textContent = isNight ? `${predictedPowerDisplay} (nighttime)` : predictedPowerDisplay;
    document.getElementById('temperature').textContent = formatMetric(data.weather.temperature, { decimals: 1, suffix: '°C' });
    document.getElementById('windSpeed').textContent = formatMetric(data.weather.wind_speed, { decimals: 1, suffix: ' m/s' });
    document.getElementById('clouds').textContent = formatMetric(data.weather.clouds, { decimals: 0, suffix: '%' });
    
    // Update location info
    document.getElementById('locationName').textContent = 
        `${data.prediction.city}, ${data.prediction.country}`;
    let description = (data.weather && typeof data.weather.description === 'string')
        ? data.weather.description.trim()
        : '';
    if (description) {
        description = capitalizeFirstLetter(description);
    }
    if (isNight && nightMessage) {
        description = nightMessage;
    }
    document.getElementById('weatherDescription').textContent = 
        description || 'No weather summary available.';
    
    // Update solar parameters
    document.getElementById('poaDirect').textContent = formatMetric(data.solar_parameters.poa_direct, { decimals: 0, suffix: ' W/m²' });
    document.getElementById('poaSky').textContent = formatMetric(data.solar_parameters.poa_sky_diffuse, { decimals: 0, suffix: ' W/m²' });
    document.getElementById('poaGround').textContent = formatMetric(data.solar_parameters.poa_ground_diffuse, { decimals: 0, suffix: ' W/m²' });
    document.getElementById('solarElevation').textContent = formatMetric(data.solar_parameters.solar_elevation, { decimals: 1, suffix: '°' });

    const mapPowerEl = document.getElementById('mapPredictedPower');
    if (mapPowerEl) {
        mapPowerEl.textContent = isNight ? `${predictedPowerDisplay} (nighttime)` : predictedPowerDisplay;
    }

    const mapSolarEl = document.getElementById('mapSolarElevation');
    if (mapSolarEl) {
        mapSolarEl.textContent = formatMetric(data.solar_parameters.solar_elevation, { decimals: 1, suffix: '°' });
    }

    const mapConditionsEl = document.getElementById('mapConditions');
    if (mapConditionsEl) {
        const temp = formatMetric(data.weather.temperature, { decimals: 1, suffix: '°C' });
        const wind = formatMetric(data.weather.wind_speed, { decimals: 1, suffix: ' m/s' });
        const clouds = formatMetric(data.weather.clouds, { decimals: 0, suffix: '% clouds' });
        const baseConditions = `${temp} • ${wind} • ${clouds}`;
        mapConditionsEl.textContent = isNight ? `Nighttime • ${baseConditions}` : baseConditions;
    }
    
    // Show results with animation
    resultsSection.classList.remove('hidden');
    resultsSection.classList.remove('animate-fadeIn');
    void resultsSection.offsetWidth;
    resultsSection.classList.add('animate-fadeIn');
}

/**
 * Update map with location marker
 * @param {Object} dataset - Prediction dataset including prediction and weather
 */
function updateMap(dataset) {
    if (!dataset || !dataset.prediction) {
        return;
    }

    const prediction = dataset.prediction;
    const weather = dataset.weather || {};
    const lat = Number(prediction.latitude);
    const lon = Number(prediction.longitude);
    const city = prediction.city || 'Selected location';

    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        return;
    }

    // Remove existing marker if any
    if (marker) {
        map.removeLayer(marker);
    }

    const isNight = Boolean(prediction.is_night);
    const predictedPowerRaw = Number(prediction.predicted_power);
    const predictedPower = Number.isFinite(predictedPowerRaw) ? predictedPowerRaw : 0;
    const powerTier = getPowerTier(predictedPower);
    const fillColor = isNight ? '#475569' : getMarkerColor(powerTier);
    const radius = isNight ? 8 : Math.max(10, Math.min(24, predictedPower / 40));
    const popupPowerDisplay = formatMetric(predictedPower, { decimals: 0, suffix: ' W', round: true });
    const popupPower = isNight ? `${popupPowerDisplay} (night)` : popupPowerDisplay;
    const nightPopupNote = isNight
        ? '<p style="margin:0.35rem 0 0; color:#94a3b8;">Nighttime conditions: solar output is effectively zero.</p>'
        : '';

    marker = L.circleMarker([lat, lon], {
        radius,
        fillColor,
        color: '#f8fafc',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.85
    }).addTo(map);

    marker.bindPopup(`
        <div style="text-align:center;">
            <h3 style="margin-bottom:0.35rem;">${city}</h3>
            <p style="font-weight:600; margin-bottom:0.35rem;">${popupPower}</p>
            <p style="margin:0;">${formatMetric(weather.temperature, { decimals: 1, suffix: '°C' })} · ${formatMetric(weather.wind_speed, { decimals: 1, suffix: ' m/s' })}</p>
            <p style="margin:0.2rem 0 0;">${formatMetric(weather.clouds, { decimals: 0, suffix: '% clouds' })}</p>
            ${nightPopupNote}
        </div>
    `).openPopup();

    // Center map on location with zoom
    map.setView([lat, lon], 10);

    console.log(`📍 Map updated: ${city} (${lat}, ${lon})`);
}

/**
 * Display error message
 * @param {string} message - Error message to display
 */
function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = `⚠️ ${message}`;
    errorMessage.classList.remove('hidden');
    
    // Hide error after 5 seconds
    setTimeout(() => {
        errorMessage.classList.add('hidden');
    }, 5000);
}

/**
 * Capitalize first letter of string
 * @param {string} str - Input string
 * @returns {string} Capitalized string
 */
function capitalizeFirstLetter(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Format numeric metrics with sensible defaults.
 */
function formatMetric(value, { decimals = 0, suffix = '', round } = {}) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return suffix ? `-- ${suffix.trim()}` : '--';
    }

    const shouldRound = round !== undefined ? round : decimals === 0;
    const factor = Math.pow(10, decimals);
    const adjusted = shouldRound
        ? Math.round(numeric * factor) / factor
        : numeric;

    const formatted = decimals === 0
        ? adjusted.toLocaleString()
        : adjusted.toFixed(decimals);

    return `${formatted}${suffix}`;
}

function getPowerTier(power) {
    if (power >= 500) return 'high';
    if (power >= 300) return 'medium';
    return 'low';
}

function getMarkerColor(tier) {
    switch (tier) {
        case 'high':
            return '#2dd4bf';
        case 'medium':
            return '#38bdf8';
        default:
            return '#fbbf24';
    }
}

// Add fade-in animation CSS dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .animate-fadeIn {
        animation: fadeIn 0.5s ease-in-out;
    }
`;
document.head.appendChild(style);