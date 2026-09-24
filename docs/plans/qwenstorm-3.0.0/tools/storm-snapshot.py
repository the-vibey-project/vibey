"""Write the storm's run state to RUN-STATE.md, and commit and push it when it changed.

    python3 storm-snapshot.py                       # print the snapshot; write nothing
    python3 storm-snapshot.py --write               # write RUN-STATE.md
    python3 storm-snapshot.py --write --commit      # ...and commit it if it changed
    python3 storm-snapshot.py --write --commit --push

The one place the snapshot is produced. `storm-stop.py` calls it at a pause and
`storm-cycle.py` calls it every pass, so there is a single rendering to keep correct rather
than two that drift until the one nobody runs is the one somebody reads.

A SNAPSHOT DOES NOT NEED THE TEST SUITE
---------------------------------------
It records one markdown file. The pre-push gate would otherwise run the whole suite twice --
once for `test-suite` and again for `coverage-gates` -- costing several minutes of the machine
the storm is trying to use, to protect code this commit does not contain. So those two hooks,
and only those two, are skipped by name through pre-commit's own SKIP, and only after
`only_the_snapshot()` has proven the push carries nothing else. Every other hook still runs,
and the pull-request gate on the forge still runs all of it. A blanket `--no-verify` is the
lazy version of this and is not used: the narrowing is conditional, verified, and reported.

AND IT USUALLY DOES NOTHING AT ALL
----------------------------------
The work is also gated on the snapshot having changed. The ledger moves when a lane settles,
a handful of times an hour rather than every ten minutes; every other pass renders the same
bytes, notices, and stops before it has cost anything. The timestamp is excluded from that
comparison on purpose -- a clock tick is not news, and counting it would make every pass a
change and defeat the arrangement.

WHAT IT PROMISES
----------------
Only what it saw. A refused push is reported as refused and the commit is left in place, safe
and local, because a snapshot recorded as pushed when it was not is worse than one that was
never taken: the first is trusted (sub-doctrine 10.f).
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# .absolute(), never .resolve(): tools/ is a symlink into the planning worktree, where specs/
# resolve but lanes/ and integration/ exist only in the runtime root.
STORM = Path(__file__).absolute().parent.parent
LANES = STORM / "lanes"
INTEGRATION = STORM / "integration"
# The worktree that owns RUN-STATE.md. tools/ is a symlink into it, so resolving this file --
# rather than .absolute() -- is the one place the real checkout is wanted.
PLANS = Path(__file__).resolve().parent.parent
STATE = PLANS / "RUN-STATE.md"
# SNAPSHOT_PATHS below are repo-relative (that is how `git diff --name-only`
# reports them); staging needs them resolved against the checkout root.
REPO = PLANS.parent.parent.parent

# The line that changes on every render whether or not anything happened. Excluded from the
# "did it change" comparison so that a clock tick alone never triggers a commit and a push.
STAMP = re.compile(r"^Snapshot .*$", re.M)


# The two pre-push hooks that each run the whole test suite. A snapshot changes one markdown
# file and cannot break anything they check, so paying several minutes of the machine twice --
# on the machine the storm needs -- buys nothing. They are skipped by name, through
# pre-commit's own SKIP, and only after this script has PROVEN the push carries nothing but
# the snapshot. Everything else still runs, and the pull-request gate still runs all of it on
# the forge. A blanket --no-verify would have been the lazy version of this and is not used:
# the narrowing is conditional, verified, and says out loud what it skipped.
HEAVY_HOOKS = "coverage-gates"
SNAPSHOT_PATHS = (
    "docs/plans/qwenstorm-3.0.0/RUN-STATE.md",
    "docs/plans/qwenstorm-3.0.0/evidence/ledger.jsonl",
    "docs/plans/qwenstorm-3.0.0/evidence/watermark.json",
    "docs/plans/qwenstorm-3.0.0/evidence/CHANGES.md",
    "docs/paper.md",
)


def run(
    argv: list[str], cwd: Path, timeout: int = 2400, env: dict[str, str] | None = None
) -> tuple[int, str]:
    try:
        done = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env
        )
    except (OSError, subprocess.SubprocessError):
        return 127, ""
    return done.returncode, (done.stdout + done.stderr).strip()


def lines_of(name: str) -> list[str]:
    path = STORM / name
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if line.strip()]


def gather() -> dict:
    lanes = sorted(d.name for d in LANES.iterdir() if d.is_dir()) if LANES.is_dir() else []
    integrated, abandoned = lines_of("integrated.txt"), lines_of("abandoned.txt")
    settled = set(integrated) | set(abandoned)
    code, head = run(["git", "rev-parse", "--short", "HEAD"], INTEGRATION, timeout=60)
    last = lines_of("progress.log")
    return {
        "when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "queue": len(lines_of("queue.txt")),
        "integrated": integrated,
        "abandoned": abandoned,
        "lanes": lanes,
        "unsettled": [s for s in lanes if s not in settled],
        "finished": [s for s in lanes if (LANES / s / ".qwenstorm/result.json").is_file()],
        "integration": head.strip() if not code else "unknown",
        "last": last[-1][:110] if last else "(nothing logged)",
    }


def render(state: dict, notes: list[str] | None = None) -> str:
    unfinished = [s for s in state["lanes"] if s not in state["finished"]]
    note_block = (
        "\n## How it was stopped\n\n" + "\n".join("- " + n for n in notes) + "\n" if notes else ""
    )
    settled = "\n".join(
        [f"integrated  {s}" for s in state["integrated"]]
        + [f"abandoned   {s}" for s in state["abandoned"]]
    )
    return f"""# QwenStorm 3.0.0 — run state

