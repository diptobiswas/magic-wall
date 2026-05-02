from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
