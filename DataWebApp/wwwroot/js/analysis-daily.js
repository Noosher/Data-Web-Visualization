/**
 * Daily Analysis - ApexCharts Initialization
 * Renders gauge, line, and bar charts for each KPI card
 */

document.addEventListener('DOMContentLoaded', function () {
    initializeAllKpiCards();
    initializeTooltips();
});

/**
 * Toggle bar chart visibility
 */
function toggleBarChart(barChartId) {
    const content = document.getElementById(barChartId + '-content');
    const icon = document.getElementById(barChartId + '-icon');

    if (content && icon) {
        content.classList.toggle('collapsed');
        icon.classList.toggle('collapsed');
    }
}

/**
 * Initialize all KPI cards with charts
 */
function initializeAllKpiCards() {
    const kpiCards = document.querySelectorAll('.kpi-card[data-symbol]');

    kpiCards.forEach(card => {
        const symbol = card.getAttribute('data-symbol');

        // Parse chart data from data attributes
        const lineChartDataRaw = card.getAttribute('data-line-chart');
        const barChartDataRaw = card.getAttribute('data-bar-chart');
        const performanceScore = parseFloat(card.getAttribute('data-performance-score'));

        if (!lineChartDataRaw || !barChartDataRaw) {
            console.warn(`Skipping ${symbol}: missing chart data`);
            return;
        }

        try {
            const lineChartData = JSON.parse(lineChartDataRaw);
            const barChartData = JSON.parse(barChartDataRaw);

            // Initialize all charts for this card
            initializeGauge(symbol, performanceScore);
            initializeLineChart(symbol, lineChartData);
            initializeBarChart(symbol, barChartData);
        } catch (error) {
            console.error(`Error initializing charts for ${symbol}:`, error);
        }
    });
}

/**
 * Initialize gauge chart (performance score)
 */
function initializeGauge(symbol, score) {
    const containerId = `gauge-${symbol.toLowerCase()}`;
    const container = document.getElementById(containerId);

    if (!container) {
        console.warn(`Gauge container not found: ${containerId}`);
        return;
    }

    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';

    // Determine color based on score
    let color = '#22c55e'; // Green for high score
    if (score < 40) {
        color = '#ef4444'; // Red for low score
    } else if (score < 70) {
        color = '#f59e0b'; // Amber for medium score
    }

    // Track background color with better contrast in light mode
    const trackBg = isDarkMode
        ? getComputedStyle(document.documentElement).getPropertyValue('--app-border-subtle').trim()
        : 'rgba(15, 23, 42, 0.15)';

    const options = {
        series: [score],
        chart: {
            type: 'radialBar',
            height: 140,
            sparkline: {
                enabled: true
            }
        },
        plotOptions: {
            radialBar: {
                startAngle: -90,
                endAngle: 90,
                hollow: {
                    size: '60%',
                    background: 'transparent'
                },
                track: {
                    background: trackBg,
                    strokeWidth: '100%'
                },
                dataLabels: {
                    show: false
                }
            }
        },
        colors: [color],
        stroke: {
            lineCap: 'round'
        }
    };

    const chart = new ApexCharts(container, options);
    chart.render();
}

/**
 * Initialize line chart (price trend)
 */
