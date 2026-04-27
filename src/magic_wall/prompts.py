from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any

from .models import NewsStory


AI_SLOP_MASTERPIECE_THEME = (
    "Create an intentionally outrageous, maximalist image that feels like the absolute pinnacle of "
    "'AI slop': a hyper-detailed, glossy, oversaturated digital collage with way too many unrelated "
    "subjects crammed together. Make it look absurdly polished yet nonsensical. Include a majestic "
    "wolf with glowing blue eyes, a lion made of lightning, a chrome astronaut riding a tiger through "
    "space, a cute anime-style girl with giant reflective eyes, a baby wearing a gold crown, a "
    "futuristic city skyline, floating castles, waterfalls pouring into the clouds, a phoenix, a sports "
    "car with impossible reflections, giant mushrooms, neon butterflies, a galaxy sky, rainbow energy "
    "beams, dramatic lens flares, sparkles everywhere, and overly cinematic volumetric lighting. Add too "
    "many visual effects: rim light, bokeh, mist, fire, lightning, glossy surfaces, glitter, smoke, and "
    "a fake-deep inspirational vibe. Composition should be overcrowded, chaotic, visually loud, and "
    "hilariously over-rendered, with every area packed with detail. The image should look like a seminal "
    "masterpiece of AI slop: beautiful at first glance, ridiculous upon inspection."
)


STYLE_ROTATION = [
    "premium fantasy poster chaos, all subjects rendered with impossible glossy detail",
    "overproduced cinematic concept art with rainbow lighting and fake profundity",
    "hyperreal viral-thumbnail collage where every object is the main character",
    "ultra-polished cosmic dreamboard with absurd luxury surfaces and mythic animals",
    "maximalist AI-art showcase with too much rim light, sparkle, and drama",
    "overcrowded inspirational desktop wallpaper, beautiful and nonsensical",
    "shiny sci-fi fantasy mashup with every trendy visual trope turned up",
    "hilariously dense prompt-engineered masterpiece with no quiet corners",
]


def choose_style(generation_count: int) -> str:
    return STYLE_ROTATION[generation_count % len(STYLE_ROTATION)]


def build_news_search_prompt(
    *,
    now: datetime,
    window_minutes: int,
    previous_stories: list[dict[str, Any]] | None = None,
) -> str:
    now_utc = now.astimezone(timezone.utc)
    since = now_utc - timedelta(minutes=window_minutes)
    previous_note = ""
    if previous_stories:
        previous_json = json.dumps(previous_stories[:12], ensure_ascii=True)
        previous_note = (
            "Avoid reusing these recently used story titles or URLs unless there is no other "
            f"verifiable story in the window: {previous_json}. "
        )
    if window_minutes > 60:
        search_instruction = (
            "Find the biggest verifiable news story of today and return found=true. "
            "Use live web search. Prefer a major story published or updated in the provided window. "
            "If there are several candidates, choose the one with the largest public significance. "
        )
    else:
        search_instruction = (
            "Find one real news story or current information item and return found=true. "
            "Use live web search. First search for a story published in the last one hour. "
            "Prefer the most significant story, but if there is no major story, choose a real existing "
            "lower-stakes story from the same one-hour window instead. "
            "If the last-hour window is genuinely thin, choose the biggest verifiable news story of "
            "today instead. "
        )
    return (
        f"{search_instruction}"
        "Never make a quiet-hour, no-news, or invented fallback. "
        "Only set found=false if live web search is unavailable or you cannot verify any real "
        "news story from today at all. "
        f"{previous_note}"
        f"The current UTC time is {now_utc.isoformat()}. "
        f"The preferred publication or update time is after {since.isoformat()}. "
        "Return only compact JSON with these keys: "
        "found, title, summary, source_name, source_url, published_at, significance, selection_reason. "
        "The title must be a short punchy one-line meme label, not a full article headline: "
        "2 to 8 words and at most 56 characters. "
        "Do not include markdown, citations outside the JSON, or extra commentary."
    )


def build_image_prompt(*, story: NewsStory, style: str, size: str) -> str:
    common = (
        f"Create a landscape artwork for a small 7-inch Raspberry Pi touchscreen at {size}. "
        "Make it feel like a deranged premium internet meme poster about the news, not a sober editorial illustration. "
        "Include exactly one short readable text element using the story title, styled like a bold meme caption or poster headline. "
        "No logos, no interface, no newspaper mastheads, and no extra words beyond that one short text element. "
        "Keep it legible as a wallpaper from across the room, but do not simplify the image. "
        "The image must encode the provided real-world information as visual symbolism; do not make "
        "generic wallpaper art. "
        f"{AI_SLOP_MASTERPIECE_THEME} "
        f"Hourly variation style note: {style}."
    )
    return (
        f"{common} Interpret this news story as symbolic art, not literal reportage. "
        "Make the information payload visibly drive the scene through repeated symbolic anchors, "
        "object choices, setting, color logic, and foreground action. "
        "If a famous public figure is central to the story, include a clearly recognizable stylized "
        "caricature or meme-poster version of that public figure to improve comprehension. "
        "Do not include private people or unrelated celebrities. "
        f"Story title: {story.title}. "
        f"Story summary: {story.summary}. "
        f"Source: {story.source_name or 'verified web source'} {story.source_url or ''}. "
        f"Published or updated at: {story.published_at or 'unknown current time'}. "
        f"Significance: {story.significance or 'major current event'}. "
        "Avoid sensational gore. Preserve the intentionally overcrowded AI-slop look while making "
        "the story instantly identifiable as a meme."
    )


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        loaded = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise
        loaded = json.loads(match.group(0))
    if not isinstance(loaded, dict):
        raise ValueError("Expected a JSON object.")
    return loaded


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
