namespace BirdLab.Api.Models;

public sealed class Analysis
{
    public int Id { get; set; }
    public string? UserId { get; set; }
    public Guid JobId { get; set; } = Guid.NewGuid();
    public Guid FileId { get; set; }
    public string Status { get; set; } = "Completed";
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? StartedAt { get; set; }
    public DateTimeOffset? CompletedAt { get; set; }
    public string? ErrorMessage { get; set; }
    public int RetryCount { get; set; }
    public Guid CorrelationId { get; set; } = Guid.NewGuid();
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
    public string AnalysisType { get; set; } = "";
    public string OriginalFileName { get; set; } = "";
    public string StoredFilePath { get; set; } = "";
    public string FileHash { get; set; } = "";
    public string PredictedSpecies { get; set; } = "";
    public double Confidence { get; set; }
    public string ModelName { get; set; } = "";
    public string ModelRevision { get; set; } = "";
    public DateTimeOffset AnalysisDate { get; set; }
    public string Description { get; set; } = "";
    public double ElapsedSeconds { get; set; }
    public string MetadataJson { get; set; } = "{}";
    public string BirdSnapshotJson { get; set; } = "{}";
    public string? LegacySource { get; set; }
    public int? LegacyId { get; set; }
    public int? BirdId { get; set; }
    public Bird? Bird { get; set; }
    public List<Prediction> Predictions { get; set; } = [];
    public Evaluation? Evaluation { get; set; }
}

public sealed class Prediction
{
    public int Id { get; set; }
    public int AnalysisId { get; set; }
    public Analysis Analysis { get; set; } = null!;
    public string SpeciesName { get; set; } = "";
    public string? ScientificName { get; set; }
    public double Confidence { get; set; }
    public int Rank { get; set; }
}

public sealed class Evaluation
{
    public int AnalysisId { get; set; }
    public Analysis Analysis { get; set; } = null!;
    public string ExpectedLabel { get; set; } = "";
    public string ExpectedScientific { get; set; } = "";
    public string LabelSource { get; set; } = "";
    public string FileHash { get; set; } = "";
    public bool Top1Correct { get; set; }
    public bool Top3Correct { get; set; }
    public string Experiment { get; set; } = "";
}
