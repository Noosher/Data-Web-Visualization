using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace DataWebApp.data;

[Table("crypto_asset_price_hourly")]
[Index("AssetId", "ObservedAt", Name = "idx_crypto_asset_price_hourly_asset_time", IsDescending = new[] { false, true })]
[Index("AssetId", "ObservedAt", "CurrencyCode", Name = "uq_crypto_asset_price_hourly_asset_time_curr", IsUnique = true)]
public partial class CryptoAssetPriceHourly
{
    [Key]
    [Column("id")]
    public long Id { get; set; }

    [Column("asset_id")]
    public Guid AssetId { get; set; }

    [Column("observed_at")]
    public DateTime ObservedAt { get; set; }

    [Column("currency_code")]
    [StringLength(3)]
    public string CurrencyCode { get; set; } = null!;

    [Column("price")]
    [Precision(18, 8)]
    public decimal Price { get; set; }

    [Column("market_cap_usd")]
    [Precision(20, 4)]
    public decimal? MarketCapUsd { get; set; }

    [Column("volume_24h_usd")]
    [Precision(20, 4)]
    public decimal? Volume24hUsd { get; set; }

    [ForeignKey("AssetId")]
    [InverseProperty("CryptoAssetPriceHourlies")]
    public virtual CryptoAsset Asset { get; set; } = null!;
}
