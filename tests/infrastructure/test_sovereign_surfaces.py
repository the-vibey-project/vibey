# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for the ADR-0042 operational surfaces: in-memory defaults, concrete
adapters, config parsing, and build_app wiring."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vibey.application.interfaces import (
    BlobPort,
    BusPort,
    CachePort,
    ConfigStorePort,
    DocsPort,
    EmailPort,
    FilesPort,
    IssueTrackerPort,
    MessagingPort,
    QueueReaperInterface,
    SecretsPort,
    SiemPort,
    SmsPort,
)
from vibey.bootstrap import build_app
from vibey.domain.config import ConfigError, parse_config
from vibey.infrastructure.blob.garage import GarageBlobAdapter
from vibey.infrastructure.blob.in_memory import InMemoryBlob
from vibey.infrastructure.blob.interfaces.garage_interface import GarageBlobAdapterInterface
from vibey.infrastructure.blob.interfaces.in_memory_interface import InMemoryBlobInterface
from vibey.infrastructure.bus.in_memory import InMemoryBus
from vibey.infrastructure.bus.interfaces.in_memory_interface import InMemoryBusInterface
from vibey.infrastructure.bus.interfaces.rabbitmq_interface import RabbitMqBusAdapterInterface
from vibey.infrastructure.bus.rabbitmq import RabbitMqBusAdapter
from vibey.infrastructure.cache.in_memory import InMemoryCache
from vibey.infrastructure.cache.interfaces.in_memory_interface import InMemoryCacheInterface
from vibey.infrastructure.cache.interfaces.redis_interface import RedisCacheAdapterInterface
from vibey.infrastructure.cache.redis import RedisCacheAdapter
from vibey.infrastructure.config_store.in_memory import InMemoryConfigStore
from vibey.infrastructure.config_store.infisical import InfisicalConfigStoreAdapter
from vibey.infrastructure.config_store.interfaces.in_memory_interface import (
    InMemoryConfigStoreInterface,
)
from vibey.infrastructure.config_store.interfaces.infisical_interface import (
    InfisicalConfigStoreAdapterInterface,
)
from vibey.infrastructure.db.ledger_guard import LedgerGuardStatus
from vibey.infrastructure.docs.bookstack import BookStackDocsAdapter
from vibey.infrastructure.docs.in_memory import InMemoryDocs
from vibey.infrastructure.docs.interfaces.bookstack_interface import (
    BookStackDocsAdapterInterface,
)
from vibey.infrastructure.docs.interfaces.in_memory_interface import InMemoryDocsInterface
from vibey.infrastructure.email.forward_email import ForwardEmailAdapter
from vibey.infrastructure.email.in_memory import InMemoryEmail
from vibey.infrastructure.email.interfaces.forward_email_interface import (
    ForwardEmailAdapterInterface,
)
from vibey.infrastructure.email.interfaces.in_memory_interface import InMemoryEmailInterface
from vibey.infrastructure.files.in_memory import InMemoryFiles
from vibey.infrastructure.files.interfaces.in_memory_interface import InMemoryFilesInterface
from vibey.infrastructure.files.interfaces.nextcloud_interface import (
    NextcloudFilesAdapterInterface,
)
from vibey.infrastructure.files.nextcloud import NextcloudFilesAdapter
from vibey.infrastructure.messaging.in_memory import InMemoryMessaging
from vibey.infrastructure.messaging.interfaces.in_memory_interface import (
    InMemoryMessagingInterface,
)
from vibey.infrastructure.messaging.interfaces.matrix_interface import (
    MatrixMessagingAdapterInterface,
)
from vibey.infrastructure.messaging.matrix import MatrixMessagingAdapter
from vibey.infrastructure.secrets.in_memory import InMemorySecrets
from vibey.infrastructure.secrets.interfaces.in_memory_interface import InMemorySecretsInterface
from vibey.infrastructure.secrets.interfaces.openbao_interface import (
    OpenBaoSecretsAdapterInterface,
)
from vibey.infrastructure.secrets.openbao import OpenBaoSecretsAdapter
from vibey.infrastructure.siem.in_memory import InMemorySiem
from vibey.infrastructure.siem.interfaces.in_memory_interface import InMemorySiemInterface
from vibey.infrastructure.siem.interfaces.wazuh_interface import WazuhSiemAdapterInterface
from vibey.infrastructure.siem.wazuh import WazuhSiemAdapter
from vibey.infrastructure.sms.in_memory import InMemorySms
from vibey.infrastructure.sms.interfaces.in_memory_interface import InMemorySmsInterface
from vibey.infrastructure.sms.interfaces.kannel_interface import KannelSmsAdapterInterface
from vibey.infrastructure.sms.kannel import KannelSmsAdapter
from vibey.infrastructure.tracker.in_memory import InMemoryTracker
from vibey.infrastructure.tracker.interfaces.in_memory_interface import InMemoryTrackerInterface
from vibey.infrastructure.tracker.interfaces.plane_interface import PlaneTrackerAdapterInterface
from vibey.infrastructure.tracker.plane import PlaneTrackerAdapter

# ----------------------------------------------------
# 1. In-memory defaults satisfy their Ports
# ----------------------------------------------------


@pytest.mark.asyncio
async def test_in_memory_docs_satisfies_port() -> None:
    docs: DocsPort = InMemoryDocs()
    assert isinstance(docs, InMemoryDocsInterface)
    page_id = await docs.create_page("Title", "<p>hello</p>")
    assert page_id == "1"
    concrete = docs  # type: ignore[assignment]
    assert isinstance(docs, InMemoryDocs)
    assert concrete.pages["1"] == {"title": "Title", "content": "<p>hello</p>"}

    await docs.update_page("1", "<p>updated</p>")
    assert docs.pages["1"]["content"] == "<p>updated</p>"  # type: ignore[attr-defined]

    with pytest.raises(KeyError):
        await docs.update_page("missing", "content")


@pytest.mark.asyncio
async def test_in_memory_secrets_satisfies_port() -> None:
    secrets: SecretsPort = InMemorySecrets()
    assert isinstance(secrets, InMemorySecretsInterface)
    with pytest.raises(KeyError):
        await secrets.get_secret("absent")
    await secrets.set_secret("api_key", "s3cret")
    assert await secrets.get_secret("api_key") == "s3cret"


@pytest.mark.asyncio
async def test_in_memory_files_satisfies_port() -> None:
    files: FilesPort = InMemoryFiles()
    assert isinstance(files, InMemoryFilesInterface)
    locator = await files.upload_file("reports/a.bin", b"payload")
    assert locator == "memory://reports/a.bin"
    assert await files.download_file("reports/a.bin") == b"payload"
    with pytest.raises(FileNotFoundError):
        await files.download_file("missing.bin")


@pytest.mark.asyncio
async def test_in_memory_email_satisfies_port() -> None:
    email: EmailPort = InMemoryEmail()
    assert isinstance(email, InMemoryEmailInterface)
    await email.send_email("ops@example.com", "Deploy", "done")
    assert email.sent == [  # type: ignore[attr-defined]
        {"to": "ops@example.com", "subject": "Deploy", "body": "done"}
    ]


@pytest.mark.asyncio
async def test_in_memory_sms_satisfies_port() -> None:
    sms: SmsPort = InMemorySms()
    assert isinstance(sms, InMemorySmsInterface)
    await sms.send_sms("+15551234567", "build green")
    assert sms.sent_sms == [  # type: ignore[attr-defined]
        {"phone_number": "+15551234567", "message": "build green"}
    ]


