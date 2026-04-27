# Magic Wall

Magic Wall turns a Raspberry Pi touchscreen into a living AI news-meme frame.

Six times per day, it asks OpenAI web search for a real current news story, turns that story into a maximalist AI-slop meme poster with GPT Image, and displays only the generated artwork fullscreen. Tap the screen to reveal the story source, timestamp, settings, and regenerate button.

It is built for a Raspberry Pi with a 7-inch touchscreen, but it also runs on any machine with Python 3.11+ and a browser.

## What It Does

- Uses only the OpenAI API at runtime.
- Prefers news from the last hour.
- If the last-hour window is thin, uses the biggest verifiable story of the day instead.
- Generates an intentionally outrageous AI-slop news meme poster.
- Keeps the visible display clean: just the artwork until the screen is tapped.
- Allows one short readable meme caption inside the image.
- Uses public-figure caricatures only when they are central to the story.
- Runs locally on the device with a user-provided OpenAI API key.
- Refreshes every 4 hours by default, for 6 generated images per day.

## Demo Behavior

Each generation follows this rough flow:

1. Search current news with OpenAI web search.
2. Select one real, sourced story.
3. Compress the story into a short meme-label title.
4. Generate a chaotic landscape artwork with the story as the visual anchor.
5. Atomically replace the current image on the local kiosk page.

The output style is intentionally absurd: glossy, overcrowded, cinematic, neon, meme-readable, and funny on inspection.

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

## Privacy And Safety

- No external news API is used.
- Runtime network calls go to OpenAI only.
- The OpenAI key is stored locally in `~/.config/magic-wall/config.toml`.
- Generated images and state are stored locally in `~/.local/share/magic-wall/`.
- Local runtime folders, generated images, logs, virtual environments, caches, and archives are ignored by git.
- Do not commit `config.toml`, `.env`, generated images, or runtime logs.

Before publishing, run:

```sh
rg -n --hidden "sk-|OPENAI_API_KEY|api_key|password|secret|token" .
```

## Cost Notes

The default image quality is `low` because the display is small and the default cadence is only six generations per day. You can switch to `medium` or `high` in the config when you want richer images.

## License

MIT
