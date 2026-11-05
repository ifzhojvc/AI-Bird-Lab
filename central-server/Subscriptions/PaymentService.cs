using System.Security.Cryptography;
using System.Text.RegularExpressions;
using BirdLab.Api.Data;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace BirdLab.Api.Subscriptions;

public sealed partial class PaymentService(BirdDbContext db, IBlockchainVerifier blockchain, IOptions<BlockchainOptions> settings)
{
    [GeneratedRegex("^0x[0-9a-fA-F]{64}$")]
    private static partial Regex HashPattern();

    public async Task<PaymentOrder> CreateAsync(string userId, int planId, string walletAddress, bool replaceCurrentPlan, CancellationToken token)
    {
        var config = settings.Value;
        config.RequirePayments();
        var wallet = WalletService.Address(walletAddress);
        if (!await db.UserWallets.AnyAsync(w => w.UserId == userId && w.WalletAddress == wallet && w.IsVerified, token)) throw new ApiException(403, "Спочатку підтвердіть володіння гаманцем.");
        var plan = await db.SubscriptionPlans.AsNoTracking().SingleOrDefaultAsync(p => p.Id == planId && p.IsActive && p.Price > 0, token) ?? throw new ApiException(400, "Оберіть активний платний тариф.");
        try { await blockchain.CheckConfigurationAsync(plan.Id, plan.Price, token); }
        catch (ApiException) { throw; }
        catch (Exception) when (!token.IsCancellationRequested) { throw new ApiException(503, "Не вдалося перевірити платіжний контракт через RPC. Спробуйте пізніше."); }
        await using var tx = db.Database.IsRelational() ? await db.Database.BeginTransactionAsync(token) : null;
        await UserLock.AcquireAsync(db, userId, token);
        var now = DateTimeOffset.UtcNow;
        var currentPlan = await db.SubscriptionPlans.AsNoTracking().SingleAsync(p => p.Id == planId, token);
        if (!currentPlan.IsActive || currentPlan.Price != plan.Price || currentPlan.DurationDays != plan.DurationDays || currentPlan.AnalysisLimit != plan.AnalysisLimit || currentPlan.Features != plan.Features) throw new ApiException(409, "Тариф змінився. Оновіть сторінку.");
        var existing = await db.PaymentOrders.SingleOrDefaultAsync(o => o.UserId == userId && (o.Status == "Created" || o.Status == "Submitted") && o.ExpiresAt > now, token);
        if (existing is not null)
        {
            if (existing.PlanId == planId && existing.WalletAddress == wallet && existing.ReplaceCurrentPlan == replaceCurrentPlan) return existing;
            throw new ApiException(409, "У вас уже є незавершене замовлення. Завершіть його або дочекайтеся завершення строку.");
        }
        var different = await db.UserSubscriptions.AnyAsync(s => s.UserId == userId && (s.Status == "Active" || s.Status == "Scheduled") && s.EndDate > now && s.PlanId != planId, token);
        if (different && !replaceCurrentPlan) throw new ApiException(409, "Зміна тарифу замінить невикористані дні й ліміти. Підтвердьте це перед створенням замовлення.");
        var order = new PaymentOrder
        {
            UserId = userId, PlanId = planId, OrderId = wallet + Convert.ToHexString(RandomNumberGenerator.GetBytes(12)).ToLowerInvariant(), WalletAddress = wallet,
            ChainId = config.ChainId, TokenContractAddress = WalletService.Address(config.TokenAddress), PaymentContractAddress = WalletService.Address(config.PaymentContractAddress),
            Amount = plan.Price, TokenDecimals = config.TokenDecimals, DurationDays = plan.DurationDays, AnalysisLimit = plan.AnalysisLimit, Features = plan.Features,
            ReplaceCurrentPlan = replaceCurrentPlan, CreatedAt = now, ExpiresAt = now.AddMinutes(config.OrderMinutes)
        };
        db.PaymentOrders.Add(order);
        await db.SaveChangesAsync(token);
        if (tx is not null) await tx.CommitAsync(token);
        return order;
    }

