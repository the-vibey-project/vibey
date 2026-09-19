# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for asking what the running interpreter has installed (vibey ADR-0016).

`[install] pin_version` promises to pin the fallback install to the release that rendered
the file. Outside the repository that IS that distribution, the only witness to which
release that was is the installed distribution's own metadata. A test has to be able to
state that metadata exactly, whatever the virtualenv running the suite was installed
from — an editable workspace sync, a plain `pip install -e`, or a wheel — or the tests
would pass or fail depending on how somebody set up their machine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class InstalledDistributionsInterface(Protocol):
    """Answers questions about one installed distribution, by name."""

    def version(self, distribution: str) -> str | None:
        """The installed version of `distribution`, or `None` when it is not installed."""
        ...

    def installed_from_source(self, distribution: str) -> bool:
        """Whether `distribution` was installed from a source tree rather than a build.

        PEP 610's `direct_url.json` is the record. A local directory (`dir_info`, editable
        or not) or a VCS checkout (`vcs_info`) is a source tree, whose version field names
        the last release while its contents may be ahead of it. An index install (no
        record at all) or an archive (`archive_info`) is a build. A record that cannot be
        read counts as source: provenance nobody can read names no release.
        """
        ...

    def installs(self, distribution: str, path: Path) -> bool:
        """Whether `path` is a file `distribution` installed — its RECORD lists it."""
        ...
