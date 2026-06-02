from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import AppConfig, ConfigError
from .generator import MagicWallGenerator
from .source_preview import fetch_source_preview
from .storage import WallStorage


KIOSK_NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def create_app(
    config: AppConfig,
    *,
    generator: MagicWallGenerator | None = None,
    storage: WallStorage | None = None,
    start_scheduler: bool = True,
) -> FastAPI:
    storage = storage or WallStorage(config)
    runtime_generator = generator
    static_dir = Path(str(files("magic_wall").joinpath("static")))
    lock = asyncio.Lock()

    def get_generator() -> MagicWallGenerator:
        nonlocal runtime_generator
        if runtime_generator is None:
            runtime_generator = MagicWallGenerator(config, storage=storage)
        return runtime_generator

    async def generate_locked() -> None:
        async with lock:
            try:
                await asyncio.to_thread(get_generator().generate_once)
            except ConfigError as exc:
                storage.mark_error(str(exc))
            except Exception as exc:  # pragma: no cover - defensive server boundary
                storage.mark_error(f"Generation failed: {exc}")

    async def scheduler_loop() -> None:
        while True:
            if _generation_due(storage):
                await generate_locked()
            await asyncio.sleep(min(30, max(1, config.refresh_seconds)))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        storage.ensure()
        if start_scheduler:
            app.state.scheduler_task = asyncio.create_task(scheduler_loop())
        try:
            yield
        finally:
            task = getattr(app.state, "scheduler_task", None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    app = FastAPI(title="Magic Wall", version="0.1.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.middleware("http")
    async def prevent_kiosk_shell_cache(request: Request, call_next):
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers.update(KIOSK_NO_CACHE_HEADERS)
        return response

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/state")
    async def state() -> dict:
        state_payload = storage.state_for_api()
        state_payload["setup_required"] = not bool(config.openai_api_key)
        return state_payload

    @app.post("/api/regenerate")
    async def regenerate() -> dict:
        if lock.locked():
            return {"status": "busy", "message": "A generation is already running."}
        asyncio.create_task(generate_locked())
        storage.mark_generating(message="Manual refresh started.")
        return {"status": "queued", "message": "Manual refresh started."}

    @app.get("/api/source-preview")
    async def source_preview(url: str) -> dict:
        try:
            preview = await asyncio.to_thread(fetch_source_preview, url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - network boundary
            raise HTTPException(status_code=502, detail=f"Source preview failed: {exc}") from exc
        return preview.to_dict()

    @app.get("/media/{name}", include_in_schema=False)
    async def media(name: str) -> FileResponse:
        if name != storage.current_image_path.name:
            raise HTTPException(status_code=404)
        if not storage.current_image_path.exists():
            raise HTTPException(status_code=404)
        media_type = "image/jpeg" if config.output_format == "jpeg" else f"image/{config.output_format}"
        return FileResponse(
            storage.current_image_path,
            media_type=media_type,
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True}

    return app


def run_server(config: AppConfig) -> None:
    import uvicorn

    uvicorn.run(create_app(config), host=config.host, port=config.port, log_level="info")


def _generation_due(storage: WallStorage) -> bool:
    state = storage.read_state()
    if state.get("status") in {"empty", "error"} and not storage.current_image_path.exists():
        return True
    next_refresh = storage.next_refresh_from_state()
    if next_refresh is None:
        return not storage.current_image_path.exists()
    return datetime.now(timezone.utc) >= next_refresh.astimezone(timezone.utc)