    public async Task<CryptoPayment> SubmitAsync(string userId, Guid orderId, string hash, CancellationToken token)
    {
        if (!HashPattern().IsMatch(hash)) throw new ApiException(400, "Невірний хеш транзакції.");
        hash = hash.ToLowerInvariant();
        await using var tx = db.Database.IsRelational() ? await db.Database.BeginTransactionAsync(token) : null;
        await UserLock.AcquireAsync(db, userId, token);
        var order = await db.PaymentOrders.SingleOrDefaultAsync(o => o.Id == orderId && o.UserId == userId, token) ?? throw new ApiException(404, "Замовлення не знайдено.");
        var payment = await db.CryptoPayments.SingleOrDefaultAsync(p => p.PaymentOrderId == orderId, token);
        if (payment is null)
        {
            payment = new CryptoPayment
            {
                PaymentOrderId = order.Id, UserId = userId, SubscriptionPlanId = order.PlanId, OrderId = order.OrderId,
                WalletAddress = order.WalletAddress, BlockchainNetwork = order.ChainId == 84532 ? "Base Sepolia" : "Local Anvil", ChainId = order.ChainId,
                TokenContractAddress = order.TokenContractAddress, PaymentContractAddress = order.PaymentContractAddress, Amount = order.Amount, TransactionHash = hash
            };
            db.CryptoPayments.Add(payment);
            order.Status = "Submitted";
        }
        else if (payment.TransactionHash != hash)
        {
            if (payment.Status is not ("Rejected" or "Reorged") || await db.UserSubscriptions.AnyAsync(s => s.PaymentOrderId == order.Id && s.Status != "Reorged", token)) throw new ApiException(409, "Замовлення вже пов’язане з іншою транзакцією.");
            payment.TransactionHash = hash;
            payment.Status = "Pending";
            payment.BlockNumber = null;
            payment.BlockHash = null;
            payment.LogIndex = null;
            payment.Error = null;
            order.Status = "Submitted";
        }
        payment.NextCheckAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(token);
        if (tx is not null) await tx.CommitAsync(token);
        return payment;
    }

