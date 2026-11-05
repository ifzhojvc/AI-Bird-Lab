using System.Net;
using System.Net.Http.Headers;
using System.Text.Json;
using BirdLab.Api.DTOs;
using BirdLab.Api.Infrastructure;

namespace BirdLab.Api.Services;

public interface IAiClient
{
    Task<AiResult> PredictAsync(Stream stream, string name, string kind, CancellationToken token);
}

public sealed class AiClient(HttpClient http) : IAiClient
{
    private static readonly JsonSerializerOptions JsonOptions = new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
    public async Task<AiResult> PredictAsync(Stream stream, string name, string kind, CancellationToken token)
    {
        using var body = new MultipartFormDataContent();
        using var content = new StreamContent(stream);
        content.Headers.ContentType = new MediaTypeHeaderValue(FileStore.ContentType(name));
        body.Add(content, "file", FileStore.CleanName(name));
        try
        {
            using var response = await http.PostAsync($"predict/{kind}", body, token);
            if (!response.IsSuccessStatusCode)
            {
                var message = "AI-сервіс не виконав аналіз. Результат не збережено.";
                try
                {
                    using var payload = JsonDocument.Parse(await response.Content.ReadAsStringAsync(token));
                    if (payload.RootElement.TryGetProperty("message", out var detail)) message = detail.GetString() ?? message;
                }
                catch (JsonException) { }
                throw new ApiException(response.StatusCode is HttpStatusCode.UnprocessableEntity or HttpStatusCode.RequestEntityTooLarge ? (int)response.StatusCode : 502, message);
            }
            var result = await response.Content.ReadFromJsonAsync<AiResult>(JsonOptions, token);
            if (result is null || result.AnalysisType != kind || string.IsNullOrWhiteSpace(result.ModelId) || string.IsNullOrWhiteSpace(result.ModelRevision) || result.Metadata.ValueKind != JsonValueKind.Object || result.Predictions is null || result.Predictions.Length != 3 || result.Predictions.Select(p => p.Rank).Order().SequenceEqual(new[] { 1, 2, 3 }) is false || result.Predictions.Any(p => !double.IsFinite(p.Confidence) || p.Confidence is < 0 or > 1 || string.IsNullOrWhiteSpace(p.SpeciesName) || p.SpeciesName.Length > 256 || p.ScientificName?.Length > 256) || result.Predictions.Select(p => p.SpeciesName).Distinct().Count() != 3 || !double.IsFinite(result.ElapsedSeconds) || result.ElapsedSeconds < 0)
                throw new ApiException(502, "AI-сервіс повернув некоректну відповідь.");
            var ordered = result.Predictions.OrderBy(p => p.Rank).ToArray();
            if (ordered[0].Confidence < ordered[1].Confidence || ordered[1].Confidence < ordered[2].Confidence || result.Metadata.TryGetProperty("mock_used", out var mock) && mock.ValueKind == JsonValueKind.True) throw new ApiException(502, "AI-сервіс повернув неприпустимі передбачення.");
            return result;
        }
        catch (OperationCanceledException) when (!token.IsCancellationRequested) { throw new ApiException(504, "Час очікування AI-сервісу вичерпано. Спробуйте ще раз."); }
        catch (HttpRequestException) { throw new ApiException(502, "AI-сервіс недоступний. Перевірте його запуск."); }
        catch (JsonException) { throw new ApiException(502, "Некоректний JSON від AI-сервісу."); }
    }
}
