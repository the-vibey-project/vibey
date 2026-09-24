"""One pass of the storm's outer loop: refresh, repair, publish, then let the train merge.

    python3 storm-cycle.py                    # report a pass; change nothing
    python3 storm-cycle.py --run              # do a pass
    python3 storm-cycle.py --run --every 600  # do a pass every 10 minutes, while a storm runs

The inner loop is storm-queue.sh, which turns issues into lane worktrees. This is the outer
one, and it is seven steps, each already its own script and each gated on evidence:

  push-gate push_gate.py reap -- first, before anything that can take long: release the
            shared push lock from a holder that is gone, and reap a push whose own process
            group sat idle for the declared window or passed the declared wall ceiling,
            with evidence first and a line in the reap log (12.d, 12.e). One sample per
            pass, kept on disk, so idleness is measured across passes, never from one
            snapshot. It cannot reap a hang in this pass's own publish step: a pass stuck
            there never reaches the next pass. The reaper's own schedule
            (`push_gate.py install-schedule`) can, and publish's `--push-timeout` records
            its own kill as a reap
  resolve   lane-resolve.py  -- settle the conflicts decidable from the tree, refuse the rest
  refresh   lane-refresh.py  -- carry what merged into develop into every idle lane
  repair    lane-repair.py   -- fix only what a formatter or a delete can fix
  publish   lane-publish.py  -- for lanes that pass every gate: commit, push, open a PR
  reap      lane-reap.py     -- settle the ledger from evidence: what landed becomes
            integrated, what the runner gave up on is abandoned, so the queue stops
            silently skipping everything downstream of a dead lane
  merge     vibey-gh merge-train
  evidence  storm-evidence.py -- consume every datum since the last run; keep the paper's
            derived block and the delta report current (10.g)
  snapshot  storm-snapshot.py -- record the run state in git, when it has changed

Resolve runs before refresh and not only inside it. Refresh calls the resolver itself for a
conflict it causes, but a lane can be sitting mid-conflict for reasons refresh never saw -- a
pass killed partway, a merge started by hand. Those lanes are invisible to every later step,
because a repo with a merge in progress cannot be refreshed, repaired or published. Clearing
that state is the first thing worth doing, not the last.

WHY THIS DOES NOT MERGE ANYTHING ITSELF
---------------------------------------
This repository already merges pull requests: `vibey-gh merge-train` squashes into develop
those whose head carries a successful `PR automation / gate` (ADR-0028), and that is what
merged #478 tonight with nobody watching. Writing a second merge here would mean a second
policy for what is allowed to land -- one this file's author chose, bypassing the gate the
repository actually ratified. ADR-0017 is explicit that a capability the family already ships
is used rather than reimplemented, so the cycle runs the train and lets it decide. If nothing
merges, the answer is in the PR's checks, which is where it should be.

WHEN IT STOPS
-------------
`--every` runs only while a storm is running, and returns when the storm does. An outer loop
that outlived the inner one would keep publishing lanes nobody was still producing, and would
hold a lock on a repository the operator had finished with.
"""

import argparse
import fcntl
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import storm_durability
import storm_paths

# .absolute(), never .resolve(): tools/ is a symlink into the planning worktree, where specs/
# resolve but lanes/ and integration/ exist only in the runtime root.
STORM = Path(__file__).absolute().parent.parent
TOOLS = STORM / "tools"

# Declared in storm.toml, derived from the tree when it is silent -- never a literal
# in this file. One operator's home directory compiled into five tools is a decision
# taken away from the next adopter, and it fails by reporting an empty tree (12.h).
MAIN = storm_paths.repo(STORM)


def say(message: str) -> None:
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"{stamp} cycle: {message}", flush=True)


def run(argv: list[str], cwd: Path, timeout: int = 3600) -> tuple[int, str]:
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, f"not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return done.returncode, (done.stdout + done.stderr).strip()


def storm_running() -> bool:
    code, out = run(["ps", "-Ao", "args="], STORM, timeout=60)
    return code == 0 and any("storm-queue.sh" in line for line in out.splitlines())


def step(name: str, argv: list[str], keep: int = 6) -> None:
    code, out = run(argv, STORM)
    tail = [line for line in out.splitlines() if line.strip()][-keep:]
    say(f"{name}: exit {code}")
    for line in tail:
        print(f"    {line}", flush=True)


