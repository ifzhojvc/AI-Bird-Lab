using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace BirdLab.Api.Migrations
{
    public partial class AsyncMessaging : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<DateTimeOffset>(
                name: "CompletedAt",
                table: "Analyses",
                type: "datetimeoffset",
                nullable: true);

            migrationBuilder.AddColumn<Guid>(
                name: "CorrelationId",
                table: "Analyses",
                type: "uniqueidentifier",
                nullable: false,
                defaultValue: new Guid("00000000-0000-0000-0000-000000000000"));

            migrationBuilder.AddColumn<DateTimeOffset>(
                name: "CreatedAt",
                table: "Analyses",
                type: "datetimeoffset",
                nullable: false,
                defaultValue: new DateTimeOffset(new DateTime(1, 1, 1, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)));

            migrationBuilder.AddColumn<string>(
                name: "ErrorMessage",
                table: "Analyses",
                type: "nvarchar(2000)",
                maxLength: 2000,
                nullable: true);

            migrationBuilder.AddColumn<Guid>(
                name: "FileId",
                table: "Analyses",
                type: "uniqueidentifier",
                nullable: false,
                defaultValue: new Guid("00000000-0000-0000-0000-000000000000"));

            migrationBuilder.AddColumn<Guid>(
                name: "JobId",
                table: "Analyses",
                type: "uniqueidentifier",
                nullable: false,
                defaultValue: new Guid("00000000-0000-0000-0000-000000000000"));

            migrationBuilder.AddColumn<int>(
                name: "RetryCount",
                table: "Analyses",
                type: "int",
                nullable: false,
                defaultValue: 0);

            migrationBuilder.AddColumn<DateTimeOffset>(
                name: "StartedAt",
                table: "Analyses",
                type: "datetimeoffset",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Status",
                table: "Analyses",
                type: "nvarchar(16)",
                maxLength: 16,
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<DateTimeOffset>(
                name: "UpdatedAt",
                table: "Analyses",
                type: "datetimeoffset",
                nullable: false,
                defaultValue: new DateTimeOffset(new DateTime(1, 1, 1, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)));

            migrationBuilder.CreateTable(
                name: "InboxMessages",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    AnalysisId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    BodyHash = table.Column<string>(type: "nvarchar(64)", maxLength: 64, nullable: false),
                    ReceivedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_InboxMessages", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "OutboxMessages",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    AnalysisId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    Payload = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    CreatedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    NextAttemptAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    PublishedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: true),
                    Attempts = table.Column<int>(type: "int", nullable: false),
                    LastError = table.Column<string>(type: "nvarchar(2000)", maxLength: 2000, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_OutboxMessages", x => x.Id);
                });

            migrationBuilder.Sql("UPDATE [Analyses] SET [JobId] = NEWID(), [CorrelationId] = NEWID(), [FileId] = COALESCE(TRY_CONVERT(uniqueidentifier, STUFF(STUFF(STUFF(STUFF(LEFT([StoredFilePath], 32), 9, 0, '-'), 14, 0, '-'), 19, 0, '-'), 24, 0, '-')), NEWID()), [CreatedAt] = [AnalysisDate], [StartedAt] = [AnalysisDate], [CompletedAt] = [AnalysisDate], [UpdatedAt] = [AnalysisDate], [Status] = 'Completed'");

            migrationBuilder.CreateIndex(
                name: "IX_Analyses_JobId",
                table: "Analyses",
                column: "JobId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Analyses_Status_UpdatedAt",
                table: "Analyses",
                columns: new[] { "Status", "UpdatedAt" });

            migrationBuilder.AddCheckConstraint(
                name: "CK_Analysis_Status",
                table: "Analyses",
                sql: "[Status] IN ('Pending','Queued','Processing','Completed','Failed')");

            migrationBuilder.CreateIndex(
                name: "IX_InboxMessages_AnalysisId",
                table: "InboxMessages",
                column: "AnalysisId");

            migrationBuilder.CreateIndex(
                name: "IX_OutboxMessages_AnalysisId",
                table: "OutboxMessages",
                column: "AnalysisId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_OutboxMessages_PublishedAt_NextAttemptAt",
                table: "OutboxMessages",
                columns: new[] { "PublishedAt", "NextAttemptAt" });
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "InboxMessages");

            migrationBuilder.DropTable(
                name: "OutboxMessages");

            migrationBuilder.DropIndex(
                name: "IX_Analyses_JobId",
                table: "Analyses");

            migrationBuilder.DropIndex(
                name: "IX_Analyses_Status_UpdatedAt",
                table: "Analyses");

            migrationBuilder.DropCheckConstraint(
                name: "CK_Analysis_Status",
                table: "Analyses");

            migrationBuilder.DropColumn(
                name: "CompletedAt",
                table: "Analyses");

            migrationBuilder.DropColumn(
                name: "CorrelationId",
                table: "Analyses");

            migrationBuilder.DropColumn(
                name: "CreatedAt",
                table: "Analyses");

            migrationBuilder.DropColumn(
                name: "ErrorMessage",
                table: "Analyses");

            migrationBuilder.DropColumn(
                name: "FileId",
                table: "Analyses");

            migrationBuilder.DropColumn(
                name: "JobId",
                table: "Analyses");

            migrationBuilder.DropColumn(
                name: "RetryCount",
                table: "Analyses");

            migrationBuilder.DropColumn(
                name: "StartedAt",
                table: "Analyses");

            migrationBuilder.DropColumn(
                name: "Status",
                table: "Analyses");

            migrationBuilder.DropColumn(
                name: "UpdatedAt",
                table: "Analyses");
        }
    }
}