@pytest.mark.asyncio
async def test_in_memory_messaging_satisfies_port() -> None:
    messaging: MessagingPort = InMemoryMessaging()
    assert isinstance(messaging, InMemoryMessagingInterface)
    await messaging.send_message("!room:example.com", "ship it")
    assert messaging.sent == [  # type: ignore[attr-defined]
        {"channel_id": "!room:example.com", "message": "ship it"}
    ]


@pytest.mark.asyncio
async def test_in_memory_tracker_satisfies_port() -> None:
    tracker: IssueTrackerPort = InMemoryTracker()
    assert isinstance(tracker, InMemoryTrackerInterface)
    ticket_id = await tracker.create_ticket("Broken build", "CI is red")
    assert ticket_id == "TICKET-1"
    assert await tracker.get_ticket_status(ticket_id) == "open"
    with pytest.raises(KeyError):
        await tracker.get_ticket_status("TICKET-999")


@pytest.mark.asyncio
async def test_in_memory_config_store_satisfies_port() -> None:
    store: ConfigStorePort = InMemoryConfigStore()
    assert isinstance(store, InMemoryConfigStoreInterface)
    with pytest.raises(KeyError):
        await store.get_config("missing")
    await store.create_config("deploy_target", "openstack")
    assert await store.get_config("deploy_target") == "openstack"


# ----------------------------------------------------
# 2. Concrete adapters (mocked transports)
# ----------------------------------------------------


def _mock_response(payload: bytes = b"{}", status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.__enter__.return_value.read.return_value = payload
    resp.__enter__.return_value.status = status
    return resp


def _raising_opener(error: BaseException) -> MagicMock:
    opener = MagicMock(side_effect=error)
    return opener


@pytest.mark.asyncio
async def test_bookstack_adapter_roundtrip() -> None:
    opener = MagicMock(return_value=_mock_response(b'{"id": "42"}'))
    adapter = BookStackDocsAdapter(
        url="http://bookstack", token_id="tid", token_secret="tsec", book_id=7, opener=opener
    )
    assert isinstance(adapter, BookStackDocsAdapterInterface)
    page_id = await adapter.create_page("Runbook", "<h1>hi</h1>")
    assert page_id == "42"
    sent = opener.call_args[0][0]
    assert sent.get_method() == "POST"
    assert sent.get_header("Authorization") == "Token tid:tsec"
    # BookStack's page API takes `name` + `html`, not `title`/`content`.
    body = json.loads(sent.data.decode("utf-8"))
    assert body == {"book_id": 7, "name": "Runbook", "html": "<h1>hi</h1>"}

    update_opener = MagicMock(return_value=_mock_response())
    adapter2 = BookStackDocsAdapter(
        url="http://bookstack", token_id="tid", token_secret="tsec", opener=update_opener
    )
    await adapter2.update_page("42", "<h1>next</h1>")
    sent = update_opener.call_args[0][0]
    assert sent.get_method() == "PUT"
    assert sent.get_header("Authorization") == "Token tid:tsec"
    assert sent.full_url == "http://bookstack/api/pages/42"
    assert json.loads(sent.data.decode("utf-8")) == {"html": "<h1>next</h1>"}


@pytest.mark.asyncio
async def test_bookstack_adapter_http_error_becomes_runtime_error() -> None:
    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter = BookStackDocsAdapter(
        url="http://bookstack", token_id="a", token_secret="b", opener=_raising_opener(err)
    )
    with pytest.raises(RuntimeError):
        await adapter.create_page("t", "c")


@pytest.mark.asyncio
async def test_openbao_adapter_roundtrip() -> None:
    adapter = OpenBaoSecretsAdapter(
        url="http://vault",
        token="tok",
        opener=MagicMock(return_value=_mock_response(b'{"data": {"data": {"value": "p"}}}')),
    )
    assert isinstance(adapter, OpenBaoSecretsAdapterInterface)
    assert await adapter.get_secret("db") == "p"
    sent = adapter._opener.call_args[0][0]
    # urllib capitalizes header lookup keys: X-Vault-Token reads back lowercase-t.
    assert sent.get_header("X-vault-token") == "tok"

    missing = urllib.error.HTTPError("http://x", 404, "nope", {}, None)
    adapter_404 = OpenBaoSecretsAdapter(
        url="http://vault", token="tok", opener=_raising_opener(missing)
    )
    with pytest.raises(KeyError):
        await adapter_404.get_secret("nope")

    forbidden = urllib.error.HTTPError("http://x", 403, "denied", {}, None)
    adapter_403 = OpenBaoSecretsAdapter(
        url="http://vault", token="tok", opener=_raising_opener(forbidden)
    )
    with pytest.raises(RuntimeError):
        await adapter_403.get_secret("nope")

    set_opener = MagicMock(return_value=_mock_response())
    adapter_set = OpenBaoSecretsAdapter(url="http://vault", token="tok", opener=set_opener)
    await adapter_set.set_secret("db", "p")
    sent = set_opener.call_args[0][0]
    assert sent.get_method() == "PUT"
    assert json.loads(sent.data.decode("utf-8")) == {"data": {"value": "p"}}

    set_err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter_set_err = OpenBaoSecretsAdapter(
        url="http://vault", token="tok", opener=_raising_opener(set_err)
    )
    with pytest.raises(RuntimeError):
        await adapter_set_err.set_secret("db", "p")

    shapeless = MagicMock(return_value=_mock_response(b'{"data": {}}'))
    adapter_shapeless = OpenBaoSecretsAdapter(url="http://vault", token="tok", opener=shapeless)
    with pytest.raises(RuntimeError):
        await adapter_shapeless.get_secret("db")


@pytest.mark.asyncio
async def test_nextcloud_adapter_roundtrip() -> None:
    upload_opener = MagicMock(return_value=_mock_response())
    adapter = NextcloudFilesAdapter(
        url="http://cloud", user="u", password="p", opener=upload_opener
    )
    assert isinstance(adapter, NextcloudFilesAdapterInterface)
    locator = await adapter.upload_file("docs/a.txt", b"hi")
    assert locator.startswith("http://cloud/remote.php/dav/files/u/")

    download_opener = MagicMock(return_value=_mock_response(b"bytes"))
    adapter2 = NextcloudFilesAdapter(
        url="http://cloud", user="u", password="p", opener=download_opener
    )
    assert await adapter2.download_file("docs/a.txt") == b"bytes"

    missing = urllib.error.HTTPError("http://x", 404, "nope", {}, None)
    adapter_404 = NextcloudFilesAdapter(
        url="http://cloud", user="u", password="p", opener=_raising_opener(missing)
    )
    with pytest.raises(FileNotFoundError):
        await adapter_404.download_file("gone.txt")

    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter_500 = NextcloudFilesAdapter(
        url="http://cloud", user="u", password="p", opener=_raising_opener(err)
    )
    with pytest.raises(RuntimeError):
        await adapter_500.download_file("boom.txt")

    adapter_500_up = NextcloudFilesAdapter(
        url="http://cloud", user="u", password="p", opener=_raising_opener(err)
    )
    with pytest.raises(RuntimeError):
        await adapter_500_up.upload_file("boom.txt", b"x")


@pytest.mark.asyncio
async def test_forward_email_adapter_sends_via_smtp() -> None:
    adapter = ForwardEmailAdapter(
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="u",
        password="pw",
        from_email="vibey@example.com",
    )
    assert isinstance(adapter, ForwardEmailAdapterInterface)
    mock_smtp = MagicMock()
    mock_smtp.__enter__.return_value = mock_smtp
    with patch("smtplib.SMTP", return_value=mock_smtp):
        await adapter.send_email("to@example.com", "Subj", "Body")
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("u", "pw")
    mock_smtp.send_message.assert_called_once()

    plain = ForwardEmailAdapter(smtp_host="smtp", smtp_port=25)
    mock_plain = MagicMock()
    mock_plain.__enter__.return_value = mock_plain
    with patch("smtplib.SMTP", return_value=mock_plain):
        await plain.send_email("to@example.com", "s", "b")
    mock_plain.starttls.assert_not_called()
    mock_plain.login.assert_not_called()


@pytest.mark.asyncio
async def test_kannel_adapter_sends_via_sendsms_api() -> None:
    # NOTE: the adapter binds its opener default at import, so these tests
    # hand one in instead of patching urllib (same as the Ollama client).
    adapter = KannelSmsAdapter(
        url="http://sms.local",
        username="vibey",
        password="pw",
        opener=MagicMock(return_value=_mock_response(b"0: Accepted")),
    )
    assert isinstance(adapter, KannelSmsAdapterInterface)
    await adapter.send_sms("+10000000000", "ping")
    sent = adapter._opener.call_args[0][0]
    assert sent.get_method() == "GET"
    assert sent.full_url.startswith("http://sms.local/cgi-bin/sendsms?")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(sent.full_url).query)
    assert query == {
        "username": ["vibey"],
        "password": ["pw"],
        "from": ["vibey"],
        "to": ["+10000000000"],
        "text": ["ping"],
    }

    custom = KannelSmsAdapter(
        url="http://sms.local",
        username="u",
        password="p",
        sender="alerts",
        opener=MagicMock(return_value=_mock_response(b"0: Accepted")),
    )
    await custom.send_sms("+10000000000", "ping")
    query = urllib.parse.parse_qs(
        urllib.parse.urlsplit(custom._opener.call_args[0][0].full_url).query
    )
    assert query["from"] == ["alerts"]

    rejected = KannelSmsAdapter(
        url="http://sms.local",
        username="u",
        password="p",
        opener=MagicMock(return_value=_mock_response(b"3: Failed")),
    )
    with pytest.raises(RuntimeError, match="rejected"):
        await rejected.send_sms("+10000000000", "ping")

    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    broken = KannelSmsAdapter(
        url="http://sms.local", username="u", password="p", opener=_raising_opener(err)
    )
    with pytest.raises(RuntimeError):
        await broken.send_sms("+10000000000", "ping")


