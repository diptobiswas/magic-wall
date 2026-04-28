# Magic Wall Workflow

Magic Wall is ready for agent-orchestrated work, but no external task system is required.

## Context

Interpret issues or user requests as product changes to the local Raspberry Pi appliance unless stated otherwise. Keep the app runnable with missing optional API keys.

## Implementation

- Reproduce bugs when practical.
- Keep UI state rendering in `static/` and domain/runtime logic in Python modules.
- Add or update tests for deterministic behavior.
- Keep changes scoped to the request.

## Verification

Run the relevant subset, normally:

```sh
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src tests
```

For UI work, also boot the app and inspect the page.

## Docs

Update `README.md`, `ARCHITECTURE.md`, and focused docs under `docs/` when behavior changes.

## Regression Tests

Add regression tests for important deterministic bugs and provider/storage/server contracts.

## Handoff

Report what changed, files changed, verification, notes or risks, and commit status.

## Commit Policy

Do not commit automatically. Ask after a complete verified change.
