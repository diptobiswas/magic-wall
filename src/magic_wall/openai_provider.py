from __future__ import annotations

import base64
from typing import Any

from .config import AppConfig
from .models import NewsStory
from .prompts import (
    build_briefing_selection_prompt,
    build_news_briefing_search_prompt,
    build_news_search_prompt,
    build_story_selection_prompt,
    extract_json_object,
)


class OpenAIProvider:
    def __init__(self, config: AppConfig, *, client: Any | None = None):
        self.config = config
        self.client = client or self._build_client(config)

    def find_top_story(
        self,
        *,
        now,
        window_minutes: int,
        previous_stories: list[dict] | None = None,
    ) -> NewsStory:
        prompt = build_news_search_prompt(
            now=now,
            window_minutes=window_minutes,
            previous_stories=previous_stories,
        )
        response = self.client.responses.create(
            model=self.config.text_model,
            tools=[{"type": "web_search"}],
            input=prompt,
        )
        text = _response_text(response)
        data = extract_json_object(text)
        return NewsStory.from_dict(data)

    def find_briefing(
        self,
        *,
        now,
        window_minutes: int,
        previous_stories: list[dict] | None = None,
    ) -> list[NewsStory]:
        prompt = build_news_briefing_search_prompt(
            now=now,
            window_minutes=window_minutes,
            previous_stories=previous_stories,
        )
        response = self.client.responses.create(
            model=self.config.text_model,
            tools=[{"type": "web_search"}],
            input=prompt,
            max_output_tokens=1600,
        )
        data = extract_json_object(_response_text(response))
        raw_stories = data.get("stories")
        if not isinstance(raw_stories, list):
            return []
        stories = [
            NewsStory.from_dict(item)
            for item in raw_stories
            if isinstance(item, dict)
        ]
        return [story for story in stories if story.found and story.title.strip() and story.summary.strip()]

    def select_story_from_candidates(
        self,
        *,
        now,
        window_minutes: int,
        candidates: list[dict[str, Any]],
        previous_stories: list[dict] | None = None,
    ) -> NewsStory:
        prompt = build_story_selection_prompt(
            now=now,
            window_minutes=window_minutes,
            candidates=candidates,
            previous_stories=previous_stories,
        )
        response = self.client.responses.create(
            model=self.config.text_model,
            input=prompt,
            max_output_tokens=700,
        )
        data = extract_json_object(_response_text(response))
        data = _fill_candidate_source_fields(data, candidates)
        return NewsStory.from_dict(data)

    def select_briefing_from_candidates(
        self,
        *,
        now,
        window_minutes: int,
        candidates: list[dict[str, Any]],
        previous_stories: list[dict] | None = None,
    ) -> list[NewsStory]:
        prompt = build_briefing_selection_prompt(
            now=now,
            window_minutes=window_minutes,
            candidates=candidates,
            previous_stories=previous_stories,
        )
        response = self.client.responses.create(
            model=self.config.text_model,
            input=prompt,
            max_output_tokens=1600,
        )
        data = extract_json_object(_response_text(response))
        raw_stories = data.get("stories")
        if not isinstance(raw_stories, list):
            return []
        stories: list[NewsStory] = []
        for item in raw_stories:
            if not isinstance(item, dict):
                continue
            merged = _fill_candidate_source_fields(item, candidates)
            story = NewsStory.from_dict(merged)
            if story.found and story.title.strip() and story.summary.strip():
                stories.append(story)
        return stories

    def generate_wallpaper(self, *, prompt: str) -> bytes:
        result = self.client.images.generate(
            model=self.config.image_model,
            prompt=prompt,
            size=self.config.image_size,
            quality=self.config.image_quality,
            output_format=self.config.output_format,
        )
        image_base64 = result.data[0].b64_json
        return base64.b64decode(image_base64)

    @staticmethod
    def _build_client(config: AppConfig):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is not installed.") from exc
        return OpenAI(api_key=config.require_api_key())


def _fill_candidate_source_fields(data: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_id = str(data.get("candidate_id") or "")
    candidate = next((item for item in candidates if str(item.get("id") or "") == candidate_id), None)
    if not candidate:
        return data
    merged = dict(data)
    for key in ("source_name", "source_url", "published_at"):
        if not merged.get(key) and candidate.get(key):
            merged[key] = candidate.get(key)
    if not merged.get("summary") and candidate.get("summary"):
        merged["summary"] = candidate.get("summary")
    return merged


def _response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(text)
    if parts:
        return "\n".join(parts)
    raise ValueError("OpenAI response did not include text output.")
