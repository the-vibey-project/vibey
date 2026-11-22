# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The local SearXNG vibey installs, as the ACP bootstrap and `vibey searxng` see it (ADR-0102).

- **`offer`** reads what is here and changes nothing: the runtime (`ContainerRuntime.find`),
  whether the person's environment names their own SearXNG (`VIBEY_SEARXNG_URL`, which they run
  themselves: vibey then installs nothing), whether a SearXNG already passes 9c's identity check
  (with the marker of vibey's record, or the person's `VIBEY_SEARXNG_INSTANCE`), and whether vibey
  installed one before.
- **`prepare`** pulls the pinned image (`SEARXNG_IMAGE`, never another) and writes the settings
  and the record in the person's configuration folder (`SearxngFiles`). The image, the port and
  the runtime are vibey's and the label is `[supervisor] label_prefix` from the person's own
  `vibey.toml`: nothing here comes from a project.
- **`answering`** is the identity check against vibey's own record: its loopback port, its marker.
  It is not authentication (ADR-0102): code running as the same person could bind the port while
  SearXNG is down, or read the marker.

Declared by `application/acp/interfaces/searxng_provisioner_interface.py`.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import PurePath
from typing import Final

from vibey.application.acp.dto import SearxngOffer, SearxngPrepared
from vibey.domain.config import ConfigError
from vibey.domain.interfaces.searxng_interface import SearxngPlanInterface
from vibey.domain.searxng import SEARXNG_IMAGE, SearxngPlan, SearxngProvision
from vibey.infrastructure.searxng.interfaces.container_runtime_interface import (
    ContainerRuntimeInterface,
)
from vibey.infrastructure.searxng.interfaces.searxng_files_interface import SearxngFilesInterface
from vibey.infrastructure.web.search import (
    DEFAULT_SEARXNG_PORT,
    SEARXNG_URL_ENV,
    SearxngBackend,
    WebSearchSettings,
)

type Health = Callable[[str, str | None], str | None]
"""Why what answers at a URL is not (the expected) SearXNG, or None when it is."""

OWN_URL_NAMES: Final = (SEARXNG_URL_ENV, "WEBSEARCH_SEARXNG_URL")
"""The variables by which the person says they run their own SearXNG."""
PROBE_SECONDS: Final = 5.0
"""One identity check's bound: the step polls it, so each poll is short."""


class SearxngProvisioner:
    """Declared by `SearxngProvisionerInterface`. `health` is the identity-check seam."""

    def __init__(
        self,
        runtime: ContainerRuntimeInterface,
        files: SearxngFilesInterface,
        *,
        label: Callable[[], str],
        environ: Mapping[str, str] = os.environ,
        health: Health | None = None,
        plan: SearxngPlanInterface | None = None,
        image: str = SEARXNG_IMAGE,
        port: int = DEFAULT_SEARXNG_PORT,
    ) -> None:
        self._runtime = runtime
        self._files = files
        self._label = label
        self._environ = environ
        self._health: Health = health or self._identity
        self._plan = plan or SearxngPlan()
        self._image = image
        self._port = port

    def offer(self) -> SearxngOffer:
        own = next((name for name in OWN_URL_NAMES if self._environ.get(name, "").strip()), None)
        record = self.record()
        answering = False
        if own is None:
            try:
                settings = WebSearchSettings.from_environment(
                    self._environ, provisioned=lambda: record
                )
            except ConfigError:
                answering = False  # a search setting vibey refuses: `vibey doctor` says which
            else:
                answering = self._health(settings.searxng_url, settings.searxng_instance) is None
        return SearxngOffer(
            runtime=self._runtime.find(),
            own_url=own,
            answering=answering,
            provisioned=record is not None,
            short=self._plan.short(self._image),
            port=self._port,
        )

    def provisioned(self) -> bool:
        return self.record() is not None

    def record(self) -> SearxngProvision | None:
        """The person's record, or None when there is none vibey can believe."""
        try:
            return self._files.read()
        except ValueError:
            return None

    def prepare(self) -> SearxngPrepared:
        runtime = self._runtime.find()
        if runtime is None:
            return SearxngPrepared(False, "vibey found neither podman nor docker on your PATH")
        name, short = PurePath(runtime).name, self._plan.short(self._image)
        pulled = self._runtime.pull(runtime, self._image)
        if not pulled.ok:
            return SearxngPrepared(
                False,
                f"`{name} pull` of searxng/searxng@sha256:{short} failed: {pulled.detail}",
                still_running=pulled.still_running,
            )
        try:
            self._files.ensure(
                image=self._image, port=self._port, label=self._label(), runtime=runtime
            )
        except (OSError, ValueError) as exc:
            return SearxngPrepared(False, f"its settings could not be written: {exc}")
        return SearxngPrepared(
            True,
            f"Downloaded searxng/searxng@sha256:{short} with {name}, and wrote its settings in "
            f"{self._files.folder}.",
        )

    def answering(self) -> bool:
        record = self.record()
        if record is None:
            return False
        return self._health(f"http://127.0.0.1:{record.port}", record.marker) is None

    def image_present(self) -> bool:
        """Whether the image vibey's record names is here (asks the runtime; downloads nothing)."""
        record = self.record()
        return record is not None and self._runtime.image_present(record.runtime, record.image)

    def remove_container(self) -> str:
        record = self.record()
        runtime = record.runtime if record is not None else self._runtime.find()
        if runtime is None:
            return ""  # no runtime: no container of vibey's can be running
        removed = self._runtime.remove_container(runtime)
        return "" if removed.ok else removed.detail

    def purge(self) -> list[str]:
        """Remove the image vibey's record names and both files; what could not be removed."""
        problems: list[str] = []
        record = self.record()
        if record is not None:
            removed = self._runtime.remove_image(record.runtime, record.image)
            if not removed.ok:
                problems.append(f"the image was kept: {removed.detail}")
        self._files.purge()
        return problems

    @staticmethod
    def _identity(url: str, marker: str | None) -> str | None:
        return SearxngBackend(url, timeout_seconds=PROBE_SECONDS, instance=marker).health()
