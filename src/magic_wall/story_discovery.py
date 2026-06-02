from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import re
import ssl
from typing import Any, Protocol
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .config import AppConfig
from .models import NewsStory, compact_summary, compact_title, parse_datetime
from .openai_provider import OpenAIProvider


MAX_CANDIDATES_FOR_SELECTION = 12
MAX_BRIEFING_STORIES = 5


class StorySelectorProvider(Protocol):
    def find_top_story(
        self,
        *,
        now: datetime,
        window_minutes: int,
        previous_stories: list[dict] | None = None,
    ) -> NewsStory:
        ...

    def select_story_from_candidates(
        self,
        *,
        now: datetime,
        window_minutes: int,
        candidates: list[dict[str, Any]],
        previous_stories: list[dict] | None = None,
    ) -> NewsStory:
        ...

    def generate_wallpaper(self, *, prompt: str) -> bytes:
        ...


class StorySource(Protocol):
    name: str

    def collect(self, *, now: datetime, window_minutes: int) -> list["StoryCandidate"]:
        ...


@dataclass(frozen=True)
class StoryCandidate:
    id: str
    title: str
    summary: str
    source_name: str
    source_url: str | None
    published_at: str | None
    source_type: str
    category: str = "world"
    score: float = 0
    metric: str | None = None
    evidence_count: int = 1
    evidence_sources: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        *,
        title: str,
        summary: str,
        source_name: str,
        source_url: str | None,
        published_at: str | None,
        source_type: str,
        category: str = "world",
        metric: str | None = None,
    ) -> "StoryCandidate":
        clean_title = compact_title(title, max_chars=120)
        clean_source = source_name.strip() or source_type
        return cls(
            id=_stable_id(source_type, clean_title, source_url),
            title=clean_title,
            summary=compact_summary(summary, max_chars=260),
            source_name=clean_source,
            source_url=source_url,
            published_at=published_at,
            source_type=source_type,
            category=category,
            metric=metric,
            evidence_sources=(clean_source,),
        )

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "published_at": self.published_at,
            "source_type": self.source_type,
            "category": self.category,
            "score": round(self.score, 2),
            "metric": self.metric,
            "evidence_count": self.evidence_count,
            "evidence_sources": list(self.evidence_sources),
        }

    def to_news_story(self, *, reason: str) -> NewsStory:
        significance = f"source-mesh score {round(self.score, 1)}"
        if self.evidence_count > 1:
            significance = f"{significance}; {self.evidence_count} corroborating signals"
        return NewsStory(
            found=True,
            title=compact_title(self.title, max_chars=64),
            summary=self.summary,
            source_name=self.source_name,
            source_url=self.source_url,
            published_at=self.published_at,
            significance=significance,
            selection_reason=reason,
        )


