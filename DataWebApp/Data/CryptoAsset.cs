using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace DataWebApp.data;

[Table("crypto_asset")]
[Index("CoingeckoId", Name = "crypto_asset_coingecko_id_key", IsUnique = true)]
[Index("Symbol", Name = "idx_crypto_asset_symbol")]
public partial class CryptoAsset
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("coingecko_id")]
    public string CoingeckoId { get; set; } = null!;

    [Column("symbol")]
    [StringLength(20)]
    public string Symbol { get; set; } = null!;

    [Column("name")]
    [StringLength(100)]
    public string Name { get; set; } = null!;

    [Column("is_active")]
    public bool IsActive { get; set; }

    [Column("time_added")]
    public DateTime TimeAdded { get; set; }

    [Column("last_daily_observed_at")]
    public DateTime? LastDailyObservedAt { get; set; }

    [Column("last_hourly_observed_at")]
    public DateTime? LastHourlyObservedAt { get; set; }

    [InverseProperty("Asset")]
    public virtual ICollection<CryptoAssetGroupHistory> CryptoAssetGroupHistories { get; set; } = new List<CryptoAssetGroupHistory>();

    [InverseProperty("Asset")]
    public virtual ICollection<CryptoAssetPriceDaily> CryptoAssetPriceDailies { get; set; } = new List<CryptoAssetPriceDaily>();

    [InverseProperty("Asset")]
    public virtual ICollection<CryptoAssetPriceHourly> CryptoAssetPriceHourlies { get; set; } = new List<CryptoAssetPriceHourly>();

    [ForeignKey("AssetId")]
    [InverseProperty("Assets")]
    public virtual ICollection<CryptoGroup> Groups { get; set; } = new List<CryptoGroup>();
}
