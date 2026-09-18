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

from typing import Protocol, runtime_checkable

from vibey_gh.forge import ForgeRelease


@runtime_checkable
class ForgeAdapterInterface(Protocol):
    """One repository on one forge, asked about in forge-neutral terms."""

    def open_change_request_heads(self, *, limit: int) -> tuple[frozenset[str], str]:
        """The head branch names of up to `limit` open change requests, and a problem.

        A head with no name, or a name that is not text, is left out rather than guessed
        at. The clean-repo survey reads this to keep a branch somebody is still working on
        out of every "merged, delete it" verdict, which is why a problem here must stop
        that verdict rather than let it run against an empty set.
        """
        ...

    def releases(self, *, limit: int) -> tuple[tuple[ForgeRelease, ...], str]:
        """Up to `limit` releases, drafts included and marked, and a problem.

        In the order the forge lists them. An entry the forge returned in a shape that is
        not a release is left out.
        """
        ...
