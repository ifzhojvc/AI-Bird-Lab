using BirdLab.Api.Data;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Services;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.EntityFrameworkCore;
using BirdLab.Api.Messaging;
using BirdLab.Api.Auth;
using BirdLab.Api.Models;
using BirdLab.Api.Subscriptions;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using System.Threading.RateLimiting;

if (args.Contains("--healthcheck"))
{
    try
    {
        using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(12) };
        using var response = await client.GetAsync("http://127.0.0.1:5100/api/health");
        Environment.ExitCode = response.IsSuccessStatusCode ? 0 : 1;
    }
    catch { Environment.ExitCode = 1; }
    return;
}

var maintenance = args.Any(a => a is "--migrate-db" or "--import-sqlite" or "--seed-catalog");
var builder = WebApplication.CreateBuilder(maintenance ? [] : args);
builder.Services.AddDbContext<BirdDbContext>(options => options.UseSqlServer(builder.Configuration.GetConnectionString("BirdLab") ?? throw new InvalidOperationException("ConnectionStrings:BirdLab is required.")));
builder.Services.AddControllers();
builder.Services.AddHttpContextAccessor();
builder.Services.AddScoped<CurrentUser>();
builder.Services.AddIdentityCore<ApplicationUser>(options =>
{
    options.User.RequireUniqueEmail = true;
    options.Password.RequiredLength = 12;
    options.Password.RequireNonAlphanumeric = true;
    options.Lockout.MaxFailedAccessAttempts = 5;
    options.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(15);
}).AddEntityFrameworkStores<BirdDbContext>().AddSignInManager();
builder.Services.AddAuthentication(SessionAuthentication.SchemeName).AddScheme<AuthenticationSchemeOptions, SessionAuthentication>(SessionAuthentication.SchemeName, _ => { });
builder.Services.AddAuthorization(options =>
{
    options.FallbackPolicy = new AuthorizationPolicyBuilder().RequireAuthenticatedUser().Build();
    options.AddPolicy("LegacyArchive", policy => policy.RequireAssertion(context => (builder.Configuration.GetSection("Auth:LegacyArchiveReaders").Get<string[]>() ?? []).Contains(context.User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value)));
});
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = 429;
    foreach (var name in new[] { "auth", "payments" })
        options.AddPolicy(name, context => RateLimitPartition.GetFixedWindowLimiter(context.Connection.RemoteIpAddress?.ToString() ?? "unknown", _ => new FixedWindowRateLimiterOptions { PermitLimit = name == "auth" ? 15 : 30, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
});
builder.Services.Configure<BlockchainOptions>(builder.Configuration.GetSection("Blockchain"));
builder.Services.AddScoped<WalletService>();
builder.Services.AddScoped<SubscriptionService>();
builder.Services.AddScoped<PaymentService>();
builder.Services.AddSingleton<IBlockchainVerifier, BlockchainVerifier>();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.AddSecurityDefinition("Bearer", new Microsoft.OpenApi.OpenApiSecurityScheme { Type = Microsoft.OpenApi.SecuritySchemeType.Http, Scheme = "bearer", BearerFormat = "opaque", Description = "Сесійний токен із POST /api/auth/login з useBearerToken=true." });
    options.AddSecurityRequirement(document => new Microsoft.OpenApi.OpenApiSecurityRequirement { [new Microsoft.OpenApi.OpenApiSecuritySchemeReference("Bearer", document)] = [] });
});
builder.Services.AddProblemDetails();
builder.Services.AddExceptionHandler<ApiExceptionHandler>();
builder.Services.Configure<FormOptions>(options => options.MultipartBodyLengthLimit = 320L * 1024 * 1024);
builder.WebHost.ConfigureKestrel(options => options.Limits.MaxRequestBodySize = 320L * 1024 * 1024);
builder.Services.AddCors(options => options.AddDefaultPolicy(policy => policy.WithOrigins(builder.Configuration.GetSection("Cors:Origins").Get<string[]>() ?? ["http://localhost:5173"]).AllowAnyHeader().AllowAnyMethod().AllowCredentials().WithExposedHeaders("Content-Disposition")));
void ConfigureAi(HttpClient client)
{
    client.BaseAddress = new Uri((builder.Configuration["AiServer:BaseUrl"] ?? "http://127.0.0.1:8000").TrimEnd('/') + "/");
    client.Timeout = TimeSpan.FromSeconds(builder.Configuration.GetValue("AiServer:TimeoutSeconds", 180));
    var key = builder.Configuration["AiServer:InternalKey"];
    if (!string.IsNullOrEmpty(key)) client.DefaultRequestHeaders.Add("X-AI-Key", key);
}
builder.Services.AddHttpClient<IAiClient, AiClient>(ConfigureAi);
builder.Services.AddHttpClient("ai-health", ConfigureAi);
builder.Services.AddSingleton<FileStore>();
builder.Services.AddScoped<AnalysisService>();
builder.Services.AddScoped<StatisticsService>();
builder.Services.AddScoped<CatalogSeeder>();
builder.Services.AddScoped<LegacyImporter>();
builder.Services.AddSingleton<RabbitBus>();
builder.Services.AddSingleton<IEventPublisher>(sp => sp.GetRequiredService<RabbitBus>());
builder.Services.AddScoped<ResultProcessor>();
builder.Services.AddSingleton<ResultConsumer>();
if (!maintenance)
{
    builder.Services.AddHostedService<OutboxDispatcher>();
    builder.Services.AddHostedService(sp => sp.GetRequiredService<ResultConsumer>());
    builder.Services.AddHostedService<StalledJobMonitor>();
    builder.Services.AddHostedService<SubscriptionMonitor>();
}
var app = builder.Build();
if (args.Contains("--migrate-db") || args.Contains("--import-sqlite") || args.Contains("--seed-catalog"))
{
    using var scope = app.Services.CreateScope();
    var db = scope.ServiceProvider.GetRequiredService<BirdDbContext>();
    await db.Database.MigrateAsync();
    await scope.ServiceProvider.GetRequiredService<CatalogSeeder>().SeedAsync();
    var importIndex = Array.IndexOf(args, "--import-sqlite");
    if (importIndex >= 0)
    {
        if (importIndex + 1 >= args.Length) throw new InvalidOperationException("Specify the SQLite path after --import-sqlite.");
        var result = await scope.ServiceProvider.GetRequiredService<LegacyImporter>().ImportAsync(args[importIndex + 1]);
        Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(result));
    }
    return;
}
app.UseExceptionHandler();
app.UseCors();
app.UseSwagger();
app.UseSwaggerUI();
app.Use(async (context, next) =>
{
    if (context.Request.Method is not ("GET" or "HEAD" or "OPTIONS") && context.Request.Headers.TryGetValue("Origin", out var origin))
    {
        var allowed = builder.Configuration.GetSection("Cors:Origins").Get<string[]>() ?? ["http://localhost:5173"];
        if (!allowed.Contains(origin.ToString(), StringComparer.OrdinalIgnoreCase))
        {
            context.Response.StatusCode = 403;
            await context.Response.WriteAsJsonAsync(new { detail = "Домен запиту не дозволений." });
            return;
        }
    }
    await next(context);
});
app.UseAuthentication();
app.UseAuthorization();
app.UseRateLimiter();
app.MapControllers();
app.MapGet("/api/health/live", () => Results.Ok(new { status = "ok", central = true })).AllowAnonymous();
app.Run();

public partial class Program;
