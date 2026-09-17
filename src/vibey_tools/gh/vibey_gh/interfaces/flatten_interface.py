# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for rebuilding a branch as one commit on its base (vibey ADR-0016).

Deciding what the new commit will say and proving it is safe to move the ref are two
different jobs, and a caller must be able to do the first without the second: `--dry-run`
is not a flag threaded through a mutation, it is the plan on its own. So the contract is
two methods, and the plan is the thing they share.

`FlattenPlan` is imported for typing only. It is a frozen data record, the same standing
`vibey_gh.config`'s settings have in the marketplace seam: naming the shape a seam speaks
in is declaring, not consuming.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey_gh.config import GhConfig

if TYPE_CHECKING:
    from vibey_gh.flatten import FlattenPlan


@runtime_checkable
class FlattenerInterface(Protocol):
    """Rewrites a branch as a single commit carrying the whole range's content."""

    def plan(
        self,
        cfg: GhConfig,
        *,
        onto: str | None = None,
        message: str | None = None,
        orphan_comments: bool = False,
    ) -> FlattenPlan:
        """What the rewrite would be: the base, the range, the message, the credit, the cost.

        Reads the repository and the forge, and changes NEITHER — no fetch, no ref moved,
        no comment written. That is the whole reason this is a method of its own, so it is
        a promise and not a habit: the fetch the rewrite needs belongs to `flatten`, which
        means a plan is read against the base as this clone already has it.

        The refusals decidable before anything moves are raised here — a detached HEAD, a
        dirty tree, a protected branch, an empty range, a base the branch has not merged, a
        message that cannot be composed — so a caller that only plans has already been told
        no about those. The ones that depend on the rewrite itself belong to `flatten`.

        One more refusal is decidable here and is the reason for `orphan_comments`: the
        branch's open pull request has unresolved review threads, which are anchored to the
        commits about to be replaced and will be detached from the code they were about.
        Passing it proceeds anyway. When the forge cannot be asked at all, the plan carries
        WHY rather than an empty answer, because a check that did not happen must never
        reach a caller looking like one that passed.
        """
        ...

    def flatten(
        self,
        cfg: GhConfig,
        *,
        onto: str | None = None,
        message: str | None = None,
        push: bool = False,
        dry_run: bool = False,
        orphan_comments: bool = False,
    ) -> tuple[FlattenPlan, tuple[str, ...]]:
        """Perform the rewrite, returning the plan and the lines describing what happened.

        Fetches the base first, and refuses if that fetch fails: the ancestry guard `plan`
        applies is only as good as the ref it is asked about. Then plans, so every refusal
        `plan` makes arrives here too, and can raise three more of its own, none of them
        decidable earlier: the commit would not build, the built tree is not the branch's,
        or the branch moved between the two. `dry_run` reports and stops before any of them
        — and before the fetch too, so it changes nothing at all, reading the base as this
        clone already has it and saying so among the notes.

        The notes name what the rewrite costs beyond this repository: the review threads it
        orphans or the reason they could not be counted, and the issues and discussions
        whose timelines will point at commits that stop existing.

        The new commit's tree must equal the old HEAD's or the branch is not moved;
        `push` sends it with a lease pinned to what this clone last saw the remote holding
        and raises if that lease is refused or the push fails for any other reason — the
        local rewrite stands either way — and without it the exact push command is reported
        instead. The command reported is the command `push` runs, including whether it
        carries a lease at all: a branch the remote does not have yet is created without
        one, because there is no remote value to pin and a lease naming one cannot be met.
        Where it goes is the BRANCH's own upstream, or `origin` when it has none — never
        `onto`'s remote, which is only ever fetched from.
        """
        ...
