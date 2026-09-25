# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey hub pair | devices | revoke`: the host's side of pairing (ADR-0068).

The running hub is stood in for by an `httpx.MockTransport`: these tests are about what
the commands send (to where, with which credential, trusting which certificate) and how
they report what comes back. The routes themselves are tested in
tests/infrastructure/hub/test_hub_pairing.py.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
import typer
from typer.testing import CliRunner

from vibey.cli import hub_pair as module
from vibey.cli.hub_pair import HUB_PAIR, HubPairCommand, _render_qr
from vibey.cli.interfaces.hub_pair_interface import HubPairCommandInterface
from vibey.cli.main import app
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord

runner = CliRunner()


class Hub:
    """A running hub, as far as the commands can tell: answers each request it is sent."""

    def __init__(self, answer: Any = None, status: int = 200, fail: bool = False) -> None:
        self.answer = answer
        self.status = status
        self.fail = fail
        self.requests: list[httpx.Request] = []
        self.opened: dict[str, Any] = {}

    def __call__(self, **fields: Any) -> httpx.Client:
        self.opened = fields
        verify = fields.pop("verify")
        self.opened["verify"] = verify

        def handle(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if self.fail:
                raise httpx.ConnectError("refused", request=request)
            return httpx.Response(self.status, json=self.answer)

        return httpx.Client(transport=httpx.MockTransport(handle), **fields)


def _command(
    tmp_path: Path, hub: Hub, *, record: ServingRecord | None = None, qr: Any = None
) -> HubPairCommand:
    state = tmp_path / "state"
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "vibey.toml").write_text(f"[hub]\nstate_dir = '{state}'\n")
    store = LocalTokenStore(state)
    store.token()
    if record is not None:
        store.record_serving(record)
    return HubPairCommand(
        config_path=lambda: tmp_path / "vibey.toml",
        client=hub,
        qr=qr if qr is not None else (lambda uri: f"[QR {uri}]"),
    )


RUNNING = ServingRecord(host="127.0.0.1", port=8765, pid=os.getpid())
OFFER = {
    "code": "123456",
    "scopes": ["answer", "view"],
    "uri": "vibey-pair://192.168.1.5:8765?fp=ab&code=123456&v=1",
    "fingerprint": "ab",
    "expires_at": 1.0,
}


def test_the_command_meets_its_declared_seam() -> None:
    assert isinstance(HUB_PAIR, HubPairCommandInterface)


def test_pair_asks_the_running_hub_as_the_host_and_shows_the_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hub = Hub(OFFER)
    command = _command(tmp_path, hub, record=RUNNING)
    command.pair(["view", "answer", "view"])
    sent = hub.requests[0]
    assert sent.method == "POST" and str(sent.url) == "http://127.0.0.1:8765/api/v1/pairing/offers"
    assert json.loads(sent.content) == {"scopes": ["answer", "view"]}
    token = (tmp_path / "state" / "token").read_text().strip()
    assert sent.headers["authorization"] == f"Bearer {token}"
    assert hub.opened["verify"] is True
    out = capsys.readouterr().out
    assert f"[QR {OFFER['uri']}]" in out and "code: 123456" in out
    assert "scopes: answer, view" in out and "fingerprint (sha256): ab" in out


def test_pair_without_a_qr_renderer_or_fingerprint_still_shows_the_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hub = Hub(dict(OFFER, fingerprint=""))
    _command(tmp_path, hub, record=RUNNING, qr=lambda uri: None).pair(["view"])
    out = capsys.readouterr().out
    assert "[QR" not in out and "code: 123456" in out and "fingerprint" not in out


@pytest.mark.parametrize("scopes", [[], ["root"]])
def test_pair_needs_known_scopes(tmp_path: Path, scopes: list[str]) -> None:
    with pytest.raises(typer.Exit) as caught:
        _command(tmp_path, Hub(), record=RUNNING).pair(scopes)
    assert caught.value.exit_code == 2


