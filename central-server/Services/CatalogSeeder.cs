using System.Text.Json;
using BirdLab.Api.Data;
using BirdLab.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace BirdLab.Api.Services;

public sealed class CatalogSeeder(BirdDbContext db, IConfiguration configuration, IWebHostEnvironment environment)
{
    public static Bird ParseBird(JsonElement payload)
    {
        string Text(string key) => payload.TryGetProperty(key, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() ?? "" : "";
        var sources = payload.TryGetProperty("sources", out var list) ? list.EnumerateArray().Select(v => v.GetString() ?? "").Where(v => Uri.TryCreate(v, UriKind.Absolute, out var uri) && uri.Scheme == "https").ToArray() : [];
        return new Bird { CommonName = Text("english_name"), UkrainianName = Text("ukrainian_name"), ScientificName = Text("scientific_name"), Family = Text("family"), Habitat = Text("habitat"), Distribution = Text("range"), Diet = Text("diet"), AverageSize = Text("size"), Description = Text("facts"), ConservationStatus = Text("conservation_status"), SourceUrl = sources.FirstOrDefault() ?? "", SourcesJson = JsonSerializer.Serialize(sources) };
    }

    public async Task SeedAsync(CancellationToken token = default)
    {
        var path = Path.GetFullPath(configuration["CatalogPath"] ?? "../data/birds.json", environment.ContentRootPath);
        using var catalog = JsonDocument.Parse(await File.ReadAllTextAsync(path, token));
        var existing = (await db.Birds.Select(b => b.ScientificName).ToListAsync(token)).ToHashSet(StringComparer.OrdinalIgnoreCase);
        foreach (var entry in catalog.RootElement.EnumerateObject())
        {
            var bird = ParseBird(entry.Value);
            if (!string.IsNullOrWhiteSpace(bird.ScientificName) && existing.Add(bird.ScientificName)) db.Birds.Add(bird);
        }
        await db.SaveChangesAsync(token);
    }
}
