# Architecture

Magic Wall is a local FastAPI kiosk app for a Raspberry Pi touchscreen.

## Runtime Shape

- `config.py`: local TOML/env configuration, key discovery, validation.
- `storage.py`: atomic image and JSON state persistence.
- `generator.py`: OpenAI news-art generation workflow.
- `story_discovery.py`: public source mesh, candidate scoring, and paid-search fallback routing.
- `dashboard.py`: hourly life-dashboard signal workflow.
- `openai_provider.py`: OpenAI web search and image boundary.
- `server.py`: FastAPI routes, scheduler, and static UI hosting.
- `static/`: touch-first kiosk UI that renders `/api/state`.

## Data Flow

1. Scheduler checks whether art generation or dashboard signals are due.
2. Art generation collects public story candidates, ranks them locally, selects a finalist, generates an image, and writes image/state.
3. Dashboard refresh gathers low-cost/free signals or xAI X/Web Search results.
4. Static UI polls `/api/state`, renders the dashboard, and queues manual refreshes.

## Provider Boundaries

- OpenAI is used for art generation, no-web finalist selection, and paid web-search fallback when source mesh discovery is empty.
- xAI is optional and used only for dashboard X/Web signal checks.
- Free public feeds are the default story discovery layer and the dashboard fallback when xAI is not configured.

## State

The app stores one JSON state file and current image under the configured data directory. API keys are never included in API responses.

## UI Boundary

The browser owns layout and local interaction only. It does not choose stories, call third-party APIs, or mutate state except through local FastAPI routes.
