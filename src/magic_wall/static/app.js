const app = document.getElementById("app");
const storySheet = document.getElementById("story-sheet");
const touchCatcher = document.getElementById("touch-catcher");
const wallpaper = document.getElementById("wallpaper");
const statusEl = document.getElementById("status");
const providerEl = document.getElementById("provider");
const clockEl = document.getElementById("clock");
const storyListEl = document.getElementById("story-list");
const leadCategoryEl = document.getElementById("lead-category");
const leadHeatEl = document.getElementById("lead-heat");
const leadTitleEl = document.getElementById("lead-title");
const leadSummaryEl = document.getElementById("lead-summary");
const leadWhyEl = document.getElementById("lead-why");
const leadTagsEl = document.getElementById("lead-tags");
const leadSourceEl = document.getElementById("lead-source");
const artTitleEl = document.getElementById("art-title");
const generatedEl = document.getElementById("generated");
const nextRefreshEl = document.getElementById("next-refresh");
const regenerateButton = document.getElementById("regenerate");
const hideStoryButton = document.getElementById("hide-story");
const sourceViewer = document.getElementById("source-viewer");
const sourceBody = document.getElementById("source-body");
const sourceTitleEl = document.getElementById("source-title");
const sourceLabelEl = document.getElementById("source-label");
const closeSourceButton = document.getElementById("close-source");

let currentImageUrl = "";
let latestState = {};
let storyOpen = false;
let sourceOpen = false;
let sourceRequest = null;

function formatTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function updateClock() {
  const now = new Date();
  clockEl.textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function setStoryOpen(open) {
  storyOpen = open;
  document.body.classList.toggle("story-open", open);
  storySheet.setAttribute("aria-hidden", open ? "false" : "true");
  touchCatcher.setAttribute("aria-label", "Show story details");
}

async function setSourceOpen(open, source = {}) {
  sourceOpen = open;
  document.body.classList.toggle("source-open", open);
  sourceViewer.setAttribute("aria-hidden", open ? "false" : "true");

  if (!open) {
    if (sourceRequest) sourceRequest.abort();
    sourceRequest = null;
    sourceBody.replaceChildren();
    return;
  }

  const url = source.url || "";
  sourceTitleEl.textContent = compact(source.title || url, 86) || "Source article";
  sourceLabelEl.textContent = source.label || "Source article";
  renderSourceLoading(url);

  if (!url) return;
  if (sourceRequest) sourceRequest.abort();
  sourceRequest = new AbortController();

  try {
    const response = await fetch(`/api/source-preview?url=${encodeURIComponent(url)}`, {
      cache: "no-store",
      signal: sourceRequest.signal,
    });
    if (!response.ok) throw new Error("Source preview unavailable");
    renderSourcePreview(await response.json(), source);
  } catch (error) {
    if (error.name !== "AbortError") renderSourceFallback(url, source);
  }
}

function renderSourceLoading(url) {
  sourceBody.replaceChildren();
  const status = document.createElement("p");
  status.className = "source-loading";
  status.textContent = "Loading readable source preview...";
  const origin = document.createElement("small");
  origin.textContent = displayUrl(url);
  sourceBody.append(status, origin);
}

function renderSourcePreview(preview, source) {
  const titleText = genericSourceTitle(preview.title) ? source.title : preview.title;
  sourceTitleEl.textContent = compact(titleText || source.title || "Source article", 86);
  sourceLabelEl.textContent = preview.site || source.label || "Source article";
  sourceBody.replaceChildren();

  const eyebrow = document.createElement("span");
  eyebrow.className = "source-eyebrow";
  eyebrow.textContent = preview.site || displayUrl(preview.url || source.url);

  const title = document.createElement("h2");
  title.textContent = titleText || source.title || "Source article";

  const description = document.createElement("p");
  description.className = "source-description";
  description.textContent =
    preview.description ||
    source.summary ||
    "Magic Wall opened a kiosk-safe preview so the touchscreen always has a way back.";

  sourceBody.append(eyebrow, title, description);

  const paragraphs = Array.isArray(preview.paragraphs) ? preview.paragraphs : [];
  if (paragraphs.length) {
    paragraphs.forEach((item) => {
      const paragraph = document.createElement("p");
      paragraph.textContent = item;
      sourceBody.append(paragraph);
    });
  } else {
    [source.summary, source.significance]
      .filter(Boolean)
      .forEach((item) => {
        const paragraph = document.createElement("p");
        paragraph.textContent = item;
        sourceBody.append(paragraph);
      });
    if (!source.summary && !source.significance) {
      const empty = document.createElement("p");
      empty.className = "source-muted";
      empty.textContent = "This source did not expose readable article text, but the briefing remains available.";
      sourceBody.append(empty);
    }
  }

  const urlNote = document.createElement("small");
  urlNote.textContent = displayUrl(preview.url || source.url);
  sourceBody.append(urlNote);
}

function renderSourceFallback(url, source) {
  sourceBody.replaceChildren();
  const eyebrow = document.createElement("span");
  eyebrow.className = "source-eyebrow";
  eyebrow.textContent = "Preview blocked";
  const title = document.createElement("h2");
  title.textContent = source.title || "Source preview unavailable";
  const note = document.createElement("p");
  note.className = "source-description";
  note.textContent =
    "The article blocked a readable preview. Use Briefing to return; Magic Wall will not open a trapped browser tab.";
  sourceBody.append(eyebrow, title, note);
  if (source.summary) {
    const summary = document.createElement("p");
    summary.textContent = source.summary;
    sourceBody.append(summary);
  }
  if (source.significance) {
    const significance = document.createElement("p");
    significance.textContent = source.significance;
    sourceBody.append(significance);
  }
  const urlText = document.createElement("small");
  urlText.textContent = displayUrl(url);
  sourceBody.append(urlText);
}

function displayUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return url || "";
  }
}

