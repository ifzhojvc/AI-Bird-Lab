using BirdLab.Api.Data;
using BirdLab.Api.DTOs;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Models;
using Microsoft.EntityFrameworkCore;
using BirdLab.Api.Messaging;
using System.Text.Json;
using BirdLab.Api.Auth;
using BirdLab.Api.Subscriptions;

namespace BirdLab.Api.Services;

public sealed class AnalysisService(BirdDbContext db, IAiClient ai, FileStore files, CurrentUser user, SubscriptionService subscriptions)
{
    public IQueryable<Analysis> Query => db.Analyses.AsNoTracking().Where(a => a.UserId == user.Id).Include(a => a.Bird).Include(a => a.Predictions).Include(a => a.Evaluation);

    public async Task<AcceptedAnalysisDto> EnqueueAsync(IFormFile file, string kind, CancellationToken token, string? requiredFeature = null)
    {
        _ = user.Id;
        FileStore.Validate(file.FileName, file.Length, kind);
        await using var input = file.OpenReadStream();
        var stored = await files.SaveAsync(input, file.FileName, kind, file.Length, token);
        var now = DateTimeOffset.UtcNow;
        var analysis = new Analysis
        {
            UserId = user.Id,
            AnalysisType = kind, OriginalFileName = stored.OriginalName, StoredFilePath = stored.Key, FileHash = stored.Hash,
            FileId = Guid.ParseExact(Path.GetFileNameWithoutExtension(stored.Key), "N"), Status = "Pending", CreatedAt = now, UpdatedAt = now, AnalysisDate = now
        };
        var request = new AnalysisRequest(1, Guid.NewGuid(), analysis.JobId, kind, analysis.FileId, stored.Hash, now, analysis.CorrelationId);
        try
        {
            await using var tx = db.Database.IsRelational() ? await db.Database.BeginTransactionAsync(token) : null;
            await subscriptions.ReserveAsync(user.Id, analysis.JobId, kind, token, requiredFeature);
            db.Analyses.Add(analysis);
            db.OutboxMessages.Add(new OutboxMessage { Id = request.EventId, AnalysisId = analysis.JobId, Payload = JsonSerializer.Serialize(request, EventJson.Options), CreatedAt = now, NextAttemptAt = now });
            await db.SaveChangesAsync(token);
            if (tx is not null) await tx.CommitAsync(token);
        }
        catch { files.Remove(stored.Key); throw; }
        return new(analysis.JobId, analysis.Status, $"/api/analyses/{analysis.JobId}/status", analysis.Id);
    }

    public async Task<AnalysisStatusDto> StatusAsync(Guid id, CancellationToken token)
    {
        var a = await Query.SingleOrDefaultAsync(a => a.JobId == id, token) ?? throw new ApiException(404, "Завдання не знайдено.");
        return new(a.JobId, a.Id, a.AnalysisType, a.Status, a.CreatedAt, a.StartedAt, a.CompletedAt, a.ErrorMessage, a.RetryCount, a.CorrelationId, a.Status is not ("Completed" or "Failed") && a.UpdatedAt < DateTimeOffset.UtcNow.AddMinutes(-15), a.Status == "Completed" ? AnalysisDto.From(a) : null);
    }

