from __future__ import annotations

from pathlib import Path

from magic_wall.key_discovery import candidate_key_files, discover_openai_api_key


def test_discovers_key_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test_abcdefghijklmnopqrstuvwxyz")

    assert discover_openai_api_key() == "sk-test_abcdefghijklmnopqrstuvwxyz"


def test_candidate_files_include_common_local_env_paths(tmp_path: Path) -> None:
    paths = candidate_key_files(tmp_path)

    assert tmp_path / ".cursor-tools/.env" in paths
    assert tmp_path / ".zshrc" in paths
