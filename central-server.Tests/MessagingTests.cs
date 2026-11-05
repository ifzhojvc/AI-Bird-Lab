using System.Text.Json;
using BirdLab.Api.Data;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Messaging;
using BirdLab.Api.Models;
using BirdLab.Api.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace BirdLab.Api.Tests;

public sealed class UnitPublisher(bool fail = false) : IEventPublisher
{
    public List<Guid> Events { get; } = [];
    public Task PublishAsync(string exchange, string key, ReadOnlyMemory<byte> body, Guid eventId, Guid correlationId, CancellationToken token, int retry = 0)
    {
        Events.Add(eventId);
        if (fail) throw new IOException("Unit test broker unavailable");
        return Task.CompletedTask;
    }
}

public sealed class MessagingTests
{
    [Theory]
    [InlineData((sbyte)0, 0)]
    [InlineData((byte)1, 1)]
    [InlineData((short)2, 2)]
    [InlineData(3, 3)]
    [InlineData(1L, 1)]
    [InlineData("1", -1)]
    [InlineData(true, -1)]
    public void AcceptsAmqpIntegerWidthsAndRejectsMalformedRetryHeader(object value, int expected) => Assert.Equal(expected, ResultConsumer.ReadRetry(value));

    private static BirdDbContext Db() => new(new DbContextOptionsBuilder<BirdDbContext>().UseInMemoryDatabase(Guid.NewGuid().ToString()).Options);
    private static byte[] Body(Analysis a, Guid causation, string status, Guid? eventId = null) => JsonSerializer.SerializeToUtf8Bytes(new AnalysisEvent(1, eventId ?? Guid.NewGuid(), a.JobId, a.CorrelationId, causation, status, DateTimeOffset.UtcNow, 0,
        status == "completed" ? [new("Cardinal", "Cardinalis cardinalis", .8, 1), new("Blue Jay", null, .15, 2), new("Mallard", null, .05, 3)] : null,
        status == "completed" ? "Cardinal" : null, status == "completed" ? .8 : null, status == "completed" ? "unit-model" : null, status == "completed" ? "unit-revision" : null, status == "completed" ? .1 : null,
        status == "completed" ? JsonDocument.Parse("{\"mock_used\":false}").RootElement.Clone() : null, status == "failed" ? "Unit file error" : null), EventJson.Options);

    private static async Task<(Analysis Analysis, OutboxMessage Request)> Pending(BirdDbContext db)
    {
        var a = new Analysis { Status = "Pending", AnalysisType = "image", StoredFilePath = Guid.NewGuid().ToString("N") + ".jpg" };
        var request = new OutboxMessage { Id = Guid.NewGuid(), AnalysisId = a.JobId };
        db.Add(a);
        db.Add(request);
        await db.SaveChangesAsync();
        return (a, request);
    }

    [Fact]
    public async Task EnqueueCreatesAnalysisAndOutboxWithoutInvokingAi()
    {
        await using var db = Db();
        using var files = new TestFiles();
        var service = await TestAccount.Analyses(db, new UnitAiClient(true), files.Store);
        var accepted = await service.EnqueueAsync(new FormFile(new MemoryStream([1, 2, 3]), 0, 3, "file", "bird.jpg"), "image", default);
        Assert.Equal("Pending", accepted.Status);
        var a = Assert.Single(db.Analyses);
        var outbox = Assert.Single(db.OutboxMessages);
        var request = JsonSerializer.Deserialize<AnalysisRequest>(outbox.Payload, EventJson.Options)!;
        Assert.Equal(a.JobId, request.AnalysisId);
        Assert.Equal(a.FileId, request.FileId);
        Assert.DoesNotContain(files.Folder, outbox.Payload);
        Assert.Empty(a.Predictions);
        Assert.Empty((await service.HistoryAsync(1, 20, null, null, "date_desc", default)).Items);
        Assert.Equal(a.JobId, (await service.StatusAsync(a.JobId, default)).AnalysisId);
        await Assert.ThrowsAsync<ApiException>(() => service.DeleteAsync(a.Id, default));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task OutboxMarksPublishedOnlyAfterConfirmation(bool fail)
    {
        var services = new ServiceCollection();
        var name = Guid.NewGuid().ToString();
        services.AddDbContext<BirdDbContext>(o => o.UseInMemoryDatabase(name));
        await using var provider = services.BuildServiceProvider();
        Analysis a;
        OutboxMessage request;
        using (var scope = provider.CreateScope()) (a, request) = await Pending(scope.ServiceProvider.GetRequiredService<BirdDbContext>());
        var publisher = new UnitPublisher(fail);
        var dispatcher = new OutboxDispatcher(provider.GetRequiredService<IServiceScopeFactory>(), publisher, NullLogger<OutboxDispatcher>.Instance);
        Assert.True(await dispatcher.DispatchOneAsync(default));
        using var check = provider.CreateScope();
        var db = check.ServiceProvider.GetRequiredService<BirdDbContext>();
        var stored = await db.OutboxMessages.SingleAsync();
        Assert.Equal(request.Id, Assert.Single(publisher.Events));
        Assert.Equal(!fail, stored.PublishedAt.HasValue);
        Assert.Equal(fail ? "Pending" : "Queued", (await db.Analyses.SingleAsync()).Status);
        if (fail) Assert.True(stored.NextAttemptAt > DateTimeOffset.UtcNow);
    }

    [Fact]
    public async Task DuplicateAndLateEventsNeverDuplicateOrRegressCompletedAnalysis()
    {
        await using var db = Db();
        var (a, request) = await Pending(db);
        var processor = new ResultProcessor(db);
        var body = Body(a, request.Id, "completed");
        await processor.ApplyAsync(body, default);
        await processor.ApplyAsync(body, default);
        await processor.ApplyAsync(Body(a, request.Id, "processing"), default);
        await processor.ApplyAsync(Body(a, request.Id, "failed"), default);
        Assert.Equal("Completed", a.Status);
        Assert.Equal(3, await db.Predictions.CountAsync());
        Assert.Equal(3, await db.InboxMessages.CountAsync());
        Assert.Single(db.Analyses);
    }

    [Fact]
    public async Task FailedIsTerminalAndInvalidCorrelationIsRejected()
    {
        await using var db = Db();
        var (a, request) = await Pending(db);
        var processor = new ResultProcessor(db);
        await Assert.ThrowsAsync<InvalidEventException>(() => processor.ApplyAsync(Body(a, Guid.NewGuid(), "completed"), default));
        await processor.ApplyAsync(Body(a, request.Id, "failed"), default);
        await processor.ApplyAsync(Body(a, request.Id, "completed"), default);
        Assert.Equal("Failed", a.Status);
        Assert.Empty(db.Predictions);
    }

    [Fact]
    public async Task EventIdCannotBeReusedWithDifferentContent()
    {
        await using var db = Db();
        var (a, request) = await Pending(db);
        var processor = new ResultProcessor(db);
        var id = Guid.NewGuid();
        await processor.ApplyAsync(Body(a, request.Id, "processing", id), default);
        await Assert.ThrowsAsync<InvalidEventException>(() => processor.ApplyAsync(Body(a, request.Id, "completed", id), default));
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"schemaVersion\":2}")]
    [InlineData("not json")]
    public void RejectsInvalidEnvelope(string json) => Assert.Throws<InvalidEventException>(() => EventJson.Read(System.Text.Encoding.UTF8.GetBytes(json)));
}
