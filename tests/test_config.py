from __future__ import annotations

import os
from pathlib import Path

import pytest

from magic_wall.config import ConfigError, load_config, write_default_config


def test_loads_default_config_from_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("MAGIC_WALL_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("MAGIC_WALL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test_abcdefghijklmnopqrstuvwxyz")

    cfg = load_config()

    assert cfg.openai_api_key == "sk-test_abcdefghijklmnopqrstuvwxyz"
    assert cfg.image_model == "gpt-image-2"
    assert cfg.image_quality == "low"
    assert cfg.refresh_minutes == 240
    assert cfg.news_window_minutes == 60


def test_require_api_key_rejects_missing_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MAGIC_WALL_CONFIG_DIR", str(tmp_path / "config"))

    cfg = load_config()

    with pytest.raises(ConfigError):
        cfg.require_api_key()


def test_config_rejects_non_hour_news_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    path = tmp_path / "config.toml"
    path.write_text(
        """
        [refresh]
        minutes = 60
        news_window_minutes = 180
        """,
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="strict last-hour"):
        load_config(path)


def test_write_default_config_is_private(tmp_path: Path) -> None:
    path = write_default_config(tmp_path / "config.toml", api_key="sk-written")

    assert 'api_key = "sk-written"' in path.read_text(encoding="utf-8")
    assert "[xai]" not in path.read_text(encoding="utf-8")
    assert "[dashboard]" not in path.read_text(encoding="utf-8")
    if os.name == "posix":
        assert oct(path.stat().st_mode & 0o777) == "0o600"


def test_ignores_legacy_xai_and_dashboard_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    path = tmp_path / "config.toml"
    path.write_text(
        """
        [xai]
        api_key = "xai-file-key"
        model = "grok-4"

        [dashboard]
        refresh_minutes = 1
        categories = ["science"]
        """,
        encoding="utf-8",
    )

    cfg = load_config(path)

    assert cfg.refresh_minutes == 240
    assert not hasattr(cfg, "xai_api_key")
    assert not hasattr(cfg, "dashboard_refresh_minutes")
