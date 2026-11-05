using BirdLab.Api.Data;
using BirdLab.Api.DTOs;
using BirdLab.Api.Infrastructure;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace BirdLab.Api.Controllers;

[ApiController, Route("api/legacy/archive"), Authorize(Policy = "LegacyArchive")]
public sealed class LegacyArchiveController(BirdDbContext db, FileStore files) : ControllerBase
{
    [HttpGet]
    public async Task<PagedResult<AnalysisDto>> List(CancellationToken token, int page = 1, int pageSize = 20)
    {
        if (page is < 1 or > 100000 || pageSize is < 1 or > 100) throw new ApiException(400, "Некоректна сторінка.");
        var query = db.Analyses.AsNoTracking().Where(a => a.UserId == null && a.Status == "Completed");
        var total = await query.CountAsync(token);
        var rows = await query.Include(a => a.Predictions).Include(a => a.Bird).Include(a => a.Evaluation).OrderBy(a => a.Id).Skip((page - 1) * pageSize).Take(pageSize).ToArrayAsync(token);
        return new(rows.Select(a => AnalysisDto.From(a) with { FileUrl = $"/api/legacy/archive/{a.Id}/file" }).ToArray(), total, page, pageSize);
    }
    [HttpGet("{id:int}/file")]
    public async Task<IActionResult> File(int id, CancellationToken token)
    {
        var a = await db.Analyses.AsNoTracking().SingleOrDefaultAsync(a => a.Id == id && a.UserId == null, token) ?? throw new ApiException(404, "Архівний аналіз не знайдено.");
        var path = files.Resolve(a.StoredFilePath);
        if (!System.IO.File.Exists(path)) throw new ApiException(404, "Файл відсутній.");
        Response.Headers["X-Content-Type-Options"] = "nosniff";
        return PhysicalFile(path, FileStore.ContentType(path), enableRangeProcessing: true);
    }
}
