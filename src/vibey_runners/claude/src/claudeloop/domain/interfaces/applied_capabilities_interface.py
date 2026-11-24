# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of `domain/capabilities.py`: what a run's locked capability snapshot gives one
session (SP-LOOPS Phase 4, Task 4)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class AppliedCapabilitiesInterface(Protocol):
    @property
    def digest(self) -> str: ...

    @property
    def plugin_dirs(self) -> tuple[str, ...]: ...

    @property
    def skills(self) -> tuple[str, ...]:
        """`plugin:skill` for each skill the snapshot's catalog enables."""
        ...

    @property
    def mcp_servers(self) -> Mapping[str, Mapping[str, object]]: ...

    @property
    def disallowed_tools(self) -> tuple[str, ...]: ...

    @property
    def add_dirs(self) -> tuple[str, ...]: ...

    @property
    def system_prompt_append(self) -> str: ...

    @property
    def notices(self) -> tuple[str, ...]: ...

    @property
    def instruction_files(self) -> tuple[str, ...]: ...

    def event_payload(self) -> dict[str, object]:
        """The `capabilities.applied` event: the digest, counts and names only."""
        ...
