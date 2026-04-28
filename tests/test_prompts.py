from __future__ import annotations

from datetime import datetime, timezone

from magic_wall.models import NewsStory
from magic_wall.prompts import (
    build_dashboard_signal_prompt,
    build_image_prompt,
    build_news_search_prompt,
    build_story_selection_prompt,
    extract_json_object,
)


def test_news_prompt_prefers_last_hour() -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    prompt = build_news_search_prompt(now=now, window_minutes=60)

    assert "last one hour" in prompt
    assert "2026-04-24T11:00:00+00:00" in prompt
    assert "lower-stakes story" in prompt
    assert "biggest verifiable news story of today" in prompt
    assert "Never make a quiet-hour" in prompt
    assert "short punchy one-line meme label" in prompt


def test_news_prompt_can_search_biggest_story_of_day() -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    prompt = build_news_search_prompt(now=now, window_minutes=1440)

    assert "biggest verifiable news story of today" in prompt
    assert "largest public significance" in prompt


def test_news_prompt_avoids_recent_used_stories() -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    prompt = build_news_search_prompt(
        now=now,
        window_minutes=60,
        previous_stories=[{"title": "Already used", "source_url": "https://example.com/used"}],
    )

    assert "Avoid reusing" in prompt
    assert "Already used" in prompt


def test_story_selection_prompt_uses_source_candidates_without_web_search() -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)

    prompt = build_story_selection_prompt(
        now=now,
        window_minutes=60,
        candidates=[
            {
                "id": "abc123",
                "title": "NASA announces AI space discovery",
                "summary": "A candidate summary.",
                "source_name": "AP News",
                "source_url": "https://example.com/space",
                "published_at": "2026-04-28T11:42:00+00:00",
                "score": 90,
            }
        ],
        previous_stories=[{"title": "Already used"}],
    )

    assert "Use only the provided candidates" in prompt
    assert "Do not use web search" in prompt
    assert "NASA announces AI space discovery" in prompt
    assert "Already used" in prompt
    assert "candidate_id" in prompt


def test_dashboard_signal_prompt_requests_x_pulse_only() -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)

    prompt = build_dashboard_signal_prompt(
        now=now,
        categories=("science", "technology", "pop culture"),
        previous_items=[{"title": "Already surfaced"}],
    )

    assert "X Search" in prompt
    assert "Do not use or summarize general web/news feeds" in prompt
    assert "Web Search" not in prompt
    assert "science, technology, pop culture" in prompt
    assert "2026-04-28T11:00:00+00:00" in prompt
    assert "Already surfaced" in prompt
    assert '"x_topics"' in prompt


def test_extract_json_object_handles_markdown_fence() -> None:
    data = extract_json_object('```json\n{"found": false, "title": "Quiet hour"}\n```')

    assert data == {"found": False, "title": "Quiet hour"}


def test_image_prompt_uses_ai_slop_masterpiece_theme() -> None:
    story = NewsStory(
        found=True,
        title="A market shock moves through global energy prices",
        summary="A sudden policy announcement shifted energy markets.",
        published_at="2026-04-24T11:31:00+00:00",
        significance="global markets",
    )

    prompt = build_image_prompt(story=story, style="hyperreal viral-thumbnail collage", size="1344x800")

    assert "absolute pinnacle of 'AI slop'" in prompt
    assert "chrome astronaut riding a tiger through space" in prompt
    assert "baby wearing a gold crown" in prompt
    assert "A market shock moves through global energy prices" in prompt
    assert "deranged premium internet meme poster" in prompt
    assert "exactly one short readable text element" in prompt
    assert "famous public figure is central" in prompt


def test_quiet_hour_prompt_keeps_ai_slop_theme() -> None:
    now = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    prompt = build_image_prompt(
        story=NewsStory.quiet(now=now),
        style="overcrowded inspirational desktop wallpaper",
        size="1344x800",
    )

    assert "absolute pinnacle of 'AI slop'" in prompt
    assert "Story title: Quiet hour" in prompt
    assert "instantly identifiable as a meme" in prompt
