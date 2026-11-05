using System;
using BirdLab.Api.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.EntityFrameworkCore.Storage.ValueConversion;

#nullable disable

namespace BirdLab.Api.Migrations
{
    [DbContext(typeof(BirdDbContext))]
    [Migration("20261028115223_InitialCreate")]
    partial class InitialCreate
    {
        protected override void BuildTargetModel(ModelBuilder modelBuilder)
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

                    b.Property<double>("Confidence")
                        .HasColumnType("float");

                    b.Property<string>("Description")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

                    b.Property<double>("ElapsedSeconds")
                        .HasColumnType("float");

                    b.Property<string>("FileHash")
                        .IsRequired()
                        .HasColumnType("nvarchar(max)");

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

                    b.Property<string>("StoredFilePath")
                        .IsRequired()
                        .HasMaxLength(100)
                        .HasColumnType("nvarchar(100)");

                    b.HasKey("Id");

                    b.HasIndex("AnalysisDate");

                    b.HasIndex("BirdId");

                    b.HasIndex("StoredFilePath")
                        .IsUnique();

                    b.HasIndex("LegacySource", "LegacyId")
                        .IsUnique()
                        .HasFilter("[LegacySource] IS NOT NULL AND [LegacyId] IS NOT NULL");

                    b.ToTable("Analyses", t =>
                        {
                            t.HasCheckConstraint("CK_Analysis_Confidence", "[Confidence] >= 0 AND [Confidence] <= 1");

                            t.HasCheckConstraint("CK_Analysis_Type", "[AnalysisType] IN ('image','audio')");
                        });
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

            modelBuilder.Entity("BirdLab.Api.Models.Analysis", b =>
                {
                    b.HasOne("BirdLab.Api.Models.Bird", "Bird")
                        .WithMany()
                        .HasForeignKey("BirdId")
                        .OnDelete(DeleteBehavior.Restrict);

                    b.Navigation("Bird");
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

            modelBuilder.Entity("BirdLab.Api.Models.Prediction", b =>
                {
                    b.HasOne("BirdLab.Api.Models.Analysis", "Analysis")
                        .WithMany("Predictions")
                        .HasForeignKey("AnalysisId")
                        .OnDelete(DeleteBehavior.Cascade)
                        .IsRequired();

                    b.Navigation("Analysis");
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
