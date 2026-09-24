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

# A channel, or one path segment of a repository name: a plain name, nothing that steps out.
PLAIN_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
HEX_SHA = re.compile(r"^[0-9a-f]{7,40}$")

# What an announcement means for the watermark (sub-doctrine 10.g), written to `position=`
# for the workflow's marker step: KNOWN and REANCHORED are recorded, UNKNOWN never is.
KNOWN = "known"
UNKNOWN = "unknown"
REANCHORED = "reanchored"

# `git check-ref-format`'s refusals inside a name: a control character or space,
# `~ ^ : ? * [ \`, `..`, `@{`, and an empty component.
_REFNAME_FORBIDDEN = re.compile(r"[\x00-\x20\x7f~^:?*\[\\]|\.\.|@\{|//")


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
class Position:
    """Where the previous accepted announcement stopped, as a commit (10.g).

    `sha` is set exactly when the position is known. Otherwise `reason` says why, and
    `structural` says which kind of not-knowing it is. True: the history ANSWERED and holds
    no usable position (the first announcement ever, nothing accepted inside what the API
    will page through), so this run re-anchors, says so, and is recorded. False: the history
    could not be read, so nothing is recorded and the next run reads the same span again.
    """

    sha: str | None
    reason: str = ""
    structural: bool = False


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

    @staticmethod
    def refname(value: str) -> bool:
        """Whether git would accept `value` as a branch or tag name (12.c): `release/next`
        and `v/2.0.0` are names; a space, `..`, `:`, or a leading `-` or `/` is not."""
        return bool(
            value
            and not value.startswith(("-", "/", "."))
            and not value.endswith(("/", ".", ".lock"))
            and "/." not in value
            and ".lock/" not in value
            and value != "@"
            and not _REFNAME_FORBIDDEN.search(value)
        )

    def __post_init__(self) -> None:
        if not HEX_SHA.fullmatch(self.sha):
            raise ValueError(f"announce: --sha must be a hex commit id, not {self.sha!r}")
        parts = self.repository.split("/")
        if len(parts) != 2 or not all(PLAIN_REF.fullmatch(part) for part in parts):
            raise ValueError(f"announce: --repository must be owner/name: {self.repository!r}")
        if not PLAIN_REF.fullmatch(self.channel):
            raise ValueError(f"announce: --channel is not a plain name: {self.channel!r}")
        if not self.refname(self.branch):
            raise ValueError(f"announce: --branch is not a git branch name: {self.branch!r}")


@dataclass(frozen=True)
class Announcement:
    """The message, how much of it there is, and what it means for the watermark.

    `position` is KNOWN, UNKNOWN or REANCHORED (see `Position`). `duplicate` is set when this
    exact commit was already announced for this branch: identity, not time, makes a re-run
    or a replay a repeat, and a repeat is not posted again.
    """

    content: str
    listed: int = 0
    surfaces: int = 0
    position: str = KNOWN
    duplicate: bool = False
