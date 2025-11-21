/**
 * Karnataka Hotspots Overview
 * Builds analytical charts and tables from the hotspot prediction API.
 */

const chartRefs = {
    topCities: null,
    distribution: null,
    weather: null
};

let overviewLoading = null;

document.addEventListener('DOMContentLoaded', () => {
    overviewLoading = document.getElementById('overviewLoading');
    const refreshBtn = document.getElementById('overviewRefreshBtn');

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadOverviewData({ manual: true }));
    }

    loadOverviewData({ initial: true });
});

async function loadOverviewData(options = {}) {
    const { initial = false, manual = false } = options;

    if (initial && overviewLoading) {
        overviewLoading.classList.remove('hidden');
    }

    if (manual) {
        setRefreshingState(true);
    }

    try {
        clearOverviewError();
        const response = await fetch('/api/karnataka-predictions');
        const payload = await response.json();

        if (!response.ok || !payload.success) {
            throw new Error(payload.message || 'Failed to load Karnataka overview data.');
        }

        const predictions = Array.isArray(payload.predictions) ? payload.predictions : [];
        updateSummaryCards(predictions);
        renderTopCitiesChart(predictions);
        renderDistributionChart(predictions);
        renderWeatherChart(predictions);
        populateCityTable(predictions);
        updateTimestamp(payload.timestamp);
    } catch (error) {
        console.error('✗ Overview fetch error:', error);
        showOverviewError(error.message || 'Unable to load overview data.');
    } finally {
        if (initial && overviewLoading) {
            overviewLoading.classList.add('hidden');
        }
        if (manual) {
            setRefreshingState(false);
        }
    }
}

function updateSummaryCards(predictions) {
    const totalEl = document.getElementById('totalOutput');
    const avgEl = document.getElementById('avgOutput');
    const medianEl = document.getElementById('medianOutput');
    const highEl = document.getElementById('highCities');
    const avgTempEl = document.getElementById('avgTemp');
    const avgWindEl = document.getElementById('avgWind');

    if (!predictions.length) {
        [totalEl, avgEl, medianEl, highEl, avgTempEl, avgWindEl].forEach(el => {
            if (el) el.textContent = '--';
        });
        return;
    }

    const powerValues = predictions.map(p => safeNumeric(p.predicted_power));
    const totalPower = powerValues.reduce((sum, value) => sum + value, 0);
    const averagePower = totalPower / powerValues.length;

    const sorted = [...powerValues].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    const medianPower = sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;

    const highCount = powerValues.filter(value => value >= 500).length;
    const averageTemp = predictions.reduce((sum, p) => sum + safeNumeric(p.temperature), 0) / predictions.length;
    const averageWind = predictions.reduce((sum, p) => sum + safeNumeric(p.wind_speed), 0) / predictions.length;

    if (totalEl) totalEl.textContent = formatEnergy(totalPower);
    if (avgEl) avgEl.textContent = formatPower(averagePower);
    if (medianEl) medianEl.textContent = formatPower(medianPower);
    if (highEl) highEl.textContent = `${highCount} cities`;
    if (avgTempEl) avgTempEl.textContent = `${averageTemp.toFixed(1)} °C`;
    if (avgWindEl) avgWindEl.textContent = `${averageWind.toFixed(1)} m/s`;
}

function renderTopCitiesChart(predictions) {
    const canvas = document.getElementById('topCitiesChart');
    if (!canvas) return;

    const topCities = [...predictions]
        .sort((a, b) => safeNumeric(b.predicted_power) - safeNumeric(a.predicted_power))
        .slice(0, 8);

    const labels = topCities.map(item => item.city);
    const data = topCities.map(item => safeNumeric(item.predicted_power));

    const config = {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Predicted Power (W)',
                    data,
                    backgroundColor: labels.map((_, index) => index === 0 ? '#2dd4bf' : '#38bdf8'),
                    borderRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: context => `${context.parsed.y.toLocaleString()} W`
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#cbd5f5' }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: value => `${value} W`,
                        color: '#cbd5f5'
                    },
                    grid: { color: 'rgba(148, 163, 184, 0.2)' }
                }
            }
        }
    };

    if (chartRefs.topCities) {
        chartRefs.topCities.data.labels = labels;
        chartRefs.topCities.data.datasets[0].data = data;
        chartRefs.topCities.update();
    } else {
        chartRefs.topCities = new Chart(canvas.getContext('2d'), config);
    }
}

function renderDistributionChart(predictions) {
    const canvas = document.getElementById('distributionChart');
    if (!canvas) return;

    const counts = { high: 0, medium: 0, low: 0 };
    predictions.forEach(prediction => {
        const value = safeNumeric(prediction.predicted_power);
        if (value >= 500) counts.high += 1;
        else if (value >= 300) counts.medium += 1;
        else counts.low += 1;
    });

    const data = [counts.high, counts.medium, counts.low];
    const labels = ['High (>=500 W)', 'Medium (300-499 W)', 'Low (<300 W)'];
    const colors = ['#14b8a6', '#38bdf8', '#fbbf24'];

    const config = {
        type: 'doughnut',
        data: {
            labels,
            datasets: [
                {
                    data,
                    backgroundColor: colors,
                    borderWidth: 0
                }
            ]
        },
        options: {
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#cbd5f5' }
                }
            }
        }
    };

    if (chartRefs.distribution) {
        chartRefs.distribution.data.datasets[0].data = data;
        chartRefs.distribution.update();
    } else {
        chartRefs.distribution = new Chart(canvas.getContext('2d'), config);
    }
}

