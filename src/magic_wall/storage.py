from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import json
import os
import tempfile

from .config import AppConfig
from .models import NewsStory, parse_datetime


class WallStorage:
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_dir = config.data_dir
        self.images_dir = self.data_dir / "images"
        self.state_path = self.data_dir / "state.json"
        self.current_image_path = self.images_dir / f"current.{config.image_suffix}"

    def ensure(self) -> None:
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self.empty_state()
        try:
            with self.state_path.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return self.empty_state(status="error", message="State file could not be read.")
        if not isinstance(state, dict):
            return self.empty_state(status="error", message="State file is invalid.")
        return state

    def write_state(self, state: dict[str, Any]) -> None:
        self.ensure()
        payload = dict(state)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_bytes_atomic(
            self.state_path,
            json.dumps(payload, indent=2, sort_keys=True).encode("utf-8"),
        )

    def write_current_image(self, image_bytes: bytes) -> str:
        self.ensure()
        self._write_bytes_atomic(self.current_image_path, image_bytes)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_path = self.images_dir / f"wallpaper-{timestamp}.{self.config.image_suffix}"
        self._write_bytes_atomic(archive_path, image_bytes)
        return self.current_image_path.name

    def mark_generating(self, *, message: str = "Generating fresh artwork.") -> None:
        state = self.read_state()
        state["status"] = "generating"
        state["message"] = message
        self.write_state(state)

    def mark_error(self, error: str) -> None:
        state = self.read_state()
        state["status"] = "error"
        state["message"] = error
        self.write_state(state)

    def generation_count(self) -> int:
        state = self.read_state()
        count = state.get("generation_count")
        if isinstance(count, int) and count >= 0:
            return count
        return len(list(self.images_dir.glob("wallpaper-*"))) if self.images_dir.exists() else 0

    def recent_stories(self) -> list[dict[str, Any]]:
        state = self.read_state()
        stories = state.get("recent_stories")
        if isinstance(stories, list):
            return [story for story in stories if isinstance(story, dict)][:12]
        story = state.get("story")
        if isinstance(story, dict) and story.get("found"):
            return [_story_memory(story)]
        return []

    def updated_recent_stories(self, story: NewsStory) -> list[dict[str, Any]]:
        recent = self.recent_stories()
        if story.found:
            current = _story_memory(story.to_dict())
            recent = [item for item in recent if item != current]
            recent.insert(0, current)
        return recent[:12]

    def state_for_api(self) -> dict[str, Any]:
        state = self.read_state()
        state.pop("dashboard", None)
        self._apply_current_refresh_schedule(state)
        if self.current_image_path.exists():
            mtime = int(self.current_image_path.stat().st_mtime)
            state["image_url"] = f"/media/{self.current_image_path.name}?v={mtime}"
        else:
            state["image_url"] = None
        state["config"] = {
            "refresh_minutes": self.config.refresh_minutes,
            "news_window_minutes": self.config.news_window_minutes,
            "image_model": self.config.image_model,
            "image_quality": self.config.image_quality,
            "image_size": self.config.image_size,
            "text_model": self.config.text_model,
        }
        return state

    def next_refresh_from_state(self) -> datetime | None:
        state = self.read_state()
        self._apply_current_refresh_schedule(state)
        return parse_datetime(state.get("next_refresh_at"))

    @staticmethod
    def empty_state(*, status: str = "empty", message: str = "No artwork generated yet.") -> dict[str, Any]:
        return {
            "status": status,
            "message": message,
            "generated_at": None,
            "next_refresh_at": None,
            "story": None,
            "style": None,
            "image_url": None,
            "generation_count": 0,
        }

    def _apply_current_refresh_schedule(self, state: dict[str, Any]) -> None:
        generated_at = parse_datetime(state.get("generated_at"))
        if generated_at is None:
            return
        next_refresh = generated_at.astimezone(timezone.utc) + timedelta(
            minutes=self.config.refresh_minutes
        )
        state["next_refresh_at"] = next_refresh.isoformat()

    @staticmethod
    def _write_bytes_atomic(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


def _story_memory(story: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": story.get("title"),
        "source_url": story.get("source_url"),
        "published_at": story.get("published_at"),
    }
