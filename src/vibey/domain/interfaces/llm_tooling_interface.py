# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for deciding which LLM-facing surfaces a client has (SP-ACP).

Mirrors `vibey/domain/llm_tooling.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.host_clients import HostClientSpec
    from vibey.domain.llm_tooling import ClientTooling, ToolingFinding


@runtime_checkable
class LlmToolingInterface(Protocol):
    def findings(self, spec: HostClientSpec, found: ClientTooling) -> tuple[ToolingFinding, ...]:
        """The client's four surfaces -- `acp-agent`, `mcp-server`, `skill`, `plugin`, in that
        order -- each present, missing (with the exact command or snippet that fixes it) or
        not applicable. Pure."""
        ...
