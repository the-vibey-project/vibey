# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey acp` sets up on its own when an editor first connects (SP-ACP).

Implemented by `application/acp/acp_bootstrap.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.acp.dto import AcpSessionContext


@runtime_checkable
class AcpBootstrapInterface(Protocol):
    @property
    def done(self) -> bool:
        """True once nothing is left for this process to do: steps 1 to 3 finished healthy
        (or `[acp] auto_bootstrap` is off) and the PostgreSQL step is settled."""
        ...

    @property
    def steps_finished(self) -> bool:
        """True once the background steps (doctor, connect) have run to an end."""
        ...

    @property
    def healthy(self) -> bool:
        """True once a run of the background steps found no `FAIL`."""
        ...

    def start(self, session_id: str) -> None:
        """Schedule steps 1 to 3 as one task, after `session/new` has answered. A no-op when
        `[acp] auto_bootstrap` is off, while a run is going, or once one finished healthy."""
        ...

    async def before_first_prompt(self, context: AcpSessionContext) -> None:
        """Wait, once per session and within `[acp] bootstrap_timeout_seconds`, for a running
        bootstrap; then run the PostgreSQL step, once per process, in a mode that may run.
        Never raises for a failed step: the prompt always goes on."""
        ...