function renderWeatherChart(predictions) {
    const canvas = document.getElementById('weatherChart');
    const summaryEl = document.getElementById('weatherSummary');
    if (!canvas) return;

    const dataset = predictions.map(prediction => ({
        x: safeNumeric(prediction.temperature),
        y: safeNumeric(prediction.predicted_power),
        r: Math.max(4, Math.min(14, safeNumeric(prediction.wind_speed) * 1.5)),
        city: prediction.city,
        wind: safeNumeric(prediction.wind_speed)
    }));

    if (summaryEl) {
        if (!dataset.length) {
            summaryEl.textContent = 'Refresh to view temperature vs. output insights.';
        } else {
            const warmLeaders = [...dataset]
                .sort((a, b) => b.y - a.y)
                .slice(0, 2)
                .map(point => point.city);
            summaryEl.textContent = `${warmLeaders.join(' & ')} show the strongest outputs right now. Larger bubbles highlight windier locations boosting convective cooling.`;
        }
    }

    const config = {
        type: 'bubble',
        data: {
            datasets: [
                {
                    label: 'Temperature vs Output',
                    data: dataset,
                    backgroundColor: 'rgba(56, 189, 248, 0.4)',
                    borderColor: '#38bdf8'
                }
            ]
        },
        options: {
            scales: {
                x: {
                    title: { display: true, text: 'Temperature (°C)', color: '#cbd5f5' },
                    ticks: { color: '#cbd5f5' },
                    grid: { color: 'rgba(148, 163, 184, 0.2)' }
                },
                y: {
                    title: { display: true, text: 'Predicted Power (W)', color: '#cbd5f5' },
                    ticks: { color: '#cbd5f5' },
                    grid: { color: 'rgba(148, 163, 184, 0.2)' }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: context => {
                            const point = context.raw;
                            const wind = point.wind.toFixed(1);
                            return `${point.city}: ${point.y.toLocaleString()} W @ ${point.x.toFixed(1)} °C (wind ${wind} m/s)`;
                        }
                    }
                },
                legend: { display: false }
            }
        }
    };

    if (chartRefs.weather) {
        chartRefs.weather.data.datasets[0].data = dataset;
        chartRefs.weather.update();
    } else {
        chartRefs.weather = new Chart(canvas.getContext('2d'), config);
    }
}

function populateCityTable(predictions) {
    const tbody = document.getElementById('cityTableBody');
    if (!tbody) return;

    if (!predictions.length) {
        tbody.innerHTML = '<tr><td colspan="6">No data available. Try refreshing shortly.</td></tr>';
        return;
    }

    const sorted = [...predictions].sort((a, b) => safeNumeric(b.predicted_power) - safeNumeric(a.predicted_power));
    tbody.innerHTML = sorted.map(prediction => {
        const power = formatPower(safeNumeric(prediction.predicted_power));
        const temperature = `${safeNumeric(prediction.temperature).toFixed(1)} °C`;
        const wind = `${safeNumeric(prediction.wind_speed).toFixed(1)} m/s`;
        const clouds = `${safeNumeric(prediction.clouds).toFixed(0)} %`;
        const humidity = `${safeNumeric(prediction.humidity).toFixed(0)} %`;
        return `
            <tr>
                <td>${prediction.city}</td>
                <td>${power}</td>
                <td>${temperature}</td>
                <td>${wind}</td>
                <td>${clouds}</td>
                <td>${humidity}</td>
            </tr>
        `;
    }).join('');
}

function updateTimestamp(timestamp) {
    const target = document.getElementById('overviewLastUpdated');
    if (!target) return;
    if (!timestamp) {
        target.textContent = '--';
        return;
    }
    const date = new Date(timestamp);
    target.textContent = Number.isNaN(date.getTime()) ? '--' : date.toLocaleString();
}

function showOverviewError(message) {
    const banner = document.getElementById('overviewError');
    if (!banner) return;
    banner.textContent = `⚠️ ${message}`;
    banner.classList.remove('hidden');
}

function clearOverviewError() {
    const banner = document.getElementById('overviewError');
    if (!banner) return;
    banner.classList.add('hidden');
    banner.textContent = '';
}

function setRefreshingState(isRefreshing) {
    const btn = document.getElementById('overviewRefreshBtn');
    const label = document.getElementById('overviewRefreshLabel');
    const loader = document.getElementById('overviewRefreshLoader');

    if (!btn || !label || !loader) return;

    btn.disabled = isRefreshing;
    if (isRefreshing) {
        label.textContent = 'Refreshing...';
        loader.classList.remove('hidden');
    } else {
        label.textContent = 'Refresh Snapshot';
        loader.classList.add('hidden');
    }
}

function formatPower(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return '--';
    return `${Math.round(numeric).toLocaleString()} W`;
}

function formatEnergy(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return '--';
    if (numeric >= 1_000_000) {
        return `${(numeric / 1_000_000).toFixed(2)} MW`;
    }
    if (numeric >= 1_000) {
        return `${(numeric / 1_000).toFixed(1)} kW`;
    }
    return `${Math.round(numeric)} W`;
}

function safeNumeric(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : 0;
}
