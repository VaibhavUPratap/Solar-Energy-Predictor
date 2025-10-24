/**
 * Karnataka Hotspots - Frontend JavaScript
 * Handles map rendering, data fetching, and hourly updates
 */

let karnatakaMap;
let cityMarkers = [];
let updateInterval;

document.addEventListener('DOMContentLoaded', function() {
    initializeKarnatakaMap();
    setupRefreshHandler();
    loadKarnatakaData();
    
    // Set up hourly updates
    updateInterval = setInterval(loadKarnatakaData, 3600000); // 1 hour
});

/**
 * Initialize Karnataka-focused map
 */
function initializeKarnatakaMap() {
    // Center on Karnataka
    karnatakaMap = L.map('karnatakaMap').setView([15.3173, 75.7139], 7);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(karnatakaMap);

    console.log('✓ Karnataka map initialized');
}

/**
 * Setup refresh button handler
 */
function setupRefreshHandler() {
    const refreshBtn = document.getElementById('refreshBtn');
    refreshBtn.addEventListener('click', function() {
        loadKarnatakaData();
    });
}

/**
 * Load Karnataka cities data
 */
async function loadKarnatakaData() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    const lastUpdated = document.getElementById('lastUpdated');
    
    try {
        // Show loading
        loadingOverlay.classList.remove('hidden');
        
        console.log('🔍 Loading Karnataka predictions...');
        
        const response = await fetch('/api/karnataka-predictions');
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Failed to load predictions');
        }
        
        if (data.success) {
            console.log('✓ Karnataka predictions loaded:', data);
            displayKarnatakaData(data.predictions);
            updateMap(data.predictions);
            updateStatistics(data.predictions);
            
            // Update timestamp
            const now = new Date();
            lastUpdated.textContent = now.toLocaleString();
        }
        
    } catch (error) {
        console.error('✗ Error loading Karnataka data:', error);
        showError('Failed to load Karnataka predictions. Please try again.');
    } finally {
        loadingOverlay.classList.add('hidden');
    }
}

/**
 * Display cities data in grid
 */
function displayKarnatakaData(predictions) {
    const citiesGrid = document.getElementById('citiesGrid');
    
    // Sort by predicted power (highest first)
    const sortedPredictions = predictions.sort((a, b) => b.predicted_power - a.predicted_power);
    
    citiesGrid.innerHTML = sortedPredictions.map(prediction => {
        const powerClass = getPowerClass(prediction.predicted_power);
        const bgColor = powerClass === 'high-power' ? 'bg-green-500/10 border-green-500/30' : 
                       powerClass === 'medium-power' ? 'bg-yellow-500/10 border-yellow-500/30' : 
                       'bg-red-500/10 border-red-500/30';
        
        return `
            <div class="bg-slate-700/50 ${bgColor} border rounded-xl p-4 cursor-pointer transition-all duration-300 hover:scale-105 hover:shadow-lg" onclick="focusOnCity(${prediction.latitude}, ${prediction.longitude})">
                <div class="font-bold text-white mb-2">${prediction.city}</div>
                <div class="text-2xl font-bold text-cyan-400 mb-3">${prediction.predicted_power} W</div>
                <div class="space-y-1 text-sm text-slate-400">
                    <div>🌡️ ${prediction.temperature.toFixed(1)}°C</div>
                    <div>💨 ${prediction.wind_speed.toFixed(1)} m/s</div>
                    <div>☁️ ${prediction.clouds}%</div>
                    <div>💧 ${prediction.humidity}%</div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Update map with city markers
 */
function updateMap(predictions) {
    // Clear existing markers
    cityMarkers.forEach(marker => karnatakaMap.removeLayer(marker));
    cityMarkers = [];
    
    // Add new markers
    predictions.forEach(prediction => {
        const powerClass = getPowerClass(prediction.predicted_power);
        const markerColor = getMarkerColor(powerClass);
        
        const marker = L.circleMarker([prediction.latitude, prediction.longitude], {
            radius: Math.max(8, Math.min(20, prediction.predicted_power / 50)),
            fillColor: markerColor,
            color: 'white',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        }).addTo(karnatakaMap);
        
        marker.bindPopup(`
            <div style="text-align: center;">
                <h3>${prediction.city}</h3>
                <p><strong>${prediction.predicted_power} W</strong></p>
                <p>🌡️ ${prediction.temperature.toFixed(1)}°C</p>
                <p>💨 ${prediction.wind_speed.toFixed(1)} m/s</p>
                <p>☁️ ${prediction.clouds}%</p>
                <p>${prediction.weather_description}</p>
            </div>
        `);
        
        cityMarkers.push(marker);
    });
}

/**
 * Update statistics
 */
function updateStatistics(predictions) {
    const totalCities = document.getElementById('totalCities');
    const avgPower = document.getElementById('avgPower');
    const maxPower = document.getElementById('maxPower');
    const bestCity = document.getElementById('bestCity');
    
    const total = predictions.length;
    const avg = predictions.reduce((sum, p) => sum + p.predicted_power, 0) / total;
    const max = Math.max(...predictions.map(p => p.predicted_power));
    const best = predictions.find(p => p.predicted_power === max);
    
    totalCities.textContent = total;
    avgPower.textContent = `${avg.toFixed(0)} W`;
    maxPower.textContent = `${max} W`;
    bestCity.textContent = best ? best.city : '--';
}

/**
 * Get power classification
 */
function getPowerClass(power) {
    if (power >= 800) return 'high-power';
    if (power >= 400) return 'medium-power';
    return 'low-power';
}

/**
 * Get marker color based on power class
 */
function getMarkerColor(powerClass) {
    switch (powerClass) {
        case 'high-power': return '#10b981';
        case 'medium-power': return '#f59e0b';
        case 'low-power': return '#ef4444';
        default: return '#6b7280';
    }
}

/**
 * Focus map on specific city
 */
function focusOnCity(lat, lon) {
    karnatakaMap.setView([lat, lon], 10);
}

/**
 * Show error message
 */
function showError(message) {
    // You can implement a toast notification or alert here
    alert(`⚠️ ${message}`);
}

// Clean up interval when page unloads
window.addEventListener('beforeunload', function() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});