function genericSourceTitle(title) {
  return ["Google News", "News"].includes(String(title || "").trim());
}

function setBusy(button, busy, label) {
  button.disabled = busy;
  button.textContent = busy ? "Working" : label;
}

function storyData() {
  return latestState.story || {};
}

function briefingData() {
  const briefing = Array.isArray(latestState.briefing) ? latestState.briefing : [];
  return briefing.length ? briefing : [storyData()].filter((story) => story && story.title);
}

function compact(value, maxLength) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) return text;
  const trimmed = text.slice(0, maxLength).replace(/[\s.,;:-]+$/, "");
  return trimmed.replace(/\s+(a|an|and|as|at|by|for|from|in|of|on|or|the|to|with)$/i, "");
}

function displayStatus(state, story) {
  if (state.setup_required) return "Setup needed";
  if (state.status === "generating") return "Making art";
  if (state.status === "error") return "Needs attention";
  if (story.found) return "World Machine";
  return "Quiet hour";
}

function providerLabel(state) {
  const config = state.config || {};
  if (state.setup_required) return "no key";
  return config.text_model || "local";
}

function updateState(state) {
  latestState = state;
  const story = storyData();

  statusEl.textContent = displayStatus(state, story);
  providerEl.textContent = providerLabel(state);
  artTitleEl.textContent = story.title || "Magic Wall";
  generatedEl.textContent = state.generated_at ? `made ${formatTime(state.generated_at)}` : "";
  nextRefreshEl.textContent = state.next_refresh_at ? `next ${formatTime(state.next_refresh_at)}` : "";
  app.classList.toggle("is-generating", state.status === "generating");

  if (state.image_url && state.image_url !== currentImageUrl) {
    currentImageUrl = state.image_url;
    wallpaper.classList.remove("is-loaded");
    wallpaper.onload = () => wallpaper.classList.add("is-loaded");
    wallpaper.src = state.image_url;
  }

  renderLead();
  renderStoryList();
}

function renderLead() {
  const state = latestState;
  const stories = briefingData();
  const story = stories[0] || storyData();
  const title = story.title || "No briefing yet";
  const summary = story.summary || state.message || "Generate the first World Machine report to fill this in.";

  leadCategoryEl.textContent = story.source_name || "news anchor";
  leadHeatEl.textContent = story.found ? `${stories.length} sectors` : state.status || "waiting";
  leadTitleEl.textContent = title;
  leadSummaryEl.textContent = compact(summary, 190);
  leadWhyEl.textContent = compact(story.significance || story.selection_reason || "", 150);

  leadSourceEl.hidden = !story.source_url;
  if (story.source_url) {
    leadSourceEl.href = story.source_url;
    leadSourceEl.dataset.sourceTitle = title;
    leadSourceEl.dataset.sourceLabel = story.source_name || "Primary source";
    leadSourceEl.dataset.sourceSummary = story.summary || "";
    leadSourceEl.dataset.sourceSignificance = story.significance || story.selection_reason || "";
  }

  leadTagsEl.replaceChildren();
  [
    story.published_at ? `published ${formatDateTime(story.published_at)}` : "",
    state.generated_at ? `made ${formatDateTime(state.generated_at)}` : "",
    story.source_name || "",
  ]
    .filter(Boolean)
    .slice(0, 4)
    .forEach((label) => {
      const pill = document.createElement("span");
      pill.textContent = label;
      leadTagsEl.append(pill);
    });
}

