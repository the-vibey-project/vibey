# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam between the workflow and pr-af running on a model the operator hosts.

`vibey_gh.pr_af_local` supplies the renderer; this declares only what a caller holds. pr-af
ships one model setting and an entrypoint that only knows OpenRouter, so a local model is a
compose override layered on the pinned checkout -- never a patch to third-party code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class PrAfLocalModelInterface(Protocol):
    """One local model, as pr-af's container reaches it."""

    @property
    def model(self) -> str:
        """The model id the local server knows, e.g. `gpt-oss:20b`."""
        ...

    @property
    def container_base_url(self) -> str:
        """The server's address as seen from inside the container, never a loopback."""
        ...

    def compose_override(self) -> str:
        """The `docker-compose.override.yml` text that points pr-af at this model."""
        ...

    def write_override(self, directory: Path) -> Path:
        """Write the override beside the pinned checkout's compose file and return its path."""
        ...
