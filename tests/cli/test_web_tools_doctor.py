# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey doctor`'s `web-tools` line (ADR-0102, SP-ACP Task 9b): whether the hub serves
`vibey_search` and `vibey_fetch` to the agent, and under which budgets. Added after the
`web-search` lines.

The hub it asks about is the person's own (their own `vibey.toml`'s `[hub]`), never one a folder's
`vibey.toml` names, and it is asked only on loopback, with no credential: a hostile project
cannot turn doctor into a request to a host of its choosing.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

import http.server
import json
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from vibey.cli.interfaces.web_tools_doctor_interface import WebToolsDoctorInterface
from vibey.cli.web_search_doctor import WebSearchDoctor
from vibey.cli.web_tools_doctor import WEB_TOOLS_DOCTOR, WebToolsDoctor
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord

DOCUMENT = json.dumps({"paths": {"/api/v1/web/search": {}, "/api/v1/web/fetch": {}}}).encode()
LOOPBACK_DOCUMENT = WebToolsDoctor.loopback_document
"""The real probe, taken before the suite's hermetic fixture stands a refusing one in."""


class World:
    """The person's own folder (`me/vibey.toml`, with its `[hub]`), the folder doctor runs in
    (`vibey.toml`), and every URL the probe was asked for."""

    def __init__(
        self, tmp_path: Path, *, answer: bytes = DOCUMENT, error: Exception | None = None
    ) -> None:
        self.root = tmp_path
        self.state = tmp_path / "state"
        self.user = tmp_path / "me" / "vibey.toml"
        self.user.parent.mkdir()
        self.mine(f"[hub]\nstate_dir = '{self.state}'\n")
        self.answer = answer
        self.error = error
        self.asked: list[tuple[str, Path | None]] = []

    def mine(self, text: str) -> None:
        self.user.write_text(text, encoding="utf-8")

    def folder(self, text: str) -> None:
        (self.root / "vibey.toml").write_text(text, encoding="utf-8")

    def serving(
        self, host: str = "127.0.0.1", *, tls: bool = False, state: Path | None = None
    ) -> None:
        LocalTokenStore(state or self.state).record_serving(
            ServingRecord(host=host, port=8765, pid=4242, tls=tls)
        )

    def probe(self, url: str, cafile: Path | None) -> bytes:
        self.asked.append((url, cafile))
        if self.error is not None:
            raise self.error
        return self.answer

    def doctor(self) -> WebToolsDoctor:
        return WebToolsDoctor(
            config_path=lambda: self.root / "vibey.toml",
            user_config=lambda: self.user,
            probe=self.probe,
        )


def test_the_line_meets_its_seam() -> None:
    assert isinstance(WEB_TOOLS_DOCTOR, WebToolsDoctorInterface)