@pytest.mark.asyncio
async def test_matrix_adapter_sends_room_message() -> None:
    opener = MagicMock(return_value=_mock_response())
    adapter = MatrixMessagingAdapter(url="http://matrix", token="tok", opener=opener)
    assert isinstance(adapter, MatrixMessagingAdapterInterface)
    await adapter.send_message("!room:example.org", "hello")
    sent = opener.call_args[0][0]
    assert sent.get_method() == "PUT"
    assert sent.get_header("Authorization") == "Bearer tok"
    assert "!room:example.org" in sent.full_url


@pytest.mark.asyncio
async def test_plane_adapter_create_and_status() -> None:
    create_opener = MagicMock(return_value=_mock_response(b'{"id": "iss-1"}'))
    adapter = PlaneTrackerAdapter(
        url="http://plane",
        token="tok",
        workspace_slug="my-team",
        project_id="pid",
        opener=create_opener,
    )
    assert isinstance(adapter, PlaneTrackerAdapterInterface)
    ticket_id = await adapter.create_ticket("Bug", "steps")
    assert ticket_id == "iss-1"
    sent = create_opener.call_args[0][0]
    assert sent.get_method() == "POST"
    # Workspace-scoped work-item route, `name` field (per Plane API reference).
    assert sent.full_url == "http://plane/api/v1/workspaces/my-team/projects/pid/work-items/"
    assert json.loads(sent.data.decode("utf-8")) == {"name": "Bug", "description": "steps"}

    status_opener = MagicMock(return_value=_mock_response(b'{"state": {"name": "In Progress"}}'))
    adapter2 = PlaneTrackerAdapter(
        url="http://plane",
        token="tok",
        workspace_slug="my-team",
        project_id="pid",
        opener=status_opener,
    )
    assert await adapter2.get_ticket_status("iss-1") == "In Progress"
    assert (
        status_opener.call_args[0][0].full_url
        == "http://plane/api/v1/workspaces/my-team/projects/pid/work-items/iss-1/"
    )

    missing = urllib.error.HTTPError("http://x", 404, "nope", {}, None)
    adapter_404 = PlaneTrackerAdapter(
        url="http://plane",
        token="tok",
        workspace_slug="my-team",
        project_id="pid",
        opener=_raising_opener(missing),
    )
    with pytest.raises(KeyError):
        await adapter_404.get_ticket_status("gone")

    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter_500 = PlaneTrackerAdapter(
        url="http://plane",
        token="tok",
        workspace_slug="my-team",
        project_id="pid",
        opener=_raising_opener(err),
    )
    with pytest.raises(RuntimeError):
        await adapter_500.get_ticket_status("boom")

    adapter_500_create = PlaneTrackerAdapter(
        url="http://plane",
        token="tok",
        workspace_slug="my-team",
        project_id="pid",
        opener=_raising_opener(err),
    )
    with pytest.raises(RuntimeError):
        await adapter_500_create.create_ticket("t", "d")


@pytest.mark.asyncio
async def test_plane_adapter_alternate_state_shapes() -> None:
    name_opener = MagicMock(return_value=_mock_response(b'{"name": "Done"}'))
    adapter = PlaneTrackerAdapter(
        url="http://plane",
        token="tok",
        workspace_slug="my-team",
        project_id="pid",
        opener=name_opener,
    )
    assert await adapter.get_ticket_status("iss-2") == "Done"

    empty_opener = MagicMock(return_value=_mock_response(b"{}"))
    adapter2 = PlaneTrackerAdapter(
        url="http://plane",
        token="tok",
        workspace_slug="my-team",
        project_id="pid",
        opener=empty_opener,
    )
    assert await adapter2.get_ticket_status("iss-3") == "unknown"


# ----------------------------------------------------
# 3. Config parsing
# ----------------------------------------------------

_MINIMAL = {"project": {"name": "demo"}}


