namespace BirdLab.Api.Models;

public sealed class Bird
{
    public int Id { get; set; }
    public string CommonName { get; set; } = "";
    public string UkrainianName { get; set; } = "";
    public string ScientificName { get; set; } = "";
    public string Family { get; set; } = "";
    public string Habitat { get; set; } = "";
    public string Distribution { get; set; } = "";
    public string Diet { get; set; } = "";
    public string AverageSize { get; set; } = "";
    public string Description { get; set; } = "";
    public string ConservationStatus { get; set; } = "";
    public string SourceUrl { get; set; } = "";
    public string SourcesJson { get; set; } = "[]";
}
