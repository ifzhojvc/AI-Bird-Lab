using BirdLab.Api.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace BirdLab.Api.Subscriptions;

public sealed class SubscriptionMonitor(IServiceScopeFactory scopes, IOptions<BlockchainOptions> settings, ILogger<SubscriptionMonitor> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                using (var scope = scopes.CreateScope())
                    await scope.ServiceProvider.GetRequiredService<SubscriptionService>().ExpireAsync(stoppingToken);
                if (settings.Value.Enabled)
                {
                    Guid[] ids;
                    using (var scope = scopes.CreateScope())
                    {
                        var db = scope.ServiceProvider.GetRequiredService<BirdDbContext>();
                        var now = DateTimeOffset.UtcNow;
                        ids = await db.CryptoPayments.Where(p => p.Status != "Rejected" && p.Status != "ReviewRequired" && p.NextCheckAt <= now).OrderBy(p => p.NextCheckAt).Select(p => p.Id).Take(30).ToArrayAsync(stoppingToken);
                    }
                    foreach (var id in ids)
                    {
                        using var scope = scopes.CreateScope();
                        await scope.ServiceProvider.GetRequiredService<PaymentService>().ProcessAsync(id, stoppingToken);
                    }
                }
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
            catch (Exception exc) { logger.LogWarning("Перевірка підписок тимчасово недоступна: {Error}", exc.GetType().Name); }
            try { await Task.Delay(TimeSpan.FromSeconds(Math.Clamp(settings.Value.PollSeconds, 2, 120)), stoppingToken); }
            catch (OperationCanceledException) { break; }
        }
    }
}
