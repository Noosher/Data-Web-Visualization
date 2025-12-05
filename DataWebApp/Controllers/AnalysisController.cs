using DataWebApp.data;
using DataWebApp.Models;
using DataWebApp.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System;
using System.Threading.Tasks;

namespace DataWebApp.Controllers
{
    public class AnalysisController : Controller
    {
        private readonly AppDbContext _db;
        private readonly AnalyticsService _analyticsService;

        public AnalysisController(AppDbContext db, AnalyticsService analyticsService)
        {
            _db = db;
            _analyticsService = analyticsService;
        }

        /// <summary>
        /// Daily ASP.NET Analysis - KPI Cards with Charts
        /// </summary>
        public async Task<IActionResult> DailyAspNetAnalysis(
            int days = 90,
            DateTime? startDate = null,
            DateTime? endDate = null,
            string sortBy = "Symbol",
            string sortOrder = "Asc",
            List<string>? groups = null)
        {
            // Get KPI data for all active assets
            var assetKpis = await _analyticsService.GetFilteredKpiDataAsync(startDate, endDate, days);

            // Filter by groups if specified
            if (groups != null && groups.Any())
            {
                var groupTags = groups.ToList();
                var assetsInGroups = await _db.CryptoAssets
                    .Where(a => a.IsActive && a.Groups.Any(g => groupTags.Contains(g.Tag)))
                    .Select(a => a.Id)
                    .ToListAsync();

                assetKpis = assetKpis.Where(kpi => assetsInGroups.Contains(kpi.AssetId)).ToList();
            }

            // Sort the results
            assetKpis = sortBy switch
            {
                "Price" => sortOrder == "Asc"
                    ? assetKpis.OrderBy(k => k.CurrentPrice).ToList()
                    : assetKpis.OrderByDescending(k => k.CurrentPrice).ToList(),
                "MarketCap" => sortOrder == "Asc"
                    ? assetKpis.OrderBy(k => k.MarketCap).ToList()
                    : assetKpis.OrderByDescending(k => k.MarketCap).ToList(),
                "Score" => sortOrder == "Asc"
                    ? assetKpis.OrderBy(k => k.PerformanceScore).ToList()
                    : assetKpis.OrderByDescending(k => k.PerformanceScore).ToList(),
                _ => sortOrder == "Asc"
                    ? assetKpis.OrderBy(k => k.Symbol).ToList()
                    : assetKpis.OrderByDescending(k => k.Symbol).ToList()
            };

            // Get total count of active assets
            var totalActiveAssets = await _db.CryptoAssets.CountAsync(a => a.IsActive);

            // Get available groups for filtering
            var allGroups = await _db.CryptoGroups
                .OrderBy(g => g.Tag)
                .Select(g => new GroupOption
                {
                    Tag = g.Tag,
                    DisplayName = g.Tag,
                    IsSelected = groups != null && groups.Contains(g.Tag)
                })
                .ToListAsync();

            var viewModel = new DailyAnalysisViewModel
            {
                AssetKpis = assetKpis,
                DefaultDaysToShow = days,
                CustomStartDate = startDate,
                CustomEndDate = endDate,
                TotalActiveAssets = totalActiveAssets,
                CardsPerRow = 3,
                SortBy = sortBy,
                SortOrder = sortOrder,
                SelectedGroups = groups ?? new List<string>(),
                AvailableGroups = allGroups
            };

            return View(viewModel);
        }

        /// <summary>
        /// Placeholder for Daily Overview
        /// </summary>
        public IActionResult DailyOverview()
        {
            ViewData["Message"] = "Daily Overview - Coming Soon";
            return View("ComingSoon");
        }

        /// <summary>
        /// Placeholder for Daily Power BI Analysis
        /// </summary>
        public IActionResult DailyPowerBIAnalysis()
        {
            ViewData["Message"] = "Daily Power BI Analysis - Coming Soon";
            return View("ComingSoon");
        }

        /// <summary>
        /// Placeholder for Daily MatPlotLib Analysis
        /// </summary>
        public IActionResult DailyMatPlotLibAnalysis()
        {
            ViewData["Message"] = "Daily MatPlotLib Analysis - Coming Soon";
            return View("ComingSoon");
        }

        /// <summary>
        /// Placeholder for Hourly Overview
        /// </summary>
        public IActionResult HourlyOverview()
        {
            ViewData["Message"] = "Hourly Overview - Coming Soon";
            return View("ComingSoon");
        }

        /// <summary>
        /// Placeholder for Hourly ASP.NET Analysis
        /// </summary>
        public IActionResult HourlyAspNetAnalysis()
        {
            ViewData["Message"] = "Hourly ASP.NET Analysis - Coming Soon";
            return View("ComingSoon");
        }

        /// <summary>
        /// Placeholder for Hourly Power BI Analysis
        /// </summary>
        public IActionResult HourlyPowerBIAnalysis()
        {
            ViewData["Message"] = "Hourly Power BI Analysis - Coming Soon";
            return View("ComingSoon");
        }

        /// <summary>
        /// Placeholder for Hourly MatPlotLib Analysis
        /// </summary>
        public IActionResult HourlyMatPlotLibAnalysis()
        {
            ViewData["Message"] = "Hourly MatPlotLib Analysis - Coming Soon";
            return View("ComingSoon");
        }
    }
}
