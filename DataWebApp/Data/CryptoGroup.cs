using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace DataWebApp.data;

[Table("crypto_group")]
[Index("Tag", Name = "crypto_group_tag_key", IsUnique = true)]
public partial class CryptoGroup
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; }

    [Column("tag")]
    public string Tag { get; set; } = null!;

    [Column("type")]
    public string Type { get; set; } = null!;

    [Column("description")]
    public string? Description { get; set; }

    [InverseProperty("Group")]
    public virtual ICollection<CryptoAssetGroupHistory> CryptoAssetGroupHistories { get; set; } = new List<CryptoAssetGroupHistory>();

    [ForeignKey("GroupId")]
    [InverseProperty("Groups")]
    public virtual ICollection<CryptoAsset> Assets { get; set; } = new List<CryptoAsset>();
}
