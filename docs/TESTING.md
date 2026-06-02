# Testing

## Commands

```sh
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src tests
```

## Coverage Focus

- Config defaults and secret redaction.
- World Machine prompt construction and JSON extraction.
- Source-mesh story ranking, no-web selection, and paid-search fallback behavior.
- Art generation state writes, including compatibility `story` and multi-story `briefing`.
- Legacy dashboard state removal from API responses.
- Server endpoints for state and art refresh.
- Installer service rendering.

## Manual UI Check

Boot the app, open `http://127.0.0.1:8765`, and verify:

- Briefing overlay renders without overlap.
- Article chamber rows, source link, and metadata are legible.
- Source links open a readable in-app preview, never a new tab, and the `Briefing` button returns without losing kiosk context.
- `Hide` and `New art` buttons respond.
- Empty, generating, ready, and error states are legible.
