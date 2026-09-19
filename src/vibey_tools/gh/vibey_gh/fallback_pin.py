# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which release `[install] pin_version` pins the managed workflows' fallback install to.

The promise the key makes is "install the exact release that rendered this file". It used
to be kept with `vibey_gh.__version__`, back when the tooling was its own distribution. It
is not one any more (ADR-0037): `vibey_gh` is a package inside `<fallback_package>`, and
`__version__` numbers the package (1.73.0), not any release an index can serve.

For a while that was taken to mean the release is unknowable outside the repository that
publishes it, so every adopter's pin was dropped and their workflows floated. The release
is knowable. When `vibey-gh` runs from an installed distribution, that distribution's own
metadata names it: `vibey-gh` from `vibey` 1.0.0 is running release 1.0.0 — the same fact
`importlib.metadata` already records for every installed package. Dropping it silently
turned a configuration key into a no-op on ten adopting repositories, against decision 5
of ADR-0037 ("`[install] pin_version` keeps its meaning") and sub-doctrine 12.c.

So the pin resolves, in order:

1. **The repository IS the fallback distribution.** It declares the release it
   publishes, and that wins: name and version are read from one `[project]` table in one
   parse, so the version cannot belong to a different distribution than the name just
   verified. This is the only case a version bump moves the pin.
2. **The running `vibey-gh` came from an installed `<fallback_package>` release.** Its
   installed version, provided three things hold: the distribution is the configured
   `fallback_package`, it was built rather than installed from a source tree, and its
   RECORD lists the very file that is running. A source tree — an editable workspace
   sync above all — carries the last release's number while its templates may be ahead
   of that release, so pinning to it would render a requirement whose templates do not
   match what it installs.
3. **Otherwise, floating** — which always resolves — with a notice saying why, because a
   key that silently does nothing is the defect this module exists to end.
"""

from __future__ import annotations

import json
import sys
import tomllib
from collections.abc import Sequence
from importlib.metadata import Distribution
from pathlib import Path

from vibey_gh.config import GhConfig
from vibey_gh.interfaces.fallback_pin_resolver_interface import (
    FallbackPin,
    FallbackPinResolverInterface,
)
from vibey_gh.interfaces.installed_distributions_interface import (
    InstalledDistributionsInterface,
)

# The running `vibey_gh`, as the file an installed distribution's RECORD would list.
RUNNING_PACKAGE = Path(__file__).with_name("__init__.py")


class InstalledDistributions(InstalledDistributionsInterface):
    """Answers from `importlib.metadata`, looking where the interpreter imports from.

    `search_path` is the list of directories searched. It defaults to `sys.path`, which
    is the only answer that describes the process actually running; a test hands it a
    directory holding exactly the metadata it means to state.

    Deliberately NOT `importlib.metadata.packages_distributions()`. That walks every
    distribution on the path (about a tenth of a second in this workspace's virtualenv)
    and can name several providers of one top-level package without saying which one was
    imported. The question here is narrower and has an exact answer: does THIS
    distribution's RECORD list the file that is running?
    """

    def __init__(self, search_path: Sequence[str] | None = None) -> None:
        self._search_path = list(sys.path if search_path is None else search_path)

    def _find(self, distribution: str) -> Distribution | None:
        found = Distribution.discover(name=distribution, path=self._search_path)
        return next(iter(found), None)

    def version(self, distribution: str) -> str | None:
        found = self._find(distribution)
        if found is None:
            return None
        return found.version or None

    def installed_from_source(self, distribution: str) -> bool:
        found = self._find(distribution)
        if found is None:
            return False
        raw = found.read_text("direct_url.json")
        if raw is None:
            return False  # installed from an index: the way a published release arrives
        try:
            origin = json.loads(raw)
        except json.JSONDecodeError:
            return True
        return not isinstance(origin, dict) or "dir_info" in origin or "vcs_info" in origin

    def installs(self, distribution: str, path: Path) -> bool:
        found = self._find(distribution)
        if found is None:
            return False
        target = path.resolve()
        return any(
            entry.parts[-2:] == target.parts[-2:]
            and Path(str(found.locate_file(entry))).resolve() == target
            for entry in found.files or ()
        )


class FallbackPinResolver(FallbackPinResolverInterface):
    """Resolves `[install] pin_version` in the order this module's docstring gives."""

    def __init__(
        self,
        distributions: InstalledDistributionsInterface | None = None,
        *,
        running: Path = RUNNING_PACKAGE,
    ) -> None:
        self._distributions = InstalledDistributions() if distributions is None else distributions
        self._running = running

    def resolve(self, cfg: GhConfig) -> FallbackPin:
        if not cfg.pin_version:
            return FallbackPin(None)
        declared = self._declared_release(cfg)
        if declared is not None:
            return FallbackPin(declared, from_repository=True)
        package = cfg.fallback_package
        installed = self._distributions.version(package)
        if installed is None:
            why = f"no `{package}` distribution is installed"
        elif self._distributions.installed_from_source(package):
            why = (
                f"`{package}` {installed} was installed from a source tree — editable, a"
                " local directory or a VCS checkout — which names no published release"
            )
        elif not self._distributions.installs(package, self._running):
            why = f"it was not installed by `{package}` {installed}"
        else:
            return FallbackPin(installed)
        return FallbackPin(
            None,
            notice=(
                f"[install] pin_version is set, but the running vibey-gh is not an installed"
                f" `{package}` release ({why}); the fallback install stays floating — run"
                " vibey-gh from a published release to pin it"
            ),
        )

    @staticmethod
    def _declared_release(cfg: GhConfig) -> str | None:
        """This repository's own `[project] version`, when it IS the fallback package."""
        try:
            data = tomllib.loads((cfg.root / "pyproject.toml").read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return None
        project = data.get("project")
        if not isinstance(project, dict) or project.get("name") != cfg.fallback_package:
            return None
        version = project.get("version")
        return str(version) if isinstance(version, str) and version else None
