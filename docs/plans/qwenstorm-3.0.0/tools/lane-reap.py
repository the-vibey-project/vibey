"""Settle the lane ledger from evidence: what landed becomes integrated, what died is reaped.

    python3 lane-reap.py                    # report; change nothing
    python3 lane-reap.py --reap             # write both ledgers
    python3 lane-reap.py --reap-worktrees   # remove worktrees whose branch has landed
    python3 lane-reap.py --sync-issues      # make the tracker agree with the ledger
    python3 lane-reap.py --reap --grace 0   # without the repair grace period

Each verb is its own flag, and none implies another. They differ in what undoes them: a
ledger line is deleted, a worktree is `git worktree add`ed again, and a closed issue with a
comment on it has already been mailed to everyone watching. A pass with no flags reports all
three and writes nothing, which is what the scheduled job runs.

THE HOLE THIS FILLS
-------------------
`integrated.txt` and `abandoned.txt` had six readers and no writer. `lane-publish.py`,
`lane-refresh.py`, `lane-repair.py`, `lane-verify.py`, `storm-snapshot.py` and
`storm-queue.sh` all ask them whether a lane is settled; nothing in the toolchain could ever
make either answer yes. `file-suite.py` says so outright -- "until a human does the operator
lane and appends its slug there by hand". A ledger with a read side and no write side is
sub-doctrine 12.e's half-automation exactly: it depends on somebody remembering the step it
did not cover, and it is worse than none at all because every reader believes it.

Measured on 2026-09-23, before this existed, over 31 lanes and a 594-lane queue:

  - 4 lanes had MERGED pull requests -- #1044, #1053, #1054, #1055 -- and not one was in
    `integrated.txt`. Their work was in `develop`, and every lane that depended on them was
    still waiting for them, because eligibility is decided by the ledger and the ledger had
    never heard of them.
  - 13 lanes carried the runner's verdict of `completed: false` and none was in
    `abandoned.txt`. 190 queued lanes -- 32% of the queue -- depended transitively on one.
    Those 190 were not even reported blocked: `storm-queue.sh` prints `blocked` only when a
    dependency is IN `abandoned.txt`, so with the file empty they failed the eligibility
    test on every pass and were skipped in silence. The storm looked like it was working
    through 594 lanes. A third of them were dark.

THE RUNNER'S VERDICT IS NOT A VERDICT ON THE WORK
-------------------------------------------------
The first draft of this reaped every `completed: false` lane, and it was wrong about one of
the thirteen. `split-332-1-transport-seams` says `completed: false` -- the model did give up
-- and its pull request #1055 is MERGED, because a person picked the lane up afterwards and
finished it. `completed` is the runner's report on its OWN effort, never a statement about
whether the lane's work reached `develop`.

Reaping it would have been wrong twice: it would have filed a success as an abandonment, and
because abandonment cascades, it would have marked all 190 dependents blocked on a
dependency that had in fact succeeded. So the forge is consulted first and outranks the
runner's verdict, for the same reason 10.f gives -- a claim names its source, and "GitHub
reports this pull request merged" is a better source for "did this land" than a note the
runner wrote about itself hours earlier.

WHY A MACHINE MAY DO THIS UNATTENDED
------------------------------------
Settling a lane sounds like a judgement, and 12.d is clear that unattended authority covers
the judgement the work actually requires and not an inch more. This requires none. Both
inputs are somebody else's finding -- the forge's merge state, and what `qwenlane.py` wrote
after exhausting `--max-attempts`. Copying findings into the ledger that six tools read is
bookkeeping, not authorship, which is the distinction 12.d draws between adding the import
the file next door already uses and supplying the definition it was meant to find.

It is also reversible in the only way that matters: un-settling a lane is deleting a line.
That is why this records and does not delete.

WHAT IT WILL NOT DO
-------------------
It does not remove a lane directory, even a reaped one. Lanes hold uncommitted work --
`lane-refresh.py` stashes and restores it precisely because the runner does not commit for
the model -- so removing the directory would destroy the only copy. Recording alone already
stops the waste: every other tool skips a settled lane, so a settled lane costs nothing
further whether or not its files remain. Disk is cheap; the invisibility was expensive.

`--reap-worktrees` is a different thing and safe for a different reason, set out on
`worktrees()`: it removes a git worktree whose branch has ALREADY LANDED and which holds
nothing uncommitted, so no state in it exists only there.

It does not touch a lane a runner is inside, a lane already settled, a lane with an OPEN
pull request (its own branch's, or any whose body closes its issue), or a `completed: true`
lane with no pull request yet -- that last one is the publish backlog and belongs to
`lane-publish.py`. It reports a lane with no verdict at all and leaves it alone: that is a
lane killed mid-run, and whether its work is worth keeping is a question for a person.

It does not reap a REFUSED lane -- one whose `result.json` carries a `refused` reason because
its issue failed the provenance check (12.j) and the runner declined to start it. Nothing
gave up, so "abandoned" would be false; and an issue the storm declined to trust is not one
to comment on. It is reported in its own bucket, left unsettled, and its queued dependants
are named on every pass, so they are held visibly rather than skipped in silence.

It does NOT confirm that `lane-publish.py` evaluated a lane in the same pass before reaping
it. `storm-cycle.py` runs publish first and reap second, and that ordering is the whole of
the guarantee: a pass in which publish failed or was skipped is not detected here.
"""

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import storm_forge
import storm_paths