class SourceMeshStoryProvider:
    def __init__(
        self,
        config: AppConfig,
        *,
        openai_provider: StorySelectorProvider | None = None,
        collector: "StoryCollector | None" = None,
    ):
        self.config = config
        self.openai_provider = openai_provider or OpenAIProvider(config)
        self.collector = collector or StoryCollector()

    def find_top_story(
        self,
        *,
        now: datetime,
        window_minutes: int,
        previous_stories: list[dict] | None = None,
    ) -> NewsStory:
        candidates = self.collector.collect(now=now, window_minutes=window_minutes)
        ranked = rank_story_candidates(
            candidates,
            now=now,
            window_minutes=window_minutes,
            previous_stories=previous_stories,
        )
        if ranked:
            selected = self._select_with_model(
                ranked=ranked,
                now=now,
                window_minutes=window_minutes,
                previous_stories=previous_stories,
            )
            if _has_required_information(selected):
                return selected
            return ranked[0].to_news_story(reason="source-mesh local ranking fallback")

        return self.openai_provider.find_top_story(
            now=now,
            window_minutes=window_minutes,
            previous_stories=previous_stories,
        )

    def generate_wallpaper(self, *, prompt: str) -> bytes:
        return self.openai_provider.generate_wallpaper(prompt=prompt)

    def find_briefing(
        self,
        *,
        now: datetime,
        window_minutes: int,
        previous_stories: list[dict] | None = None,
    ) -> list[NewsStory]:
        candidates = self.collector.collect(now=now, window_minutes=window_minutes)
        ranked = rank_story_candidates(
            candidates,
            now=now,
            window_minutes=window_minutes,
            previous_stories=previous_stories,
        )
        selected = _select_briefing_candidates(ranked)
        if selected:
            model_selected = self._select_briefing_with_model(
                selected=selected,
                now=now,
                window_minutes=window_minutes,
                previous_stories=previous_stories,
            )
            if model_selected:
                return model_selected
            return [
                candidate.to_news_story(reason="source-mesh briefing selection")
                for candidate in selected
            ]
        find_briefing = getattr(self.openai_provider, "find_briefing", None)
        if callable(find_briefing):
            stories = find_briefing(
                now=now,
                window_minutes=window_minutes,
                previous_stories=previous_stories,
            )
            if isinstance(stories, list) and stories:
                return [story for story in stories if isinstance(story, NewsStory)]
        return [
            self.openai_provider.find_top_story(
                now=now,
                window_minutes=window_minutes,
                previous_stories=previous_stories,
            )
        ]

    def _select_briefing_with_model(
        self,
        *,
        selected: list[StoryCandidate],
        now: datetime,
        window_minutes: int,
        previous_stories: list[dict] | None,
    ) -> list[NewsStory]:
        select_briefing = getattr(self.openai_provider, "select_briefing_from_candidates", None)
        if not callable(select_briefing):
            return []
        candidates = [candidate.to_prompt_dict() for candidate in selected[:MAX_BRIEFING_STORIES]]
        try:
            stories = select_briefing(
                now=now,
                window_minutes=window_minutes,
                candidates=candidates,
                previous_stories=previous_stories,
            )
        except Exception:
            return []
        return [
            story
            for story in stories[:MAX_BRIEFING_STORIES]
            if _has_required_information(story)
            and not _title_has_bad_tail(story.title)
            and "..." not in story.title
            and "…" not in story.title
        ]

    def _select_with_model(
        self,
        *,
        ranked: list[StoryCandidate],
        now: datetime,
        window_minutes: int,
        previous_stories: list[dict] | None,
    ) -> NewsStory:
        candidates = [candidate.to_prompt_dict() for candidate in ranked[:MAX_CANDIDATES_FOR_SELECTION]]
        try:
            story = self.openai_provider.select_story_from_candidates(
                now=now,
                window_minutes=window_minutes,
                candidates=candidates,
                previous_stories=previous_stories,
            )
        except Exception:
            return NewsStory.quiet(now=now, reason="Source mesh model selection failed.")
        if not _story_matches_candidate(story, ranked):
            return NewsStory.quiet(now=now, reason="Source mesh model selection did not match a candidate.")
        return story


class StoryCollector:
    def __init__(self, sources: tuple[StorySource, ...] | None = None):
        self.sources = sources or (
            GoogleNewsSource(),
            HackerNewsSource(),
        )

    def collect(self, *, now: datetime, window_minutes: int) -> list[StoryCandidate]:
        candidates: list[StoryCandidate] = []
        for source in self.sources:
            try:
                candidates.extend(source.collect(now=now, window_minutes=window_minutes))
            except Exception:
                continue
        return candidates


class GoogleNewsSource:
    name = "google-news"

    def collect(self, *, now: datetime, window_minutes: int) -> list[StoryCandidate]:
        del now
        urls = [_google_news_url(query=None)]
        for category, query in _google_news_queries(window_minutes=window_minutes):
            urls.append(_google_news_url(query=query, category=category))

        candidates: list[StoryCandidate] = []
        seen_urls: set[str] = set()
        for url in urls:
            try:
                payload = _read_url(url)
                root = ET.fromstring(payload)
            except Exception:
                continue
            category = _category_from_google_url(url)
            for node in root.findall(".//item")[:24]:
                title = _clean_google_title(node.findtext("title") or "")
                if not title:
                    continue
                link = _clean_optional(node.findtext("link"))
                if link and link in seen_urls:
                    continue
                if link:
                    seen_urls.add(link)
                source_name = _clean_optional(node.findtext("source")) or "Google News"
                published = _parse_rss_time(node.findtext("pubDate"))
                candidates.append(
                    StoryCandidate.create(
                        title=title,
                        summary=f"Current public news signal from {source_name}.",
                        source_name=source_name,
                        source_url=link,
                        published_at=published.isoformat() if published else None,
                        source_type=self.name,
                        category=category,
                        metric="Google News RSS",
                    )
                )
        return candidates


