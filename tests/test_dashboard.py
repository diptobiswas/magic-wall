from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from magic_wall.config import AppConfig
from magic_wall.dashboard import DashboardUpdater, FreeFeedSignalProvider, XaiSignalProvider, build_signal_provider
from magic_wall.models import DashboardSignal, TrendItem
from magic_wall.storage import WallStorage


class FakeSignalProvider:
    name = "fake"

    def __init__(self) -> None:
        self.previous_items = None

    def collect_dashboard_signal(self, *, now, categories, previous_items=None):
        self.previous_items = previous_items
        return DashboardSignal(
            status="ready",
            message="Fresh fake signal.",
            checked_at=now.isoformat(),
            next_check_at=None,
            provider=self.name,
            categories=categories,
            items=(
                TrendItem.from_dict(
                    {
                        "category": "science",
                        "title": "Lab result starts a useful debate",
                        "summary": "People are discussing a new lab result.",
                        "source_url": "https://example.com/lab",
                    }
                ),
            ),
        )


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return type(
            "FakeResponse",
            (),
            {
                "output_text": (
                    '{"status":"ready","message":"X is talking about AI chips.",'
                    '"items":[{"category":"x pulse","title":"AI chip argument",'
                    '"summary":"X posts are clustering around a chip supply argument.",'
                    '"source_name":"X","source_url":"https://x.com/search?q=ai+chips&f=live",'
                    '"heat":"rising","metric":"multiple current posts","tags":["ai","chips"]}],'
                    '"x_topics":[{"name":"AI chips","url":"https://x.com/search?q=ai+chips&f=live",'
                    '"metric":"rising discussion"}]}'
                )
            },
        )()


class FakeXaiClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def make_config(tmp_path: Path, *, xai_api_key: str | None = None) -> AppConfig:
    return AppConfig(
        config_path=tmp_path / "config.toml",
        data_dir=tmp_path / "data",
        xai_api_key=xai_api_key,
    )


def test_build_signal_provider_uses_free_feeds_without_xai_key(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)

    provider = build_signal_provider(cfg)

    assert isinstance(provider, FreeFeedSignalProvider)


def test_xai_signal_provider_uses_x_search_only(tmp_path: Path) -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    cfg = make_config(tmp_path, xai_api_key="xai-test")
    client = FakeXaiClient()

    signal = XaiSignalProvider(cfg, client=client).collect_dashboard_signal(
        now=now,
        categories=("science", "technology"),
    )

    request = client.responses.kwargs
    assert request["model"] == "grok-4"
    assert request["tools"] == [
        {
            "type": "x_search",
            "from_date": "2026-04-28",
            "to_date": "2026-04-28",
        }
    ]
    assert "Web Search" not in request["input"][0]["content"]
    assert signal.provider == "xai"
    assert signal.items[0].category == "x pulse"
    assert signal.x_topics[0]["name"] == "AI chips"


def test_dashboard_updater_writes_next_hour_schedule(tmp_path: Path) -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    cfg = make_config(tmp_path)
    storage = WallStorage(cfg)
    provider = FakeSignalProvider()

    dashboard = DashboardUpdater(
        cfg,
        provider=provider,
        storage=storage,
        clock=lambda: now,
    ).refresh_once()

    assert dashboard["status"] == "ready"
    assert dashboard["checked_at"] == "2026-04-28T12:00:00+00:00"
    assert dashboard["next_check_at"] == "2026-04-28T13:00:00+00:00"
    assert dashboard["items"][0]["title"] == "Lab result starts a useful debate"


def test_dashboard_updater_passes_previous_items_to_provider(tmp_path: Path) -> None:
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    cfg = make_config(tmp_path)
    storage = WallStorage(cfg)
    provider = FakeSignalProvider()
    DashboardUpdater(cfg, provider=provider, storage=storage, clock=lambda: now).refresh_once()

    second_provider = FakeSignalProvider()
    DashboardUpdater(cfg, provider=second_provider, storage=storage, clock=lambda: now).refresh_once()

    assert second_provider.previous_items == [
        {
            "category": "science",
            "title": "Lab result starts a useful debate",
            "source_url": "https://example.com/lab",
            "found_at": None,
        }
    ]
