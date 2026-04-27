from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from magic_wall.config import AppConfig
from magic_wall.generator import MagicWallGenerator
from magic_wall.models import NewsStory
from magic_wall.storage import WallStorage


class FakeProvider:
    def __init__(self, story: NewsStory | list[NewsStory]):
        self.stories = story if isinstance(story, list) else [story]
        self.prompts: list[str] = []
        self.previous_stories: list[dict] | None = None
        self.search_windows: list[int] = []

    def find_top_story(
        self,
        *,
        now: datetime,
        window_minutes: int,
        previous_stories: list[dict] | None = None,
    ) -> NewsStory:
        self.previous_stories = previous_stories
        self.search_windows.append(window_minutes)
        if len(self.search_windows) <= len(self.stories):
            return self.stories[len(self.search_windows) - 1]
        return self.stories[-1]

    def generate_wallpaper(self, *, prompt: str) -> bytes:
        self.prompts.append(prompt)
        return b"fake-image"


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        config_path=tmp_path / "config.toml",
        data_dir=tmp_path / "data",
        openai_api_key="sk-test",
    )


def test_generation_uses_recent_story_and_writes_state(tmp_path: Path) -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    story = NewsStory(
        found=True,
        title="Court blocks emergency order",
        summary="A major court ruling changed a national policy.",
        source_name="Example Wire",
        source_url="https://example.com/story",
        published_at="2026-04-24T11:31:00+00:00",
        significance="national policy",
    )
    provider = FakeProvider(story)
    cfg = make_config(tmp_path)
    storage = WallStorage(cfg)

    state = MagicWallGenerator(cfg, provider=provider, storage=storage, clock=lambda: now).generate_once()

    assert state["status"] == "ready"
    assert state["story"]["found"] is True
    assert state["story"]["title"] == story.title
    assert storage.current_image_path.read_bytes() == b"fake-image"
    assert "Court blocks emergency order" in provider.prompts[0]


def test_generation_compacts_long_news_title_for_display_and_image_text(tmp_path: Path) -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    story = NewsStory(
        found=True,
        title=(
            "Officials say a complicated market and diplomatic crisis is spreading across "
            "multiple countries after a dramatic overnight announcement"
        ),
        summary="A major announcement created market and diplomatic pressure.",
        source_name="Example Wire",
        source_url="https://example.com/long",
        published_at="2026-04-24T11:31:00+00:00",
        significance="global markets",
    )
    provider = FakeProvider(story)
    cfg = make_config(tmp_path)

    state = MagicWallGenerator(cfg, provider=provider, clock=lambda: now).generate_once()

    assert len(state["story"]["title"]) <= 64
    assert "\n" not in state["story"]["title"]
    assert state["story"]["title"].endswith("...")
    assert state["story"]["title"] in provider.prompts[0]


def test_generation_uses_current_information_even_outside_last_hour(tmp_path: Path) -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    old_story = NewsStory(
        found=True,
        title="Agency reports new public health totals",
        summary="A public agency updated a daily information page this morning.",
        source_name="Example Agency",
        source_url="https://example.com/update",
        published_at="2026-04-24T09:30:00+00:00",
        significance="public information",
    )
    provider = FakeProvider(old_story)
    cfg = make_config(tmp_path)

    state = MagicWallGenerator(cfg, provider=provider, clock=lambda: now).generate_once()

    assert state["story"]["found"] is True
    assert state["story"]["title"] == "Agency reports new public health totals"
    assert "biggest-news-of-day fallback outside the preferred last-hour window" in state["story"]["significance"]
    assert "Agency reports new public health totals" in provider.prompts[0]
    assert "instantly identifiable as a meme" in provider.prompts[0]


def test_generation_retries_with_biggest_news_of_day_when_last_hour_has_no_story(tmp_path: Path) -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    daily_story = NewsStory(
        found=True,
        title="Global leaders announce climate finance deal",
        summary="Leaders announced a major climate finance agreement earlier today.",
        source_name="Example Wire",
        source_url="https://example.com/climate",
        published_at="2026-04-24T07:15:00+00:00",
        significance="global policy",
    )
    provider = FakeProvider([NewsStory.quiet(now=now), daily_story])
    cfg = make_config(tmp_path)
    storage = WallStorage(cfg)

    state = MagicWallGenerator(cfg, provider=provider, storage=storage, clock=lambda: now).generate_once()

    assert provider.search_windows == [60, 1440]
    assert state["story"]["found"] is True
    assert state["story"]["title"] == "Global leaders announce climate finance deal"
    assert "Global leaders announce climate finance deal" in provider.prompts[0]


def test_generation_never_errors_when_search_returns_no_story(tmp_path: Path) -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    provider = FakeProvider([NewsStory.quiet(now=now), NewsStory.quiet(now=now)])
    cfg = make_config(tmp_path)
    storage = WallStorage(cfg)

    state = MagicWallGenerator(cfg, provider=provider, storage=storage, clock=lambda: now).generate_once()

    assert provider.search_windows == [60, 1440]
    assert state["story"]["found"] is True
    assert state["story"]["title"].startswith("Biggest news of the day fallback")
    assert "biggest-news-of-day fallback" in provider.prompts[0]
    assert storage.current_image_path.exists()


def test_style_rotation_advances_with_generation_count(tmp_path: Path) -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    story = NewsStory(
        found=True,
        title="Local transit opens new station",
        summary="A city transit agency opened a station today.",
        source_url="https://example.com/transit",
        published_at="2026-04-24T11:20:00+00:00",
    )
    cfg = make_config(tmp_path)
    storage = WallStorage(cfg)

    first = MagicWallGenerator(cfg, provider=FakeProvider(story), storage=storage, clock=lambda: now).generate_once()
    second = MagicWallGenerator(cfg, provider=FakeProvider(story), storage=storage, clock=lambda: now).generate_once()

    assert first["style"] != second["style"]
    assert second["generation_count"] == 2


def test_default_next_refresh_is_four_hours_later(tmp_path: Path) -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    story = NewsStory(
        found=True,
        title="Weather office posts updated forecast",
        summary="The forecast office updated the current regional forecast.",
        source_url="https://example.com/weather",
        published_at="2026-04-24T11:45:00+00:00",
    )
    cfg = make_config(tmp_path)

    state = MagicWallGenerator(cfg, provider=FakeProvider(story), clock=lambda: now).generate_once()

    assert state["next_refresh_at"] == "2026-04-24T16:00:00+00:00"
    assert state["config"]["refresh_minutes"] == 240


def test_generation_passes_recent_stories_to_provider(tmp_path: Path) -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    first_story = NewsStory(
        found=True,
        title="First story",
        summary="Already used.",
        source_url="https://example.com/first",
        published_at="2026-04-24T11:10:00+00:00",
    )
    second_story = NewsStory(
        found=True,
        title="Second story",
        summary="Fresh story.",
        source_url="https://example.com/second",
        published_at="2026-04-24T11:20:00+00:00",
    )
    cfg = make_config(tmp_path)
    storage = WallStorage(cfg)
    MagicWallGenerator(cfg, provider=FakeProvider(first_story), storage=storage, clock=lambda: now).generate_once()
    provider = FakeProvider(second_story)

    MagicWallGenerator(cfg, provider=provider, storage=storage, clock=lambda: now).generate_once()

    assert provider.previous_stories == [
        {
            "title": "First story",
            "source_url": "https://example.com/first",
            "published_at": "2026-04-24T11:10:00+00:00",
        }
    ]
