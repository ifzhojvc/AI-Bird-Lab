using System.ComponentModel.DataAnnotations;
using System.Security.Cryptography;
using BirdLab.Api.Auth;
using BirdLab.Api.Data;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;

namespace BirdLab.Api.Controllers;

public sealed record Credentials([Required, EmailAddress, MaxLength(254)] string Email, [Required, MinLength(12), MaxLength(128)] string Password, bool UseBearerToken = false);

[ApiController, Route("api/auth")]
public sealed class AuthController(UserManager<ApplicationUser> users, SignInManager<ApplicationUser> signIn, BirdDbContext db, CurrentUser current, IWebHostEnvironment environment) : ControllerBase
{
    [AllowAnonymous, HttpPost("register"), EnableRateLimiting("auth")]
    public async Task<IActionResult> Register(Credentials input, CancellationToken token)
    {
        SecureTransport();
        var email = input.Email.Trim();
        var user = new ApplicationUser { UserName = email, Email = email };
        var result = await users.CreateAsync(user, input.Password);
        if (!result.Succeeded) throw new ApiException(400, "Не вдалося зареєструватися. Використайте іншу адресу та пароль від 12 символів з великою і малою літерами, цифрою та спеціальним символом.");
        return StatusCode(201, await CreateSession(user, input.UseBearerToken, token));
    }

    [AllowAnonymous, HttpPost("login"), EnableRateLimiting("auth")]
    public async Task<IActionResult> Login(Credentials input, CancellationToken token)
    {
        SecureTransport();
        var user = await users.FindByEmailAsync(input.Email.Trim());
        if (user is null || !(await signIn.CheckPasswordSignInAsync(user, input.Password, true)).Succeeded)
            throw new ApiException(401, "Невірні дані входу або обліковий запис тимчасово заблоковано.");
        return Ok(await CreateSession(user, input.UseBearerToken, token));
    }

    [Authorize, HttpGet("me")]
    public async Task<IActionResult> Me(CancellationToken token)
    {
        var user = await db.Users.AsNoTracking().SingleAsync(u => u.Id == current.Id, token);
        return Ok(new { user.Id, user.Email, user.CreatedAt });
    }

    [Authorize, HttpPost("logout")]
    public async Task<IActionResult> Logout(CancellationToken token)
    {
        var value = SessionAuthentication.ReadToken(Request);
        if (value is not null)
        {
            var session = await db.AuthSessions.FindAsync([SessionAuthentication.Hash(value)], token);
            if (session is not null) { db.AuthSessions.Remove(session); await db.SaveChangesAsync(token); }
        }
        Response.Cookies.Delete(SessionAuthentication.CookieName, new CookieOptions { Path = "/api" });
        return NoContent();
    }

    private void SecureTransport()
    {
        if (!Request.IsHttps && !environment.IsDevelopment()) throw new ApiException(400, "Для входу потрібне HTTPS-з’єднання.");
    }

    private async Task<object> CreateSession(ApplicationUser user, bool bearer, CancellationToken token)
    {
        var value = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
        var expires = DateTimeOffset.UtcNow.AddHours(8);
        db.AuthSessions.Add(new AuthSession { Id = SessionAuthentication.Hash(value), UserId = user.Id, ExpiresAt = expires });
        await db.SaveChangesAsync(token);
        if (!bearer) Response.Cookies.Append(SessionAuthentication.CookieName, value, new CookieOptions { HttpOnly = true, Secure = Request.IsHttps, SameSite = SameSiteMode.Lax, Expires = expires, Path = "/api", IsEssential = true });
        return new { user = new { user.Id, user.Email, user.CreatedAt }, accessToken = bearer ? value : null, expiresAt = expires };
    }
}
