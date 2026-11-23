# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of the SearXNG vibey provisions, its pure half (ADR-0102).

Mirrors `vibey/domain/searxng.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.searxng import SearxngProvision


@runtime_checkable
class SearxngPlanInterface(Protocol):
    """What reaches a container runtime, and what vibey writes for its SearXNG. Pure. Every
    method raises ValueError, naming what is wrong, for a value vibey would not have made."""

    def check(self, provision: SearxngProvision) -> None:
        """Refuse a provision vibey would not have written."""
        ...

    def record(self, provision: SearxngProvision) -> dict[str, object]:
        """The provision as `provision.json` holds it."""
        ...

    def parse(self, data: object) -> SearxngProvision:
        """A provision read back from `provision.json`, checked in full: its image must be the
        one this vibey pins."""
        ...

    def parse_installed(self, data: object) -> SearxngProvision:
        """A provision checked in full but for the pin: a record of what an earlier vibey
        installed (any SearXNG digest), read to update it, never to run it."""
        ...

    def pinned(self, image: str) -> bool:
        """Whether `image` is the one this vibey pins."""
        ...

    def digest_of(self, image: str) -> str:
        """The first twelve digest digits of any SearXNG image reference (pinned or not)."""
        ...

    def container_name(self, uid: int) -> str:
        """The person's own container's name, `vibey-searxng-<uid>`."""
        ...

    def marker_in(self, settings_text: str) -> str | None:
        """The marker a `settings.yml` vibey wrote names in its `instance_name`; None when none."""
        ...

    def new_marker(self, hex32: str) -> str:
        """The identity marker made from 32 random lower-case hex digits."""
        ...

    def settings_text(self, *, secret_key: str, marker: str) -> str:
        """SearXNG's `settings.yml`: loopback-only, private, answering JSON, no telemetry."""
        ...

    def run_argv(
        self, provision: SearxngProvision, *, settings_path: str, uid: int, gid: int
    ) -> tuple[str, ...]:
        """The one command line that runs the container (`vibey searxng serve` execs it)."""
        ...

    def pull_argv(self, runtime: str, image: str) -> tuple[str, ...]:
        """Download the pinned image."""
        ...

    def image_argv(self, runtime: str, image: str) -> tuple[str, ...]:
        """Ask whether the image is present (exit 0 when it is); downloads nothing."""
        ...

    def labels_argv(self, runtime: str, uid: int) -> tuple[str, ...]:
        """Ask the labels of the container of `uid`'s name (exit non-zero when there is none)."""
        ...

    def remove_argv(self, runtime: str, uid: int) -> tuple[str, ...]:
        """Remove the container of `uid`'s name, running or not (only after its labels say it
        is vibey's own for that uid)."""
        ...

    def remove_image_argv(self, runtime: str, image: str) -> tuple[str, ...]:
        """Remove a SearXNG image named by its digest: the pinned one, or an earlier pin's
        after an update; never any other image."""
        ...

    def info_argv(self, runtime: str) -> tuple[str, ...]:
        """Ask whether the runtime answers (exit 0): a podman whose machine is stopped does not."""
        ...

    def context_argv(self, runtime: str) -> tuple[str, ...] | None:
        """For docker, print the endpoint of the CLI's current context; None for podman."""
        ...

    def short(self, image: str) -> str:
        """The first twelve hex digits of the image's digest, as it is said to a person."""
        ...