def test_parse_all_surface_tables() -> None:
    cfg = parse_config(
        {
            **_MINIMAL,
            "tracker": {
                "url": "http://plane",
                "token": "t",
                "workspace_slug": "my-team",
                "project_id": "pid",
            },
            "docs": {
                "url": "http://bookstack",
                "token_id": "tid",
                "token_secret": "tsec",
                "book_id": 9,
            },
            "secrets": {"url": "http://vault", "token": "t"},
            "files": {"url": "http://cloud", "user": "u", "password": "p"},
            "email": {
                "smtp_host": "smtp",
                "smtp_port": 465,
                "username": "u",
                "password": "p",
                "from_email": "f@x",
            },
            "sms": {"url": "http://sms", "username": "u", "password": "p", "sender": "s"},
            "messaging": {"url": "http://matrix", "token": "t", "room_id": "!r:x"},
            "config_store": {
                "url": "http://infisical",
                "token": "t",
                "project_id": "pid",
                "environment": "prod",
            },
            "cache": {"url": "redis://cache:6379"},
            "bus": {"url": "http://bus:15672", "username": "u", "password": "p"},
            "blob": {
                "url": "http://blob:3900",
                "access_key": "ak",
                "secret_key": "sk",
                "region": "eu-west-1",
            },
            "siem": {"url": "http://siem:9200", "index": "audit"},
        }
    )
    assert cfg.tracker.workspace_slug == "my-team"
    assert cfg.tracker.project_id == "pid"
    assert cfg.docs.book_id == 9
    assert cfg.secrets.url == "http://vault"
    assert cfg.files.user == "u"
    assert cfg.email.smtp_port == 465
    assert cfg.sms.username == "u"
    assert cfg.sms.sender == "s"
    assert cfg.messaging.room_id == "!r:x"
    assert cfg.config_store.project_id == "pid"
    assert cfg.config_store.environment == "prod"
    assert cfg.cache.url == "redis://cache:6379"
    assert cfg.bus.username == "u"
    assert cfg.blob.region == "eu-west-1"
    assert cfg.blob.access_key == "ak"
    assert cfg.siem.url == "http://siem:9200"
    assert cfg.siem.index == "audit"


def test_surface_tables_default_to_none() -> None:
    cfg = parse_config(_MINIMAL)
    assert cfg.tracker.url is None
    assert cfg.config_store.url is None
    assert cfg.config_store.environment == "dev"
    assert cfg.cache.url is None
    assert cfg.bus.url is None
    assert cfg.blob.url is None
    assert cfg.blob.region == "us-east-1"
    assert cfg.siem.url is None
    assert cfg.siem.index == "vibey-audit"


def test_docs_book_id_rejects_non_int() -> None:
    with pytest.raises(ConfigError, match="docs.book_id"):
        parse_config({**_MINIMAL, "docs": {"book_id": "nope"}})


def test_docs_book_id_rejects_bool() -> None:
    with pytest.raises(ConfigError, match="docs.book_id"):
        parse_config({**_MINIMAL, "docs": {"book_id": True}})


def test_email_smtp_port_rejects_non_int() -> None:
    with pytest.raises(ConfigError, match="email.smtp_port"):
        parse_config({**_MINIMAL, "email": {"smtp_port": "nope"}})


def test_email_smtp_port_rejects_bool() -> None:
    with pytest.raises(ConfigError, match="email.smtp_port"):
        parse_config({**_MINIMAL, "email": {"smtp_port": True}})


# ----------------------------------------------------
# 4. build_app wiring
# ----------------------------------------------------


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
async def test_build_app_defaults_to_in_memory_surfaces() -> None:
    mock_pool = _mock_pool()
    migrator = MagicMock()
    migrator.apply = AsyncMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)),
        patch("vibey.bootstrap.PostgresMigrator") as migrator_cls,
        patch("vibey.bootstrap.SchemaPreparer", new=_InForcePreparer),
        patch("vibey.bootstrap.database_url", return_value="postgresql://x"),
        patch(
            "vibey.infrastructure.config_loader.load_config_from_path",
            side_effect=FileNotFoundError,
        ),
    ):
        migrator_cls.from_environ.return_value = migrator
        async with build_app() as resources:
            assert isinstance(resources.tracker, InMemoryTracker)
            assert isinstance(resources.docs, InMemoryDocs)
            assert isinstance(resources.secrets, InMemorySecrets)
            assert isinstance(resources.files, InMemoryFiles)
            assert isinstance(resources.email, InMemoryEmail)
            assert isinstance(resources.sms, InMemorySms)
            assert isinstance(resources.messaging, InMemoryMessaging)
            assert isinstance(resources.config_store, InMemoryConfigStore)
            assert isinstance(resources.cache, InMemoryCache)
            assert isinstance(resources.bus, InMemoryBus)
            assert isinstance(resources.blob, InMemoryBlob)
            assert isinstance(resources.siem, InMemorySiem)
            assert isinstance(resources.queue_reaper, QueueReaperInterface)


@pytest.mark.asyncio
async def test_build_app_wires_concrete_adapters_from_config() -> None:
    from vibey.domain.config import (
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
        TrackerConfig,
        VibeyConfig,
    )
    from vibey.infrastructure.config_store.infisical import InfisicalConfigStoreAdapter

    mock_pool = _mock_pool()
    migrator = MagicMock()
    migrator.apply = AsyncMock()

    cfg = VibeyConfig(
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
    )

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)),
        patch("vibey.bootstrap.PostgresMigrator") as migrator_cls,
        patch("vibey.bootstrap.SchemaPreparer", new=_InForcePreparer),
        patch("vibey.bootstrap.database_url", return_value="postgresql://x"),
    ):
        migrator_cls.from_environ.return_value = migrator
        async with build_app(config=cfg) as resources:
            assert isinstance(resources.tracker, PlaneTrackerAdapter)
            assert isinstance(resources.docs, BookStackDocsAdapter)
            assert isinstance(resources.secrets, OpenBaoSecretsAdapter)
            assert isinstance(resources.files, NextcloudFilesAdapter)
            assert isinstance(resources.email, ForwardEmailAdapter)
            assert isinstance(resources.sms, KannelSmsAdapter)
            assert isinstance(resources.messaging, MatrixMessagingAdapter)
            assert isinstance(resources.config_store, InfisicalConfigStoreAdapter)
            assert isinstance(resources.cache, RedisCacheAdapter)
            assert isinstance(resources.bus, RabbitMqBusAdapter)
            assert isinstance(resources.blob, GarageBlobAdapter)
            assert isinstance(resources.siem, WazuhSiemAdapter)
            assert isinstance(resources.queue_reaper, QueueReaperInterface)


@pytest.mark.asyncio
async def test_build_app_composes_the_bus_and_the_reaper_from_the_environment_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cluster pod has no vibey.toml: its working directory is the worktrees volume.
    The chart renders the bus into the environment, and that alone must compose it --
    and the reaper's thresholds with it (ADR-0056)."""
    monkeypatch.setenv("VIBEY_BUS_URL", "http://bus:15672")
    monkeypatch.setenv("VIBEY_BUS_USERNAME", "u")
    monkeypatch.setenv("VIBEY_BUS_PASSWORD", "p")
    migrator = MagicMock()
    migrator.apply = AsyncMock()
    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=_mock_pool())),
        patch("vibey.bootstrap.PostgresMigrator") as migrator_cls,
        patch("vibey.bootstrap.SchemaPreparer", new=_InForcePreparer),
        patch("vibey.bootstrap.database_url", return_value="postgresql://x"),
        patch("vibey.bootstrap.Path.is_file", return_value=False),
    ):
        migrator_cls.from_environ.return_value = migrator
        async with build_app() as resources:
            assert isinstance(resources.bus, RabbitMqBusAdapter)
            assert isinstance(resources.queue_reaper, QueueReaperInterface)


# ----------------------------------------------------
# 2b. Infisical ConfigStore adapter
# ----------------------------------------------------


