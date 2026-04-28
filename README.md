# Magic Wall

Magic Wall turns a Raspberry Pi touchscreen into a playful X Pulse display.

It keeps the living AI news-art layer, then adds hourly xAI-powered checks for what people are talking about on X. The result is still fun from across the room, but useful when you walk up and touch it.

It is built for a Raspberry Pi with a 7-inch touchscreen, but it also runs on any machine with Python 3.11+ and a browser.

## What It Does

- Uses OpenAI for image generation and optional xAI for X Pulse signal checks.
- Builds a free public-source mesh for art story discovery before using paid web search.
- Uses xAI/Grok API access for real X Search when configured.
- Falls back to free public feeds when xAI is not configured.
- Checks X Pulse signals every hour by default.
- Keeps image generation separate from low-cost signal checks.
- Prefers news from the last hour for the ambient art story.
- If the last-hour window is thin, uses the biggest verifiable story of the day instead.
- Generates an intentionally outrageous AI-slop news meme poster.
- Shows a touch-first X Pulse overlay over the artwork.
- Uses direct X topic links instead of an embedded X webview.
- Allows one short readable meme caption inside the image.
- Uses public-figure caricatures only when they are central to the story.
- Runs locally on the device with a user-provided OpenAI API key.
- Refreshes every 4 hours by default, for 6 generated images per day.

## Demo Behavior

Each generation follows this rough flow:

1. Collect current story candidates from public feeds such as Google News RSS and Hacker News.
2. Dedupe, cluster, and score candidates locally for freshness, source quality, traction, novelty, and visual potential.
3. Ask the configured OpenAI text model to choose from the finalist list without web search.
4. Fall back to OpenAI web search only when the public source mesh has no usable story.
5. Compress the chosen story into a short meme-label title.
6. Generate a chaotic landscape artwork with the story as the visual anchor.
7. Atomically replace the current image on the local kiosk page.

The output style is intentionally absurd: glossy, overcrowded, cinematic, neon, meme-readable, and funny on inspection.

X Pulse checks follow a separate flow:

1. If xAI is configured, use Grok with X Search to find current conversation signals.
2. If xAI is not configured, use free public feeds such as Google News RSS and Hacker News.
3. Store compact X Pulse cards for the local overlay.
4. Refresh the touchscreen without changing the current artwork.

## Install On Raspberry Pi

On the Pi:

```sh
git clone https://github.com/diptobiswas/magic-wall.git
cd magic-wall
./install.sh
```

The installer creates a Python virtual environment, installs Magic Wall, writes user-level systemd services, and launches Chromium in kiosk mode at:

```text
http://127.0.0.1:8765
```

For detailed touchscreen setup, see [docs/raspberry-pi.md](docs/raspberry-pi.md).

## OpenAI Key

Magic Wall is bring-your-own-key. Your key stays on your device.

The default config lives at:

```text
~/.config/magic-wall/config.toml
```

Generated images and metadata live at:

```text
~/.local/share/magic-wall/
```

You can also supply:

```sh
export OPENAI_API_KEY="sk-..."
```

Then initialize:

```sh
magic-wall init
```

Default config:

```toml
[openai]
api_key = ""
text_model = "gpt-5.4-mini"
image_model = "gpt-image-2"
image_quality = "low"
image_size = "1344x800"
output_format = "jpeg"

[xai]
api_key = ""
model = "grok-4"

[refresh]
minutes = 240
news_window_minutes = 60

[dashboard]
refresh_minutes = 60
categories = ["science", "technology", "pop culture", "world"]
x_view_url = "https://x.com/explore/tabs/trending"

[server]
host = "127.0.0.1"
port = 8765
timezone = "local"
```

## Commands

```sh
magic-wall init
magic-wall run
magic-wall generate-now
magic-wall check-now
magic-wall status
```

## Development

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
```

Run locally:

```sh
.venv/bin/magic-wall init
.venv/bin/magic-wall run
```

Open:

```text
http://127.0.0.1:8765
```

## Privacy And Safety

- Art story discovery uses public feeds first, then OpenAI web search only as a fallback.
- X Pulse calls use xAI only when configured; otherwise they use public feeds.
- The OpenAI key is stored locally in `~/.config/magic-wall/config.toml`.
- The xAI key can be stored in config or supplied as `XAI_API_KEY` / `GROK_API_KEY`.
- Generated images and state are stored locally in `~/.local/share/magic-wall/`.
- Local runtime folders, generated images, logs, virtual environments, caches, and archives are ignored by git.
- Do not commit `config.toml`, `.env`, generated images, or runtime logs.

Before publishing, run:

```sh
rg -n --hidden "sk-|OPENAI_API_KEY|api_key|password|secret|token" .
```

## Cost Notes

The default image quality is `low` because the display is small and the default cadence is only six generations per day. Hourly X Pulse checks do not generate images. Art generation uses the source mesh before paid web search, so normal hourly art mode should mostly pay for image generation plus a small text-model finalist selection rather than a web-search tool call every hour. xAI search tools may bill per tool invocation, so the app falls back to free feeds when no xAI key is configured.

## Project Docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [WORKFLOW.md](WORKFLOW.md)
- [docs/PRODUCT.md](docs/PRODUCT.md)
- [docs/DESIGN.md](docs/DESIGN.md)
- [docs/TESTING.md](docs/TESTING.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## License

MIT
