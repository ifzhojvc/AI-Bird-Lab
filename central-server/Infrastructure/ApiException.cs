using System.Text.Json;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;

namespace BirdLab.Api.Infrastructure;

public sealed class ApiException(int status, string message) : Exception(message)
{
    public int Status { get; } = status;
}

public sealed class ApiExceptionHandler(ILogger<ApiExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext context, Exception exception, CancellationToken token)
    {
        var status = exception switch { ApiException api => api.Status, BadHttpRequestException bad => bad.StatusCode, SqlException or DbUpdateException => 503, _ => 500 };
        var detail = exception is ApiException or BadHttpRequestException ? exception.Message : status == 503 ? "База даних недоступна. Перевірте SQL Server та connection string." : "Внутрішня помилка сервера. Ідентифікатор запиту допоможе знайти її в журналі.";
        logger.LogError(exception, "Request failed {TraceId}", context.TraceIdentifier);
        context.Response.StatusCode = status;
        await context.Response.WriteAsJsonAsync(new ProblemDetails { Status = status, Title = "Не вдалося виконати запит", Detail = detail, Extensions = { ["traceId"] = context.TraceIdentifier } }, token);
        return true;
    }
}
