using System.Text.Json;
using System.Text.Json.Serialization;

namespace BirdLab.Api.Messaging;

public sealed record AnalysisRequest(int SchemaVersion, Guid EventId, Guid AnalysisId, string AnalysisType, Guid FileId, string FileSha256, DateTimeOffset CreatedAt, Guid CorrelationId);
public sealed record EventPrediction(string Species, string? ScientificName, double Confidence, int Rank);
public sealed record AnalysisEvent(int SchemaVersion, Guid EventId, Guid AnalysisId, Guid CorrelationId, Guid CausationId, string Status, DateTimeOffset OccurredAt, int RetryCount, EventPrediction[]? Predictions = null, string? PredictedSpecies = null, double? Confidence = null, string? ModelName = null, string? ModelRevision = null, double? ElapsedSeconds = null, JsonElement? Metadata = null, string? ErrorMessage = null);

public sealed class InvalidEventException(string message) : Exception(message);

public static class EventJson
{
    public static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = false,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        MaxDepth = 16
    };

    public static AnalysisEvent Read(ReadOnlySpan<byte> body)
    {
        if (body.Length > 65536) throw new InvalidEventException("Повідомлення перевищує 64 КБ.");
        AnalysisEvent e;
        try { e = JsonSerializer.Deserialize<AnalysisEvent>(body, Options) ?? throw new JsonException(); }
        catch (JsonException) { throw new InvalidEventException("Некоректний JSON події."); }
        if (e.SchemaVersion != 1 || e.EventId == Guid.Empty || e.AnalysisId == Guid.Empty || e.CorrelationId == Guid.Empty || e.CausationId == Guid.Empty || e.OccurredAt == default || e.OccurredAt.Offset != TimeSpan.Zero || e.RetryCount is < 0 or > 3 || e.Status is not ("processing" or "completed" or "failed"))
            throw new InvalidEventException("Невідома схема або некоректний конверт події.");
        if (e.Status == "failed" && (string.IsNullOrWhiteSpace(e.ErrorMessage) || e.ErrorMessage.Length > 2000)) throw new InvalidEventException("Подія помилки не містить коректного пояснення.");
        if (e.Status == "completed")
        {
            var p = e.Predictions;
            if (p is null || p.Length != 3 || p.Any(x => x is null) || !p.Select(x => x.Rank).Order().SequenceEqual([1, 2, 3]) || p.Any(x => string.IsNullOrWhiteSpace(x.Species) || x.Species.Length > 256 || x.ScientificName?.Length > 256 || !double.IsFinite(x.Confidence) || x.Confidence is < 0 or > 1) || p.Select(x => x.Species).Distinct().Count() != 3 || string.IsNullOrWhiteSpace(e.ModelName) || e.ModelName.Length > 512 || string.IsNullOrWhiteSpace(e.ModelRevision) || e.ModelRevision.Length > 256 || e.ElapsedSeconds is null || !double.IsFinite(e.ElapsedSeconds.Value) || e.ElapsedSeconds < 0 || e.Metadata is not { ValueKind: JsonValueKind.Object })
                throw new InvalidEventException("Неповний результат моделі.");
            var ordered = p.OrderBy(x => x.Rank).ToArray();
            if (ordered[0].Confidence < ordered[1].Confidence || ordered[1].Confidence < ordered[2].Confidence || e.PredictedSpecies != ordered[0].Species || e.Confidence != ordered[0].Confidence || !e.Metadata.Value.TryGetProperty("mock_used", out var mock) || mock.ValueKind != JsonValueKind.False)
                throw new InvalidEventException("Некоректні TOP-3 або походження результату.");
        }
        return e;
    }
}
