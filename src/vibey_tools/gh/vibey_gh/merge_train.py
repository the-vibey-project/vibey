# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The merge train: review every open pull request into the integration branch and merge
the ones that are ready.

"Ready" is mechanical, and deliberately not a judgement of the code — code review is a
human's job, and a branch ruleset's. This decides only whether a change may merge
UNATTENDED: not a draft, no conflicts, checks green, nobody has asked for changes.

Who may merge unattended is the other half. A pull request from the owner or one of their
own bots merges on a green build; from anyone else it additionally needs an approving
review, because "CI passed" is not a review and an outside change must not reach the
integration branch on a robot's say-so.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, cast

from vibey_gh import reconcile, versioning
from vibey_gh.config import GhConfig, normalise_actor
from vibey_gh.pr_automation import (
    BLOCKED_LABEL,
    EXHAUSTED_LABEL,
    EXTERNAL_REPAIR_LABEL,
    OWN_CHECKS,
    newest_per_name,
)
from vibey_gh.protected_paths import CHANGED_PATHS_KEY, LISTED_FILES_KEY, ProtectedPathsGuard

NEEDS_REVIEW_LABEL = "needs-human-review"
_PROTECTED_PATHS = ProtectedPathsGuard()
# The phrase the owner-notification comment is recognised by. Matching on our own text is
# what keeps the mention to once per pull request; see hold_for_review().
_NOTIFIED_MARKER = "awaiting your review"
# Both gates the split PR automation renders must be green before the train may merge: the
# scan gate from pr-evaluate.yml and the review gate from pr-review.yml. `PR automation /
# gate` is the pre-split spelling; a head that has it in its rollup is checked by name
# during the exact-head gate read, but only the two current gates count as passed.
GATES = ("PR evaluate / gate", "PR review / gate")


@dataclass
class Verdict:
    number: int
    title: str
    author: str
    reason: str | None  # None means ready to merge
    # True when the ONLY thing standing in the way is the owner's approval. A draft or a
    # failing build is the contributor's to fix and needs no notification; an outside
    # contribution that is green and simply unapproved is waiting on the owner, and
    # nobody finds out unless someone says so.
    held_for_review: bool = False
    # True when the obstacle is only that the head is conflicting or behind -- a state
    # the train can clear for itself by merging the integration branch forward, rather
    # than one that needs a person. Carried as a flag instead of re-read from `reason`,
    # because a caller matching on that sentence would break the moment it is reworded.
    restackable: bool = False

    @property
    def ready(self) -> bool:
        return self.reason is None


def _gh_json(*args: str) -> Any:
    """Parsed JSON from `gh`. Any, not object: the shape differs per subcommand and the
    callers below index into it."""
    r = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if r.returncode:
        raise RuntimeError(f"gh {' '.join(args)}: {r.stderr.strip()}")
    return json.loads(r.stdout or "null")


def _gh(*args: str) -> tuple[bool, str]:
    """Run `gh` and report whether it worked. Never raises: these are courtesy actions
    around a merge decision that has already been made, and failing to apply a label is
    not a reason to abandon the train."""
    r = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    return r.returncode == 0, (r.stdout or "") + (r.stderr or "")


def hold_for_review(verdict: Verdict, cfg: GhConfig, label: str = NEEDS_REVIEW_LABEL) -> None:
    """Label a held pull request and mention the owner, once.

    Once is the important part. Repeating the mention every week would train the owner to
    ignore it, which is the opposite of the point, so an existing notification is detected
    before another is posted.
    """
    number = str(verdict.number)
    if label:
        ok, _ = _gh("pr", "edit", number, "--add-label", label)
        if not ok:
            # The usual reason is that the label does not exist yet in this repository.
            _gh(
                "label",
                "create",
                label,
                "--color",
                "D93F0B",
                "--description",
                "Outside contribution awaiting the code owner",
            )
            _gh("pr", "edit", number, "--add-label", label)

    owner = cfg.owner
    if not owner:
        return
    ok, existing = _gh("pr", "view", number, "--json", "comments", "-q", ".comments[].body")
    if ok and _NOTIFIED_MARKER in existing:
        return
    _gh(
        "pr",
        "comment",
        number,
        "--body",
        f"@{owner} this pull request is green but comes from @{verdict.author}, who is not "
        f"on the merge train's trusted list, so it is **{_NOTIFIED_MARKER}** rather than "
        f"merging automatically. Approve it and the next train will take it.",
    )


