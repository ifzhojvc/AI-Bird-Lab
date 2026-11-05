using BirdLab.Api.Auth;
using BirdLab.Api.Data;
using BirdLab.Api.Subscriptions;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;
using System.ComponentModel.DataAnnotations;

namespace BirdLab.Api.Controllers;

public sealed record WalletRequest([Required, MaxLength(42)] string WalletAddress);
public sealed record WalletProof([Required, MaxLength(64)] string Nonce, [Required, MaxLength(2000)] string Message, [Required, MaxLength(132)] string Signature);

[ApiController, Authorize, Route("api/wallets")]
public sealed class WalletsController(WalletService wallets, CurrentUser current, BirdDbContext db) : ControllerBase
{
    [HttpPost("nonce"), EnableRateLimiting("auth")]
    public async Task<IActionResult> Nonce(WalletRequest input, CancellationToken token)
    {
        var nonce = await wallets.NonceAsync(current.Id, input.WalletAddress, token);
        return Ok(new { nonce = nonce.Id, nonce.Message, nonce.ExpiresAt, nonce.ChainId });
    }
    [HttpPost("verify"), EnableRateLimiting("auth")]
    public async Task<IActionResult> Verify(WalletProof input, CancellationToken token) => Ok(await wallets.VerifyAsync(current.Id, input.Nonce, input.Message, input.Signature, token));
    [HttpGet("me")]
    public async Task<IActionResult> Me(CancellationToken token) => Ok(await db.UserWallets.AsNoTracking().Where(w => w.UserId == current.Id).ToArrayAsync(token));
}
