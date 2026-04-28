from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import ssl
from typing import Any, Protocol
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .config import AppConfig
from .models import DashboardSignal, TrendItem, utc_now, x_search_url
from .prompts import build_dashboard_signal_prompt, extract_json_object
from .storage import WallStorage


class SignalProvider(Protocol):
    name: str

    def collect_dashboard_signal(
        self,
        *,
        now: datetime,
        categories: tuple[str, ...],
        previous_items: list[dict[str, Any]] | None = None,
    ) -> DashboardSignal:
        ...


class DashboardUpdater:
    def __init__(
        self,
        config: AppConfig,
        *,
        provider: SignalProvider | None = None,
        storage: WallStorage | None = None,
        clock=utc_now,
    ):
        self.config = config
        self.provider = provider or build_signal_provider(config)
        self.storage = storage or WallStorage(config)
        self.clock = clock

    def refresh_once(self) -> dict[str, Any]:
        now = self.clock().astimezone(timezone.utc)
        self.storage.mark_dashboard_checking()
        next_check = now + timedelta(minutes=self.config.dashboard_refresh_minutes)
        signal = self.provider.collect_dashboard_signal(
            now=now,
            categories=self.config.dashboard_categories,
            previous_items=self.storage.recent_dashboard_items(),
        )
        signal = replace(
            signal,
            checked_at=now.isoformat(),
            next_check_at=next_check.isoformat(),
            categories=self.config.dashboard_categories,
        )
        self.storage.write_dashboard_signal(signal)
        return self.storage.state_for_api().get("dashboard", {})


def build_signal_provider(config: AppConfig) -> SignalProvider:
    if config.xai_api_key:
        return XaiSignalProvider(config)
    return FreeFeedSignalProvider()


class XaiSignalProvider:
    name = "xai"

    def __init__(self, config: AppConfig, *, client: Any | None = None):
        self.config = config
        self.client = client or self._build_client(config)

    def collect_dashboard_signal(
        self,
        *,
        now: datetime,
        categories: tuple[str, ...],
        previous_items: list[dict[str, Any]] | None = None,
    ) -> DashboardSignal:
        now_utc = now.astimezone(timezone.utc)
        since = now_utc - timedelta(minutes=self.config.dashboard_refresh_minutes)
        prompt = build_dashboard_signal_prompt(
            now=now,
            categories=categories,
            previous_items=previous_items,
        )
        response = self.client.responses.create(
            model=self.config.xai_model,
            input=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "type": "x_search",
                    "from_date": since.date().isoformat(),
                    "to_date": now_utc.date().isoformat(),
                }
            ],
            max_output_tokens=1400,
        )
        data = extract_json_object(_response_text(response))
        data["provider"] = self.name
        return DashboardSignal.from_dict(data, categories=categories)

    @staticmethod
    def _build_client(config: AppConfig):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is not installed.") from exc
        return OpenAI(
            api_key=config.require_xai_api_key(),
            base_url="https://api.x.ai/v1",
            timeout=75,
            max_retries=1,
        )


class FreeFeedSignalProvider:
    name = "free-feeds"

    def collect_dashboard_signal(
        self,
        *,
        now: datetime,
        categories: tuple[str, ...],
        previous_items: list[dict[str, Any]] | None = None,
    ) -> DashboardSignal:
        del previous_items
        items: list[TrendItem] = []
        for category in categories:
            category_items = _google_news_items(category=category, now=now, limit=3, fresh=True)
            if not category_items:
                category_items = _google_news_items(category=category, now=now, limit=3, fresh=False)
            items.extend(category_items)
        if "technology" in categories:
            items.extend(_hacker_news_items(now=now, limit=3))

        deduped = _dedupe_items(items)[:12]
        topics = tuple(
            {
                "name": item.title,
                "url": x_search_url(item.title),
                "metric": item.metric or item.category,
            }
            for item in deduped[:6]
        )
        status = "ready" if deduped else "empty"
        message = (
            "Fresh public feed signals ready."
            if deduped
            else "No public feed signals could be reached on this check."
        )
        return DashboardSignal(
            status=status,
            message=message,
            checked_at=now.astimezone(timezone.utc).isoformat(),
            next_check_at=None,
            provider=self.name,
            categories=categories,
            items=tuple(deduped),
            x_topics=topics,
        )


