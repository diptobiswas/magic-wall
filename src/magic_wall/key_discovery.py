from __future__ import annotations

from pathlib import Path
import os
import re


KEY_RE = re.compile(r"(sk-[A-Za-z0-9_-]{20,})")
ENV_RE = re.compile(r"^\s*OPENAI_API_KEY\s*=\s*[\"']?([^\"'\s#]+)", re.MULTILINE)


def discover_openai_api_key() -> str | None:
    env_key = _clean_key(os.environ.get("OPENAI_API_KEY"))
    if env_key:
        return env_key

    for path in candidate_key_files():
        key = _read_key_file(path)
        if key:
            return key
    return None


def candidate_key_files(home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    names = [
        ".cursor-tools/.env",
        ".cityscope/.env",
        ".zshrc",
        ".zprofile",
        ".bash_profile",
        ".codex/config.toml",
        "Downloads/.env",
    ]
    paths = [home / name for name in names]
    for env_file in home.glob("*/.env*"):
        paths.append(env_file)
    return _dedupe(paths)


def _read_key_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    env_match = ENV_RE.search(text)
    if env_match:
        key = _clean_key(env_match.group(1))
        if key:
            return key

    key_match = KEY_RE.search(text)
    if key_match:
        return _clean_key(key_match.group(1))
    return None


def _clean_key(value: str | None) -> str | None:
    if value is None:
        return None
    key = value.strip().strip('"').strip("'")
    return key if KEY_RE.fullmatch(key) else None


def _dedupe(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        expanded = path.expanduser()
        if expanded not in seen:
            seen.add(expanded)
            unique.append(expanded)
    return unique
