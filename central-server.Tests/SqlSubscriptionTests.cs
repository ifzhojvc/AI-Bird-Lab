using BirdLab.Api.Data;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Models;
using BirdLab.Api.Services;
using BirdLab.Api.Subscriptions;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Xunit;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using BirdLab.Api.Messaging;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;

namespace BirdLab.Api.Tests;

public sealed class SqlSubscriptionTests
{
    private sealed class DuringPublishPublisher(Func<Task> action) : IEventPublisher
    {
        public Task PublishAsync(string exchange, string routingKey, ReadOnlyMemory<byte> body, Guid eventId, Guid correlationId, CancellationToken token, int retry = 0) => action();
    }

    [SqlFact]
    public async Task FastWorkerCompletionCannotBeOverwrittenByQueuedAfterPublisherConfirm()
    {
        await using var database = new SqlDatabase();
        var db = database.Db;
        await db.Database.MigrateAsync();
        using var files = new TestFiles();
        var service = await TestAccount.Analyses(db, new UnitAiClient(true), files.Store);
        var task = await service.EnqueueAsync(new FormFile(new MemoryStream([1]), 0, 1, "file", "fast.jpg"), "image", default);
        var analysis = await db.Analyses.AsNoTracking().SingleAsync();
        var request = await db.OutboxMessages.AsNoTracking().SingleAsync();
        var body = JsonSerializer.SerializeToUtf8Bytes(new AnalysisEvent(1, Guid.NewGuid(), analysis.JobId, analysis.CorrelationId, request.Id, "completed", DateTimeOffset.UtcNow, 0,
            [new("first", null, .8, 1), new("second", null, .15, 2), new("third", null, .05, 3)], "first", .8, "unit-model", "unit-revision", .1, JsonDocument.Parse("{\"mock_used\":false}").RootElement.Clone()), EventJson.Options);
        var connection = db.Database.GetConnectionString();
        var services = new ServiceCollection();
        services.AddDbContext<BirdDbContext>(options => options.UseSqlServer(connection));
        await using var provider = services.BuildServiceProvider();
        var publisher = new DuringPublishPublisher(async () =>
        {
            await using var worker = new BirdDbContext(new DbContextOptionsBuilder<BirdDbContext>().UseSqlServer(connection).Options);
            await new ResultProcessor(worker).ApplyAsync(body, default);
        });
        var dispatcher = new OutboxDispatcher(provider.GetRequiredService<IServiceScopeFactory>(), publisher, NullLogger<OutboxDispatcher>.Instance);
        Assert.True(await dispatcher.DispatchOneAsync(default));
        db.ChangeTracker.Clear();
        Assert.Equal("Completed", (await service.StatusAsync(task.AnalysisId, default)).Status);
        Assert.Equal(3, await db.Predictions.CountAsync());
        Assert.NotNull((await db.OutboxMessages.SingleAsync()).PublishedAt);
        Assert.Equal("Consumed", (await db.UsageRecords.SingleAsync()).Status);
    }

    [SqlFact]
    public async Task IdentityRegistrationAndSessionAreStoredInRealSqlServer()
    {
        await using var database = new SqlDatabase();
        await database.Db.Database.MigrateAsync();
        await using var factory = new SubscriptionApiFactory(database.Db.Database.GetConnectionString());
        using var client = await factory.Client();
        var response = await client.PostAsJsonAsync("/api/auth/register", new { email = "identity-sql@example.test", password = "Bird-Sql!Test2026", useBearerToken = true });
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var user = await database.Db.Users.SingleAsync();
        Assert.NotEqual("Bird-Sql!Test2026", user.PasswordHash);
        Assert.Equal(user.Id, (await database.Db.AuthSessions.SingleAsync()).UserId);
    }

    [SqlFact]
    public async Task TwentyParallelRequestsCannotExceedFiveFreeReservations()
    {
        await using var database = new SqlDatabase();
        await database.Db.Database.MigrateAsync();
        database.Db.Users.Add(new ApplicationUser { Id = TestAccount.UserId, UserName = "concurrent@example.test" });
        await database.Db.SaveChangesAsync();
        var connection = database.Db.Database.GetConnectionString();
        using var files = new TestFiles();
        var results = await Task.WhenAll(Enumerable.Range(0, 20).Select(async i =>
        {
            await using var db = new BirdDbContext(new DbContextOptionsBuilder<BirdDbContext>().UseSqlServer(connection).Options);
            var service = new AnalysisService(db, new UnitAiClient(true), files.Store, TestAccount.Current(), new SubscriptionService(db));
            try { await service.EnqueueAsync(new FormFile(new MemoryStream([1, 2, 3]), 0, 3, "file", $"{i}.jpg"), "image", default); return 202; }
            catch (ApiException error) { return error.Status; }
        }));
        Assert.Equal(5, results.Count(s => s == 202));
        Assert.Equal(15, results.Count(s => s == 429));
        Assert.Equal(5, await database.Db.Analyses.CountAsync());
        Assert.Equal(5, await database.Db.UsageRecords.CountAsync());
        Assert.Equal(5, await database.Db.OutboxMessages.CountAsync());
        Assert.Equal(5, Directory.GetFiles(files.Folder).Length);
    }

    [SqlFact]
    public async Task ConcurrentVerificationAndEventReplayCreateOnlyOnePaidPeriod()
    {
        await using var database = new SqlDatabase();
        var db = database.Db;
        await db.Database.MigrateAsync();
        db.Users.Add(new ApplicationUser { Id = TestAccount.UserId, UserName = "payments@example.test" });
        await db.SaveChangesAsync();
        var (service, order, _) = await SubscriptionTests.Order(db);
        var payment = await service.SubmitAsync(TestAccount.UserId, order.Id, "0x" + new string('a', 64), default);
        var connection = db.Database.GetConnectionString();
        await Task.WhenAll(Enumerable.Range(0, 12).Select(async _ =>
        {
            await using var worker = new BirdDbContext(new DbContextOptionsBuilder<BirdDbContext>().UseSqlServer(connection).Options);
            await new PaymentService(worker, new FakeBlockchain(), Microsoft.Extensions.Options.Options.Create(SubscriptionTests.Options())).ProcessAsync(payment.Id, default);
        }));
        Assert.Single(await db.UserSubscriptions.AsNoTracking().ToArrayAsync());
        var secondOrder = await service.CreateAsync(TestAccount.UserId, 1, order.WalletAddress, false, default);
        var replay = await service.SubmitAsync(TestAccount.UserId, secondOrder.Id, payment.TransactionHash, default);
        Assert.Equal(409, (await Assert.ThrowsAsync<ApiException>(() => service.ProcessAsync(replay.Id, default))).Status);
        Assert.Single(await db.UserSubscriptions.AsNoTracking().ToArrayAsync());
    }
}