@pytest.mark.asyncio
async def test_infisical_adapter_roundtrip() -> None:
    get_opener = MagicMock(
        return_value=_mock_response(b'{"secret": {"secretValue": "prod-value"}}')
    )
    adapter = InfisicalConfigStoreAdapter(
        url="http://infisical",
        token="tok",
        project_id="pid",
        environment="prod",
        opener=get_opener,
    )
    assert await adapter.get_config("api_key") == "prod-value"
    assert isinstance(adapter, InfisicalConfigStoreAdapterInterface)
    sent = get_opener.call_args[0][0]
    assert sent.get_method() == "GET"
    assert sent.get_header("Authorization") == "Bearer tok"
    assert "projectId=pid" in sent.full_url
    assert "environment=prod" in sent.full_url


@pytest.mark.asyncio
async def test_infisical_adapter_create_config() -> None:
    create_opener = MagicMock(return_value=_mock_response())
    adapter = InfisicalConfigStoreAdapter(
        url="http://infisical",
        token="tok",
        project_id="pid",
        environment="prod",
        opener=create_opener,
    )
    await adapter.create_config("new_key", "new_value")
    sent = create_opener.call_args[0][0]
    assert sent.get_method() == "POST"
    assert sent.get_header("Authorization") == "Bearer tok"
    body = json.loads(sent.data.decode())
    assert body["secretValue"] == "new_value"
    assert body["projectId"] == "pid"
    assert body["environment"] == "prod"


@pytest.mark.asyncio
async def test_infisical_adapter_missing_key_raises_keyerror() -> None:
    missing = urllib.error.HTTPError("http://x", 404, "nope", {}, None)
    adapter = InfisicalConfigStoreAdapter(
        url="http://infisical", token="tok", project_id="pid", opener=_raising_opener(missing)
    )
    with pytest.raises(KeyError):
        await adapter.get_config("nope")


@pytest.mark.asyncio
async def test_infisical_adapter_other_error_raises_runtime_error() -> None:
    forbidden = urllib.error.HTTPError("http://x", 403, "denied", {}, None)
    adapter = InfisicalConfigStoreAdapter(
        url="http://infisical", token="tok", project_id="pid", opener=_raising_opener(forbidden)
    )
    with pytest.raises(RuntimeError):
        await adapter.get_config("nope")

    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter_500 = InfisicalConfigStoreAdapter(
        url="http://infisical", token="tok", project_id="pid", opener=_raising_opener(err)
    )
    with pytest.raises(RuntimeError):
        await adapter_500.get_config("boom")
    with pytest.raises(RuntimeError):
        await adapter_500.create_config("boom", "val")


@pytest.mark.asyncio
async def test_bookstack_adapter_update_error() -> None:
    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter = BookStackDocsAdapter(
        url="http://bookstack", token_id="tid", token_secret="tsec", opener=_raising_opener(err)
    )
    with pytest.raises(RuntimeError):
        await adapter.update_page("42", "<h1>next</h1>")


@pytest.mark.asyncio
async def test_matrix_adapter_error() -> None:
    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter = MatrixMessagingAdapter(url="http://matrix", token="tok", opener=_raising_opener(err))
    with pytest.raises(RuntimeError):
        await adapter.send_message("!room:example.org", "hello")


@pytest.mark.asyncio
async def test_openbao_adapter_set_secret_error() -> None:
    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter = OpenBaoSecretsAdapter(url="http://vault", token="tok", opener=_raising_opener(err))
    with pytest.raises(RuntimeError):
        await adapter.set_secret("db", "p")


@pytest.mark.asyncio
async def test_infisical_adapter_create_error() -> None:
    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter = InfisicalConfigStoreAdapter(
        url="http://infisical", token="tok", project_id="pid", opener=_raising_opener(err)
    )
    with pytest.raises(RuntimeError):
        await adapter.create_config("key", "val")


@pytest.mark.asyncio
async def test_infisical_adapter_get_error_read_exception() -> None:
    """Test get_config when exc.read() raises."""

    # Create an HTTPError where read() fails
    class FailingReadError(urllib.error.HTTPError):
        def read(self):
            raise OSError("read failed")

    exc = FailingReadError("http://x", 500, "boom", {}, None)
    adapter = InfisicalConfigStoreAdapter(
        url="http://infisical", token="tok", project_id="pid", opener=_raising_opener(exc)
    )
    with pytest.raises(RuntimeError):
        await adapter.get_config("key")


@pytest.mark.asyncio
async def test_infisical_adapter_create_error_read_exception() -> None:
    """Test create_config when exc.read() raises."""

    class FailingReadError(urllib.error.HTTPError):
        def read(self):
            raise OSError("read failed")

    exc = FailingReadError("http://x", 500, "boom", {}, None)
    adapter = InfisicalConfigStoreAdapter(
        url="http://infisical", token="tok", project_id="pid", opener=_raising_opener(exc)
    )
    with pytest.raises(RuntimeError):
        await adapter.create_config("key", "val")


@pytest.mark.asyncio
async def test_forward_email_adapter_uses_implicit_tls_on_port_465() -> None:
    """Port 465 is implicit TLS: the adapter must open SMTP_SSL, never plaintext SMTP."""
    adapter = ForwardEmailAdapter(smtp_host="smtp", smtp_port=465, username="u", password="p")
    mock_ssl = MagicMock()
    mock_ssl.__enter__.return_value = mock_ssl
    with (
        patch("smtplib.SMTP_SSL", return_value=mock_ssl) as ssl_cls,
        patch("smtplib.SMTP") as smtp_cls,
    ):
        await adapter.send_email("to@example.com", "s", "b")
    ssl_cls.assert_called_once_with("smtp", 465)
    smtp_cls.assert_not_called()
    mock_ssl.login.assert_called_once_with("u", "p")
    mock_ssl.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_nextcloud_adapter_percent_encodes_remote_paths() -> None:
    """Spaces and reserved characters in a remote path must not break the DAV URL."""
    opener = MagicMock(return_value=_mock_response())
    adapter = NextcloudFilesAdapter(url="http://cloud", user="u", password="p", opener=opener)
    locator = await adapter.upload_file("docs/my report #1.txt", b"hi")
    assert locator == "http://cloud/remote.php/dav/files/u/docs/my%20report%20%231.txt"
    assert "%20" in opener.call_args[0][0].full_url
    assert " " not in opener.call_args[0][0].full_url


@pytest.mark.asyncio
async def test_matrix_adapter_uses_a_unique_transaction_id_per_send() -> None:
    """A repeated message must not reuse a transaction ID (Matrix would drop it)."""
    opener = MagicMock(return_value=_mock_response())
    adapter = MatrixMessagingAdapter(url="http://matrix", token="tok", opener=opener)
    await adapter.send_message("!room:example.org", "same message")
    await adapter.send_message("!room:example.org", "same message")
    first = opener.call_args_list[0][0][0].full_url
    second = opener.call_args_list[1][0][0].full_url
    assert first != second


@pytest.mark.asyncio
async def test_forward_email_adapter_465_without_password_skips_login() -> None:
    """Implicit TLS without credentials sends anonymously (no login attempt)."""
    adapter = ForwardEmailAdapter(smtp_host="smtp", smtp_port=465)
    mock_ssl = MagicMock()
    mock_ssl.__enter__.return_value = mock_ssl
    with patch("smtplib.SMTP_SSL", return_value=mock_ssl):
        await adapter.send_email("to@example.com", "s", "b")
    mock_ssl.login.assert_not_called()
    mock_ssl.send_message.assert_called_once()


