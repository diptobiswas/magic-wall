# Testing

## Commands

```sh
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src tests
```

## Coverage Focus

- Config defaults and secret redaction.
- Prompt construction and JSON extraction.
- Source-mesh story ranking, no-web selection, and paid-search fallback behavior.
- Art generation state writes.
- Dashboard signal scheduling and storage.
- Server endpoints for state, art refresh, and dashboard check.
- Installer service rendering.

## Manual UI Check

Boot the app, open `http://127.0.0.1:8765`, and verify:

- Dashboard panels render without overlap.
- Category tabs and cards are touchable.
- `Check`, `Art`, `X`, and `Focus` buttons respond.
- Empty, checking, and ready states are legible.
