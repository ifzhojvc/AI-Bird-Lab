using System.Text.Json;
using BirdLab.Api.Models;

namespace BirdLab.Api.DTOs;

public sealed record BirdDto(int Id, string CommonName, string UkrainianName, string ScientificName, string Family, string Habitat, string Distribution, string Diet, string AverageSize, string Description, string ConservationStatus, string SourceUrl, string[] Sources)
{
    public static BirdDto From(Bird b) => new(b.Id, b.CommonName, b.UkrainianName, b.ScientificName, b.Family, b.Habitat, b.Distribution, b.Diet, b.AverageSize, b.Description, b.ConservationStatus, b.SourceUrl, JsonSerializer.Deserialize<string[]>(b.SourcesJson) ?? []);
}

public sealed record PredictionDto(string SpeciesName, string? ScientificName, double Confidence, int Rank);
public sealed record EvaluationDto(string ExpectedLabel, string ExpectedScientific, string LabelSource, bool Top1Correct, bool Top3Correct, string Experiment);
public sealed record AnalysisDto(int Id, string AnalysisType, string OriginalFileName, string FileUrl, string PredictedSpecies, double Confidence, string ModelName, string ModelRevision, DateTimeOffset AnalysisDate, string Description, double ElapsedSeconds, BirdDto? Bird, PredictionDto[] Predictions, EvaluationDto? Evaluation, Guid AnalysisId, string Status)
{
    public static AnalysisDto From(Analysis a) => new(a.Id, a.AnalysisType, a.OriginalFileName, $"/api/analyses/{a.Id}/file", a.PredictedSpecies, a.Confidence, a.ModelName, a.ModelRevision, a.AnalysisDate, a.Description, a.ElapsedSeconds, a.Bird is null ? null : BirdDto.From(a.Bird), a.Predictions.OrderBy(p => p.Rank).Select(p => new PredictionDto(p.SpeciesName, p.ScientificName, p.Confidence, p.Rank)).ToArray(), a.Evaluation is null ? null : new EvaluationDto(a.Evaluation.ExpectedLabel, a.Evaluation.ExpectedScientific, a.Evaluation.LabelSource, a.Evaluation.Top1Correct, a.Evaluation.Top3Correct, a.Evaluation.Experiment), a.JobId, a.Status);
}

public sealed record PagedResult<T>(T[] Items, int Total, int Page, int PageSize);
public sealed record BatchItem(string FileName, AnalysisDto? Analysis, string? Error);
public sealed record AcceptedAnalysisDto(Guid AnalysisId, string Status, string StatusUrl, int HistoryId);
public sealed record AcceptedBatchItem(string FileName, AcceptedAnalysisDto? Task, string? Error);
public sealed record AnalysisStatusDto(Guid AnalysisId, int HistoryId, string AnalysisType, string Status, DateTimeOffset CreatedAt, DateTimeOffset? StartedAt, DateTimeOffset? CompletedAt, string? ErrorMessage, int RetryCount, Guid CorrelationId, bool Stalled, AnalysisDto? Result);
public sealed record AiPrediction(string SpeciesName, string? ScientificName, double Confidence, int Rank);
public sealed record AiResult(string AnalysisType, string ModelId, string ModelRevision, double ElapsedSeconds, AiPrediction[] Predictions, JsonElement Metadata);
public sealed record ComparisonDto(BirdDto First, BirdDto Second);
public sealed record ModelComparisonDto(AnalysisDto First, AnalysisDto Second, string Conclusion);
public sealed record SummaryDto(int TotalAnalyses, int ImageAnalyses, int AudioAnalyses, int IdentifiedSpecies, double? AverageConfidence, double? MinConfidence, double? MaxConfidence, int LabelledEvaluations);
public sealed record SpeciesStatisticsDto(string Species, int Count, double AverageConfidence);
public sealed record ConfidenceBinDto(string Label, int Count);
public sealed record EvaluationStatisticsDto(string Model, string Experiment, int Samples, int Top1Correct, int Top3Correct);
