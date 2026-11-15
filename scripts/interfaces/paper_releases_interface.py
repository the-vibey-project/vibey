# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/paper_releases.py` implements. Interfaces declare; they never consume.

A *release ledger* is the tracked, reviewable list of releases the paper's figures count. A
*tag reader* is the one place a forge's tags are read, and only to propose entries for that list.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class ReleaseLedgerInterface(Protocol):
    """The tracked list of releases: what each release was, and which family it belongs to."""

    def families(self) -> list[dict[str, str]]:
        """Each release family as `package`, `tag_prefix` and `version_file`, in file order."""
        ...

    def releases(self) -> list[dict[str, Any]]:
        """Every recorded release as `package`, `version`, `tag`, `commit` and `released`.

        `released` is a timezone-aware datetime. The list is sorted by it, then by tag.
        """
        ...

    def problems(self) -> list[str]:
        """Why the ledger is not well formed, one reason per line; empty when it is."""
        ...

    def record(self, release: dict[str, Any]) -> bool:
        """Append one release; False, changing nothing, when its tag is already recorded."""
        ...


class ReleaseTagReaderInterface(Protocol):
    """Reads release tags from a clone, so an entry can be proposed for the tracked ledger."""

    def read(self, tag_prefix: str, package: str) -> list[dict[str, Any]]:
        """Every tag under `tag_prefix` as a release: its tag, commit and creation instant."""
        ...


class ReleaseAuditorInterface(Protocol):
    """Says out loud when a release that exists has no entry in the ledger."""

    def released_version(self, family: dict[str, str]) -> str | None:
        """The version the release branch ships for `family`, or None when it cannot be read."""
        ...

    def unrecorded(self) -> list[str]:
        """One line per released version the ledger does not hold; empty when it holds all."""
        ...


class ReleaseCutoffInterface(Protocol):
    """Decides which recorded releases already existed when a revision was the tip."""

    def existed_at(self, release: dict[str, Any], revision: str, tip_time: datetime) -> bool:
        """Whether `release` was cut strictly before `revision`, which stood at `tip_time`."""
        ...
