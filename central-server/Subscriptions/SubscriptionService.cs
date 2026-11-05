using System.Text.Json;
using BirdLab.Api.Data;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace BirdLab.Api.Subscriptions;

public sealed record Entitlement(int PlanId, string Plan, string Status, int AnalysisLimit, int AnalysesUsed, int Remaining, string[] Features, DateTimeOffset StartDate, DateTimeOffset EndDate, Guid? SubscriptionId);

public sealed class SubscriptionService(BirdDbContext db)
{
    public static string[] Features(string json) => JsonSerializer.Deserialize<string[]>(json) ?? [];
    public async Task<Entitlement> GetAsync(string userId, CancellationToken token)
    {
        var now = DateTimeOffset.UtcNow;
        var active = await db.UserSubscriptions.AsNoTracking().Where(s => s.UserId == userId && (s.Status == "Active" || s.Status == "Scheduled") && s.StartDate <= now && s.EndDate > now).OrderByDescending(s => s.StartDate).FirstOrDefaultAsync(token);
        if (active is not null)
        {
            var name = await db.SubscriptionPlans.Where(p => p.Id == active.PlanId).Select(p => p.Name).SingleAsync(token);
            return new(active.PlanId, name, "Active", active.AnalysisLimit, active.AnalysesUsed, Math.Max(0, active.AnalysisLimit - active.AnalysesUsed), Features(active.Features), active.StartDate, active.EndDate, active.Id);
        }
        var free = await db.SubscriptionPlans.AsNoTracking().SingleAsync(p => p.Id == 0, token);
        var start = new DateTimeOffset(now.UtcDateTime.Date, TimeSpan.Zero);
        var end = start.AddDays(1);
        var used = await db.UsageRecords.CountAsync(u => u.UserId == userId && u.UserSubscriptionId == null && u.CreatedAt >= start && u.CreatedAt < end && u.Status != "Released", token);
        return new(0, free.Name, "Free", free.AnalysisLimit, used, Math.Max(0, free.AnalysisLimit - used), free.IsActive ? Features(free.Features) : [], start, end, null);
    }

    public async Task RequireFeatureAsync(string userId, string feature, CancellationToken token)
    {
        if (!(await GetAsync(userId, token)).Features.Contains(feature)) throw new ApiException(403, "Ця можливість недоступна у вашому тарифі. Перегляньте доступні тарифи.");
    }

    public async Task ReserveAsync(string userId, Guid jobId, string feature, CancellationToken token, string? requiredFeature = null)
    {
        await UserLock.AcquireAsync(db, userId, token);
        var access = await GetAsync(userId, token);
        if (!access.Features.Contains(feature) || requiredFeature is not null && !access.Features.Contains(requiredFeature)) throw new ApiException(403, "Ця можливість недоступна у вашому тарифі.");
        if (access.Remaining < 1) throw new ApiException(429, "Ліміт аналізів вичерпано. Дочекайтеся нового періоду або оберіть інший тариф.");
        if (access.SubscriptionId is { } id)
        {
            var subscription = await db.UserSubscriptions.SingleAsync(s => s.Id == id, token);
            subscription.AnalysesUsed++;
        }
        db.UsageRecords.Add(new UsageRecord { JobId = jobId, UserId = userId, UserSubscriptionId = access.SubscriptionId, Feature = requiredFeature ?? feature });
    }

    public static async Task SettleAsync(BirdDbContext db, Guid jobId, bool success, CancellationToken token)
    {
        var usage = await db.UsageRecords.SingleOrDefaultAsync(u => u.JobId == jobId, token);
        if (usage is null || usage.Status != "Reserved") return;
        if (success) usage.Status = "Consumed";
        else
        {
            usage.Status = "Released";
            usage.ReleasedAt = DateTimeOffset.UtcNow;
            if (usage.UserSubscriptionId is { } id)
            {
                var subscription = await db.UserSubscriptions.SingleAsync(s => s.Id == id, token);
                subscription.AnalysesUsed--;
            }
        }
    }

    public async Task ExpireAsync(CancellationToken token)
    {
        var now = DateTimeOffset.UtcNow;
        var users = await db.UserSubscriptions.Where(s => (s.Status == "Active" || s.Status == "Scheduled") && (s.EndDate <= now || s.Status == "Scheduled" && s.StartDate <= now)).Select(s => s.UserId).Distinct().Take(200).ToArrayAsync(token);
        foreach (var userId in users)
        {
            await using var tx = db.Database.IsRelational() ? await db.Database.BeginTransactionAsync(token) : null;
            await UserLock.AcquireAsync(db, userId, token);
            var rows = await db.UserSubscriptions.Where(s => s.UserId == userId && (s.Status == "Active" || s.Status == "Scheduled")).ToArrayAsync(token);
            foreach (var row in rows)
            {
                if (row.EndDate <= now) row.Status = "Expired";
                else if (row.StartDate <= now) row.Status = "Active";
            }
            await db.SaveChangesAsync(token);
            if (tx is not null) await tx.CommitAsync(token);
        }
    }
}
