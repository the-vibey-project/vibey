# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/vibey_state_action.py` implements. Interfaces declare; they never consume.

The *state action* lets any GitHub workflow open the repository's synced state (ADR-0086) in
a database of its own, use it, and hand it back: the gate that says whether this run may
open it at all, the runner's own PostgreSQL, the state commands, and the three steps of the
composite action `.github/actions/vibey-state`.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol


class StateDeclarationError(ValueError):
    """`.github/vibey-state.toml` cannot be read as declared. The message names what is
    wrong: the file, the unknown key, or the value of the wrong type."""


class ProcessRunnerInterface(Protocol):
    """Runs one argument vector, never through a shell."""

    def run(
        self, argv: Sequence[str], env: Mapping[str, str], timeout_s: float
    ) -> tuple[int, str, str]:
        """Exit code, stdout, stderr. A timeout is exit 124 with the reason on stderr."""
        ...


class StateDeclarationInterface(Protocol):
    """The repository's `.github/vibey-state.toml`."""

    def public(self) -> bool:
        """Whether a public repository may open the state: `[state] public`, false when the
        file is absent. A file that cannot be read as declared raises
        `StateDeclarationError`, naming what is wrong."""
        ...


class StateGateInterface(Protocol):
    """Whether this run may open the synced state."""

    def decide(self) -> tuple[bool, str]:
        """Allowed, and a note for stderr when it is not. Allowed needs a key, and a private
        repository or a declaration that a public one may. Without a key nothing was asked
        for, and the note is empty. A broken declaration raises `StateDeclarationError`."""
        ...


class PostgresProvisionerInterface(Protocol):
    """Starts the runner's preinstalled PostgreSQL with the owner role the state uses."""

    def start(self) -> str:
        """Empty when the database answers; otherwise what went wrong, for stderr."""
        ...


class StateCommandsInterface(Protocol):
    """The vibey commands the state needs, each with an environment built for it alone."""

    def environment(self, app_url: str, owner_url: str, *, migrate: bool) -> dict[str, str]:
        """A vibey command's environment: the system basics and its DSN; the owner's DSN only
        for a migration."""
        ...

    def state_environment(self, owner_url: str) -> dict[str, str]:
        """A state command's environment: the system basics, `VIBEY_STATE_*`, the key, the
        repository, `gh`'s token and the owner's DSN."""
        ...

    def migrate(self, app_url: str, owner_url: str) -> str:
        """Migrate the database: empty when done, otherwise a note for stderr."""
        ...

    def run(self, argv: Sequence[str], owner_url: str) -> tuple[int, str, str]:
        """One `vibey state ...` command against the owner's DSN."""
        ...

    def write_back(self, state: Path, app_url: str, owner_url: str) -> tuple[int, str]:
        """A sealed export into an empty database, then synced with the branch: the exit
        code, and what was said."""
        ...


class StateActionInterface(Protocol):
    """The steps of `.github/actions/vibey-state`. Each returns the step's exit code."""

    def open(self) -> int:
        """Restore the state into a database for this job and tell later steps its DSNs."""
        ...

    def close(self, out: Path, *, push: bool) -> int:
        """Export the state, sealed, for a write job; or with `push`, sync it directly."""
        ...

    def write_back(self, state: Path) -> int:
        """Merge a sealed export with the branch and write it back."""
        ...
