# Product

Magic Wall is a touch-optimized X Pulse display for a Raspberry Pi.

## Purpose

Keep a lightweight ambient screen useful: fun AI art in the background, hourly signal cards in the foreground, and quick access to what people are talking about.

## Current Features

- Ambient AI news-art layer.
- Source-mesh art story discovery from public feeds before paid web search.
- Hourly X Pulse checks.
- Categories for science, technology, pop culture, and world.
- Optional xAI-powered X Search signal collection.
- Free public feed fallback when xAI is not configured.
- Focused X Pulse overlay with live X search links.
- Manual signal check and art refresh buttons.
- Art-first screen that reveals dashboard information only after touch.

## Acceptance Criteria

- App boots without OpenAI or xAI keys.
- Dashboard checks run hourly by default.
- Image generation and signal checks are independent.
- Normal story discovery does not require a web-search tool call when public feed candidates are available.
- Touch targets are large enough for a 7-inch screen.
- The dashboard can be hidden after it is opened.
- API responses never expose keys.
