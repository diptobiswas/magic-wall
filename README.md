# Magic Wall

Magic Wall turns a Raspberry Pi touchscreen into an ambient AI news-art frame.

It finds a small set of current news stories, turns them into a wild but readable World Machine infographic, and shows the story context when you walk up and touch the screen.

It is built for a Raspberry Pi with a 7-inch touchscreen, but it also runs on any machine with Python 3.11+ and a browser.

## What It Does

- Uses OpenAI for story selection fallback and image generation.
- Builds a free public-source mesh for art story discovery before using paid web search.
- Prefers news from the last hour for the ambient briefing.
- If the last-hour window is thin, uses the biggest verifiable story of the day instead.
- Generates a medium-quality multi-story World Machine Report infographic.
- Shows a touch-first briefing overlay over the artwork.
- Uses large labels, article sectors, chart-like signals, and timeline/legend structure inside the image.
- Uses public-figure caricatures only when they are central to the story.
- Runs locally on the device with a user-provided OpenAI API key.
- Refreshes every 4 hours by default, for 6 generated images per day.

## Demo Behavior

Each generation follows this rough flow:

1. Collect current story candidates from public feeds such as Google News RSS and Hacker News.
2. Dedupe, cluster, and score candidates locally for freshness, source quality, traction, novelty, and visual potential.
3. Select a small briefing from the ranked source mesh without web search.
4. Fall back to OpenAI web search only when the public source mesh has no usable story.
5. Compress briefing titles for display and image labels.
6. Generate a World Machine Report infographic with each story as a visual sector.
7. Atomically replace the current image on the local kiosk page.

The output style is intentionally intense: an exploded-view planet machine with readable story sectors, timeline orbit, legend, symbols, and consequence tags.

On touch, the kiosk reveals only the information used for the current wallpaper: primary story, briefing sectors, summaries, sources, published times, generation time, next refresh, and style.

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
image_quality = "medium"
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

The default image quality is `medium` because the generated image now carries readable infographic structure. Art generation uses the source mesh before paid web search, so normal art mode should mostly pay for image generation plus source collection rather than a web-search tool call every cycle.

## Project Docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [WORKFLOW.md](WORKFLOW.md)
- [docs/PRODUCT.md](docs/PRODUCT.md)
- [docs/DESIGN.md](docs/DESIGN.md)
- [docs/TESTING.md](docs/TESTING.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## License

MIT
