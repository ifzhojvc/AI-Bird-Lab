using BirdLab.Api.Data;
using BirdLab.Api.DTOs;
using BirdLab.Api.Auth;
using BirdLab.Api.Models;
using BirdLab.Api.Subscriptions;
using Microsoft.EntityFrameworkCore;

namespace BirdLab.Api.Services;

public sealed class StatisticsService(BirdDbContext db, CurrentUser current, SubscriptionService subscriptions)
{
    private IQueryable<Analysis> Query => db.Analyses.Where(a => a.UserId == current.Id);
    public async Task<SummaryDto> SummaryAsync(CancellationToken token)
    {
        var count = await Query.Where(a => a.Status == "Completed").CountAsync(token);
        var features = (await subscriptions.GetAsync(current.Id, token)).Features;
        var extended = features.Contains("statistics");
        return new(count,
            await Query.Where(a => a.Status == "Completed").CountAsync(a => a.AnalysisType == "image", token),
            await Query.Where(a => a.Status == "Completed").CountAsync(a => a.AnalysisType == "audio", token),
            await Query.Where(a => a.Status == "Completed").Where(a => a.BirdId != null).Select(a => a.BirdId).Distinct().CountAsync(token),
            extended ? await Query.Where(a => a.Status == "Completed").Select(a => (double?)a.Confidence).AverageAsync(token) : null,
            !extended || count == 0 ? null : await Query.Where(a => a.Status == "Completed").MinAsync(a => a.Confidence, token),
            !extended || count == 0 ? null : await Query.Where(a => a.Status == "Completed").MaxAsync(a => a.Confidence, token),
            features.Contains("advancedStatistics") ? await db.Evaluations.Where(e => e.Analysis.UserId == current.Id).CountAsync(token) : 0);
    }

    public async Task<SpeciesStatisticsDto[]> SpeciesAsync(CancellationToken token)
    {
        var rows = await Query.Where(a => a.Status == "Completed").GroupBy(a => a.PredictedSpecies).Select(g => new { species = g.Key, count = g.Count(), averageConfidence = g.Average(a => a.Confidence) }).OrderByDescending(g => g.count).Take(30).ToArrayAsync(token);
        return rows.Select(g => new SpeciesStatisticsDto(g.species, g.count, g.averageConfidence)).ToArray();
    }

    public async Task<ConfidenceBinDto[]> ConfidenceAsync(CancellationToken token)
    {
        var bins = await Query.Where(a => a.Status == "Completed").GroupBy(a => a.Confidence < 0.25 ? 0 : a.Confidence < 0.5 ? 1 : a.Confidence < 0.75 ? 2 : 3).Select(g => new { bin = g.Key, count = g.Count() }).ToDictionaryAsync(g => g.bin, g => g.count, token);
        return Enumerable.Range(0, 4).Select(i => new ConfidenceBinDto(new[] { "0–25%", "25–50%", "50–75%", "75–100%" }[i], bins.GetValueOrDefault(i))).ToArray();
    }

    public async Task<EvaluationStatisticsDto[]> EvaluationsAsync(CancellationToken token)
    {
        var rows = await db.Evaluations.Where(e => e.Analysis.UserId == current.Id).GroupBy(e => new { e.Analysis.ModelName, e.Experiment }).Select(g => new { model = g.Key.ModelName, experiment = g.Key.Experiment, samples = g.Count(), top1Correct = g.Count(e => e.Top1Correct), top3Correct = g.Count(e => e.Top3Correct) }).ToArrayAsync(token);
        return rows.Select(g => new EvaluationStatisticsDto(g.model, g.experiment, g.samples, g.top1Correct, g.top3Correct)).ToArray();
    }
}