Snapshot {state["when"]}, written by `tools/storm-snapshot.py`.

The runner's durable record is `integrated.txt` and `abandoned.txt`: a lane in neither is
unsettled, whatever exists under `lanes/`. `lanes/` lives in the storm root, on durable
storage under the storm home (sub-doctrine 10.h), but it is working material rather than the
record, so nothing here depends on it surviving.

- queue: **{state["queue"]} lanes** · integrated: **{len(state["integrated"])}** · abandoned: **{len(state["abandoned"])}**
- lane worktrees: **{len(state["lanes"])}** · finished awaiting review: **{len(state["finished"])}** · unsettled: **{len(state["unsettled"])}**
- integration branch: `{state["integration"]}`
- last line of progress.log: `{state["last"]}`

Still running or never finished ({len(unfinished)}): {", ".join(f"`{s}`" for s in unfinished) or "none"}
{note_block}

## How to resume

```bash
cd {STORM}
touch UNATTENDED                      # batch review; a finished lane does not block the queue
nohup bash tools/storm-queue.sh > scratch/storm-run.log 2>&1 < /dev/null & disown
```

macOS has no `setsid`; `nohup ... & disown` is what survives the launching shell.
`storm-queue.sh` starts `storm-cycle.py` itself, so the outer loop needs no separate command.
A lane with a `.qwenstorm/result.json` is treated as finished and awaiting review; delete that
file to have it run again.

To run a lane next, after the lane running now (ADR-0054; the operator or a declared source):

```bash
python3 tools/storm-priority.py push SLUG ISSUE --deps a,b   # or: bump SLUG / unbump SLUG
python3 tools/storm-priority.py list                         # the order the storm will run
```

Health, without needing `ps` (which the sandbox refuses):

```bash
python3 tools/storm-watch.py            # exit 0 healthy, 1 wrong, 2 cannot tell
python3 tools/storm-stop.py --stop      # pause: quiet the watch, stop softly, record it
```

## Settled