def judge(pr: dict, cfg: GhConfig) -> Verdict:
    author = (pr.get("author") or {}).get("login", "")
    # Deduplicated the same way the gate deduplicates, and for the same reason: a rollup
    # carries every check run for the head, so a superseded run's CANCELLED jobs sit beside
    # the successful jobs that replaced them. Judging both would skip a pull request over
    # evidence the gate has already discarded.
    rollup = newest_per_name(pr.get("statusCheckRollup") or [])
    # The same exclusion set the gate uses, not just `gate`. A superseded PR-automation run
    # leaves CANCELLED check runs behind for every job it did not finish — `Resolve merge
    # conflicts`, `Mirror fork for safe repair`, `Repair failed scans or review findings`,
    # and the rest. Excluding only `gate` meant this counted its own leftovers as failures
    # and skipped a pull request the gate had already certified: "skipped — 7 check(s)
    # failing" beside a green `PR evaluate / gate` + `PR review / gate`, with nothing actually wrong.
    ignored = set(cfg.pr_automation.ignored_checks) | OWN_CHECKS
    policy_rollup = [check for check in rollup if check.get("name") not in ignored]
    review = pr.get("reviewDecision") or ""
    labels = {
        label.get("name", "") if isinstance(label, dict) else str(label)
        for label in pr.get("labels") or []
    }

    pending = [c for c in policy_rollup if c.get("status") not in (None, "COMPLETED")]
    failing = [
        c
        for c in policy_rollup
        if c.get("conclusion") not in (None, "SUCCESS", "NEUTRAL", "SKIPPED")
    ]

    reason = None
    held = False
    restackable = False
    if pr.get("isDraft"):
        reason = "draft"
    elif pr.get("mergeable") == "CONFLICTING":
        reason = f"conflicts with {cfg.integration_branch}"
        # Conflicting AS GITHUB COMPUTES IT, which is not the same question as whether
        # the merge conflicts. GitHub merges without this repository's `.gitattributes`,
        # so a path declared `merge=union` -- the changelog every branch appends to --
        # is called a conflict there and resolves here. Worth attempting before a person
        # is asked to: observed as nine open pull requests, each made unmergeable by the
        # one before it landing, every one of them clearing on a local merge.
        restackable = not pr.get("isCrossRepository", False)
    elif pr.get("mergeStateStatus") == "BEHIND":
        reason = "head branch is behind its target"
        restackable = not pr.get("isCrossRepository", False)
    elif labels & {BLOCKED_LABEL, EXHAUSTED_LABEL}:
        reason = "PR automation requires operator action"
    elif review == "CHANGES_REQUESTED":
        reason = "changes requested"
    elif pending:
        reason = f"{len(pending)} check(s) still running"
    elif failing:
        reason = f"{len(failing)} check(s) failing"
    else:
        trusted = {normalise_actor(a) for a in cfg.trusted_authors}
        if cfg.owner:
            trusted.add(normalise_actor(cfg.owner))
        automation_passed = all(
            any(
                c.get("name") == gate
                and c.get("status") == "COMPLETED"
                and c.get("conclusion") == "SUCCESS"
                for c in rollup
            )
            for gate in GATES
        )
        untrusted = normalise_actor(author) not in trusted or EXTERNAL_REPAIR_LABEL in labels
        if cfg.pr_automation.enabled and not automation_passed:
            reason = (
                "automated outside-author review has not passed"
                if untrusted
                else "PR automation gates have not passed"
            )
        elif untrusted and not cfg.pr_automation.enabled and review != "APPROVED":
            owner = cfg.owner or "the code owner"
            reason = f"from @{author} and not approved — needs {owner}'s review"
            held = True
        elif pr.get("baseRefName") == cfg.release_branch:
            # The merge-time re-derivation (#254): a promotion opened when everything
            # was bumped can gain bump-deriving merges before it merges, and the
            # release then publishes NOTHING (skip-existing) while looking green. The
            # merger re-asks the version question against the CURRENT head; owing a
            # bump means not ready, loudly, naming the exact release commit owed.
            head = str(pr.get("headRefOid") or "HEAD")
            owed, why = versioning.owed_at(cfg, f"origin/{cfg.release_branch}", head)
            if owed:
                reason = (
                    f"promotion owes `chore(release): {owed}` before it may merge —"
                    f" {why}; merging unbumped publishes nothing (see #254)"
                )

    # Last, so it is the reason given only when nothing else stands in the way: a pull
    # request touching a protected path is otherwise ready, and must still not merge
    # unattended -- `merge()` would fall back to `--admin` and bypass the code-owner review
    # the ruleset asks for. A promotion is exempt: everything it carries already merged
    # into the integration branch, where this same check held it for a human.
    promotion = (
        pr.get("baseRefName") == cfg.release_branch
        and pr.get("headRefName") == cfg.integration_branch
    )
    if reason is None and not promotion:
        reason = _PROTECTED_PATHS.refusal(pr, cfg.protected_paths)

    return Verdict(
        pr["number"],
        pr.get("title", ""),
        author,
        reason,
        held_for_review=held,
        restackable=restackable,
    )


_PR_FIELDS = (
    "number,title,state,isDraft,mergeable,mergeStateStatus,reviewDecision,"
    "statusCheckRollup,author,labels,headRefOid,headRefName,baseRefName,isCrossRepository,"
    # body: so the caller can see whether the squash commit will carry the Made-With
    # trailer, and supply one when it will not. A bot's pull request body never has it.
    "body,"
    # changedFiles: GitHub's own count, against which the protected-paths listing is
    # checked for truncation.
    "changedFiles"
)


def pull_request(number: int, cfg: GhConfig | None = None) -> dict:
    pr = cast(dict, _gh_json("pr", "view", str(number), "--json", _PR_FIELDS))
    _include_exact_head_gate(pr)
    if cfg is not None and cfg.protected_paths:
        _include_changed_paths(pr)
    return pr


