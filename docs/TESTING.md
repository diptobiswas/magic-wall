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
- Legacy dashboard state removal from API responses.
- Server endpoints for state and art refresh.
- Installer service rendering.

## Manual UI Check

Boot the app, open `http://127.0.0.1:8765`, and verify:

- Story overlay renders without overlap.
- Source link and metadata rows are legible.
- `Hide` and `New art` buttons respond.
- Empty, generating, ready, and error states are legible.
