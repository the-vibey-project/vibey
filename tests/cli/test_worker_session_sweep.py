# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey worker` sweeps the session registry once as it starts (SP-LOOPS Phase 6, Task 7; R4).

A worker that crashed or was killed never revoked its engine sessions' web principals. Their
token files go with their run folders under the snapshot sweep; their registry entries, in the
hub's state folder, are removed here once expired -- never a live one, never one that cannot be
read. A sweep that cannot run is logged and never stops the worker. No database is reached: the
registry is real files in pytest's folder. That the worker sweeps before it claims anything is
pinned against a real database in `test_worker_all_projects.py`.
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

import vibey.bootstrap
import vibey.cli.main as main
from vibey.application.dto import SessionSweepReport
from vibey.bootstrap import session_registry_sweep
from vibey.domain.config import ConfigError
from vibey.domain.session_principal import SessionPrincipal
from vibey.infrastructure.hub.session_registry import SESSIONS_FOLDER, SessionRegistry

pytestmark = pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX")


class _Logger:
    def __init__(self) -> None:
        self.lines: list[tuple[str, str, dict[str, Any]]] = []

    def bind(self, **kwargs: Any) -> _Logger:
        return self

    def debug(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("debug", event, kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("warning", event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("error", event, kwargs))


def _digest(n: int) -> str:
    return hashlib.sha256(f"token-{n}".encode()).hexdigest()


def _principal(n: int, expires_at: float) -> SessionPrincipal:
    run = UUID(int=n)
    return SessionPrincipal(name=f"session:{run}", run_id=run, expires_at=expires_at)


def _registry_in(monkeypatch: pytest.MonkeyPatch, state: Path) -> SessionRegistry:
    """The worker's sweep reads `state`, as it would read the person's `[hub] state_dir`."""
    monkeypatch.setattr(
        vibey.bootstrap,
        "session_registry_sweep",
        lambda **_: session_registry_sweep(state_dir=state),
    )
    return SessionRegistry(state)


def test_expired_entries_go_live_ones_stay_and_a_replay_removes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = _registry_in(monkeypatch, tmp_path / "hub")
    now = time.time()
    registry.record(_digest(1), _principal(1, now - 60))  # a crashed run's, an hour past
    registry.record(_digest(2), _principal(2, now + 3_600))  # a live run's, another worker's
    logger = _Logger()

    main._sweep_session_registry(logger)  # noqa: SLF001
    main._sweep_session_registry(logger)  # noqa: SLF001  (idempotent under replay)

    assert logger.lines == [
        ("info", "session_registry_sweep", {"removed": 1, "kept": 1, "refused": 0}),
        ("info", "session_registry_sweep", {"removed": 0, "kept": 1, "refused": 0}),
    ]
    assert registry.find(_digest(1)) is None
    assert registry.find(_digest(2)) == _principal(2, now + 3_600)


def test_an_entry_that_cannot_be_read_is_named_and_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = _registry_in(monkeypatch, tmp_path / "hub")
    registry.record(_digest(1), _principal(1, time.time() - 60))
    planted = tmp_path / "hub" / SESSIONS_FOLDER / f"{_digest(1)}.json"
    os.chmod(planted, 0o644)
    logger = _Logger()

    main._sweep_session_registry(logger)  # noqa: SLF001

    assert logger.lines[0] == (
        "info",
        "session_registry_sweep",
        {"removed": 0, "kept": 0, "refused": 1},
    )
    level, event, fields = logger.lines[1]
    assert (level, event) == ("warning", "session_registry_entry_left")
    assert str(planted) in fields["reason"] and "open to other accounts" in fields["reason"]
    assert planted.exists()


def test_no_hub_state_folder_at_all_is_an_empty_sweep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _registry_in(monkeypatch, tmp_path / "never")
    logger = _Logger()

    main._sweep_session_registry(logger)  # noqa: SLF001

    assert logger.lines == [
        ("info", "session_registry_sweep", {"removed": 0, "kept": 0, "refused": 0})
    ]


class _Sweep:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def sweep(self) -> SessionSweepReport:
        raise self.error


@pytest.mark.parametrize(
    "error",
    [
        PermissionError("/hub/sessions is open to other accounts; refusing to use it"),
        ConfigError("/person/vibey.toml", "hub.state_dir must be a path"),
        ValueError("the sweep needs a finite now to judge expiry by, not inf"),
    ],
    ids=["os", "config", "value"],
)
def test_a_sweep_that_cannot_run_is_logged_never_fatal(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    monkeypatch.setattr(vibey.bootstrap, "session_registry_sweep", lambda **_: _Sweep(error))
    logger = _Logger()

    main._sweep_session_registry(logger)  # noqa: SLF001

    assert logger.lines == [("warning", "session_registry_sweep_refused", {"error": str(error)})]


def test_the_composition_sweeps_the_persons_own_hub_state_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without `state_dir`, the registry the worker mints into: the person's `[hub] state_dir`."""
    person = tmp_path / "config" / "vibey.toml"
    person.parent.mkdir()
    state = tmp_path / "persons-hub"
    person.write_text(f'[hub]\nstate_dir = "{state}"\n', encoding="utf-8")
    monkeypatch.setattr(vibey.bootstrap, "acp_user_config", lambda: person)
    registry = SessionRegistry(state)
    registry.record(_digest(1), _principal(1, time.time() - 1))

    report = session_registry_sweep().sweep()

    assert report == SessionSweepReport(removed=(f"session:{UUID(int=1)}",), kept=0, refused=())
    assert registry.find(_digest(1)) is None
