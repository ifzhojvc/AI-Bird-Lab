using System.Security.Cryptography;
using System.Text.RegularExpressions;
using BirdLab.Api.Data;
using BirdLab.Api.Infrastructure;
using BirdLab.Api.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Nethereum.Signer;
using Nethereum.Util;

namespace BirdLab.Api.Subscriptions;

public sealed partial class WalletService(BirdDbContext db, IOptions<BlockchainOptions> options)
{
    [GeneratedRegex("^0x[0-9a-fA-F]{40}$")]
    private static partial Regex AddressPattern();
    public static string Address(string value)
    {
        if (!AddressPattern().IsMatch(value) || value[2..].All(c => c == '0')) throw new ApiException(400, "Невірна адреса EVM-гаманця.");
        return value.ToLowerInvariant();
    }

    public async Task<WalletNonce> NonceAsync(string userId, string wallet, CancellationToken token)
    {
        wallet = Address(wallet);
        var config = options.Value;
        config.ValidateNetwork();
        var now = DateTimeOffset.UtcNow;
        var nonce = new WalletNonce { Id = Convert.ToHexString(RandomNumberGenerator.GetBytes(24)), UserId = userId, WalletAddress = wallet, Domain = config.SiweDomain, ChainId = config.ChainId, ExpiresAt = now.AddMinutes(5) };
        var checksum = new AddressUtil().ConvertToChecksumAddress(wallet);
        nonce.Message = $"{nonce.Domain} wants you to sign in with your Ethereum account:\n{checksum}\n\nLink this wallet to your AI Bird Lab account. No transaction or token approval.\n\nURI: {config.SiweUri}\nVersion: 1\nChain ID: {nonce.ChainId}\nNonce: {nonce.Id}\nIssued At: {now:O}\nExpiration Time: {nonce.ExpiresAt:O}\nRequest ID: {userId}";
        db.WalletNonces.Add(nonce);
        await db.SaveChangesAsync(token);
        return nonce;
    }

    public async Task<UserWallet> VerifyAsync(string userId, string nonceId, string message, string signature, CancellationToken token)
    {
        await using var tx = db.Database.IsRelational() ? await db.Database.BeginTransactionAsync(token) : null;
        await UserLock.AcquireAsync(db, userId, token);
        var nonce = await db.WalletNonces.SingleOrDefaultAsync(n => n.Id == nonceId && n.UserId == userId, token);
        if (nonce is null || nonce.UsedAt is not null || nonce.ExpiresAt <= DateTimeOffset.UtcNow || nonce.Message != message || nonce.Domain != options.Value.SiweDomain || nonce.ChainId != options.Value.ChainId)
            throw new ApiException(400, "Повідомлення гаманця прострочене, використане або не відповідає домену чи мережі.");
        string recovered;
        try { recovered = new EthereumMessageSigner().EncodeUTF8AndEcRecover(message, signature); }
        catch (Exception) { throw new ApiException(400, "Невірний підпис гаманця."); }
        if (!string.Equals(recovered, nonce.WalletAddress, StringComparison.OrdinalIgnoreCase)) throw new ApiException(400, "Підпис не належить вибраному гаманцю.");
        var wallet = await db.UserWallets.SingleOrDefaultAsync(w => w.WalletAddress == nonce.WalletAddress, token);
        if (wallet is not null && wallet.UserId != userId) throw new ApiException(409, "Гаманець уже прив’язано до іншого облікового запису.");
        nonce.UsedAt = DateTimeOffset.UtcNow;
        if (wallet is null) { wallet = new UserWallet { UserId = userId, WalletAddress = nonce.WalletAddress }; db.UserWallets.Add(wallet); }
        wallet.IsVerified = true;
        wallet.VerifiedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(token);
        if (tx is not null) await tx.CommitAsync(token);
        return wallet;
    }
}
