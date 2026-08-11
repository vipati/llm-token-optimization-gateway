$ErrorActionPreference = "Stop"

Write-Host "LLM Token Optimization Gateway Demo"
Write-Host ""

$demoCache = "cache/demo-cache.json"
if (Test-Path -LiteralPath $demoCache) {
    Remove-Item -LiteralPath $demoCache -Force
}

Write-Host "1. Count the original support prompt"
uv run token-gateway count data/examples/support_prompt.txt
Write-Host ""

Write-Host "2. First completion: optimize prompt and call local LLM service"
uv run token-gateway complete "How do I reset my password?" data/examples/support_prompt.txt --cache-file $demoCache
Write-Host ""

Write-Host "3. Second completion: same request should hit exact cache"
uv run token-gateway complete "How do I reset my password?" data/examples/support_prompt.txt --cache-file $demoCache