    public async Task<AnalysisDto> AnalyzeAsync(IFormFile file, string kind, CancellationToken token)
    {
        _ = user.Id;
        FileStore.Validate(file.FileName, file.Length, kind);
        await using var input = file.OpenReadStream();
        var stored = await files.SaveAsync(input, file.FileName, kind, file.Length, token);
        var analysis = new Analysis { UserId = user.Id, AnalysisType = kind, OriginalFileName = stored.OriginalName, StoredFilePath = stored.Key, FileHash = stored.Hash, FileId = Guid.ParseExact(Path.GetFileNameWithoutExtension(stored.Key), "N"), Status = "Processing", AnalysisDate = DateTimeOffset.UtcNow, StartedAt = DateTimeOffset.UtcNow };
        try
        {
            await using (var tx = db.Database.IsRelational() ? await db.Database.BeginTransactionAsync(token) : null)
            {
                await subscriptions.ReserveAsync(user.Id, analysis.JobId, kind, token);
                db.Analyses.Add(analysis);
                await db.SaveChangesAsync(token);
                if (tx is not null) await tx.CommitAsync(token);
            }
        }
        catch { files.Remove(stored.Key); throw; }
        try
        {
            await using var content = File.OpenRead(files.Resolve(stored.Key));
            var result = await ai.PredictAsync(content, stored.OriginalName, kind, token);
            var best = result.Predictions.MinBy(p => p.Rank)!;
            var bird = best.ScientificName is null ? null : await db.Birds.SingleOrDefaultAsync(b => b.ScientificName == best.ScientificName, token);
            var completed = DateTimeOffset.UtcNow;
            await using var tx = db.Database.IsRelational() ? await db.Database.BeginTransactionAsync(token) : null;
            await UserLock.AcquireAsync(db, user.Id, token);
            analysis.Status = "Completed";
            analysis.PredictedSpecies = best.SpeciesName;
            analysis.Confidence = best.Confidence;
            analysis.ModelName = result.ModelId;
            analysis.ModelRevision = result.ModelRevision;
            analysis.AnalysisDate = completed;
            analysis.CompletedAt = completed;
            analysis.UpdatedAt = completed;
            analysis.ElapsedSeconds = result.ElapsedSeconds;
            analysis.Bird = bird;
            analysis.Description = kind == "audio" && best.SpeciesName == "background" ? "Фоновий звук. Пташиний вид не визначено." : "Найвище значення confidence моделі; вид потребує незалежного підтвердження.";
            analysis.MetadataJson = result.Metadata.GetRawText();
            analysis.Predictions = result.Predictions.Select(p => new Prediction { SpeciesName = p.SpeciesName, ScientificName = p.ScientificName, Confidence = p.Confidence, Rank = p.Rank }).ToList();
            await SubscriptionService.SettleAsync(db, analysis.JobId, true, token);
            await db.SaveChangesAsync(token);
            if (tx is not null) await tx.CommitAsync(token);
            return AnalysisDto.From(analysis);
        }
        catch
        {
            db.ChangeTracker.Clear();
            await using var tx = db.Database.IsRelational() ? await db.Database.BeginTransactionAsync(CancellationToken.None) : null;
            await UserLock.AcquireAsync(db, user.Id, CancellationToken.None);
            var failed = await db.Analyses.SingleAsync(a => a.JobId == analysis.JobId, CancellationToken.None);
            if (failed.Status != "Completed")
            {
                failed.Status = "Failed";
                failed.ErrorMessage = "Синхронний аналіз завершився технічною помилкою. Ліміт повернено.";
                failed.CompletedAt = DateTimeOffset.UtcNow;
                failed.UpdatedAt = DateTimeOffset.UtcNow;
                await SubscriptionService.SettleAsync(db, failed.JobId, false, CancellationToken.None);
                db.Analyses.Remove(failed);
                await db.SaveChangesAsync(CancellationToken.None);
            }
            if (tx is not null) await tx.CommitAsync(CancellationToken.None);
            if (failed.Status != "Completed") files.Remove(stored.Key);
            throw;
        }
    }

    public async Task<Analysis> GetAsync(int id, CancellationToken token) => await Query.SingleOrDefaultAsync(a => a.Id == id, token) ?? throw new ApiException(404, "Аналіз не знайдено.");

    public async Task<PagedResult<AnalysisDto>> HistoryAsync(int page, int pageSize, string? search, string? analysisType, string sort, CancellationToken token)
    {
        if (page is < 1 or > 100000 || pageSize is < 1 or > 100) throw new ApiException(400, "Сторінка має бути додатною, розмір сторінки — від 1 до 100.");
        var query = Query.Where(a => a.Status == "Completed");
        if (!string.IsNullOrEmpty(analysisType))
        {
            if (analysisType is not ("image" or "audio")) throw new ApiException(400, "Невідомий тип аналізу.");
            query = query.Where(a => a.AnalysisType == analysisType);
        }
        if (!string.IsNullOrWhiteSpace(search))
        {
            var text = search.Trim();
            if (text.Length > 200) throw new ApiException(400, "Пошуковий запит задовгий.");
            query = query.Where(a => a.OriginalFileName.Contains(text) || a.PredictedSpecies.Contains(text) || a.Bird != null && (a.Bird.UkrainianName.Contains(text) || a.Bird.ScientificName.Contains(text) || a.Bird.CommonName.Contains(text)));
        }
        var total = await query.CountAsync(token);
        query = sort switch { "date_desc" => query.OrderByDescending(a => a.AnalysisDate).ThenByDescending(a => a.Id), "date_asc" => query.OrderBy(a => a.AnalysisDate).ThenBy(a => a.Id), "confidence_desc" => query.OrderByDescending(a => a.Confidence).ThenByDescending(a => a.Id), "species" => query.OrderBy(a => a.PredictedSpecies).ThenBy(a => a.Id), _ => throw new ApiException(400, "Невідомий порядок сортування.") };
        var rows = await query.Skip((page - 1) * pageSize).Take(pageSize).ToArrayAsync(token);
        return new(rows.Select(AnalysisDto.From).ToArray(), total, page, pageSize);
    }

    public async Task DeleteAsync(int id, CancellationToken token)
    {
        var record = await db.Analyses.SingleOrDefaultAsync(a => a.Id == id && a.UserId == user.Id, token) ?? throw new ApiException(404, "Аналіз не знайдено.");
        if (record.Status is not ("Completed" or "Failed")) throw new ApiException(409, "Завдання ще обробляється. Дочекайтеся завершення.");
        var original = files.Resolve(record.StoredFilePath);
        var quarantine = files.Resolve(Guid.NewGuid().ToString("N") + ".tmp");
        var moved = File.Exists(original);
        if (moved) File.Move(original, quarantine);
        try { db.Analyses.Remove(record); await db.SaveChangesAsync(token); }
        catch { if (moved) File.Move(quarantine, original); throw; }
        if (moved) File.Delete(quarantine);
    }
}
