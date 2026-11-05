using System.Text;
using BirdLab.Api.Data;
using BirdLab.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace BirdLab.Api.Messaging;

public sealed class OutboxDispatcher(IServiceScopeFactory scopes, IEventPublisher publisher, ILogger<OutboxDispatcher> logger) : BackgroundService
{
    public static TimeSpan Backoff(int attempt) => TimeSpan.FromSeconds(Math.Min(60, Math.Pow(2, Math.Min(attempt, 6))));

    public async Task<bool> DispatchOneAsync(CancellationToken token)
    {
        using var scope = scopes.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<BirdDbContext>();
        await using var tx = db.Database.IsRelational() ? await db.Database.BeginTransactionAsync(token) : null;
        var now = DateTimeOffset.UtcNow;
        var query = db.Database.IsSqlServer()
            ? db.OutboxMessages.FromSqlInterpolated($"SELECT TOP (1) * FROM OutboxMessages WITH (UPDLOCK, READPAST, ROWLOCK) WHERE PublishedAt IS NULL AND NextAttemptAt <= {now} ORDER BY CreatedAt")
            : db.OutboxMessages.Where(e => e.PublishedAt == null && e.NextAttemptAt <= now).Take(1);
        var item = (await query.ToArrayAsync(token)).FirstOrDefault();
        if (item is null) return false;
        item.Attempts++;
        try
        {
            var analysis = await db.Analyses.SingleOrDefaultAsync(a => a.JobId == item.AnalysisId, token);
            if (analysis is null) throw new InvalidOperationException("Outbox не має відповідного аналізу.");
            await publisher.PublishAsync(RabbitBus.Exchange, "analysis.requested", Encoding.UTF8.GetBytes(item.Payload), item.Id, analysis.CorrelationId, token);
            item.PublishedAt = DateTimeOffset.UtcNow;
            item.LastError = null;
            if (analysis.Status == "Pending")
            {
                if (db.Database.IsRelational())
                    await db.Analyses.Where(a => a.JobId == item.AnalysisId && a.Status == "Pending").ExecuteUpdateAsync(update => update.SetProperty(a => a.Status, "Queued").SetProperty(a => a.UpdatedAt, DateTimeOffset.UtcNow), token);
                else { analysis.Status = "Queued"; analysis.UpdatedAt = DateTimeOffset.UtcNow; }
            }
        }
        catch (OperationCanceledException) when (token.IsCancellationRequested) { throw; }
        catch (Exception exc)
        {
            item.LastError = "Брокер не підтвердив публікацію: " + exc.GetType().Name;
            item.NextAttemptAt = DateTimeOffset.UtcNow + Backoff(item.Attempts);
            logger.LogWarning("Outbox {EventId}, спроба {Attempt}: {Error}", item.Id, item.Attempts, exc.GetType().Name);
        }
        await db.SaveChangesAsync(token);
        if (tx is not null) await tx.CommitAsync(token);
        return true;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try { if (await DispatchOneAsync(stoppingToken)) continue; }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
            catch (Exception exc) { logger.LogWarning("Outbox тимчасово недоступний: {Error}", exc.GetType().Name); }
            try { await Task.Delay(TimeSpan.FromSeconds(2), stoppingToken); }
            catch (OperationCanceledException) { break; }
        }
    }
}
