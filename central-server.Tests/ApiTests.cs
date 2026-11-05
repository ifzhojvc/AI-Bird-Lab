using System.Net;
using System.Text;
using System.Text.Json;
using BirdLab.Api.Data;
using BirdLab.Api.DTOs;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Models;
using BirdLab.Api.Services;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.FileProviders;
using Xunit;

namespace BirdLab.Api.Tests;

public sealed class TestEnvironment : IWebHostEnvironment
{
    public string ApplicationName { get; set; } = "BirdLab.Api.Tests";
    public IFileProvider WebRootFileProvider { get; set; } = new NullFileProvider();
    public string WebRootPath { get; set; } = "";
    public string EnvironmentName { get; set; } = "Development";
    public string ContentRootPath { get; set; } = AppContext.BaseDirectory;
    public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
}

public sealed class TestFiles : IDisposable
{
    public string Folder { get; } = Path.Combine(Path.GetTempPath(), "birdlab-tests-" + Guid.NewGuid().ToString("N"));
    public FileStore Store { get; }
    public TestFiles() => Store = new FileStore(new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?> { ["Storage:Root"] = Folder }).Build(), new TestEnvironment());
    public void Dispose()
    {
        if (!Folder.StartsWith(Path.GetTempPath(), StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException();
        Directory.Delete(Folder, true);
    }
}

public sealed class FileAndCsvTests
{
    [Theory]
    [InlineData("../../birds.db")]
    [InlineData("..\\birds.db")]
    [InlineData("C:\\secret.txt")]
    [InlineData("nested/file.jpg")]
    public void RejectsTraversal(string key)
    {
        using var files = new TestFiles();
        Assert.Throws<ApiException>(() => files.Store.Resolve(key));
    }

    [Theory]
    [InlineData("bird.exe", 3, "image")]
    [InlineData("bird.jpg", 0, "image")]
    [InlineData("bird.jpg", 21000000, "image")]
    public void ValidatesTypeAndLength(string name, long length, string kind) => Assert.Throws<ApiException>(() => FileStore.Validate(name, length, kind));

    [Fact]
    public async Task GeneratedFileNameDoesNotContainUserPath()
    {
        using var files = new TestFiles();
        await using var content = new MemoryStream([1, 2, 3]);
        var stored = await files.Store.SaveAsync(content, "../../птах.jpg", "image", 3, default);
        Assert.Equal("птах.jpg", stored.OriginalName);
        Assert.Matches("^[0-9a-f]{32}\\.jpg$", stored.Key);
        Assert.Equal(64, stored.Hash.Length);
        Assert.True(File.Exists(files.Store.Resolve(stored.Key)));
    }

    [Fact]
    public async Task IncompleteUploadLeavesNoFile()
    {
        using var files = new TestFiles();
        await Assert.ThrowsAsync<ApiException>(() => files.Store.SaveAsync(new MemoryStream([1, 2]), "bird.jpg", "image", 3, default));
        Assert.Empty(Directory.GetFiles(files.Folder));
    }

    [Fact]
    public void CsvHasBomEscapesQuotesAndFormula()
    {
        var bytes = CsvExport.Build([new Analysis { Id = 1, OriginalFileName = "=HYPERLINK(\"x\")", PredictedSpecies = "Кардинал, червоний", Confidence = .8, AnalysisDate = DateTimeOffset.Parse("2026-10-16T10:00:00Z") }]);
        Assert.True(bytes.Take(3).SequenceEqual(new byte[] { 239, 187, 191 }));
        var text = Encoding.UTF8.GetString(bytes);
        Assert.Contains("\"'=HYPERLINK(\"\"x\"\")\"", text);
        Assert.Contains("\"Кардинал, червоний\"", text);
        Assert.Contains("0.8", text);
    }

    [Fact]
    public void MigrationSnapshotMatchesCurrentModel()
    {
        using var db = new BirdDbContext(new DbContextOptionsBuilder<BirdDbContext>().UseSqlServer("Server=unused;Database=unused;Integrated Security=true").Options);
        Assert.Equal(3, db.Database.GetMigrations().Count());
        Assert.False(db.Database.HasPendingModelChanges());
        var sql = db.Database.GenerateCreateScript();
        Assert.Contains("CK_Analysis_Confidence", sql);
        Assert.Contains("ON DELETE CASCADE", sql);
        Assert.Contains("LegacySource", sql);
    }
}

public sealed class ResponseHandler(HttpResponseMessage? response = null, Exception? error = null) : HttpMessageHandler
{
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) => error is null ? Task.FromResult(response!) : Task.FromException<HttpResponseMessage>(error);
}

