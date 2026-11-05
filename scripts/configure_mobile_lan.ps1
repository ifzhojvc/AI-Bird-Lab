param([string]$Address)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Address) {
    $network = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1
    if (-not $network) { throw 'Не знайдено мережу з IPv4-шлюзом. Передайте -Address вручну.' }
    $Address = $network.IPv4Address.IPAddress | Select-Object -First 1
}
$parsed = $null
if (-not [System.Net.IPAddress]::TryParse($Address, [ref]$parsed) -or [System.Net.IPAddress]::IsLoopback($parsed) -or $parsed.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) { throw "Вкажіть IPv4-адресу комп’ютера в локальній мережі." }
$target = Join-Path $projectRoot 'mobile-app\.env'
$lines = if (Test-Path -LiteralPath $target) { @(Get-Content -LiteralPath $target | Where-Object { $_ -notmatch '^EXPO_PUBLIC_API_URL=' }) } else { @() }
$lines += "EXPO_PUBLIC_API_URL=http://${Address}:5100"
[System.IO.File]::WriteAllLines($target, $lines)
Write-Output "API для iPhone: http://${Address}:5100/api/health"
Write-Output 'Після зміни адреси перезапустіть Expo: npm start -- --clear'
