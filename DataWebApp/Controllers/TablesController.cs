using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using DataWebApp.data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace DataWebApp.Controllers
{
    public class TablesController : Controller
    {
        private readonly AppDbContext _db;

        public TablesController(AppDbContext db)
        {
            _db = db;
        }

        // ============================
        // View Models (custom pages)
        // ============================

        public class CryptoGroupRowViewModel
        {
            public Guid Id { get; set; }
            public string Tag { get; set; } = string.Empty;
            public string Type { get; set; } = string.Empty;
            public string? Description { get; set; }
            public int CurrentMemberCount { get; set; }
        }

        public class CryptoGroupsPageViewModel
        {
            public int TotalGroups { get; set; }
            public int DistinctTypes { get; set; }
            public int TotalMemberships { get; set; }
            public List<CryptoGroupRowViewModel> Groups { get; set; } = new();
        }

        public class CryptoAssetGroupMembershipRowViewModel
        {
            public string Symbol { get; set; } = string.Empty;
            public string Name { get; set; } = string.Empty;
            public string Tag { get; set; } = string.Empty;
            public string Type { get; set; } = string.Empty;

            public List<string> OtherGroupTags { get; set; } = new();
        }

        public class CryptoAssetGroupsPageViewModel
        {
            public int TotalMemberships { get; set; }
            public int DistinctAssets { get; set; }
            public int DistinctGroups { get; set; }
            public double AvgGroupsPerAsset { get; set; }

            // NEW:
            public int AssetsWith2Groups { get; set; }
            public int AssetsWith3PlusGroups { get; set; }

            public List<CryptoAssetGroupMembershipRowViewModel> Memberships { get; set; } = new();
        }


        // ============================
        // Actions
        // ============================

        public async Task<IActionResult> CryptoAssets()
        {
            var assets = await _db.CryptoAssets
                .OrderBy(a => a.Symbol)
                .ToListAsync();

            return View(assets);
        }

        public async Task<IActionResult> CryptoGroups()
        {
            var groupRows = await _db.CryptoGroups
                .Select(g => new CryptoGroupRowViewModel
                {
                    Id = g.Id,
                    Tag = g.Tag,
                    Type = g.Type,
                    Description = g.Description,
                    CurrentMemberCount = g.Assets.Count()
                })
                .OrderBy(g => g.Tag)
                .ToListAsync();

            var vm = new CryptoGroupsPageViewModel
            {
                TotalGroups = groupRows.Count,
                DistinctTypes = groupRows
                    .Select(g => g.Type)
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .Count(),
                TotalMemberships = groupRows.Sum(g => g.CurrentMemberCount),
                Groups = groupRows
            };

            return View(vm);
        }
        // /Tables/CryptoAssetGroups
        public async Task<IActionResult> CryptoAssetGroups()
        {
            // Use many-to-many via CryptoAsset.Groups navigation
            var membershipRows = await _db.CryptoAssets
                .SelectMany(
                    asset => asset.Groups,
                    (asset, group) => new CryptoAssetGroupMembershipRowViewModel
                    {
                        Symbol = asset.Symbol,
                        Name = asset.Name,
                        Tag = group.Tag,
                        Type = group.Type
                    })
                .OrderBy(m => m.Symbol)
                .ThenBy(m => m.Tag)
                .ToListAsync();

            // ============================
            // Build per-asset group lists
            // ============================
            var tagsBySymbol = membershipRows
                .GroupBy(m => m.Symbol, StringComparer.OrdinalIgnoreCase)
                .ToDictionary(
                    g => g.Key,
                    g => g.Select(x => x.Tag)
                          .Distinct(StringComparer.OrdinalIgnoreCase)
                          .ToList(),
                    StringComparer.OrdinalIgnoreCase);

            // Use those tag lists to populate OtherGroupTags per row (Σ Overlap)
            foreach (var row in membershipRows)
            {
                if (tagsBySymbol.TryGetValue(row.Symbol, out var allTags))
                {
                    row.OtherGroupTags = allTags
                        .Where(tag => !string.Equals(tag, row.Tag, StringComparison.OrdinalIgnoreCase))
                        .Distinct(StringComparer.OrdinalIgnoreCase)
                        .ToList();
                }
                else
                {
                    row.OtherGroupTags = new List<string>();
                }
            }

            // ============================
            // Per-asset group counts
            // ============================
            var perAssetGroupCounts = tagsBySymbol
                .Select(kvp => new
                {
                    Symbol = kvp.Key,
                    GroupCount = kvp.Value.Count   // already distinct above
                })
                .ToList();

            var totalMemberships = membershipRows.Count;
            var distinctAssets = perAssetGroupCounts.Count;
            var distinctGroups = membershipRows
                .Select(m => m.Tag)
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .Count();

            var avgGroupsPerAsset = distinctAssets == 0
                ? 0
                : Math.Round(perAssetGroupCounts.Average(x => x.GroupCount), 2);

            var assetsWith2Groups = perAssetGroupCounts.Count(x => x.GroupCount == 2);
            var assetsWith3PlusGroups = perAssetGroupCounts.Count(x => x.GroupCount >= 3);

            var vm = new CryptoAssetGroupsPageViewModel
            {
                TotalMemberships = totalMemberships,
                DistinctAssets = distinctAssets,
                DistinctGroups = distinctGroups,
                AvgGroupsPerAsset = avgGroupsPerAsset,
                AssetsWith2Groups = assetsWith2Groups,
                AssetsWith3PlusGroups = assetsWith3PlusGroups,
                Memberships = membershipRows
            };

            // View: Views/Tables/CryptoAssetGroups.cshtml
            return View(vm);
        }

        public async Task<IActionResult> CryptoAssetPriceDaily()
        {
            var rows = await _db.CryptoAssetPriceDailies
                .Include(p => p.Asset)
                .OrderByDescending(p => p.Id)
                .Take(500)
                .ToListAsync();

            return View(rows);
        }

        public async Task<IActionResult> CryptoAssetPriceHourly()
        {
            var rows = await _db.CryptoAssetPriceHourlies
                .Include(p => p.Asset)
                .OrderByDescending(p => p.Id)
                .Take(500)
                .ToListAsync();

            return View(rows);
        }
        

        public async Task<IActionResult> CryptoAssetGroupHistory()
        {
            var rows = await _db.CryptoAssetGroupHistories
                .Include(h => h.Asset)
                .Include(h => h.Group)
                .OrderByDescending(h => h.EventTimestamp)
                .Take(500)
                .ToListAsync();

            return View(rows);
        }

        // /Tables/JobRunLogs
        public async Task<IActionResult> JobRunLogs()
        {
            var rows = await _db.JobRunLogs
                .OrderByDescending(j => j.JobName)
                .ToListAsync();

            return View(rows);
        }
    }
}
