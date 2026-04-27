#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_DIR="${ROOT_DIR}/.venv"
HOST="${MAGIC_WALL_HOST:-127.0.0.1}"
PORT="${MAGIC_WALL_PORT:-8765}"
DRY_RUN=0

if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
fi

APP_SERVICE="$HOME/.config/systemd/user/magic-wall.service"
KIOSK_SERVICE="$HOME/.config/systemd/user/magic-wall-kiosk.service"
PYTHON_BIN="${VENV_DIR}/bin/python"
MAGIC_WALL_BIN="${VENV_DIR}/bin/magic-wall"
URL="http://${HOST}:${PORT}"

detect_chromium() {
  if command -v chromium-browser >/dev/null 2>&1; then
    command -v chromium-browser
  elif command -v chromium >/dev/null 2>&1; then
    command -v chromium
  else
    printf '%s' chromium-browser
  fi
}

CHROMIUM_BIN=$(detect_chromium)

render_app_service() {
  cat <<EOF
[Unit]
Description=Magic Wall local art service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${ROOT_DIR}
ExecStart=${MAGIC_WALL_BIN} run --host ${HOST} --port ${PORT}
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF
}

render_kiosk_service() {
  cat <<EOF
[Unit]
Description=Magic Wall Chromium kiosk
After=magic-wall.service graphical-session.target
Wants=magic-wall.service

[Service]
Type=simple
ExecStart=/bin/sh -lc '${CHROMIUM_BIN} --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble --check-for-update-interval=31536000 ${URL}'
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
}

if [ "$DRY_RUN" = "1" ]; then
  printf '%s\n' "Would install Magic Wall from: ${ROOT_DIR}"
  printf '%s\n\n' "Would create virtualenv: ${VENV_DIR}"
  printf '%s\n' "--- ${APP_SERVICE} ---"
  render_app_service
  printf '%s\n' "--- ${KIOSK_SERVICE} ---"
  render_kiosk_service
  exit 0
fi

python3 -m venv "$VENV_DIR"
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -e "$ROOT_DIR"
"$MAGIC_WALL_BIN" init

mkdir -p "$HOME/.config/systemd/user"
render_app_service > "$APP_SERVICE"
render_kiosk_service > "$KIOSK_SERVICE"

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload
  systemctl --user enable --now magic-wall.service
  systemctl --user enable --now magic-wall-kiosk.service
  printf '%s\n' "Magic Wall is running at ${URL}"
else
  printf '%s\n' "Installed Magic Wall. Start it with: ${MAGIC_WALL_BIN} run --host ${HOST} --port ${PORT}"
fi
