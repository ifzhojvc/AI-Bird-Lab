namespace BirdLab.Api.Models;

public sealed class OutboxMessage
{
    public Guid Id { get; set; }
    public Guid AnalysisId { get; set; }
    public string Payload { get; set; } = "";
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset NextAttemptAt { get; set; }
    public DateTimeOffset? PublishedAt { get; set; }
    public int Attempts { get; set; }
    public string? LastError { get; set; }
}

public sealed class InboxMessage
{
    public Guid Id { get; set; }
    public Guid AnalysisId { get; set; }
    public string BodyHash { get; set; } = "";
    public DateTimeOffset ReceivedAt { get; set; }
}