class HackerNewsSource:
    name = "hacker-news"

    def collect(self, *, now: datetime, window_minutes: int) -> list[StoryCandidate]:
        threshold = int(
            (now.astimezone(timezone.utc) - timedelta(minutes=max(window_minutes, 8 * 60))).timestamp()
        )
        urls = [
            (
                "https://hn.algolia.com/api/v1/search_by_date?"
                f"tags=story&hitsPerPage=30&numericFilters=created_at_i>{threshold}"
            ),
            "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30",
        ]
        hits: list[dict[str, Any]] = []
        for url in urls:
            try:
                payload = _read_url(url)
                data = json.loads(payload)
            except Exception:
                continue
            raw_hits = data.get("hits") if isinstance(data, dict) else None
            if isinstance(raw_hits, list):
                hits.extend(hit for hit in raw_hits if isinstance(hit, dict))

        candidates: list[StoryCandidate] = []
        seen_ids: set[str] = set()
        for hit in hits:
            title = _clean_optional(hit.get("title"))
            object_id = _clean_optional(hit.get("objectID"))
            if not title or not object_id or object_id in seen_ids:
                continue
            seen_ids.add(object_id)
            points = _clean_int(hit.get("points"))
            comments = _clean_int(hit.get("num_comments"))
            article_url = _clean_optional(hit.get("url"))
            comments_url = f"https://news.ycombinator.com/item?id={object_id}"
            source_url = article_url or comments_url
            metric = f"{points} points, {comments} comments"
            candidates.append(
                StoryCandidate.create(
                    title=title,
                    summary="A Hacker News story is gathering technical and founder attention.",
                    source_name="Hacker News",
                    source_url=source_url,
                    published_at=_clean_optional(hit.get("created_at")),
                    source_type=self.name,
                    category="technology",
                    metric=metric,
                )
            )
        return candidates


def rank_story_candidates(
    candidates: list[StoryCandidate],
    *,
    now: datetime,
    window_minutes: int,
    previous_stories: list[dict] | None = None,
) -> list[StoryCandidate]:
    clusters = _cluster_candidates(_usable_candidates(candidates))
    ranked = [
        _score_candidate(candidate, now=now, window_minutes=window_minutes, previous_stories=previous_stories)
        for candidate in clusters
    ]
    return sorted(ranked, key=lambda candidate: candidate.score, reverse=True)


def _select_briefing_candidates(candidates: list[StoryCandidate]) -> list[StoryCandidate]:
    selected: list[StoryCandidate] = []
    used_categories: set[str] = set()
    used_domains: set[str] = set()
    for candidate in candidates:
        category = candidate.category.lower()
        domain = _domain(candidate.source_url)
        if category in used_categories and len(selected) < 3:
            continue
        if domain and domain in used_domains and len(selected) < 3:
            continue
        selected.append(candidate)
        used_categories.add(category)
        if domain:
            used_domains.add(domain)
        if len(selected) >= MAX_BRIEFING_STORIES:
            break
    if len(selected) < min(3, len(candidates)):
        for candidate in candidates:
            if candidate not in selected:
                selected.append(candidate)
            if len(selected) >= min(MAX_BRIEFING_STORIES, len(candidates)):
                break
    return selected


def _title_has_bad_tail(title: str) -> bool:
    words = title.strip().split()
    if not words:
        return True
    return words[-1].lower().strip(".,;:-") in {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "creates",
        "for",
        "from",
        "in",
        "of",
        "on",
        "or",
        "prompts",
        "says",
        "the",
        "to",
        "with",
    }


