using System.Security.Claims;
using BirdLab.Api.Auth;
using BirdLab.Api.Data;
using BirdLab.Api.Models;
using BirdLab.Api.Services;
using BirdLab.Api.Subscriptions;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;

namespace BirdLab.Api.Tests;

public static class TestAccount
{
    private sealed class TestAccessor : IHttpContextAccessor { public HttpContext? HttpContext { get; set; } }
    public const string UserId = "unit-user";
    public static CurrentUser Current(string id = UserId) => new(new TestAccessor { HttpContext = new DefaultHttpContext { User = new ClaimsPrincipal(new ClaimsIdentity([new Claim(ClaimTypes.NameIdentifier, id)], "unit")) } });
    public static async Task<AnalysisService> Analyses(BirdDbContext db, IAiClient ai, Infrastructure.FileStore files)
    {
        if (!await db.Users.AnyAsync(u => u.Id == UserId)) { db.Users.Add(new ApplicationUser { Id = UserId, UserName = "unit@example.test", Email = "unit@example.test" }); await db.SaveChangesAsync(); }
        if (!await db.SubscriptionPlans.AnyAsync()) { await db.Database.EnsureCreatedAsync(); }
        if (!await db.SubscriptionPlans.AnyAsync(p => p.Id == 0)) { db.SubscriptionPlans.Add(new SubscriptionPlan { Id = 0, Name = "FREE", AnalysisLimit = 5, DurationDays = 1, Features = "[\"image\",\"history\",\"basicInfo\"]" }); await db.SaveChangesAsync(); }
        return new AnalysisService(db, ai, files, Current(), new SubscriptionService(db));
    }
}
