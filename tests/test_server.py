from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from magic_wall.config import AppConfig
from magic_wall.server import create_app
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
    assert "/api/state" not in response.text