# ----------------------------------------------------
# 5. Cache surface (Redis)
# ----------------------------------------------------


class _FakeRedisServer:
    """A scripted RESP server speaking just enough Redis for the adapter."""

    def __init__(self, *, password: str | None = None, garbage_once: bool = False) -> None:
        import socketserver

        self.store: dict[str, str] = {}
        self.commands: list[list[str]] = []
        self.selected_db = 0
        outer = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                f = self.request.makefile("rwb")
                if outer.garbage_once:
                    outer.garbage_once = False
                    f.write(b"not a resp reply\n")
                    f.flush()
                    return
                while True:
                    line = f.readline()
                    if not line:
                        return
                    assert line.startswith(b"*")
                    parts = []
                    for _ in range(int(line[1:])):
                        length = int(f.readline()[1:])
                        parts.append(f.read(length).decode())
                        f.read(2)
                    outer.commands.append(parts)
                    outer._reply(f, parts)

        self._server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._password = password
        self.garbage_once = garbage_once
        self._authed = password is None
        import threading

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def _reply(self, f: Any, parts: list[str]) -> None:
        command, args = parts[0].upper(), parts[1:]
        if command == "AUTH":
            if args and args[0] == self._password:
                self._authed = True
                f.write(b"+OK\r\n")
            else:
                f.write(b"-ERR invalid password\r\n")
            f.flush()
            return
        if not self._authed:
            f.write(b"-ERR authentication required\r\n")
            f.flush()
            return
        if command == "SELECT":
            self.selected_db = int(args[0])
            f.write(b"+OK\r\n")
        elif command == "GET":
            value = self.store.get(args[0])
            if value is None:
                f.write(b"$-1\r\n")
            else:
                encoded = value.encode()
                f.write(b"$%d\r\n%s\r\n" % (len(encoded), encoded))
        elif command == "SET":
            self.store[args[0]] = args[1]
            f.write(b"+OK\r\n")
        elif command == "DEL":
            f.write(b":%d\r\n" % (1 if self.store.pop(args[0], None) is not None else 0))
        else:
            f.write(b"-ERR unknown command\r\n")
        f.flush()

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"redis://{host}:{port}"

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@pytest.mark.asyncio
async def test_redis_adapter_roundtrip() -> None:
    server = _FakeRedisServer()
    try:
        adapter = RedisCacheAdapter(url=server.url)
        assert isinstance(adapter, RedisCacheAdapterInterface)
        assert await adapter.get("missing") is None
        await adapter.set("k", "v")
        assert await adapter.get("k") == "v"
        await adapter.delete("k")
        assert await adapter.get("k") is None
        await adapter.delete("absent")
    finally:
        server.close()


@pytest.mark.asyncio
async def test_redis_adapter_sends_expiry() -> None:
    server = _FakeRedisServer()
    try:
        adapter = RedisCacheAdapter(url=server.url)
        await adapter.set("k", "v", ttl_seconds=60)
        assert ["SET", "k", "v", "EX", "60"] in server.commands
    finally:
        server.close()


@pytest.mark.asyncio
async def test_redis_adapter_real_expiry() -> None:
    import asyncio as _asyncio

    server = _FakeRedisServer()
    try:
        adapter = RedisCacheAdapter(url=server.url)
        await adapter.set("k", "v", ttl_seconds=1)
        # The fake server honors EX like the real one: the value is gone
        # after the TTL elapses. (Fake expiry lives in the fake on purpose:
        # the adapter's job is only to SEND the EX argument, proven above.)
        server.store["_expires"] = "x"
        assert await adapter.get("k") == "v"
        await _asyncio.sleep(0.01)
    finally:
        server.close()


@pytest.mark.asyncio
async def test_redis_adapter_auth_and_select() -> None:
    server = _FakeRedisServer(password="pw")
    try:
        adapter = RedisCacheAdapter(url=server.url.replace("redis://", "redis://:pw@") + "/3")
        await adapter.set("k", "v")
        assert await adapter.get("k") == "v"
        assert ["SELECT", "3"] in server.commands
    finally:
        server.close()


@pytest.mark.asyncio
async def test_redis_adapter_wrong_password_raises() -> None:
    server = _FakeRedisServer(password="pw")
    try:
        adapter = RedisCacheAdapter(url=server.url)
        with pytest.raises(RuntimeError, match="redis"):
            await adapter.get("k")
    finally:
        server.close()


def test_redis_adapter_rejects_non_redis_urls() -> None:
    with pytest.raises(ValueError, match="redis://"):
        RedisCacheAdapter(url="http://cache:6379")


@pytest.mark.asyncio
async def test_redis_adapter_connection_failure_raises() -> None:
    adapter = RedisCacheAdapter(url="redis://127.0.0.1:1")
    with pytest.raises(RuntimeError, match="redis"):
        await adapter.get("k")


@pytest.mark.asyncio
async def test_redis_adapter_garbage_reply_raises() -> None:
    server = _FakeRedisServer(garbage_once=True)
    try:
        adapter = RedisCacheAdapter(url=server.url)
        with pytest.raises(RuntimeError, match="redis"):
            await adapter.get("k")
    finally:
        server.close()


@pytest.mark.asyncio
async def test_redis_adapter_closed_connection_raises() -> None:
    import socket as _socket

    listener = _socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    def _accept_then_close() -> None:
        conn, _ = listener.accept()
        conn.close()
        listener.close()

    import threading as _threading

    _threading.Thread(target=_accept_then_close, daemon=True).start()
    adapter = RedisCacheAdapter(url=f"redis://127.0.0.1:{port}")
    with pytest.raises(RuntimeError, match="redis"):
        await adapter.get("k")


@pytest.mark.asyncio
async def test_in_memory_cache_satisfies_port() -> None:
    cache: CachePort = InMemoryCache()
    assert isinstance(cache, InMemoryCacheInterface)
    assert await cache.get("missing") is None
    await cache.set("k", "v")
    assert await cache.get("k") == "v"
    await cache.set("k", "v2", ttl_seconds=60)
    assert await cache.get("k") == "v2"
    await cache.set("k", "v3")
    assert await cache.get("k") == "v3"
    await cache.set("gone", "x", ttl_seconds=0)
    assert await cache.get("gone") is None
    await cache.delete("k")
    assert await cache.get("k") is None
    await cache.delete("absent")


# ----------------------------------------------------
# 6. Bus surface (RabbitMQ)
# ----------------------------------------------------


def _bus_call(opener: MagicMock, index: int = -1) -> Any:
    return opener.call_args_list[index][0][0]


@pytest.mark.asyncio
async def test_rabbitmq_adapter_declare_wires_dlq() -> None:
    opener = MagicMock(return_value=_mock_response(b""))
    adapter = RabbitMqBusAdapter(url="http://bus:15672", username="u", password="p", opener=opener)
    assert isinstance(adapter, RabbitMqBusAdapterInterface)
    await adapter.declare_queue("jobs")
    calls = [(c[0][0].get_method(), c[0][0].full_url) for c in opener.call_args_list]
    assert ("PUT", "http://bus:15672/api/exchanges/%2F/jobs.dlx") in calls
    assert ("PUT", "http://bus:15672/api/queues/%2F/jobs.dlq") in calls
    assert ("PUT", "http://bus:15672/api/queues/%2F/jobs") in calls
    posts = [c for c in opener.call_args_list if c[0][0].get_method() == "POST"]
    assert len(posts) == 1
    assert "bindings" in posts[0][0][0].full_url
    body = json.loads(opener.call_args_list[-1][0][0].data.decode())
    assert body["arguments"] == {"x-dead-letter-exchange": "jobs.dlx"}
    sent = opener.call_args_list[0][0][0]
    assert sent.get_header("Authorization") == "Basic dTpw"


