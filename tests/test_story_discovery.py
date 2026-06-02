from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from magic_wall.config import AppConfig
from magic_wall.models import NewsStory
from magic_wall.story_discovery import (
    SourceMeshStoryProvider,
    StoryCandidate,
    StoryCollector,
    rank_story_candidates,
)


class FakeCollector:
    def __init__(self, candidates: list[StoryCandidate]):
        self.candidates = candidates
        self.calls: list[int] = []

    def collect(self, *, now: datetime, window_minutes: int) -> list[StoryCandidate]:
        del now
        self.calls.append(window_minutes)
        return self.candidates


class FakeOpenAIProvider:
    def __init__(self, selected: NewsStory | None = None, *, fail_selection: bool = False):
        self.selected = selected
        self.fail_selection = fail_selection
        self.candidate_batches: list[list[dict]] = []
        self.web_search_windows: list[int] = []

    def select_story_from_candidates(
        self,
        *,
        now: datetime,
        window_minutes: int,
        candidates: list[dict],
        previous_stories: list[dict] | None = None,
    ) -> NewsStory:
        del previous_stories, window_minutes
        self.candidate_batches.append(candidates)
        if self.fail_selection:
            raise RuntimeError("selection failed")
        return self.selected or NewsStory(
            found=True,
            title=str(candidates[0]["title"]),
            summary=str(candidates[0]["summary"]),
            source_name=str(candidates[0]["source_name"]),
            source_url=str(candidates[0]["source_url"]),
            published_at=str(candidates[0]["published_at"]),
            significance="selected from source mesh",
            selection_reason="best candidate",
        )

    def select_briefing_from_candidates(
        self,
        *,
        now: datetime,
        window_minutes: int,
        candidates: list[dict],
        previous_stories: list[dict] | None = None,
    ) -> list[NewsStory]:
        del now, previous_stories, window_minutes
        self.candidate_batches.append(candidates)
        if self.fail_selection:
            raise RuntimeError("selection failed")
        return [
            NewsStory(
                found=True,
                title=f"Sector {index + 1} Ready",
                summary=str(candidate["summary"]),
                source_name=str(candidate["source_name"]),
                source_url=str(candidate["source_url"]),
                published_at=str(candidate["published_at"]),
                significance="model briefing rewrite",
                selection_reason="briefing candidate",
            )
            for index, candidate in enumerate(candidates)
        ]

    def find_top_story(
        self,
        *,
        now: datetime,
        window_minutes: int,
        previous_stories: list[dict] | None = None,
    ) -> NewsStory:
        del previous_stories
        self.web_search_windows.append(window_minutes)
        return NewsStory(
            found=True,
            title="Paid search fallback story",
            summary="Fallback web search returned a story.",
            source_name="OpenAI web search",
            source_url="https://example.com/fallback",
            published_at=now.isoformat(),
        )

    def generate_wallpaper(self, *, prompt: str) -> bytes:
        del prompt
        return b"image"


class StaticSource:
    name = "static"

    def __init__(self, candidates: list[StoryCandidate]):
        self.candidates = candidates

    def collect(self, *, now: datetime, window_minutes: int) -> list[StoryCandidate]:
        del now, window_minutes
        return self.candidates


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        config_path=tmp_path / "config.toml",
        data_dir=tmp_path / "data",
        openai_api_key="sk-test",
    )


def make_candidate(
    title: str,
    *,
    source_name: str = "AP News",
    source_url: str = "https://example.com/story",
    published_at: str = "2026-04-28T11:40:00+00:00",
    metric: str | None = None,
    category: str = "world",
) -> StoryCandidate:
    return StoryCandidate.create(
        title=title,
        summary=f"{title} is unfolding now.",
        source_name=source_name,
        source_url=source_url,
        published_at=published_at,
        source_type="test",
        category=category,
        metric=metric,
    )


