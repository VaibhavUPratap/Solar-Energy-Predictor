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
            updateMap(data.prediction.latitude, data.prediction.longitude, data.prediction.city);
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
    
    // Update result values
    document.getElementById('predictedPower').textContent = `${data.prediction.predicted_power} W`;
    document.getElementById('temperature').textContent = `${data.weather.temperature.toFixed(1)}°C`;
    document.getElementById('windSpeed').textContent = `${data.weather.wind_speed.toFixed(1)} m/s`;
    document.getElementById('clouds').textContent = `${data.weather.clouds}%`;
    
    // Update location info
    document.getElementById('locationName').textContent = 
        `${data.prediction.city}, ${data.prediction.country}`;
    document.getElementById('weatherDescription').textContent = 
        `${capitalizeFirstLetter(data.weather.description)}`;
    
    // Update solar parameters
    document.getElementById('poaDirect').textContent = data.solar_parameters.poa_direct;
    document.getElementById('poaSky').textContent = data.solar_parameters.poa_sky_diffuse;
    document.getElementById('poaGround').textContent = data.solar_parameters.poa_ground_diffuse;
    document.getElementById('solarElevation').textContent = data.solar_parameters.solar_elevation;
    
    // Show results with animation
    resultsSection.classList.remove('hidden');
    resultsSection.classList.add('animate-fadeIn');
}

/**
 * Update map with location marker
 * @param {number} lat - Latitude
 * @param {number} lon - Longitude
 * @param {string} city - City name
 */
function updateMap(lat, lon, city) {
    // Remove existing marker if any
    if (marker) {
        map.removeLayer(marker);
    }

    // Add new marker
    marker = L.marker([lat, lon]).addTo(map);
    marker.bindPopup(`<b>${city}</b><br>Solar prediction location`).openPopup();

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
`;
document.head.appendChild(style);