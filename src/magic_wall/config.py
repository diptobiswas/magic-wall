from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import os
import stat
import textwrap
import tomllib

from .key_discovery import discover_openai_api_key


QUALITY_VALUES = {"low", "medium", "high", "auto"}
OUTPUT_FORMAT_VALUES = {"jpeg", "png", "webp"}
DEFAULT_REFRESH_MINUTES = 240
DEFAULT_NEWS_WINDOW_MINUTES = 60


class ConfigError(ValueError):
    """Raised when Magic Wall configuration is missing or invalid."""


def default_config_dir() -> Path:
    return Path(os.environ.get("MAGIC_WALL_CONFIG_DIR", Path.home() / ".config" / "magic-wall"))


def default_data_dir() -> Path:
    return Path(os.environ.get("MAGIC_WALL_DATA_DIR", Path.home() / ".local" / "share" / "magic-wall"))


def default_config_path() -> Path:
    return default_config_dir() / "config.toml"


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    data_dir: Path
    openai_api_key: str | None = None
    text_model: str = "gpt-5.4-mini"
    image_model: str = "gpt-image-2"
    image_quality: str = "low"
    image_size: str = "1344x800"
    output_format: str = "jpeg"
    refresh_minutes: int = DEFAULT_REFRESH_MINUTES
    news_window_minutes: int = DEFAULT_NEWS_WINDOW_MINUTES
    host: str = "127.0.0.1"
    port: int = 8765
    timezone: str = "local"

    @property
    def refresh_seconds(self) -> int:
        return self.refresh_minutes * 60

    @property
    def image_suffix(self) -> str:
        return "jpg" if self.output_format == "jpeg" else self.output_format

    def with_overrides(self, *, host: str | None = None, port: int | None = None) -> "AppConfig":
        values: dict[str, object] = {}
        if host is not None:
            values["host"] = host
        if port is not None:
            values["port"] = port
        return replace(self, **values)

    def require_api_key(self) -> str:
        key = (self.openai_api_key or "").strip()
        if not key:
            raise ConfigError(
                "OpenAI API key is missing. Run `magic-wall init` or set OPENAI_API_KEY."
            )
        return key


def default_config() -> AppConfig:
    return AppConfig(
        config_path=default_config_path(),
        data_dir=default_data_dir(),
        openai_api_key=discover_openai_api_key(),
    )


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path).expanduser() if path else default_config_path()
    base = default_config()
    if not config_path.exists():
        return replace(base, config_path=config_path, openai_api_key=discover_openai_api_key())

    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    openai = raw.get("openai", {})
    refresh = raw.get("refresh", {})
    server = raw.get("server", {})
    storage = raw.get("storage", {})

    cfg = AppConfig(
        config_path=config_path,
        data_dir=Path(storage.get("data_dir", default_data_dir())).expanduser(),
        openai_api_key=discover_openai_api_key() or _clean_optional(openai.get("api_key")),
        text_model=str(openai.get("text_model", base.text_model)),
        image_model=str(openai.get("image_model", base.image_model)),
        image_quality=str(openai.get("image_quality", base.image_quality)),
        image_size=str(openai.get("image_size", base.image_size)),
        output_format=str(openai.get("output_format", base.output_format)),
        refresh_minutes=int(refresh.get("minutes", base.refresh_minutes)),
        news_window_minutes=int(refresh.get("news_window_minutes", base.news_window_minutes)),
        host=str(server.get("host", base.host)),
        port=int(server.get("port", base.port)),
        timezone=str(server.get("timezone", base.timezone)),
    )
    validate_config(cfg)
    return cfg


def validate_config(cfg: AppConfig) -> None:
    if cfg.refresh_minutes < 1:
        raise ConfigError("refresh.minutes must be at least 1.")
    if cfg.news_window_minutes != 60:
        raise ConfigError("refresh.news_window_minutes must stay at 60 for strict last-hour mode.")
    if cfg.image_quality not in QUALITY_VALUES:
        raise ConfigError(f"openai.image_quality must be one of: {', '.join(sorted(QUALITY_VALUES))}.")
    if cfg.output_format not in OUTPUT_FORMAT_VALUES:
        raise ConfigError(
            f"openai.output_format must be one of: {', '.join(sorted(OUTPUT_FORMAT_VALUES))}."
        )
    if cfg.image_size != "auto":
        width, height = parse_image_size(cfg.image_size)
        if width % 16 != 0 or height % 16 != 0:
            raise ConfigError("openai.image_size dimensions must be multiples of 16.")
    if not (1 <= cfg.port <= 65535):
        raise ConfigError("server.port must be between 1 and 65535.")


def parse_image_size(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width = int(width_text)
        height = int(height_text)
    except (ValueError, AttributeError) as exc:
        raise ConfigError("openai.image_size must look like 1344x800 or auto.") from exc
    if width <= 0 or height <= 0:
        raise ConfigError("openai.image_size dimensions must be positive.")
    return width, height


def write_default_config(
    path: str | Path | None = None,
    *,
    api_key: str | None = None,
    overwrite: bool = False,
) -> Path:
    config_path = Path(path).expanduser() if path else default_config_path()
    if config_path.exists() and not overwrite:
        raise ConfigError(f"Config already exists at {config_path}. Use --force to overwrite.")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(default_config_text(api_key=api_key), encoding="utf-8")
    config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return config_path


def default_config_text(*, api_key: str | None = None) -> str:
    safe_key = (api_key or "").replace('"', '\\"')
    return textwrap.dedent(
        f"""\
        [openai]
        api_key = "{safe_key}"
        text_model = "gpt-5.4-mini"
        image_model = "gpt-image-2"
        image_quality = "low"
        image_size = "1344x800"
        output_format = "jpeg"

        [refresh]
        minutes = 240
        news_window_minutes = 60

        [server]
        host = "127.0.0.1"
        port = 8765
        timezone = "local"
        """
    )


def _clean_optional(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
