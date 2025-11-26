using System;
using System.Collections.Generic;
using Microsoft.EntityFrameworkCore;

namespace DataWebApp.data;

public partial class AppDbContext : DbContext
{
    public AppDbContext()
    {
    }

    public AppDbContext(DbContextOptions<AppDbContext> options)
        : base(options)
    {
    }

    public virtual DbSet<CryptoAsset> CryptoAssets { get; set; }

    public virtual DbSet<CryptoAssetGroupHistory> CryptoAssetGroupHistories { get; set; }

    public virtual DbSet<CryptoAssetPriceDaily> CryptoAssetPriceDailies { get; set; }

    public virtual DbSet<CryptoAssetPriceHourly> CryptoAssetPriceHourlies { get; set; }

    public virtual DbSet<CryptoGroup> CryptoGroups { get; set; }

    public virtual DbSet<JobRunLog> JobRunLogs { get; set; }

    protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
    {
        if (!optionsBuilder.IsConfigured) // NEW: only configure here if DI didn't already do it
        {
            optionsBuilder.UseNpgsql("Name=ConnectionStrings:DefaultConnection"); // EXISTING: fallback for design-time
        }
    }


    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasPostgresExtension("uuid-ossp");

        modelBuilder.Entity<CryptoAsset>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("crypto_asset_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
            entity.Property(e => e.IsActive).HasDefaultValue(true);
            entity.Property(e => e.TimeAdded).HasDefaultValueSql("now()");

            entity.HasMany(d => d.Groups).WithMany(p => p.Assets)
                .UsingEntity<Dictionary<string, object>>(
                    "CryptoAssetGroup",
                    r => r.HasOne<CryptoGroup>().WithMany()
                        .HasForeignKey("GroupId")
                        .HasConstraintName("crypto_asset_group_group_id_fkey"),
                    l => l.HasOne<CryptoAsset>().WithMany()
                        .HasForeignKey("AssetId")
                        .HasConstraintName("crypto_asset_group_asset_id_fkey"),
                    j =>
                    {
                        j.HasKey("AssetId", "GroupId").HasName("crypto_asset_group_pkey");
                        j.ToTable("crypto_asset_group");
                        j.HasIndex(new[] { "GroupId" }, "idx_crypto_asset_group_group_id");
                        j.IndexerProperty<Guid>("AssetId").HasColumnName("asset_id");
                        j.IndexerProperty<Guid>("GroupId").HasColumnName("group_id");
                    });
        });

        modelBuilder.Entity<CryptoAssetGroupHistory>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("crypto_asset_group_history_pkey");

            entity.Property(e => e.EventTimestamp).HasDefaultValueSql("now()");

            entity.HasOne(d => d.Asset).WithMany(p => p.CryptoAssetGroupHistories).HasConstraintName("crypto_asset_group_history_asset_id_fkey");

            entity.HasOne(d => d.Group).WithMany(p => p.CryptoAssetGroupHistories).HasConstraintName("crypto_asset_group_history_group_id_fkey");
        });

        modelBuilder.Entity<CryptoAssetPriceDaily>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("crypto_asset_price_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("nextval('crypto_asset_price_id_seq'::regclass)");
            entity.Property(e => e.CurrencyCode)
                .HasDefaultValueSql("'USD'::bpchar")
                .IsFixedLength();

            entity.HasOne(d => d.Asset).WithMany(p => p.CryptoAssetPriceDailies).HasConstraintName("crypto_asset_price_asset_id_fkey");
        });

        modelBuilder.Entity<CryptoAssetPriceHourly>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("crypto_asset_price_hourly_pkey");

            entity.Property(e => e.CurrencyCode)
                .HasDefaultValueSql("'USD'::bpchar")
                .IsFixedLength();

            entity.HasOne(d => d.Asset).WithMany(p => p.CryptoAssetPriceHourlies).HasConstraintName("crypto_asset_price_hourly_asset_id_fkey");
        });

        modelBuilder.Entity<CryptoGroup>(entity =>
        {
            entity.HasKey(e => e.Id).HasName("crypto_group_pkey");

            entity.Property(e => e.Id).HasDefaultValueSql("uuid_generate_v4()");
        });

        modelBuilder.Entity<JobRunLog>(entity =>
        {
            entity.HasKey(e => e.JobName).HasName("job_run_log_pkey");
        });

        OnModelCreatingPartial(modelBuilder);
    }

    partial void OnModelCreatingPartial(ModelBuilder modelBuilder);
}
