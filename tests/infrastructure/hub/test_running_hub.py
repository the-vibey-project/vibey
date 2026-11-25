# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The worker finds the running hub the way every other client does: the runtime record in the
hub's state folder, believed only while the process it names holds the hub's lock, and only on
loopback (SP-LOOPS Phase 6, Task 5). The lock's holder is a fake; nothing listens or connects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from vibey.application.interfaces import HubLocatorInterface
from vibey.infrastructure.hub.interfaces.running_hub_interface import RunningHubInterface
from vibey.infrastructure.hub.local_token import RUNTIME_FILE, LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.running_hub import RunningHub

PID = 4321


class _Logger:
    def __init__(self) -> None:
        self.lines: list[tuple[str, dict[str, Any]]] = []

    def bind(self, **kwargs: Any) -> _Logger:
        return self

    def debug(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))


def _serving(state: Path, host: str = "127.0.0.1", port: int = 28100, tls: bool = False) -> None:
    LocalTokenStore(state).record_serving(ServingRecord(host=host, port=port, pid=PID, tls=tls))


def _hub(state: Path, holder: int | None = PID, logger: _Logger | None = None) -> RunningHub:
    return RunningHub(
        state, holder=lambda folder: holder if folder == state else None, logger=logger
    )


def test_it_meets_both_seams(tmp_path: Path) -> None:
    hub = _hub(tmp_path)
    assert isinstance(hub, RunningHubInterface)
    assert isinstance(hub, HubLocatorInterface)


def test_a_running_hub_is_its_loopback_url_with_no_path(tmp_path: Path) -> None:
    _serving(tmp_path)
    assert _hub(tmp_path).url() == "http://127.0.0.1:28100"


def test_a_hub_serving_tls_is_https(tmp_path: Path) -> None:
    _serving(tmp_path, tls=True)
    assert _hub(tmp_path).url() == "https://127.0.0.1:28100"


@pytest.mark.parametrize(
    ("host", "url"),
    [
        ("localhost", "http://127.0.0.1:28100"),
        ("0.0.0.0", "http://127.0.0.1:28100"),
        ("::1", "http://[::1]:28100"),
    ],
)
def test_the_url_is_the_loopback_literal_the_record_maps_to(
    tmp_path: Path, host: str, url: str
) -> None:
    _serving(tmp_path, host=host)
    assert _hub(tmp_path).url() == url


def test_no_record_is_no_hub(tmp_path: Path) -> None:
    assert _hub(tmp_path).url() is None


@pytest.mark.parametrize("holder", [None, 0, PID + 1], ids=["unlocked", "starting", "another"])
def test_a_record_whose_process_does_not_hold_the_lock_is_no_hub(
    tmp_path: Path, holder: int | None
) -> None:
    _serving(tmp_path)
    assert _hub(tmp_path, holder=holder).url() is None


def test_a_record_naming_another_computer_is_no_hub_and_is_said(tmp_path: Path) -> None:
    _serving(tmp_path, host="192.168.1.20")
    logger = _Logger()
    assert _hub(tmp_path, logger=logger).url() is None
    assert logger.lines == [("hub_record_not_loopback", {"state_dir": str(tmp_path)})]


def test_an_unreadable_record_is_no_hub_and_is_said(tmp_path: Path) -> None:
    (tmp_path / RUNTIME_FILE).write_text("[]")
    logger = _Logger()
    assert _hub(tmp_path, logger=logger).url() is None
    [(event, fields)] = logger.lines
    assert event == "hub_record_unreadable" and str(tmp_path) in fields["error"]


def test_without_a_logger_the_failures_are_still_no_hub(tmp_path: Path) -> None:
    (tmp_path / RUNTIME_FILE).write_text("[]")
    assert _hub(tmp_path).url() is None
    _serving(tmp_path, host="192.168.1.20")
    assert _hub(tmp_path).url() is None


def test_the_default_holder_asks_the_hubs_own_lock(tmp_path: Path) -> None:
    """No hub has ever run here, so the lock file is absent and nobody holds it."""
    _serving(tmp_path)
    assert RunningHub(tmp_path).url() is None
