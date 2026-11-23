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
import socket
from collections.abc import Callable, Mapping
from pathlib import PurePath
from typing import Final

from vibey.application.acp.dto import SearxngOffer, SearxngPrepared
from vibey.domain.config import ConfigError
from vibey.domain.interfaces.searxng_interface import SearxngPlanInterface
from vibey.domain.searxng import SEARXNG_IMAGE, SearxngPlan, SearxngProvision
from vibey.infrastructure.searxng.container_runtime import (
    DAEMON_VARIABLES,
    RuntimeProblem,
    RuntimeRefusal,
)
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
from vibey.infrastructure.web.untrusted_text import UntrustedText

type Health = Callable[[str, str | None], str | None]
"""Why what answers at a URL is not (the expected) SearXNG, or None when it is."""
type Listening = Callable[[int], bool]
"""Whether anything accepts a connection on 127.0.0.1 at a port."""

OWN_URL_NAMES: Final = (SEARXNG_URL_ENV, "WEBSEARCH_SEARXNG_URL")
"""The variables by which the person says they run their own SearXNG."""
PROBE_SECONDS: Final = 5.0
"""One identity check's bound: the step polls it, so each poll is short."""
REMOTE_DAEMON: Final = ("DOCKER_HOST", "CONTAINER_HOST")
"""Variables that may name a daemon on another machine: install refuses one that is not a local
socket, since the unit at login never has them and would talk to another daemon."""
RUNTIME_GONE_REMEDY: Final = (
    "vibey keeps its SearXNG with the runtime it was installed with: put that runtime back, or "
    "run `vibey searxng uninstall --purge` and then `vibey searxng install` to use the one vibey "
    "finds now"
)
"""What to do when the runtime vibey recorded is not there any more (SP-ACP Task 11a)."""
RUNTIME_REFUSED_REMEDY: Final = (
    "vibey keeps its SearXNG with the runtime it was installed with, and no longer trusts it: "
    "fix it (writable by its owner alone, `chmod g-w,o-w`, in one of vibey's trusted folders), "
    "or stop the old container with it yourself, then run `vibey searxng uninstall --purge` and "
    "`vibey searxng install` to use the one vibey finds now"
)
"""What to do when the recorded runtime is there but refused: its old container may still run
and hold SearXNG's port, so a fresh install alone would collide with it (review 1 S-3)."""


