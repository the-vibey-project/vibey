# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for wiring notification services with sovereign surface ports in build_app."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from vibey.bootstrap import build_app
from vibey.domain.config import MessagingConfig, ProjectConfig, VibeyConfig
from vibey.infrastructure.db.ledger_guard import LedgerGuardStatus
from vibey.infrastructure.email.in_memory import InMemoryEmail
from vibey.infrastructure.messaging.in_memory import InMemoryMessaging
from vibey.infrastructure.sms.in_memory import InMemorySms


def _mock_pool() -> MagicMock:
    mock_conn = MagicMock()
    mock_conn.fetchval = AsyncMock(return_value="170000")
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    mock_pool.acquire.return_value.__aexit__.return_value = None
    mock_pool.close = AsyncMock()
    return mock_pool


class _InForcePreparer:
    """build_app's migrate-and-inspect step, for tests about what it wires afterwards."""

    def __init__(self, **_: object) -> None:
        pass

    async def prepare(self, *_: object) -> LedgerGuardStatus:
        return LedgerGuardStatus("app")


@pytest.mark.asyncio
async def test_build_app_hands_the_sovereign_ports_to_notifications() -> None:
    cfg = VibeyConfig(
        project=ProjectConfig(name="demo"),
        messaging=MessagingConfig(room_id="!ops:matrix.test"),
    )
    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=_mock_pool())),
        patch("vibey.bootstrap.PostgresMigrator") as migrator_cls,
        patch("vibey.bootstrap.SchemaPreparer", new=_InForcePreparer),
        patch("vibey.bootstrap.database_url", return_value="postgresql://x"),
    ):
        migrator_cls.from_environ.return_value = MagicMock(apply=AsyncMock())
        async with build_app(config=cfg) as resources:
            assert isinstance(resources.messaging, InMemoryMessaging)
            assert isinstance(resources.email, InMemoryEmail)
            assert isinstance(resources.sms, InMemorySms)

            project_config = {
                "notifications": {
                    "enabled": True,
                    "desktop": False,
                    "messaging": True,
                    "email_to": ["ops@example.org"],
                    "sms_to": ["+15551234567"],
                }
            }
            res = await resources.notifications.notify(
                project_id=uuid4(),
                kind="run_completed",
                title="Run Completed",
                message="done",
                config=project_config,
            )
            assert res == {
                "desktop": False,
                "webhooks": [],
                "messaging": True,
                "email": [True],
                "sms": [True],
            }
            assert len(resources.messaging.sent) == 1
            assert resources.messaging.sent[0]["channel_id"] == "!ops:matrix.test"
            assert "[vibey] Run Completed\ndone" in resources.messaging.sent[0]["message"]
            assert len(resources.email.sent) == 1
            assert resources.email.sent[0]["to"] == "ops@example.org"
            assert len(resources.sms.sent_sms) == 1
            assert resources.sms.sent_sms[0]["phone_number"] == "+15551234567"


@pytest.mark.asyncio
async def test_build_app_without_a_room_sends_no_matrix_message() -> None:
    cfg = VibeyConfig(
        project=ProjectConfig(name="demo"),
    )
    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=_mock_pool())),
        patch("vibey.bootstrap.PostgresMigrator") as migrator_cls,
        patch("vibey.bootstrap.SchemaPreparer", new=_InForcePreparer),
        patch("vibey.bootstrap.database_url", return_value="postgresql://x"),
    ):
        migrator_cls.from_environ.return_value = MagicMock(apply=AsyncMock())
        async with build_app(config=cfg) as resources:
            project_config = {
                "notifications": {
                    "enabled": True,
                    "desktop": False,
                    "messaging": True,
                }
            }
            res = await resources.notifications.notify(
                project_id=uuid4(),
                kind="run_completed",
                title="Run Completed",
                message="done",
                config=project_config,
            )
            assert res == {"enabled": False, "desktop": False, "webhooks": []}
            assert resources.messaging.sent == []


@pytest.mark.asyncio
async def test_the_room_is_declared_by_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VIBEY_MESSAGING_ROOM_ID", "!env:matrix.test")
    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=_mock_pool())),
        patch("vibey.bootstrap.PostgresMigrator") as migrator_cls,
        patch("vibey.bootstrap.SchemaPreparer", new=_InForcePreparer),
        patch("vibey.bootstrap.database_url", return_value="postgresql://x"),
    ):
        migrator_cls.from_environ.return_value = MagicMock(apply=AsyncMock())
        async with build_app() as resources:
            project_config = {
                "notifications": {
                    "enabled": True,
                    "desktop": False,
                    "messaging": True,
                }
            }
            res = await resources.notifications.notify(
                project_id=uuid4(),
                kind="run_completed",
                title="Run Completed",
                message="done",
                config=project_config,
            )
            assert res == {
                "desktop": False,
                "webhooks": [],
                "messaging": True,
            }
            assert len(resources.messaging.sent) == 1
            assert resources.messaging.sent[0]["channel_id"] == "!env:matrix.test"
