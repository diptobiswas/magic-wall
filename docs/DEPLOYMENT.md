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

## Fast Deploy From This Mac

After SSH access is set up, deploy the current workspace to the Raspberry Pi with:

```sh
scripts/deploy-pi.sh
```

Defaults:

```text
PI_USER=ditto
PI_HOST=dittoPi.local
PI_DIR=/home/ditto/magic-wall
```

Override any of those values inline when needed:

```sh
PI_HOST=10.0.0.113 scripts/deploy-pi.sh
```

The deploy script syncs code, docs, tests, and top-level project files, reinstalls the local editable package on the Pi, compiles Python sources, restarts `magic-wall.service`, restarts `magic-wall-kiosk.service` when present, and checks the local health and state endpoints.

## Config

Default config:

```text
~/.config/magic-wall/config.toml
```

Optional keys:

- `OPENAI_API_KEY`: art generation.

The app can boot without an OpenAI key so setup and the local kiosk still load.
Art generation also checks public feeds before using OpenAI web search, but image generation still requires `OPENAI_API_KEY`.

## Verify On Pi

```sh
systemctl --user status magic-wall.service
systemctl --user status magic-wall-kiosk.service
curl http://127.0.0.1:8765/healthz
curl http://127.0.0.1:8765/api/state
```

After deploying UI changes, restart `magic-wall-kiosk.service` so the touchscreen reloads Chromium. The app sends no-cache headers for the kiosk shell and static assets to avoid stale UI code.