# The storm root is the one location that cannot come from configuration -- it is where the
# configuration lives. `storm_paths.storm` derives it, spelling out the `.absolute()` that
# keeps `tools/`'s symlink unfollowed; resolving it would address the planning worktree,
# which has no lanes/, and this would report "0 lanes, nothing to do" from a tree it was
# never looking at.
STORM = storm_paths.storm(__file__)
LANES = STORM / "lanes"

# Declared in storm.toml, derived from the tree when it is silent -- never a literal in this
# file. One operator's home directory compiled into five tools is a decision taken away from
# the next adopter, and it fails by reporting an empty tree (12.h).
MAIN = storm_paths.repo(STORM)
LANE_BRANCH = "lane/"


def _stopper():
    """`storm-stop.py`, imported by path because its name is not an identifier.

    For `lane_in_flight` and `is_invocation`. Reimplementing the "is a runner inside this
    lane" test would mean a second answer to a question this toolchain already answers, and
    the naive form of it -- `"qwenlane.py" in argv` -- is a bug storm-stop.py's own comment
    records having been bitten by: it matched a process that merely mentioned the name.
    """
    spec = importlib.util.spec_from_file_location(
        "storm_stop", Path(__file__).with_name("storm-stop.py")
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


STOP = _stopper()


def lines_of(name: str) -> list[str]:
    path = STORM / name
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if line.strip()]


def settled() -> set[str]:
    return set(lines_of("integrated.txt")) | set(lines_of("abandoned.txt"))


def queue() -> dict[str, list[str]]:
    """Each queued slug and the dependencies it waits on."""
    out: dict[str, list[str]] = {}
    for line in lines_of("queue.txt"):
        parts = line.split()
        if not parts:
            continue
        deps = parts[2].split(",") if len(parts) > 2 else []
        out[parts[0]] = [d for d in deps if d]
    return out


def verdict(lane: Path) -> dict | None:
    """What `qwenlane.py` recorded for this lane, or None if it never finished."""
    path = lane / ".qwenstorm" / "result.json"
    if not path.is_file():
        return None
    try:
        found = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        # A result nobody can read is not a verdict. Left for a person rather than guessed
        # at in either direction -- reaping on it would abandon a lane on a parse error.
        return None
    return found if isinstance(found, dict) else None


def forge() -> list[storm_forge.PullRequest] | None:
    """Every pull request on the forge, newest first, or None if it cannot be read whole.

    One call for every lane rather than one per lane: a query per lane over thirty lanes is
    thirty round trips to answer a question one round trip answers, which is the machinery
    wasting its own time as surely as anybody else's (12.g). The read is `storm_forge`'s,
    shared with `lane-publish.py`, so both tools agree on what a pull request closes (10.e).

    None, not [], when the read fails -- or comes back exactly as long as its limit, which
    means the oldest may be missing. An empty list and an unreachable forge would otherwise
    be the same value and opposite facts -- the first says "nothing was ever published", the
    second says "I could not find out" -- and acting on the second would abandon lanes whose
    work is sitting merged in `develop` (10.f).
    """
    try:
        return storm_forge.pull_requests(MAIN, None, storm_forge.limit(STORM))
    except storm_forge.Unreadable as exc:
        print(f"  forge: {exc}")
        return None


