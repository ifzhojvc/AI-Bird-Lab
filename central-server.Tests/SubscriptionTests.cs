using System.Text.Json;
using BirdLab.Api.Data;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Messaging;
using BirdLab.Api.Models;
using BirdLab.Api.Subscriptions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Nethereum.Signer;
using Xunit;

namespace BirdLab.Api.Tests;

public sealed class FakeBlockchain : IBlockchainVerifier
{
    public PaymentEvidence Evidence { get; set; } = new("Confirmed", null, 10, "0x" + new string('b', 64), 1);
    public Task CheckConfigurationAsync(int planId, long price, CancellationToken token) => Task.CompletedTask;
    public Task<PaymentEvidence> VerifyAsync(PaymentOrder order, string hash, CancellationToken token) => Task.FromResult(Evidence);
}

public sealed class SubscriptionTests
{
    internal static BlockchainOptions Options() => new() { Enabled = true, AllowLocalAnvil = true, ChainId = 31337, TokenAddress = "0x1111111111111111111111111111111111111111", PaymentContractAddress = "0x2222222222222222222222222222222222222222", Confirmations = 2 };
    internal static async Task<BirdDbContext> Database()
    {
        var db = new BirdDbContext(new DbContextOptionsBuilder<BirdDbContext>().UseInMemoryDatabase(Guid.NewGuid().ToString()).Options);
        await db.Database.EnsureCreatedAsync();
        db.Users.Add(new ApplicationUser { Id = TestAccount.UserId, UserName = "unit@example.test" });
        await db.SaveChangesAsync();
        return db;
    }
    internal static async Task<(PaymentService Service, PaymentOrder Order, FakeBlockchain Chain)> Order(BirdDbContext db, int plan = 1, bool replace = false)
    {
        var wallet = "0x3333333333333333333333333333333333333333";
        if (!await db.UserWallets.AnyAsync()) { db.UserWallets.Add(new UserWallet { UserId = TestAccount.UserId, WalletAddress = wallet, IsVerified = true }); await db.SaveChangesAsync(); }
        var chain = new FakeBlockchain();
        var service = new PaymentService(db, chain, Microsoft.Extensions.Options.Options.Create(Options()));
        return (service, await service.CreateAsync(TestAccount.UserId, plan, wallet, replace, default), chain);
    }

    [Fact]
    public async Task SignedNonceChecksAddressMessageExpiryAndSingleUse()
    {
        await using var db = await Database();
        var options = Microsoft.Extensions.Options.Options.Create(Options());
        var service = new WalletService(db, options);
        var key = EthECKey.GenerateKey();
        var nonce = await service.NonceAsync(TestAccount.UserId, key.GetPublicAddress(), default);
        var signer = new EthereumMessageSigner();
        var signature = signer.EncodeUTF8AndSign(nonce.Message, key);
        await Assert.ThrowsAsync<ApiException>(() => service.VerifyAsync(TestAccount.UserId, nonce.Id, nonce.Message.Replace("localhost", "evil.test"), signature, default));
        await Assert.ThrowsAsync<ApiException>(() => service.VerifyAsync(TestAccount.UserId, nonce.Id, nonce.Message, signer.EncodeUTF8AndSign(nonce.Message, EthECKey.GenerateKey()), default));
        var wallet = await service.VerifyAsync(TestAccount.UserId, nonce.Id, nonce.Message, signature, default);
        Assert.True(wallet.IsVerified);
        await Assert.ThrowsAsync<ApiException>(() => service.VerifyAsync(TestAccount.UserId, nonce.Id, nonce.Message, signature, default));
        var expired = await service.NonceAsync(TestAccount.UserId, key.GetPublicAddress(), default);
        expired.ExpiresAt = DateTimeOffset.UtcNow.AddSeconds(-1); await db.SaveChangesAsync();
        await Assert.ThrowsAsync<ApiException>(() => service.VerifyAsync(TestAccount.UserId, expired.Id, expired.Message, signer.EncodeUTF8AndSign(expired.Message, key), default));
    }

    [Fact]
    public async Task SiweBindsUserDomainAndChain()
    {
        await using var db = await Database();
        var config = Options();
        var service = new WalletService(db, Microsoft.Extensions.Options.Options.Create(config));
        var key = EthECKey.GenerateKey();
        var nonce = await service.NonceAsync(TestAccount.UserId, key.GetPublicAddress(), default);
        var signature = new EthereumMessageSigner().EncodeUTF8AndSign(nonce.Message, key);
        await Assert.ThrowsAsync<ApiException>(() => service.VerifyAsync("different-user", nonce.Id, nonce.Message, signature, default));
        config.ChainId = 84532;
        await Assert.ThrowsAsync<ApiException>(() => service.VerifyAsync(TestAccount.UserId, nonce.Id, nonce.Message, signature, default));
        config.ChainId = 31337; config.SiweDomain = "other.test";
        await Assert.ThrowsAsync<ApiException>(() => service.VerifyAsync(TestAccount.UserId, nonce.Id, nonce.Message, signature, default));
    }

