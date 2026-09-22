# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory SIEM implementation of the SIEM port (ADR-0042)."""

from __future__ import annotations

from vibey.application.interfaces.siem import SiemPort


class InMemorySiem(SiemPort):
    """Faked event sink for testing and unconfigured local runs."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    async def send_event(self, index: str, event: dict[str, object]) -> None:
        self.events.append((index, dict(event)))
