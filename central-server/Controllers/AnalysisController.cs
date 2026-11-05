using BirdLab.Api.DTOs;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Services;
using Microsoft.AspNetCore.Mvc;
using BirdLab.Api.Auth;
using BirdLab.Api.Subscriptions;
using Microsoft.AspNetCore.Authorization;

namespace BirdLab.Api.Controllers;

[ApiController]
[Authorize]
[Route("api")]
public sealed class AnalysisController(AnalysisService service, FileStore files, CurrentUser user, SubscriptionService subscriptions) : ControllerBase
{
    [HttpPost("analysis/image")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType<AcceptedAnalysisDto>(202)]
    public async Task<ActionResult<AcceptedAnalysisDto>> Image(IFormFile file, CancellationToken token)
    {
        var result = await service.EnqueueAsync(file, "image", token);
        return Accepted(result.StatusUrl, result);
    }

    [HttpPost("analysis/audio")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType<AcceptedAnalysisDto>(202)]
    public async Task<ActionResult<AcceptedAnalysisDto>> Audio(IFormFile file, CancellationToken token)
    {
        var result = await service.EnqueueAsync(file, "audio", token);
        return Accepted(result.StatusUrl, result);
    }

    [HttpPost("analysis/batch")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType<AcceptedBatchItem[]>(202)]
    public async Task<ActionResult<AcceptedBatchItem[]>> Batch(List<IFormFile> files, CancellationToken token)
    {
        await subscriptions.RequireFeatureAsync(user.Id, "batch", token);
        if (files.Count is < 1 or > 15) throw new ApiException(400, "Виберіть від 1 до 15 фотографій.");
        foreach (var file in files) FileStore.Validate(file.FileName, file.Length, "image");
        var results = new List<AcceptedBatchItem>();
        foreach (var file in files)
        {
            try { results.Add(new(FileStore.CleanName(file.FileName), await service.EnqueueAsync(file, "image", token, "batch"), null)); }
            catch (ApiException exc) { results.Add(new(FileStore.CleanName(file.FileName), null, exc.Message)); }
        }
        return Accepted(results);
    }

    [HttpGet("analyses/{id:guid}/status")]
    public Task<AnalysisStatusDto> Status(Guid id, CancellationToken token) => service.StatusAsync(id, token);

    [HttpPost("analysis/sync/{kind}")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType<AnalysisDto>(201)]
    public async Task<ActionResult<AnalysisDto>> Sync(string kind, IFormFile file, CancellationToken token)
    {
        if (kind is not ("image" or "audio")) throw new ApiException(400, "Невідомий тип аналізу.");
        var result = await service.AnalyzeAsync(file, kind, token);
        return CreatedAtAction(nameof(Get), new { id = result.Id }, result);
    }

    [HttpGet("analyses")]
    public Task<PagedResult<AnalysisDto>> History(CancellationToken token, int page = 1, int pageSize = 20, string? search = null, string? analysisType = null, string sort = "date_desc") => service.HistoryAsync(page, pageSize, search, analysisType, sort, token);

    [HttpGet("analyses/gallery")]
    public async Task<PagedResult<AnalysisDto>> Gallery(CancellationToken token, int page = 1, int pageSize = 20, string? search = null, string sort = "date_desc")
    {
        await subscriptions.RequireFeatureAsync(user.Id, "gallery", token);
        return await service.HistoryAsync(page, pageSize, search, "image", sort, token);
    }

    [HttpGet("analyses/{id:int}")]
    public async Task<AnalysisDto> Get(int id, CancellationToken token) => AnalysisDto.From(await service.GetAsync(id, token));

    [HttpGet("analyses/{id:int}/file")]
    public async Task<IActionResult> Media(int id, CancellationToken token)
    {
        var record = await service.GetAsync(id, token);
        var path = files.Resolve(record.StoredFilePath);
        if (!System.IO.File.Exists(path)) throw new ApiException(404, "Файл відсутній у сховищі.");
        Response.Headers["X-Content-Type-Options"] = "nosniff";
        return PhysicalFile(path, FileStore.ContentType(path), enableRangeProcessing: true);
    }

    [HttpDelete("analyses/{id:int}")]
    public async Task<IActionResult> Delete(int id, CancellationToken token) { await service.DeleteAsync(id, token); return NoContent(); }

    [HttpGet("analyses/compare")]
    public async Task<ModelComparisonDto> Compare(int firstId, int secondId, CancellationToken token)
    {
        await subscriptions.RequireFeatureAsync(user.Id, "compare", token);
        if (firstId == secondId) throw new ApiException(400, "Оберіть два різні аналізи.");
        var first = await service.GetAsync(firstId, token);
        var second = await service.GetAsync(secondId, token);
        if (first.Status != "Completed" || second.Status != "Completed") throw new ApiException(409, "Порівнювати можна лише завершені аналізи.");
        var conclusion = first.BirdId is null || second.BirdId is null ? "Порівняння неможливе: немає перевіреного зіставлення видів." : first.BirdId == second.BirdId ? "Моделі визначили той самий вид." : "Моделі визначили різні види.";
        return new(AnalysisDto.From(first), AnalysisDto.From(second), conclusion + " Збіг не підтверджує одну особину або точність моделі.");
    }
}