def test_source_mesh_selects_from_candidates_without_paid_web_search(tmp_path: Path) -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    candidate = make_candidate("Court launches energy market crisis")
    openai = FakeOpenAIProvider()

    story = SourceMeshStoryProvider(
        make_config(tmp_path),
        openai_provider=openai,
        collector=FakeCollector([candidate]),
    ).find_top_story(now=now, window_minutes=60)

    assert story.title == "Court launches energy market crisis"
    assert openai.candidate_batches
    assert openai.web_search_windows == []


def test_source_mesh_falls_back_to_paid_search_when_mesh_is_empty(tmp_path: Path) -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    openai = FakeOpenAIProvider()

    story = SourceMeshStoryProvider(
        make_config(tmp_path),
        openai_provider=openai,
        collector=FakeCollector([]),
    ).find_top_story(now=now, window_minutes=60)

    assert story.title == "Paid search fallback story"
    assert openai.candidate_batches == []
    assert openai.web_search_windows == [60]


def test_source_mesh_uses_local_top_candidate_when_model_selection_fails(tmp_path: Path) -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    top = make_candidate("NASA announces AI space discovery", source_url="https://example.com/top")
    weak = make_candidate(
        "Tiny lifestyle post gets syndicated",
        source_name="Unknown Blog",
        source_url="https://example.com/weak",
        published_at="2026-04-28T05:00:00+00:00",
    )
    openai = FakeOpenAIProvider(fail_selection=True)

    story = SourceMeshStoryProvider(
        make_config(tmp_path),
        openai_provider=openai,
        collector=FakeCollector([weak, top]),
    ).find_top_story(now=now, window_minutes=60)

    assert story.title == "NASA announces AI space discovery"
    assert story.selection_reason == "source-mesh local ranking fallback"
    assert openai.web_search_windows == []


def test_source_mesh_briefing_uses_model_rewritten_labels(tmp_path: Path) -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    candidates = [
        make_candidate("Sandy Fire burning in Simi Valley prompts evacuation warnings", category="weather"),
        make_candidate("Bond jitters test finance chiefs at summit", source_url="https://example.com/bonds"),
        make_candidate("AI chip deal expands cloud capacity", source_url="https://example.com/ai"),
    ]
    openai = FakeOpenAIProvider()

    stories = SourceMeshStoryProvider(
        make_config(tmp_path),
        openai_provider=openai,
        collector=FakeCollector(candidates),
    ).find_briefing(now=now, window_minutes=60)

    assert [story.title for story in stories] == ["Sector 1 Ready", "Sector 2 Ready", "Sector 3 Ready"]
    assert openai.candidate_batches


def test_rank_story_candidates_penalizes_recent_repeats() -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    repeated = make_candidate("Court launches energy market crisis", source_url="https://example.com/repeated")
    fresh = make_candidate("NASA announces AI space discovery", source_url="https://example.com/fresh")

    ranked = rank_story_candidates(
        [repeated, fresh],
        now=now,
        window_minutes=60,
        previous_stories=[{"title": repeated.title, "source_url": repeated.source_url}],
    )

    assert ranked[0].title == fresh.title


def test_rank_story_candidates_penalizes_photo_wire_noise() -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    photo_item = make_candidate(
        "Licensable picture: The 79th Cannes Film Festival",
        source_name="Reuters Connect",
        source_url="https://example.com/photo",
    )
    hard_news = make_candidate(
        "Court launches energy market crisis",
        source_name="AP News",
        source_url="https://example.com/court",
    )

    ranked = rank_story_candidates(
        [photo_item, hard_news],
        now=now,
        window_minutes=60,
    )

    assert ranked[0].title == hard_news.title


def test_story_collector_combines_sources_without_failing_all_sources() -> None:
    candidate = make_candidate("Microsoft and OpenAI redraw their deal")

    class BrokenSource:
        name = "broken"

        def collect(self, *, now: datetime, window_minutes: int) -> list[StoryCandidate]:
            del now, window_minutes
            raise RuntimeError("source down")

    collector = StoryCollector(sources=(BrokenSource(), StaticSource([candidate])))

    assert collector.collect(now=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc), window_minutes=60) == [candidate]
