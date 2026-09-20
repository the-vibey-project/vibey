# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam between everything vibey-gh decides and the forge it decides about (vibey
ADR-0016; #138).

Code above this seam asks forge-neutral questions and gets answers in the nouns of
`vibey_gh.forge`. An adapter below it turns each question into one forge's own call and
each answer back into those nouns. Nothing above the seam names a platform.

Every verb answers in one shape, `(value, problem)`, and the shape is the contract. It
comes from the clean-repo survey, which learned it the hard way: a forge that could not be
asked (no client installed, no credentials, a rate limit, an error envelope where a
listing belonged) must never read as a forge that answered "nothing". So `problem` is empty
exactly when the forge answered, and when it is not, `value` is empty and `problem` is one
sentence saying what went wrong. A caller that gets a problem knows it could not look, and
says so, rather than reporting that it looked and found nothing. No verb raises for any of
these; they are answers.

Only the verbs something already consumes are declared. A verb arrives with its first
caller (vibey-gh PR #186: never an interface without a consumer), so the adapter for a
new forge never has to implement a promise nobody has tested.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from vibey_gh.forge import (
    ChangeRequest,
    ForgeComment,
    ForgeIssue,
    ForgeRelease,
    ForgeReview,
)


@runtime_checkable
class ForgeAdapterInterface(Protocol):
    """One repository on one forge, asked about in forge-neutral terms."""

    def for_repository(self, repository: str) -> ForgeAdapterInterface:
        """Return the same adapter bound to the repository namespace it will call."""
        ...

    # --- Generic Walk (for snapshots) ---

    def list_artifacts(
        self,
        forge_class: str,
        since: str | None = None,
        page: int = 1,
        limit: int = 100,
    ) -> tuple[list[dict[str, Any]], str]:
        """A paginated listing of a forge-neutral artifact class, and a problem.

        The adapter handles the native listing and returns a list of raw JSON objects.
        The `since` filter is applied if the class supports it.
        """
        ...

    # --- Specific Verbs ---

    def open_change_request_heads(self, *, limit: int) -> tuple[frozenset[str], str]:
        """The head branch names of up to `limit` open change requests, and a problem."""
        ...

    def releases(self, *, limit: int) -> tuple[tuple[ForgeRelease, ...], str]:
        """Up to `limit` releases, drafts included and marked, and a problem."""
        ...

    def get_change_request(self, number: int) -> tuple[ChangeRequest | None, str]:
        """A change request by number, and a problem."""
        ...

    def get_issue(self, number: int) -> tuple[ForgeIssue | None, str]:
        """An issue by number, and a problem."""
        ...

    def get_issue_thread(self, number: int) -> tuple[tuple[ForgeComment, ...], str]:
        """The comments of an issue or change request, and a problem."""
        ...

    def get_reviews(self, number: int) -> tuple[tuple[ForgeReview, ...], str]:
        """The reviews of a change request, and a problem."""
        ...

    def get_check_results(self, head_sha: str) -> tuple[tuple[Any, ...], str]:
        """The check results for a commit, and a problem."""
        ...

    # --- Mutations ---

    def create_comment(self, number: int, body: str) -> tuple[ForgeComment | None, str]:
        """A new comment on an issue or change request, and a problem."""
        ...

    def update_change_request(
        self,
        number: int,
        title: str | None = None,
        body: str | None = None,
    ) -> tuple[ChangeRequest | None, str]:
        """Updates to a change request, and a problem."""
        ...

    def merge_change_request(
        self, number: int, method: str = "squash", admin: bool = False
    ) -> tuple[bool, str]:
        """Merges a change request, and a problem."""
        ...

    def create_release(
        self, tag: str, name: str, body: str, draft: bool = False
    ) -> tuple[ForgeRelease | None, str]:
        """A new release, and a problem."""
        ...

    def set_protected_ref(self, ref: str, protected: bool) -> tuple[bool, str]:
        """Sets the protection state of a ref, and a problem."""
        ...

    def get_protected_refs(self) -> tuple[frozenset[str], str]:
        """The set of protected ref names, and a problem."""
        ...
