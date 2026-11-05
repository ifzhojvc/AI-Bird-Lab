using BirdLab.Api.Infrastructure;

namespace BirdLab.Api.Subscriptions;

public sealed class BlockchainOptions
{
    public bool Enabled { get; set; }
    public bool TestMode { get; set; } = true;
    public bool AllowLocalAnvil { get; set; }
    public long ChainId { get; set; } = 84532;
    public string RpcUrl { get; set; } = "https://sepolia.base.org";
    public string PublicRpcUrl { get; set; } = "https://sepolia.base.org";
    public string TokenAddress { get; set; } = "0x036CbD53842c5426634e7929541eC2318f3dCF7e";
    public int TokenDecimals { get; set; } = 6;
    public string PaymentContractAddress { get; set; } = "";
    public int Confirmations { get; set; } = 12;
    public int PollSeconds { get; set; } = 15;
    public int OrderMinutes { get; set; } = 30;
    public string SiweDomain { get; set; } = "localhost:5173";
    public string SiweUri { get; set; } = "http://localhost:5173";
    public string ExplorerUrl => ChainId == 84532 ? "https://sepolia.basescan.org" : "";

    public void ValidateNetwork()
    {
        if (!TestMode || (ChainId != 84532 && !(ChainId == 31337 && AllowLocalAnvil)))
            throw new ApiException(503, "Дозволено лише Base Sepolia або явно ввімкнений локальний Anvil. Mainnet вимкнено.");
        if (!Uri.TryCreate(SiweUri, UriKind.Absolute, out var uri) || uri.Authority != SiweDomain || uri.Scheme is not ("http" or "https"))
            throw new ApiException(503, "Некоректні налаштування домену SIWE.");
    }

    public void RequirePayments()
    {
        ValidateNetwork();
        if (!Enabled) throw new ApiException(503, "Тестові платежі ще не налаштовано власником лабораторії.");
        _ = WalletService.Address(TokenAddress);
        _ = WalletService.Address(PaymentContractAddress);
        if (!Uri.TryCreate(RpcUrl, UriKind.Absolute, out var rpc) || rpc.Scheme is not ("http" or "https") || (ChainId == 84532 && rpc.Scheme != "https") || TokenDecimals is < 0 or > 18 || Confirmations is < 1 or > 1000 || OrderMinutes is < 1 or > 120)
            throw new ApiException(503, "Некоректні налаштування тестових платежів.");
    }
}
