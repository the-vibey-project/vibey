# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the dependency-advisory gate and its declared exceptions (vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Advisory:
    """One advisory as `npm audit --json` reports it against one package.

    `id` is the GitHub advisory id (`GHSA-...`) when the report's URL carries one, and the
    URL itself otherwise -- an advisory without a GHSA id can be reported, never excepted.
    """

    id: str
    package: str
    severity: str
    title: str
    url: str
    range: str


@dataclass(frozen=True)
class AdvisoryException:
    """One declared exception: a reviewed decision to accept one advisory, for one package,
    in one npm workspace, until a date.

    `reason` is the reachability evidence that justifies it; `retire_when` the condition
    that ends it early (a patched release, an upstream change); `upstream` links to where
    that condition is tracked.
    """

    advisory: str
    package: str
    workspace: str
    reason: str
    added: date
    expires: date
    retire_when: str
    upstream: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdvisoryVerdict:
    """What one workspace's audit came to.

    `blocking` holds every advisory at the audit level or worse with no exception in force;
    `excepted` every one an exception covers, with that exception; `expired` exceptions
    past their date; `stale` exceptions that matched nothing at the audit level; and
    `unexplained` every package the report puts at the level or worse with no advisory
    at that level behind it -- a report this gate cannot account for is refused, not
    passed. `covered` names packages at the level only through excepted advisories, so
    the output says why they are not blocking.
    """

    workspace: str
    blocking: tuple[Advisory, ...]
    excepted: tuple[tuple[Advisory, AdvisoryException], ...]
    expired: tuple[AdvisoryException, ...]
    stale: tuple[AdvisoryException, ...]
    unexplained: tuple[str, ...]
    covered: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Nothing blocking, expired, stale or unexplained."""
        return not (self.blocking or self.expired or self.stale or self.unexplained)


@runtime_checkable
class AdvisoryGateInterface(Protocol):
    """Gates a change on the advisories `npm audit` reports, less the declared exceptions.

    `npm audit --audit-level=high` has one answer to an advisory with no patched release:
    fail every pull request until one is published. This keeps that answer for everything
    nobody has decided about, and lets a reviewed, expiring exception stand for the rest --
    printed on every run, and refused the moment it expires, stops matching, or a patched
    release makes it unnecessary.
    """

    def exceptions(self, path: Path) -> tuple[AdvisoryException, ...]:
        """Every exception declared in `path`, validated. A missing file declares none.

        Raises `ValueError` naming the entry and the key on anything malformed.
        """
        ...

    def audit(self, workspace: Path) -> Mapping[str, Any]:
        """`npm audit --json` run in `workspace`, decoded.

        Raises `RuntimeError` when npm reports an error or prints something that is not an
        audit report: an audit that could not be read is one that never ran.
        """
        ...

    def verdict(
        self,
        report: Mapping[str, Any],
        *,
        workspace: str,
        exceptions: Sequence[AdvisoryException],
        audit_level: str,
        today: date,
    ) -> AdvisoryVerdict:
        """Judge one workspace's audit report against the exceptions declared for it."""
        ...

    def patched_version(self, advisory: str, package: str) -> str | None:
        """The first patched release of `package` the advisory database names, or `None`
        when it names none. Raises `RuntimeError` when the database cannot be read."""
        ...

    def run(self, workspaces: Sequence[str], audit_file: Path | None = None) -> int:
        """Audit each workspace, print every finding and every exception honoured, and
        return the exit status: 0 clean, 1 refused."""
        ...
