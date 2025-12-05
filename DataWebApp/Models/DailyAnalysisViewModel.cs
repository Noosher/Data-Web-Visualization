using System;
using System.Collections.Generic;

namespace DataWebApp.Models
{
    public class DailyAnalysisViewModel
    {
        public List<AssetKpiCardViewModel> AssetKpis { get; set; } = new();
        public int DefaultDaysToShow { get; set; } = 90;
        public DateTime? CustomStartDate { get; set; }
        public DateTime? CustomEndDate { get; set; }
        public int TotalActiveAssets { get; set; }
        public int CardsPerRow { get; set; } = 3; // Default: 3 per row

        // Sorting
        public string SortBy { get; set; } = "Symbol"; // Symbol, Price, MarketCap, Score
        public string SortOrder { get; set; } = "Asc"; // Asc or Desc

        // Filtering
        public List<string> SelectedGroups { get; set; } = new();
        public List<GroupOption> AvailableGroups { get; set; } = new();
    }

    public class GroupOption
    {
        public string Tag { get; set; } = string.Empty;
        public string DisplayName { get; set; } = string.Empty;
        public bool IsSelected { get; set; }
    }
}
