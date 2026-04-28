# Decisions

## Separate Art And Signals

Hourly checks update dashboard data only. Art generation keeps its own cadence so useful checks do not require image-generation cost.

## Source Mesh Before Paid Search

Art generation now gathers public-feed candidates first, ranks them locally, and uses the text model to choose from finalists without web search. OpenAI web search remains a fallback for empty or unusable source-mesh results.

## xAI Is Optional

xAI is the best path for X-native signal discovery, but the app must still boot and show free public feed signals without it.

The default X Pulse model is `grok-4` because live X Search completed with it during verification, while `grok-4.20-reasoning` timed out on the same key.

## X Webview Is Best Effort

The touch overlay is X Pulse only. It uses API-generated signal cards and direct X links rather than an embedded X webview, because X may require login or block iframe rendering.

## No New Frontend Build Step

The kiosk stays static HTML/CSS/JS to keep Raspberry Pi install simple.
