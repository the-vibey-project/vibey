# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh approve-check`: the delegated approver's grant, enforced by code (12.f, 12.j).

Run as `python -m vibey_gh.approval_check` -- the form the delegated approver is granted, and
the only one it may use -- or as `vibey-gh approve-check`, a thin delegate kept for people.
The module form keeps `vibey_gh.cli` off the approver's trust path: everything it executes is
the transitive closure of this module's `vibey_gh` imports, and `forbidden_paths` covers all
of it (test_approve_check.py derives the closure and enforces that).

`[unattended_approval]` is the operator's grant to an agent that approves a change while they
are away (ADR-0049), and `authors` bounds whose change it may approve (ADR-0053). Until this
module, nothing in the tree read either: every condition of the grant was a sentence in the
approver's instructions, and a condition a model is asked to honour is a hope with a good track
record rather than a control. This is the control. It exits zero only when EVERY condition
holds, and otherwise prints each one that did not -- the refusals are reportable output (12.d),
and all of them are reported, never only the first.

The conditions, each a refusal when it does not hold or cannot be read:

1. **the grant is in force** -- `enabled = true` in the declared half, AND the live half, the
   repository variable `switch_variable` names, reads exactly `switch_value`. Absent, off,
   empty, malformed and unreadable are one answer: "I cannot tell" is refusal (12.f).
2. **the author is admitted** -- the pull request's author is in `authors`, expanded by
   `config.expand_authors` exactly as the grant documents (`@codeowners` becomes the logins
   `.github/CODEOWNERS` names; no CODEOWNERS is nobody). Bot logins compare the way the merge
   train compares them, `app/x` and `x[bot]` being one account.
3. **it lands where the grant reaches** -- the base branch matches a `branches` glob.
4. **it touches nothing forbidden** -- no changed file matches a `forbidden_paths` entry, and
   the WHOLE pull request is refused when one does; there is no safe subset. A listing that
   failed or came back shorter than GitHub's own count cannot rule a path out, so it refuses.
5. **the gates are green** (when `require_all_gates`) -- every current check on the head says
   COMPLETED with an explicit passing conclusion (a missing or null field is not a pass), every
   commit status says SUCCESS, and both of the merge train's `GATES` succeeded on it.
6. **the approving account wrote none of it** -- 12.f's load-bearing rule at the one level a
   machine can see: the account `gh` is authenticated as is neither the pull request's author
   nor an author of any of its commits; a commit author with no account login might be it, so
   that refuses too. Whether THIS SESSION wrote any of the diff is not
   visible to a command and stays with the approver.
7. **it is an open pull request, ready for review, at the head that was examined** -- and with
   `--head`, a head that has moved since is refused, so what was examined is what is approved.

With `--approve` (which requires `--head`), and only when every condition holds, the command
submits ONE approving review pinned to that head and confirms the forge recorded it. That is
the only write the delegated approver is granted: no `gh pr review`, which can also request
changes or comment, and no `gh api`, which reaches every write endpoint the token can.

Glob semantics for `forbidden_paths` are the merge train's (`ProtectedPathsGuard`: shell
globs, case-sensitive, over the whole root-relative path, `*` crossing `/`) PLUS the other
common reading of `**/`, where it also matches zero directories. The two readings disagree
about `**/x` at the root and `a/**/b` with nothing between; a forbidden list is a bound, so a
path either reading forbids is forbidden. The bound can only be wider for it, never narrower.

