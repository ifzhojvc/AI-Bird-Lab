using BirdLab.Api.Data;
using BirdLab.Api.DTOs;
using BirdLab.Api.Infrastructure;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using BirdLab.Api.Auth;
using BirdLab.Api.Subscriptions;

namespace BirdLab.Api.Controllers;

[ApiController]
[Route("api/birds")]
public sealed class BirdsController(BirdDbContext db, CurrentUser current, SubscriptionService subscriptions) : ControllerBase
{
    [HttpGet]
    [HttpGet("search")]
    public async Task<BirdDto[]> Search(CancellationToken token, string? search = null)
    {
        if (search?.Length > 200) throw new ApiException(400, "Пошуковий запит задовгий.");
        var query = db.Birds.AsNoTracking();
        if (!string.IsNullOrWhiteSpace(search)) query = query.Where(b => b.CommonName.Contains(search) || b.UkrainianName.Contains(search) || b.ScientificName.Contains(search) || b.Family.Contains(search));
        return (await query.OrderBy(b => b.UkrainianName).Take(500).ToArrayAsync(token)).Select(BirdDto.From).ToArray();
    }

    [HttpGet("{id:int}")]
    public async Task<BirdDto> Get(int id, CancellationToken token) => BirdDto.From(await db.Birds.AsNoTracking().SingleOrDefaultAsync(b => b.Id == id, token) ?? throw new ApiException(404, "Птаха не знайдено."));

    [HttpGet("compare")]
    public async Task<ComparisonDto> Compare(int firstId, int secondId, CancellationToken token)
    {
        await subscriptions.RequireFeatureAsync(current.Id, "compare", token);
        if (firstId == secondId) throw new ApiException(400, "Оберіть два різні види.");
        return new(await Get(firstId, token), await Get(secondId, token));
    }
}
