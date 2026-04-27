from __future__ import annotations

from datetime import datetime, timezone

from magic_wall.models import NewsStory
from magic_wall.prompts import build_image_prompt, build_news_search_prompt, extract_json_object


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
