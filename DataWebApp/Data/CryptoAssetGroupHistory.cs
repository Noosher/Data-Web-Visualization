using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace DataWebApp.data;

[Table("crypto_asset_group_history")]
[Index("AssetId", "GroupId", Name = "idx_crypto_asset_group_history_asset_group")]
[Index("AssetId", Name = "idx_crypto_asset_group_history_asset_id")]
[Index("EventTimestamp", Name = "idx_crypto_asset_group_history_event_timestamp")]
[Index("GroupId", Name = "idx_crypto_asset_group_history_group_id")]
public partial class CryptoAssetGroupHistory
{
    [Key]
    [Column("id")]
    public long Id { get; set; }

    [Column("asset_id")]
    public Guid AssetId { get; set; }

    [Column("group_id")]
    public Guid GroupId { get; set; }

    [Column("event_type")]
    [StringLength(10)]
    public string EventType { get; set; } = null!;

    [Column("event_timestamp")]
    public DateTime EventTimestamp { get; set; }

    [Column("market_cap_usd")]
    [Precision(20, 4)]
    public decimal? MarketCapUsd { get; set; }

    [Column("rank_in_group")]
    public int? RankInGroup { get; set; }

    [Column("metadata", TypeName = "jsonb")]
    public string? Metadata { get; set; }

    [ForeignKey("AssetId")]
    [InverseProperty("CryptoAssetGroupHistories")]
    public virtual CryptoAsset Asset { get; set; } = null!;

    [ForeignKey("GroupId")]
    [InverseProperty("CryptoAssetGroupHistories")]
    public virtual CryptoGroup Group { get; set; } = null!;
}
