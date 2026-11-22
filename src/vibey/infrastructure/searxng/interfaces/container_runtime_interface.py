# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the container runtime vibey drives for its SearXNG (ADR-0102).

Implemented by `infrastructure/searxng/container_runtime.py`. Every method but `find` runs one
fixed command and blocks; a refused runtime or image raises ValueError before anything runs.
Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.searxng.container_runtime import RuntimeOutcome


@runtime_checkable
class ContainerRuntimeInterface(Protocol):
    def find(self) -> str | None:
        """podman, else docker, as an absolute path found on the PATH once; None when neither."""
        ...

    def image_present(self, runtime: str, image: str) -> bool:
        """Whether the image is already here. Downloads nothing."""
        ...

    def pull(self, runtime: str, image: str) -> RuntimeOutcome:
        """Download the image, bounded by the install bound."""
        ...

    def remove_container(self, runtime: str) -> RuntimeOutcome:
        """Remove vibey's container, running or not; an absent one is removed already."""
        ...

    def remove_image(self, runtime: str, image: str) -> RuntimeOutcome:
        """Remove the image; an absent one is removed already."""
        ...