def test_a_tls_hub_is_reached_over_https_trusting_only_its_own_certificate(
    tmp_path: Path,
) -> None:
    hub = Hub([])
    record = ServingRecord(host="0.0.0.0", port=9100, pid=os.getpid(), tls=True)  # nosec B104
    _command(tmp_path, hub, record=record).devices()
    assert str(hub.requests[0].url) == "https://127.0.0.1:9100/api/v1/devices"
    assert hub.opened["verify"] == str(tmp_path / "state" / "hub-cert.pem")


def test_an_ipv6_hub_is_bracketed(tmp_path: Path) -> None:
    hub = Hub([])
    _command(tmp_path, hub, record=ServingRecord(host="::1", port=1, pid=1)).devices()
    assert str(hub.requests[0].url) == "http://[::1]:1/api/v1/devices"


def test_devices_lists_and_revoke_revokes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    listed = [{"device_id": "d1", "name": "phone", "scopes": ["view"], "paired_at": 1.0}]
    _command(tmp_path, Hub([]), record=RUNNING).devices()
    _command(tmp_path, Hub(listed), record=RUNNING).devices()
    hub = Hub({"revoked": "d1"})
    _command(tmp_path, hub, record=RUNNING).revoke("d1")
    assert hub.requests[0].method == "DELETE" and hub.requests[0].url.path.endswith("/devices/d1")
    out = capsys.readouterr().out
    assert "no paired devices" in out and "d1  phone  view" in out and "revoked d1" in out


def test_no_running_hub_a_dead_hub_or_a_refusal_exit_cleanly(tmp_path: Path) -> None:
    for command, code in (
        (_command(tmp_path / "a", Hub()), 3),
        (_command(tmp_path / "b", Hub(fail=True), record=RUNNING), 3),
        (_command(tmp_path / "c", Hub({"detail": "no"}, status=404), record=RUNNING), 1),
    ):
        with pytest.raises(typer.Exit) as caught:
            command.revoke("d1")
        assert caught.value.exit_code == code


def test_a_config_that_cannot_be_read_exits_two(tmp_path: Path) -> None:
    (tmp_path / "vibey.toml").write_text("[hub]\nlan = 'yes'\n")
    command = HubPairCommand(config_path=lambda: tmp_path / "vibey.toml", client=Hub())
    with pytest.raises(typer.Exit) as caught:
        command.devices()
    assert caught.value.exit_code == 2


def test_the_qr_code_renders_or_steps_aside_without_segno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered = _render_qr("vibey-pair://h:1?code=1")
    assert rendered is not None and "██" in rendered
    monkeypatch.setitem(sys.modules, "segno", None)
    assert _render_qr("x") is None


def test_the_typer_commands_reach_the_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, Any]] = []

    class Recorder:
        def pair(self, scopes: list[str]) -> None:
            calls.append(("pair", scopes))

        def devices(self) -> None:
            calls.append(("devices", None))

        def revoke(self, device_id: str) -> None:
            calls.append(("revoke", device_id))

    monkeypatch.setattr(module, "HUB_PAIR", Recorder())
    for args in (["hub", "pair", "--scope", "view"], ["hub", "devices"], ["hub", "revoke", "d1"]):
        result = runner.invoke(app, args)
        assert result.exit_code == 0, result.output
    assert calls == [("pair", ["view"]), ("devices", None), ("revoke", "d1")]


def test_a_serving_record_whose_tls_is_not_a_boolean_is_refused(tmp_path: Path) -> None:
    store = LocalTokenStore(tmp_path)
    store.record_serving(RUNNING)
    record = json.loads((tmp_path / "serving.json").read_text())
    assert record["tls"] is False and store.serving() == RUNNING
    (tmp_path / "serving.json").write_text(json.dumps(dict(record, tls="yes")))
    with pytest.raises(ValueError, match="tls"):
        store.serving()
