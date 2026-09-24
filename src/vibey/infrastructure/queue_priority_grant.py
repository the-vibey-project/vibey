# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where a queue-priority grant comes from, and who is asking (ADR-0054, 12.j).

The grant is read from the project's own reviewed configuration: `vibey.toml` at the
root of the repository the project record names -- the path `bootstrap` resolves for
the project's worker -- and nowhere else. Not the working directory, and not a path the
caller chooses: a grant a caller can point at is a grant the caller writes.

The operator is the account that owns that file (or, with no file, the repository
root): the process's uid against the file's owner, a check the operating system makes,
not a claim anyone types (SD-01 §2). The account's name comes from the password
database, never from `$USER`, which the caller sets for itself.
"""

import os
import pwd
from pathlib import Path
from typing import Final

from vibey.application.dto import ProjectRecord
from vibey.domain.config import ConfigError
from vibey.domain.queue_priority import Caller, PriorityGrant
from vibey.infrastructure.config_loader import QUEUE_CONFIG
from vibey.infrastructure.interfaces.class_contracts import QueueConfigLoaderInterface

CONFIG_NAME: Final = "vibey.toml"
"""The reviewed configuration's name at a project's repository root. The one place a
file name is fixed (12.h): a tool must find its configuration before it can read it."""


class ProjectPriorityGrantReader:
    """Reads a project's grant from `<repo_path>/vibey.toml`."""

    def __init__(self, loader: QueueConfigLoaderInterface = QUEUE_CONFIG) -> None:
        self._loader = loader

    def read(self, project: ProjectRecord) -> PriorityGrant:
        root = Path(project.repo_path)
        anchor = root / CONFIG_NAME
        owner = self._owner(anchor)
        if owner is None:
            owner = self._owner(root)
        declared = self._loader.load(anchor).priority.sources
        return PriorityGrant(declared, owner_uid=owner, anchor=str(anchor))

    @staticmethod
    def _owner(path: Path) -> int | None:
        """The uid owning `path`; None when nothing is there, which admits nobody. A
        path that is there and cannot be examined is an error, never "nobody": the
        grant is then unknown, and an unknown grant refuses (10.f)."""
        try:
            return path.stat().st_uid
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ConfigError(str(path), f"cannot be read: {exc}") from exc


class ProcessCaller:
    """The account this process runs as, from the operating system."""

    def current(self) -> Caller:
        uid = os.getuid()
        try:
            name = pwd.getpwuid(uid).pw_name
        except KeyError:
            name = f"uid-{uid}"
        return Caller(uid=uid, name=name)
