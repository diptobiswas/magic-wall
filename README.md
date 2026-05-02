# Magic Wall

Magic Wall turns a Raspberry Pi touchscreen into an ambient AI news-art frame.

It finds a current news story, turns it into intentionally outrageous AI-slop wallpaper, and shows the story context when you walk up and touch the screen.

It is built for a Raspberry Pi with a 7-inch touchscreen, but it also runs on any machine with Python 3.11+ and a browser.

## What It Does

- Uses OpenAI for story selection fallback and image generation.
- Builds a free public-source mesh for art story discovery before using paid web search.
- Prefers news from the last hour for the ambient art story.
- If the last-hour window is thin, uses the biggest verifiable story of the day instead.
- Generates an intentionally outrageous AI-slop news meme poster.
- Shows a touch-first story details overlay over the artwork.
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

On touch, the kiosk reveals only the information used for the current wallpaper: title, summary, source, published time, generation time, next refresh, and style.

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

[refresh]
minutes = 240
news_window_minutes = 60

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

Deploy the current workspace to the Raspberry Pi after SSH is configured:

```sh
scripts/deploy-pi.sh
```

## Privacy And Safety

- Art story discovery uses public feeds first, then OpenAI web search only as a fallback.
- The OpenAI key is stored locally in `~/.config/magic-wall/config.toml`.
- Generated images and state are stored locally in `~/.local/share/magic-wall/`.
- Local runtime folders, generated images, logs, virtual environments, caches, and archives are ignored by git.
- Do not commit `config.toml`, `.env`, generated images, or runtime logs.

Before publishing, run:

```sh
rg -n --hidden "sk-|OPENAI_API_KEY|api_key|password|secret|token" .
```

## Cost Notes

The default image quality is `low` because the display is small and the default cadence is only six generations per day. Art generation uses the source mesh before paid web search, so normal hourly art mode should mostly pay for image generation plus a small text-model finalist selection rather than a web-search tool call every hour.

## Project Docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [WORKFLOW.md](WORKFLOW.md)
- [docs/PRODUCT.md](docs/PRODUCT.md)
- [docs/DESIGN.md](docs/DESIGN.md)
- [docs/TESTING.md](docs/TESTING.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## License

MIT
