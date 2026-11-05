using System.Numerics;
using BirdLab.Api.Models;
using BirdLab.Api.Infrastructure;
using Microsoft.Extensions.Options;
using Nethereum.ABI.FunctionEncoding.Attributes;
using Nethereum.Contracts;
using Nethereum.RPC.Eth.DTOs;
using Nethereum.Util;
using Nethereum.Web3;

namespace BirdLab.Api.Subscriptions;

[Event("SubscriptionPurchased")]
public sealed class SubscriptionPurchasedEvent : IEventDTO
{
    [Parameter("bytes32", "orderId", 1, true)] public byte[] OrderId { get; set; } = [];
    [Parameter("address", "payer", 2, true)] public string Payer { get; set; } = "";
    [Parameter("uint256", "planId", 3, true)] public BigInteger PlanId { get; set; }
    [Parameter("uint256", "amount", 4, false)] public BigInteger Amount { get; set; }
    [Parameter("address", "token", 5, false)] public string Token { get; set; } = "";
}
[Function("prices", "uint256")]
public sealed class PriceFunction : FunctionMessage
{
    [Parameter("uint256", "", 1)] public BigInteger PlanId { get; set; }
}
[Function("paymentToken", "address")] public sealed class TokenFunction : FunctionMessage;
[Function("decimals", "uint8")] public sealed class DecimalsFunction : FunctionMessage;
[Function("paused", "bool")] public sealed class PausedFunction : FunctionMessage;

public sealed record PaymentEvidence(string State, string? Error = null, long? BlockNumber = null, string? BlockHash = null, int? LogIndex = null);
public interface IBlockchainVerifier
{
    Task CheckConfigurationAsync(int planId, long price, CancellationToken token);
    Task<PaymentEvidence> VerifyAsync(PaymentOrder order, string transactionHash, CancellationToken token);
}

public sealed class BlockchainVerifier(IOptions<BlockchainOptions> settings) : IBlockchainVerifier
{
    private BlockchainOptions Config => settings.Value;
    private static Task<T> Rpc<T>(Task<T> task, CancellationToken token) => task.WaitAsync(TimeSpan.FromSeconds(12), token);
    private static bool Same(string? a, string? b) => string.Equals(a, b, StringComparison.OrdinalIgnoreCase);

    public async Task CheckConfigurationAsync(int planId, long price, CancellationToken token)
    {
        Config.RequirePayments();
        var web3 = new Web3(Config.RpcUrl);
        if ((await Rpc(web3.Eth.ChainId.SendRequestAsync(), token)).Value != Config.ChainId) throw new ApiException(503, "RPC підключений до іншої мережі.");
        var code = await Rpc(web3.Eth.GetCode.SendRequestAsync(Config.PaymentContractAddress), token);
        if (code is "0x" or "0x0" or "") throw new ApiException(503, "Платіжний контракт відсутній у вибраній мережі.");
        var contract = web3.Eth.GetContractHandler(Config.PaymentContractAddress);
        var address = await Rpc(contract.QueryAsync<TokenFunction, string>(new()), token);
        var amount = await Rpc(contract.QueryAsync<PriceFunction, BigInteger>(new() { PlanId = planId }), token);
        var paused = await Rpc(contract.QueryAsync<PausedFunction, bool>(new()), token);
        var decimals = await Rpc(web3.Eth.GetContractHandler(Config.TokenAddress).QueryAsync<DecimalsFunction, byte>(new()), token);
        if (!Same(address, Config.TokenAddress) || amount != price || decimals != Config.TokenDecimals || paused)
            throw new ApiException(503, "Ціна, токен або стан контракту не відповідає серверному тарифу. Потрібна перевірка адміністратора.");
    }

