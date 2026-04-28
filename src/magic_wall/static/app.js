const app = document.getElementById("app");
const dashboard = document.getElementById("dashboard");
const touchCatcher = document.getElementById("touch-catcher");
const wallpaper = document.getElementById("wallpaper");
const statusEl = document.getElementById("status");
const providerEl = document.getElementById("provider");
const clockEl = document.getElementById("clock");
const trendListEl = document.getElementById("trend-list");
const leadCategoryEl = document.getElementById("lead-category");
const leadHeatEl = document.getElementById("lead-heat");
const leadTitleEl = document.getElementById("lead-title");
const leadSummaryEl = document.getElementById("lead-summary");
const leadWhyEl = document.getElementById("lead-why");
const leadTagsEl = document.getElementById("lead-tags");
const leadSourceEl = document.getElementById("lead-source");
const artTitleEl = document.getElementById("art-title");
const generatedEl = document.getElementById("generated");
const nextCheckEl = document.getElementById("next-check");
const checkNowButton = document.getElementById("check-now");
const hideDashboardButton = document.getElementById("hide-dashboard");

let currentImageUrl = "";
let latestState = {};
let selectedItemId = "";
let dashboardOpen = false;

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

function setDashboard(open) {
  dashboardOpen = open;
  document.body.classList.toggle("dashboard-open", open);
  dashboard.setAttribute("aria-hidden", open ? "false" : "true");
  touchCatcher.setAttribute("aria-label", "Show X Pulse");
}

function dashboardData() {
  return latestState.dashboard || {};
}

function pulseItems() {
  const pulse = dashboardData();
  const items = Array.isArray(pulse.items) ? pulse.items : [];
  if (items.length) return items;
  const topics = Array.isArray(pulse.x_topics) ? pulse.x_topics : [];
  return topics.map((topic, index) => ({
    id: `topic-${index}-${topic.name || "x"}`,
    category: "x pulse",
    title: topic.name || "X topic",
    summary: topic.metric || "Live X topic.",
    source_url: topic.url || xSearchUrl(topic.name || ""),
    heat: "watch",
    metric: topic.metric || "live",
    tags: ["x"],
  }));
}

function selectedItem() {
  const items = pulseItems();
  return items.find((item) => item.id === selectedItemId) || items[0] || null;
}

function xSearchUrl(query) {
  return `https://x.com/search?q=${encodeURIComponent(query || "")}&src=typed_query&f=live`;
}

function setBusy(button, busy, label) {
  button.disabled = busy;
  button.textContent = busy ? "Checking" : label;
}

function providerLabel(pulse, config) {
  if (pulse.provider === "xai") return "xAI search";
  if (config.xai_configured) return "xAI ready";
  return "xAI key needed";
}

function updateState(state) {
  latestState = state;
  const pulse = dashboardData();
  const config = state.config || {};
  const story = state.story || {};

  const ready = pulse.status === "ready";
  statusEl.textContent = ready ? "X Pulse live" : pulse.status || "X Pulse";
  providerEl.textContent = providerLabel(pulse, config);

  artTitleEl.textContent = pulse.message || "X Pulse";
  generatedEl.textContent = pulse.checked_at ? `checked ${formatTime(pulse.checked_at)}` : "";
  nextCheckEl.textContent = pulse.next_check_at ? `next ${formatTime(pulse.next_check_at)}` : "";

  if (state.image_url && state.image_url !== currentImageUrl) {
    currentImageUrl = state.image_url;
    wallpaper.classList.remove("is-loaded");
    wallpaper.onload = () => wallpaper.classList.add("is-loaded");
    wallpaper.src = state.image_url;
  }

  if (!state.image_url && story.title) {
    artTitleEl.textContent = story.title;
  }

  renderPulseList();
  renderLead();
}

function renderPulseList() {
  trendListEl.replaceChildren();
  const pulse = dashboardData();
  const items = pulseItems();
  app.classList.toggle("is-checking", pulse.status === "checking");

  if (pulse.status === "checking") {
    for (let index = 0; index < 5; index += 1) {
      const skeleton = document.createElement("div");
      skeleton.className = "pulse-row skeleton";
      trendListEl.append(skeleton);
    }
    return;
  }

  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = pulse.message || "No X Pulse yet.";
    trendListEl.append(empty);
    return;
  }

  items.slice(0, 8).forEach((item, index) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = item.id === selectedItemId ? "pulse-row is-selected" : "pulse-row";
    row.style.setProperty("--index", String(index));
    row.addEventListener("click", () => {
      selectedItemId = item.id;
      renderPulseList();
      renderLead();
    });

    const marker = document.createElement("span");
    marker.className = `pulse-dot heat-${item.heat || "watch"}`;

    const body = document.createElement("span");
    body.className = "pulse-row-body";
    const title = document.createElement("strong");
    title.textContent = item.title || "Untitled X topic";
    const meta = document.createElement("span");
    meta.textContent = item.metric || item.source_name || item.category || "X";
    body.append(title, meta);

    row.append(marker, body);
    trendListEl.append(row);
  });
}

function renderLead() {
  const item = selectedItem();
  if (!item) {
    leadCategoryEl.textContent = "x pulse";
    leadHeatEl.textContent = "empty";
    leadTitleEl.textContent = "No X Pulse yet";
    leadSummaryEl.textContent = (latestState.dashboard || {}).message || "Waiting for the next check.";
    leadWhyEl.textContent = "";
    leadTagsEl.replaceChildren();
    leadSourceEl.hidden = true;
    return;
  }

  selectedItemId = item.id;
  leadCategoryEl.textContent = "x pulse";
  leadHeatEl.textContent = item.heat || "watch";
  leadTitleEl.textContent = item.title || "Untitled X topic";
  leadSummaryEl.textContent = item.summary || "";
  leadWhyEl.textContent = item.why_it_matters || "";
  leadSourceEl.hidden = false;
  leadSourceEl.href = item.source_url || xSearchUrl(item.title);

  leadTagsEl.replaceChildren();
  const tags = Array.isArray(item.tags) ? item.tags : [];
  tags.slice(0, 4).forEach((tag) => {
    const pill = document.createElement("span");
    pill.textContent = tag;
    leadTagsEl.append(pill);
  });
  if (item.found_at) {
    const pill = document.createElement("span");
    pill.textContent = formatDateTime(item.found_at);
    leadTagsEl.append(pill);
  }
}

async function loadState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) throw new Error("State request failed");
  updateState(await response.json());
}

async function postCheckNow() {
  setBusy(checkNowButton, true, "Refresh");
  try {
    const response = await fetch("/api/check-now", { method: "POST" });
    if (!response.ok) throw new Error("Request failed");
    await loadState();
  } catch (error) {
    statusEl.textContent = "Error";
    leadTitleEl.textContent = "X Pulse failed";
    leadSummaryEl.textContent = error.message;
  } finally {
    setBusy(checkNowButton, false, "Refresh");
  }
}

checkNowButton.addEventListener("click", postCheckNow);
document.addEventListener(
  "click",
  (event) => {
    if (event.target.closest("#hide-dashboard")) {
      event.preventDefault();
      event.stopPropagation();
      setDashboard(false);
    }
  },
  true,
);
hideDashboardButton.addEventListener("pointerup", () => setDashboard(false));
hideDashboardButton.addEventListener("click", () => setDashboard(false));
touchCatcher.addEventListener("click", () => {
  if (!dashboardOpen) setDashboard(true);
});
dashboard.addEventListener("click", (event) => event.stopPropagation());

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
