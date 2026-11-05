using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using BirdLab.Api.Data;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Models;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;

namespace BirdLab.Api.Services;

public sealed class LegacyImporter(BirdDbContext db, FileStore files, CatalogSeeder catalog, ILogger<LegacyImporter> logger)
{
    public async Task<object> ImportAsync(string sourcePath, CancellationToken token = default)
    {
        sourcePath = Path.GetFullPath(sourcePath);
        if (!File.Exists(sourcePath)) throw new InvalidOperationException("Вихідну SQLite-базу не знайдено.");
        var sourceRoot = Path.GetDirectoryName(sourcePath)!;
        var backup = Path.Combine(sourceRoot, "data", "backups", "migration-" + DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffffffZ"));
        Directory.CreateDirectory(backup);
        var backupDb = Path.Combine(backup, "birds.db");
        using (var original = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = sourcePath, Mode = SqliteOpenMode.ReadOnly }.ToString()))
        using (var copy = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = backupDb }.ToString()))
        {
            await original.OpenAsync(token);
            await copy.OpenAsync(token);
            original.BackupDatabase(copy);
        }
        if (File.Exists(Path.Combine(sourceRoot, "bird_analysis.csv"))) File.Copy(Path.Combine(sourceRoot, "bird_analysis.csv"), Path.Combine(backup, "bird_analysis.csv"));
        using var source = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = backupDb, Mode = SqliteOpenMode.ReadOnly }.ToString());
        await source.OpenAsync(token);
        var sourceId = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(sourcePath.ToUpperInvariant()))).ToLowerInvariant();
        var legacy = new List<Dictionary<string, object>>();
        using (var command = source.CreateCommand())
        {
            command.CommandText = "SELECT * FROM analyses ORDER BY id";
            using var reader = await command.ExecuteReaderAsync(token);
            while (await reader.ReadAsync(token)) legacy.Add(Enumerable.Range(0, reader.FieldCount).ToDictionary(reader.GetName, reader.GetValue));
        }
        var expectedPredictions = 0;
        var expectedEvaluations = 0;
        using (var count = source.CreateCommand())
        {
            count.CommandText = "SELECT COUNT(*) FROM predictions";
            expectedPredictions = Convert.ToInt32(await count.ExecuteScalarAsync(token));
            count.CommandText = "SELECT COUNT(*) FROM evaluations";
            expectedEvaluations = Convert.ToInt32(await count.ExecuteScalarAsync(token));
        }
        var manifest = new Dictionary<string, string>();
        foreach (var row in legacy)
        {
            var relative = Convert.ToString(row["file_path"], CultureInfo.InvariantCulture)!;
            var path = Path.GetFullPath(relative, sourceRoot);
            var uploadRoot = Path.Combine(sourceRoot, "uploads") + Path.DirectorySeparatorChar;
            if (!path.StartsWith(uploadRoot, StringComparison.OrdinalIgnoreCase) || !File.Exists(path)) throw new InvalidOperationException($"Файл відсутній або шлях небезпечний: {relative}");
            await using var content = File.OpenRead(path);
            var hash = Convert.ToHexString(await SHA256.HashDataAsync(content, token)).ToLowerInvariant();
            if (hash != Convert.ToString(row["file_hash"], CultureInfo.InvariantCulture)) throw new InvalidOperationException($"SHA-256 не збігається: {relative}");
            var target = Path.GetFullPath(relative, backup);
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            File.Copy(path, target, true);
            manifest[relative] = hash;
        }
        await File.WriteAllTextAsync(Path.Combine(backup, "manifest.json"), JsonSerializer.Serialize(new { source = sourcePath, sourceId, analyses = legacy.Count, predictions = expectedPredictions, evaluations = expectedEvaluations, files = manifest }, new JsonSerializerOptions { WriteIndented = true }), token);
        await catalog.SeedAsync(token);
        var copiedKeys = new List<string>();
        var added = 0;
        var skipped = 0;
        await using var transaction = await db.Database.BeginTransactionAsync(token);
        try
        {
            using (var command = source.CreateCommand())
            {
                command.CommandText = "SELECT payload FROM bird_info";
                using var reader = await command.ExecuteReaderAsync(token);
                while (await reader.ReadAsync(token))
                {
                    using var payload = JsonDocument.Parse(reader.GetString(0));
                    var bird = CatalogSeeder.ParseBird(payload.RootElement);
                    if (!string.IsNullOrWhiteSpace(bird.ScientificName) && !await db.Birds.AnyAsync(b => b.ScientificName == bird.ScientificName, token)) { db.Birds.Add(bird); await db.SaveChangesAsync(token); }
                }
            }
            foreach (var row in legacy)
            {
                var oldId = Convert.ToInt32(row["id"]);
                if (await db.Analyses.AnyAsync(a => a.LegacySource == sourceId && a.LegacyId == oldId, token)) { skipped++; continue; }
                string Text(string key) => row[key] is DBNull ? "" : Convert.ToString(row[key], CultureInfo.InvariantCulture) ?? "";
                var kind = Text("analysis_type");
                var fromBackup = Path.GetFullPath(Text("file_path"), backup);
                await using var content = File.OpenRead(fromBackup);
                var stored = await files.SaveAsync(content, Text("original_name"), kind, content.Length, token);
                copiedKeys.Add(stored.Key);
                var scientific = Text("scientific_name");
                var analysis = new Analysis
                {
                    LegacySource = sourceId, LegacyId = oldId, AnalysisType = kind, OriginalFileName = stored.OriginalName, StoredFilePath = stored.Key,
                    FileHash = stored.Hash, PredictedSpecies = Text("predicted_species"), Confidence = Convert.ToDouble(row["confidence"]),
                    ModelName = Text("model_id"), ModelRevision = Text("model_revision"), AnalysisDate = DateTimeOffset.Parse(Text("analysis_date"), CultureInfo.InvariantCulture),
                    Description = Text("description"), ElapsedSeconds = Convert.ToDouble(row["elapsed_seconds"]), MetadataJson = Text("metadata"), BirdSnapshotJson = Text("bird_snapshot"),
                    Bird = await db.Birds.SingleOrDefaultAsync(b => b.ScientificName == scientific, token)
                };
                analysis.FileId = Guid.ParseExact(Path.GetFileNameWithoutExtension(stored.Key), "N");
                analysis.CreatedAt = analysis.AnalysisDate;
                analysis.StartedAt = analysis.AnalysisDate;
                analysis.CompletedAt = analysis.AnalysisDate;
                analysis.UpdatedAt = analysis.AnalysisDate;
                using (var command = source.CreateCommand())
                {
                    command.CommandText = "SELECT label, scientific_name, score, rank FROM predictions WHERE analysis_id=$id ORDER BY rank";
                    command.Parameters.AddWithValue("$id", oldId);
                    using var reader = await command.ExecuteReaderAsync(token);
                    while (await reader.ReadAsync(token)) analysis.Predictions.Add(new Prediction { SpeciesName = reader.GetString(0), ScientificName = reader.IsDBNull(1) ? null : reader.GetString(1), Confidence = reader.GetDouble(2), Rank = reader.GetInt32(3) });
                }
                using (var command = source.CreateCommand())
                {
                    command.CommandText = "SELECT * FROM evaluations WHERE analysis_id=$id";
                    command.Parameters.AddWithValue("$id", oldId);
                    using var reader = await command.ExecuteReaderAsync(token);
                    if (await reader.ReadAsync(token)) analysis.Evaluation = new Evaluation { ExpectedLabel = reader.GetString(reader.GetOrdinal("expected_label")), ExpectedScientific = reader.GetString(reader.GetOrdinal("expected_scientific")), LabelSource = reader.GetString(reader.GetOrdinal("label_source")), FileHash = reader.GetString(reader.GetOrdinal("file_hash")), Top1Correct = reader.GetBoolean(reader.GetOrdinal("top1_correct")), Top3Correct = reader.GetBoolean(reader.GetOrdinal("top3_correct")), Experiment = reader.GetString(reader.GetOrdinal("experiment")) };
                }
                db.Analyses.Add(analysis);
                await db.SaveChangesAsync(token);
                added++;
            }
            var migrated = await db.Analyses.CountAsync(a => a.LegacySource == sourceId, token);
            var predictions = await db.Predictions.CountAsync(p => p.Analysis.LegacySource == sourceId, token);
            var evaluations = await db.Evaluations.CountAsync(e => e.Analysis.LegacySource == sourceId, token);
            if (migrated != legacy.Count || predictions != expectedPredictions || evaluations != expectedEvaluations) throw new InvalidOperationException("Кількість перенесених записів не збігається з SQLite. Транзакцію скасовано.");
            await transaction.CommitAsync(token);
            var report = new { backup, sourceId, sourceAnalyses = legacy.Count, added, skipped, migratedAnalyses = migrated, predictions, evaluations, verified = true };
            try { await File.WriteAllTextAsync(Path.Combine(backup, "result.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }), CancellationToken.None); }
            catch (Exception exc) when (exc is IOException or UnauthorizedAccessException) { logger.LogWarning(exc, "Migration committed; could not write result.json at {Backup}", backup); }
            logger.LogInformation("SQLite migration complete: {Added} added, {Skipped} skipped, {Total} verified", added, skipped, migrated);
            return report;
        }
        catch
        {
            await transaction.RollbackAsync(CancellationToken.None);
            foreach (var key in copiedKeys) files.Remove(key);
            throw;
        }
    }
}
