"""The contract of the krypton launcher (ADR-0016: an interface beside every class)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class KryptonLauncherInterface(ABC):
    """Starts the local vibey hub and opens it, or says plainly why it cannot."""

    @abstractmethod
    def launch(self, host: str, port: int, open_browser: bool) -> int:
        """Run the hub until it exits; return the process exit status."""