def test_a_running_hub_offering_the_routes_to_an_agent_holding_web_passes(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.serving()
    line = world.doctor().line()
    assert line.startswith("PASS web-tools ")
    assert "vibey_search and vibey_fetch" in line
    assert "60 searches and 30 fetches per hour per principal" in line
    assert world.asked == [("http://127.0.0.1:8765/api/v1/openapi.json", None)]


@pytest.mark.parametrize(
    ("host", "probed"),
    [
        ("localhost", "127.0.0.1"),
        ("127.0.0.1", "127.0.0.1"),
        ("127.8.9.10", "127.8.9.10"),
        ("::1", "[::1]"),
        ("0.0.0.0", "127.0.0.1"),
        ("::", "[::1]"),
        ("::ffff:127.0.0.1", "127.0.0.1"),
    ],
)
def test_a_record_naming_this_computer_is_probed_at_a_fixed_loopback_literal(
    tmp_path: Path, host: str, probed: str
) -> None:
    world = World(tmp_path)
    world.serving(host)
    assert world.doctor().line().startswith("PASS")
    assert world.asked == [(f"http://{probed}:8765/api/v1/openapi.json", None)]


@pytest.mark.parametrize(
    "host",
    [
        "203.0.113.9",
        "192.168.1.5",
        "evil.example",
        "localhost.evil.example",
        "evil.localhost",
        "localhost.",
        "LOCALHOST",
        "127.1",
        "0x7f.1",
        "::ffff:10.0.0.1",
    ],
)
def test_a_record_naming_another_host_is_never_probed(tmp_path: Path, host: str) -> None:
    world = World(tmp_path)
    world.serving(host)
    line = world.doctor().line()
    assert line.startswith("WARN web-tools ") and "non-loopback address; not probed" in line
    assert world.asked == []


def test_a_hostile_folder_cannot_point_doctor_at_a_hub_record_of_its_own(tmp_path: Path) -> None:
    """The folder's vibey.toml names a state folder holding a record for 203.0.113.9: doctor reads
    the person's own state folder, finds no hub, and sends nothing anywhere."""
    world = World(tmp_path)
    planted = tmp_path / "planted"
    world.folder(f"[hub]\nstate_dir = '{planted}'\n")
    world.serving("203.0.113.9", state=planted)
    line = world.doctor().line()
    assert line.startswith("WARN web-tools ") and "no hub is running" in line
    assert world.asked == []


def test_the_persons_own_state_folder_is_honoured(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.folder("[hub]\nstate_dir = '/nonexistent/elsewhere'\n")
    world.serving()  # in the person's own state folder
    assert world.doctor().line().startswith("PASS")


def test_the_budgets_shown_are_the_persons_narrowed_by_the_folder(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.mine(
        f"[hub]\nstate_dir = '{world.state}'\n[web]\nsearches_per_hour = 9\nfetches_per_hour = 4\n"
    )
    world.folder("[web]\nfetches_per_hour = 2\nsearches_per_hour = 900\n")
    world.serving()
    assert "9 searches and 2 fetches per hour" in world.doctor().line()


def test_an_agent_without_web_is_told_how_to_grant_it(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.mine(f"[hub]\nstate_dir = '{world.state}'\nagent_scopes = ['view', 'answer', 'run']\n")
    world.serving()
    line = world.doctor().line()
    assert line.startswith("WARN web-tools ") and "[hub] agent_scopes" in line
    assert world.asked == []  # nothing to check on the hub for an agent that cannot use it


def test_no_running_hub_is_a_warning_and_nothing_is_started(tmp_path: Path) -> None:
    world = World(tmp_path)
    line = world.doctor().line()
    assert line.startswith("WARN web-tools ") and "vibey hub start" in line
    assert world.asked == []


@pytest.mark.parametrize(
    ("answer", "error", "needle"),
    [
        (json.dumps({"paths": {"/api/v1/projects": {}}}).encode(), None, "does not offer"),
        (b"", ConnectionRefusedError("refused"), "did not answer"),
        (b"<html>", None, "did not answer"),
        (b"[]", None, "did not answer"),
    ],
)
def test_a_hub_that_does_not_offer_the_routes_or_does_not_answer_is_a_warning(
    tmp_path: Path, answer: bytes, error: Exception | None, needle: str
) -> None:
    world = World(tmp_path, answer=answer, error=error)
    world.serving()
    line = world.doctor().line()
    assert line.startswith("WARN web-tools ") and needle in line


def test_a_tls_hub_is_asked_over_https_trusting_its_own_certificate(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.serving(tls=True)
    assert world.doctor().line().startswith("PASS")
    ((url, cafile),) = world.asked
    assert url.startswith("https://127.0.0.1:8765/") and cafile == world.state / "hub-cert.pem"


@pytest.mark.parametrize(
    ("mine", "folder"),
    [
        ("", "[web]\nallow_hosts = ['*.x.com']\n"),
        ("[hub]\nport = 'x'\n", ""),
    ],
)
def test_a_setting_the_hub_would_refuse_to_start_with_fails(
    tmp_path: Path, mine: str, folder: str
) -> None:
    world = World(tmp_path)
    world.mine(mine)
    world.folder(folder)
    assert world.doctor().line().startswith("FAIL web-tools ")


def test_a_malformed_serving_record_is_a_warning_never_a_crash(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.state.mkdir()
    (world.state / "serving.json").write_text("[]")
    assert world.doctor().line().startswith("WARN web-tools ")


def test_the_line_never_raises(tmp_path: Path) -> None:
    def boom() -> Path:
        raise RuntimeError("no folder")

    line = WebToolsDoctor(config_path=boom, user_config=boom).line()
    assert line.startswith("UNKNOWN web-tools ") and "could not check" in line


def test_the_web_search_section_adds_the_line_after_the_ones_it_had(tmp_path: Path) -> None:
    section = WebSearchDoctor(
        environ=lambda: {},
        opener=lambda request, timeout: (_ for _ in ()).throw(ConnectionRefusedError("down")),
        searxng=lambda: "WARN searxng x",
        web_tools=lambda: "PASS web-tools y",
    )
    lines, ok = section.doctor_lines()
    assert [line.split()[1] for line in lines] == [
        "web-search",
        "web-search-backup",
        "searxng",
        "web-tools",
    ]
    assert ok


# -- the real probe, against a loopback server of the test's own ---------------------------------


class _Hub(http.server.BaseHTTPRequestHandler):
    seen: list[dict[str, str]] = []

    def do_GET(self) -> None:  # noqa: N802 - the standard library's name
        type(self).seen.append(dict(self.headers.items()))
        if self.path == "/elsewhere":
            self.send_response(302)
            self.send_header("Location", "http://198.51.100.7/api/v1/openapi.json")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(DOCUMENT)

    def log_message(self, *args: object) -> None:
        return None


@pytest.fixture
def hub() -> Iterator[str]:
    _Hub.seen = []
    server = http.server.HTTPServer(("127.0.0.1", 0), _Hub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.web_network
def test_the_real_probe_sends_no_credential_and_follows_no_redirect_off_its_origin(
    hub: str,
) -> None:
    body = LOOPBACK_DOCUMENT(f"{hub}/api/v1/openapi.json", None)
    assert json.loads(body) == json.loads(DOCUMENT)
    (headers,) = _Hub.seen
    assert not {"authorization", "cookie"} & {name.lower() for name in headers}
    with pytest.raises(OSError):  # the 302 to another host is refused, never followed
        LOOPBACK_DOCUMENT(f"{hub}/elsewhere", None)


@pytest.mark.web_network
def test_a_missing_certificate_is_a_failure_to_answer(tmp_path: Path, hub: str) -> None:
    with pytest.raises(OSError):
        LOOPBACK_DOCUMENT(hub.replace("http:", "https:"), tmp_path / "no-cert.pem")


@pytest.mark.web_network
def test_the_real_probe_never_goes_through_a_proxy(
    hub: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A proxy in the environment would see the probe; the hub is on this computer, so it is
    asked directly."""
    for name in ("http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"):
        monkeypatch.setenv(name, "http://127.0.0.1:9")
    for name in ("no_proxy", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
    assert json.loads(LOOPBACK_DOCUMENT(f"{hub}/api/v1/openapi.json", None)) == json.loads(DOCUMENT)


@pytest.mark.parametrize(
    ("folder", "offered"),
    [
        ("", True),
        ("[hub]\nagent_scopes = ['view', 'web']\n", True),
        ("[hub]\nagent_scopes = ['view', 'answer']\n", False),
        ("[hub]\nagent_scopes = []\n", False),
    ],
)
def test_the_line_and_the_mcp_tools_list_agree(tmp_path: Path, folder: str, offered: bool) -> None:
    """P-9b-11 (SP-ACP Task 11a): doctor's PASS and what `vibey mcp` offers in `tools/list` are
    read by one rule -- the person's `[hub]`, narrowed by the folder's -- so they never disagree."""
    from vibey.domain.host_tools import HOST_TOOL_CATALOG
    from vibey.domain.hub_scope import HubScope
    from vibey.infrastructure.mcp.hub_gateway import HubGateway

    world = World(tmp_path)
    world.folder(folder)
    world.serving()
    gateway = HubGateway(
        config_path=lambda: world.user, project_config=lambda: tmp_path / "vibey.toml"
    )
    listed = {tool.name for tool in HOST_TOOL_CATALOG.for_scopes(gateway.agent_scopes())}
    line = world.doctor().line()
    assert line.startswith("PASS" if offered else "WARN")
    assert ("vibey_fetch" in listed) is offered
    assert (HubScope.WEB in gateway.agent_scopes()) is offered
