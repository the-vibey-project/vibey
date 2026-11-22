# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `tests/system/acp_stub_hub.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.dto import HumanGateRecord, ProjectRecord
    from vibey.domain.ledger import LedgerEvent


@runtime_checkable
class StubHubInterface(Protocol):
    """The hub `vibey acp` speaks to in the conformance test, scripted by a test: the hub's own
    app and services over in-memory stores, behind a loopback front that records what it was
    asked and counts requests without `<state_dir>/agent.token`. Every wait it offers is
    bounded and event-driven."""

    @property
    def port(self) -> int:
        """The loopback port it listens on (after `start`)."""
        ...

    def start(self) -> None:
        """Listen on 127.0.0.1, then write `agent.token` and `serving.json` the way
        `LocalTokenStore` reads them."""
        ...

    def stop(self) -> None:
        """Release anything held, stop serving and join the server thread."""
        ...

    def set_projects(self, projects: Sequence[ProjectRecord]) -> None:
        """The projects the hub holds (its documents render them as `vibey projects --json`)."""
        ...

    def append_ledger(self, event: LedgerEvent) -> None:
        """Add one event to its project's ledger; its `seq` must be the next one."""
        ...

    def set_gates(self, gates: Sequence[HumanGateRecord]) -> None:
        """The gates the hub holds (open while `answered_at` is None)."""
        ...

    def hold_chat(self) -> None:
        """Hold the next chat turns until `release_chat` (never longer than a bound below the
        agent's HTTP timeout, so the agent never falls back to `vibey hub start`)."""
        ...

    def release_chat(self) -> None:
        """Let held chat turns answer."""
        ...

    def wait_chat_held(self, timeout: float) -> bool:
        """Whether a chat turn arrived and is being held, within `timeout` seconds."""
        ...

    def refuse_sessions_under(self, cwd: str) -> None:
        """Answer a session create for exactly this folder with a 400 (a permanent refusal)."""
        ...

    def forge_session_event(self, session_id: str, kind: str, payload: Mapping[str, Any]) -> int:
        """Append the next event to a kept session's log through the hub's own route, as any
        holder of the agent's key could; returns its `seq`."""
        ...

    def session_events(self, session_id: str) -> tuple[tuple[int, str, Mapping[str, Any]], ...]:
        """The kept log of a session: `(seq, kind, payload)`, oldest first."""
        ...

    def wait_for_session_event(self, session_id: str, kind: str, timeout: float) -> bool:
        """Whether the session's kept log holds an event of `kind`, within `timeout` seconds."""
        ...

    @property
    def answers(self) -> tuple[tuple[str, Mapping[str, Any], str | None], ...]:
        """Every gate answer the agent sent: `(gate_id, answer, request_id)`, in order."""
        ...

    @property
    def requests(self) -> tuple[tuple[str, str], ...]:
        """Every request served: `(method, path)`, in order."""
        ...

    @property
    def unauthorised(self) -> int:
        """How many requests did not carry the agent token."""
        ...
