# Deployment

Magic Wall is designed for a Raspberry Pi running the local service and Chromium kiosk mode.

## Install

```sh
./install.sh
```

The installer creates a virtual environment, installs the package, and writes user-level systemd services.

## Runtime URL

```text
http://127.0.0.1:8765
```

## Config

Default config:

```text
~/.config/magic-wall/config.toml
```

Optional keys:

- `OPENAI_API_KEY`: art generation.
- `XAI_API_KEY` or `GROK_API_KEY`: xAI X Pulse search.

The app can boot without either key. Free public feeds power dashboard checks when xAI is not configured.
Art generation also checks public feeds before using OpenAI web search, but image generation still requires `OPENAI_API_KEY`.

## Verify On Pi

```sh
systemctl --user status magic-wall.service
systemctl --user status magic-wall-kiosk.service
curl http://127.0.0.1:8765/healthz
curl http://127.0.0.1:8765/api/state
```

After deploying UI changes, restart `magic-wall-kiosk.service` so the touchscreen reloads Chromium. The app sends no-cache headers for the kiosk shell and static assets to avoid stale dashboard code.
