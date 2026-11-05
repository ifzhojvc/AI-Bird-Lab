param([switch]$BaseSepolia)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
foreach ($line in Get-Content -LiteralPath (Join-Path $projectRoot '.env')) {
    if ($line -match '^([A-Z][A-Z0-9_]*)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim().Trim('"').Trim("'"), 'Process') }
}
$env:ASPNETCORE_ENVIRONMENT = 'Development'
$env:RabbitMQ__Username = $env:RABBITMQ_USERNAME
$env:RabbitMQ__Password = $env:RABBITMQ_PASSWORD
$env:AiServer__InternalKey = $env:AI_INTERNAL_KEY
if (!$BaseSepolia) {
    $deployment = Get-Content -LiteralPath (Join-Path $projectRoot 'verification\local-deployment.json') -Raw | ConvertFrom-Json
    if ($deployment.chainId -ne 31337 -or !$deployment.testOnly) { throw 'Expected a local Anvil deployment' }
    $env:Blockchain__Enabled = 'true'
    $env:Blockchain__TestMode = 'true'
    $env:Blockchain__AllowLocalAnvil = 'true'
    $env:Blockchain__ChainId = '31337'
    $env:Blockchain__RpcUrl = $deployment.rpcUrl
    $env:Blockchain__PublicRpcUrl = $deployment.rpcUrl
    $env:Blockchain__TokenAddress = $deployment.tokenAddress
    $env:Blockchain__PaymentContractAddress = $deployment.paymentContractAddress
    $env:Blockchain__Confirmations = '3'
} else {
    if ($env:BLOCKCHAIN_CHAIN_ID -and $env:BLOCKCHAIN_CHAIN_ID -ne '84532') { throw 'Base Sepolia only' }
    $env:Blockchain__Enabled = $env:BLOCKCHAIN_ENABLED
    $env:Blockchain__TestMode = 'true'
    $env:Blockchain__AllowLocalAnvil = 'false'
    $env:Blockchain__ChainId = '84532'
    $env:Blockchain__RpcUrl = $env:BLOCKCHAIN_RPC_URL
    $env:Blockchain__PublicRpcUrl = $env:BLOCKCHAIN_PUBLIC_RPC_URL
    $env:Blockchain__TokenAddress = $env:BLOCKCHAIN_TOKEN_ADDRESS
    $env:Blockchain__PaymentContractAddress = $env:BLOCKCHAIN_PAYMENT_CONTRACT_ADDRESS
    $env:Blockchain__Confirmations = $env:BLOCKCHAIN_CONFIRMATIONS
}
if ($env:SIWE_DOMAIN) { $env:Blockchain__SiweDomain = $env:SIWE_DOMAIN }
if ($env:SIWE_URI) { $env:Blockchain__SiweUri = $env:SIWE_URI }
dotnet run --project central-server
exit $LASTEXITCODE