def _include_changed_paths(pr: dict) -> None:
    """Every path the pull request changes, for `[merge_train] protected_paths`.

    Paginated REST, because `pr view --json files` is one GraphQL page of at most 100. Left
    absent when the listing fails or cannot be read, and `judge` then refuses the merge
    rather than assuming the files it never saw were clean.

    A module-level function, beside the `_include_exact_head_gate` it mirrors: this module
    is the merge train's functions and has not yet converged on classes (vibey ADR-0016,
    tenants converge module by module), and the decision itself lives in
    `ProtectedPathsGuard`, behind its interface.
    """
    run = subprocess.run(
        [
            "gh",
            "api",
            "--paginate",
            f"repos/{{owner}}/{{repo}}/pulls/{pr['number']}/files?per_page=100",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode:
        return
    try:
        paths, listed = _PROTECTED_PATHS.parse_listing(run.stdout)
    except (TypeError, ValueError):
        return
    pr[CHANGED_PATHS_KEY] = list(paths)
    pr[LISTED_FILES_KEY] = listed


def _include_exact_head_gate(pr: dict) -> None:
    """GitHub may omit a freshly API-created check from a PR rollup for a few seconds.

    The checks are already durable on the exact commit. Reading that authoritative endpoint
    closes the event-to-merge race without relaxing any gate: only completed successful
    checks with the exact required names are copied into the rollup.
    """
    rollup = pr.setdefault("statusCheckRollup", [])
    present = {item.get("name") for item in rollup}
    if all(gate in present for gate in GATES):
        return
    sha = str(pr.get("headRefOid") or "")
    if not sha:
        return
    repository = _gh_json("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    response = _gh_json("api", f"repos/{repository}/commits/{sha}/check-runs")
    for item in response.get("check_runs", []):
        name = item.get("name")
        if (
            name in GATES
            and item.get("status") == "completed"
            and item.get("conclusion") == "success"
        ):
            rollup.append({"name": name, "status": "COMPLETED", "conclusion": "SUCCESS"})


def open_pull_requests(cfg: GhConfig, number: int | None = None) -> list[dict]:
    if number is not None:
        return [pull_request(number, cfg)]
    numbers = _gh_json(
        "pr",
        "list",
        "--base",
        cfg.integration_branch,
        "--state",
        "open",
        "--json",
        "number",
        "--jq",
        "sort_by(.number)",
    )
    out: list[dict] = []
    for entry in numbers or []:
        out.append(pull_request(int(entry["number"]), cfg))
    return out


def method_for(pr: dict, cfg: GhConfig, default: str = "squash") -> str:
    return "rebase" if pr.get("baseRefName") == cfg.release_branch else default


def should_delete_head(pr: dict, cfg: GhConfig) -> bool:
    """Delete merged topic branches, never permanent or contributor-fork branches."""
    return reconcile.deletable(
        str(pr.get("headRefName") or ""), cfg, fork=bool(pr.get("isCrossRepository", False))
    )


def delete_head_branch(pr: dict) -> bool:
    """Best-effort deletion after a successful merge; never called for permanent refs."""
    repository = _gh_json("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    head = str(pr["headRefName"])
    ok, _ = _gh("api", f"repos/{repository}/git/refs/heads/{head}", "--method", "DELETE")
    return ok


def merge(
    number: int, method: str = "squash", squash_body: str | None = None
) -> tuple[bool, bool, str]:
    """(merged, bypassed, error). Plain merge first: it is refused while a ruleset's
    approving-review requirement is unmet — even for an admin's token, because bypassing
    is opt-in per call — so fall back to --admin, which succeeds only if the token really
    carries the admin role.

    `error` is the failing attempt's stderr, "" on success. It used to be discarded, and
    every failure surfaced as "the ruleset refused it" — which sent a real token-scope
    problem on a live repository into an hour of ruleset archaeology, because the one
    string that named the actual cause was captured and thrown away.

    `squash_body` replaces the squash commit body when given. The caller uses it to
    guarantee the Made-With trailer: a squash merge takes its body from the pull request,
    a bot's pull request body never carries the trailer, and the provenance check then
    rejects the very commit the train just created — observed as a promotion blocked by
    five trailer-less dependabot commits it could do nothing about.
    """
    # Never ask GitHub to delete the head branch. In particular, the promotion PR's head
    # is `develop`; deleting it after a develop -> main merge would destroy a permanent
    # branch even though the merge itself was correct.
    base = ["gh", "pr", "merge", str(number), f"--{method}"]
    if squash_body is not None and method == "squash":
        base += ["--body", squash_body]
    first = subprocess.run(base, capture_output=True, text=True, check=False)
    if first.returncode == 0:
        return True, False, ""
    second = subprocess.run(base + ["--admin"], capture_output=True, text=True, check=False)
    if second.returncode == 0:
        return True, True, ""
    detail = (second.stderr or second.stdout or first.stderr or first.stdout).strip()
    return False, True, " ".join(detail.split())[:300]
