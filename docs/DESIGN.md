# Design

Magic Wall should feel like an ambient object first and an annotated briefing machine second.

## Principles

- Keep the generated image as the default full-screen view.
- Reveal information only after touch, then make it easy to hide again.
- Keep a visible way back to the briefing whenever a source is opened.
- Make generated images visually intense, but keep information hierarchy decipherable.
- Use dense information only where it explains the current wallpaper.
- Favor big touch targets over tiny controls.
- Keep text short and useful.
- Use motion for state changes, not decoration.

## Briefing Overlay Layout

- Hidden by default over the artwork.
- Header: status, time, provider, hide.
- Left: primary briefing sector title, summary, significance, source link.
- Right: article chamber list with compact summaries, source names, timing, and impact tags.
- Footer: primary title, generated time, manual art refresh.

## Source Viewer

- Renders source links as a Magic Wall-owned readable preview instead of an embedded page.
- Top bar: large back-to-briefing control and compact source context.
- Never opens a new browser tab from kiosk mode.
- The return control must remain visible in Chromium kiosk mode.

## Visual Tone

Dark glass panels over bright artwork, sharp lime/blue/coral chamber accents, and readable briefing rows. Avoid cramped paragraph text and clipped labels.