def cycle(dry: bool) -> None:
    python = sys.executable
    say("pass starting" + (" (dry run)" if dry else ""))

    # FIRST, and not only because it is cheap. Every later step can take long -- publish
    # alone runs the full pre-push gates once per lane -- and a pass stuck behind a hung
    # push must not be the thing that stops the reaper from seeing it. This is the storm's
    # one scheduler doing the reaping; there is no second loop (push_gate.py says why each
    # condition, and only those, may act unattended).
    step(
        "push-gate",
        [python, str(TOOLS / "push_gate.py"), "reap", *(["--dry-run"] if dry else [])],
        keep=4,
    )

    if not dry:
        # Idempotent and cheap, and it must reach lanes created since the last pass: rerere
        # is per-clone configuration, so a lane set up an hour ago has none of it until this
        # runs. Turning it on is what makes one hand-made resolution settle the same conflict
        # in every other lane and on every pass after.
        step("install", [python, str(TOOLS / "lane-resolve.py"), "--install"], keep=2)
    step("resolve", [python, str(TOOLS / "lane-resolve.py"), *([] if dry else ["--resolve"])])
    step("refresh", [python, str(TOOLS / "lane-refresh.py"), *([] if dry else ["--refresh"])])
    step("repair", [python, str(TOOLS / "lane-repair.py"), *([] if dry else ["--repair"])], keep=10)
    step(
        "publish",
        [python, str(TOOLS / "lane-publish.py"), *([] if dry else ["--publish"])],
        keep=10,
    )
    # AFTER publish, never before: a lane the publisher could still rescue must have had its
    # chance this pass before anything records it as dead. The ledger writes are safe
    # unattended (bookkeeping, per lane-reap's own docstring); the issue writes and the
    # worktree removals are NOT passed here, because those reach outside the storm's scratch
    # and a scheduled pass should report them for a person rather than perform them (12.d).
    step("reap", [python, str(TOOLS / "lane-reap.py"), *([] if dry else ["--reap"])], keep=10)

    if dry:
        say("merge: would run the repository's own merge train")
    else:
        # ONE TRAIN AT A TIME, whichever scheduler asked for it.
        # `storm-merge.py` runs the same command hourly as a backstop for when this cycle
        # is not up, and both start immediately, so they coincide on the hour. Each train
        # reads the whole open-pull-request list, judges it, then merges: interleave two
        # and the second decides from state the first has already changed, and the train
        # falls through to its `--admin` path when what it expected is no longer there.
        # `flock`, so a scheduler killed mid-train leaves nothing behind to clear by hand;
        # non-blocking, because whoever holds it is already doing this step.
        lock = STORM / "scratch/merge-train.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("w") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                say("merge-train: another scheduler holds it; skipped this cycle")
            else:
                # The train merges what its gate allows; this asks it to look, and reports
                # what it did.
                code, out = run(["uv", "run", "vibey-gh", "merge-train"], MAIN, timeout=1800)
                tail = [line for line in out.splitlines() if line.strip()][-6:]
                say(f"merge-train: exit {code}")
                for line in tail:
                    print(f"    {line}", flush=True)

    # Last, so the snapshot records what this pass actually did rather than what it was about
    # to do. Cheap on both counts: it writes nothing at all when the run state has not moved
    # (the ledger changes when a lane settles, a handful of times an hour, not every ten
    # minutes), and when it does push, storm-snapshot.py skips the two hooks that each run the
    # whole suite -- having first proven the push carries nothing but one markdown file.
    # Before the snapshot, because the snapshot should describe a ledger that is already
    # current. It reads every byte and record written since its own last run (10.g) -- the
    # watermark is a position in the data, the ledger is what de-duplication consults, and a
    # truncated or unreadable source is reported as a gap rather than stepped over.
    step(
        "evidence",
        [
            python,
            str(TOOLS / "storm-evidence.py"),
            *([] if dry else ["--consume", "--paper", "--report"]),
        ],
        keep=6,
    )
    step(
        "snapshot",
        [
            python,
            str(TOOLS / "storm-snapshot.py"),
            *([] if dry else ["--write", "--commit", "--push"]),
        ],
        keep=4,
    )
    say("pass complete")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run", action="store_true", help="actually refresh, repair, publish, merge"
    )
    parser.add_argument("--every", type=int, metavar="SECONDS")
    parser.add_argument(
        "--detached",
        action="store_true",
        help="only run while a storm is running, and exit when it stops",
    )
    args = parser.parse_args()

    if args.run:
        # A pass writes logs, evidence and lane commits into the storm root. Not on storage
        # a reboot empties (10.h, ADR-0057): the gate names the key to move it, and exits 78.
        home, _ = storm_durability.StormHome(os.environ, STORM).resolve()
        storm_durability.DurabilityGate(
            storm_durability.VolatileLocations(os.environ), disposable_root=STORM
        ).enforce({"storm home": home, "storm root": STORM}, storm_durability.MOVE_IT)

    if not args.every:
        cycle(dry=not args.run)
        return 0

    while True:
        if args.detached and not storm_running():
            say("no storm is running; the outer loop stops with the inner one")
            return 0
        cycle(dry=not args.run)
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