Reused rather than copied: the pull request is read by `merge_train.pull_request`, which
already reconciles the exact-head gates and lists the changed files through the paginated
REST endpoint; the gate names are `merge_train.GATES`; the check deduplication and the
automation's own exclusions are `pr_automation.newest_per_name` and `OWN_CHECKS` beside the
configured `ignored_checks`; matching is `ProtectedPathsGuard.touched`.
"""

from __future__ import annotations

import argparse
import dataclasses
import itertools
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any

from vibey_gh import merge_train
from vibey_gh.config import GhConfig, expand_authors, load_config, normalise_actor
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.approval_check_interface import (
    ApprovalCheckInterface,
    ApprovalVerdictInterface,
)
from vibey_gh.interfaces.forge_transport_interface import ForgeTransportInterface
from vibey_gh.interfaces.protected_paths_interface import ProtectedPathsInterface
from vibey_gh.pr_automation import OWN_CHECKS, newest_per_name
from vibey_gh.protected_paths import CHANGED_PATHS_KEY, LISTED_FILES_KEY, ProtectedPathsGuard

__all__ = ["DEFAULT_BODY", "ApprovalCheck", "ApprovalVerdict", "PullRequestReader"]

# How the pull request is read: `merge_train.pull_request`'s shape, so the default is that
# function and a test substitutes a table at this declared seam.
type PullRequestReader = Callable[[int, GhConfig], Mapping[str, Any]]

_PROG = "vibey-gh approve-check"
# How many forbidden paths a refusal names before summarising the rest.
_SHOWN = 3
# `gh pr view --json commits` reads one GraphQL page. A listing that reaches this length may
# have stopped short, and an author on the page it never read is an author all the same.
_COMMIT_PAGE = 100
# A commit status (not a check run) carries `state`; these two mean it has not finished.
_UNFINISHED_STATES = ("PENDING", "EXPECTED")
# A check run is green only when it says so twice over: an explicit COMPLETED status and one
# of these explicit conclusions -- the non-failing set the merge train accepts. A missing or
# null field is not a pass; it is a shape nobody can vouch for.
_PASSING_CONCLUSIONS = ("SUCCESS", "NEUTRAL", "SKIPPED")
_RUNNING_STATUSES = ("QUEUED", "IN_PROGRESS", "WAITING", "PENDING", "REQUESTED")
# The review body `--approve` submits when the approver supplies none.
DEFAULT_BODY = "Approved under [unattended_approval] after `vibey-gh approve-check` passed."


@dataclass(frozen=True)
class ApprovalVerdict:
    """Implements `ApprovalVerdictInterface`, structurally: the interface declares its fields
    as read-only properties, and a frozen dataclass inheriting them could not set its own."""

    number: int
    head: str
    refusals: tuple[str, ...]

    @property
    def granted(self) -> bool:
        return not self.refusals

    def report(self) -> str:
        at = self.head or "an unknown head"
        if not self.granted:
            lines = [f"{_PROG}: #{self.number} at {at}: REFUSED"]
            lines += [f"  - {reason}" for reason in self.refusals]
            return "\n".join(lines)
        return (
            f"{_PROG}: #{self.number} at {at}: every condition of [unattended_approval] holds.\n"
            f"  Approve with --head {self.head} --approve, which re-checks every condition and\n"
            "  submits nothing if any fails or the head has moved."
        )


class ApprovalCheck(ApprovalCheckInterface):
    """Implements `ApprovalCheckInterface`.

    Every collaborator is a declared seam: the configuration loader, the transport the
    switch, the approving identity and the commit authors are read through, the pull-request
    reader, and the path matcher. The defaults are the production ones.
    """

    def __init__(
        self,
        *,
        config: Callable[[], GhConfig] = load_config,
        transport: ForgeTransportInterface | None = None,
        reader: PullRequestReader | None = None,
        guard: ProtectedPathsInterface | None = None,
    ) -> None:
        self._config = config
        self._transport: ForgeTransportInterface = transport or GhTransport()
        self._reader: PullRequestReader = reader or self.read_pull_request
        self._guard: ProtectedPathsInterface = guard or ProtectedPathsGuard()

    @staticmethod
    def declare(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """Add the command's arguments to `parser`: one declaration for both entry points,
        `python -m vibey_gh.approval_check` and the `vibey-gh approve-check` delegate."""
        parser.add_argument("pr", type=int, help="the pull request to judge")
        parser.add_argument(
            "--head", metavar="SHA", help="refuse unless the head is exactly this commit"
        )
        parser.add_argument(
            "--approve",
            action="store_true",
            help="when every condition holds, submit one approving review pinned to --head; "
            "submit nothing otherwise",
        )
        parser.add_argument("--body", help="the approving review's body (with --approve)")
        return parser

    @classmethod
    def dispatch(cls, args: argparse.Namespace) -> int:
        """Run parsed arguments with the production collaborators; the exit status."""
        return cls().run(args.pr, args.head, args.approve, args.body)

    @classmethod
    def main(cls, argv: Sequence[str] | None = None) -> int:
        """`python -m vibey_gh.approval_check`: the approver's own entry point.

        It exists so that `vibey_gh.cli` is never on the approver's path. The CLI module is
        large, frequently changed, and not forbidden to the approver; had the approver run
        the check through it, an approvable change to `cli.py` could make the check say yes
        to anything. This entry point imports only the check's own closure, every module of
        which `forbidden_paths` covers (enforced by test_approve_check.py).
        """
        parser = argparse.ArgumentParser(
            prog="python -m vibey_gh.approval_check",
            description="Exit 0 only if every [unattended_approval] condition holds for a PR.",
        )
        return cls.dispatch(cls.declare(parser).parse_args(argv))

    @staticmethod
    def read_pull_request(number: int, cfg: GhConfig) -> Mapping[str, Any]:
        """The pull request as the merge train reads it, with its changed files listed.

        `merge_train.pull_request` lists the changed files exactly when the configuration it
        is handed names paths to guard, so it is handed the grant's `forbidden_paths` in that
        key -- the listing is then the train's own, paginated and truncation-counted, rather
        than a second copy of it here.
        """
        guarded = dataclasses.replace(cfg, protected_paths=cfg.unattended_approval.forbidden_paths)
        return merge_train.pull_request(number, guarded)

    def run(
        self,
        number: int,
        head: str | None = None,
        approve: bool = False,
        body: str | None = None,
    ) -> int:
        if approve and head is None:
            # Nothing is read and nothing is sent: an approval not pinned to the commit that
            # was examined could land on whatever the head became in the meantime.
            print(f"{_PROG}: #{number}: REFUSED\n  - --approve needs --head SHA", file=sys.stdout)
            return 1
        verdict, cfg = self._evaluate(number, head)
        print(verdict.report(), file=sys.stdout)
        if not verdict.granted or cfg is None:
            if approve:
                print(f"{_PROG}: no approval was submitted", file=sys.stdout)
            return 1
        if not approve:
            return 0
        return self._approve(cfg, number, verdict.head, DEFAULT_BODY if body is None else body)

    def _approve(self, cfg: GhConfig, number: int, head: str, body: str) -> int:
        """Submit ONE approving review, pinned to `head`, and confirm the forge recorded it.

        The only write this module makes, and reached only after every condition held. It
        goes through the same transport as every read; `survey` never raises and returns the
        forge's answer beside a problem sentence, which is exactly what confirming a write
        needs. `-f` sends each field as a raw string, so a body is never read as a file.
        """
        answer, problem = self._transport.survey(
            [
                "api",
                "-X",
                "POST",
                f"repos/{{owner}}/{{repo}}/pulls/{number}/reviews",
                "-f",
                "event=APPROVE",
                "-f",
                f"commit_id={head}",
                "-f",
                f"body={body}",
            ],
            cwd=cfg.root,
        )
        state = answer.get("state") if isinstance(answer, dict) else None
        if problem or state != "APPROVED":
            print(
                f"{_PROG}: the approval of #{number} at {head} was not recorded "
                f"({problem or f'the forge answered state {state!r}'})",
                file=sys.stdout,
            )
            return 1
        print(f"{_PROG}: approved #{number} at {head}", file=sys.stdout)
        return 0

    def evaluate(self, number: int, head: str | None = None) -> ApprovalVerdictInterface:
        return self._evaluate(number, head)[0]

    def _evaluate(self, number: int, head: str | None) -> tuple[ApprovalVerdict, GhConfig | None]:
        """The verdict, and the configuration it was judged under (None when unreadable)."""
        try:
            cfg = self._config()
        except Exception as exc:  # noqa: BLE001 -- any failure to read the grant is refusal
            refused = (f"grant: .vibey-gh.toml could not be read ({exc})",)
            return ApprovalVerdict(number, "", refused), None
        grant = cfg.unattended_approval
        refusals: list[str] = []
        if not grant.enabled:
            refusals.append("grant: [unattended_approval] enabled is false — no grant is in force")
        refusals += self._switch(cfg)
        try:
            pr = self._reader(number, cfg)
        except Exception as exc:  # noqa: BLE001 -- any failure to read the forge is refusal
            refusals.append(f"pull request: #{number} could not be read from the forge ({exc})")
            return ApprovalVerdict(number, "", tuple(refusals)), cfg
        actual = str(pr.get("headRefOid") or "")
        try:
            refusals += self._conditions(number, head, actual, pr, cfg)
        except Exception as exc:  # noqa: BLE001 -- the check never raises; unread is refused
            refusals.append(f"check: failed before every condition was read ({exc})")
        return ApprovalVerdict(number, actual, tuple(refusals)), cfg

    def _conditions(
        self,
        number: int,
        head: str | None,
        actual: str,
        pr: Mapping[str, Any],
        cfg: GhConfig,
    ) -> list[str]:
        grant = cfg.unattended_approval
        refusals = self._state(pr)
        if head is not None and head != actual:
            refusals.append(f"head: is {actual}, not the pinned {head}")
        refusals += self._author(pr, cfg)
        refusals += self._branch(pr, grant.branches)
        refusals += self._forbidden(pr, grant.forbidden_paths)
        if grant.require_all_gates:
            refusals += self._gates(pr, cfg)
        refusals += self._authorship(number, pr, cfg)
        return refusals

    # ------------------------------------------------------------------------ conditions

    def _switch(self, cfg: GhConfig) -> list[str]:
        grant = cfg.unattended_approval
        name = grant.switch_variable
        answer, problem = self._transport.survey(
            ["api", f"repos/{{owner}}/{{repo}}/actions/variables/{name}"], cwd=cfg.root
        )
        if problem:
            return [
                (
                    f"switch: repository variable {name} could not be read ({problem}) — "
                    "absence and unreadability are both refusal"
                )
            ]
        value = answer.get("value") if isinstance(answer, dict) else None
        if not isinstance(value, str):
            return [f"switch: repository variable {name} is malformed (no string value)"]
        if value != grant.switch_value:
            return [
                (
                    f"switch: repository variable {name} reads {value!r}, not exactly "
                    f"{grant.switch_value!r}"
                )
            ]
        return []

    def _state(self, pr: Mapping[str, Any]) -> list[str]:
        state = str(pr.get("state") or "")
        if state != "OPEN":
            return [f"pull request: is {state or 'in an unknown state'}, not open"]
        if pr.get("isDraft"):
            return ["pull request: is a draft"]
        return []

    def _author(self, pr: Mapping[str, Any], cfg: GhConfig) -> list[str]:
        try:
            expanded = expand_authors(cfg.unattended_approval.authors, cfg.root)
        except (OSError, UnicodeError) as exc:
            return [f"author: [unattended_approval] authors could not be expanded ({exc})"]
        admitted = {normalise_actor(login) for login in expanded}
        if not admitted:
            return ["author: [unattended_approval] authors expands to nobody"]
        author = _login(pr.get("author"))
        if normalise_actor(author) not in admitted:
            return [f"author: @{author} is not in [unattended_approval] authors"]
        return []

    def _branch(self, pr: Mapping[str, Any], branches: Sequence[str]) -> list[str]:
        base = str(pr.get("baseRefName") or "")
        if any(fnmatchcase(base, glob) for glob in branches):
            return []
        return [f"branch: base {base!r} matches no [unattended_approval] branches glob"]

    def _forbidden(self, pr: Mapping[str, Any], patterns: Sequence[str]) -> list[str]:
        paths = pr.get(CHANGED_PATHS_KEY)
        if paths is None:
            return ["forbidden path: the changed files could not be listed"]
        listed, total = pr.get(LISTED_FILES_KEY), pr.get("changedFiles")
        if not isinstance(listed, int) or not isinstance(total, int) or listed < total:
            return [f"forbidden path: GitHub listed {listed} of {total} changed files"]
        hits = self._guard.touched(_both_readings(patterns), paths)
        if not hits:
            return []
        shown = ", ".join(hits[:_SHOWN])
        if len(hits) > _SHOWN:
            shown += f" and {len(hits) - _SHOWN} more"
        return [f"forbidden path: touches {shown}"]

    def _gates(self, pr: Mapping[str, Any], cfg: GhConfig) -> list[str]:
        rollup = newest_per_name(pr.get("statusCheckRollup") or [])
        ignored = set(cfg.pr_automation.ignored_checks) | OWN_CHECKS
        running: list[str] = []
        failing: list[str] = []
        unreadable: list[str] = []
        for item in rollup:
            name = str(item.get("name") or item.get("context") or "unnamed check")
            if name in ignored:
                continue
            state = item.get("state")
            if state is not None:
                # A commit status: the merge train reads only check runs, and a red status
                # would pass unseen there. Here it counts, because a gate is a gate.
                if state in _UNFINISHED_STATES:
                    running.append(name)
                elif state != "SUCCESS":
                    failing.append(name)
            elif item.get("status") in _RUNNING_STATUSES:
                running.append(name)
            elif item.get("status") != "COMPLETED" or item.get("conclusion") is None:
                unreadable.append(name)
            elif item.get("conclusion") not in _PASSING_CONCLUSIONS:
                failing.append(name)
        missing = [
            gate
            for gate in merge_train.GATES
            if not any(
                item.get("name") == gate
                and item.get("status") == "COMPLETED"
                and item.get("conclusion") == "SUCCESS"
                for item in rollup
            )
        ]
        found: list[str] = []
        for label, names in (
            ("failing", failing),
            ("still running", running),
            ("of no provable result (no COMPLETED status or no conclusion)", unreadable),
            ("not green on this head", missing),
        ):
            if names:
                found.append(f"gates: {label} — {', '.join(sorted(names))}")
        return found

    def _authorship(self, number: int, pr: Mapping[str, Any], cfg: GhConfig) -> list[str]:
        unknown = "authorship: could not be established"
        who, problem = self._transport.survey(["api", "user"], cwd=cfg.root)
        approver = _login(who) if not problem else ""
        if not approver:
            return [f"{unknown} — the approving account is unreadable ({problem or 'no login'})"]
        mine = normalise_actor(approver)
        if normalise_actor(_login(pr.get("author"))) == mine:
            return [f"authorship: the approving account @{approver} is the pull request's author"]
        listing, problem = self._transport.survey(
            ["pr", "view", str(number), "--json", "commits"], cwd=cfg.root
        )
        commits = listing.get("commits") if isinstance(listing, dict) else None
        if problem or not isinstance(commits, list):
            return [f"{unknown} — the commits are unreadable ({problem or 'no commit list'})"]
        if len(commits) >= _COMMIT_PAGE:
            return [f"{unknown} — the commit listing may be truncated at {len(commits)}"]
        if not commits:
            return [f"{unknown} — the pull request lists no commits"]
        authors: list[str] = []
        for commit in commits:
            named = commit.get("authors") if isinstance(commit, dict) else None
            if not isinstance(named, list) or not named:
                return [f"{unknown} — a commit lists no authors"]
            logins = [_login(entry) for entry in named]
            if not all(logins):
                # An author GitHub could not tie to an account -- an unlinked co-author
                # trailer, say -- might be the approving account. Unprovable is refusal.
                return [f"{unknown} — a commit author has no account login"]
            authors += [normalise_actor(login) for login in logins]
        if mine in authors:
            return [
                (
                    f"authorship: the approving account @{approver} authored a commit in this "
                    "pull request"
                )
            ]
        return []


# Module-level rather than methods: both are pure helpers over plain values that no
# collaborator needs to substitute (vibey ADR-0016's last resort, reason stated as required).
def _login(value: Any) -> str:
    return str(value.get("login") or "") if isinstance(value, dict) else ""


def _both_readings(patterns: Iterable[str]) -> tuple[str, ...]:
    """Every pattern as written, plus every variant with some `**/` matching no directory."""
    out: list[str] = []
    for pattern in patterns:
        pieces = pattern.split("**/")
        for keep in itertools.product((True, False), repeat=len(pieces) - 1):
            variant = pieces[0] + "".join(
                ("**/" if kept else "") + piece for kept, piece in zip(keep, pieces[1:])
            )
            if variant not in out:
                out.append(variant)
    return tuple(out)


if __name__ == "__main__":
    raise SystemExit(ApprovalCheck.main())
