using System;
using BirdLab.Api.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.EntityFrameworkCore.Storage.ValueConversion;

#nullable disable

namespace BirdLab.Api.Migrations
{
    [DbContext(typeof(BirdDbContext))]
    partial class BirdDbContextModelSnapshot : ModelSnapshot
    {
        protected override void BuildModel(ModelBuilder modelBuilder)
        {
#pragma warning disable 612, 618
            modelBuilder
                .HasAnnotation("ProductVersion", "10.0.14")
                .HasAnnotation("Relational:MaxIdentifierLength", 128);

            SqlServerModelBuilderExtensions.UseIdentityColumns(modelBuilder);

            modelBuilder.Entity("BirdLab.Api.Models.Analysis", b =>
                {
                    b.Property<int>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("int");

                    SqlServerPropertyBuilderExtensions.UseIdentityColumn(b.Property<int>("Id"));

                    b.Property<DateTimeOffset>("AnalysisDate")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("AnalysisType")
                        .IsRequired()
                        .HasMaxLength(10)
                        .HasColumnType("nvarchar(10)");

                    b.Property<int?>("BirdId")
                        .HasColumnType("int");

                    b.Property<string>("BirdSnapshotJson")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<DateTimeOffset?>("CompletedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<double>("Confidence")
                        .HasColumnType("float");

                    b.Property<Guid>("CorrelationId")
                        .HasColumnType("uniqueidentifier");

                    b.Property<DateTimeOffset>("CreatedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("Description")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<double>("ElapsedSeconds")
                        .HasColumnType("float");

                    b.Property<string>("ErrorMessage")
                        .HasMaxLength(2000)
                        .HasColumnType("nvarchar(2000)");

                    b.Property<string>("FileHash")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<Guid>("FileId")
                        .HasColumnType("uniqueidentifier");

                    b.Property<Guid>("JobId")
                        .HasColumnType("uniqueidentifier");

                    b.Property<int?>("LegacyId")
                        .HasColumnType("int");

                    b.Property<string>("LegacySource")
                        .HasMaxLength(64)
                        .HasColumnType("nvarchar(64)");

                    b.Property<string>("MetadataJson")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("ModelName")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("ModelRevision")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("OriginalFileName")
                        .IsRequired()
                        .HasMaxLength(255)
                        .HasColumnType("nvarchar(255)");

                    b.Property<string>("PredictedSpecies")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<int>("RetryCount")
                        .HasColumnType("int");

                    b.Property<DateTimeOffset?>("StartedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("Status")
                        .IsRequired()
                        .HasMaxLength(16)
                        .HasColumnType("nvarchar(16)");

                    b.Property<string>("StoredFilePath")
                        .IsRequired()
                        .HasMaxLength(100)
                        .HasColumnType("nvarchar(100)");

                    b.Property<DateTimeOffset>("UpdatedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("UserId")
                        .HasColumnType("nvarchar(450)");

                    b.HasKey("Id");

                    b.HasIndex("AnalysisDate");

                    b.HasIndex("BirdId");

                    b.HasIndex("JobId")
                        .IsUnique();

                    b.HasIndex("StoredFilePath")
                        .IsUnique();

                    b.HasIndex("LegacySource", "LegacyId")
                        .IsUnique()
                        .HasFilter("[LegacySource] IS NOT NULL AND [LegacyId] IS NOT NULL");

                    b.HasIndex("Status", "UpdatedAt");

                    b.HasIndex("UserId", "AnalysisDate");

                    b.ToTable("Analyses", t =>
                        {
                            t.HasCheckConstraint("CK_Analysis_Confidence", "[Confidence] >= 0 AND [Confidence] <= 1");

                            t.HasCheckConstraint("CK_Analysis_Status", "[Status] IN ('Pending','Queued','Processing','Completed','Failed')");

                            t.HasCheckConstraint("CK_Analysis_Type", "[AnalysisType] IN ('image','audio')");
                        });
                });

            modelBuilder.Entity("BirdLab.Api.Models.ApplicationUser", b =>
                {
                    b.Property<string>("Id")
                        .HasColumnType("nvarchar(450)");

                    b.Property<int>("AccessFailedCount")
                        .HasColumnType("int");

                    b.Property<string>("ConcurrencyStamp")
                        .IsConcurrencyToken()
                        .HasColumnType("nvarchar(max)");

                    b.Property<DateTimeOffset>("CreatedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("Email")
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.Property<bool>("EmailConfirmed")
                        .HasColumnType("bit");

                    b.Property<bool>("LockoutEnabled")
                        .HasColumnType("bit");

                    b.Property<DateTimeOffset?>("LockoutEnd")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("NormalizedEmail")
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.Property<string>("NormalizedUserName")
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.Property<string>("PasswordHash")
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("PhoneNumber")
                        .HasColumnType("nvarchar(max)");

                    b.Property<bool>("PhoneNumberConfirmed")
                        .HasColumnType("bit");

                    b.Property<string>("SecurityStamp")
                        .HasColumnType("nvarchar(max)");

                    b.Property<bool>("TwoFactorEnabled")
                        .HasColumnType("bit");

                    b.Property<string>("UserName")
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.HasKey("Id");

                    b.HasIndex("NormalizedEmail")
                        .HasDatabaseName("EmailIndex");

                    b.HasIndex("NormalizedUserName")
                        .IsUnique()
                        .HasDatabaseName("UserNameIndex")
                        .HasFilter("[NormalizedUserName] IS NOT NULL");

                    b.ToTable("AspNetUsers", (string)null);
                });

            modelBuilder.Entity("BirdLab.Api.Models.AuthSession", b =>
                {
                    b.Property<string>("Id")
                        .HasMaxLength(64)
                        .HasColumnType("nvarchar(64)");

                    b.Property<DateTimeOffset>("ExpiresAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("UserId")
                        .IsRequired()
                        .HasColumnType("nvarchar(450)");

                    b.HasKey("Id");

                    b.HasIndex("ExpiresAt");

                    b.HasIndex("UserId");

                    b.ToTable("AuthSessions");
                });

            modelBuilder.Entity("BirdLab.Api.Models.Bird", b =>
                {
                    b.Property<int>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("int");

                    SqlServerPropertyBuilderExtensions.UseIdentityColumn(b.Property<int>("Id"));

                    b.Property<string>("AverageSize")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("CommonName")
                        .IsRequired()
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.Property<string>("ConservationStatus")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("Description")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("Diet")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("Distribution")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("Family")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("Habitat")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("ScientificName")
                        .IsRequired()
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.Property<string>("SourceUrl")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("SourcesJson")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("UkrainianName")
                        .IsRequired()
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.HasKey("Id");

                    b.HasIndex("ScientificName")
                        .IsUnique();

                    b.ToTable("Birds");
                });

            modelBuilder.Entity("BirdLab.Api.Models.CryptoPayment", b =>
                {
                    b.Property<Guid>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("uniqueidentifier");

                    b.Property<long>("Amount")
                        .HasColumnType("bigint");

                    b.Property<int>("Attempts")
                        .HasColumnType("int");

                    b.Property<string>("BlockHash")
                        .HasMaxLength(66)
                        .HasColumnType("nvarchar(66)");

                    b.Property<long?>("BlockNumber")
                        .HasColumnType("bigint");

                    b.Property<string>("BlockchainNetwork")
                        .IsRequired()
                        .HasMaxLength(32)
                        .HasColumnType("nvarchar(32)");

                    b.Property<long>("ChainId")
                        .HasColumnType("bigint");

                    b.Property<DateTimeOffset?>("ConfirmedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<DateTimeOffset>("CreatedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("Error")
                        .HasMaxLength(500)
                        .HasColumnType("nvarchar(500)");

                    b.Property<int?>("LogIndex")
                        .HasColumnType("int");

                    b.Property<DateTimeOffset>("NextCheckAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("OrderId")
                        .IsRequired()
                        .HasMaxLength(66)
                        .HasColumnType("nvarchar(66)");

                    b.Property<string>("PaymentContractAddress")
                        .IsRequired()
                        .HasMaxLength(42)
                        .HasColumnType("nvarchar(42)");

                    b.Property<Guid>("PaymentOrderId")
                        .HasColumnType("uniqueidentifier");

                    b.Property<string>("Status")
                        .IsRequired()
                        .HasMaxLength(24)
                        .HasColumnType("nvarchar(24)");

                    b.Property<int>("SubscriptionPlanId")
                        .HasColumnType("int");

                    b.Property<string>("TokenContractAddress")
                        .IsRequired()
                        .HasMaxLength(42)
                        .HasColumnType("nvarchar(42)");

                    b.Property<string>("TransactionHash")
                        .IsRequired()
                        .HasMaxLength(66)
                        .HasColumnType("nvarchar(66)");

                    b.Property<string>("UserId")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("WalletAddress")
                        .IsRequired()
                        .HasMaxLength(42)
                        .HasColumnType("nvarchar(42)");

                    b.HasKey("Id");

                    b.HasIndex("OrderId")
                        .IsUnique();

                    b.HasIndex("PaymentOrderId");

                    b.HasIndex("Status", "NextCheckAt");

                    b.HasIndex("ChainId", "TransactionHash", "LogIndex")
                        .IsUnique()
                        .HasFilter("[LogIndex] IS NOT NULL");

                    b.ToTable("CryptoPayments");
                });

            modelBuilder.Entity("BirdLab.Api.Models.Evaluation", b =>
                {
                    b.Property<int>("AnalysisId")
                        .HasColumnType("int");

                    b.Property<string>("ExpectedLabel")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("ExpectedScientific")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("Experiment")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("FileHash")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("LabelSource")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<bool>("Top1Correct")
                        .HasColumnType("bit");

                    b.Property<bool>("Top3Correct")
                        .HasColumnType("bit");

                    b.HasKey("AnalysisId");

                    b.ToTable("Evaluations");
                });

            modelBuilder.Entity("BirdLab.Api.Models.InboxMessage", b =>
                {
                    b.Property<Guid>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("uniqueidentifier");

                    b.Property<Guid>("AnalysisId")
                        .HasColumnType("uniqueidentifier");

                    b.Property<string>("BodyHash")
                        .IsRequired()
                        .HasMaxLength(64)
                        .HasColumnType("nvarchar(64)");

                    b.Property<DateTimeOffset>("ReceivedAt")
                        .HasColumnType("datetimeoffset");

                    b.HasKey("Id");

                    b.HasIndex("AnalysisId");

                    b.ToTable("InboxMessages");
                });

            modelBuilder.Entity("BirdLab.Api.Models.OutboxMessage", b =>
                {
                    b.Property<Guid>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("uniqueidentifier");

                    b.Property<Guid>("AnalysisId")
                        .HasColumnType("uniqueidentifier");

                    b.Property<int>("Attempts")
                        .HasColumnType("int");

                    b.Property<DateTimeOffset>("CreatedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("LastError")
                        .HasMaxLength(2000)
                        .HasColumnType("nvarchar(2000)");

                    b.Property<DateTimeOffset>("NextAttemptAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("Payload")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<DateTimeOffset?>("PublishedAt")
                        .HasColumnType("datetimeoffset");

                    b.HasKey("Id");

                    b.HasIndex("AnalysisId")
                        .IsUnique();

                    b.HasIndex("PublishedAt", "NextAttemptAt");

                    b.ToTable("OutboxMessages");
                });

            modelBuilder.Entity("BirdLab.Api.Models.PaymentOrder", b =>
                {
                    b.Property<Guid>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("uniqueidentifier");

                    b.Property<long>("Amount")
                        .HasColumnType("bigint");

                    b.Property<int>("AnalysisLimit")
                        .HasColumnType("int");

                    b.Property<long>("ChainId")
                        .HasColumnType("bigint");

                    b.Property<DateTimeOffset>("CreatedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<int>("DurationDays")
                        .HasColumnType("int");

                    b.Property<DateTimeOffset>("ExpiresAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("Features")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("OrderId")
                        .IsRequired()
                        .HasMaxLength(66)
                        .HasColumnType("nvarchar(66)");

                    b.Property<string>("PaymentContractAddress")
                        .IsRequired()
                        .HasMaxLength(42)
                        .HasColumnType("nvarchar(42)");

                    b.Property<int>("PlanId")
                        .HasColumnType("int");

                    b.Property<bool>("ReplaceCurrentPlan")
                        .HasColumnType("bit");

                    b.Property<string>("Status")
                        .IsRequired()
                        .HasMaxLength(24)
                        .HasColumnType("nvarchar(24)");

                    b.Property<string>("TokenContractAddress")
                        .IsRequired()
                        .HasMaxLength(42)
                        .HasColumnType("nvarchar(42)");

                    b.Property<int>("TokenDecimals")
                        .HasColumnType("int");

                    b.Property<string>("UserId")
                        .IsRequired()
                        .HasColumnType("nvarchar(450)");

                    b.Property<string>("WalletAddress")
                        .IsRequired()
                        .HasMaxLength(42)
                        .HasColumnType("nvarchar(42)");

                    b.HasKey("Id");

                    b.HasIndex("OrderId")
                        .IsUnique();

                    b.HasIndex("PlanId");

                    b.HasIndex("UserId", "CreatedAt");

                    b.ToTable("PaymentOrders", t =>
                        {
                            t.HasCheckConstraint("CK_Order_Amount", "[Amount] > 0");
                        });
                });

            modelBuilder.Entity("BirdLab.Api.Models.Prediction", b =>
                {
                    b.Property<int>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("int");

                    SqlServerPropertyBuilderExtensions.UseIdentityColumn(b.Property<int>("Id"));

                    b.Property<int>("AnalysisId")
                        .HasColumnType("int");

                    b.Property<double>("Confidence")
                        .HasColumnType("float");

                    b.Property<int>("Rank")
                        .HasColumnType("int");

                    b.Property<string>("ScientificName")
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.Property<string>("SpeciesName")
                        .IsRequired()
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.HasKey("Id");

                    b.HasIndex("AnalysisId", "Rank")
                        .IsUnique();

                    b.ToTable("Predictions", t =>
                        {
                            t.HasCheckConstraint("CK_Prediction_Confidence", "[Confidence] >= 0 AND [Confidence] <= 1");

                            t.HasCheckConstraint("CK_Prediction_Rank", "[Rank] BETWEEN 1 AND 3");
                        });
                });

            modelBuilder.Entity("BirdLab.Api.Models.SubscriptionPlan", b =>
                {
                    b.Property<int>("Id")
                        .HasColumnType("int");

                    b.Property<int>("AnalysisLimit")
                        .HasColumnType("int");

                    b.Property<string>("Currency")
                        .IsRequired()
                        .HasMaxLength(16)
                        .HasColumnType("nvarchar(16)");

                    b.Property<int>("DurationDays")
                        .HasColumnType("int");

                    b.Property<string>("Features")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<bool>("IsActive")
                        .HasColumnType("bit");

                    b.Property<string>("Name")
                        .IsRequired()
                        .HasMaxLength(32)
                        .HasColumnType("nvarchar(32)");

                    b.Property<long>("Price")
                        .HasColumnType("bigint");

                    b.HasKey("Id");

                    b.HasIndex("Name")
                        .IsUnique();

                    b.ToTable("SubscriptionPlans", t =>
                        {
                            t.HasCheckConstraint("CK_Plan_Terms", "[Price] >= 0 AND [AnalysisLimit] > 0 AND [DurationDays] > 0");
                        });

                    b.HasData(
                        new
                        {
                            Id = 0,
                            AnalysisLimit = 5,
                            Currency = "USDC",
                            DurationDays = 1,
                            Features = "[\"image\",\"history\",\"basicInfo\"]",
                            IsActive = true,
                            Name = "FREE",
                            Price = 0L
                        },
                        new
                        {
                            Id = 1,
                            AnalysisLimit = 100,
                            Currency = "USDC",
                            DurationDays = 30,
                            Features = "[\"image\",\"audio\",\"history\",\"basicInfo\",\"gallery\",\"statistics\"]",
                            IsActive = true,
                            Name = "PRO",
                            Price = 5000000L
                        },
                        new
                        {
                            Id = 2,
                            AnalysisLimit = 500,
                            Currency = "USDC",
                            DurationDays = 30,
                            Features = "[\"image\",\"audio\",\"history\",\"basicInfo\",\"gallery\",\"statistics\",\"batch\",\"compare\",\"advancedStatistics\"]",
                            IsActive = true,
                            Name = "PREMIUM",
                            Price = 10000000L
                        });
                });

            modelBuilder.Entity("BirdLab.Api.Models.UsageRecord", b =>
                {
                    b.Property<Guid>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("uniqueidentifier");

                    b.Property<DateTimeOffset>("CreatedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("Feature")
                        .IsRequired()
                        .HasMaxLength(32)
                        .HasColumnType("nvarchar(32)");

                    b.Property<Guid>("JobId")
                        .HasColumnType("uniqueidentifier");

                    b.Property<DateTimeOffset?>("ReleasedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("Status")
                        .IsRequired()
                        .HasMaxLength(16)
                        .HasColumnType("nvarchar(16)");

                    b.Property<string>("UserId")
                        .IsRequired()
                        .HasColumnType("nvarchar(450)");

                    b.Property<Guid?>("UserSubscriptionId")
                        .HasColumnType("uniqueidentifier");

                    b.HasKey("Id");

                    b.HasIndex("JobId")
                        .IsUnique();

                    b.HasIndex("UserSubscriptionId");

                    b.HasIndex("UserId", "CreatedAt");

                    b.ToTable("UsageRecords");
                });

            modelBuilder.Entity("BirdLab.Api.Models.UserSubscription", b =>
                {
                    b.Property<Guid>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("uniqueidentifier");

                    b.Property<int>("AnalysesUsed")
                        .HasColumnType("int");

                    b.Property<int>("AnalysisLimit")
                        .HasColumnType("int");

                    b.Property<DateTimeOffset>("CreatedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<DateTimeOffset>("EndDate")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("Features")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<Guid>("PaymentOrderId")
                        .HasColumnType("uniqueidentifier");

                    b.Property<int>("PlanId")
                        .HasColumnType("int");

                    b.Property<Guid?>("ReplacedByPaymentOrderId")
                        .HasColumnType("uniqueidentifier");

                    b.Property<DateTimeOffset>("StartDate")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("Status")
                        .IsRequired()
                        .HasMaxLength(24)
                        .HasColumnType("nvarchar(24)");

                    b.Property<string>("UserId")
                        .IsRequired()
                        .HasColumnType("nvarchar(450)");

                    b.HasKey("Id");

                    b.HasIndex("PaymentOrderId")
                        .IsUnique();

                    b.HasIndex("PlanId");

                    b.HasIndex("UserId", "StartDate", "EndDate");

                    b.ToTable("UserSubscriptions", t =>
                        {
                            t.HasCheckConstraint("CK_Subscription_Usage", "[AnalysesUsed] >= 0 AND [AnalysesUsed] <= [AnalysisLimit] AND [EndDate] > [StartDate]");
                        });
                });

            modelBuilder.Entity("BirdLab.Api.Models.UserWallet", b =>
                {
                    b.Property<Guid>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("uniqueidentifier");

                    b.Property<bool>("IsVerified")
                        .HasColumnType("bit");

                    b.Property<string>("UserId")
                        .IsRequired()
                        .HasColumnType("nvarchar(450)");

                    b.Property<DateTimeOffset?>("VerifiedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("WalletAddress")
                        .IsRequired()
                        .HasMaxLength(42)
                        .HasColumnType("nvarchar(42)");

                    b.HasKey("Id");

                    b.HasIndex("WalletAddress")
                        .IsUnique();

                    b.HasIndex("UserId", "WalletAddress")
                        .IsUnique();

                    b.ToTable("UserWallets");
                });

            modelBuilder.Entity("BirdLab.Api.Models.WalletNonce", b =>
                {
                    b.Property<string>("Id")
                        .HasMaxLength(64)
                        .HasColumnType("nvarchar(64)");

                    b.Property<long>("ChainId")
                        .HasColumnType("bigint");

                    b.Property<string>("Domain")
                        .IsRequired()
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.Property<DateTimeOffset>("ExpiresAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("Message")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<DateTimeOffset?>("UsedAt")
                        .HasColumnType("datetimeoffset");

                    b.Property<string>("UserId")
                        .IsRequired()
                        .HasColumnType("nvarchar(450)");

                    b.Property<string>("WalletAddress")
                        .IsRequired()
                        .HasMaxLength(42)
                        .HasColumnType("nvarchar(42)");

                    b.HasKey("Id");

                    b.HasIndex("ExpiresAt");

                    b.HasIndex("UserId");

                    b.ToTable("WalletNonces");
                });

            modelBuilder.Entity("Microsoft.AspNetCore.Identity.IdentityRole", b =>
                {
                    b.Property<string>("Id")
                        .HasColumnType("nvarchar(450)");

                    b.Property<string>("ConcurrencyStamp")
                        .IsConcurrencyToken()
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("Name")
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.Property<string>("NormalizedName")
                        .HasMaxLength(256)
                        .HasColumnType("nvarchar(256)");

                    b.HasKey("Id");

                    b.HasIndex("NormalizedName")
                        .IsUnique()
                        .HasDatabaseName("RoleNameIndex")
                        .HasFilter("[NormalizedName] IS NOT NULL");

                    b.ToTable("AspNetRoles", (string)null);
                });

            modelBuilder.Entity("Microsoft.AspNetCore.Identity.IdentityRoleClaim<string>", b =>
                {
                    b.Property<int>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("int");

                    SqlServerPropertyBuilderExtensions.UseIdentityColumn(b.Property<int>("Id"));

                    b.Property<string>("ClaimType")
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("ClaimValue")
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("RoleId")
                        .IsRequired()
                        .HasColumnType("nvarchar(450)");

                    b.HasKey("Id");

                    b.HasIndex("RoleId");

                    b.ToTable("AspNetRoleClaims", (string)null);
                });

            modelBuilder.Entity("Microsoft.AspNetCore.Identity.IdentityUserClaim<string>", b =>
                {
                    b.Property<int>("Id")
                        .ValueGeneratedOnAdd()
                        .HasColumnType("int");

                    SqlServerPropertyBuilderExtensions.UseIdentityColumn(b.Property<int>("Id"));

                    b.Property<string>("ClaimType")
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("ClaimValue")
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("UserId")
                        .IsRequired()
                        .HasColumnType("nvarchar(450)");

                    b.HasKey("Id");

                    b.HasIndex("UserId");

                    b.ToTable("AspNetUserClaims", (string)null);
                });

            modelBuilder.Entity("Microsoft.AspNetCore.Identity.IdentityUserLogin<string>", b =>
                {
                    b.Property<string>("LoginProvider")
                        .HasColumnType("nvarchar(450)");

                    b.Property<string>("ProviderKey")
                        .HasColumnType("nvarchar(450)");

                    b.Property<string>("ProviderDisplayName")
                        .HasColumnType("nvarchar(max)");

                    b.Property<string>("UserId")
                        .IsRequired()
                        .HasColumnType("nvarchar(450)");

                    b.HasKey("LoginProvider", "ProviderKey");

                    b.HasIndex("UserId");

                    b.ToTable("AspNetUserLogins", (string)null);
                });

            modelBuilder.Entity("Microsoft.AspNetCore.Identity.IdentityUserRole<string>", b =>
                {
                    b.Property<string>("UserId")
                        .HasColumnType("nvarchar(450)");

                    b.Property<string>("RoleId")
                        .HasColumnType("nvarchar(450)");

                    b.HasKey("UserId", "RoleId");

                    b.HasIndex("RoleId");

                    b.ToTable("AspNetUserRoles", (string)null);
                });

            modelBuilder.Entity("Microsoft.AspNetCore.Identity.IdentityUserToken<string>", b =>
                {
                    b.Property<string>("UserId")
                        .HasColumnType("nvarchar(450)");

                    b.Property<string>("LoginProvider")
                        .HasColumnType("nvarchar(450)");

                    b.Property<string>("Name")
                        .HasColumnType("nvarchar(450)");

                    b.Property<string>("Value")
                        .HasColumnType("nvarchar(max)");

                    b.HasKey("UserId", "LoginProvider", "Name");

                    b.ToTable("AspNetUserTokens", (string)null);
                });

            modelBuilder.Entity("BirdLab.Api.Models.Analysis", b =>
                {
                    b.HasOne("BirdLab.Api.Models.Bird", "Bird")
                        .WithMany()
                        .HasForeignKey("BirdId")
                        .OnDelete(DeleteBehavior.Restrict);

                    b.HasOne("BirdLab.Api.Models.ApplicationUser", null)
                        .WithMany()
                        .HasForeignKey("UserId")
                        .OnDelete(DeleteBehavior.Restrict);

                    b.Navigation("Bird");
                });

            modelBuilder.Entity("BirdLab.Api.Models.AuthSession", b =>
                {
                    b.HasOne("BirdLab.Api.Models.ApplicationUser", null)
                        .WithMany()
                        .HasForeignKey("UserId")
                        .OnDelete(DeleteBehavior.Cascade)
                        .IsRequired();
                });

            modelBuilder.Entity("BirdLab.Api.Models.CryptoPayment", b =>
                {
                    b.HasOne("BirdLab.Api.Models.PaymentOrder", null)
                        .WithMany()
                        .HasForeignKey("PaymentOrderId")
                        .OnDelete(DeleteBehavior.Restrict)
                        .IsRequired();
                });

            modelBuilder.Entity("BirdLab.Api.Models.Evaluation", b =>
                {
                    b.HasOne("BirdLab.Api.Models.Analysis", "Analysis")
                        .WithOne("Evaluation")
                        .HasForeignKey("BirdLab.Api.Models.Evaluation", "AnalysisId")
                        .OnDelete(DeleteBehavior.Cascade)
                        .IsRequired();

                    b.Navigation("Analysis");
                });

            modelBuilder.Entity("BirdLab.Api.Models.PaymentOrder", b =>
                {
                    b.HasOne("BirdLab.Api.Models.SubscriptionPlan", null)
                        .WithMany()
                        .HasForeignKey("PlanId")
                        .OnDelete(DeleteBehavior.Restrict)
                        .IsRequired();

                    b.HasOne("BirdLab.Api.Models.ApplicationUser", null)
                        .WithMany()
                        .HasForeignKey("UserId")
                        .OnDelete(DeleteBehavior.Restrict)
                        .IsRequired();
                });

            modelBuilder.Entity("BirdLab.Api.Models.Prediction", b =>
                {
                    b.HasOne("BirdLab.Api.Models.Analysis", "Analysis")
                        .WithMany("Predictions")
                        .HasForeignKey("AnalysisId")
                        .OnDelete(DeleteBehavior.Cascade)
                        .IsRequired();

                    b.Navigation("Analysis");
                });

            modelBuilder.Entity("BirdLab.Api.Models.UsageRecord", b =>
                {
                    b.HasOne("BirdLab.Api.Models.ApplicationUser", null)
                        .WithMany()
                        .HasForeignKey("UserId")
                        .OnDelete(DeleteBehavior.Restrict)
                        .IsRequired();

                    b.HasOne("BirdLab.Api.Models.UserSubscription", null)
                        .WithMany()
                        .HasForeignKey("UserSubscriptionId")
                        .OnDelete(DeleteBehavior.Restrict);
                });

            modelBuilder.Entity("BirdLab.Api.Models.UserSubscription", b =>
                {
                    b.HasOne("BirdLab.Api.Models.PaymentOrder", null)
                        .WithMany()
                        .HasForeignKey("PaymentOrderId")
                        .OnDelete(DeleteBehavior.Restrict)
                        .IsRequired();

                    b.HasOne("BirdLab.Api.Models.SubscriptionPlan", null)
                        .WithMany()
                        .HasForeignKey("PlanId")
                        .OnDelete(DeleteBehavior.Restrict)
                        .IsRequired();

                    b.HasOne("BirdLab.Api.Models.ApplicationUser", null)
                        .WithMany()
                        .HasForeignKey("UserId")
                        .OnDelete(DeleteBehavior.Restrict)
                        .IsRequired();
                });

            modelBuilder.Entity("BirdLab.Api.Models.UserWallet", b =>
                {
                    b.HasOne("BirdLab.Api.Models.ApplicationUser", null)
                        .WithMany()
                        .HasForeignKey("UserId")
                        .OnDelete(DeleteBehavior.Restrict)
                        .IsRequired();
                });

            modelBuilder.Entity("BirdLab.Api.Models.WalletNonce", b =>
                {
                    b.HasOne("BirdLab.Api.Models.ApplicationUser", null)
                        .WithMany()
                        .HasForeignKey("UserId")
                        .OnDelete(DeleteBehavior.Cascade)
                        .IsRequired();
                });

            modelBuilder.Entity("Microsoft.AspNetCore.Identity.IdentityRoleClaim<string>", b =>
                {
                    b.HasOne("Microsoft.AspNetCore.Identity.IdentityRole", null)
                        .WithMany()
                        .HasForeignKey("RoleId")
                        .OnDelete(DeleteBehavior.Cascade)
                        .IsRequired();
                });

            modelBuilder.Entity("Microsoft.AspNetCore.Identity.IdentityUserClaim<string>", b =>
                {
                    b.HasOne("BirdLab.Api.Models.ApplicationUser", null)
                        .WithMany()
                        .HasForeignKey("UserId")
                        .OnDelete(DeleteBehavior.Cascade)
                        .IsRequired();
                });

            modelBuilder.Entity("Microsoft.AspNetCore.Identity.IdentityUserLogin<string>", b =>
                {
                    b.HasOne("BirdLab.Api.Models.ApplicationUser", null)
                        .WithMany()
                        .HasForeignKey("UserId")
                        .OnDelete(DeleteBehavior.Cascade)
                        .IsRequired();
                });

            modelBuilder.Entity("Microsoft.AspNetCore.Identity.IdentityUserRole<string>", b =>
                {
                    b.HasOne("Microsoft.AspNetCore.Identity.IdentityRole", null)
                        .WithMany()
                        .HasForeignKey("RoleId")
                        .OnDelete(DeleteBehavior.Cascade)
                        .IsRequired();

                    b.HasOne("BirdLab.Api.Models.ApplicationUser", null)
                        .WithMany()
                        .HasForeignKey("UserId")
                        .OnDelete(DeleteBehavior.Cascade)
                        .IsRequired();
                });

            modelBuilder.Entity("Microsoft.AspNetCore.Identity.IdentityUserToken<string>", b =>
                {
                    b.HasOne("BirdLab.Api.Models.ApplicationUser", null)
                        .WithMany()
                        .HasForeignKey("UserId")
                        .OnDelete(DeleteBehavior.Cascade)
                        .IsRequired();
                });

            modelBuilder.Entity("BirdLab.Api.Models.Analysis", b =>
                {
                    b.Navigation("Evaluation");

                    b.Navigation("Predictions");
                });
#pragma warning restore 612, 618
        }
    }
}