def heads(prs: list[storm_forge.PullRequest]) -> dict[str, tuple[int, str]]:
    """Each head ref's newest pull request, as (number, state).

    Keyed by the WHOLE head ref, not by lane slug. Keying on the slug meant the map held only
    `lane/*` branches, so the worktree pass could not find a pull request for `docs/...` or
    `fix/...` and kept all eighteen of them as "never published" -- a right answer to a
    question about a map that had never been asked to hold them. The list is newest first,
    so the first one seen is the live one: a branch republished after a closed attempt is
    judged on the new request.
    """
    out: dict[str, tuple[int, str]] = {}
    for pr in prs:
        if pr.head and pr.head not in out:
            out[pr.head] = (pr.number, pr.state)
    return out


def claimed(
    prs: list[storm_forge.PullRequest], issue: str | None, state: str
) -> storm_forge.PullRequest | None:
    """The newest pull request in `state` whose body closes `issue`, under any branch name.

    The lane's own `lane/<slug>` branch is not the only road to `develop`. rmq-r03 merged as
    `feat/amqp-dependency` (#1040), and #396 carried eight wave-1 lanes at once; looking only
    at `lane/<slug>` left rmq-r03 unsettled indefinitely, and every lane waiting on it waiting
    with it. What says a pull request delivered an issue is the closing reference the forge
    itself acts on, and `storm_forge` reads exactly that.
    """
    number = int(issue) if issue and issue.isdigit() else None
    for pr in storm_forge.closing(prs, number):
        if pr.state == state:
            return pr
    return None


def survey(
    grace_seconds: float, prs: list[storm_forge.PullRequest]
) -> dict[str, list[tuple[str, str]]]:
    """Every lane on disk, sorted into what may be done about it and why."""
    if not LANES.is_dir():
        raise SystemExit(f"no lanes directory at {LANES} -- run this from the runtime root")

    # `process_table()` answers None when it could not read the process list at all -- under
    # a sandbox that denies `ps`, for one, which is not hypothetical. There is no safe way to
    # reap without it: "no runner is inside this lane" and "I cannot see any runner" are the
    # same value and opposite facts, and acting on the second would abandon a lane a model is
    # working in right now. So this refuses the whole pass rather than treat silence as an
    # all-clear, which is sub-doctrine 10.f -- missing evidence stays unknown.
    table = STOP.process_table()
    if table is None:
        raise SystemExit(
            "cannot read the process table, so cannot tell which lane is live -- refusing to "
            "reap. Nothing was changed."
        )

    done, live = settled(), STOP.lane_in_flight(table)
    now = time.time()
    branches, issues = heads(prs), issue_of()
    out: dict[str, list[tuple[str, str]]] = {
        "integrate": [],
        "reap": [],
        "live": [],
        "settled": [],
        "in-flight": [],
        "publishable": [],
        "unfinished": [],
        "young": [],
        "refused": [],
    }
    for lane in sorted(p for p in LANES.iterdir() if p.is_dir()):
        slug = lane.name
        pr = branches.get(LANE_BRANCH + slug)
        merged = claimed(prs, issues.get(slug), "MERGED")
        opened = claimed(prs, issues.get(slug), "OPEN")
        found = verdict(lane)
        if slug == live:
            out["live"].append((slug, "a runner is inside it"))
        elif slug in done:
            out["settled"].append((slug, "already in the ledger"))
        elif pr and pr[1] == "MERGED":
            # The forge outranks the runner's note about itself. This is the branch that
            # `split-332-1-transport-seams` needed and the first draft did not have.
            out["integrate"].append((slug, f"#{pr[0]} is merged, so its work is in develop"))
        elif merged:
            out["integrate"].append(
                (
                    slug,
                    f"#{merged.number} ({merged.head}) is merged and closes #{issues[slug]}, "
                    "so its work is in develop",
                )
            )
        elif pr and pr[1] == "OPEN":
            out["in-flight"].append((slug, f"#{pr[0]} is open; the merge train decides it"))
        elif opened:
            out["in-flight"].append(
                (
                    slug,
                    f"#{opened.number} ({opened.head}) is open and closes #{issues[slug]}; "
                    "the merge train decides it",
                )
            )
        elif found is None:
            out["unfinished"].append(
                (slug, "no readable verdict -- killed mid-run, or still being written")
            )
        elif "refused" in found:
            # The runner declined to START this lane -- its issue failed the provenance check
            # (12.j) -- so nothing was attempted and nothing gave up. Reaping it would write a
            # false "gave up after 0 attempt(s)" into the ledger (10.f), cascade that into
            # every dependant as a dead dependency, and post a comment on an issue the storm
            # has just declined to trust. Whether the issue is sound is a person's call; the
            # lane stays unsettled until one makes it, and its dependants are named below.
            out["refused"].append((slug, f"refused to start: {found['refused']}"))
        elif found.get("completed") is True and not pr:
            out["publishable"].append((slug, "the runner completed it; lane-publish.py owns it"))
        elif found.get("completed") is True:
            out["reap"].append((slug, f"#{pr[0]} was closed unmerged, so the work was refused"))
        elif (age := now - (lane / ".qwenstorm" / "result.json").stat().st_mtime) < grace_seconds:
            # The cycle repairs every ten minutes, and `lane-repair.py` runs before this
            # step. A verdict minutes old has not yet had a repair pass argue with it, so
            # recording it now would settle a lane the next pass might have rescued.
            out["young"].append(
                (slug, f"gave up {age / 60:.0f}m ago; repair has not had its passes yet")
            )
        else:
            gave_up = f"the runner gave up after {len(found.get('attempts') or [])} attempt(s)"
            closed = (
                f", and #{pr[0]} was closed unmerged" if pr else ", and nothing was ever published"
            )
            out["reap"].append((slug, gave_up + closed))
    return out


