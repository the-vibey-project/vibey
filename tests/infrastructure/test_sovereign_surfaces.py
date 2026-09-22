# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for the ADR-0042 operational surfaces: in-memory defaults, concrete
adapters, config parsing, and build_app wiring."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vibey.application.interfaces import (
    ConfigStorePort,
    DocsPort,
    EmailPort,
    FilesPort,
    IssueTrackerPort,
    MessagingPort,
    SecretsPort,
    SmsPort,
)
from vibey.bootstrap import build_app
from vibey.domain.config import ConfigError, parse_config
from vibey.infrastructure.config_store.in_memory import InMemoryConfigStore
from vibey.infrastructure.config_store.infisical import InfisicalConfigStoreAdapter
from vibey.infrastructure.config_store.interfaces.in_memory_interface import (
    InMemoryConfigStoreInterface,
)
from vibey.infrastructure.config_store.interfaces.infisical_interface import (
    InfisicalConfigStoreAdapterInterface,
)
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
from vibey.infrastructure.secrets.bitwarden import BitwardenSecretsAdapter
from vibey.infrastructure.secrets.in_memory import InMemorySecrets
from vibey.infrastructure.secrets.interfaces.bitwarden_interface import (
    BitwardenSecretsAdapterInterface,
)
from vibey.infrastructure.secrets.interfaces.in_memory_interface import InMemorySecretsInterface
from vibey.infrastructure.sms.fossify import FossifySmsAdapter
from vibey.infrastructure.sms.in_memory import InMemorySms
from vibey.infrastructure.sms.interfaces.fossify_interface import FossifySmsAdapterInterface
from vibey.infrastructure.sms.interfaces.in_memory_interface import InMemorySmsInterface
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


def _mock_response(payload: bytes = b"{}") -> MagicMock:
    resp = MagicMock()
    resp.__enter__.return_value.read.return_value = payload
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
async def test_bitwarden_adapter_roundtrip() -> None:
    adapter = BitwardenSecretsAdapter(
        url="http://vault",
        token="tok",
        opener=MagicMock(return_value=_mock_response(b'{"value": "p"}')),
    )
    assert isinstance(adapter, BitwardenSecretsAdapterInterface)
    assert await adapter.get_secret("db") == "p"

    missing = urllib.error.HTTPError("http://x", 404, "nope", {}, None)
    adapter_404 = BitwardenSecretsAdapter(
        url="http://vault", token="tok", opener=_raising_opener(missing)
    )
    with pytest.raises(KeyError):
        await adapter_404.get_secret("nope")

    forbidden = urllib.error.HTTPError("http://x", 403, "denied", {}, None)
    adapter_403 = BitwardenSecretsAdapter(
        url="http://vault", token="tok", opener=_raising_opener(forbidden)
    )
    with pytest.raises(RuntimeError):
        await adapter_403.get_secret("nope")

    set_opener = MagicMock(return_value=_mock_response())
    adapter_set = BitwardenSecretsAdapter(url="http://vault", token="tok", opener=set_opener)
    await adapter_set.set_secret("db", "p")
    assert set_opener.call_count == 1


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
async def test_fossify_sms_adapter_posts_json() -> None:
    adapter = FossifySmsAdapter(url="http://sms.local/api", token="tok")
    assert isinstance(adapter, FossifySmsAdapterInterface)
    with patch("urllib.request.urlopen", return_value=_mock_response()) as opener:
        await adapter.send_sms("+10000000000", "ping")
        sent = opener.call_args[0][0]
        assert sent.get_method() == "POST"
        assert sent.get_header("Authorization") == "Bearer tok"

    anonymous = FossifySmsAdapter(url="http://sms.local/api")
    with patch("urllib.request.urlopen", return_value=_mock_response()) as opener:
        await anonymous.send_sms("+10000000000", "ping")
        sent = opener.call_args[0][0]
        assert sent.get_header("Authorization") is None


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
            "sms": {"url": "http://sms", "token": "t"},
            "messaging": {"url": "http://matrix", "token": "t", "room_id": "!r:x"},
            "config_store": {
                "url": "http://infisical",
                "token": "t",
                "project_id": "pid",
                "environment": "prod",
            },
        }
    )
    assert cfg.tracker.workspace_slug == "my-team"
    assert cfg.tracker.project_id == "pid"
    assert cfg.docs.book_id == 9
    assert cfg.secrets.url == "http://vault"
    assert cfg.files.user == "u"
    assert cfg.email.smtp_port == 465
    assert cfg.sms.token == "t"
    assert cfg.messaging.room_id == "!r:x"
    assert cfg.config_store.project_id == "pid"
    assert cfg.config_store.environment == "prod"


def test_surface_tables_default_to_none() -> None:
    cfg = parse_config(_MINIMAL)
    assert cfg.tracker.url is None
    assert cfg.config_store.url is None
    assert cfg.config_store.environment == "dev"


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


@pytest.mark.asyncio
async def test_build_app_defaults_to_in_memory_surfaces() -> None:
    mock_pool = _mock_pool()
    migrator = MagicMock()
    migrator.apply = AsyncMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)),
        patch("vibey.bootstrap.PostgresMigrator") as migrator_cls,
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


@pytest.mark.asyncio
async def test_build_app_wires_concrete_adapters_from_config() -> None:
    from vibey.domain.config import (
        ConfigStoreConfig,
        DocsConfig,
        EmailConfig,
        FilesConfig,
        MessagingConfig,
        ProjectConfig,
        SecretsConfig,
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
        secrets=SecretsConfig(url="http://bw", token="t"),
        files=FilesConfig(url="http://nc", user="u", password="p"),
        email=EmailConfig(smtp_host="smtp", smtp_port=587),
        sms=SmsConfig(url="http://sms"),
        messaging=MessagingConfig(url="http://mx", token="t"),
        config_store=ConfigStoreConfig(url="http://inf", token="t", project_id="p"),
    )

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)),
        patch("vibey.bootstrap.PostgresMigrator") as migrator_cls,
        patch("vibey.bootstrap.database_url", return_value="postgresql://x"),
    ):
        migrator_cls.from_environ.return_value = migrator
        async with build_app(config=cfg) as resources:
            assert isinstance(resources.tracker, PlaneTrackerAdapter)
            assert isinstance(resources.docs, BookStackDocsAdapter)
            assert isinstance(resources.secrets, BitwardenSecretsAdapter)
            assert isinstance(resources.files, NextcloudFilesAdapter)
            assert isinstance(resources.email, ForwardEmailAdapter)
            assert isinstance(resources.sms, FossifySmsAdapter)
            assert isinstance(resources.messaging, MatrixMessagingAdapter)
            assert isinstance(resources.config_store, InfisicalConfigStoreAdapter)


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
async def test_bitwarden_adapter_set_secret_error() -> None:
    err = urllib.error.HTTPError("http://x", 500, "boom", {}, None)
    adapter = BitwardenSecretsAdapter(url="http://vault", token="tok", opener=_raising_opener(err))
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
