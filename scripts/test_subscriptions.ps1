param([switch]$Sql)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if ($Sql -and !$env:BIRDLAB_TEST_SQL) { $env:BIRDLAB_TEST_SQL = 'Server=.\SQLEXPRESS;Database=master;Trusted_Connection=True;TrustServerCertificate=True' }
$resultName = if ($Sql) { 'subscriptions-sql.trx' } else { 'subscriptions-unit.trx' }
dotnet build central-server.Tests --no-restore -t:Rebuild
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
dotnet test central-server.Tests --no-build --no-restore --logger "trx;LogFileName=$resultName" --results-directory verification
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
[xml]$result = Get-Content -LiteralPath (Join-Path $projectRoot "verification\$resultName") -Raw
if ([int]$result.TestRun.ResultSummary.Counters.executed -eq 0) { throw 'No tests executed; do not treat discovery or application-control failures as success' }
if ($Sql -and [int]$result.TestRun.ResultSummary.Counters.notExecuted -ne 0) { throw 'SQL checks were skipped' }
