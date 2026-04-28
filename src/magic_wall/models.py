from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any


@dataclass(frozen=True)
class NewsStory:
    found: bool
    title: str
    summary: str
    source_name: str | None = None
    source_url: str | None = None
    published_at: str | None = None
    significance: str | None = None
    selection_reason: str | None = None

    def with_compact_title(self, *, max_chars: int = 64) -> "NewsStory":
        return NewsStory(
            found=self.found,
            title=compact_title(self.title, max_chars=max_chars),
            summary=self.summary,
            source_name=self.source_name,
            source_url=self.source_url,
            published_at=self.published_at,
            significance=self.significance,
            selection_reason=self.selection_reason,
        )

    @classmethod
    def quiet(cls, *, now: datetime, reason: str = "No significant news found in the last hour.") -> "NewsStory":
        return cls(
            found=False,
            title="Quiet hour",
            summary=reason,
            source_name=None,
            source_url=None,
            published_at=now.astimezone(timezone.utc).isoformat(),
            significance="quiet",
            selection_reason=reason,
        )

    @classmethod
    def daily_news_fallback(
        cls,
        *,
        now: datetime,
        reason: str = "OpenAI web search did not return a verifiable news story.",
    ) -> "NewsStory":
        timestamp = now.astimezone(timezone.utc).isoformat()
        return cls(
            found=True,
            title=f"Biggest news of the day fallback at {timestamp}",
            summary=(
                "OpenAI web search did not return a verified story payload for this cycle, so this "
                "generation must use the biggest verifiable news story of the day as the visual anchor."
            ),
            source_name="Magic Wall runtime",
            source_url=None,
            published_at=timestamp,
            significance="biggest-news-of-day fallback",
            selection_reason=reason,
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "NewsStory":
        return cls(
            found=bool(value.get("found")),
            title=str(value.get("title") or "Quiet hour"),
            summary=str(value.get("summary") or ""),
            source_name=_optional_string(value.get("source_name")),
            source_url=_optional_string(value.get("source_url")),
            published_at=_optional_string(value.get("published_at")),
            significance=_optional_string(value.get("significance")),
            selection_reason=_optional_string(value.get("selection_reason")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "found": self.found,
            "title": self.title,
            "summary": self.summary,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "published_at": self.published_at,
            "significance": self.significance,
            "selection_reason": self.selection_reason,
        }

    def is_within_window(self, *, now: datetime, minutes: int) -> bool:
        if not self.found or not self.published_at:
            return False
        published = parse_datetime(self.published_at)
        if published is None:
            return False
        now_utc = now.astimezone(timezone.utc)
        published_utc = published.astimezone(timezone.utc)
        return now_utc - timedelta(minutes=minutes) <= published_utc <= now_utc


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compact_title(value: str, *, max_chars: int = 64) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    words = text.split()
    shortened = ""
    for word in words:
        candidate = f"{shortened} {word}".strip()
        if len(candidate) > max_chars - 3:
            break
        shortened = candidate
    if not shortened:
        shortened = text[: max_chars - 3].rstrip()
    return f"{shortened.rstrip(' .,;:-')}..."


@dataclass(frozen=True)
class TrendItem:
    id: str
    category: str
    title: str
    summary: str
    source_name: str | None = None
    source_url: str | None = None
    found_at: str | None = None
    heat: str = "watch"
    metric: str | None = None
    why_it_matters: str | None = None
    tags: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any], *, default_category: str = "general") -> "TrendItem":
        title = compact_title(str(value.get("title") or "Untitled signal"), max_chars=78)
        category = _clean_category(value.get("category")) or default_category
        source_url = _optional_string(value.get("source_url"))
        item_id = _optional_string(value.get("id")) or _stable_id(category, title, source_url)
        return cls(
            id=item_id,
            category=category,
            title=title,
            summary=compact_summary(str(value.get("summary") or value.get("why_it_matters") or ""), max_chars=220),
            source_name=_optional_string(value.get("source_name")) or _optional_string(value.get("source")),
            source_url=source_url,
            found_at=_optional_string(value.get("found_at")) or _optional_string(value.get("published_at")),
            heat=_clean_heat(value.get("heat")),
            metric=_optional_string(value.get("metric")),
            why_it_matters=compact_summary(str(value.get("why_it_matters") or ""), max_chars=180),
            tags=_clean_tags(value.get("tags")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "summary": self.summary,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "found_at": self.found_at,
            "heat": self.heat,
            "metric": self.metric,
            "why_it_matters": self.why_it_matters,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class DashboardSignal:
    status: str
    message: str
    checked_at: str | None
    next_check_at: str | None
    provider: str
    categories: tuple[str, ...]
    items: tuple[TrendItem, ...] = ()
    x_topics: tuple[dict[str, str], ...] = ()

    @classmethod
    def empty(
        cls,
        *,
        categories: tuple[str, ...],
        message: str = "No X Pulse checked yet.",
        provider: str = "none",
    ) -> "DashboardSignal":
        return cls(
            status="empty",
            message=message,
            checked_at=None,
            next_check_at=None,
            provider=provider,
            categories=categories,
        )

    @classmethod
    def error(
        cls,
        *,
        categories: tuple[str, ...],
        message: str,
        checked_at: str | None,
        next_check_at: str | None,
        provider: str = "unknown",
    ) -> "DashboardSignal":
        return cls(
            status="error",
            message=message,
            checked_at=checked_at,
            next_check_at=next_check_at,
            provider=provider,
            categories=categories,
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any], *, categories: tuple[str, ...]) -> "DashboardSignal":
        raw_items = value.get("items")
        items = tuple(
            TrendItem.from_dict(item)
            for item in raw_items
            if isinstance(item, dict)
        ) if isinstance(raw_items, list) else ()
        raw_topics = value.get("x_topics")
        x_topics = tuple(_clean_topic(topic) for topic in raw_topics if isinstance(topic, dict)) if isinstance(raw_topics, list) else ()
        x_topics = tuple(topic for topic in x_topics if topic)
        status = str(value.get("status") or ("ready" if items else "empty"))
        return cls(
            status=status,
            message=str(value.get("message") or ("Fresh signals ready." if items else "No fresh signals found.")),
            checked_at=_optional_string(value.get("checked_at")),
            next_check_at=_optional_string(value.get("next_check_at")),
            provider=str(value.get("provider") or "unknown"),
            categories=tuple(str(category) for category in value.get("categories") or categories),
            items=items,
            x_topics=x_topics,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "checked_at": self.checked_at,
            "next_check_at": self.next_check_at,
            "provider": self.provider,
            "categories": list(self.categories),
            "items": [item.to_dict() for item in self.items],
            "x_topics": list(self.x_topics),
        }


def compact_summary(value: str, *, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip(' .,;:-')}..."


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_category(value: object) -> str | None:
    text = _optional_string(value)
    if not text:
        return None
    return " ".join(text.lower().replace("_", " ").split())


def _clean_heat(value: object) -> str:
    text = _clean_category(value) or "watch"
    return text if text in {"watch", "rising", "hot"} else "watch"


def _clean_tags(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    tags: list[str] = []
    for item in value:
        tag = _clean_category(item)
        if tag and tag not in tags:
            tags.append(compact_title(tag, max_chars=24))
    return tuple(tags[:4])


def _clean_topic(value: dict[str, Any]) -> dict[str, str]:
    name = _optional_string(value.get("name")) or _optional_string(value.get("title"))
    if not name:
        return {}
    topic = {
        "name": compact_title(name, max_chars=42),
        "url": _optional_string(value.get("url")) or x_search_url(name),
    }
    metric = _optional_string(value.get("metric"))
    if metric:
        topic["metric"] = compact_title(metric, max_chars=48)
    return topic


def x_search_url(query: str) -> str:
    from urllib.parse import quote_plus

    return f"https://x.com/search?q={quote_plus(query)}&src=typed_query&f=live"


def _stable_id(category: str, title: str, source_url: str | None) -> str:
    payload = f"{category}\n{title}\n{source_url or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
