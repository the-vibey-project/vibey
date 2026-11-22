# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for reading which LLM-facing surfaces each client has (SP-ACP).

Mirrors `vibey/infrastructure/mcp/llm_tooling_probe.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.host_clients import HostClientSpec
    from vibey.domain.llm_tooling import ToolingFinding


@runtime_checkable
class LlmToolingProbeInterface(Protocol):
    def detected(self) -> tuple[HostClientSpec, ...]:
        """The clients installed for this user: those whose own folder exists here."""
        ...

    def findings(self, client_ids: Sequence[str] | None = None) -> tuple[ToolingFinding, ...]:
        """Each named client's four surfaces (every detected client's when none is named),
        read from disk without writing anything and never through a link."""
        ...
