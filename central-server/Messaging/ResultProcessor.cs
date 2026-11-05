using System.Data;
using System.Security.Cryptography;
using BirdLab.Api.Data;
using BirdLab.Api.Models;
using Microsoft.EntityFrameworkCore;
using BirdLab.Api.Subscriptions;

namespace BirdLab.Api.Messaging;

public sealed class ResultProcessor(BirdDbContext db)
{
    public async Task ApplyAsync(ReadOnlyMemory<byte> body, CancellationToken token)
    {
        var e = EventJson.Read(body.Span);
        var hash = Convert.ToHexString(SHA256.HashData(body.Span));
        var owner = await db.Analyses.AsNoTracking().Where(a => a.JobId == e.AnalysisId).Select(a => a.UserId).SingleOrDefaultAsync(token);
        await using var tx = db.Database.IsRelational() ? await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, token) : null;
        if (owner is not null) await UserLock.AcquireAsync(db, owner, token);
        var existing = await db.InboxMessages.SingleOrDefaultAsync(x => x.Id == e.EventId, token);
        if (existing is not null)
        {
            if (existing.BodyHash != hash || existing.AnalysisId != e.AnalysisId) throw new InvalidEventException("eventId повторено з іншим вмістом.");
            return;
        }
        var a = await db.Analyses.Include(x => x.Predictions).SingleOrDefaultAsync(x => x.JobId == e.AnalysisId, token) ?? throw new InvalidEventException("Невідомий analysisId.");
        var request = await db.OutboxMessages.SingleOrDefaultAsync(x => x.AnalysisId == e.AnalysisId, token);
        if (a.CorrelationId != e.CorrelationId || request?.Id != e.CausationId) throw new InvalidEventException("Подія не відповідає початковому завданню.");
        if (a.Status is not ("Completed" or "Failed"))
        {
            a.RetryCount = Math.Max(a.RetryCount, e.RetryCount);
            a.UpdatedAt = DateTimeOffset.UtcNow;
            if (e.Status == "processing")
            {
                a.Status = "Processing";
                a.StartedAt ??= e.OccurredAt;
            }
            else if (e.Status == "failed")
            {
                a.Status = "Failed";
                a.ErrorMessage = e.ErrorMessage;
                a.CompletedAt = e.OccurredAt;
                await SubscriptionService.SettleAsync(db, a.JobId, false, token);
            }
            else
            {
                a.Status = "Completed";
                a.CompletedAt = e.OccurredAt;
                a.StartedAt ??= e.OccurredAt - TimeSpan.FromSeconds(e.ElapsedSeconds!.Value);
                a.AnalysisDate = e.OccurredAt;
                a.PredictedSpecies = e.PredictedSpecies!;
                a.Confidence = e.Confidence!.Value;
                a.ModelName = e.ModelName!;
                a.ModelRevision = e.ModelRevision!;
                a.ElapsedSeconds = e.ElapsedSeconds!.Value;
                a.MetadataJson = e.Metadata!.Value.GetRawText();
                a.ErrorMessage = null;
                var best = e.Predictions!.Single(p => p.Rank == 1);
                a.Bird = best.ScientificName is null ? null : await db.Birds.SingleOrDefaultAsync(b => b.ScientificName == best.ScientificName, token);
                a.Description = a.AnalysisType == "audio" && best.Species == "background" ? "Фоновий звук. Пташиний вид не визначено." : "Найвище значення confidence моделі; вид потребує незалежного підтвердження.";
                a.Predictions = e.Predictions!.Select(p => new Prediction { SpeciesName = p.Species, ScientificName = p.ScientificName, Confidence = p.Confidence, Rank = p.Rank }).ToList();
                await SubscriptionService.SettleAsync(db, a.JobId, true, token);
            }
        }
        db.InboxMessages.Add(new InboxMessage { Id = e.EventId, AnalysisId = e.AnalysisId, BodyHash = hash, ReceivedAt = DateTimeOffset.UtcNow });
        await db.SaveChangesAsync(token);
        if (tx is not null) await tx.CommitAsync(token);
    }
}
