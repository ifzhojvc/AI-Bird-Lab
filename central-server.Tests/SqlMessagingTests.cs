using System.Text.Json;
using BirdLab.Api.Data;
using BirdLab.Api.Messaging;
using BirdLab.Api.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Xunit;

namespace BirdLab.Api.Tests;

public sealed class SqlFactAttribute : FactAttribute
{
    public SqlFactAttribute()
    {
        if (string.IsNullOrEmpty(Environment.GetEnvironmentVariable("BIRDLAB_TEST_SQL"))) Skip = "Потрібен справжній SQL Server: BIRDLAB_TEST_SQL; тест створює окрему тимчасову базу.";
    }
}

public sealed class SqlDatabase : IAsyncDisposable
{
    public BirdDbContext Db { get; }
    private readonly string name = "BirdLabMessagingTest_" + Guid.NewGuid().ToString("N");
    public SqlDatabase()
    {
        var connection = new SqlConnectionStringBuilder(Environment.GetEnvironmentVariable("BIRDLAB_TEST_SQL")) { InitialCatalog = name };
        Db = new BirdDbContext(new DbContextOptionsBuilder<BirdDbContext>().UseSqlServer(connection.ConnectionString).Options);
    }
    public async ValueTask DisposeAsync()
    {
        if (!Db.Database.GetDbConnection().Database.StartsWith("BirdLabMessagingTest_", StringComparison.Ordinal)) throw new InvalidOperationException();
        await Db.Database.EnsureDeletedAsync();
        await Db.DisposeAsync();
    }
}

public sealed class SqlMessagingTests
{
    [SqlFact]
    public async Task MigrationPreservesExistingNumericIdsPredictionsAndResult()
    {
        await using var database = new SqlDatabase();
        var db = database.Db;
        var migrator = db.GetService<IMigrator>();
        await migrator.MigrateAsync("20261028115223_InitialCreate");
        await db.Database.ExecuteSqlRawAsync("INSERT INTO Analyses (AnalysisType,OriginalFileName,StoredFilePath,FileHash,PredictedSpecies,Confidence,ModelName,ModelRevision,AnalysisDate,Description,ElapsedSeconds,MetadataJson,BirdSnapshotJson) VALUES ('image',N'Старий птах.jpg','11111111111111111111111111111111.jpg','old-hash','Old species',0.8,'old-model','old-revision','2026-10-28T10:00:00+00:00',N'Старий опис',1,'{{}}','{{}}'); INSERT INTO Predictions (AnalysisId,SpeciesName,ScientificName,Confidence,Rank) VALUES (1,'Old species',NULL,0.8,1),(1,'Second',NULL,0.15,2),(1,'Third',NULL,0.05,3)");
        await migrator.MigrateAsync();
        var old = await db.Analyses.Include(a => a.Predictions).SingleAsync();
        Assert.Equal(1, old.Id);
        Assert.Equal("Old species", old.PredictedSpecies);
        Assert.Equal("Старий опис", old.Description);
        Assert.Equal(3, old.Predictions.Count);
        Assert.Equal("Completed", old.Status);
        Assert.Equal(old.AnalysisDate, old.CreatedAt);
        Assert.NotEqual(Guid.Empty, old.JobId);
        Assert.Equal(Guid.Parse("11111111-1111-1111-1111-111111111111"), old.FileId);
        await migrator.MigrateAsync();
        Assert.Single(db.Analyses);
    }

    [SqlFact]
    public async Task SqlAtomicOutboxRollbackAndInboxDeduplication()
    {
        await using var database = new SqlDatabase();
        var db = database.Db;
        await db.Database.MigrateAsync();
        using var files = new TestFiles();
        var service = await TestAccount.Analyses(db, new UnitAiClient(true), files.Store);
        db.InboxMessages.Add(new() { Id = Guid.NewGuid(), BodyHash = new string('x', 65) });
        await Assert.ThrowsAsync<DbUpdateException>(() => service.EnqueueAsync(new FormFile(new MemoryStream([1]), 0, 1, "file", "bad-transaction.jpg"), "image", default));
        db.ChangeTracker.Clear();
        Assert.Empty(await db.Analyses.ToArrayAsync());
        Assert.Empty(await db.OutboxMessages.ToArrayAsync());
        var accepted = await service.EnqueueAsync(new FormFile(new MemoryStream([1]), 0, 1, "file", "unit.jpg"), "image", default);
        var analysis = await db.Analyses.SingleAsync();
        var outbox = await db.OutboxMessages.SingleAsync();
        Assert.Equal(accepted.AnalysisId, outbox.AnalysisId);
        var body = JsonSerializer.SerializeToUtf8Bytes(new AnalysisEvent(1, Guid.NewGuid(), analysis.JobId, analysis.CorrelationId, outbox.Id, "completed", DateTimeOffset.UtcNow, 0,
            [new("unit-a", null, .8, 1), new("unit-b", null, .15, 2), new("unit-c", null, .05, 3)], "unit-a", .8, "unit-model", "unit-revision", .1, JsonDocument.Parse("{\"mock_used\":false}").RootElement.Clone()), EventJson.Options);
        var processor = new ResultProcessor(db);
        await processor.ApplyAsync(body, default);
        await processor.ApplyAsync(body, default);
        Assert.Single(await db.Analyses.ToArrayAsync());
        Assert.Single(await db.InboxMessages.ToArrayAsync());
        Assert.Equal(3, await db.Predictions.CountAsync());
        Assert.Equal("Completed", (await service.StatusAsync(accepted.AnalysisId, default)).Status);
    }
}
