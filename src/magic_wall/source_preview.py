from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import re
import ssl
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import certifi


MAX_BYTES = 600_000
MAX_PARAGRAPHS = 8
TIMEOUT_SECONDS = 8


@dataclass(frozen=True)
class SourcePreview:
    url: str
    title: str
    description: str
    paragraphs: list[str]
    site: str

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "paragraphs": self.paragraphs,
            "site": self.site,
        }


def fetch_source_preview(url: str) -> SourcePreview:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Source URL must be http or https.")

    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 "
                "(KHTML, like Gecko) MagicWall/0.1 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=TIMEOUT_SECONDS, context=ssl_context) as response:
        final_url = response.geturl() or url
        content = response.read(MAX_BYTES)
        content_type = response.headers.get_content_charset() or "utf-8"

    text = content.decode(content_type, errors="replace")
    parsed_final = urlparse(final_url)
    preview = _SourcePreviewParser()
    preview.feed(text)
    title = _clean_text(preview.title or preview.og_title or parsed_final.netloc)
    description = _clean_text(preview.description or "")
    paragraphs = [_clean_text(item) for item in preview.paragraphs]
    paragraphs = [item for item in paragraphs if len(item) >= 45][:MAX_PARAGRAPHS]

    return SourcePreview(
        url=final_url,
        title=title,
        description=description,
        paragraphs=paragraphs,
        site=parsed_final.netloc.replace("www.", ""),
    )


class _SourcePreviewParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.og_title = ""
        self.paragraphs: list[str] = []
        self._ignored_depth = 0
        self._in_title = False
        self._in_paragraph = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if tag in {"script", "style", "nav", "footer", "header", "aside", "noscript"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == "title":
            self._in_title = True
            self._buffer = []
            return
        if tag == "meta":
            name = attr_map.get("name", "").lower()
            prop = attr_map.get("property", "").lower()
            content = attr_map.get("content", "")
            if name == "description":
                self.description = self.description or content
            if prop == "og:title":
                self.og_title = self.og_title or content
            if prop == "og:description":
                self.description = self.description or content
            return
        if tag == "p":
            self._in_paragraph = True
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "footer", "header", "aside", "noscript"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            return
        if self._ignored_depth:
            return
        if tag == "title" and self._in_title:
            self.title = self.title or " ".join(self._buffer)
            self._in_title = False
            self._buffer = []
            return
        if tag == "p" and self._in_paragraph:
            self.paragraphs.append(" ".join(self._buffer))
            self._in_paragraph = False
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._in_title or self._in_paragraph:
            self._buffer.append(data)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()
