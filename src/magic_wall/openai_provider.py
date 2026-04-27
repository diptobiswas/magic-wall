from __future__ import annotations

import base64
from typing import Any

from .config import AppConfig
from .models import NewsStory
from .prompts import build_news_search_prompt, extract_json_object


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
