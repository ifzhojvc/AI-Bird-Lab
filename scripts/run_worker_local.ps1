$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
foreach ($line in Get-Content -LiteralPath (Join-Path $projectRoot '.env')) {
    if ($line -match '^([A-Z][A-Z0-9_]*)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim().Trim('"').Trim("'"), 'Process') }
}
$env:BIRD_MEDIA_ROOT = Join-Path $projectRoot 'central-server\storage'
& (Join-Path $projectRoot '.venv\Scripts\python.exe') -X utf8 ai-server/worker.py
exit $LASTEXITCODE