def blocked_by(dead: set[str], waiting: dict[str, list[str]]) -> set[str]:
    """Queued lanes that can never become eligible, because a dependency is dead.

    Transitive: a lane blocked on a blocked lane is blocked. Computed here so the report
    can say what recording these actually buys, rather than leaving it to be believed.
    """
    stuck: set[str] = set()
    frontier = set(dead)
    while frontier:
        found = {
            slug
            for slug, deps in waiting.items()
            if slug not in stuck
            and slug not in dead
            and any(d in frontier or d in stuck or d in dead for d in deps)
        }
        stuck |= found
        frontier = found
    return stuck


def issue_of() -> dict[str, str]:
    """Each queued slug's issue number, from `queue.txt`'s second column."""
    out: dict[str, str] = {}
    for line in lines_of("queue.txt"):
        parts = line.split()
        if len(parts) >= 2:
            out[parts[0]] = parts[1]
    return out


def gh(args: list[str]) -> bool:
    done = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120, cwd=MAIN)
    if done.returncode != 0:
        print(f"    gh {' '.join(args[:3])}: {done.stderr.strip()[:160]}")
    return done.returncode == 0


def sync_issues(
    landed: list[tuple[str, str]],
    dead: list[tuple[str, str]],
    numbers: dict[str, str],
    label: str,
    apply: bool,
) -> tuple[int, int]:
    """Make the issue list say what the ledger now says (sub-doctrine 12.i).

    A tracker is a claim about the present, and people act on it without re-deriving it. Left
    to drift it is worse than no tracker, because nobody distrusts it -- measured here on
    2026-09-23, issue #1001 was open while its pull request #1055 sat merged in `develop`,
    and twelve issues the runner had given up on three times each were indistinguishable
    from twelve nobody had touched.

    The two outcomes are not symmetrical, and the asymmetry is the point:

      - A LANDED lane's issue is closed. The work is in `develop`; an open issue for it asks
        somebody to do it twice. GitHub closes these itself when a pull request body carries
        a closing keyword, which is why three of the four were already closed -- this covers
        the fourth, whose body did not.
      - A REAPED lane's issue is NOT closed. The runner gave up; the work still wants doing,
        and closing it would turn "we could not do this" into "this does not need doing",
        which is a lie the tracker would then tell every reader. It is labelled and
        commented instead, so the next person sees the three attempts rather than a silence
        they will read as an untouched issue.
    """
    closed = marked = 0
    for slug, why in landed:
        number = numbers.get(slug)
        if not number:
            continue
        print(f"  issue #{number:>5s} {'close' if apply else 'WOULD close'}: {slug} -- {why}")
        if apply and gh(
            [
                "issue",
                "close",
                number,
                "--reason",
                "completed",
                "--comment",
                f"Settled by the storm ledger: lane `{slug}` {why}.",
            ]
        ):
            closed += 1
    for slug, why in dead:
        number = numbers.get(slug)
        if not number:
            continue
        print(
            f"  issue #{number:>5s} {'label' if apply else 'WOULD label'} {label}: {slug} -- {why}"
        )
        if apply and gh(
            [
                "issue",
                "comment",
                number,
                "--body",
                f"The storm reaped lane `{slug}`: {why}. Left OPEN on purpose -- the "
                f"work still wants doing; it is the automated attempt that stopped.",
            ]
        ):
            gh(["issue", "edit", number, "--add-label", label])
            marked += 1
    return closed, marked


