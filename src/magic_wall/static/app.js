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

let currentImageUrl = "";
let latestState = {};
let storyOpen = false;

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

function setBusy(button, busy, label) {
  button.disabled = busy;
  button.textContent = busy ? "Working" : label;
}

function storyData() {
  return latestState.story || {};
}

function displayStatus(state, story) {
  if (state.setup_required) return "Setup needed";
  if (state.status === "generating") return "Making art";
  if (state.status === "error") return "Needs attention";
  if (story.found) return "Wallpaper Story";
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
  const story = storyData();
  const title = story.title || "No wallpaper story yet";
  const summary = story.summary || state.message || "Generate the first wallpaper to fill this in.";

  leadCategoryEl.textContent = story.source_name || "news anchor";
  leadHeatEl.textContent = story.found ? "used for image" : state.status || "waiting";
  leadTitleEl.textContent = title;
  leadSummaryEl.textContent = summary;
  leadWhyEl.textContent = story.significance || story.selection_reason || "";

  leadSourceEl.hidden = !story.source_url;
  if (story.source_url) {
    leadSourceEl.href = story.source_url;
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
  const story = storyData();
  const config = state.config || {};
  storyListEl.replaceChildren();

  const rows = [
    ["Source", story.source_name || "Not selected yet"],
    ["Published", formatDateTime(story.published_at) || "Unknown"],
    ["Generated", formatDateTime(state.generated_at) || "Not generated yet"],
    ["Next art", formatDateTime(state.next_refresh_at) || "Waiting"],
    ["Cadence", config.refresh_minutes ? `${config.refresh_minutes} min` : "Default"],
    ["Style", state.style || "Rotating AI-slop poster"],
  ];

  rows.forEach(([label, value], index) => {
    const row = document.createElement("div");
    row.className = "story-row";
    row.style.setProperty("--index", String(index));

    const name = document.createElement("span");
    name.textContent = label;
    const detail = document.createElement("strong");
    detail.textContent = value;

    row.append(name, detail);
    storyListEl.append(row);
  });
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
  },
  true,
);
hideStoryButton.addEventListener("pointerup", () => setStoryOpen(false));
hideStoryButton.addEventListener("click", () => setStoryOpen(false));
touchCatcher.addEventListener("click", () => {
  if (!storyOpen) setStoryOpen(true);
});
storySheet.addEventListener("click", (event) => event.stopPropagation());

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
