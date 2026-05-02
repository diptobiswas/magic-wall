#!/usr/bin/env bash
set -euo pipefail

PI_HOST="${PI_HOST:-dittoPi.local}"
PI_USER="${PI_USER:-ditto}"
PI_DIR="${PI_DIR:-/home/ditto/magic-wall}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${PI_USER}@${PI_HOST}"
REMOTE_DIR_Q="$(printf "%q" "${PI_DIR}")"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new)
RSYNC_RSH="ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"

cd "${ROOT_DIR}"

remote() {
  ssh "${SSH_OPTS[@]}" "${REMOTE}" "$@"
}

sync_dir() {
  local dir="$1"

  if [[ ! -d "${dir}" ]]; then
    return 0
  fi

  remote "mkdir -p ${REMOTE_DIR_Q}/$(printf "%q" "${dir}")"
  rsync -az --delete -e "${RSYNC_RSH}" "${dir}/" "${REMOTE}:${PI_DIR}/${dir}/"
}

printf 'Deploying Magic Wall to %s:%s\n' "${REMOTE}" "${PI_DIR}"
remote "mkdir -p ${REMOTE_DIR_Q}"

top_files=()
for file in AGENTS.md ARCHITECTURE.md README.md WORKFLOW.md pyproject.toml install.sh LICENSE SECURITY.md .env.example; do
  if [[ -e "${file}" ]]; then
    top_files+=("${file}")
  fi
done

rsync -az -e "${RSYNC_RSH}" "${top_files[@]}" "${REMOTE}:${PI_DIR}/"

sync_dir src
sync_dir docs
sync_dir tests
sync_dir scripts

remote "PI_DIR=${REMOTE_DIR_Q} bash -s" <<'REMOTE'
set -euo pipefail

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
cd "${PI_DIR}"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -e .
.venv/bin/python -m compileall -q src tests

has_user_unit() {
  systemctl --user cat "$1" >/dev/null 2>&1
}

if ! has_user_unit magic-wall.service; then
  ./install.sh
else
  systemctl --user daemon-reload
  systemctl --user restart magic-wall.service

  if has_user_unit magic-wall-kiosk.service; then
    systemctl --user restart magic-wall-kiosk.service
  fi
fi

for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8765/healthz >/tmp/magic-wall-healthz.json 2>/dev/null; then
    break
  fi

  if [[ "${attempt}" -eq 30 ]]; then
    echo "Magic Wall did not become healthy after restart." >&2
    systemctl --user --no-pager --plain status magic-wall.service >&2 || true
    exit 1
  fi

  sleep 1
done
curl -fsS http://127.0.0.1:8765/api/state >/tmp/magic-wall-state.json

systemctl --user --no-pager --plain is-active magic-wall.service
if has_user_unit magic-wall-kiosk.service; then
  systemctl --user --no-pager --plain is-active magic-wall-kiosk.service
fi
REMOTE

printf 'Deployed Magic Wall to %s\n' "${REMOTE}"
