# Execution Plan: Life Dashboard

## Goal

Turn Magic Wall from a pure news-art frame into a touch-optimized X Pulse display that keeps the playful image layer while surfacing useful hourly signals from X.

## Current state

Magic Wall ran a local FastAPI kiosk, generated news-art through OpenAI, stored one state file, and showed a fullscreen image with a tap-to-open details overlay.

## Target state

The app keeps ambient artwork, adds an hourly X Pulse refresh, exposes a touch API for manual signal refresh, and uses direct X links rather than an embedded webview.

## Steps

- [x] Add dashboard signal models, config, prompts, storage, and provider boundary.
- [x] Add scheduler/API support for hourly signal checks.
- [x] Rebuild the static kiosk UI into a touch-first dashboard.
- [x] Update tests and docs.
- [x] Verify locally.
- [x] Deploy and verify on the Raspberry Pi.

## Verification

- `.venv/bin/python -m pytest`
- `.venv/bin/python -m compileall -q src tests`
- `node --check src/magic_wall/static/app.js`
- Local browser smoke check: default art-only view, tap-to-open dashboard, Hide action, X sheet.
- Raspberry Pi service check: `systemctl --user is-active magic-wall.service`
- Raspberry Pi endpoint checks: `/healthz`, `/`, `/static/app.js`, dashboard `check-now`

## Decisions

- Keep image generation separate from hourly dashboard checks to control cost.
- Prefer free feed checks when no xAI key is configured.
- Use xAI X Search only when an xAI/Grok key is configured.
- Treat embedded X as out of scope because X may require login or block iframe rendering.
- Make the 7-inch landscape UI art-first: information is hidden until touch and can be hidden again.

## Open questions

- Whether to store an xAI key on the Pi for X-native search, or keep the default free-feed mode.

## Completion notes

Implemented and deployed to `dittoPi`. The Pi is serving the updated touch-catcher UI and the user service is active.