function initializeLineChart(symbol, data) {
    const containerId = `line-${symbol.toLowerCase()}`;
    const container = document.getElementById(containerId);

    if (!container) {
        console.warn(`Line chart container not found: ${containerId}`);
        return;
    }

    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDarkMode ? '#e5e7eb' : '#1f2937';
    const gridColor = isDarkMode ? 'rgba(148, 163, 184, 0.2)' : 'rgba(15, 23, 42, 0.15)';

    const series = [{
        name: 'Price (USD)',
        data: data.map(d => ({
            x: new Date(d.date).getTime(),
            y: parseFloat(d.price)
        }))
    }];

    const options = {
        series: series,
        chart: {
            type: 'area',
            height: 180,
            toolbar: {
                show: false
            },
            zoom: {
                enabled: false
            },
            animations: {
                enabled: true,
                easing: 'easeinout',
                speed: 800
            }
        },
        dataLabels: {
            enabled: false
        },
        stroke: {
            curve: 'smooth',
            width: 2,
            colors: ['#38bdf8']
        },
        fill: {
            type: 'gradient',
            gradient: {
                shadeIntensity: 1,
                opacityFrom: 0.5,
                opacityTo: 0.1,
                stops: [0, 90, 100]
            },
            colors: ['#38bdf8']
        },
        xaxis: {
            type: 'datetime',
            labels: {
                style: {
                    colors: textColor,
                    fontSize: '10px'
                },
                datetimeFormatter: {
                    year: 'yyyy',
                    month: 'MMM',
                    day: 'dd MMM'
                }
            },
            axisBorder: {
                show: false
            },
            axisTicks: {
                show: false
            }
        },
        yaxis: {
            labels: {
                style: {
                    colors: textColor,
                    fontSize: '10px'
                },
                formatter: function (value) {
                    return '$' + value.toFixed(2);
                }
            }
        },
        grid: {
            borderColor: gridColor,
            strokeDashArray: 4,
            xaxis: {
                lines: {
                    show: false
                }
            }
        },
        tooltip: {
            theme: isDarkMode ? 'dark' : 'light',
            x: {
                format: 'dd MMM yyyy'
            },
            y: {
                formatter: function (value) {
                    return '$' + value.toFixed(2);
                }
            }
        }
    };

    const chart = new ApexCharts(container, options);
    chart.render();
}

/**
 * Initialize bar chart (weekly volume)
 */
function initializeBarChart(symbol, data) {
    const containerId = `bar-${symbol.toLowerCase()}`;
    const container = document.getElementById(containerId);

    if (!container) {
        console.warn(`Bar chart container not found: ${containerId}`);
        return;
    }

    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDarkMode ? '#e5e7eb' : '#1f2937';
    const gridColor = isDarkMode ? 'rgba(148, 163, 184, 0.2)' : 'rgba(15, 23, 42, 0.15)';

    const series = [{
        name: 'Volume (USD)',
        data: data.map(d => parseFloat(d.value))
    }];

    const categories = data.map(d => d.label);

    const options = {
        series: series,
        chart: {
            type: 'bar',
            height: 200,
            toolbar: {
                show: false
            },
            animations: {
                enabled: true,
                easing: 'easeinout',
                speed: 800
            }
        },
        plotOptions: {
            bar: {
                horizontal: false,
                columnWidth: '85%',
                borderRadius: 4,
                dataLabels: {
                    position: 'top'
                }
            }
        },
        dataLabels: {
            enabled: false
        },
        stroke: {
            show: true,
            width: 2,
            colors: ['transparent']
        },
        xaxis: {
            categories: categories,
            labels: {
                style: {
                    colors: textColor,
                    fontSize: '10px'
                },
                rotate: -35,
                rotateAlways: true,
                hideOverlappingLabels: false
            },
            axisBorder: {
                show: false
            },
            axisTicks: {
                show: false
            }
        },
        yaxis: {
            labels: {
                style: {
                    colors: textColor,
                    fontSize: '10px'
                },
                formatter: function (value) {
                    return '$' + (value / 1000000).toFixed(1) + 'M';
                }
            }
        },
        fill: {
            type: 'gradient',
            gradient: {
                shade: 'light',
                type: 'vertical',
                shadeIntensity: 0.5,
                gradientToColors: ['#6366f1'],
                inverseColors: false,
                opacityFrom: 0.85,
                opacityTo: 0.65,
                stops: [0, 100]
            },
            colors: ['#38bdf8']
        },
        grid: {
            borderColor: gridColor,
            strokeDashArray: 4,
            yaxis: {
                lines: {
                    show: true
                }
            },
            xaxis: {
                lines: {
                    show: false
                }
            }
        },
        tooltip: {
            theme: isDarkMode ? 'dark' : 'light',
            y: {
                formatter: function (value) {
                    return '$' + (value / 1000000).toFixed(2) + 'M';
                }
            }
        }
    };

    const chart = new ApexCharts(container, options);
    chart.render();
}

/**
 * Initialize tooltips for info icons
 */
function initializeTooltips() {
    // Check if Tippy.js is loaded
    if (typeof tippy !== 'undefined') {
        tippy('.kpi-info-icon', {
            theme: 'custom',
            placement: 'top',
            arrow: true,
            animation: 'scale',
            duration: [200, 150],
            maxWidth: 300
        });
    } else {
        console.warn('Tippy.js not loaded, tooltips will not be initialized');
    }
}
