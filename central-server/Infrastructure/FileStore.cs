using System.Security.Cryptography;

namespace BirdLab.Api.Infrastructure;

public sealed record StoredUpload(string Key, string Hash, string OriginalName);

public sealed class FileStore
{
    public string Root { get; }
    public FileStore(IConfiguration configuration, IWebHostEnvironment environment)
    {
        Root = Path.GetFullPath(configuration["Storage:Root"] ?? "storage", environment.ContentRootPath);
        Directory.CreateDirectory(Root);
    }

    public static string CleanName(string name) => Path.GetFileName(name.Replace('\\', '/'));
    public static void Validate(string name, long length, string kind)
    {
        var ext = Path.GetExtension(name).ToLowerInvariant();
        var allowed = kind == "image" ? new[] { ".jpg", ".jpeg", ".png" } : new[] { ".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg" };
        if (!allowed.Contains(ext)) throw new ApiException(422, kind == "image" ? "Виберіть JPG, JPEG або PNG." : "Виберіть WAV, MP3, FLAC, M4A, AAC або OGG.");
        if (length <= 0 || length > (kind == "image" ? 20L : 50L) * 1024 * 1024) throw new ApiException(413, "Файл порожній або перевищує ліміт: фото 20 МБ, аудіо 50 МБ.");
        if (CleanName(name).Length > 255) throw new ApiException(422, "Назва файлу задовга.");
    }

    public string Resolve(string key)
    {
        if (string.IsNullOrWhiteSpace(key) || key != Path.GetFileName(key) || key.Contains('\\') || key.Contains('/') || key.Contains(':')) throw new ApiException(400, "Некоректний шлях файлу.");
        var path = Path.GetFullPath(Path.Combine(Root, key));
        if (!path.StartsWith(Root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new ApiException(400, "Некоректний шлях файлу.");
        return path;
    }

    public async Task<StoredUpload> SaveAsync(Stream stream, string name, string kind, long length, CancellationToken token)
    {
        Validate(name, length, kind);
        var key = Guid.NewGuid().ToString("N") + Path.GetExtension(name).ToLowerInvariant();
        var path = Resolve(key);
        try
        {
            await using (var output = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None, 81920, true))
            {
                var buffer = new byte[81920];
                long written = 0;
                int count;
                while ((count = await stream.ReadAsync(buffer, token)) > 0)
                {
                    written += count;
                    Validate(name, written, kind);
                    await output.WriteAsync(buffer.AsMemory(0, count), token);
                }
                if (written != length) throw new ApiException(422, "Розмір переданого файлу змінився.");
            }
            await using var saved = File.OpenRead(path);
            var hash = Convert.ToHexString(await SHA256.HashDataAsync(saved, token)).ToLowerInvariant();
            return new(key, hash, CleanName(name));
        }
        catch { File.Delete(path); throw; }
    }

    public void Remove(string key) => File.Delete(Resolve(key));
    public static string ContentType(string path) => Path.GetExtension(path).ToLowerInvariant() switch { ".png" => "image/png", ".jpg" or ".jpeg" => "image/jpeg", ".wav" => "audio/wav", ".mp3" => "audio/mpeg", ".flac" => "audio/flac", ".m4a" => "audio/mp4", ".aac" => "audio/aac", ".ogg" => "audio/ogg", _ => "application/octet-stream" };
}
