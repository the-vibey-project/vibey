# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts of `domain/backend.py`: which endpoint a run talks to, how that
endpoint is identified in run meta, and what the gateway is handed at runtime."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BackendIdentityInterface(Protocol):
    """Where a run's transcript lives. Compared, never inspected, by resume."""

    @property
    def kind(self) -> str:
        """``anthropic``, ``gateway`` or ``local``."""
        ...

    @property
    def url(self) -> str:
        """The normalised endpoint, empty for the default Anthropic endpoint."""
        ...

    @property
    def is_local(self) -> bool: ...

    def check_model(self, model: str) -> None: ...

    def check_server_tools(self) -> None: ...

    def resume_refusal(self, previous: BackendIdentityInterface | None) -> str | None:
        """Why this backend must not resume a session last run on ``previous``."""
        ...


@runtime_checkable
class BackendRuntimeInterface(Protocol):
    """A resolved profile, as the agent gateway and capacity probe consume it."""

    @property
    def cli_path(self) -> str | None: ...

    @property
    def pass_effort(self) -> bool: ...

    @property
    def cost_mode(self) -> str: ...

    @property
    def local(self) -> bool: ...

    @property
    def done_marker_fallback(self) -> bool: ...

    def environment(self) -> dict[str, str]:
        """The overlay applied on top of the inherited process environment."""
        ...


@runtime_checkable
class BackendProfileInterface(Protocol):
    """One validated ``[profiles.<name>]`` table."""

    @property
    def name(self) -> str: ...

    @property
    def base_url(self) -> str: ...

    @property
    def auth_token(self) -> str: ...

    @property
    def auth_token_env(self) -> str: ...

    @property
    def cli_path(self) -> str: ...

    @property
    def is_local(self) -> bool: ...

    @property
    def effective_cost_mode(self) -> str: ...

    def tier_models(self, *, low: str, medium: str, high: str) -> tuple[str, str, str]: ...

    def required_models(self) -> tuple[str, ...]: ...

    def check_model(self, model: str) -> None: ...

    def check_tools(self, *, web_search: bool, deep_research: bool) -> None: ...

    def identity(self, *, ambient_base_url: str = "") -> BackendIdentityInterface: ...

    def env_overlay(self, *, auth_token: str) -> dict[str, str]: ...

    def runtime(self, *, auth_token: str) -> BackendRuntimeInterface: ...
