from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from magic_wall.config import AppConfig
import magic_wall.server as server_module
from magic_wall.server import create_app
from magic_wall.source_preview import SourcePreview
from magic_wall.storage import WallStorage


def test_state_api_redacts_key_and_serves_image_url(tmp_path: Path) -> None:
    cfg = AppConfig(
        config_path=tmp_path / "config.toml",
        data_dir=tmp_path / "data",
        openai_api_key="sk-secret",
    )
    storage = WallStorage(cfg)
    storage.write_current_image(b"fake-image")
    storage.write_state({"status": "ready", "story": {"title": "A story"}, "generation_count": 1})

    app = create_app(cfg, storage=storage, start_scheduler=False)
    client = TestClient(app)

    response = client.get("/api/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["image_url"].startswith("/media/current.jpg")
    assert "sk-secret" not in response.text


def test_index_is_pure_art_shell_without_visible_news_card(tmp_path: Path) -> None:
    cfg = AppConfig(config_path=tmp_path / "config.toml", data_dir=tmp_path / "data")
    app = create_app(cfg, start_scheduler=False)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert 'class="wallpaper"' in response.text
    assert 'id="story-sheet"' in response.text
    assert 'id="source-viewer"' in response.text
    assert 'id="close-source"' in response.text
    assert "Open tab" not in response.text
    assert "<iframe" not in response.text
    assert "X Pulse" not in response.text
    assert 'aria-hidden="true"' in response.text
    assert "/api/state" not in response.text


def test_source_preview_rejects_non_web_urls(tmp_path: Path) -> None:
    cfg = AppConfig(config_path=tmp_path / "config.toml", data_dir=tmp_path / "data")
    app = create_app(cfg, start_scheduler=False)
    client = TestClient(app)

    response = client.get("/api/source-preview", params={"url": "file:///etc/passwd"})

    assert response.status_code == 400


def test_source_preview_returns_kiosk_safe_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_fetch(url: str) -> SourcePreview:
        return SourcePreview(
            url=url,
            title="Readable article",
            description="A short source preview.",
            paragraphs=["The article body is rendered inside Magic Wall."],
            site="example.com",
        )

    monkeypatch.setattr(server_module, "fetch_source_preview", fake_fetch)
    cfg = AppConfig(config_path=tmp_path / "config.toml", data_dir=tmp_path / "data")
    app = create_app(cfg, start_scheduler=False)
    client = TestClient(app)

    response = client.get("/api/source-preview", params={"url": "https://example.com/story"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Readable article"
    assert payload["paragraphs"] == ["The article body is rendered inside Magic Wall."]


def test_kiosk_shell_and_assets_disable_browser_cache(tmp_path: Path) -> None:
    cfg = AppConfig(config_path=tmp_path / "config.toml", data_dir=tmp_path / "data")
    app = create_app(cfg, start_scheduler=False)
    client = TestClient(app)

    index_response = client.get("/")
    script_response = client.get("/static/app.js")

    assert "no-store" in index_response.headers["Cache-Control"]
    assert "no-store" in script_response.headers["Cache-Control"]
    assert index_response.headers["Pragma"] == "no-cache"
    assert script_response.headers["Expires"] == "0"


def test_check_now_endpoint_is_removed(tmp_path: Path) -> None:
    cfg = AppConfig(config_path=tmp_path / "config.toml", data_dir=tmp_path / "data")
    storage = WallStorage(cfg)
    app = create_app(cfg, storage=storage, start_scheduler=False)
    client = TestClient(app)

    response = client.post("/api/check-now")

    assert response.status_code == 404
    assert "dashboard" not in storage.state_for_api()