def _google_news_items(*, category: str, now: datetime, limit: int, fresh: bool) -> list[TrendItem]:
    query = _category_query(category, fresh=fresh)
    url = (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )
    try:
        payload = _read_url(url)
        root = ET.fromstring(payload)
    except Exception:
        return []

    items: list[TrendItem] = []
    for node in root.findall(".//item")[: limit * 2]:
        title = _clean_google_title(node.findtext("title") or "")
        if not title:
            continue
        published = _parse_rss_time(node.findtext("pubDate"))
        source_name = node.findtext("source")
        link = node.findtext("link")
        summary = f"{category.title()} signal from a public news feed."
        if published:
            age = now.astimezone(timezone.utc) - published.astimezone(timezone.utc)
            hours = max(0, round(age.total_seconds() / 3600, 1))
            summary = f"Public feed item seen about {hours:g} hours ago."
        items.append(
            TrendItem.from_dict(
                {
                    "category": category,
                    "title": title,
                    "summary": summary,
                    "source_name": source_name or "Google News",
                    "source_url": link,
                    "found_at": published.isoformat() if published else now.isoformat(),
                    "heat": "rising",
                    "metric": "public news feed",
                    "why_it_matters": "Worth scanning because it is appearing in a current public feed.",
                    "tags": [category],
                },
                default_category=category,
            )
        )
        if len(items) >= limit:
            break
    return items


def _hacker_news_items(*, now: datetime, limit: int) -> list[TrendItem]:
    threshold = int((now.astimezone(timezone.utc) - timedelta(hours=8)).timestamp())
    fresh_url = (
        "https://hn.algolia.com/api/v1/search_by_date?"
        f"tags=story&numericFilters=created_at_i>{threshold}"
    )
    fallback_url = "https://hn.algolia.com/api/v1/search?tags=front_page"
    try:
        payload = _read_url(fresh_url)
        data = json.loads(payload)
    except Exception:
        data = {}

    hits = data.get("hits") if isinstance(data, dict) else None
    if not isinstance(hits, list):
        hits = []
    if not hits:
        try:
            payload = _read_url(fallback_url)
            data = json.loads(payload)
            hits = data.get("hits") if isinstance(data, dict) else []
        except Exception:
            hits = []
    if not isinstance(hits, list):
        return []

    scored = sorted(
        (hit for hit in hits if isinstance(hit, dict) and hit.get("title")),
        key=lambda hit: (int(hit.get("points") or 0) + int(hit.get("num_comments") or 0) * 2),
        reverse=True,
    )
    items: list[TrendItem] = []
    for hit in scored[:limit]:
        title = str(hit.get("title") or "")
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        comments = int(hit.get("num_comments") or 0)
        points = int(hit.get("points") or 0)
        items.append(
            TrendItem.from_dict(
                {
                    "category": "technology",
                    "title": title,
                    "summary": "A fresh Hacker News thread is picking up discussion.",
                    "source_name": "Hacker News",
                    "source_url": url,
                    "found_at": hit.get("created_at"),
                    "heat": "hot" if comments >= 25 else "rising",
                    "metric": f"{points} points, {comments} comments",
                    "why_it_matters": "Developer attention is often an early signal for useful technical shifts.",
                    "tags": ["technology", "hn"],
                },
                default_category="technology",
            )
        )
    return items


def _category_query(category: str, *, fresh: bool) -> str:
    freshness = " when:1h" if fresh else ""
    queries = {
        "science": f"science breakthrough OR space OR climate OR physics{freshness}",
        "technology": f"technology OR AI OR chips OR software{freshness}",
        "pop culture": f"music OR film OR television OR celebrity OR games{freshness}",
        "world": f"top news OR global conversation{freshness}",
    }
    return queries.get(category, f"{category}{freshness}")


def _read_url(url: str, *, timeout: int = 12) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "MagicWall/0.1 (+https://github.com/diptobiswas/magic-wall)",
        },
    )
    with urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        return response.read().decode("utf-8", errors="replace")


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _parse_rss_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _clean_google_title(value: str) -> str:
    text = " ".join(value.split())
    if " - " in text:
        text = text.rsplit(" - ", 1)[0]
    return text


def _dedupe_items(items: list[TrendItem]) -> list[TrendItem]:
    seen: set[str] = set()
    deduped: list[TrendItem] = []
    for item in items:
        key = item.source_url or item.title.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


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
    raise ValueError("xAI response did not include text output.")
