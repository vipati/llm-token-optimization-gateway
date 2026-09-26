#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
demo_cache="cache/demo-cache.json"
context="data/examples/support_prompt.txt"
rm -f "$demo_cache"

echo "LLM Token Optimization Gateway Demo"
echo

echo "1. Count the original support prompt"
uv run token-gateway count "$context"
echo

echo "2. First request: compress the prompt and call the model"
uv run token-gateway complete "How do I reset my password?" "$context" --cache-file "$demo_cache"
echo

echo "3. Same request again: served from the exact cache, zero tokens sent"
uv run token-gateway complete "How do I reset my password?" "$context" --cache-file "$demo_cache"
echo

echo "4. Replay a 65-request support workload"
uv run token-gateway benchmark
