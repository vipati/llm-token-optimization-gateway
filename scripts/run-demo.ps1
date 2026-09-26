$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")
$demoCache = "cache/demo-cache.json"
$context = "data/examples/support_prompt.txt"
if (Test-Path -LiteralPath $demoCache) {
    Remove-Item -LiteralPath $demoCache -Force
}

Write-Host "LLM Token Optimization Gateway Demo"
Write-Host ""

Write-Host "1. Count the original support prompt"
uv run token-gateway count $context
Write-Host ""

Write-Host "2. First request: compress the prompt and call the model"
uv run token-gateway complete "How do I reset my password?" $context --cache-file $demoCache
Write-Host ""

Write-Host "3. Same request again: served from the exact cache, zero tokens sent"
uv run token-gateway complete "How do I reset my password?" $context --cache-file $demoCache
Write-Host ""

Write-Host "4. Replay a 65-request support workload"
uv run token-gateway benchmark
