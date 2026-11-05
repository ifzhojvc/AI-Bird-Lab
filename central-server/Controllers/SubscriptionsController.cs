using System.ComponentModel.DataAnnotations;
using BirdLab.Api.Auth;
using BirdLab.Api.Data;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Subscriptions;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace BirdLab.Api.Controllers;

public sealed record CreateOrder(int PlanId, [Required, MaxLength(42)] string WalletAddress, bool ReplaceCurrentPlan = false);
public sealed record VerifyPayment(Guid OrderId, [Required, MaxLength(66)] string TransactionHash);

[ApiController, Authorize, Route("api/subscriptions")]
public sealed class SubscriptionsController(BirdDbContext db, CurrentUser current, SubscriptionService subscriptions, PaymentService payments, IOptions<BlockchainOptions> settings) : ControllerBase
{
    [AllowAnonymous, HttpGet("plans")]
    public async Task<IActionResult> Plans(CancellationToken token)
    {
        var plans = await db.SubscriptionPlans.AsNoTracking().Where(p => p.IsActive).OrderBy(p => p.Id).ToArrayAsync(token);
        return Ok(plans.Select(p => new { p.Id, p.Name, price = p.Price.ToString(System.Globalization.CultureInfo.InvariantCulture), p.Currency, p.DurationDays, p.AnalysisLimit, features = SubscriptionService.Features(p.Features), tokenDecimals = settings.Value.TokenDecimals }));
    }
    [AllowAnonymous, HttpGet("network")]
    public IActionResult Network() => Ok(new { settings.Value.Enabled, settings.Value.TestMode, settings.Value.ChainId, rpcUrl = settings.Value.PublicRpcUrl, settings.Value.TokenAddress, settings.Value.PaymentContractAddress, settings.Value.TokenDecimals, settings.Value.Confirmations, settings.Value.ExplorerUrl });
    [HttpGet("me"), HttpGet("usage")]
    public Task<Entitlement> Me(CancellationToken token) => subscriptions.GetAsync(current.Id, token);
    [HttpGet("history")]
    public async Task<IActionResult> History(CancellationToken token) => Ok(await db.UserSubscriptions.AsNoTracking().Where(s => s.UserId == current.Id).OrderByDescending(s => s.CreatedAt).Take(200).ToArrayAsync(token));
    [HttpPost("orders"), EnableRateLimiting("payments")]
    public async Task<IActionResult> Order(CreateOrder input, CancellationToken token)
    {
        var order = await payments.CreateAsync(current.Id, input.PlanId, input.WalletAddress, input.ReplaceCurrentPlan, token);
        return Created($"/api/subscriptions/orders/{order.Id}", OrderView(order));
    }
    [HttpGet("orders/{id:guid}")]
    public async Task<IActionResult> GetOrder(Guid id, CancellationToken token)
    {
        var order = await db.PaymentOrders.AsNoTracking().SingleOrDefaultAsync(o => o.Id == id && o.UserId == current.Id, token) ?? throw new ApiException(404, "Замовлення не знайдено.");
        return Ok(OrderView(order));
    }
    [HttpPost("payments/verify"), EnableRateLimiting("payments")]
    public async Task<IActionResult> Verify(VerifyPayment input, CancellationToken token)
    {
        var payment = await payments.SubmitAsync(current.Id, input.OrderId, input.TransactionHash, token);
        var result = await payments.ProcessAsync(payment.Id, token);
        var decimals = await db.PaymentOrders.Where(o => o.Id == result.PaymentOrderId).Select(o => o.TokenDecimals).SingleAsync(token);
        return Ok(PaymentView(result, decimals));
    }
    [HttpGet("payments")]
    public async Task<IActionResult> Payments(CancellationToken token)
    {
        var rows = await db.CryptoPayments.AsNoTracking().Where(p => p.UserId == current.Id).OrderByDescending(p => p.CreatedAt).Take(200).ToArrayAsync(token);
        var ids = rows.Select(p => p.PaymentOrderId).ToArray();
        var decimals = await db.PaymentOrders.Where(o => ids.Contains(o.Id)).ToDictionaryAsync(o => o.Id, o => o.TokenDecimals, token);
        return Ok(rows.Select(p => PaymentView(p, decimals[p.PaymentOrderId])));
    }
    private static object OrderView(Models.PaymentOrder o) => new { o.Id, o.OrderId, o.PlanId, o.WalletAddress, o.ChainId, o.TokenContractAddress, o.PaymentContractAddress, amount = o.Amount.ToString(System.Globalization.CultureInfo.InvariantCulture), o.TokenDecimals, o.DurationDays, o.AnalysisLimit, features = SubscriptionService.Features(o.Features), status = o.Status == "Created" && o.ExpiresAt <= DateTimeOffset.UtcNow ? "Expired" : o.Status, o.CreatedAt, o.ExpiresAt, o.ReplaceCurrentPlan };
    private static object PaymentView(Models.CryptoPayment p, int decimals) => new { p.Id, p.PaymentOrderId, p.OrderId, p.SubscriptionPlanId, p.WalletAddress, p.BlockchainNetwork, p.ChainId, p.TokenContractAddress, p.PaymentContractAddress, amount = p.Amount.ToString(System.Globalization.CultureInfo.InvariantCulture), p.TransactionHash, p.BlockNumber, p.LogIndex, p.Status, p.Error, p.CreatedAt, p.ConfirmedAt, explorerUrl = p.ChainId == 84532 ? $"https://sepolia.basescan.org/tx/{p.TransactionHash}" : null, tokenDecimals = decimals };
}
