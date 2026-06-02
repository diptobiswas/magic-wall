# Product

Magic Wall is a touch-optimized AI news-art frame for a Raspberry Pi.

## Purpose

Keep a lightweight ambient screen useful: wild infographic art in the background, with quick access to the exact briefing context that shaped the current wallpaper.

## Current Features

- Ambient AI news-infographic layer.
- Source-mesh art story discovery from public feeds before paid web search.
- Multi-story World Machine Report generation with readable article sectors.
- Touch briefing overlay with primary story, article chambers, summaries, sources, published time, generation time, next refresh, and style.
- In-app readable source preview with a persistent return control for kiosk navigation.
- Manual art refresh button.
- Art-first screen that reveals news context only after touch.

## Acceptance Criteria

- App boots without an OpenAI key.
- Normal briefing discovery does not require a web-search tool call when public feed candidates are available.
- Touch targets are large enough for a 7-inch screen.
- The story overlay can be hidden after it is opened.
- Source links do not open trapped Chromium tabs or take the kiosk away from Magic Wall.
- API responses never expose keys.
