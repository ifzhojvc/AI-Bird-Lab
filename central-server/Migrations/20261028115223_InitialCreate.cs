using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace BirdLab.Api.Migrations
{
    public partial class InitialCreate : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Birds",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    CommonName = table.Column<string>(type: "nvarchar(256)", maxLength: 256, nullable: false),
                    UkrainianName = table.Column<string>(type: "nvarchar(256)", maxLength: 256, nullable: false),
                    ScientificName = table.Column<string>(type: "nvarchar(256)", maxLength: 256, nullable: false),
                    Family = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    Habitat = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    Distribution = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    Diet = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    AverageSize = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    Description = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    ConservationStatus = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    SourceUrl = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    SourcesJson = table.Column<string>(type: "nvarchar(max)", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Birds", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Analyses",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    AnalysisType = table.Column<string>(type: "nvarchar(10)", maxLength: 10, nullable: false),
                    OriginalFileName = table.Column<string>(type: "nvarchar(255)", maxLength: 255, nullable: false),
                    StoredFilePath = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    FileHash = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    PredictedSpecies = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    Confidence = table.Column<double>(type: "float", nullable: false),
                    ModelName = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    ModelRevision = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    AnalysisDate = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    Description = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    ElapsedSeconds = table.Column<double>(type: "float", nullable: false),
                    MetadataJson = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    BirdSnapshotJson = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    LegacySource = table.Column<string>(type: "nvarchar(64)", maxLength: 64, nullable: true),
                    LegacyId = table.Column<int>(type: "int", nullable: true),
                    BirdId = table.Column<int>(type: "int", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Analyses", x => x.Id);
                    table.CheckConstraint("CK_Analysis_Confidence", "[Confidence] >= 0 AND [Confidence] <= 1");
                    table.CheckConstraint("CK_Analysis_Type", "[AnalysisType] IN ('image','audio')");
                    table.ForeignKey(
                        name: "FK_Analyses_Birds_BirdId",
                        column: x => x.BirdId,
                        principalTable: "Birds",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Evaluations",
                columns: table => new
                {
                    AnalysisId = table.Column<int>(type: "int", nullable: false),
                    ExpectedLabel = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    ExpectedScientific = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    LabelSource = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    FileHash = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    Top1Correct = table.Column<bool>(type: "bit", nullable: false),
                    Top3Correct = table.Column<bool>(type: "bit", nullable: false),
                    Experiment = table.Column<string>(type: "nvarchar(max)", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Evaluations", x => x.AnalysisId);
                    table.ForeignKey(
                        name: "FK_Evaluations_Analyses_AnalysisId",
                        column: x => x.AnalysisId,
                        principalTable: "Analyses",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "Predictions",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    AnalysisId = table.Column<int>(type: "int", nullable: false),
                    SpeciesName = table.Column<string>(type: "nvarchar(256)", maxLength: 256, nullable: false),
                    ScientificName = table.Column<string>(type: "nvarchar(256)", maxLength: 256, nullable: true),
                    Confidence = table.Column<double>(type: "float", nullable: false),
                    Rank = table.Column<int>(type: "int", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Predictions", x => x.Id);
                    table.CheckConstraint("CK_Prediction_Confidence", "[Confidence] >= 0 AND [Confidence] <= 1");
                    table.CheckConstraint("CK_Prediction_Rank", "[Rank] BETWEEN 1 AND 3");
                    table.ForeignKey(
                        name: "FK_Predictions_Analyses_AnalysisId",
                        column: x => x.AnalysisId,
                        principalTable: "Analyses",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_Analyses_AnalysisDate",
                table: "Analyses",
                column: "AnalysisDate");

            migrationBuilder.CreateIndex(
                name: "IX_Analyses_BirdId",
                table: "Analyses",
                column: "BirdId");

            migrationBuilder.CreateIndex(
                name: "IX_Analyses_LegacySource_LegacyId",
                table: "Analyses",
                columns: new[] { "LegacySource", "LegacyId" },
                unique: true,
                filter: "[LegacySource] IS NOT NULL AND [LegacyId] IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "IX_Analyses_StoredFilePath",
                table: "Analyses",
                column: "StoredFilePath",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Birds_ScientificName",
                table: "Birds",
                column: "ScientificName",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Predictions_AnalysisId_Rank",
                table: "Predictions",
                columns: new[] { "AnalysisId", "Rank" },
                unique: true);
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "Evaluations");

            migrationBuilder.DropTable(
                name: "Predictions");

            migrationBuilder.DropTable(
                name: "Analyses");

            migrationBuilder.DropTable(
                name: "Birds");
        }
    }
}