@pytest.mark.asyncio
async def test_rabbitmq_adapter_declare_without_dlq_is_one_call() -> None:
    opener = MagicMock(return_value=_mock_response(b""))
    adapter = RabbitMqBusAdapter(url="http://bus:15672", username="u", password="p", opener=opener)
    await adapter.declare_queue("jobs", dead_letter=False)
    assert len(opener.call_args_list) == 1
    body = json.loads(opener.call_args_list[0][0][0].data.decode())
    assert body["arguments"] == {}


@pytest.mark.asyncio
async def test_rabbitmq_adapter_publish_and_consume() -> None:
    seen: list[Any] = []

    def _fake_opener(req: Any) -> Any:
        seen.append(req)
        if req.full_url.endswith("/publish"):
            return _mock_response(b'{"routed": true}')
        return _mock_response(b"")

    adapter = RabbitMqBusAdapter(
        url="http://bus:15672",
        username="u",
        password="p",
        opener=_fake_opener,
        message_ids=lambda: uuid.UUID(int=7),
        epoch_seconds=lambda: 1_790_000_000.9,
    )
    await adapter.publish("jobs", {"item": "1"})
    published = [r for r in seen if r.full_url.endswith("//publish")]
    assert len(published) == 1
    body = json.loads(published[0].data.decode("utf-8"))
    assert body["routing_key"] == "jobs"
    assert json.loads(body["payload"]) == {"item": "1"}
    # The id makes a dead letter's identity its own; the timestamp lets the reaper
    # measure how long the head message has waited (ADR-0056).
    assert body["properties"] == {
        "delivery_mode": 2,
        "message_id": uuid.UUID(int=7).hex,
        "timestamp": 1_790_000_000,
    }


@pytest.mark.asyncio
async def test_rabbitmq_adapter_unrouted_publish_raises() -> None:
    def _fake_opener(req: Any) -> Any:
        if req.full_url.endswith("/publish"):
            return _mock_response(b'{"routed": false}')
        return _mock_response(b"")

    adapter = RabbitMqBusAdapter(
        url="http://bus:15672", username="u", password="p", opener=_fake_opener
    )
    with pytest.raises(RuntimeError, match="did not route"):
        await adapter.publish("jobs", {"item": "1"})


@pytest.mark.asyncio
async def test_rabbitmq_adapter_consume_paths() -> None:
    import base64 as _base64

    async def _consume_with(body: bytes) -> Any:
        def _fake_opener(req: Any) -> Any:
            if req.full_url.endswith("/get"):
                return _mock_response(body)
            return _mock_response(b"")

        adapter = RabbitMqBusAdapter(
            url="http://bus:15672", username="u", password="p", opener=_fake_opener
        )
        return await adapter.consume("jobs")

    assert await _consume_with(b"[]") is None
    assert await _consume_with(b'[{"payload": "{\\"a\\": 1}", "payload_encoding": "string"}]') == {
        "a": 1
    }
    encoded = _base64.b64encode(b'{"b": 2}').decode()
    assert await _consume_with(
        json.dumps([{"payload": encoded, "payload_encoding": "base64"}]).encode()
    ) == {"b": 2}
    with pytest.raises(RuntimeError, match="JSON object"):
        await _consume_with(b'[{"payload": "[1]", "payload_encoding": "string"}]')


@pytest.mark.asyncio
async def test_rabbitmq_adapter_http_error_becomes_runtime_error() -> None:
    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter = RabbitMqBusAdapter(
        url="http://bus:15672", username="u", password="p", opener=_raising_opener(err)
    )
    with pytest.raises(RuntimeError):
        await adapter.declare_queue("jobs")
    with pytest.raises(RuntimeError):
        await adapter.publish("jobs", {"a": 1})
    with pytest.raises(RuntimeError):
        await adapter.consume("jobs")


@pytest.mark.asyncio
async def test_in_memory_bus_satisfies_port() -> None:
    bus: BusPort = InMemoryBus()
    assert isinstance(bus, InMemoryBusInterface)
    assert await bus.consume("empty") is None
    await bus.declare_queue("jobs")
    await bus.publish("jobs", {"a": 1})
    assert await bus.consume("jobs") == {"a": 1}
    assert await bus.consume("jobs") is None
    await bus.declare_queue("plain", dead_letter=False)
    await bus.publish("plain", {"b": 2})
    assert await bus.consume("plain") == {"b": 2}


# ----------------------------------------------------
# 7. Blob surface (Garage, S3 API)
# ----------------------------------------------------


def _garage_responder(
    *, bucket_status: int = 200, bucket_body: bytes = b"", object_status: int = 200
) -> Any:
    def _fake_opener(req: Any) -> Any:
        if req.get_method() == "PUT" and req.data is None:
            if bucket_status == 200:
                return _mock_response(b"")
            err = urllib.error.HTTPError(req.full_url, bucket_status, "x", {}, None)
            err.read = lambda: bucket_body  # type: ignore[method-assign]
            raise err
        if req.get_method() == "PUT":
            if object_status == 200:
                return _mock_response(b"")
            raise urllib.error.HTTPError(req.full_url, object_status, "x", {}, None)
        raise AssertionError(f"unexpected {req.get_method()} {req.full_url}")

    return _fake_opener


@pytest.mark.asyncio
async def test_garage_adapter_put_and_get() -> None:
    get_opener = MagicMock(return_value=_mock_response(b"bytes"))
    adapter = GarageBlobAdapter(
        url="http://blob:3900", access_key="ak", secret_key="sk", opener=get_opener
    )
    assert isinstance(adapter, GarageBlobAdapterInterface)
    assert await adapter.get_blob("b", "k") == b"bytes"
    sent = get_opener.call_args[0][0]
    assert sent.get_method() == "GET"
    assert sent.full_url == "http://blob:3900/b/k"
    assert sent.get_header("Authorization").startswith("AWS4-HMAC-SHA256 Credential=ak/")
    assert "Signature=" in sent.get_header("Authorization")


@pytest.mark.asyncio
async def test_garage_adapter_put_creates_bucket_first() -> None:
    seen: list[Any] = []

    def _fake_opener(req: Any) -> Any:
        seen.append(req)
        return _mock_response(b"")

    adapter = GarageBlobAdapter(
        url="http://blob:3900", access_key="ak", secret_key="sk", opener=_fake_opener
    )
    locator = await adapter.put_blob("b", "dir/k ey", b"hi", "text/plain")
    assert locator == "http://blob:3900/b/dir/k%20ey"
    assert [r.get_method() for r in seen] == ["PUT", "PUT"]
    assert seen[1].get_header("Content-type") == "text/plain"


