$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
foreach ($line in Get-Content -LiteralPath (Join-Path $projectRoot '.env')) {
    if ($line -match '^([A-Z][A-Z0-9_]*)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim().Trim('"').Trim("'"), 'Process') }
}
& (Join-Path $projectRoot '.venv\Scripts\python.exe') -m uvicorn ai_api.app:app --app-dir ai-server --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
