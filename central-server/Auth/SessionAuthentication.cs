using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using BirdLab.Api.Data;
using BirdLab.Api.Infrastructure;
using Microsoft.AspNetCore.Authentication;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace BirdLab.Api.Auth;

public sealed class CurrentUser(IHttpContextAccessor accessor)
{
    public string Id => accessor.HttpContext?.User.FindFirstValue(ClaimTypes.NameIdentifier) ?? throw new ApiException(401, "Увійдіть до облікового запису.");
}

public sealed class SessionAuthentication(IOptionsMonitor<AuthenticationSchemeOptions> options, ILoggerFactory logger, UrlEncoder encoder, BirdDbContext db) : AuthenticationHandler<AuthenticationSchemeOptions>(options, logger, encoder)
{
    public const string SchemeName = "BirdSession";
    public const string CookieName = "birdlab_session";
    public static string Hash(string value) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    public static string? ReadToken(HttpRequest request)
    {
        var header = request.Headers.Authorization.ToString();
        return header.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase) ? header[7..] : request.Cookies[CookieName];
    }

    protected override async Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var value = ReadToken(Request);
        if (string.IsNullOrEmpty(value)) return AuthenticateResult.NoResult();
        if (value.Length != 64) return AuthenticateResult.Fail("Invalid session.");
        var id = Hash(value);
        var session = await db.AuthSessions.AsNoTracking().SingleOrDefaultAsync(s => s.Id == id && s.ExpiresAt > DateTimeOffset.UtcNow, Context.RequestAborted);
        if (session is null) return AuthenticateResult.Fail("Expired session.");
        var user = await db.Users.AsNoTracking().SingleOrDefaultAsync(u => u.Id == session.UserId, Context.RequestAborted);
        if (user is null || user.LockoutEnd > DateTimeOffset.UtcNow) return AuthenticateResult.Fail("Invalid account.");
        var claims = new[] { new Claim(ClaimTypes.NameIdentifier, user.Id), new Claim(ClaimTypes.Name, user.Email ?? "") };
        return AuthenticateResult.Success(new AuthenticationTicket(new ClaimsPrincipal(new ClaimsIdentity(claims, SchemeName)), SchemeName));
    }

    protected override Task HandleChallengeAsync(AuthenticationProperties properties)
    {
        Response.StatusCode = 401;
        return Response.WriteAsJsonAsync(new { status = 401, detail = "Увійдіть до облікового запису." });
    }
}
