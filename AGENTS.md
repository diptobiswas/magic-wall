# Magic Wall

Raspberry Pi touchscreen appliance that blends ambient AI news-art with an hourly life-dashboard signal.

## Repo Map

- `src/magic_wall/`: Python package, FastAPI server, providers, storage, static kiosk UI.
- `src/magic_wall/static/`: touch dashboard HTML, CSS, and JavaScript.
- `tests/`: unit and API regression tests.
- `docs/`: product, architecture, deployment, testing, and execution plans.
- `install.sh`: Raspberry Pi install entrypoint.

## Commands

- Install: `.venv/bin/python -m pip install -e ".[dev]"`
- Run: `.venv/bin/magic-wall run`
- Generate art: `.venv/bin/magic-wall generate-now`
- Check dashboard: `.venv/bin/magic-wall check-now`
- Test: `.venv/bin/python -m pytest`
- Compile: `.venv/bin/python -m compileall -q src tests`

## Boundaries

- UI renders state only; business logic stays in providers, generator, storage, and server modules.
- OpenAI image/news-art generation and xAI dashboard search are separate provider boundaries.
- Runtime config and generated files must stay outside git.

## Verification

- Run tests and compile check before handoff.
- For UI changes, boot the app and inspect the kiosk page.
- For Pi changes, verify the user service and `http://127.0.0.1:8765/healthz`.

## Docs

Start with `README.md`, `ARCHITECTURE.md`, `WORKFLOW.md`, and `docs/PRODUCT.md`.

## Do Not

- Do not commit API keys, `config.toml`, generated images, logs, or runtime data.
- Do not make hourly dashboard checks depend on image generation.
- Do not make X required for the app to boot.

## Documentation Updates

When behavior changes, update the relevant docs in `docs/` and move completed execution plans to `docs/exec-plans/completed/`.
