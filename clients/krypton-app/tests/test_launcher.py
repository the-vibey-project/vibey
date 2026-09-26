"""The krypton launcher, with every side effect faked: no process, browser or network."""

from __future__ import annotations

import io
from collections.abc import Sequence

import pytest

from krypton_app import cli
from krypton_app.launcher import KryptonLauncher


class FakeProcess:
    def __init__(
        self, polls: Sequence[int | None] = (None,), wait: int | BaseException = 0
    ) -> None:
        self._polls = list(polls)
        self._wait = wait
        self.terminated = False

    def poll(self) -> int | None:
        return self._polls.pop(0) if len(self._polls) > 1 else self._polls[0]

    def wait(self) -> int:
        if isinstance(self._wait, BaseException):
            raise self._wait
        return self._wait

    def terminate(self) -> None:
        self.terminated = True


def make(
    *,
    found: str | None = "/x/vibey",
    serve_rc: int = 0,
    process: FakeProcess | None = None,
    probes: Sequence[bool] = (True,),
    times: Sequence[float] = (0.0,),
) -> tuple[KryptonLauncher, io.StringIO, list[list[str]], list[str]]:
    out = io.StringIO()
    spawned: list[list[str]] = []
    browsed: list[str] = []
    probe_values = list(probes)
    clock_values = list(times)
    proc = process or FakeProcess()

    def spawn(argv: Sequence[str]) -> FakeProcess:
        spawned.append(list(argv))
        return proc

    launcher = KryptonLauncher(
        out=out,
        find=lambda _name: found,
        run=lambda _argv: serve_rc,
        spawn=spawn,
        probe=lambda _url: probe_values.pop(0) if len(probe_values) > 1 else probe_values[0],
        browse=browsed.append,
        sleep=lambda _s: None,
        clock=lambda: clock_values.pop(0) if len(clock_values) > 1 else clock_values[0],
    )
    return launcher, out, spawned, browsed


def test_no_vibey_says_how_to_install_it() -> None:
    launcher, out, spawned, _ = make(found=None)
    assert launcher.launch("127.0.0.1", 8765, open_browser=True) == 1
    assert "pip install vibey-engine" in out.getvalue()
    assert spawned == []


def test_an_engine_without_serve_starts_nothing_and_says_what_is_available() -> None:
    launcher, out, spawned, _ = make(serve_rc=2)
    assert launcher.launch("127.0.0.1", 8765, open_browser=True) == 1
    assert "does not provide it yet" in out.getvalue()
    assert "vibey --help" in out.getvalue()
    assert spawned == []


def test_the_hub_starts_and_opens() -> None:
    launcher, out, spawned, browsed = make()
    assert launcher.launch("127.0.0.1", 8765, open_browser=True) == 0
    assert spawned == [["/x/vibey", "serve", "--host", "127.0.0.1", "--port", "8765"]]
    assert browsed == ["http://127.0.0.1:8765/"]
    assert "the vibey hub is at" in out.getvalue()


def test_no_browser_opens_nothing() -> None:
    launcher, _, _, browsed = make()
    assert launcher.launch("127.0.0.1", 8765, open_browser=False) == 0
    assert browsed == []


def test_a_serve_that_dies_early_is_reported() -> None:
    launcher, out, _, _ = make(process=FakeProcess(polls=[3]), probes=[False])
    assert launcher.launch("127.0.0.1", 8765, open_browser=True) == 3
    assert "exited with status 3" in out.getvalue()


def test_a_serve_that_never_answers_is_stopped() -> None:
    proc = FakeProcess()
    launcher, out, _, _ = make(process=proc, probes=[False], times=[0.0, 100.0])
    assert launcher.launch("127.0.0.1", 8765, open_browser=True) == 1
    assert proc.terminated
    assert "nothing answered" in out.getvalue()


def test_a_poll_after_one_wait_then_ready() -> None:
    launcher, _, _, browsed = make(probes=[False, True], times=[0.0, 1.0])
    assert launcher.launch("h", 1, open_browser=True) == 0
    assert browsed == ["http://h:1/"]


def test_interrupt_stops_the_hub() -> None:
    proc = FakeProcess(wait=KeyboardInterrupt())
    launcher, _, _, _ = make(process=proc)
    assert launcher.launch("127.0.0.1", 8765, open_browser=False) == 130
    assert proc.terminated


def test_cli_passes_its_options(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, bool]] = []

    class Fake:
        def __init__(self, out: object, vibey: str | None) -> None:
            assert vibey == "/nonexistent/vibey"

        def launch(self, host: str, port: int, open_browser: bool) -> int:
            calls.append((host, port, open_browser))
            return 7

    monkeypatch.setattr(cli, "KryptonLauncher", Fake)
    assert cli.main(["--no-browser", "--vibey", "/nonexistent/vibey"]) == 7
    assert calls == [("127.0.0.1", 8765, False)]


def test_cli_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(["--help"])
    assert raised.value.code == 0
