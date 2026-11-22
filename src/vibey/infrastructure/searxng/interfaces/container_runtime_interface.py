# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the container runtime vibey drives for its SearXNG (ADR-0102).

Implemented by `infrastructure/searxng/container_runtime.py`. Every method but `find` and `vet`
runs fixed commands and blocks; a runtime that `vet` refuses, or an image other than the pinned
one, raises ValueError (its message cleaned) before anything runs.
Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.searxng.container_runtime import RuntimeOutcome


@runtime_checkable
class ContainerRuntimeInterface(Protocol):
    def find(self) -> str | None:
        """podman, else docker, found once in vibey's trusted folders (never the PATH), and only
        one that passes `vet`'s checks on its file; None when neither."""
        ...

    def vet(self, runtime: str) -> str:
        """Why `runtime` may not be run ("" when it may): not podman or docker in a trusted
        folder, a link leading outside them, not a regular executable, writable by anyone,
        someone else's, or not the one a fresh look finds."""
        ...

    def image_present(self, runtime: str, image: str) -> bool:
        """Whether the image is already here. Downloads nothing."""
        ...

    def pull(self, runtime: str, image: str) -> RuntimeOutcome:
        """Download the image, bounded by the install bound."""
        ...

    def remove_container(self, runtime: str, uid: int) -> RuntimeOutcome:
        """Remove `uid`'s container, running or not, only when its labels say vibey started it
        for `uid`; an absent one is removed already, and one without that label is left and
        said."""
        ...

    def remove_image(self, runtime: str, image: str) -> RuntimeOutcome:
        """Remove the image; an absent one is removed already."""
        ...