    public async Task<PaymentEvidence> VerifyAsync(PaymentOrder order, string transactionHash, CancellationToken token)
    {
        Config.RequirePayments();
        if (order.ChainId != Config.ChainId || !Same(order.TokenContractAddress, Config.TokenAddress) || !Same(order.PaymentContractAddress, Config.PaymentContractAddress)) return new("Rejected", "Заказ не відповідає налаштованій тестовій мережі.");
        var web3 = new Web3(Config.RpcUrl);
        if ((await Rpc(web3.Eth.ChainId.SendRequestAsync(), token)).Value != order.ChainId) return new("RpcUnavailable", "RPC повернув іншу мережу.");
        var transaction = await Rpc(web3.Eth.Transactions.GetTransactionByHash.SendRequestAsync(transactionHash), token);
        if (transaction is null) return new("Pending", "Транзакцію ще не знайдено через RPC.");
        if (!Same(transaction.TransactionHash, transactionHash) || !Same(transaction.To, order.PaymentContractAddress) || !Same(transaction.From, order.WalletAddress) || transaction.Value.Value != 0)
            return new("Rejected", "Транзакція має іншого відправника або одержувача.");
        var selector = new Sha3Keccack().CalculateHash("purchaseSubscription(bytes32,uint256)")[..8];
        var expectedInput = "0x" + selector + order.OrderId[2..] + order.PlanId.ToString("x").PadLeft(64, '0');
        if (!Same(transaction.Input, expectedInput)) return new("Rejected", "Виклик контракту не відповідає замовленню.");
        var receipt = await Rpc(web3.Eth.Transactions.GetTransactionReceipt.SendRequestAsync(transactionHash), token);
        if (receipt is null) return new("Pending", "Очікуємо включення транзакції до блоку.");
        if (receipt.Status?.Value != 1) return new("Rejected", "Транзакція завершилася помилкою у блокчейні.");
        if (!Same(receipt.To, order.PaymentContractAddress) || !Same(receipt.TransactionHash, transactionHash) || !Same(receipt.From, order.WalletAddress)) return new("Rejected", "Receipt не відповідає транзакції.");
        var block = await Rpc(web3.Eth.Blocks.GetBlockWithTransactionsHashesByNumber.SendRequestAsync(new BlockParameter(receipt.BlockNumber)), token);
        if (block is null || !Same(block.BlockHash, receipt.BlockHash) || !Same(transaction.BlockHash, receipt.BlockHash)) return new("Reorged", "Блок більше не належить канонічному ланцюжку.");
        var minedAt = DateTimeOffset.FromUnixTimeSeconds((long)block.Timestamp.Value);
        if (minedAt < order.CreatedAt.AddSeconds(-30) || minedAt > order.ExpiresAt) return new("Rejected", "Транзакцію включено до блоку поза строком замовлення.");
        var events = receipt.DecodeAllEvents<SubscriptionPurchasedEvent>().Where(e => Same(e.Log.Address, order.PaymentContractAddress) && Same("0x" + Convert.ToHexString(e.Event.OrderId), order.OrderId)).ToArray();
        if (events.Length != 1) return new("Rejected", "Не знайдено єдину справжню подію оплати замовлення.");
        var purchased = events[0];
        if (!Same(purchased.Event.Payer, order.WalletAddress) || purchased.Event.PlanId != order.PlanId || purchased.Event.Amount != order.Amount || !Same(purchased.Event.Token, order.TokenContractAddress))
            return new("Rejected", "Параметри події не відповідають замовленню, токену або сумі.");
        var latest = (await Rpc(web3.Eth.Blocks.GetBlockNumber.SendRequestAsync(), token)).Value;
        var confirmations = latest - receipt.BlockNumber.Value + 1;
        var state = confirmations >= Config.Confirmations ? "Confirmed" : "Pending";
        return new(state, state == "Pending" ? $"Очікуємо {Config.Confirmations} підтверджень." : null, (long)receipt.BlockNumber.Value, receipt.BlockHash.ToLowerInvariant(), (int)purchased.Log.LogIndex.Value);
    }
}
