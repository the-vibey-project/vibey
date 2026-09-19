# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for what a promotion pull request says about itself (vibey ADR-0016).

`vibey-gh promote` derives the version and the file count again on every run, but the
pull request that carries them is opened once and reused for as long as it stays open.
What a reviewer reads when deciding to approve a release is therefore only as current as
the last run that WROTE it. A reuse path that never wrote anything back left one pull
request advertising `0.8.0` and five files while it proposed a 178-file `1.0.0` (#235):
the derivation was right and nobody could see it.

So the words are a contract of their own: how they are rendered, how the version the
pull request was opened at is read back out of them, and how an open pull request is
brought up to date.

The promotion it speaks for is declared here too, as `PromotionInterface`, rather than
imported from `vibey_gh.promote`: that module reaches `vibey_gh.install` through
`versioning`, and a seam that imported it — even for typing — would consume the very
module the declare-only contract keeps out of this package.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class PromotionInterface(Protocol):
    """What a promotion's outcome (`vibey_gh.promote.Promotion`) offers its pull request."""

    changed_files: int
    version: str
    reason: str  # what the version derivation said
    released: str | None  # the release branch's version, or None when unreadable
    previous: str | None  # the version a reused pull request was opened at, if known

    def say(self, note: str) -> None:
        """Record one line of what the promotion did."""
        ...


@runtime_checkable
class PromotionPullRequestInterface(Protocol):
    """Renders, reads back, and refreshes the title and body of a promotion pull request."""

    def title(self, version: str) -> str:
        """The title for a promotion of `version` — the one spelling create and edit share."""
        ...

    def body(self, result: PromotionInterface) -> str:
        """The body for `result`, opening with a machine-readable record of its version.

        It says whether merging publishes anything, and it says so from the versions on
        both branches rather than as a caveat printed on every promotion. When the pull
        request was opened at a different version than it now carries, it says that too:
        the earlier number is how long the promotion has been open.
        """
        ...

    def recorded_version(self, title: str, body: str) -> str | None:
        """The version this pull request was opened at, or `None` when nothing states it.

        The body's own record comes first; a title in the `chore(release): <version>`
        form is the fallback, because a promotion opened before the record existed never
        had its title changed. Anything else is unknown, never guessed.
        """
        ...

    def read(self, number: int) -> tuple[str, str]:
        """`(title, body)` as the forge holds them now. Raises `RuntimeError` if unreadable."""
        ...

    def write(self, number: int, title: str, body: str) -> None:
        """Replace the title and body of `number`. Raises `RuntimeError` if it cannot."""
        ...

    def refresh(self, number: int, result: PromotionInterface) -> None:
        """Bring an open pull request's title and body up to `result`, noting the outcome.

        Records the version it was opened at on `result`. Sends nothing when the words
        are already current, and never raises: a pull request whose words could not be
        refreshed is still the promotion, so the failure is a note on `result`.
        """
        ...
