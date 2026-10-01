# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for changelog fragments (vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_gh.config import GhConfig


@dataclass(frozen=True)
class Fragment:
    """One changelog entry waiting to be folded in: `<slug>.<kind>.md` and what it says."""

    path: str
    slug: str
    kind: str
    text: str


@dataclass(frozen=True)
class ChangelogFinding:
    """One reason a pull request's changelog is refused: `where` names it for a person."""

    where: str
    problem: str


@runtime_checkable
class ChangelogInterface(Protocol):
    """Folds one-file-per-change fragments into a changelog, and checks a pull request's.

    Every pull request used to edit the same unreleased lines, so concurrent pull requests
    conflicted on every merge. A fragment is a new file no other change names, so it cannot
    conflict; the release folds them in once, under the headings their types name.
    """

    def fragment_problems(self, name: str, text: str, kinds: Sequence[str]) -> tuple[str, ...]:
        """Why a fragment file called `name` holding `text` is malformed; empty when it is
        not. `kinds` are the types a name may carry."""
        ...

    def fragments(self, root: Path, directory: str, kinds: Sequence[str]) -> tuple[Fragment, ...]:
        """Every fragment waiting in `directory` under `root`, ordered by name. Raises
        ValueError naming every malformed one, so nothing is folded from a bad set."""
        ...

    def unreleased_section(self, text: str, unreleased: str) -> str | None:
        """The body of the `## <unreleased>` section, normalised for comparison; None when
        the changelog has no such section."""
        ...

    def fold(
        self,
        text: str,
        unreleased: str,
        fragments: Sequence[Fragment],
        titles: Mapping[str, str],
    ) -> str:
        """`text` with each fragment appended under its type's heading in the unreleased
        section, creating the section or heading where absent, in `titles`' order, and
        never a second heading of the same name. Unchanged when there are no fragments."""
        ...

    def cut(self, text: str, unreleased: str, heading: str, version: str, released: date) -> str:
        """`text` with the unreleased section renamed to the version's heading (`heading`
        formatted with `version` and `released`) and a fresh, empty unreleased section
        above it. Unchanged when the version already has a section."""
        ...

    def assemble(self, cfg: GhConfig) -> tuple[str, ...]:
        """Fold every configured changelog's fragments in and delete them. Returns every
        path written or removed, repository-relative; empty when there was nothing."""
        ...

    def release(self, cfg: GhConfig, version: str, released: date) -> tuple[str, ...]:
        """`assemble`, then `cut` every versioned changelog for `version`. Returns every
        path written or removed, for the release commit to stage."""
        ...

    def ensure_label(self, cfg: GhConfig) -> bool:
        """Create the skip label, or bring an existing one up to date, so a person can apply
        it. False when the table is off or declares no label; raises RuntimeError when the
        forge refuses."""
        ...

    def check(
        self,
        cfg: GhConfig,
        base: str,
        head: str,
        labels: Sequence[str],
        checkout: Path | None = None,
    ) -> tuple[ChangelogFinding, ...]:
        """Every reason the change from `base` to `head` is refused: a required path
        changed with no fragment added and no skip label, a malformed fragment, or an
        unreleased section edited directly. Empty when it passes."""
        ...
