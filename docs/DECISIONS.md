# Decisions

## Story Overlay Only

The X Pulse/dashboard feature was removed because trend checks failed too often. The touch overlay now shows only the news story and generation metadata behind the current wallpaper.

## Source Mesh Before Paid Search

Art generation now gathers public-feed candidates first, ranks them locally, and uses the text model to choose from finalists without web search. OpenAI web search remains a fallback for empty or unusable source-mesh results.

## No New Frontend Build Step

The kiosk stays static HTML/CSS/JS to keep Raspberry Pi install simple.
