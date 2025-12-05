using System;
using System.Collections.Generic;

namespace DataWebApp.Models
{
    public class AssetKpiCardViewModel
    {
        public Guid AssetId { get; set; }
        public string Symbol { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public bool HasData { get; set; } = false;

        // Current metrics
        public decimal CurrentPrice { get; set; }
        public decimal MarketCap { get; set; }
        public decimal Volume24h { get; set; }

        // Performance score (0-100)
        public decimal PerformanceScore { get; set; }
        public string PerformanceScoreExplanation { get; set; } = string.Empty;

        // Price changes
        public decimal? PriceChange7d { get; set; }
        public decimal? PriceChange30d { get; set; }

        // Chart data
        public List<PriceDataPoint> ChartData { get; set; } = new();
        public List<BarChartDataPoint> BarChartData { get; set; } = new();

        // Linear regression prediction
        public int ForecastDays { get; set; }
        public decimal PredictedPrice { get; set; }
        public decimal PredictionConfidence { get; set; } // R² as percentage
        public string PredictionExplanation { get; set; } = string.Empty;

        // Metadata
        public DateTime LatestObservation { get; set; }
    }

    public class PriceDataPoint
    {
        public DateTime Date { get; set; }
        public decimal Price { get; set; }
        public decimal MarketCap { get; set; }
        public decimal Volume { get; set; }
    }

    public class BarChartDataPoint
    {
        public string Label { get; set; } = string.Empty;
        public decimal Value { get; set; }
    }
}