def worktrees(prs: dict[str, tuple[int, str]], apply: bool) -> tuple[int, int]:
    """Remove worktrees whose branch has already landed, and keep every other one.

    A worktree outlives its pull request. Thirty-three existed on 2026-09-23 and twenty-one
    were finished work sitting on disk, each a full checkout of the repository -- and each
    one a tree that `git worktree list` offers, that a stale-branch search walks, and that a
    person reading the list has to recognise and dismiss again. That is the machinery wasting
    a person's attention rather than their time, which 12.g covers just the same.

    The removal is safe for a narrow, checkable reason, not because merged branches are
    usually fine: the branch's work is in `develop`, and the tree has nothing uncommitted, so
    there is no state here that exists nowhere else. Recreating one is `git worktree add`.

    Never removed, each for its own reason:

      - the main checkout -- it is not a worktree of anything, it is the thing;
      - a tree with uncommitted changes -- the only copy of that work is in it. `git worktree
        remove` refuses these itself without `--force`, and `--force` is deliberately never
        passed, so this is two independent guards rather than one;
      - a branch with no pull request -- nothing says the work landed, so nothing says it is
        safe to drop. Unpublished is not the same as finished;
      - a branch whose pull request is still OPEN -- it is in flight;
      - a detached head -- there is no branch to ask the forge about, so the question cannot
        be answered, and 10.f says an unanswerable question stays unanswered.
    """
    done = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=MAIN,
        timeout=60,
    )
    if done.returncode != 0:
        print(f"    git worktree list failed: {done.stderr.strip()[:160]}")
        return 0, 0

    trees, current = [], {}
    for line in done.stdout.splitlines():
        if line.startswith("worktree "):
            current = {"path": line[len("worktree ") :]}
        elif line.startswith("branch "):
            current["branch"] = line[len("branch ") :].replace("refs/heads/", "")
        elif not line and current:
            trees.append(current)
            current = {}
    if current:
        trees.append(current)

    removed = kept = 0
    for tree in trees:
        path, branch = Path(tree["path"]), tree.get("branch")
        if path == MAIN or branch is None:
            kept += 1
            continue
        state = prs.get(branch)
        if state is None or state[1] not in ("MERGED", "CLOSED"):
            kept += 1
            continue
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=path, timeout=60
        )
        if dirty.returncode != 0 or dirty.stdout.strip():
            print(f"  {path.name:44s} kept -- uncommitted work, the only copy of it is here")
            kept += 1
            continue
        print(
            f"  {path.name:44s} {'removed' if apply else 'WOULD remove'}: #{state[0]} is {state[1].lower()}"
        )
        if apply:
            # No --force, ever. Its whole effect here would be to discard the state the check
            # above exists to protect.
            gone = subprocess.run(
                ["git", "worktree", "remove", str(path)],
                capture_output=True,
                text=True,
                cwd=MAIN,
                timeout=120,
            )
            if gone.returncode == 0:
                removed += 1
            else:
                print(f"    refused: {gone.stderr.strip()[:160]}")
    return removed, kept


