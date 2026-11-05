using BirdLab.Api.Data;
using Microsoft.EntityFrameworkCore;

namespace BirdLab.Api.Messaging;

public sealed class StalledJobMonitor(IServiceScopeFactory scopes, ILogger<StalledJobMonitor> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromMinutes(1));
        try
        {
            while (await timer.WaitForNextTickAsync(stoppingToken))
            {
                try
                {
                    using var scope = scopes.CreateScope();
                    var db = scope.ServiceProvider.GetRequiredService<BirdDbContext>();
                    var before = DateTimeOffset.UtcNow.AddMinutes(-15);
                    var stalled = await db.Analyses.Where(a => a.Status != "Completed" && a.Status != "Failed" && a.UpdatedAt < before).Select(a => new { a.JobId, a.Status, a.CorrelationId }).Take(50).ToArrayAsync(stoppingToken);
                    foreach (var job in stalled) logger.LogWarning("Завдання {AnalysisId} без оновлень понад 15 хв: {Status}, correlation={CorrelationId}; перевірте outbox, consumers і DLQ", job.JobId, job.Status, job.CorrelationId);
                }
                catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
                catch (Exception exc) { logger.LogWarning("Діагностика завдань недоступна: {Error}", exc.GetType().Name); }
            }
        }
        catch (OperationCanceledException) { }
    }
}
