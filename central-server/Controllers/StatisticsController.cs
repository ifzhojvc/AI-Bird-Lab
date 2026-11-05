using BirdLab.Api.Data;
using BirdLab.Api.DTOs;
using BirdLab.Api.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using BirdLab.Api.Messaging;
using BirdLab.Api.Auth;
using BirdLab.Api.Subscriptions;
using Microsoft.AspNetCore.Authorization;

namespace BirdLab.Api.Controllers;

[ApiController]
[Route("api")]
public sealed class StatisticsController(StatisticsService statistics, AnalysisService analyses, BirdDbContext db, IHttpClientFactory clients, RabbitBus rabbit, ResultConsumer consumer, CurrentUser current, SubscriptionService subscriptions) : ControllerBase
{
    [HttpGet("statistics/summary")]
    public Task<SummaryDto> Summary(CancellationToken token) => statistics.SummaryAsync(token);
    [HttpGet("statistics/species")]
    public async Task<SpeciesStatisticsDto[]> Species(CancellationToken token) { await subscriptions.RequireFeatureAsync(current.Id, "statistics", token); return await statistics.SpeciesAsync(token); }
    [HttpGet("statistics/confidence")]
    public async Task<ConfidenceBinDto[]> Confidence(CancellationToken token) { await subscriptions.RequireFeatureAsync(current.Id, "statistics", token); return await statistics.ConfidenceAsync(token); }
    [HttpGet("statistics/evaluations")]
    public async Task<EvaluationStatisticsDto[]> Evaluations(CancellationToken token) { await subscriptions.RequireFeatureAsync(current.Id, "advancedStatistics", token); return await statistics.EvaluationsAsync(token); }
    [HttpGet("export/csv")]
    public async Task<IActionResult> Export(CancellationToken token) => File(CsvExport.Build(await analyses.Query.Where(a => a.Status == "Completed").OrderBy(a => a.AnalysisDate).ToArrayAsync(token)), "text/csv; charset=utf-8", "bird_analysis.csv");
    [HttpGet("health")]
    [AllowAnonymous]
    public async Task<IActionResult> Health(CancellationToken token)
    {
        var database = false;
        var ai = false;
        using var databaseDeadline = CancellationTokenSource.CreateLinkedTokenSource(token);
        databaseDeadline.CancelAfter(TimeSpan.FromSeconds(3));
        try { database = await db.Database.CanConnectAsync(databaseDeadline.Token); } catch (Exception) { }
        try
        {
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(token);
            deadline.CancelAfter(TimeSpan.FromSeconds(3));
            using var response = await clients.CreateClient("ai-health").GetAsync("health", deadline.Token);
            ai = response.IsSuccessStatusCode;
        }
        catch (Exception) { }
        var broker = await rabbit.ProbeAsync(token);
        var healthy = database && ai && broker && consumer.Listening && rabbit.WorkerConsumers > 0;
        return StatusCode(healthy ? 200 : 503, new { status = healthy ? "ok" : "degraded", central = true, database, ai, rabbitmq = broker, worker = rabbit.WorkerConsumers > 0, resultConsumer = consumer.Listening, timestamp = DateTimeOffset.UtcNow });
    }
}
