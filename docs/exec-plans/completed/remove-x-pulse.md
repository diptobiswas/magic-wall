# Execution Plan: Remove X Pulse

## Goal

Remove the unreliable X Pulse feature and make the touch overlay show only the news context behind the current wallpaper.

## Current state

Magic Wall runs separate art generation and dashboard/X signal refresh loops. The UI opens an X Pulse overlay and calls `/api/check-now`.

## Target state

Magic Wall generates news-based art, stores the selected story, and shows that story's title, summary, source, timing, and generation metadata on touch. No X, xAI, dashboard refresh, or check-now flow remains.

## Steps

- [x] Remove dashboard/xAI config, server scheduling, storage API fields, CLI command, and prompt/model helpers.
- [x] Replace the kiosk overlay with current-story details and an art regenerate action.
- [x] Update tests and docs to describe the simplified news-art appliance.
- [x] Run tests, compile check, and a local app boot smoke check.

## Verification

- `.venv/bin/python -m pytest`
- `.venv/bin/python -m compileall -q src tests`
- Local server boot plus `/healthz` and `/api/state` checks.

## Decisions

- Keep existing generated state readable, but stop exposing stale `dashboard` data through `/api/state`.
- Existing config files may still contain old `[xai]` and `[dashboard]` sections; the loader ignores them.

## Open questions

- None.

## Completion notes

Removed the X Pulse pipeline and changed the kiosk overlay to current-story details only. Verified tests, compile, server boot, API state, static assets, and a Safari render/touch smoke check.
