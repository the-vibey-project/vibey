# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The frozen records `vibey-gh announce` speaks in, apart from the code that makes them.

They live here, and not in `vibey_gh.announce`, so the announce seams can name them without
reaching what the announcer imports: the transport, `flatten`, the version reader. An
interface declares; it never consumes, and import-linter's `vibey_gh interfaces declare
seams` contract holds that edge by edge. This module imports the standard library only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# A commit or tag named in an API path, or a channel or branch: nothing that could step out.
PLAIN_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
HEX_SHA = re.compile(r"^[0-9a-f]{7,40}$")


@dataclass(frozen=True)
class CommitRecord:
    """One commit: its identity and its whole message."""

    sha: str
    message: str


@dataclass(frozen=True)
class CommitRange:
    """`base...head` as the forge compared it. `total` counts every commit in the range,
    `commits` only those read, so `total - len(commits)` is what was never read."""

    status: str
    total: int
    commits: tuple[CommitRecord, ...]
    html_url: str


@dataclass(frozen=True)
class Change:
    """One announced line, its parts kept apart until they are rendered and escaped."""

    group: str
    word: str
    scope: str
    description: str
    reference: str = ""
    url: str = ""
    breaking: bool = False


@dataclass(frozen=True)
class ChangeSet:
    """The classified range: changes in display order, plus what is counted and not listed."""

    changes: tuple[Change, ...] = ()
    noise: int = 0
    unread: int = 0


@dataclass(frozen=True)
class ReleaseNotes:
    """A version's changelog section, and the version the section after it names."""

    changes: ChangeSet
    previous_version: str | None


@dataclass(frozen=True)
class Surface:
    """A published file the message links to."""

    label: str
    url: str


@dataclass(frozen=True)
class AnnounceRequest:
    """What a deploy published: the channel, the branch it came from, and its commit."""

    channel: str
    branch: str
    sha: str
    repository: str
    server_url: str = "https://github.com"
    site_dir: Path = Path("channel-site")
    version: str = ""

    def __post_init__(self) -> None:
        if not HEX_SHA.fullmatch(self.sha):
            raise ValueError(f"announce: --sha must be a hex commit id, not {self.sha!r}")
        parts = self.repository.split("/")
        if len(parts) != 2 or not all(PLAIN_REF.fullmatch(part) for part in parts):
            raise ValueError(f"announce: --repository must be owner/name: {self.repository!r}")
        for name in ("channel", "branch"):
            value = getattr(self, name)
            if not PLAIN_REF.fullmatch(value):
                raise ValueError(f"announce: --{name} is not a plain name: {value!r}")


@dataclass(frozen=True)
class Announcement:
    """The message, and how much of it there is, for the log line that reports the post."""

    content: str
    listed: int = 0
    surfaces: int = 0
