/**
 * CIX Investment Platform - Main JavaScript
 */

// Global state
let lastResultsTimestamp = 0;

/**
 * Format currency values
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('en-GB', {
        style: 'currency',
        currency: 'GBP',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

/**
 * Format percentage values
 */
function formatPercent(value) {
    return (value * 100).toFixed(1) + '%';
}

/**
 * Check for results updates (used by Marketplace page)
 */
async function checkResultsTimestamp() {
    try {
        const response = await fetch('/api/results-timestamp');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error checking results timestamp:', error);
        return { exists: false, timestamp: 0 };
    }
}

/**
 * Show loading indicator
 */
function showLoading(containerId, message = 'Loading...') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <span>${message}</span>
            </div>
        `;
    }
}

/**
 * Create sector badge HTML
 */
function createSectorBadge(sector) {
    const cleanSector = sector.toLowerCase().replace(/[&\s]/g, '_');
    return `<span class="badge badge-sector ${cleanSector}">${sector.replace('_', ' ')}</span>`;
}

/**
 * Create risk badge HTML
 */
function createRiskBadge(level) {
    const levelClass = level.toLowerCase().includes('low') ? 'low' :
        level.toLowerCase().includes('medium') ? 'medium' : 'high';
    return `<span class="badge badge-risk ${levelClass}">${level}</span>`;
}

/**
 * Poll for updates at regular intervals
 */
function startPolling(callback, interval = 5000) {
    setInterval(async () => {
        const data = await checkResultsTimestamp();
        if (data.timestamp > lastResultsTimestamp && lastResultsTimestamp > 0) {
            callback(data);
        }
        lastResultsTimestamp = data.timestamp;
    }, interval);

    // Initial check
    checkResultsTimestamp().then(data => {
        lastResultsTimestamp = data.timestamp;
    });
}

/**
 * Initialize tooltips and interactive elements
 */
document.addEventListener('DOMContentLoaded', () => {
    // Add hover effects to nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('mouseenter', () => {
            item.style.transform = 'translateX(4px)';
        });
        item.addEventListener('mouseleave', () => {
            item.style.transform = 'translateX(0)';
        });
    });

    // Smooth transitions for cards
    document.querySelectorAll('.card, .metric-card').forEach(card => {
        card.style.transition = 'transform 0.2s ease, box-shadow 0.2s ease';
    });
});

console.log('CIX Investment Platform loaded');
