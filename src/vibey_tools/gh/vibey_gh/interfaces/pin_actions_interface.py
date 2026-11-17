# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for pinning every `uses:` reference to a commit SHA (vibey ADR-0016).

`vibey_gh.pin_actions` supplies the class. `ActionUse` is declared beside the port, as
`NightlyVerdict` is, so a test double needs nothing from the implementation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ActionUse:
    """One `uses:` reference that is not pinned to a commit: where it is, and what it names.

    `action` is `owner/repo` or `owner/repo/path` (a composite action in a subdirectory, or a
    reusable workflow such as `owner/repo/.github/workflows/x.yml`); `ref` is the tag, branch
    or other name after the `@`.
    """

    path: Path
    line: int
    action: str
    ref: str


@dataclass(frozen=True)
class PinnedUse:
    """One `uses:` reference already pinned to a commit: where it is, and what it stands for.

    `ref` is the name the trailing `# <ref>` comment gives (`v4`, `release/v1`), the thing a
    refresh asks the forge about; `None` when the line has no comment to read one from.
    """

    path: Path
    line: int
    action: str
    sha: str
    ref: str | None


@runtime_checkable
class PinActionsInterface(Protocol):
    """Finds every mutable `uses:` reference and rewrites it to the commit it names today.

    A tag or branch is a moving name, so a workflow that trusts one trusts whatever its
    owner publishes next. A commit SHA does not move. The tag stays beside it as a comment,
    so a person (or Dependabot) can still read, and bump, what the pin stands for.
    """

    def unpinned(self, text: str, path: Path) -> list[ActionUse]:
        """The `uses:` values in `text` whose ref is not a full 40-hex commit. Pure: no
        network, no file read. Only real `uses:` keys count; a `run:` block, a comment, a
        local `./` action and a `docker://` reference are not references to pin."""
        ...

    def rewrite(self, text: str, shas: Mapping[tuple[str, str], str]) -> str:
        """`text` with each unpinned `(action, ref)` found in `shas` rewritten to
        `action@<sha> # <ref>`, an existing trailing comment kept after it. Pure. A pinned
        reference, or one `shas` has no answer for, is left byte for byte as it was."""
        ...

    def resolve(self, action: str, ref: str) -> str:
        """The 40-hex commit `ref` names in `action`'s repository today, an annotated tag
        dereferenced to the commit it points at. Asks the forge. Raises `RuntimeError` when
        the ref does not resolve to a commit."""
        ...

    def run(self, paths: Sequence[Path], *, apply: bool) -> int:
        """Without `apply`: touch no network and no file, name every unpinned use, and return
        1 when there is one, else 0. With `apply`: resolve every unpinned use first and only
        then rewrite the files, so a ref that does not resolve leaves every file unchanged,
        says so, and returns 1."""
        ...

    def pinned(self, text: str, path: Path) -> list[PinnedUse]:
        """The `uses:` values in `text` already pinned to a full 40-hex commit, each with
        the ref its trailing comment names (`None` when there is none to read). Pure: no
        network, no file read. Local `./` actions, `docker://` references and `uses:` text in
        a `run:` block or a comment are not pins."""
        ...

    def restamp(self, text: str, shas: Mapping[tuple[str, str], str]) -> str:
        """`text` with each pinned `(action, ref)` found in `shas` moved to that commit when
        it differs, the `# <ref>` comment and everything else on the line left as it was.
        Pure. A pin `shas` has no answer for, or one already on the answer, is untouched."""
        ...

    def refresh(self, paths: Sequence[Path], *, write: bool) -> int:
        """Ask the forge what each pin's `# <ref>` names today and say which moved, as
        `path:line` with the old and new commit. With `write`, rewrite the stale pins; without
        it, touch no file (the freshness check). A pin that cannot be refreshed (no readable
        ref, a ref that does not resolve, a use that is not pinned) is listed as
        `path:line` and the run returns 1, never claiming a refresh it did not make; a
        pin that is stale in check mode also returns 1. Pins of held actions are reported and
        left alone. Idempotent."""
        ...

    def announce(self, paths: Sequence[Path]) -> int:
        """The freshness check for automation: look at every pin as `refresh` does with
        `write=False`, then keep ONE tracking issue open while a pin is stale or cannot be
        checked, and close it when none is. Returns 0 once that is done, 1 when the check or
        the issue could not be completed."""
        ...
