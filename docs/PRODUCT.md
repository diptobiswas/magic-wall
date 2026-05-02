# Product

Magic Wall is a touch-optimized AI news-art frame for a Raspberry Pi.

## Purpose

Keep a lightweight ambient screen useful: fun AI art in the background, with quick access to the exact news context that shaped the current wallpaper.

## Current Features

- Ambient AI news-art layer.
- Source-mesh art story discovery from public feeds before paid web search.
- Touch story overlay with title, summary, source, published time, generation time, next refresh, and style.
- Manual art refresh button.
- Art-first screen that reveals news context only after touch.

## Acceptance Criteria

- App boots without an OpenAI key.
- Normal story discovery does not require a web-search tool call when public feed candidates are available.
- Touch targets are large enough for a 7-inch screen.
- The story overlay can be hidden after it is opened.
- API responses never expose keys.
