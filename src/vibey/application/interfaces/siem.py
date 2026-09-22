# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The SIEM port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SiemPort(Protocol):
    """Common protocol for FOSS security event sinks (sovereign default: Wazuh).

    Events are audit-grade JSON documents: what happened, where, and when.
    Delivery is best-effort transport, never a job outcome: a sink that is
    down must not fail the work that produced the event.
    """

    async def send_event(self, index: str, event: dict[str, object]) -> None:
        """Ship one audit event to the named index/stream; transport errors raise."""
        ...