function renderStoryList() {
  const state = latestState;
  const config = state.config || {};
  const stories = briefingData();
  storyListEl.replaceChildren();

  if (!stories.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state compact";
    empty.textContent = "No briefing sectors yet.";
    storyListEl.append(empty);
    return;
  }

  stories.slice(0, 5).forEach((story, index) => {
    const row = story.source_url ? document.createElement("a") : document.createElement("div");
    row.className = "story-row briefing-card";
    row.style.setProperty("--index", String(index));
    if (story.source_url) {
      row.href = story.source_url;
      row.target = "_blank";
      row.rel = "noreferrer";
      row.dataset.sourceTitle = story.title || "Source article";
      row.dataset.sourceLabel = `Sector ${index + 1} · ${story.source_name || "Source"}`;
      row.dataset.sourceSummary = story.summary || "";
      row.dataset.sourceSignificance = story.significance || story.selection_reason || "";
    }

    const name = document.createElement("span");
    name.textContent = `Sector ${index + 1} · ${story.source_name || "Source"}`;

    const title = document.createElement("strong");
    title.textContent = compact(story.title || "Untitled story", 64);

    const summary = document.createElement("p");
    summary.textContent = compact(story.summary || story.significance || "", 118);

    const meta = document.createElement("small");
    meta.textContent = [
      formatDateTime(story.published_at) || "Time unknown",
      story.significance ? compact(story.significance, 48) : "",
    ]
      .filter(Boolean)
      .join(" · ");

    row.append(name, title, summary, meta);
    storyListEl.append(row);
  });

  const meta = document.createElement("div");
  meta.className = "story-row system-row";
  meta.style.setProperty("--index", String(stories.length));
  const label = document.createElement("span");
  label.textContent = "Artwork";
  const value = document.createElement("strong");
  value.textContent = [
    config.image_quality ? `${config.image_quality} quality` : "",
    state.style || "World Machine Report",
    state.generated_at ? `made ${formatTime(state.generated_at)}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
  meta.append(label, value);
  storyListEl.append(meta);
}

async function loadState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) throw new Error("State request failed");
  updateState(await response.json());
}

async function postRegenerate() {
  setBusy(regenerateButton, true, "New art");
  try {
    const response = await fetch("/api/regenerate", { method: "POST" });
    if (!response.ok) throw new Error("Request failed");
    await loadState();
  } catch (error) {
    statusEl.textContent = "Error";
    leadTitleEl.textContent = "Could not start new art";
    leadSummaryEl.textContent = error.message;
  } finally {
    setBusy(regenerateButton, false, "New art");
  }
}

regenerateButton.addEventListener("click", postRegenerate);
document.addEventListener(
  "click",
  (event) => {
    if (event.target.closest("#hide-story")) {
      event.preventDefault();
      event.stopPropagation();
      setStoryOpen(false);
    }

    const sourceLink = event.target.closest("a[href]");
    if (sourceLink && sourceLink.closest("#story-sheet")) {
      event.preventDefault();
      event.stopPropagation();
      void setSourceOpen(true, {
        url: sourceLink.href,
        title: sourceLink.dataset.sourceTitle || sourceLink.textContent,
        label: sourceLink.dataset.sourceLabel || "Source article",
        summary: sourceLink.dataset.sourceSummary || "",
        significance: sourceLink.dataset.sourceSignificance || "",
      });
    }
  },
  true,
);
hideStoryButton.addEventListener("pointerup", () => setStoryOpen(false));
hideStoryButton.addEventListener("click", () => setStoryOpen(false));
closeSourceButton.addEventListener("click", () => void setSourceOpen(false));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && sourceOpen) {
    void setSourceOpen(false);
    return;
  }
  if (event.key === "Escape" && storyOpen) {
    setStoryOpen(false);
  }
});
touchCatcher.addEventListener("click", () => {
  if (!storyOpen) setStoryOpen(true);
});
storySheet.addEventListener("click", (event) => event.stopPropagation());
sourceViewer.addEventListener("click", (event) => event.stopPropagation());

updateClock();
setInterval(updateClock, 1000);
loadState().catch((error) => {
  statusEl.textContent = "Offline";
  leadTitleEl.textContent = "Local service not ready";
  leadSummaryEl.textContent = error.message;
});
setInterval(() => {
  loadState().catch(() => {});
}, 60000);
