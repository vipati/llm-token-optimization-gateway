# Demo Recording Guide

## Recommended Demo Format

Use a short terminal recording or GIF, around 30 to 45 seconds.

The strongest demo story is:

1. Show the original prompt token count.
2. Run the optimized completion once.
3. Show token reduction and cost-saving metrics.
4. Run the same request again.
5. Show the cache hit.

## Run The Demo

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-demo.ps1
```

## Generated Recording

The committed GIF demo is available at:

```text
docs/assets/token-gateway-demo.gif
```

To regenerate it:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-demo.ps1 | Tee-Object -FilePath reports\demo-output.txt
uv run --with pillow python scripts\render-demo-gif.py
```

## What The Demo Proves

- The gateway sits between the app and the local LLM service.
- The local LLM still returns a useful answer.
- The gateway reduces tokens before model execution.
- Repeated optimized prompts are served from cache.
- Token savings are measured instead of assumed.

## Best Recording Options

Recommended:

- Use ScreenToGif on Windows for a quick GIF.
- Use OBS Studio for a polished MP4.
- Use a terminal recorder if you want a clean command-line demo.

For GitHub README usage:

- Keep GIFs under 10 MB when possible.
- Prefer MP4 for LinkedIn or portfolio sites.
- Put final media under `docs/assets/`.
- Name files clearly, for example `docs/assets/token-gateway-demo.gif`.

## Suggested Script

```text
This project reduces LLM token usage before a request reaches the local model service.

First, I count the original prompt.
Then I run a completion through the gateway.
The gateway removes duplicate lines, keeps relevant context, and reports token savings.
Finally, I run the same request again to show the exact cache hit.
```

## Future Visual Demo

A Streamlit dashboard would make a stronger visual demo later:

- before and after prompt
- tokens before and after
- reduction percentage
- estimated cost saved
- cache hit or miss
- local LLM response
