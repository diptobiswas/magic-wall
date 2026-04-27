from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .config import ConfigError, load_config, write_default_config
from .generator import MagicWallGenerator
from .key_discovery import discover_openai_api_key
from .server import run_server
from .storage import WallStorage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="magic-wall", description="Raspberry Pi news-to-art appliance.")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.toml.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create local config.")
    init_parser.add_argument("--api-key", default=None, help="OpenAI API key to write into config.")
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing config.")

    run_parser = subparsers.add_parser("run", help="Run the local web service.")
    run_parser.add_argument("--host", default=None, help="Host override.")
    run_parser.add_argument("--port", type=int, default=None, help="Port override.")

    subparsers.add_parser("generate-now", help="Generate a wallpaper immediately.")
    subparsers.add_parser("status", help="Print current status.")

    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            return _init(args)
        if args.command == "run":
            cfg = load_config(args.config).with_overrides(host=args.host, port=args.port)
            run_server(cfg)
            return 0
        if args.command == "generate-now":
            cfg = load_config(args.config)
            cfg.require_api_key()
            state = MagicWallGenerator(cfg).generate_once()
            print(json.dumps(_summary(state), indent=2))
            return 0
        if args.command == "status":
            cfg = load_config(args.config)
            print(json.dumps(WallStorage(cfg).state_for_api(), indent=2))
            return 0
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    return 1


def _init(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY") or discover_openai_api_key()
    config_path = write_default_config(args.config, api_key=api_key, overwrite=args.force)
    print(f"Wrote config to {config_path}")
    if not api_key:
        print("No local OpenAI key was discovered. Add one later with OPENAI_API_KEY or config.toml.")
    return 0


def _summary(state: dict) -> dict:
    story = state.get("story") or {}
    return {
        "status": state.get("status"),
        "generated_at": state.get("generated_at"),
        "next_refresh_at": state.get("next_refresh_at"),
        "story_title": story.get("title"),
        "story_found": story.get("found"),
        "image_url": state.get("image_url"),
    }
