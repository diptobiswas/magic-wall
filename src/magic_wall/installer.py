from __future__ import annotations

from pathlib import Path
import textwrap


def render_app_service(*, root_dir: Path, magic_wall_bin: Path, host: str, port: int) -> str:
    return textwrap.dedent(
        f"""\
        [Unit]
        Description=Magic Wall local art service
        After=network-online.target
        Wants=network-online.target

        [Service]
        Type=simple
        WorkingDirectory={root_dir}
        ExecStart={magic_wall_bin} run --host {host} --port {port}
        Restart=always
        RestartSec=10
        Environment=PYTHONUNBUFFERED=1

        [Install]
        WantedBy=default.target
        """
    )


def render_kiosk_service(*, chromium_bin: str, url: str) -> str:
    return textwrap.dedent(
        f"""\
        [Unit]
        Description=Magic Wall Chromium kiosk
        After=magic-wall.service graphical-session.target
        Wants=magic-wall.service

        [Service]
        Type=simple
        ExecStart=/bin/sh -lc '{chromium_bin} --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble --check-for-update-interval=31536000 {url}'
        Restart=always
        RestartSec=5

        [Install]
        WantedBy=default.target
        """
    )
