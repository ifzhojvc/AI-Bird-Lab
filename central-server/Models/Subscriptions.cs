using Microsoft.AspNetCore.Identity;

namespace BirdLab.Api.Models;

public sealed class ApplicationUser : IdentityUser
{
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class AuthSession
{
    public string Id { get; set; } = "";
    public string UserId { get; set; } = "";
    public DateTimeOffset ExpiresAt { get; set; }
}

public sealed class SubscriptionPlan
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public long Price { get; set; }
    public string Currency { get; set; } = "USDC";
    public int DurationDays { get; set; }
    public int AnalysisLimit { get; set; }
    public string Features { get; set; } = "[]";
    public bool IsActive { get; set; } = true;
}

public sealed class UserSubscription
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string UserId { get; set; } = "";
    public int PlanId { get; set; }
    public Guid PaymentOrderId { get; set; }
    public Guid? ReplacedByPaymentOrderId { get; set; }
    public DateTimeOffset StartDate { get; set; }
    public DateTimeOffset EndDate { get; set; }
    public string Status { get; set; } = "Active";
    public int AnalysisLimit { get; set; }
    public string Features { get; set; } = "[]";
    public int AnalysesUsed { get; set; }
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class PaymentOrder
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string OrderId { get; set; } = "";
    public string UserId { get; set; } = "";
    public int PlanId { get; set; }
    public string WalletAddress { get; set; } = "";
    public long ChainId { get; set; }
    public string TokenContractAddress { get; set; } = "";
    public string PaymentContractAddress { get; set; } = "";
    public long Amount { get; set; }
    public int TokenDecimals { get; set; }
    public int DurationDays { get; set; }
    public int AnalysisLimit { get; set; }
    public string Features { get; set; } = "[]";
    public bool ReplaceCurrentPlan { get; set; }
    public string Status { get; set; } = "Created";
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset ExpiresAt { get; set; }
}

public sealed class CryptoPayment
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid PaymentOrderId { get; set; }
    public string UserId { get; set; } = "";
    public int SubscriptionPlanId { get; set; }
    public string OrderId { get; set; } = "";
    public string WalletAddress { get; set; } = "";
    public string BlockchainNetwork { get; set; } = "";
    public long ChainId { get; set; }
    public string TokenContractAddress { get; set; } = "";
    public string PaymentContractAddress { get; set; } = "";
    public long Amount { get; set; }
    public string TransactionHash { get; set; } = "";
    public long? BlockNumber { get; set; }
    public string? BlockHash { get; set; }
    public int? LogIndex { get; set; }
    public string Status { get; set; } = "Pending";
    public string? Error { get; set; }
    public int Attempts { get; set; }
    public DateTimeOffset NextCheckAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? ConfirmedAt { get; set; }
}

public sealed class UserWallet
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string UserId { get; set; } = "";
    public string WalletAddress { get; set; } = "";
    public bool IsVerified { get; set; }
    public DateTimeOffset? VerifiedAt { get; set; }
}

public sealed class WalletNonce
{
    public string Id { get; set; } = "";
    public string UserId { get; set; } = "";
    public string WalletAddress { get; set; } = "";
    public string Message { get; set; } = "";
    public string Domain { get; set; } = "";
    public long ChainId { get; set; }
    public DateTimeOffset ExpiresAt { get; set; }
    public DateTimeOffset? UsedAt { get; set; }
}

public sealed class UsageRecord
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid JobId { get; set; }
    public string UserId { get; set; } = "";
    public Guid? UserSubscriptionId { get; set; }
    public string Feature { get; set; } = "";
    public string Status { get; set; } = "Reserved";
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? ReleasedAt { get; set; }
}
