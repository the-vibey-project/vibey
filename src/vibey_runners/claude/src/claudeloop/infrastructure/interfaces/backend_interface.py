# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts of `infrastructure/backend.py`: reading ``[profiles.<name>]``
tables, resolving a profile against the process environment, and reading back
which backend a session last ran on."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from claudeloop.domain.interfaces import (
    BackendIdentityInterface,
    BackendProfileInterface,
    BackendRuntimeInterface,
)


@runtime_checkable
class BackendProfileLoaderInterface(Protocol):
    def parse(self, table: object, *, source: str) -> Mapping[str, BackendProfileInterface]:
        """Every profile in one file's ``[profiles]`` table, validated."""
        ...

    def select(
        self, profiles: Mapping[str, BackendProfileInterface], name: str | None
    ) -> BackendProfileInterface:
        """The named profile, or the default Anthropic profile when none is named."""
        ...


@runtime_checkable
class BackendEnvironmentResolverInterface(Protocol):
    def auth_token(self, profile: BackendProfileInterface) -> str:
        """The token a local profile sends. Raises when ``auth_token_env`` is unset."""
        ...

    def try_auth_token(self, profile: BackendProfileInterface) -> str | None: ...

    def runtime(self, profile: BackendProfileInterface) -> BackendRuntimeInterface: ...

    def identity(self, profile: BackendProfileInterface) -> BackendIdentityInterface: ...


@runtime_checkable
class RunBackendHistoryInterface(Protocol):
    def last_backend(self, session_id: str) -> BackendIdentityInterface | None:
        """The backend a session's most recent recorded run used, if any recorded one."""
        ...
