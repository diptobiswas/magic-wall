const stage = document.getElementById("stage");
const wallpaper = document.getElementById("wallpaper");
const overlay = document.getElementById("overlay");
const statusEl = document.getElementById("status");
const titleEl = document.getElementById("title");
const summaryEl = document.getElementById("summary");
const sourceEl = document.getElementById("source");
const generatedEl = document.getElementById("generated");
const nextEl = document.getElementById("next");
const styleEl = document.getElementById("style");
const refreshButton = document.getElementById("refresh");
const closeButton = document.getElementById("close");

let currentImageUrl = "";
let overlayOpen = false;

function setOverlay(open) {
  overlayOpen = open;
  document.body.classList.toggle("overlay-open", open);
  overlay.setAttribute("aria-hidden", open ? "false" : "true");
}

function formatTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function updateState(state) {
  const story = state.story || {};
  statusEl.textContent = state.status === "ready" ? "Fresh artwork" : state.status || "Waiting";
  titleEl.textContent = story.title || (state.setup_required ? "OpenAI key needed" : "Magic Wall");
  summaryEl.textContent =
    story.summary || state.message || "Tap regenerate after setup to create the first artwork.";
  sourceEl.textContent = story.source_name || "";
  generatedEl.textContent = state.generated_at ? `made ${formatTime(state.generated_at)}` : "";
  nextEl.textContent = state.next_refresh_at ? `next ${formatTime(state.next_refresh_at)}` : "";
  styleEl.textContent = state.style || "";

  if (state.image_url && state.image_url !== currentImageUrl) {
    currentImageUrl = state.image_url;
    wallpaper.classList.remove("is-loaded");
    wallpaper.onload = () => wallpaper.classList.add("is-loaded");
    wallpaper.src = state.image_url;
  }
}

async function loadState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) throw new Error("State request failed");
  updateState(await response.json());
}

async function regenerate() {
  refreshButton.disabled = true;
  refreshButton.textContent = "Working";
  try {
    const response = await fetch("/api/regenerate", { method: "POST" });
    if (!response.ok) throw new Error("Regenerate request failed");
    await loadState();
  } catch (error) {
    statusEl.textContent = "Error";
    summaryEl.textContent = error.message;
    setOverlay(true);
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Regenerate";
  }
}

stage.addEventListener("click", (event) => {
  if (event.target.closest("button")) return;
  setOverlay(!overlayOpen);
});

closeButton.addEventListener("click", () => setOverlay(false));
refreshButton.addEventListener("click", regenerate);

loadState().catch((error) => {
  statusEl.textContent = "Offline";
  summaryEl.textContent = error.message;
  setOverlay(true);
});

setInterval(() => {
  loadState().catch(() => {});
}, 60000);