```
{settled or "(nothing settled yet)"}
```
"""


def only_the_snapshot() -> bool:
    """Whether everything about to be pushed is the snapshot file and nothing else.

    Checked rather than assumed. If a real change is riding along on this branch -- a tool
    edit, a spec, anything -- the heavy hooks run, because the reason they can be skipped is
    the content, not the intent of whoever started the job.
    """
    for base in ("@{upstream}", "origin/develop"):
        code, out = run(["git", "diff", "--name-only", f"{base}..HEAD"], PLANS, timeout=120)
        if code:
            continue
        changed = {line.strip() for line in out.splitlines() if line.strip()}
        # A subset, not an exact match: a pass may move the ledger without the paper, or the
        # paper without the report. Anything OUTSIDE the set means real work is riding along
        # and the full gate runs.
        return bool(changed) and changed <= set(SNAPSHOT_PATHS)
    return False  # could not establish it, so do not skip anything


def unchanged(text: str) -> bool:
    """Whether this render says anything the file does not already say, ignoring the clock."""
    if not STATE.is_file():
        return False
    try:
        old = STATE.read_text(errors="replace")
    except OSError:
        return False
    return STAMP.sub("", old).strip() == STAMP.sub("", text).strip()


# Branches this must never write directly. 12.d is explicit that unattended work reaches
# develop as a pull request through the merge train or it does not reach it at all, and a
# periodic job is unattended by definition. The runtime worktree is a checkout like any
# other: put it on develop for an afternoon and every ten-minute pass would start pushing
# straight at the protected branch, which is how a rule that everyone agrees with gets
# broken by nobody in particular.
PROTECTED = ("develop", "main")


def current_branch() -> str:
    """The branch this worktree is on, or "" when git could not say.

    NOT "?" -- that reads like a branch name and is not in `PROTECTED`, so a failed probe
    fell straight through the guard below and pushed. A guard that cannot tell where it is
    standing has to refuse, not proceed: the whole point of it is that nobody is watching.
    An unknown is an unknown, never a pass (10.f).
    """
    code, out = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], PLANS, timeout=60)
    return out.strip() if not code else ""


# `docs/paper.md` is a paper somebody writes, carrying ONE block that automation regenerates.
# The other snapshot paths are automation's entirely. That difference decides what a timer may
# commit, so the markers are named here rather than assumed.
GENERATED = (
    "<!-- BEGIN GENERATED storm-evidence — regenerated by tools/storm-evidence.py -->",
    "<!-- END GENERATED storm-evidence -->",
)


def hand_written(text: str) -> str:
    """Everything in `docs/paper.md` except the block automation owns."""
    begin, end = GENERATED
    if begin not in text or end not in text:
        return text
    head, rest = text.split(begin, 1)
    return head + rest.split(end, 1)[1]


def not_ours() -> list[str]:
    """Snapshot paths carrying a change this storm's automation did not make.

    `git add -- <SNAPSHOT_PATHS>` stages them because they exist, not because anything here
    wrote them. An operator part-way through an edit to `docs/paper.md` would have it
    committed by a timer and pushed -- and `only_the_snapshot()` would then see nothing
    outside the snapshot set, skip the heavy hooks, and let it through untested. A timer
    that commits somebody's unfinished paragraph and skips the tests is the worst of both.

    The test is ownership, not dirtiness. The evidence ledger, its watermark, the delta
    report and RUN-STATE.md are written wholly by the storm's own jobs, and `storm-evidence`
    runs on its own timer, so finding them modified is the normal case rather than a
    warning. `docs/paper.md` is the one a person writes: automation owns only the block
    between its markers, so only a change OUTSIDE that block is somebody else's.
    """
    paper = REPO / "docs/paper.md"
    if not paper.is_file():
        return []
    # NOT `run()`: it strips its output, so the committed copy loses the trailing newline
    # that the working copy keeps, the two can never compare equal, and this guard refuses
    # EVERY snapshot forever -- a fail-closed that never opens is just off. `lane-resolve.py`
    # carries a `read_blob()` for the same reason and the same mistake was made again here.
    try:
        done = subprocess.run(
            ["git", "show", "HEAD:docs/paper.md"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if done.returncode:
        return []  # no committed version to compare against; nothing to protect yet
    if hand_written(done.stdout) == hand_written(paper.read_text(encoding="utf-8")):
        return []
    return ["docs/paper.md"]


def publish(text: str, commit: bool, push: bool) -> list[str]:
    waiting = not_ours()  # read BEFORE this pass writes anything of its own
    STATE.write_text(text)
    notes = [f"wrote {STATE.name}"]
    branch = current_branch()
    if push and not branch:
        notes.append(
            "REFUSED to push: git could not say which branch this worktree is on, and a "
            "guard that cannot tell where it is standing does not get to proceed."
        )
        push = False
    if push and branch in PROTECTED:
        # Decided up front and said once. Committing locally is still useful -- the work is
        # safe in git either way -- but the push is refused: unattended work reaches develop
        # as a pull request through the merge train or it does not reach it at all (12.d).
        notes.append(
            f"REFUSED to push: this worktree is on '{branch}', a protected branch. "
            "Put it on a branch of its own; unattended work reaches develop by pull request."
        )
        push = False
    if not commit:
        return notes
    # Every artifact the run produces, not only RUN-STATE.md: the evidence ledger, its
    # watermark, the delta report and the paper's regenerated block are all written by this
    # pass and would otherwise be left uncommitted, and uncommitted work is one reboot or one
    # lost disk from gone (10.h).
    if waiting:
        return notes + [
            "REFUSED to commit: "
            f"{', '.join(sorted(waiting))} changed outside the block this storm generates, "
            "so the change is somebody's and not a timer's to commit."
        ]
    present = [rel for rel in SNAPSHOT_PATHS if (REPO / rel).exists()]
    if not present:
        return notes + ["none of the snapshot artifacts exist to stage"]
    code, out = run(["git", "add", "--", *present], REPO, timeout=120)
    if code:
        return notes + [f"could not stage: {(out.splitlines() or ['?'])[-1][:70]}"]
    code, out = run(
        ["git", "commit", "-q", "-m", "chore(storm): snapshot the run"], PLANS, timeout=900
    )
    if code and "nothing to commit" not in out:
        return notes + [f"commit refused: {(out.splitlines() or ['?'])[-1][:80]}"]
    notes.append("committed")
    if not push:
        return notes
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)  # or uv resolves the package from whichever venv launched us
    if only_the_snapshot():
        env["SKIP"] = HEAVY_HOOKS
        notes.append(f"only {STATE.name} changed; skipping {HEAVY_HOOKS}")
    else:
        notes.append("more than the snapshot is on this branch; running the full gate")
    # A refusal here is ordinary and is reported as itself rather than smoothed into success.
    # The commit is safe either way.
    # Through the push gate like every push here, even when the heavy hook is skipped: the
    # gate serialises pre-push runs, and when more than the snapshot is on the branch this
    # push runs the full one. `STORM / "tools"` is where push_gate.py resolves the storm's
    # shared lock; the planning tree it resolves into would derive a private one.
    code, out = run(
        [sys.executable, str(STORM / "tools" / "push_gate.py"), "run", "--wait-timeout", "1800"]
        + ["--", "git", "push"],
        PLANS,
        env=env,
    )
    notes.append("pushed" if not code else f"PUSH REFUSED: {(out.splitlines() or ['?'])[-1][:80]}")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write RUN-STATE.md")
    parser.add_argument("--commit", action="store_true", help="commit it when it changed")
    parser.add_argument("--push", action="store_true", help="push the commit")
    parser.add_argument(
        "--force", action="store_true", help="write even when nothing changed but the clock"
    )
    parser.add_argument(
        "--note", action="append", help="a line for the 'how it was stopped' section"
    )
    args = parser.parse_args()

    text = render(gather(), args.note)
    if not args.write:
        print(text)
        return 0
    if unchanged(text) and not args.force:
        # The common case, and saying so costs nothing: the pass that does nothing should be
        # legible, or the next person wonders whether the job is running at all.
        print("storm-snapshot: unchanged since the last snapshot; nothing committed or pushed")
        return 0
    for note in publish(text, commit=args.commit, push=args.push):
        print(f"storm-snapshot: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
