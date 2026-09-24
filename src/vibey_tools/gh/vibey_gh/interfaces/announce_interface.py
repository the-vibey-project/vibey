# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams of `vibey-gh announce`: the changelog a docs deploy posts (vibey ADR-0016).

Four jobs, four contracts, so each can be tested without the others. Reading where the last
announcement stopped is a question for the forge; turning commits or release notes into a
few lines is pure text; delivering those lines is one HTTP request; and deciding which of
them a deploy says is the announcer's. A test hands the announcer a scripted history and a
recording poster and reads the message it would have sent: no network, no clock.

The records they speak in (`CommitRecord`, `CommitRange`, `Position`, `ChangeSet`,
`ReleaseNotes`, `Surface`, `AnnounceRequest`, `Announcement`) are frozen data from `vibey_gh.announce_records`,
imported for typing only: naming the shape a seam speaks in is declaring, not consuming.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey_gh.announce_records import (
        Announcement,
        AnnounceRequest,
        ChangeSet,
        CommitRange,
        CommitRecord,
        Position,
        ReleaseNotes,
        Surface,
    )


@runtime_checkable
class ReleaseHistoryInterface(Protocol):
    """Where the previous announcement stopped, and what was committed since (10.g).

    Every answer is a POSITION in the forge's data, a commit, never a time, together with a
    reason that is empty exactly when the answer is known. "Could not ask" is never
    reported as "nothing there".
    """

    def previous_position(self, branch: str, head: str) -> Position:
        """The release commit the last accepted announcement for `branch` covered.

        When it cannot be established, `Position.sha` is `None` with a sentence saying why,
        and `structural` separates a history that could not be READ (the watermark must not
        move) from one that was read and holds no usable position (re-anchor, and say so).
        """
        ...

    def compare(self, base: str, head: str) -> tuple[CommitRange | None, str]:
        """The commits in `base...head` as the forge compares them, or `None` and why."""
        ...

    def commit(self, sha: str) -> tuple[CommitRecord | None, str]:
        """One commit's full message, or `None` and why."""
        ...


@runtime_checkable
class ChangelogComposerInterface(Protocol):
    """Turns commits or a release's notes into a short, safe, bounded Discord message."""

    def from_commits(self, commits: Sequence[CommitRecord], unread: int = 0) -> ChangeSet:
        """Every commit classified: breaking, a named group, the other group, or noise.

        Noise is counted, not listed. `unread` is commits the range holds that were never
        read, carried so the message can count them rather than lose them.
        """
        ...

    def from_changelog(self, text: str, version: str) -> ReleaseNotes | None:
        """`version`'s section of a changelog as changes, or `None` when there is none."""
        ...

    def render(
        self,
        header: str,
        changes: ChangeSet,
        *,
        more_url: str = "",
        more_label: str = "",
        surfaces: Sequence[Surface] = (),
    ) -> Announcement:
        """The message: header, grouped lines, what was left out and a link to it, and the
        surface links. Never longer than `[announce] max_message_chars`, by construction,
        and never loses a breaking change without counting it by name."""
        ...

    @staticmethod
    def escape(text: str) -> str:
        """`text` as inert Discord content: no mention, link, markdown or control character
        in it can act. Every commit subject and changelog line passes through this."""
        ...


@runtime_checkable
class WebhookPosterInterface(Protocol):
    """Delivers one JSON payload to a webhook, and never raises."""

    def post(self, url: str, payload: Mapping[str, Any]) -> tuple[bool, str]:
        """Whether the webhook accepted it, and a detail that never contains `url`."""
        ...


@runtime_checkable
class AnnouncerInterface(Protocol):
    """Decides what a deploy announces, and announces it without ever failing the deploy."""

    def compose(self, request: AnnounceRequest) -> Announcement:
        """The message for `request`, read from the history and the repository."""
        ...

    def run(
        self,
        request: AnnounceRequest,
        webhook_url: str,
        *,
        dry_run: bool = False,
        github_output: str = "",
    ) -> int:
        """Post the announcement; the exit status, which is 0 whatever the webhook did.

        With no webhook it says so and passes; a webhook failure is a `::warning::`; the URL
        is printed nowhere; a commit already announced for its branch is not posted again.
        With `github_output`, `posted=true|false` and `position=known|unknown|reanchored`
        are appended to that file: the workflow's marker step records this run only when it
        posted and the position is not `unknown`.
        """
        ...
