# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for `vibey doctor`'s local sections as doctor probes (SP-ACP, ADR-0016).

Mirrors `vibey/cli/doctor_probes.py`. Interfaces declare; they never consume. The types the
seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from vibey.application.acp.dto import DoctorResult
    from vibey.cli.interfaces.doctor_output_interface import DoctorOutputInterface


@runtime_checkable
class LocalDoctorProbeInterface(Protocol):
    """One of doctor's local sections: a `DoctorProbeInterface` that can also print what it
    found the way `vibey doctor` always printed it."""

    name: str

    async def run(self) -> tuple[DoctorResult, ...]:
        """Run the section, capturing anything it prints; never writes to stdout."""
        ...

    def show(self, out: DoctorOutputInterface, results: Sequence[DoctorResult]) -> None:
        """Print `results` through `out` exactly as the section printed them."""
        ...


@runtime_checkable
class LocalDoctorProbesInterface(Protocol):
    """Builds doctor's local sections, in the order `vibey doctor` prints them."""

    def for_doctor(
        self,
        *,
        database_security: Callable[[], Awaitable[bool]],
        passwordless_reach: Callable[[], Awaitable[bool]],
        hub_exposure: Callable[[], bool],
        sabbath: Callable[[], tuple[list[str], bool]],
        gate_notices: Callable[[], Awaitable[str]],
        supervisor: Callable[[], tuple[list[str], bool]],
        host_health: Callable[[], tuple[list[str], bool]],
        ollama_enabled: Callable[[], bool],
        llm_tooling: Callable[[], tuple[list[str], bool]] | None = None,
        web_search: Callable[[], tuple[list[str], bool]] | None = None,
    ) -> tuple[LocalDoctorProbeInterface, ...]:
        """The sections `vibey doctor` runs, from the printing helpers it names; the web-search
        section after host health when `web_search` is given, and the LLM tooling section last,
        when `llm_tooling` is given."""
        ...

    def for_editor(self) -> tuple[LocalDoctorProbeInterface, ...]:
        """The same sections for `vibey acp`: nothing printed, the database read as lines, the
        web-search section, and the LLM tooling section last."""
        ...


@runtime_checkable
class LocalDatabaseDoctorInterface(Protocol):
    """`vibey doctor`'s two database sections (ADR-0055, sub-doctrine 10.j)."""

    async def security_lines(self) -> tuple[list[str], bool]:
        """The ledger guard and password-less access lines, and False when either failed."""
        ...

    async def security(self) -> bool:
        """Print `security_lines` and return its verdict."""
        ...

    async def passwordless_lines(self) -> tuple[list[str], bool]:
        """The `db-passwordless` line, and False on its FAIL."""
        ...

    async def passwordless(self) -> bool:
        """Print `passwordless_lines` and return its verdict."""
        ...
