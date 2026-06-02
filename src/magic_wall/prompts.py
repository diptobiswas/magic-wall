from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any

from .models import NewsStory


WORLD_MACHINE_THEME = (
    "Create a wildly imaginative but decipherable World Machine Report: an exploded-view planet-machine "
    "floating in space, with each current news article turned into a labeled mechanical sector. The image "
    "should feel like a collectible premium infographic poster from the future, not a normal dashboard. "
    "Make the machine strange, dense, kinetic, and beautiful, while preserving a strict information "
    "hierarchy: one title, large article labels, obvious symbols, tiny chart-like signals, consequence "
    "tags, a legend, and a visible timeline orbit. The spectacle must serve the information."
)


STYLE_ROTATION = [
    "exploded-view planet machine with five readable article sectors",
    "retro-futurist control room fused into a world-machine cutaway",
    "glowing orbital timeline around a fractured mechanical earth",
    "sci-fi museum diagram with premium editorial data labels",
    "luminous reactor-core planet with article chambers and source chips",
    "cinematic technical poster with chart glyphs and consequence tags",
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


def build_news_briefing_search_prompt(
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
            f"verifiable briefing item in the window: {previous_json}. "
        )
    window_note = (
        "Prefer stories published or updated in the last one hour. "
        if window_minutes <= 60
        else "Prefer major stories published or updated today. "
    )
    return (
        "Find a compact briefing of 3 to 5 real, verifiable current news stories for Magic Wall, "
        "a Raspberry Pi screen that turns multiple articles into one World Machine infographic. "
        f"{window_note}"
        "Use live web search. Choose stories that are distinct from each other and visually legible "
        "as infographic sectors: markets/economy, weather/climate, science/space, technology, policy, "
        "culture, world events, or other major public signals. "
        "If the last-hour window is thin, include the biggest verifiable stories of today so the "
        "briefing still has multiple items. "
        "Never invent stories and never return a quiet-hour fallback if web search can verify current news. "
        f"{previous_note}"
        f"The current UTC time is {now_utc.isoformat()}. "
        f"The preferred publication or update time is after {since.isoformat()}. "
        "Return only compact JSON with key stories, where stories is an array of objects with keys: "
        "found, title, summary, source_name, source_url, published_at, significance, selection_reason. "
        "Each title must be a short infographic label: 2 to 7 words and at most 46 characters. "
        "Titles must be complete phrases with no ellipses or trailing prepositions. "
        "Each summary must be one sentence, faithful to the source, and not add unsupported facts."
    )


def build_story_selection_prompt(
    *,
    now: datetime,
    window_minutes: int,
    candidates: list[dict[str, Any]],
    previous_stories: list[dict[str, Any]] | None = None,
) -> str:
    now_utc = now.astimezone(timezone.utc)
    since = now_utc - timedelta(minutes=window_minutes)
    previous_note = ""
    if previous_stories:
        previous_json = json.dumps(previous_stories[:12], ensure_ascii=True)
        previous_note = (
            "Avoid repeating these recently used story titles or URLs unless the candidate is clearly "
            f"the strongest current update: {previous_json}. "
        )
    candidates_json = json.dumps(candidates[:12], ensure_ascii=True)
    return (
        "Choose the single best story candidate for Magic Wall, a Raspberry Pi screen that turns "
        "current news into an absurd, high-impact AI meme poster. "
        "Quality is more important than pure recency, but prefer candidates published or updated "
        f"after {since.isoformat()} when they are genuinely interesting. "
        "Use only the provided candidates. Do not use web search, do not invent facts, and do not "
        "combine different stories. Prefer stories with public significance, visual symbolism, "
        "multiple evidence signals, strong source quality, and an instantly readable image concept. "
        "Avoid routine commodity headlines, generic SEO posts, and stories that would make dull art. "
        f"The current UTC time is {now_utc.isoformat()}. {previous_note}"
        f"Candidates: {candidates_json}. "
        "Return only compact JSON with these keys: "
        "found, candidate_id, title, summary, source_name, source_url, published_at, significance, "
        "selection_reason. "
        "Set found=false only if every candidate is unusable. "
        "The title must be a short punchy meme label, 2 to 8 words and at most 56 characters. "
        "The summary must be faithful to the selected candidate and must not add unsupported facts."
    )


def build_briefing_selection_prompt(
    *,
    now: datetime,
    window_minutes: int,
    candidates: list[dict[str, Any]],
    previous_stories: list[dict[str, Any]] | None = None,
) -> str:
    now_utc = now.astimezone(timezone.utc)
    since = now_utc - timedelta(minutes=window_minutes)
    previous_note = ""
    if previous_stories:
        previous_json = json.dumps(previous_stories[:12], ensure_ascii=True)
        previous_note = f"Avoid repeating these recently used titles or URLs: {previous_json}. "
    candidates_json = json.dumps(candidates[:12], ensure_ascii=True)
    return (
        "Choose 3 to 5 distinct candidates for a Magic Wall World Machine infographic briefing. "
        "Use only the provided candidates. Do not use web search and do not invent unsupported facts. "
        "Prefer a mix of categories with public significance and clear visual symbols. "
        f"Prefer candidates published or updated after {since.isoformat()} when useful. "
        f"The current UTC time is {now_utc.isoformat()}. {previous_note}"
        "Rewrite each selected title into a complete 2 to 7 word infographic label. "
        "Every label must make sense by itself, must not end mid-phrase, must not end with a soft "
        "preposition such as on/of/for/to/with, and must not include ellipses. "
        "Keep each summary faithful to the selected candidate and one sentence long. "
        f"Candidates: {candidates_json}. "
        "Return only compact JSON with key stories, where stories is an array of objects with keys: "
        "found, candidate_id, title, summary, significance, selection_reason. "
        "Set found=false only for an unusable item; omit unusable items when possible."
    )


def build_image_prompt(*, story: NewsStory, style: str, size: str, briefing: list[NewsStory] | None = None) -> str:
    stories = [item for item in (briefing or [story]) if item.found] or [story]
    briefing_lines = "\n".join(
        (
            f"{index}. Label: {item.title}; Summary: {item.summary}; "
            f"Source: {item.source_name or 'verified source'}; "
            f"Published: {item.published_at or 'unknown'}; "
            f"Why it matters: {item.significance or item.selection_reason or 'current public signal'}."
        )
        for index, item in enumerate(stories[:5], start=1)
    )
    return (
        f"Create a landscape infographic wallpaper for a small 7-inch Raspberry Pi touchscreen at {size}. "
        f"{WORLD_MACHINE_THEME} "
        f"Style variation: {style}. "
        "Use the exact readable main title: WORLD MACHINE REPORT. "
        "Combine all provided stories into one coherent visual artifact; do not focus on only one story. "
        "Give each story a distinct large sector with a short label, one visual symbol, one chart-like signal, "
        "and one short consequence tag. Include a clean bottom legend and an orbital timeline labeled "
        "PAST, NOW, FUTURE. "
        "Keep text sparse, large, and safely inside its containers. No tiny paragraphs, no cropped labels, "
        "no ellipses, no labels that end mid-phrase, "
        "no real outlet logos, no newspaper mastheads, no UI chrome, and no watermark. "
        "Do not invent unsupported facts; use visual symbolism for uncertain details. "
        "Avoid sensational gore and avoid unrelated celebrities or private people. "
        "News briefing to encode:\n"
        f"{briefing_lines}"
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
