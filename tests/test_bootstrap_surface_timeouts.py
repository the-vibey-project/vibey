# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""build_app hands the declared `[surfaces] adapter_timeout_seconds` to every real surface adapter.

Gap K3 (and sub-doctrine 12.c) require the bound on a sovereign adapter's calls to be a declared
key, not a constant each adapter keeps for itself. Redis is the case that moves: its own default
was 5 seconds, and it now follows the declared 10."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.infrastructure.test_sovereign_surfaces import _InForcePreparer, _mock_pool
from vibey.bootstrap import AppResources, build_app
from vibey.domain.config import (
    DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS,
    BlobConfig,
    BusConfig,
    CacheConfig,
    ConfigStoreConfig,
    DocsConfig,
    EmailConfig,
    FilesConfig,
    MessagingConfig,
    ProjectConfig,
    SecretsConfig,
    SiemConfig,
    SmsConfig,
    SurfacesConfig,
    TrackerConfig,
    VibeyConfig,
)


def _all_surfaces(**extra: object) -> VibeyConfig:
    return VibeyConfig(
        project=ProjectConfig(name="demo"),
        tracker=TrackerConfig(
            url="http://plane", token="t", workspace_slug="my-team", project_id="pid"
        ),
        docs=DocsConfig(url="http://bs", token_id="i", token_secret="s", book_id=3),
        secrets=SecretsConfig(url="http://openbao", token="t"),
        files=FilesConfig(url="http://nc", user="u", password="p"),
        email=EmailConfig(smtp_host="smtp", smtp_port=587),
        sms=SmsConfig(url="http://sms", username="u", password="p"),
        messaging=MessagingConfig(url="http://mx", token="t"),
        config_store=ConfigStoreConfig(url="http://inf", token="t", project_id="p"),
        cache=CacheConfig(url="redis://cache:6379"),
        bus=BusConfig(url="http://bus:15672", username="u", password="p"),
        blob=BlobConfig(url="http://blob:3900", access_key="ak", secret_key="sk"),
        siem=SiemConfig(url="http://siem:9200"),
        **extra,  # type: ignore[arg-type]
    )


def _timeouts(resources: AppResources) -> dict[str, float]:
    """The bound each of the twelve real adapters holds, by surface name."""
    bus: Any = getattr(resources.bus, "_delegate", resources.bus)
    return {
        "tracker": resources.tracker._timeout,  # type: ignore[attr-defined]
        "docs": resources.docs._timeout,  # type: ignore[attr-defined]
        "secrets": resources.secrets._timeout,  # type: ignore[attr-defined]
        "files": resources.files._timeout,  # type: ignore[attr-defined]
        "email": resources.email._timeout,  # type: ignore[attr-defined]
        "sms": resources.sms._timeout,  # type: ignore[attr-defined]
        "messaging": resources.messaging._timeout,  # type: ignore[attr-defined]
        "config_store": resources.config_store._timeout,  # type: ignore[attr-defined]
        "cache": resources.cache._timeout,  # type: ignore[attr-defined]
        "bus": bus._api._timeout,
        "blob": resources.blob._timeout,  # type: ignore[attr-defined]
        "siem": resources.siem._timeout,  # type: ignore[attr-defined]
    }


def _database() -> tuple[object, ...]:
    migrator = MagicMock()
    migrator.apply = AsyncMock()
    return (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=_mock_pool())),
        patch("vibey.bootstrap.PostgresMigrator", **{"from_environ.return_value": migrator}),
        patch("vibey.bootstrap.SchemaPreparer", new=_InForcePreparer),
        patch("vibey.bootstrap.database_url", return_value="postgresql://x"),
    )


@pytest.mark.asyncio
async def test_build_app_hands_the_declared_timeout_to_every_real_adapter() -> None:
    cfg = _all_surfaces(surfaces=SurfacesConfig(adapter_timeout_seconds=7))
    a, b, c, d = _database()
    with a, b, c, d:  # type: ignore[attr-defined]
        async with build_app(config=cfg) as resources:
            assert _timeouts(resources) == dict.fromkeys(_timeouts(resources), 7)
            assert len(_timeouts(resources)) == 12


@pytest.mark.asyncio
async def test_build_app_defaults_every_real_adapter_to_the_surface_timeout() -> None:
    a, b, c, d = _database()
    with a, b, c, d:  # type: ignore[attr-defined]
        async with build_app(config=_all_surfaces()) as resources:
            assert set(_timeouts(resources).values()) == {DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS}


@pytest.mark.asyncio
async def test_the_environment_declares_the_adapter_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    monkeypatch.chdir(tmp_path)  # type: ignore[arg-type]
    monkeypatch.setenv("VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS", "9")
    monkeypatch.setenv("VIBEY_TRACKER_URL", "http://plane")
    monkeypatch.setenv("VIBEY_TRACKER_TOKEN", "t")
    monkeypatch.setenv("VIBEY_TRACKER_WORKSPACE_SLUG", "my-team")
    monkeypatch.setenv("VIBEY_TRACKER_PROJECT_ID", "pid")
    a, b, c, d = _database()
    with a, b, c, d:  # type: ignore[attr-defined]
        async with build_app() as resources:
            assert resources.tracker._timeout == 9  # type: ignore[attr-defined]
