# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An engine run's web access: its own grant from the running hub, or none and why (SP-LOOPS
Phase 6, Task 5; R1, R4).

The hub locator, the clock and the principals are fakes here; one test at the end mints through
the real token store and registry, to show the token's only copy is the run's own 0600 file.
"""

from __future__ import annotations

import os
import stat
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from vibey.application.dto import RunWebAccess, SessionGrant
from vibey.application.interfaces import HubLocatorInterface, RunWebGrantsInterface
from vibey.application.run_web_grants import RunWebGrants
from vibey.application.session_web_principals import SessionWebPrincipals
from vibey.domain.errors import SessionGrantRefused
from vibey.domain.session_principal import SessionPrincipal
from vibey.domain.session_web_state import NO_HUB, NO_RUN_FOLDER, NO_TOKEN
from vibey.infrastructure.hub.session_registry import SessionRegistry
from vibey.infrastructure.hub.session_token_store import WEB_TOKEN_FILE, SessionTokenStore

RUN = UUID("00000000-0000-4000-8000-000000000005")
HUB = "http://127.0.0.1:28100"
NOW = 1_800_000_000.0
TOKEN = "tok-CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"


class _Hub:
    def __init__(self, url: str | None) -> None:
        self._url = url
        self.asked = 0

    def url(self) -> str | None:
        self.asked += 1
        return self._url


class _Principals:
    def __init__(self) -> None:
        self.minted: list[tuple[UUID, Path, float]] = []
        self.revoked: list[SessionGrant] = []
        self.mint_error: Exception | None = None
        self.revoke_error: Exception | None = None

    def mint(self, run_id: UUID, folder: Path, now: float) -> SessionGrant:
        if self.mint_error is not None:
            raise self.mint_error
        self.minted.append((run_id, folder, now))
        return SessionGrant(
            token_file=folder / "web-token",
            principal=SessionPrincipal(name=f"session:{run_id}", run_id=run_id, expires_at=now + 1),
            digest="d" * 64,
        )

    def revoke(self, grant: SessionGrant) -> None:
        if self.revoke_error is not None:
            raise self.revoke_error
        self.revoked.append(grant)

    def lookup(self, token: str, now: float) -> SessionPrincipal | None:
        return None


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


def _grants(
    hub: str | None = HUB, *, logger: _Logger | None = None
) -> tuple[RunWebGrants, _Hub, _Principals]:
    locator, principals = _Hub(hub), _Principals()
    return (
        RunWebGrants(hub=locator, principals=principals, clock=lambda: NOW, logger=logger),
        locator,
        principals,
    )


def test_the_service_and_the_hub_fake_meet_their_seams() -> None:
    grants, locator, _ = _grants()
    assert isinstance(grants, RunWebGrantsInterface)
    assert isinstance(locator, HubLocatorInterface)


def test_with_a_hub_the_run_gets_its_own_grant_minted_with_the_wall_clock(tmp_path: Path) -> None:
    grants, _, principals = _grants()
    access = grants.open(RUN, tmp_path)
    assert access.state == "hub" and access.hub_url == HUB
    assert access.token_file == tmp_path / "web-token"
    assert principals.minted == [(RUN, tmp_path, NOW)]


def test_the_default_clock_is_the_wall_clock(tmp_path: Path) -> None:
    import time

    principals = _Principals()
    before = time.time()
    RunWebGrants(hub=_Hub(HUB), principals=principals).open(RUN, tmp_path)
    assert before <= principals.minted[0][2] <= time.time()


def test_without_a_hub_nothing_is_minted_and_the_reason_is_fixed(tmp_path: Path) -> None:
    grants, _, principals = _grants(None)
    access = grants.open(RUN, tmp_path)
    assert access == RunWebAccess("none", reason=NO_HUB)
    assert access.token_file is None
    assert principals.minted == []
    assert list(tmp_path.iterdir()) == []


def test_a_run_without_a_folder_of_its_own_is_given_none_and_the_hub_is_not_asked() -> None:
    grants, locator, principals = _grants()
    assert grants.open(RUN, None) == RunWebAccess("none", reason=NO_RUN_FOLDER)
    assert locator.asked == 0 and principals.minted == []


@pytest.mark.parametrize(
    "error", [SessionGrantRefused("the folder already holds a token"), OSError("full")]
)
def test_a_grant_that_cannot_be_minted_is_logged_and_the_run_has_none(
    tmp_path: Path, error: Exception
) -> None:
    logger = _Logger()
    grants, _, principals = _grants(logger=logger)
    principals.mint_error = error
    assert grants.open(RUN, tmp_path) == RunWebAccess("none", reason=NO_TOKEN)
    assert logger.lines == [
        (
            "session_web_grant_refused",
            {"principal": f"session:{RUN}", "error": type(error).__name__},
        )
    ]


def test_a_refused_mint_with_no_logger_is_still_none(tmp_path: Path) -> None:
    grants, _, principals = _grants()
    principals.mint_error = OSError("full")
    assert grants.open(RUN, tmp_path).state == "none"


def test_close_revokes_the_grant(tmp_path: Path) -> None:
    grants, _, principals = _grants()
    access = grants.open(RUN, tmp_path)
    grants.close(access)
    assert principals.revoked == [access.grant]


def test_close_of_no_access_revokes_nothing() -> None:
    grants, _, principals = _grants()
    grants.close(RunWebAccess("none", reason=NO_HUB))
    assert principals.revoked == []


@pytest.mark.parametrize("error", [OSError("cannot write"), RuntimeError("bug")])
def test_a_revocation_that_fails_is_logged_and_never_raised(
    tmp_path: Path, error: Exception
) -> None:
    logger = _Logger()
    grants, _, principals = _grants(logger=logger)
    access = grants.open(RUN, tmp_path)
    principals.revoke_error = error
    grants.close(access)
    assert logger.lines == [
        (
            "session_web_revoke_failed",
            {"principal": f"session:{RUN}", "error": type(error).__name__},
        )
    ]


def test_a_failed_revocation_with_no_logger_is_still_swallowed(tmp_path: Path) -> None:
    grants, _, principals = _grants()
    access = grants.open(RUN, tmp_path)
    principals.revoke_error = OSError("cannot write")
    grants.close(access)


def test_an_interrupt_during_revocation_is_not_swallowed(tmp_path: Path) -> None:
    grants, _, principals = _grants()
    access = grants.open(RUN, tmp_path)
    principals.revoke_error = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        grants.close(access)


class _FixedToken:
    def token(self) -> str:
        return TOKEN


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
def test_the_real_token_is_one_0600_file_in_the_run_folder_and_nowhere_else(
    tmp_path: Path,
) -> None:
    """Minted through the real store and registry: the token's only copy is `<run>/web-token`,
    0600 in a 0700 folder; the registry holds its digest, and the access holds its path."""
    state, run = tmp_path / "hub-state", tmp_path / "run"
    state.mkdir(mode=0o700)
    run.mkdir(mode=0o700)
    principals = SessionWebPrincipals(
        tokens=_FixedToken(),
        files=SessionTokenStore(),
        registry=SessionRegistry(state),
        run_deadline=timedelta(hours=2),
    )
    grants = RunWebGrants(hub=_Hub(HUB), principals=principals, clock=lambda: NOW)
    access = grants.open(RUN, run)

    assert access.token_file == run / WEB_TOKEN_FILE
    assert stat.S_IMODE(os.stat(run / WEB_TOKEN_FILE).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(run).st_mode) == 0o700
    holding = [p for p in tmp_path.rglob("*") if p.is_file() and TOKEN in p.read_text()]
    assert holding == [run / WEB_TOKEN_FILE]
    assert TOKEN not in repr(access)
    assert principals.lookup(TOKEN, NOW) is not None

    grants.close(access)
    assert not (run / WEB_TOKEN_FILE).exists()
    assert principals.lookup(TOKEN, NOW) is None
