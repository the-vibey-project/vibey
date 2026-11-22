# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ACP agent's port onto the local SearXNG vibey installs and runs (ADR-0102).

Implemented by `infrastructure/searxng/searxng_provisioner.py`, over the container runtime, the
SearXNG's files in the person's configuration folder and 9c's identity check. Every method
blocks (it reads files, runs a runtime or asks a SearXNG over loopback), so the caller runs it
off the event loop. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.acp.dto import SearxngOffer, SearxngPrepared
    from vibey.domain.searxng import SearxngProvision


@runtime_checkable
class SearxngProvisionerInterface(Protocol):
    def offer(self) -> SearxngOffer:
        """What is here now: a runtime, the person's own SearXNG, one answering, one vibey
        installed before. Read-only: it downloads, writes and runs nothing."""
        ...

    def provisioned(self) -> bool:
        """Whether vibey installed its SearXNG for this person (a record it can believe)."""
        ...

    def record(self) -> SearxngProvision | None:
        """The person's provision record, or None when there is none vibey can believe."""
        ...

    def image_present(self) -> bool:
        """Whether the image the record names is here. Asks the runtime; downloads nothing."""
        ...

    def prepare(self) -> SearxngPrepared:
        """Download the pinned image (bounded by `[acp] install_timeout_seconds`), then write
        the settings (once) and the provision record. Never raises for a runtime's refusal: the
        outcome says it."""
        ...

    def answering(self) -> bool:
        """Whether vibey's own SearXNG answers on loopback and proves it is (its marker)."""
        ...

    def remove_container(self) -> str:
        """Remove vibey's container: "" when it is gone (or was), else why not."""
        ...

    def purge(self) -> list[str]:
        """Remove the image the record names, the settings and the record; what was kept."""
        ...
