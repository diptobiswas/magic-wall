# Execution Plan: World Machine Briefing

## Goal

Change Magic Wall from single-story meme wallpaper into a multi-story, medium-quality World Machine infographic with a readable touch briefing.

## Current state

The generator selects one story, builds an intentionally chaotic AI-slop prompt, and stores one `story` object. The touch overlay shows a selected story plus metadata, but text can wrap tightly and lose meaning on the 7-inch display.

## Target state

Each generation selects a small briefing of current stories, generates a World Machine Report style infographic at medium quality, and stores both the primary `story` and a `briefing` list. The touch overlay shows the briefing as readable article modules with short summaries and sources.

## Steps

- [x] Add briefing selection from source-mesh candidates.
- [x] Replace AI-slop image prompt with World Machine infographic prompt.
- [x] Switch default image quality to medium.
- [x] Redesign the touch overlay for readable briefing modules.
- [x] Update tests and docs.
- [x] Verify locally.
- [x] Deploy to the Raspberry Pi and verify service health.

## Verification

- `.venv/bin/python -m pytest`
- `.venv/bin/python -m compileall -q src tests`
- Local app boot and API/UI smoke check.
- Pi deploy script, `/healthz`, and `/api/state`.

## Decisions

- Keep `story` in API state for backward compatibility and add `briefing` for the new multi-story experience.
- Use source-mesh ranking for the briefing to avoid extra paid web-search calls in the normal path.

## Open questions

- Whether future versions should ask the text model to rewrite briefing summaries for stronger on-image phrasing.

## Completion notes

Built and deployed the World Machine briefing flow. New generations select 3 to 5 stories, rewrite them into complete sector labels, generate medium-quality World Machine Report infographics, and expose a `briefing` list in state while keeping `story` for compatibility. The Pi was updated to `image_quality = "medium"`, regenerated successfully, and reported active app and kiosk services.
