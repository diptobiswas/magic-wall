from __future__ import annotations

from pathlib import Path

from magic_wall.config import AppConfig
from magic_wall.models import DashboardSignal, NewsStory, TrendItem
from magic_wall.storage import WallStorage


def test_current_image_replacement_is_atomic_and_updates_api_url(tmp_path: Path) -> None:
    cfg = AppConfig(config_path=tmp_path / "config.toml", data_dir=tmp_path / "data")
    storage = WallStorage(cfg)

    first = storage.write_current_image(b"one")
    second = storage.write_current_image(b"two")
    api_state = storage.state_for_api()

    assert first == "current.jpg"
    assert second == "current.jpg"
    assert storage.current_image_path.read_bytes() == b"two"
    assert api_state["image_url"].startswith("/media/current.jpg")


def test_state_api_recalculates_next_refresh_from_current_config(tmp_path: Path) -> None:
    cfg = AppConfig(config_path=tmp_path / "config.toml", data_dir=tmp_path / "data")
    storage = WallStorage(cfg)
    storage.write_state(
        {
            "status": "ready",
            "generated_at": "2026-04-24T12:00:00+00:00",
            "next_refresh_at": "2026-04-24T13:00:00+00:00",
        }
    )

    api_state = storage.state_for_api()

    assert api_state["next_refresh_at"] == "2026-04-24T16:00:00+00:00"


def test_recent_stories_keeps_real_story_memory(tmp_path: Path) -> None:
    cfg = AppConfig(config_path=tmp_path / "config.toml", data_dir=tmp_path / "data")
    storage = WallStorage(cfg)
    story = NewsStory(
        found=True,
        title="Used story",
        summary="Summary",
        source_url="https://example.com/used",
        published_at="2026-04-24T12:00:00+00:00",
    )

    recent = storage.updated_recent_stories(story)

    assert recent == [
        {
            "title": "Used story",
            "source_url": "https://example.com/used",
            "published_at": "2026-04-24T12:00:00+00:00",
        }
    ]


def test_dashboard_signal_round_trips_through_state_api(tmp_path: Path) -> None:
    cfg = AppConfig(config_path=tmp_path / "config.toml", data_dir=tmp_path / "data")
    storage = WallStorage(cfg)
    signal = DashboardSignal(
        status="ready",
        message="Fresh signals ready.",
        checked_at="2026-04-28T12:00:00+00:00",
        next_check_at="2026-04-28T13:00:00+00:00",
        provider="test",
        categories=("science", "technology"),
        items=(
            TrendItem.from_dict(
                {
                    "category": "science",
                    "title": "A new telescope result is everywhere",
                    "summary": "A fresh result is picking up attention.",
                    "source_url": "https://example.com/telescope",
                }
            ),
        ),
        x_topics=({"name": "space telescope", "url": "https://x.com/search?q=space"},),
    )

    storage.write_dashboard_signal(signal)
    api_state = storage.state_for_api()

    assert api_state["dashboard"]["status"] == "ready"
    assert api_state["dashboard"]["items"][0]["category"] == "science"
    assert api_state["dashboard"]["x_topics"][0]["name"] == "space telescope"
    assert api_state["config"]["dashboard_refresh_minutes"] == 60