    public async Task<CryptoPayment> ProcessAsync(Guid paymentId, CancellationToken token)
    {
        var snapshot = await db.CryptoPayments.AsNoTracking().SingleAsync(p => p.Id == paymentId, token);
        var orderSnapshot = await db.PaymentOrders.AsNoTracking().SingleAsync(o => o.Id == snapshot.PaymentOrderId, token);
        PaymentEvidence evidence;
        try { evidence = await blockchain.VerifyAsync(orderSnapshot, snapshot.TransactionHash, token); }
        catch (Exception) when (!token.IsCancellationRequested) { evidence = new("RpcUnavailable", "RPC тимчасово недоступний. Перевірка повториться автоматично."); }
        await using var tx = db.Database.IsRelational() ? await db.Database.BeginTransactionAsync(token) : null;
        await UserLock.AcquireAsync(db, snapshot.UserId, token);
        var payment = await db.CryptoPayments.SingleAsync(p => p.Id == paymentId, token);
        var order = await db.PaymentOrders.SingleAsync(o => o.Id == snapshot.PaymentOrderId, token);
        if (db.Database.IsRelational()) { await db.Entry(payment).ReloadAsync(token); await db.Entry(order).ReloadAsync(token); }
        if (payment.TransactionHash != snapshot.TransactionHash) return payment;
        payment.Attempts++;
        payment.Error = evidence.Error;
        payment.NextCheckAt = DateTimeOffset.UtcNow.AddSeconds(evidence.State == "Confirmed" ? Math.Max(30, settings.Value.PollSeconds) : Math.Min(120, settings.Value.PollSeconds * Math.Max(1, payment.Attempts)));
        var subscription = await db.UserSubscriptions.SingleOrDefaultAsync(s => s.PaymentOrderId == order.Id, token);
        if (evidence.State == "Confirmed")
        {
            var alreadyUsed = await db.CryptoPayments.AnyAsync(p => p.Id != payment.Id && p.ChainId == payment.ChainId && p.TransactionHash == payment.TransactionHash && p.LogIndex == evidence.LogIndex, token);
            if (alreadyUsed) throw new ApiException(409, "Цю подію блокчейна вже оброблено.");
            if (!await db.UserWallets.AnyAsync(w => w.UserId == order.UserId && w.WalletAddress == order.WalletAddress && w.IsVerified, token)) throw new ApiException(403, "Гаманець більше не підтверджений.");
            var now = DateTimeOffset.UtcNow;
            if (subscription is null)
            {
                var previous = await db.UserSubscriptions.Where(s => s.UserId == order.UserId && (s.Status == "Active" || s.Status == "Scheduled") && s.EndDate > now).ToArrayAsync(token);
                var different = previous.Any(s => s.PlanId != order.PlanId);
                if (different && !order.ReplaceCurrentPlan)
                {
                    payment.Status = "ReviewRequired";
                    payment.Error = "Після створення замовлення тариф змінився. Потрібне ручне узгодження оплаченого періоду.";
                    order.Status = "ReviewRequired";
                    await db.SaveChangesAsync(token);
                    if (tx is not null) await tx.CommitAsync(token);
                    return payment;
                }
                if (different)
                    foreach (var old in previous) { old.Status = "Replaced"; old.ReplacedByPaymentOrderId = order.Id; }
                var start = different || previous.Length == 0 ? now : previous.Max(s => s.EndDate);
                subscription = new UserSubscription { UserId = order.UserId, PlanId = order.PlanId, PaymentOrderId = order.Id, StartDate = start, EndDate = start.AddDays(order.DurationDays), Status = start > now ? "Scheduled" : "Active", AnalysisLimit = order.AnalysisLimit, Features = order.Features };
                db.UserSubscriptions.Add(subscription);
            }
            else if (subscription.Status == "Reorged")
            {
                var newer = await db.UserSubscriptions.AnyAsync(s => s.UserId == order.UserId && s.Id != subscription.Id && s.CreatedAt > subscription.CreatedAt && (s.Status == "Active" || s.Status == "Scheduled"), token);
                subscription.Status = newer ? "Replaced" : subscription.EndDate <= now ? "Expired" : subscription.StartDate > now ? "Scheduled" : "Active";
                if (!newer && order.ReplaceCurrentPlan)
                {
                    var restored = await db.UserSubscriptions.Where(s => s.ReplacedByPaymentOrderId == order.Id && (s.Status == "Active" || s.Status == "Scheduled")).ToArrayAsync(token);
                    foreach (var old in restored) old.Status = "Replaced";
                }
            }
            payment.Status = "Confirmed";
            payment.ConfirmedAt ??= now;
            payment.BlockNumber = evidence.BlockNumber;
            payment.BlockHash = evidence.BlockHash;
            payment.LogIndex = evidence.LogIndex;
            order.Status = "Paid";
        }
        else if (evidence.State != "RpcUnavailable")
        {
            var reorg = payment.ConfirmedAt is not null || evidence.State == "Reorged";
            payment.Status = reorg ? "Reorged" : evidence.State;
            order.Status = reorg ? "Reorged" : evidence.State == "Rejected" ? "Rejected" : "Submitted";
            if (subscription is not null && reorg && subscription.Status is "Active" or "Scheduled" or "Expired")
            {
                subscription.Status = "Reorged";
                var newer = await db.UserSubscriptions.AnyAsync(s => s.UserId == order.UserId && s.Id != subscription.Id && s.CreatedAt > subscription.CreatedAt && (s.Status == "Active" || s.Status == "Scheduled"), token);
                if (!newer)
                {
                    var restore = await db.UserSubscriptions.Where(s => s.ReplacedByPaymentOrderId == order.Id && s.Status == "Replaced").ToArrayAsync(token);
                    foreach (var old in restore) old.Status = old.EndDate <= DateTimeOffset.UtcNow ? "Expired" : old.StartDate > DateTimeOffset.UtcNow ? "Scheduled" : "Active";
                }
            }
            if (!reorg) { payment.BlockNumber = evidence.BlockNumber; payment.BlockHash = evidence.BlockHash; payment.LogIndex = evidence.LogIndex; }
        }
        await db.SaveChangesAsync(token);
        if (tx is not null) await tx.CommitAsync(token);
        return payment;
    }
}
