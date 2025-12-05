using DataWebApp.data;
using DataWebApp.Models;
using Microsoft.EntityFrameworkCore;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace DataWebApp.Services
{
    public class AnalyticsService
    {
        private readonly AppDbContext _db;

        public AnalyticsService(AppDbContext db)
        {
            _db = db;
        }

        /// <summary>
        /// Get KPI data for all active crypto assets
        /// </summary>
        public async Task<List<AssetKpiCardViewModel>> GetAssetKpiDataAsync(int defaultDaysToShow = 90)
        {
            var activeAssets = await _db.CryptoAssets
                .Where(a => a.IsActive)
                .OrderBy(a => a.Symbol)
                .ToListAsync();

            var kpiCards = new List<AssetKpiCardViewModel>();

            foreach (var asset in activeAssets)
            {
                var kpiData = await CalculateAssetKpiAsync(asset.Id, defaultDaysToShow);
                kpiCards.Add(kpiData);
            }

            return kpiCards;
        }

        /// <summary>
        /// Calculate KPI data for a single asset
        /// </summary>
        public async Task<AssetKpiCardViewModel> CalculateAssetKpiAsync(Guid assetId, int daysToShow = 90)
        {
            var asset = await _db.CryptoAssets.FindAsync(assetId);
            if (asset == null)
            {
                throw new ArgumentException($"Asset with ID {assetId} not found");
            }

            // Get all daily price data for this asset
            var allPrices = await _db.CryptoAssetPriceDailies
                .Where(p => p.AssetId == assetId)
                .OrderBy(p => p.ObservedAt)
                .ToListAsync();

            if (!allPrices.Any())
            {
                return new AssetKpiCardViewModel
                {
                    AssetId = assetId,
                    Symbol = asset.Symbol,
                    Name = asset.Name,
                    HasData = false
                };
            }

            // Get prices for chart display (last N days)
            var chartPrices = allPrices
                .OrderByDescending(p => p.ObservedAt)
                .Take(daysToShow)
                .OrderBy(p => p.ObservedAt)
                .ToList();

            // Calculate performance score
            var performanceScore = CalculatePerformanceScore(allPrices);

            // Calculate linear regression prediction
            var (forecastDays, predictedPrice, confidence, predictionExplanation) = CalculateLinearRegressionPrediction(allPrices);

            // Get current price (most recent)
            var currentPrice = allPrices.Last().Price;
            var currentMarketCap = allPrices.Last().MarketCapUsd ?? 0;
            var current24hVolume = allPrices.Last().Volume24hUsd ?? 0;

            // Calculate price changes
            var priceChange7d = CalculatePriceChange(allPrices, 7);
            var priceChange30d = CalculatePriceChange(allPrices, 30);

            return new AssetKpiCardViewModel
            {
                AssetId = assetId,
                Symbol = asset.Symbol,
                Name = asset.Name,
                HasData = true,
                CurrentPrice = currentPrice,
                MarketCap = currentMarketCap,
                Volume24h = current24hVolume,
                PerformanceScore = performanceScore,
                PerformanceScoreExplanation = GetPerformanceScoreExplanation(allPrices),
                PriceChange7d = priceChange7d,
                PriceChange30d = priceChange30d,
                ChartData = chartPrices.Select(p => new PriceDataPoint
                {
                    Date = p.ObservedAt,
                    Price = p.Price,
                    MarketCap = p.MarketCapUsd ?? 0,
                    Volume = p.Volume24hUsd ?? 0
                }).ToList(),
                BarChartData = CalculateBarChartData(chartPrices),
                ForecastDays = forecastDays,
                PredictedPrice = predictedPrice,
                PredictionConfidence = confidence,
                PredictionExplanation = predictionExplanation,
                LatestObservation = allPrices.Last().ObservedAt
            };
        }

        /// <summary>
        /// Calculate performance score (0-100) considering both recent trend AND overall position
        /// Less forgiving algorithm that looks at absolute position relative to historical data
        /// </summary>
        private decimal CalculatePerformanceScore(List<CryptoAssetPriceDaily> prices)
        {
            if (prices.Count < 31)
            {
                return 50; // Neutral score for insufficient data
            }

            var orderedPrices = prices.OrderBy(p => p.ObservedAt).ToList();
            var currentPrice = orderedPrices.Last().Price;

            // Get last 30 days
            var last30Days = orderedPrices.TakeLast(30).ToList();

            // Get historical data (everything before last 30 days)
            var historicalData = orderedPrices.Take(orderedPrices.Count - 30).ToList();

            if (!historicalData.Any())
            {
                return 50; // Not enough historical data
            }

            // COMPONENT 1: Recent trend (30-day average vs historical average) - 30% weight
            var recent30DayAvg = last30Days.Average(p => p.Price);
            var historicalAvg = historicalData.Average(p => p.Price);
            var trendPercent = ((recent30DayAvg - historicalAvg) / historicalAvg) * 100;

            // COMPONENT 2: Current position relative to historical range - 70% weight
            var historicalMax = historicalData.Max(p => p.Price);
            var historicalMin = historicalData.Min(p => p.Price);
            var historicalRange = historicalMax - historicalMin;

            // Where are we in the historical range? (0 = at min, 1 = at max)
            var positionInRange = historicalRange > 0
                ? (double)((currentPrice - historicalMin) / historicalRange)
                : 0.5;

            // Convert position to score (0-100)
            var positionScore = (decimal)(positionInRange * 100);

            // COMPONENT 3: Momentum - is current price better than 30-day average? - bonus/penalty
            var momentumPercent = ((currentPrice - recent30DayAvg) / recent30DayAvg) * 100;
            var momentumAdjustment = momentumPercent * 0.1m; // Small adjustment

            // Weighted combination:
            // 70% based on where we are in historical range (prevents overly optimistic scores when still low)
            // 30% based on recent trend (rewards improvement but doesn't dominate)
            // Plus small momentum bonus/penalty
            var trendScore = Math.Max(0, Math.Min(100, 50 + trendPercent)); // Clamp trend to 0-100
            var finalScore = (positionScore * 0.7m) + (trendScore * 0.3m) + momentumAdjustment;

            // Clamp final score to 0-100
            return Math.Max(0, Math.Min(100, finalScore));
        }

        /// <summary>
        /// Generate human-readable explanation of performance score calculation
        /// </summary>
        private string GetPerformanceScoreExplanation(List<CryptoAssetPriceDaily> prices)
        {
            if (prices.Count < 31)
            {
                return "Need 31+ days of data for score calculation";
            }

            var orderedPrices = prices.OrderBy(p => p.ObservedAt).ToList();
            var currentPrice = orderedPrices.Last().Price;
            var last30Days = orderedPrices.TakeLast(30).ToList();
            var historicalData = orderedPrices.Take(orderedPrices.Count - 30).ToList();

            if (!historicalData.Any())
            {
                return "Need more historical data";
            }

            var recent30DayAvg = last30Days.Average(p => p.Price);
            var historicalMax = historicalData.Max(p => p.Price);
            var historicalMin = historicalData.Min(p => p.Price);
            var positionPercent = ((currentPrice - historicalMin) / (historicalMax - historicalMin)) * 100;

            // Build brief tooltip explanation
            var explanation = $"Current: ${currentPrice:N2} | Range: ${historicalMin:N2} - ${historicalMax:N2} | " +
                             $"Position: {positionPercent:N0}% of range | 30d avg: ${recent30DayAvg:N2}";

            return explanation;
        }

        /// <summary>
        /// Calculate price change percentage over N days
        /// </summary>
        private decimal? CalculatePriceChange(List<CryptoAssetPriceDaily> prices, int days)
        {
            if (prices.Count < days + 1)
            {
                return null;
            }

            var orderedPrices = prices.OrderByDescending(p => p.ObservedAt).ToList();
            var currentPrice = orderedPrices[0].Price;
            var pastPrice = orderedPrices[Math.Min(days, orderedPrices.Count - 1)].Price;

            if (pastPrice == 0) return null;

            return ((currentPrice - pastPrice) / pastPrice) * 100;
        }

        /// <summary>
        /// Calculate linear regression prediction
        /// Returns: (forecastDays, predictedPrice, confidence, explanation)
        /// </summary>
        private (int forecastDays, decimal predictedPrice, decimal confidence, string explanation) CalculateLinearRegressionPrediction(
            List<CryptoAssetPriceDaily> prices)
        {
            if (prices.Count < 14)
            {
                return (0, 0, 0, "Insufficient data: Linear regression requires at least 14 days of price history for meaningful predictions."); // Not enough data
            }

            // Use the most recent data for prediction
            var dataPoints = prices
                .OrderByDescending(p => p.ObservedAt)
                .Take(Math.Min(90, prices.Count))
                .OrderBy(p => p.ObservedAt)
                .ToList();

            int n = dataPoints.Count;

            // Convert dates to numeric values (days from first observation)
            var firstDate = dataPoints[0].ObservedAt;
            var xValues = dataPoints.Select(p => (double)(p.ObservedAt - firstDate).TotalDays).ToArray();
            var yValues = dataPoints.Select(p => (double)p.Price).ToArray();

            // Calculate linear regression: y = mx + b
            double sumX = xValues.Sum();
            double sumY = yValues.Sum();
            double sumXY = xValues.Zip(yValues, (x, y) => x * y).Sum();
            double sumX2 = xValues.Sum(x => x * x);

            double slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
            double intercept = (sumY - slope * sumX) / n;

            // Calculate R² (coefficient of determination) for confidence
            double yMean = sumY / n;
            double ssTotal = yValues.Sum(y => Math.Pow(y - yMean, 2));
            double ssResidual = xValues.Zip(yValues, (x, y) =>
                Math.Pow(y - (slope * x + intercept), 2)).Sum();
            double rSquared = 1 - (ssResidual / ssTotal);

            // Dynamic forecast based on data quality and confidence
            int forecastDays = CalculateForecastDays(n, rSquared);

            // Predict price N days ahead
            double lastXValue = xValues.Last();
            double futureXValue = lastXValue + forecastDays;
            double predictedPriceValue = slope * futureXValue + intercept;

            // Build brief tooltip explanation
            var confidenceLevel = rSquared >= 0.7 ? "HIGH" : rSquared >= 0.4 ? "MEDIUM" : "LOW";
            var explanation = $"Model: y = {slope:N2}x + {intercept:N2} | " +
                             $"Training: {n} days | R² = {rSquared * 100:N1}% ({confidenceLevel}) | " +
                             $"Forecast: {forecastDays} days ahead";

            return (
                forecastDays,
                (decimal)Math.Max(0, predictedPriceValue), // Ensure non-negative
                (decimal)(rSquared * 100), // Convert to percentage
                explanation
            );
        }

        /// <summary>
        /// Calculate appropriate forecast days based on data availability and confidence
        /// </summary>
        private int CalculateForecastDays(int dataPoints, double rSquared)
        {
            // Base forecast on data quantity
            int baseForecast;
            if (dataPoints >= 90) baseForecast = 30;
            else if (dataPoints >= 60) baseForecast = 14;
            else if (dataPoints >= 30) baseForecast = 7;
            else baseForecast = 3;

            // Adjust based on confidence (R²)
            if (rSquared < 0.3) return Math.Max(3, baseForecast / 3); // Low confidence = shorter forecast
            if (rSquared < 0.6) return baseForecast / 2; // Medium confidence
            return baseForecast; // High confidence
        }

        /// <summary>
        /// Calculate bar chart data (period volume aggregates with date ranges)
        /// </summary>
        private List<BarChartDataPoint> CalculateBarChartData(List<CryptoAssetPriceDaily> prices)
        {
            if (!prices.Any()) return new List<BarChartDataPoint>();

            // Sort prices by date
            var sortedPrices = prices.OrderBy(p => p.ObservedAt).ToList();

            // Determine period size based on data range
            int totalDays = (sortedPrices.Last().ObservedAt - sortedPrices.First().ObservedAt).Days + 1;
            int periodDays = totalDays switch
            {
                <= 30 => 5,    // 5-day periods for short ranges
                <= 60 => 7,    // Weekly for medium ranges
                <= 180 => 14,  // Bi-weekly for longer ranges
                _ => 30        // Monthly for very long ranges
            };

            var periodData = new List<BarChartDataPoint>();
            var currentGroup = new List<CryptoAssetPriceDaily>();
            DateTime? periodStart = null;

            foreach (var price in sortedPrices)
            {
                if (periodStart == null)
                {
                    periodStart = price.ObservedAt;
                    currentGroup.Add(price);
                }
                else if ((price.ObservedAt - periodStart.Value).Days < periodDays)
                {
                    currentGroup.Add(price);
                }
                else
                {
                    // Finalize current period
                    if (currentGroup.Any())
                    {
                        var periodEnd = currentGroup.Last().ObservedAt;
                        periodData.Add(new BarChartDataPoint
                        {
                            Label = $"{periodStart.Value:MMM dd} - {periodEnd:MMM dd}",
                            Value = currentGroup.Sum(p => p.Volume24hUsd ?? 0)
                        });
                    }

                    // Start new period
                    periodStart = price.ObservedAt;
                    currentGroup = new List<CryptoAssetPriceDaily> { price };
                }
            }

            // Add final period
            if (currentGroup.Any() && periodStart.HasValue)
            {
                var periodEnd = currentGroup.Last().ObservedAt;
                periodData.Add(new BarChartDataPoint
                {
                    Label = $"{periodStart.Value:MMM dd} - {periodEnd:MMM dd}",
                    Value = currentGroup.Sum(p => p.Volume24hUsd ?? 0)
                });
            }

            return periodData;
        }

        /// <summary>
        /// Get filtered price data for a specific date range
        /// </summary>
        public async Task<List<AssetKpiCardViewModel>> GetFilteredKpiDataAsync(
            DateTime? startDate = null,
            DateTime? endDate = null,
            int? days = null)
        {
            int daysToShow = days ?? 90;

            // If custom date range is provided, calculate days
            if (startDate.HasValue && endDate.HasValue)
            {
                daysToShow = (int)(endDate.Value - startDate.Value).TotalDays;
            }

            return await GetAssetKpiDataAsync(daysToShow);
        }
    }
}