def _usable_candidates(candidates: list[StoryCandidate]) -> list[StoryCandidate]:
    usable: list[StoryCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate.title.strip():
            continue
        key = candidate.source_url or _fingerprint(candidate.title)
        if key in seen:
            continue
        seen.add(key)
        usable.append(candidate)
    return usable


def _cluster_candidates(candidates: list[StoryCandidate]) -> list[StoryCandidate]:
    clusters: list[StoryCandidate] = []
    for candidate in candidates:
        match_index = next(
            (
                index
                for index, existing in enumerate(clusters)
                if _same_story(candidate, existing)
            ),
            None,
        )
        if match_index is None:
            clusters.append(candidate)
            continue
        existing = clusters[match_index]
        clusters[match_index] = _merge_candidates(existing, candidate)
    return clusters


def _merge_candidates(first: StoryCandidate, second: StoryCandidate) -> StoryCandidate:
    preferred = first if _pre_score(first) >= _pre_score(second) else second
    sources = tuple(dict.fromkeys([*first.evidence_sources, *second.evidence_sources]))
    metric = preferred.metric
    if first.metric and second.metric and first.metric != second.metric:
        metric = f"{first.metric}; {second.metric}"
    return replace(
        preferred,
        evidence_count=first.evidence_count + second.evidence_count,
        evidence_sources=sources,
        metric=compact_summary(metric or "", max_chars=120) or None,
    )


def _score_candidate(
    candidate: StoryCandidate,
    *,
    now: datetime,
    window_minutes: int,
    previous_stories: list[dict] | None,
) -> StoryCandidate:
    age_hours = _age_hours(candidate.published_at, now=now)
    freshness = _freshness_score(age_hours, window_minutes=window_minutes)
    authority = _authority_score(candidate.source_name, candidate.source_url)
    evidence = min(22, max(0, candidate.evidence_count - 1) * 8 + len(candidate.evidence_sources) * 2)
    traction = _traction_score(candidate.metric)
    visual = _visual_potential_score(candidate.title, candidate.summary)
    novelty_penalty = _novelty_penalty(candidate, previous_stories=previous_stories)
    low_traction_penalty = _low_traction_penalty(candidate)
    feed_noise_penalty = _feed_noise_penalty(candidate)
    score = (
        freshness
        + authority
        + evidence
        + traction
        + visual
        - novelty_penalty
        - low_traction_penalty
        - feed_noise_penalty
    )
    return replace(candidate, score=round(score, 3))


def _pre_score(candidate: StoryCandidate) -> float:
    return _authority_score(candidate.source_name, candidate.source_url) + _traction_score(candidate.metric)


def _freshness_score(age_hours: float | None, *, window_minutes: int) -> float:
    if age_hours is None:
        return 6
    if age_hours < -0.1:
        return 0
    if age_hours <= 1:
        return 40
    if age_hours <= 4:
        return 28
    if age_hours <= 12:
        return 18
    if age_hours <= 24:
        return 10 if window_minutes > 60 else 2
    return 0


def _authority_score(source_name: str, source_url: str | None) -> float:
    text = f"{source_name} {_domain(source_url)}".lower()
    authority = {
        "reuters": 30,
        "associated press": 30,
        "ap news": 30,
        "bbc": 24,
        "npr": 21,
        "the guardian": 21,
        "new york times": 21,
        "washington post": 20,
        "wall street journal": 20,
        "wsj": 20,
        "financial times": 20,
        "bloomberg": 19,
        "cnbc": 17,
        "nbc": 13,
        "cbs": 13,
        "abc": 13,
        "hacker news": 10,
        ".gov": 16,
        ".edu": 12,
    }
    return max((score for key, score in authority.items() if key in text), default=8)


def _traction_score(metric: str | None) -> float:
    if not metric:
        return 0
    numbers = _metric_numbers(metric)
    if not numbers:
        return 0
    points = numbers[0]
    comments = numbers[1] if len(numbers) > 1 else 0
    return min(12, math.log1p(points) * 2 + math.log1p(comments) * 2.5)


def _low_traction_penalty(candidate: StoryCandidate) -> float:
    if candidate.source_type != "hacker-news":
        return 0
    numbers = _metric_numbers(candidate.metric)
    points = numbers[0] if numbers else 0
    comments = numbers[1] if len(numbers) > 1 else 0
    return 20 if points < 25 and comments < 5 else 0


def _feed_noise_penalty(candidate: StoryCandidate) -> float:
    text = f"{candidate.title} {candidate.summary} {candidate.source_name}".lower()
    noisy_phrases = (
        "licensable picture",
        "reuters connect",
        "screening of",
        "red carpet",
        "photo gallery",
        "in pictures",
        "pictures of the day",
        "best photos",
        "award show",
        "awards:",
        "film festival",
    )
    if any(phrase in text for phrase in noisy_phrases):
        return 55
    return 0


def _metric_numbers(metric: str | None) -> list[int]:
    if not metric:
        return []
    return [int(value) for value in re.findall(r"\d+", metric)]


def _visual_potential_score(title: str, summary: str) -> float:
    text = f"{title} {summary}".lower()
    keywords = {
        "ai",
        "space",
        "nasa",
        "rocket",
        "market",
        "court",
        "strike",
        "deal",
        "crisis",
        "climate",
        "chip",
        "robot",
        "energy",
        "election",
        "king",
        "president",
        "movie",
        "music",
        "launch",
        "fire",
        "storm",
        "discovery",
        "breakthrough",
    }
    hits = sum(1 for keyword in keywords if keyword in text)
    properish = sum(1 for token in title.split() if token[:1].isupper() and len(token) > 3)
    length_bonus = 4 if 18 <= len(title) <= 88 else 0
    return min(18, hits * 3 + properish * 0.8 + length_bonus)


def _novelty_penalty(candidate: StoryCandidate, *, previous_stories: list[dict] | None) -> float:
    if not previous_stories:
        return 0
    candidate_title = _fingerprint(candidate.title)
    candidate_url = candidate.source_url
    for story in previous_stories:
        if not isinstance(story, dict):
            continue
        if candidate_url and story.get("source_url") == candidate_url:
            return 80
        previous_title = _fingerprint(str(story.get("title") or ""))
        if previous_title and _jaccard(candidate_title, previous_title) >= 0.55:
            return 45
    return 0


def _story_matches_candidate(story: NewsStory, candidates: list[StoryCandidate]) -> bool:
    if not _has_required_information(story):
        return False
    story_url = story.source_url
    story_title = _fingerprint(story.title)
    for candidate in candidates[:MAX_CANDIDATES_FOR_SELECTION]:
        if story_url and candidate.source_url == story_url:
            return True
        if _jaccard(story_title, _fingerprint(candidate.title)) >= 0.35:
            return True
    return False


def _has_required_information(story: NewsStory) -> bool:
    return story.found and bool(story.title.strip()) and bool(story.summary.strip())


def _google_news_queries(*, window_minutes: int) -> list[tuple[str, str]]:
    freshness = " when:1h" if window_minutes <= 60 else ""
    return [
        ("world", f"top news OR global politics OR economy OR court OR conflict{freshness}"),
        ("business", f"markets OR economy OR company earnings OR energy OR central bank{freshness}"),
        ("technology", f"AI OR technology OR chips OR software OR cybersecurity{freshness}"),
        ("science", f"science OR space OR climate OR energy OR health breakthrough{freshness}"),
    ]


def _google_news_url(*, query: str | None, category: str = "world") -> str:
    base = "https://news.google.com/rss"
    if not query:
        return f"{base}?hl=en-US&gl=US&ceid=US:en#category=world"
    return (
        f"{base}/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        f"#category={quote_plus(category)}"
    )


def _category_from_google_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.fragment.startswith("category="):
        return parsed.fragment.removeprefix("category=").replace("+", " ")
    return "world"


def _read_url(url: str, *, timeout: int = 12) -> str:
    request = Request(
        url.split("#", 1)[0],
        headers={"User-Agent": "MagicWall/0.1 (+https://github.com/diptobiswas/magic-wall)"},
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


def _same_story(first: StoryCandidate, second: StoryCandidate) -> bool:
    if first.source_url and first.source_url == second.source_url:
        return True
    return _jaccard(_fingerprint(first.title), _fingerprint(second.title)) >= 0.52


def _fingerprint(value: str) -> str:
    words = [
        word
        for word in re.findall(r"[a-z0-9]+", value.lower())
        if word not in _STOPWORDS and len(word) > 2
    ]
    return " ".join(words[:12])


def _jaccard(first: str, second: str) -> float:
    a = set(first.split())
    b = set(second.split())
    if not a or not b:
        return 0
    return len(a & b) / len(a | b)


def _age_hours(published_at: str | None, *, now: datetime) -> float | None:
    published = parse_datetime(published_at)
    if published is None:
        return None
    delta = now.astimezone(timezone.utc) - published.astimezone(timezone.utc)
    return delta.total_seconds() / 3600


def _domain(url: str | None) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.lower().removeprefix("www.")


def _stable_id(source_type: str, title: str, source_url: str | None) -> str:
    payload = f"{source_type}\n{title}\n{source_url or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _clean_optional(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "are",
    "was",
    "were",
    "will",
    "has",
    "have",
    "into",
    "over",
    "after",
    "about",
    "says",
    "say",
    "new",
    "latest",
    "update",
    "updates",
    "live",
}
