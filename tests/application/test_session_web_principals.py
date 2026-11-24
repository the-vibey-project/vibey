# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Minting, finding and revoking an engine session's web-only hub principal (SP-LOOPS Phase 6,
Task 2; R1, R4).

The token file and the registry are in-memory fakes here: the files' modes and the registry's
folder are `tests/infrastructure/hub/`'s. Tokens come from a fixed source, so nothing depends on
real randomness, and the clock is the `now` each call is given.
"""

from __future__ import annotations

import hashlib
import math
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from vibey.application.dto import SessionGrant
from vibey.application.interfaces.session_web_principals_interface import (
    SessionWebPrincipalsInterface,
)
from vibey.application.loop_capabilities_service import DEADLINE_MARGIN
from vibey.application.session_web_principals import SessionWebPrincipals
from vibey.domain.errors import SessionGrantRefused
from vibey.domain.hub_scope import HubScope
from vibey.domain.session_principal import SessionPrincipal

RUN = UUID("00000000-0000-4000-8000-000000000001")
OTHER_RUN = UUID("00000000-0000-4000-8000-000000000002")
TOKEN = "tok-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
SECOND = "tok-BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
DEADLINE = timedelta(hours=2)
NOW = 1_800_000_000.0
EXPIRES = NOW + (DEADLINE + DEADLINE_MARGIN).total_seconds()


class _Tokens:
    def __init__(self, *tokens: str) -> None:
        self._tokens = list(tokens)

    def token(self) -> str:
        return self._tokens.pop(0)


class _Files:
    def __init__(self) -> None:
        self.files: dict[Path, str] = {}
        self.stuck: set[Path] = set()

    def write(self, folder: Path, token: str) -> Path:
        path = folder / "web-token"
        if path in self.files:
            raise SessionGrantRefused(f"{path} already exists")
        self.files[path] = token
        return path

    def read(self, path: Path) -> str:
        return self.files[path]

    def remove(self, path: Path) -> bool:
        if path in self.stuck:
            return False
        self.files.pop(path, None)
        return True


class _Registry:
    def __init__(self) -> None:
        self.entries: dict[str, SessionPrincipal] = {}
        self.refuse_record = False
        self.refuse_forget = False

    def record(self, digest: str, principal: SessionPrincipal) -> None:
        if self.refuse_record:
            raise OSError("the registry folder is full")
        self.entries[digest] = principal

    def find(self, digest: str) -> SessionPrincipal | None:
        return self.entries.get(digest)

    def forget(self, digest: str) -> bool:
        if self.refuse_forget:
            raise OSError("the registry folder cannot be written")
        return self.entries.pop(digest, None) is not None


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


class _World:
    def __init__(self, *tokens: str, logger: _Logger | None = None) -> None:
        self.files = _Files()
        self.registry = _Registry()
        self.logger = logger
        self.service = SessionWebPrincipals(
            tokens=_Tokens(*(tokens or (TOKEN,))),
            files=self.files,
            registry=self.registry,
            run_deadline=DEADLINE,
            logger=logger,
        )


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def test_the_service_meets_its_declared_seam() -> None:
    assert isinstance(_World().service, SessionWebPrincipalsInterface)


def test_mint_writes_the_token_file_and_registers_only_its_digest(tmp_path: Path) -> None:
    world = _World()
    grant = world.service.mint(RUN, tmp_path, NOW)

    assert isinstance(grant, SessionGrant)
    assert grant.token_file == tmp_path / "web-token"
    assert world.files.files == {tmp_path / "web-token": TOKEN}
    assert grant.name == f"session:{RUN}"
    assert grant.run_id == RUN
    assert grant.expires_at == EXPIRES  # R4: the run deadline plus DEADLINE_MARGIN
    assert grant.principal.scopes == frozenset({HubScope.WEB})
    # The registry knows the token by its digest only: no key and no value is the token.
    assert world.registry.entries == {_digest(TOKEN): grant.principal}
    assert grant.digest == _digest(TOKEN)
    assert TOKEN not in repr(world.registry.entries)


def test_the_grant_repr_shows_neither_the_token_nor_its_digest(tmp_path: Path) -> None:
    grant = _World().service.mint(RUN, tmp_path, NOW)

    assert TOKEN not in repr(grant)
    assert _digest(TOKEN) not in repr(grant)
    assert f"session:{RUN}" in repr(grant)


def test_lookup_finds_the_principal_until_it_expires(tmp_path: Path) -> None:
    world = _World()
    grant = world.service.mint(RUN, tmp_path, NOW)

    assert world.service.lookup(TOKEN, NOW) == grant.principal
    assert world.service.lookup(TOKEN, EXPIRES - 0.001) == grant.principal
    assert world.service.lookup(TOKEN, EXPIRES) is None  # expiry is exclusive
    assert world.service.lookup(SECOND, NOW) is None  # never minted
    assert world.service.lookup("", NOW) is None


def test_revoke_deletes_the_file_and_makes_the_principal_unknown(tmp_path: Path) -> None:
    world = _World()
    grant = world.service.mint(RUN, tmp_path, NOW)

    world.service.revoke(grant)

    assert world.files.files == {}
    assert world.registry.entries == {}
    assert world.service.lookup(TOKEN, NOW) is None


def test_revoking_twice_is_harmless(tmp_path: Path) -> None:
    world = _World()
    grant = world.service.mint(RUN, tmp_path, NOW)
    world.service.revoke(grant)

    world.service.revoke(grant)  # a replayed job revokes again; nothing is left to remove

    assert world.files.files == {}
    assert world.registry.entries == {}


def test_a_second_mint_for_the_same_run_folder_refuses_and_keeps_the_first(
    tmp_path: Path,
) -> None:
    world = _World(TOKEN, SECOND)
    first = world.service.mint(RUN, tmp_path, NOW)

    with pytest.raises(SessionGrantRefused):
        world.service.mint(RUN, tmp_path, NOW)

    assert world.files.files == {tmp_path / "web-token": TOKEN}
    assert world.registry.entries == {_digest(TOKEN): first.principal}
    assert world.service.lookup(SECOND, NOW) is None


def test_two_runs_hold_two_principals(tmp_path: Path) -> None:
    world = _World(TOKEN, SECOND)
    a = world.service.mint(RUN, tmp_path / "a", NOW)
    b = world.service.mint(OTHER_RUN, tmp_path / "b", NOW)

    assert world.service.lookup(TOKEN, NOW) == a.principal
    assert world.service.lookup(SECOND, NOW) == b.principal
    world.service.revoke(a)
    assert world.service.lookup(TOKEN, NOW) is None
    assert world.service.lookup(SECOND, NOW) == b.principal


@pytest.mark.parametrize("now", [math.inf, -math.inf, math.nan])
def test_mint_with_a_now_that_is_not_an_instant_refuses_before_writing(
    tmp_path: Path, now: float
) -> None:
    world = _World()

    with pytest.raises(SessionGrantRefused, match="finite"):
        world.service.mint(RUN, tmp_path, now)

    assert world.files.files == {}
    assert world.registry.entries == {}


@pytest.mark.parametrize("bad", ["", "has space", "two\nlines", "tab\there", "naïve"])
def test_an_unusable_token_from_the_source_is_refused_without_naming_it(
    tmp_path: Path, bad: str
) -> None:
    world = _World(bad)

    with pytest.raises(SessionGrantRefused) as refused:
        world.service.mint(RUN, tmp_path, NOW)

    assert bad == "" or bad not in str(refused.value)
    assert world.files.files == {}
    assert world.registry.entries == {}


def test_a_registry_that_refuses_takes_the_token_file_with_it(tmp_path: Path) -> None:
    world = _World()
    world.registry.refuse_record = True

    with pytest.raises(OSError, match="full"):
        world.service.mint(RUN, tmp_path, NOW)

    assert world.files.files == {}  # nothing is left behind


def test_a_registry_that_cannot_forget_still_loses_the_file_and_raises(tmp_path: Path) -> None:
    world = _World()
    grant = world.service.mint(RUN, tmp_path, NOW)
    world.registry.refuse_forget = True

    with pytest.raises(OSError, match="cannot be written"):
        world.service.revoke(grant)

    assert world.files.files == {}


def test_a_token_file_that_cannot_be_removed_is_logged_by_path_never_by_token(
    tmp_path: Path,
) -> None:
    logger = _Logger()
    world = _World(logger=logger)
    grant = world.service.mint(RUN, tmp_path, NOW)
    world.files.stuck.add(grant.token_file)

    world.service.revoke(grant)

    assert world.registry.entries == {}  # the hub refuses it from now on, file or not
    assert logger.lines == [
        (
            "session_web_token_kept",
            {"principal": f"session:{RUN}", "token_file": str(grant.token_file)},
        )
    ]
    assert all(TOKEN not in repr(line) for line in logger.lines)
    assert all(_digest(TOKEN) not in repr(line) for line in logger.lines)


def test_without_a_logger_a_kept_token_file_is_silent(tmp_path: Path) -> None:
    world = _World()
    grant = world.service.mint(RUN, tmp_path, NOW)
    world.files.stuck.add(grant.token_file)

    world.service.revoke(grant)

    assert world.registry.entries == {}


@pytest.mark.parametrize("deadline", [timedelta(0), timedelta(seconds=-1)])
def test_a_run_deadline_that_is_not_positive_is_refused(deadline: timedelta) -> None:
    with pytest.raises(ValueError, match="deadline"):
        SessionWebPrincipals(
            tokens=_Tokens(TOKEN),
            files=_Files(),
            registry=_Registry(),
            run_deadline=deadline,
        )