def record(name: str, verb: str, rows: list[tuple[str, str]]) -> None:
    """Append to one ledger, and say why in the log a person and storm-evidence both read.

    Append-only and duplicate-safe: `storm-evidence.py` treats these files as streams and
    `lane-resolve.py` settles them as APPEND ledgers, so a slug written twice would be
    counted twice in the evidence even though the set it denotes is unchanged.
    """
    already = set(lines_of(name))
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with (STORM / name).open("a", encoding="utf-8") as handle:
        for slug, _ in rows:
            if slug not in already:
                handle.write(f"{slug}\n")
                already.add(slug)
    with (STORM / "progress.log").open("a", encoding="utf-8") as log:
        for slug, why in rows:
            log.write(f"{stamp} {verb} {slug}: {why}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reap", action="store_true", help="record the dead; without it, only report"
    )
    parser.add_argument(
        "--grace",
        type=float,
        default=60.0,
        help="minutes a verdict must stand before it is recorded, so repair has its passes (default 60)",
    )
    parser.add_argument(
        "--reap-worktrees",
        action="store_true",
        help=(
            "also remove worktrees whose branch has landed and which hold nothing "
            "uncommitted. Separate from --reap because it touches the working tree rather "
            "than a ledger a line-delete undoes"
        ),
    )
    parser.add_argument(
        "--sync-issues",
        action="store_true",
        help=(
            "also make the issue tracker agree with the ledger (12.i). OFF by default and "
            "separate from --reap on purpose: the ledgers are local files a line-delete "
            "undoes, while closing and commenting on issues is outward-facing and reaches "
            "everyone watching the repository. A scheduled pass reports the drift; a person "
            "decides when it writes."
        ),
    )
    args = parser.parse_args()

    prs = forge()
    if prs is None:
        raise SystemExit(
            "cannot reach the forge, so cannot tell which lanes landed -- refusing to "
            "settle anything. Nothing was changed."
        )

    found = survey(args.grace * 60, prs)
    waiting = queue()
    dead = {slug for slug, _ in found["reap"]}
    landed = {slug for slug, _ in found["integrate"]}
    # What integrating these unlocks: a queued lane whose every dependency is settled as
    # integrated, and which was not eligible before.
    done_now = set(lines_of("integrated.txt")) | landed
    eligible = {
        slug
        for slug, deps in waiting.items()
        if deps
        and slug not in done_now
        and set(deps) <= done_now
        and not set(deps) <= set(lines_of("integrated.txt"))
    }
    frees = blocked_by(dead | set(lines_of("abandoned.txt")), waiting) - dead
    # A refused lane is left unsettled, so storm-queue.sh -- which names a lane blocked only
    # when its dependency is in abandoned.txt -- would skip its dependants in silence. They
    # are named here instead, every pass, until a person settles the refusal.
    refused = {slug for slug, _ in found["refused"]}
    held_back = sorted(blocked_by(refused, waiting) - refused)

    for bucket, label in (
        ("live", "left alone -- a runner is inside"),
        ("in-flight", "left alone -- its pull request is open"),
        ("young", "left alone -- within the repair grace period"),
        ("publishable", "left alone -- the publisher's, not this tool's"),
        ("unfinished", "REPORTED, not settled -- needs a person"),
        ("refused", "REFUSED, not settled and not reaped -- needs a person"),
    ):
        for slug, why in found[bucket]:
            print(f"  {slug:44s} {label}: {why}")

    for slug, why in found["integrate"]:
        print(f"  {slug:44s} {'integrated' if args.reap else 'WOULD integrate'}: {why}")
    for slug, why in found["reap"]:
        print(f"  {slug:44s} {'reaped' if args.reap else 'WOULD reap'}: {why}")

    # Declared, not compiled in (12.h): a repository that labels these differently says so in
    # storm.toml rather than editing a tool.
    label = storm_paths.declared(STORM, "issues", "abandoned_label") or "storm:reaped"
    closed, marked = sync_issues(
        found["integrate"], found["reap"], issue_of(), label, args.sync_issues
    )

    if args.reap:
        if found["integrate"]:
            record("integrated.txt", "integrated", found["integrate"])
        if found["reap"]:
            record("abandoned.txt", "reaped", found["reap"])

    gone, held = worktrees(heads(prs), args.reap_worktrees)

    print(
        f"\n{len(found['integrate'])} landed, {len(found['reap'])} dead, "
        f"{len(found['publishable'])} awaiting publish, {len(found['in-flight'])} in flight, "
        f"{len(found['unfinished'])} unfinished, {len(found['refused'])} refused, "
        f"{len(found['settled'])} already settled"
    )
    if refused:
        print(
            f"{len(held_back)} queued lane(s) wait on a refused lane and cannot start until a "
            f"person settles it: {', '.join(held_back[:12]) or 'none'}"
            + (f" and {len(held_back) - 12} more" if len(held_back) > 12 else "")
        )
    if landed:
        print(
            f"{len(eligible)} queued lane(s) {'are now' if args.reap else 'would become'} eligible to start -- "
            "their dependencies are integrated and the ledger can finally say so"
        )
    if dead:
        print(
            f"{len(frees)} queued lane(s) {'are now' if args.reap else 'would be'} reported blocked rather than "
            "silently skipped -- storm-queue.sh names a lane blocked only when its dependency is in the ledger"
        )
    print(
        f"worktrees: {gone if args.reap_worktrees else 0} removed, {held} kept"
        + ("" if args.reap_worktrees else " (pass --reap-worktrees to remove the landed ones)")
    )
    if closed or marked:
        print(f"issues: {closed} closed, {marked} labelled {label}")
    elif not args.sync_issues and (found["integrate"] or found["reap"]):
        print("issues: reported only (pass --sync-issues to make the tracker agree)")
    if (found["reap"] or found["integrate"]) and not args.reap:
        print("nothing was changed; pass --reap to record these")
    return 0


if __name__ == "__main__":
    sys.exit(main())
