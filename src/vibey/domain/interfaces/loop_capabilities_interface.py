# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam behind the `LoopCapabilitiesSnapshotted` payload (SP-LOOPS Phase 4, ruling R3).

Implemented by `domain/loop_capabilities.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from uuid import UUID


@runtime_checkable
class LoopCapabilitiesRecordInterface(Protocol):
    def payload(
        self,
        *,
        run_id: UUID,
        digest: str,
        plugins: int,
        skills: int,
        skills_skipped: int,
        mcp_local: int,
        mcp_remote: int,
        notices: int,
    ) -> dict[str, object]:
        """The event's payload: exactly `run_id`, `digest`, `plugins`, `skills`,
        `skills_skipped`, `mcp_local`, `mcp_remote` and `project_notices`. Pure. Raises
        `ValueError` for a digest that is not `sha256:` and 64 lower-case hex digits, or for a
        count that is negative or not an integer."""
        ...
