# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for Claude-domain values introduced by backend-capacity work."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class BackendMisconfiguredInterface(Protocol):
    @property
    def reason(self) -> str: ...

    @property
    def detail(self) -> str: ...

    def describe(self) -> str: ...


@runtime_checkable
class TurnSignalsInterface(Protocol):
    @property
    def rate_limit_status(self) -> str | None: ...

    @property
    def rate_limit_type(self) -> str | None: ...

    @property
    def resets_at(self) -> datetime | None: ...

    @property
    def utilization(self) -> float | None: ...

    @property
    def overage_status(self) -> str | None: ...

    @property
    def overage_resets_at(self) -> datetime | None: ...

    @property
    def overage_disabled_reason(self) -> str | None: ...

    @property
    def api_error_status(self) -> int | None: ...

    @property
    def assistant_error(self) -> str | None: ...

    @property
    def error_code(self) -> str | None: ...

    @property
    def disabled_reason(self) -> str | None: ...

    @property
    def can_purchase(self) -> bool | None: ...

    @property
    def result_text(self) -> str | None: ...

    @property
    def local_backend(self) -> bool: ...


@runtime_checkable
class BackendProfileErrorInterface(Protocol):
    @property
    def args(self) -> tuple[object, ...]: ...