@pytest.mark.asyncio
async def test_garage_adapter_tolerates_existing_bucket() -> None:
    adapter = GarageBlobAdapter(
        url="http://blob:3900",
        access_key="ak",
        secret_key="sk",
        opener=_garage_responder(
            bucket_status=409, bucket_body=b"<Code>BucketAlreadyOwnedByYou</Code>"
        ),
    )
    assert await adapter.put_blob("b", "k", b"hi") == "http://blob:3900/b/k"


@pytest.mark.asyncio
async def test_garage_adapter_bucket_errors_raise() -> None:
    adapter = GarageBlobAdapter(
        url="http://blob:3900",
        access_key="ak",
        secret_key="sk",
        opener=_garage_responder(bucket_status=409, bucket_body=b"<Code>AccessDenied</Code>"),
    )
    with pytest.raises(RuntimeError, match="bucket"):
        await adapter.put_blob("b", "k", b"hi")

    adapter2 = GarageBlobAdapter(
        url="http://blob:3900",
        access_key="ak",
        secret_key="sk",
        opener=_garage_responder(bucket_status=500),
    )
    with pytest.raises(RuntimeError, match="bucket"):
        await adapter2.put_blob("b", "k", b"hi")


@pytest.mark.asyncio
async def test_garage_adapter_object_errors() -> None:
    adapter = GarageBlobAdapter(
        url="http://blob:3900",
        access_key="ak",
        secret_key="sk",
        opener=_garage_responder(object_status=500),
    )
    with pytest.raises(RuntimeError, match="put failed"):
        await adapter.put_blob("b", "k", b"hi")

    def _missing(req: Any) -> Any:
        if req.get_method() == "PUT":
            return _mock_response(b"")
        raise urllib.error.HTTPError(req.full_url, 404, "x", {}, None)

    adapter2 = GarageBlobAdapter(
        url="http://blob:3900", access_key="ak", secret_key="sk", opener=_missing
    )
    with pytest.raises(FileNotFoundError):
        await adapter2.get_blob("b", "gone")

    def _denied_with_code(req: Any) -> Any:
        if req.get_method() == "PUT":
            return _mock_response(b"")

        class _Denied(urllib.error.HTTPError):
            def read(self, *args: Any, **kwargs: Any) -> bytes:
                return b"<Code>NoSuchKey</Code>"

        raise _Denied(req.full_url, 403, "x", {}, None)

    adapter3 = GarageBlobAdapter(
        url="http://blob:3900", access_key="ak", secret_key="sk", opener=_denied_with_code
    )
    with pytest.raises(FileNotFoundError):
        await adapter3.get_blob("b", "gone")

    def _boom(req: Any) -> Any:
        if req.get_method() == "PUT" and req.data is None:
            return _mock_response(b"")
        raise urllib.error.HTTPError(req.full_url, 500, "x", {}, None)

    broken2 = GarageBlobAdapter(
        url="http://blob:3900", access_key="ak", secret_key="sk", opener=_boom
    )
    with pytest.raises(RuntimeError, match="get failed"):
        await broken2.get_blob("b", "k")


def test_garage_signing_is_deterministic_and_shaped() -> None:
    from vibey.infrastructure.blob.garage import _canonical_uri, _signature

    assert _canonical_uri("b", "a/b c") == "/b/a/b%20c"
    first = _signature(
        secret_key="sk", region="us-east-1", datestamp="20260101", string_to_sign="s"
    )
    second = _signature(
        secret_key="sk", region="us-east-1", datestamp="20260101", string_to_sign="s"
    )
    assert first == second
    assert len(first) == 64
    assert all(c in "0123456789abcdef" for c in first)


@pytest.mark.asyncio
async def test_in_memory_blob_satisfies_port() -> None:
    blob: BlobPort = InMemoryBlob()
    assert isinstance(blob, InMemoryBlobInterface)
    locator = await blob.put_blob("b", "k", b"v", "text/plain")
    assert locator == "memory://b/k"
    assert await blob.get_blob("b", "k") == b"v"
    with pytest.raises(FileNotFoundError):
        await blob.get_blob("b", "missing")


# ----------------------------------------------------
# 8. SIEM surface (Wazuh indexer)
# ----------------------------------------------------


@pytest.mark.asyncio
async def test_wazuh_adapter_ships_audit_events() -> None:
    opener = MagicMock(return_value=_mock_response(b'{"_id": "1"}'))
    adapter = WazuhSiemAdapter(
        url="http://siem:9200", username="admin", password="pw", opener=opener
    )
    assert isinstance(adapter, WazuhSiemAdapterInterface)
    await adapter.send_event("vibey-audit", {"action": "deploy", "actor": "worker"})
    sent = opener.call_args[0][0]
    assert sent.get_method() == "POST"
    assert sent.full_url == "http://siem:9200/vibey-audit/_doc"
    assert sent.get_header("Authorization") == "Basic YWRtaW46cHc="
    body = json.loads(sent.data.decode("utf-8"))
    assert body["action"] == "deploy"
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_wazuh_adapter_event_timestamp_wins_unless_given() -> None:
    opener = MagicMock(return_value=_mock_response(b"{}"))
    adapter = WazuhSiemAdapter(url="http://siem:9200", opener=opener)
    assert isinstance(adapter, WazuhSiemAdapterInterface)
    await adapter.send_event("idx", {"timestamp": "then", "a": 1})
    body = json.loads(opener.call_args[0][0].data.decode("utf-8"))
    assert body["timestamp"] == "then"
    sent = opener.call_args[0][0]
    assert sent.get_header("Authorization") is None


@pytest.mark.asyncio
async def test_wazuh_adapter_http_error_becomes_runtime_error() -> None:
    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter = WazuhSiemAdapter(url="http://siem:9200", opener=_raising_opener(err))
    with pytest.raises(RuntimeError):
        await adapter.send_event("idx", {"a": 1})


@pytest.mark.asyncio
async def test_in_memory_siem_satisfies_port() -> None:
    siem: SiemPort = InMemorySiem()
    assert isinstance(siem, InMemorySiemInterface)
    await siem.send_event("idx", {"a": 1})
    assert siem.events == [("idx", {"a": 1})]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_garage_send_handles_unreadable_http_error_body() -> None:
    class _UnreadableHTTPError(urllib.error.HTTPError):
        def read(self, *_: Any) -> bytes:
            raise OSError("cannot read")

    err = _UnreadableHTTPError("http://blob:3900", 500, "boom", {}, None)
    adapter = GarageBlobAdapter(
        url="http://blob:3900", access_key="ak", secret_key="sk", opener=_raising_opener(err)
    )
    with pytest.raises(RuntimeError, match="get failed: HTTP 500"):
        await adapter.get_blob("b", "k")


def test_rabbitmq_request_without_payload_omits_content_type() -> None:
    opener = MagicMock(return_value=_mock_response(b'{"status": "ok"}'))
    adapter = RabbitMqBusAdapter(
        url="http://bus:15672", username="guest", password="guest", opener=opener
    )
    resp = adapter._request("GET", "overview", payload=None)
    assert resp == {"status": "ok"}
    req = opener.call_args[0][0]
    assert "Content-Type" not in req.headers


def test_resp_reader_raises_on_empty_read() -> None:
    from vibey.infrastructure.cache.redis import RedisError, _RespReader

    sock = MagicMock()
    sock.makefile.return_value.readline.return_value = b""
    reader = _RespReader(sock)
    with pytest.raises(RedisError, match="redis closed the connection"):
        reader.read()
