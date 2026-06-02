from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Protocol

from .config import AppConfig
from .models import NewsStory, utc_now
from .prompts import build_image_prompt, choose_style, prompt_hash
from .story_discovery import SourceMeshStoryProvider
from .storage import WallStorage


class WallProvider(Protocol):
    def find_top_story(
        self,
        *,
        now: datetime,
        window_minutes: int,
        previous_stories: list[dict] | None = None,
    ) -> NewsStory:
        ...

    def generate_wallpaper(self, *, prompt: str) -> bytes:
        ...


class MagicWallGenerator:
    def __init__(
        self,
        config: AppConfig,
        *,
        provider: WallProvider | None = None,
        storage: WallStorage | None = None,
        clock=utc_now,
    ):
        self.config = config
        self.provider = provider or SourceMeshStoryProvider(config)
        self.storage = storage or WallStorage(config)
        self.clock = clock

    def generate_once(self) -> dict:
        now = self.clock().astimezone(timezone.utc)
        self.storage.mark_generating()
        generation_count = self.storage.generation_count()
        recent_stories = self.storage.recent_stories()
        briefing = self._find_briefing(
            now=now,
            window_minutes=self.config.news_window_minutes,
            previous_stories=recent_stories,
        )
        story = briefing[0] if briefing else NewsStory.quiet(now=now)
        if not _has_required_information(story):
            briefing = self._find_briefing(
                now=now,
                window_minutes=24 * 60,
                previous_stories=recent_stories,
            )
            story = briefing[0] if briefing else NewsStory.quiet(now=now)
        if not _has_required_information(story):
            story = NewsStory.daily_news_fallback(
                now=now,
                reason="OpenAI web search did not return a verified last-hour or daily news story.",
            )
            briefing = [story]

        briefing = [_compact_story(item) for item in briefing if _has_required_information(item)]
        if not briefing:
            briefing = [_compact_story(story)]
        story = briefing[0]
        if not story.is_within_window(now=now, minutes=self.config.news_window_minutes):
            story = replace(
                story,
                significance=_append_note(
                    story.significance,
                    "biggest-news-of-day fallback outside the preferred last-hour window",
                ),
            )
            briefing = [story, *briefing[1:]]

        style = choose_style(generation_count)
        prompt = build_image_prompt(
            story=story,
            briefing=briefing,
            style=style,
            size=self.config.image_size,
        )
        image_bytes = self.provider.generate_wallpaper(prompt=prompt)
        filename = self.storage.write_current_image(image_bytes)
        next_refresh = now + timedelta(minutes=self.config.refresh_minutes)

        state = {
            "status": "ready",
            "message": "Artwork ready.",
            "generated_at": now.isoformat(),
            "next_refresh_at": next_refresh.isoformat(),
            "story": story.to_dict(),
            "briefing": [item.to_dict() for item in briefing],
            "style": style,
            "image_file": filename,
            "image_model": self.config.image_model,
            "image_quality": self.config.image_quality,
            "image_size": self.config.image_size,
            "prompt_hash": prompt_hash(prompt),
            "generation_count": generation_count + 1,
            "recent_stories": self.storage.updated_recent_stories(story, extra_stories=briefing[1:]),
        }
        self.storage.write_state(state)
        return self.storage.state_for_api()

    def _find_briefing(
        self,
        *,
        now: datetime,
        window_minutes: int,
        previous_stories: list[dict] | None,
    ) -> list[NewsStory]:
        find_briefing = getattr(self.provider, "find_briefing", None)
        if callable(find_briefing):
            stories = find_briefing(
                now=now,
                window_minutes=window_minutes,
                previous_stories=previous_stories,
            )
            if isinstance(stories, list):
                return [story for story in stories if isinstance(story, NewsStory)]
        return [
            self.provider.find_top_story(
                now=now,
                window_minutes=window_minutes,
                previous_stories=previous_stories,
            )
        ]


def _has_required_information(story: NewsStory) -> bool:
    return story.found and bool(story.title.strip()) and bool(story.summary.strip())


def _compact_story(story: NewsStory) -> NewsStory:
    return story.with_compact_title(max_chars=46)


def _append_note(value: str | None, note: str) -> str:
    if not value:
        return note
    if note in value:
        return value
    return f"{value}; {note}"
