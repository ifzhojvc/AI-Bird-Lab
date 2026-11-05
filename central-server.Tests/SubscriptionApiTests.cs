using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using BirdLab.Api.Data;
using BirdLab.Api.Models;
using BirdLab.Api.Subscriptions;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Xunit;

namespace BirdLab.Api.Tests;

public sealed class SubscriptionApiFactory(string? connection = null) : WebApplicationFactory<Program>
{
    private readonly string name = Guid.NewGuid().ToString();
    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Development");
        builder.ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(new Dictionary<string, string?> { ["Blockchain:Enabled"] = "false" }));
        builder.ConfigureServices(services =>
        {
            services.RemoveAll<BirdDbContext>();
            services.RemoveAll<DbContextOptions<BirdDbContext>>();
            services.RemoveAll<IDbContextOptionsConfiguration<BirdDbContext>>();
            services.AddDbContext<BirdDbContext>(options => { if (connection is null) options.UseInMemoryDatabase(name); else options.UseSqlServer(connection); });
            services.RemoveAll<IHostedService>();
        });
    }
    public async Task<HttpClient> Client()
    {
        var client = CreateClient(new WebApplicationFactoryClientOptions { BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false });
        using var scope = Services.CreateScope();
        await scope.ServiceProvider.GetRequiredService<BirdDbContext>().Database.EnsureCreatedAsync();
        return client;
    }
}

public sealed class SubscriptionApiTests
{
    private const string Password = "Bird-Lab!Test2026";
    private static async Task<JsonElement> Register(HttpClient client, string email, bool bearer = false)
    {
        var response = await client.PostAsJsonAsync("/api/auth/register", new { email, password = Password, useBearerToken = bearer });
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        return (await response.Content.ReadFromJsonAsync<JsonElement>()).Clone();
    }

    [Fact]
    public async Task RegistrationCookieLoginProfileAndLogoutAreRealIdentityFlows()
    {
        await using var factory = new SubscriptionApiFactory();
        using var client = await factory.Client();
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/subscriptions/me")).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/api/subscriptions/plans")).StatusCode);
        var registered = await Register(client, "identity@example.test");
        Assert.Equal(JsonValueKind.Null, registered.GetProperty("accessToken").ValueKind);
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/api/auth/me")).StatusCode);
        var access = await client.GetFromJsonAsync<JsonElement>("/api/subscriptions/me");
        Assert.Equal("FREE", access.GetProperty("plan").GetString());
        Assert.Equal(5, access.GetProperty("remaining").GetInt32());
        var summary = await client.GetFromJsonAsync<JsonElement>("/api/statistics/summary");
        Assert.Equal(JsonValueKind.Null, summary.GetProperty("averageConfidence").ValueKind);
        using (var scope = factory.Services.CreateScope())
        {
            var user = await scope.ServiceProvider.GetRequiredService<BirdDbContext>().Users.SingleAsync();
            Assert.NotEqual(Password, user.PasswordHash);
            Assert.NotNull(user.PasswordHash);
        }
        Assert.Equal(HttpStatusCode.NoContent, (await client.PostAsync("/api/auth/logout", null)).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/auth/me")).StatusCode);
        var login = await client.PostAsJsonAsync("/api/auth/login", new { email = "identity@example.test", password = Password });
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/api/auth/me")).StatusCode);
    }

    [Fact]
    public async Task BearerSessionIsRevokedOnLogoutAndForeignOriginCannotRegister()
    {
        await using var factory = new SubscriptionApiFactory();
        using var client = await factory.Client();
        var session = await Register(client, "mobile@example.test", true);
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", session.GetProperty("accessToken").GetString());
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/api/auth/me")).StatusCode);
        await client.PostAsync("/api/auth/logout", null);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/auth/me")).StatusCode);
        client.DefaultRequestHeaders.Authorization = null;
        client.DefaultRequestHeaders.Add("Origin", "https://evil.example");
        Assert.Equal(HttpStatusCode.Forbidden, (await client.PostAsJsonAsync("/api/auth/register", new { email = "csrf@example.test", password = Password })).StatusCode);
    }

    [Fact]
    public async Task WrongPasswordLocksAccountAndDuplicateRegistrationFails()
    {
        await using var factory = new SubscriptionApiFactory();
        using var client = await factory.Client();
        await Register(client, "lockout@example.test");
        await client.PostAsync("/api/auth/logout", null);
        for (var i = 0; i < 5; i++) Assert.Equal(HttpStatusCode.Unauthorized, (await client.PostAsJsonAsync("/api/auth/login", new { email = "lockout@example.test", password = "Wrong-Password!123" })).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.PostAsJsonAsync("/api/auth/login", new { email = "lockout@example.test", password = Password })).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync("/api/auth/register", new { email = "lockout@example.test", password = Password })).StatusCode);
    }

    [Fact]
    public async Task FreeCannotBypassPaidRoutesAndCannotReadLegacyOrAnotherUsersMedia()
    {
        await using var factory = new SubscriptionApiFactory();
        using var client = await factory.Client();
        await Register(client, "private@example.test");
        int id;
        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<BirdDbContext>();
            db.Analyses.Add(new Analysis { StoredFilePath = "legacy.jpg", PredictedSpecies = "Preserved legacy" });
            db.Users.Add(new ApplicationUser { Id = "other-user", UserName = "other" });
            var other = new Analysis { UserId = "other-user", StoredFilePath = "other.jpg" }; db.Analyses.Add(other);
            await db.SaveChangesAsync(); id = other.Id;
        }
        Assert.Equal(HttpStatusCode.Forbidden, (await client.GetAsync("/api/legacy/archive")).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await client.GetAsync($"/api/analyses/{id}")).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await client.GetAsync($"/api/analyses/{id}/file")).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await client.DeleteAsync($"/api/analyses/{id}")).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await client.GetAsync("/api/analyses/gallery")).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await client.GetAsync("/api/birds/compare?firstId=1&secondId=2")).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await client.GetAsync("/api/statistics/species")).StatusCode);
        var history = await client.GetFromJsonAsync<JsonElement>("/api/analyses");
        Assert.Equal(0, history.GetProperty("total").GetInt32());
        Assert.Equal(HttpStatusCode.ServiceUnavailable, (await client.PostAsJsonAsync("/api/subscriptions/orders", new { planId = 1, walletAddress = "0x3333333333333333333333333333333333333333", amount = 1 })).StatusCode);
        var swagger = await client.GetFromJsonAsync<JsonElement>("/swagger/v1/swagger.json");
        Assert.True(swagger.GetProperty("paths").TryGetProperty("/api/subscriptions/payments/verify", out _));
    }
}
