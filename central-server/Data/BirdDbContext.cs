using BirdLab.Api.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;

namespace BirdLab.Api.Data;

public sealed class BirdDbContext(DbContextOptions<BirdDbContext> options) : IdentityDbContext<ApplicationUser>(options)
{
    public DbSet<Bird> Birds => Set<Bird>();
    public DbSet<Analysis> Analyses => Set<Analysis>();
    public DbSet<Prediction> Predictions => Set<Prediction>();
    public DbSet<Evaluation> Evaluations => Set<Evaluation>();
    public DbSet<OutboxMessage> OutboxMessages => Set<OutboxMessage>();
    public DbSet<InboxMessage> InboxMessages => Set<InboxMessage>();
    public DbSet<AuthSession> AuthSessions => Set<AuthSession>();
    public DbSet<SubscriptionPlan> SubscriptionPlans => Set<SubscriptionPlan>();
    public DbSet<UserSubscription> UserSubscriptions => Set<UserSubscription>();
    public DbSet<PaymentOrder> PaymentOrders => Set<PaymentOrder>();
    public DbSet<CryptoPayment> CryptoPayments => Set<CryptoPayment>();
    public DbSet<UserWallet> UserWallets => Set<UserWallet>();
    public DbSet<WalletNonce> WalletNonces => Set<WalletNonce>();
    public DbSet<UsageRecord> UsageRecords => Set<UsageRecord>();

    protected override void OnModelCreating(ModelBuilder model)
    {
        base.OnModelCreating(model);
        SubscriptionSchema.Configure(model);
        var bird = model.Entity<Bird>();
        bird.HasIndex(b => b.ScientificName).IsUnique();
        bird.Property(b => b.ScientificName).HasMaxLength(256);
        bird.Property(b => b.CommonName).HasMaxLength(256);
        bird.Property(b => b.UkrainianName).HasMaxLength(256);
        var analysis = model.Entity<Analysis>();
        analysis.HasOne<ApplicationUser>().WithMany().HasForeignKey(a => a.UserId).OnDelete(DeleteBehavior.Restrict);
        analysis.HasIndex(a => new { a.UserId, a.AnalysisDate });
        analysis.Property(a => a.AnalysisType).HasMaxLength(10);
        analysis.Property(a => a.OriginalFileName).HasMaxLength(255);
        analysis.Property(a => a.StoredFilePath).HasMaxLength(100);
        analysis.Property(a => a.LegacySource).HasMaxLength(64);
        analysis.Property(a => a.Status).HasMaxLength(16);
        analysis.Property(a => a.ErrorMessage).HasMaxLength(2000);
        analysis.HasIndex(a => a.JobId).IsUnique();
        analysis.HasIndex(a => new { a.Status, a.UpdatedAt });
        analysis.ToTable(t => t.HasCheckConstraint("CK_Analysis_Status", "[Status] IN ('Pending','Queued','Processing','Completed','Failed')"));
        analysis.HasIndex(a => a.StoredFilePath).IsUnique();
        analysis.HasIndex(a => a.AnalysisDate);
        analysis.HasIndex(a => new { a.LegacySource, a.LegacyId }).IsUnique().HasFilter("[LegacySource] IS NOT NULL AND [LegacyId] IS NOT NULL");
        analysis.HasOne(a => a.Bird).WithMany().HasForeignKey(a => a.BirdId).OnDelete(DeleteBehavior.Restrict);
        analysis.ToTable(t => { t.HasCheckConstraint("CK_Analysis_Type", "[AnalysisType] IN ('image','audio')"); t.HasCheckConstraint("CK_Analysis_Confidence", "[Confidence] >= 0 AND [Confidence] <= 1"); });
        var prediction = model.Entity<Prediction>();
        prediction.Property(p => p.SpeciesName).HasMaxLength(256);
        prediction.Property(p => p.ScientificName).HasMaxLength(256);
        prediction.HasIndex(p => new { p.AnalysisId, p.Rank }).IsUnique();
        prediction.HasOne(p => p.Analysis).WithMany(a => a.Predictions).HasForeignKey(p => p.AnalysisId).OnDelete(DeleteBehavior.Cascade);
        prediction.ToTable(t => { t.HasCheckConstraint("CK_Prediction_Rank", "[Rank] BETWEEN 1 AND 3"); t.HasCheckConstraint("CK_Prediction_Confidence", "[Confidence] >= 0 AND [Confidence] <= 1"); });
        model.Entity<Evaluation>().HasKey(e => e.AnalysisId);
        model.Entity<Evaluation>().HasOne(e => e.Analysis).WithOne(a => a.Evaluation).HasForeignKey<Evaluation>(e => e.AnalysisId).OnDelete(DeleteBehavior.Cascade);
        var outbox = model.Entity<OutboxMessage>();
        outbox.Property(e => e.LastError).HasMaxLength(2000);
        outbox.HasIndex(e => new { e.PublishedAt, e.NextAttemptAt });
        outbox.HasIndex(e => e.AnalysisId).IsUnique();
        model.Entity<InboxMessage>().Property(e => e.BodyHash).HasMaxLength(64);
        model.Entity<InboxMessage>().HasIndex(e => e.AnalysisId);
    }
}
