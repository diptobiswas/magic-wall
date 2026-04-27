from __future__ import annotations

from pathlib import Path

from magic_wall.installer import render_app_service, render_kiosk_service


def test_app_service_contains_cli_entrypoint(tmp_path: Path) -> None:
    service = render_app_service(
        root_dir=tmp_path,
        magic_wall_bin=tmp_path / ".venv" / "bin" / "magic-wall",
        host="127.0.0.1",
        port=8765,
    )

    assert "Description=Magic Wall local art service" in service
    assert "magic-wall run --host 127.0.0.1 --port 8765" in service
    assert "Restart=always" in service


def test_kiosk_service_opens_local_url() -> None:
    service = render_kiosk_service(chromium_bin="/usr/bin/chromium", url="http://127.0.0.1:8765")

    assert "--kiosk" in service
    assert "http://127.0.0.1:8765" in service
    assert "Wants=magic-wall.service" in service