public sealed class AiClientTests
{
    private static AiClient Client(HttpMessageHandler handler) => new(new HttpClient(handler) { BaseAddress = new Uri("http://unit-test/") });
    [Theory]
    [InlineData(422, 422)]
    [InlineData(503, 502)]
    public async Task UpstreamErrorsAreVisibleAndNeverPredictions(int upstream, int expected)
    {
        var client = Client(new ResponseHandler(new HttpResponseMessage((HttpStatusCode)upstream) { Content = new StringContent("{\"message\":\"Перевірте файл\"}") }));
        var error = await Assert.ThrowsAsync<ApiException>(() => client.PredictAsync(new MemoryStream([1]), "bird.jpg", "image", default));
        Assert.Equal(expected, error.Status);
        Assert.Equal("Перевірте файл", error.Message);
    }

    [Fact]
    public async Task TimeoutBecomes504()
    {
        var error = await Assert.ThrowsAsync<ApiException>(() => Client(new ResponseHandler(error: new TaskCanceledException())).PredictAsync(new MemoryStream([1]), "bird.jpg", "image", default));
        Assert.Equal(504, error.Status);
    }

    [Fact]
    public async Task RejectsMalformedModelJson()
    {
        var client = Client(new ResponseHandler(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("{}", Encoding.UTF8, "application/json") }));
        var error = await Assert.ThrowsAsync<ApiException>(() => client.PredictAsync(new MemoryStream([1]), "bird.jpg", "image", default));
        Assert.Equal(502, error.Status);
    }

    [Theory]
    [InlineData(true, false, false)]
    [InlineData(false, true, false)]
    [InlineData(false, false, true)]
    public async Task RejectsMockDuplicatesAndMissingMetadata(bool mockUsed, bool duplicateRanks, bool missingMetadata)
    {
        var payload = new Dictionary<string, object?>
        {
            ["analysis_type"] = "image", ["model_id"] = "unit-test-model", ["model_revision"] = "unit", ["elapsed_seconds"] = .1,
            ["predictions"] = new[] {
                new { species_name = "first", scientific_name = (string?)null, confidence = .8, rank = 1 },
                new { species_name = "second", scientific_name = (string?)null, confidence = .15, rank = duplicateRanks ? 1 : 2 },
                new { species_name = "third", scientific_name = (string?)null, confidence = .05, rank = 3 }
            }
        };
        if (!missingMetadata) payload["metadata"] = new { mock_used = mockUsed };
        var client = Client(new ResponseHandler(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json") }));
        var error = await Assert.ThrowsAsync<ApiException>(() => client.PredictAsync(new MemoryStream([1]), "bird.jpg", "image", default));
        Assert.Equal(502, error.Status);
    }
}

public sealed class UnitAiClient(bool fail = false) : IAiClient
{
    public Task<AiResult> PredictAsync(Stream stream, string name, string kind, CancellationToken token)
    {
        if (fail) throw new ApiException(502, "Unit test upstream failure");
        return Task.FromResult(new AiResult(kind, "unit-test-model", "test", .1, [new("Cardinal", "Cardinalis cardinalis", .8, 1), new("Blue Jay", null, .15, 2), new("Mallard", null, .05, 3)], JsonDocument.Parse("{\"mock_used\":true}").RootElement.Clone()));
    }
}

public sealed class AnalysisServiceTests
{
    [Fact]
    public async Task UnitSaveHistorySearchAndDelete()
    {
        using var files = new TestFiles();
        await using var db = new BirdDbContext(new DbContextOptionsBuilder<BirdDbContext>().UseInMemoryDatabase(Guid.NewGuid().ToString()).Options);
        db.Birds.Add(new Bird { ScientificName = "Cardinalis cardinalis", UkrainianName = "кардинал червоний" });
        await db.SaveChangesAsync();
        var service = await TestAccount.Analyses(db, new UnitAiClient(), files.Store);
        var saved = await service.AnalyzeAsync(new FormFile(new MemoryStream([1, 2, 3]), 0, 3, "file", "bird.jpg"), "image", default);
        Assert.Equal(3, saved.Predictions.Length);
        Assert.NotNull(saved.Bird);
        var history = await service.HistoryAsync(1, 20, "кардинал", "image", "date_desc", default);
        Assert.Single(history.Items);
        await service.DeleteAsync(saved.Id, default);
        Assert.Empty(await db.Analyses.ToListAsync());
        Assert.Empty(Directory.GetFiles(files.Folder));
    }

    [Fact]
    public async Task UnitAiFailureDoesNotSaveHistoryOrFile()
    {
        using var files = new TestFiles();
        await using var db = new BirdDbContext(new DbContextOptionsBuilder<BirdDbContext>().UseInMemoryDatabase(Guid.NewGuid().ToString()).Options);
        var service = await TestAccount.Analyses(db, new UnitAiClient(true), files.Store);
        await Assert.ThrowsAsync<ApiException>(() => service.AnalyzeAsync(new FormFile(new MemoryStream([1]), 0, 1, "file", "bird.jpg"), "image", default));
        Assert.Empty(await db.Analyses.ToListAsync());
        Assert.Empty(Directory.GetFiles(files.Folder));
    }
}
