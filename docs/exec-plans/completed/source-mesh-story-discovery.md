# Execution Plan: Source Mesh Story Discovery

## Goal

Lower hourly art-generation cost while improving story quality by replacing default paid web search with free/public candidate collection, local ranking, and cheap model selection.

## Current state

Art generation asks OpenAI web search to find and judge one story, then generates an image. Free public feeds are used only for the dashboard fallback.

## Target state

Art generation first builds a source mesh from public feeds, scores candidates locally, asks the text model to choose from finalists without web search, and only falls back to OpenAI web search when the mesh has no usable candidates.

## Steps

- [x] Add story candidate collection and scoring.
- [x] Add no-web model selection prompt and provider method.
- [x] Make the default generation provider use source mesh before paid search fallback.
- [x] Add regression tests for no paid search on usable candidates and fallback on empty mesh.
- [x] Update docs and cost notes.

## Verification

- `.venv/bin/python -m pytest`
- `.venv/bin/python -m compileall -q src tests`
- App boot and `/healthz` smoke check if available.

## Decisions

- Keep image generation on OpenAI.
- Keep paid web search as a fallback, not as the default hourly path.
- Prefer public/free source inputs that work for an open-source Pi appliance.

## Open questions

- Whether to add optional paid GDELT Cloud later for stronger global story clusters.

## Completion notes

Implemented `story_discovery.py`, added source-mesh prompt/provider support, switched generation defaults to source mesh, and documented the new cost/quality path.