    [Theory]
    [InlineData(8453, true, true)]
    [InlineData(1, true, true)]
    [InlineData(31337, false, true)]
    [InlineData(84532, false, false)]
    public void MainnetAndImplicitLocalModeAreRejected(long chain, bool local, bool test)
    {
        var options = Options(); options.ChainId = chain; options.AllowLocalAnvil = local; options.TestMode = test;
        Assert.Throws<ApiException>(options.ValidateNetwork);
    }

    [Fact]
    public async Task OrderUsesServerPriceAndRequiresVerifiedWallet()
    {
        await using var db = await Database();
        var service = new PaymentService(db, new FakeBlockchain(), Microsoft.Extensions.Options.Options.Create(Options()));
        await Assert.ThrowsAsync<ApiException>(() => service.CreateAsync(TestAccount.UserId, 1, "0x3333333333333333333333333333333333333333", false, default));
        var (_, order, _) = await Order(db);
        Assert.Equal(5_000_000, order.Amount);
        Assert.StartsWith(order.WalletAddress, order.OrderId);
        Assert.Equal(66, order.OrderId.Length);
        Assert.Equal(100, order.AnalysisLimit);
        await Assert.ThrowsAsync<ApiException>(() => service.CreateAsync(TestAccount.UserId, 0, order.WalletAddress, false, default));
        await Assert.ThrowsAsync<ApiException>(() => service.SubmitAsync("other-user", order.Id, "0x" + new string('a', 64), default));
    }

    [Theory]
    [InlineData("Pending")]
    [InlineData("Rejected")]
    [InlineData("RpcUnavailable")]
    [InlineData("Reorged")]
    public async Task UnconfirmedOrInvalidEvidenceNeverActivatesSubscription(string state)
    {
        await using var db = await Database();
        var (service, order, chain) = await Order(db);
        chain.Evidence = new(state, "unit-test evidence");
        var payment = await service.SubmitAsync(TestAccount.UserId, order.Id, "0x" + new string('a', 64), default);
        await service.ProcessAsync(payment.Id, default);
        Assert.Empty(db.UserSubscriptions);
        Assert.Equal("FREE", (await new SubscriptionService(db).GetAsync(TestAccount.UserId, default)).Plan);
    }

    [Fact]
    public async Task RepeatedPaymentEventActivatesExactlyOnceAndReorgRestoresSamePeriod()
    {
        await using var db = await Database();
        var (service, order, chain) = await Order(db);
        var payment = await service.SubmitAsync(TestAccount.UserId, order.Id, "0x" + new string('a', 64), default);
        await service.ProcessAsync(payment.Id, default);
        var first = Assert.Single(db.UserSubscriptions);
        var end = first.EndDate;
        await service.ProcessAsync(payment.Id, default);
        Assert.Single(db.UserSubscriptions);
        Assert.Equal(end, first.EndDate);
        chain.Evidence = new("RpcUnavailable"); await service.ProcessAsync(payment.Id, default);
        Assert.Equal("Active", first.Status);
        chain.Evidence = new("Reorged"); await service.ProcessAsync(payment.Id, default);
        Assert.Equal("FREE", (await new SubscriptionService(db).GetAsync(TestAccount.UserId, default)).Plan);
        chain.Evidence = new("Confirmed", null, 12, "0x" + new string('c', 64), 1);
        await service.ProcessAsync(payment.Id, default);
        Assert.Equal("PRO", (await new SubscriptionService(db).GetAsync(TestAccount.UserId, default)).Plan);
        Assert.Equal(end, Assert.Single(db.UserSubscriptions).EndDate);
    }

    [Fact]
    public async Task RenewalQueuesNewQuotaAndPlanSwitchRequiresConsent()
    {
        await using var db = await Database();
        var (service, order, _) = await Order(db);
        var payment = await service.SubmitAsync(TestAccount.UserId, order.Id, "0x" + new string('a', 64), default);
        await service.ProcessAsync(payment.Id, default);
        var first = Assert.Single(db.UserSubscriptions);
        var renewal = await service.CreateAsync(TestAccount.UserId, 1, order.WalletAddress, false, default);
        var second = await service.SubmitAsync(TestAccount.UserId, renewal.Id, "0x" + new string('b', 64), default);
        await service.ProcessAsync(second.Id, default);
        var next = await db.UserSubscriptions.SingleAsync(s => s.PaymentOrderId == renewal.Id);
        Assert.Equal(first.EndDate, next.StartDate);
        Assert.Equal("Scheduled", next.Status);
        Assert.Equal(0, next.AnalysesUsed);
        await Assert.ThrowsAsync<ApiException>(() => service.CreateAsync(TestAccount.UserId, 2, order.WalletAddress, false, default));
        var upgrade = await service.CreateAsync(TestAccount.UserId, 2, order.WalletAddress, true, default);
        var third = await service.SubmitAsync(TestAccount.UserId, upgrade.Id, "0x" + new string('c', 64), default);
        await service.ProcessAsync(third.Id, default);
        Assert.Equal("Replaced", first.Status); Assert.Equal("Replaced", next.Status);
        Assert.Equal(500, (await new SubscriptionService(db).GetAsync(TestAccount.UserId, default)).Remaining);
    }