class SearxngProvisioner:
    """Declared by `SearxngProvisionerInterface`. `health`, `listening` and `uid` are seams."""

    def __init__(
        self,
        runtime: ContainerRuntimeInterface,
        files: SearxngFilesInterface,
        *,
        label: Callable[[], str],
        environ: Mapping[str, str] = os.environ,
        health: Health | None = None,
        listening: Listening | None = None,
        plan: SearxngPlanInterface | None = None,
        image: str = SEARXNG_IMAGE,
        port: int = DEFAULT_SEARXNG_PORT,
        uid: Callable[[], int] = os.getuid,
    ) -> None:
        self._runtime = runtime
        self._files = files
        self._label = label
        self._environ = environ
        self._health: Health = health or self._identity
        self._listening: Listening = listening or self._connects
        self._plan = plan or SearxngPlan()
        self._image = image
        self._port = port
        self._uid = uid

    def offer(self) -> SearxngOffer:
        own = next((name for name in OWN_URL_NAMES if self._environ.get(name, "").strip()), None)
        record = self.installed()
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
            # The runtime an install or update would use, so the question names it.
            runtime=record.runtime if record is not None else self._runtime.find(),
            own_url=own,
            answering=answering,
            provisioned=record is not None,
            short=self._plan.short(self._image),
            port=self._port,
            disabled=self._files.disabled(),
            outdated=self._outdated(record),
        )

    def installed(self) -> SearxngProvision | None:
        """The record as installed, possibly by an earlier pin (to recognise its SearXNG and to
        update it, never to run it); None when there is none vibey can believe."""
        try:
            return self._checked_label(self._files.read_installed())
        except ValueError:
            return None

    def _outdated(self, record: SearxngProvision | None) -> str:
        """`old -> new` when the record names an image other than the pinned one, else ""."""
        if record is None or self._plan.pinned(record.image):
            return ""
        return f"{self._plan.digest_of(record.image)} -> {self._plan.short(self._image)}"

    def provisioned(self) -> bool:
        return self.record() is not None

    def record(self) -> SearxngProvision | None:
        """The person's record, or None when there is none vibey can believe."""
        try:
            return self._believed()
        except ValueError:
            return None

    def refusal(self) -> str:
        try:
            record = self._believed()
        except ValueError as exc:
            outdated = self._outdated(self.installed())
            if outdated:
                return (
                    f"a newer pinned image is available ({outdated}); `vibey searxng install` "
                    "updates it"
                )
            return UntrustedText.clean(str(exc))
        if record is None:
            return ""
        refusal = self._runtime.vet(record.runtime)
        return UntrustedText.clean(f"{refusal}; {self._remedy(refusal)}" if refusal else "")

    @staticmethod
    def _remedy(refusal: RuntimeRefusal) -> str:
        """The remedy for a recorded runtime `vet` refuses: one that is gone can only be put
        back or replaced; one that is there but refused may still run the old container. Told
        apart by the typed reason, never by the wording (SP-ACP Task 11b, review 2 N2-5)."""
        if refusal.reason is RuntimeProblem.GONE:
            return RUNTIME_GONE_REMEDY
        return RUNTIME_REFUSED_REMEDY

    def runtime_gone(self) -> bool:
        record = self.installed()
        if record is None:
            return False
        refusal = self._runtime.vet(record.runtime)
        return refusal is not None and refusal.reason is RuntimeProblem.GONE

    def _believed(self) -> SearxngProvision | None:
        """The record, checked in full: the label is never taken from it, only compared."""
        return self._checked_label(self._files.read())

    def _checked_label(self, record: SearxngProvision | None) -> SearxngProvision | None:
        if record is not None and record.label != self._label():
            raise ValueError(
                f"its label {record.label} is not this SearXNG's ({self._label()}), so vibey "
                "uses nothing in it; `vibey searxng install` writes it again"
            )
        return record

    def disabled(self) -> bool:
        return self._files.disabled()

    def disable(self) -> None:
        self._files.disable()

    def busy(self) -> str:
        if not self._listening(self._port):
            return ""
        # vibey's own instance is known by its marker: from the record as installed (an earlier
        # pin's included, so an update is never refused as "not vibey's"), else from settings.yml.
        record = self.installed()
        marker = record.marker if record is not None else self._files.settings_marker()
        why = self._health(f"http://127.0.0.1:{self._port}", marker)
        if why is None and marker is not None:
            return ""  # vibey's own, answering
        said = UntrustedText.clean(why or "a SearXNG that is not vibey's")
        return (
            f"something already listens on 127.0.0.1:{self._port} ({said}), so vibey installs "
            "no SearXNG there; stop it, or set VIBEY_SEARXNG_URL to the SearXNG you run"
        )

    def prepare(self) -> SearxngPrepared:
        remote = self._remote_daemon()
        if remote:
            return SearxngPrepared(False, remote)
        runtime, problem = self._install_runtime()
        if problem:
            return SearxngPrepared(False, problem)
        if runtime is None:
            return SearxngPrepared(
                False, "vibey found neither podman nor docker in its trusted folders"
            )
        name, short = PurePath(runtime).name, self._plan.short(self._image)
        try:
            pulled = self._runtime.pull(runtime, self._image)
        except ValueError as exc:
            return SearxngPrepared(False, str(exc))
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
        self._files.enable()
        ignored = [key for key in DAEMON_VARIABLES if self._environ.get(key, "").strip()]
        note = (
            f" {', '.join(ignored)} {'is' if len(ignored) == 1 else 'are'} ignored: vibey and its "
            "unit use the runtime's own default connection."
            if ignored
            else ""
        )
        return SearxngPrepared(
            True,
            f"Downloaded searxng/searxng@sha256:{short} with {name}, and wrote its settings in "
            f"{self._files.folder}.{note}",
        )

    def _install_runtime(self) -> tuple[str | None, str]:
        """The runtime an install or an update uses, and why it may not (SP-ACP Task 11a): the
        one vibey installed its SearXNG with (an earlier pin's record included), trust-checked
        again, so an update never moves it to another daemon; with no record, the one `find`
        chooses now."""
        record = self.installed()
        if record is None:
            return self._runtime.find(), ""
        refusal = self._runtime.vet(record.runtime)
        if refusal is not None:
            return record.runtime, UntrustedText.clean(f"{refusal}; {self._remedy(refusal)}")
        return record.runtime, ""

    def _remote_daemon(self) -> str:
        for key in REMOTE_DAEMON:
            value = self._environ.get(key, "").strip()
            if value and not value.startswith("unix://"):
                return (
                    f"{key} names a daemon that is not a local socket; vibey runs SearXNG only on "
                    f"this computer's own runtime, so unset {key} to install it"
                )
        return ""

    def answering(self) -> bool:
        record = self.installed()
        if record is None:
            return False
        return self._health(f"http://127.0.0.1:{record.port}", record.marker) is None

    def image_present(self) -> bool:
        """Whether the image vibey's record names is here (asks the runtime; downloads nothing)."""
        record = self.record()
        if record is None:
            return False
        try:
            return self._runtime.image_present(record.runtime, record.image)
        except ValueError:
            return False  # a runtime vibey will not run: `refusal` says why

    def remove_container(self) -> str:
        # The record as installed, an earlier pin's included: its container lives in the
        # runtime it names, not necessarily the one `find` would choose now.
        record = self.installed()
        runtime = record.runtime if record is not None else self._runtime.find()
        if runtime is None:
            return ""  # no runtime: no container of vibey's can be running
        try:
            removed = self._runtime.remove_container(runtime, self._uid())
        except ValueError as exc:
            return str(exc)
        return "" if removed.ok else removed.detail

    def purge(self) -> list[str]:
        """Remove the image vibey's record names and both files; what could not be removed."""
        problems: list[str] = []
        record = self.installed()  # an earlier pin's image is removed from where it was pulled
        if record is not None:
            try:
                removed = self._runtime.remove_image(record.runtime, record.image)
            except ValueError as exc:
                problems.append(f"the image was kept: {exc}")
            else:
                if not removed.ok:
                    problems.append(f"the image was kept: {removed.detail}")
        self._files.purge()
        return problems

    @staticmethod
    def _identity(url: str, marker: str | None) -> str | None:
        return SearxngBackend(url, timeout_seconds=PROBE_SECONDS, instance=marker).health()

    @staticmethod
    def _connects(port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                return True
        except OSError:
            return False