    [Theory]
    [InlineData(0, "audio", false)]
    [InlineData(0, "image", true)]
    [InlineData(1, "audio", true)]
    [InlineData(1, "batch", false)]
    [InlineData(1, "advancedStatistics", false)]
    [InlineData(2, "batch", true)]
    [InlineData(2, "compare", true)]
    public async Task FeaturesAreEnforcedFromDatabase(int plan, string feature, bool allowed)
    {
        await using var db = await Database();
        if (plan > 0)
        {
            var (service, order, _) = await Order(db, plan);
            var payment = await service.SubmitAsync(TestAccount.UserId, order.Id, "0x" + new string('a', 64), default);
            await service.ProcessAsync(payment.Id, default);
        }
        var subscriptions = new SubscriptionService(db);
        if (allowed) await subscriptions.RequireFeatureAsync(TestAccount.UserId, feature, default);
        else Assert.Equal(403, (await Assert.ThrowsAsync<ApiException>(() => subscriptions.RequireFeatureAsync(TestAccount.UserId, feature, default))).Status);
    }

    [Fact]
    public async Task ExpiredSubscriptionFallsBackToFreeWithoutDeletingHistory()
    {
        await using var db = await Database();
        var (service, order, _) = await Order(db);
        var payment = await service.SubmitAsync(TestAccount.UserId, order.Id, "0x" + new string('a', 64), default);
        await service.ProcessAsync(payment.Id, default);
        var period = Assert.Single(db.UserSubscriptions);
        period.StartDate = DateTimeOffset.UtcNow.AddDays(-31); period.EndDate = DateTimeOffset.UtcNow.AddSeconds(-1);
        db.Analyses.Add(new Analysis { UserId = TestAccount.UserId, StoredFilePath = "history.jpg" });
        await db.SaveChangesAsync();
        var subscriptions = new SubscriptionService(db);
        Assert.Equal("FREE", (await subscriptions.GetAsync(TestAccount.UserId, default)).Plan);
        await subscriptions.ExpireAsync(default);
        Assert.Equal("Expired", period.Status);
        Assert.Single(db.Analyses);
    }

    [Fact]
    public async Task BatchFeatureIsCheckedAgainInsideQuotaReservation()
    {
        await using var db = await Database();
        var subscriptions = new SubscriptionService(db);
        Assert.Equal(403, (await Assert.ThrowsAsync<ApiException>(() => subscriptions.ReserveAsync(TestAccount.UserId, Guid.NewGuid(), "image", default, "batch"))).Status);
        Assert.Empty(db.UsageRecords);
    }

    [Fact]
    public async Task FreeQuotaDoesNotResetWhenAnalysisDeletedAndFailureReleasesOnlyOnce()
    {
        await using var db = await Database();
        using var files = new TestFiles();
        var service = await TestAccount.Analyses(db, new UnitAiClient(true), files.Store);
        var tasks = new List<DTOs.AcceptedAnalysisDto>();
        for (var i = 0; i < 5; i++) tasks.Add(await service.EnqueueAsync(new Microsoft.AspNetCore.Http.FormFile(new MemoryStream([1]), 0, 1, "file", $"{i}.jpg"), "image", default));
        Assert.Equal(429, (await Assert.ThrowsAsync<ApiException>(() => service.EnqueueAsync(new Microsoft.AspNetCore.Http.FormFile(new MemoryStream([1]), 0, 1, "file", "limit.jpg"), "image", default))).Status);
        var task = await db.Analyses.SingleAsync(a => a.JobId == tasks[0].AnalysisId);
        var outbox = await db.OutboxMessages.SingleAsync(o => o.AnalysisId == task.JobId);
        var body = JsonSerializer.SerializeToUtf8Bytes(new AnalysisEvent(1, Guid.NewGuid(), task.JobId, task.CorrelationId, outbox.Id, "failed", DateTimeOffset.UtcNow, 0, ErrorMessage: "unit failure"), EventJson.Options);
        var processor = new ResultProcessor(db);
        await processor.ApplyAsync(body, default); await processor.ApplyAsync(body, default);
        Assert.Equal(1, (await new SubscriptionService(db).GetAsync(TestAccount.UserId, default)).Remaining);
        await service.DeleteAsync(task.Id, default);
        Assert.Equal(1, (await new SubscriptionService(db).GetAsync(TestAccount.UserId, default)).Remaining);
        Assert.Equal("Released", (await db.UsageRecords.SingleAsync(u => u.JobId == task.JobId)).Status);
    }
}
