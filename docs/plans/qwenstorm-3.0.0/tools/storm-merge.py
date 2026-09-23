"""Run the repository's merge train, hourly, independently of the outer cycle.

    python3 storm-merge.py                 # report what the train would see; merge nothing
    python3 storm-merge.py --run           # run the train once
    python3 storm-merge.py --run --every 3600            # hourly, while a storm is running
    python3 storm-merge.py --run --every 3600 --detached # ...and stop when the storm does

WHY THIS EXISTS WHEN THE CYCLE ALREADY RUNS THE TRAIN
-----------------------------------------------------
`storm-cycle.py` runs `vibey-gh merge-train` as one of its seven steps, every ten minutes, so
on a healthy night this has nothing to add. It exists for the night that is not healthy: the
cycle is one process, and when it dies the train stops with it, silently, while lanes keep
finishing and pull requests keep piling up behind a queue nobody is draining. A backstop that
shares a process with the thing it backs up is not a backstop.

So this is deliberately separate, deliberately dumber, and deliberately slower. Hourly rather
than every ten minutes, because its job is to catch a stalled cycle rather than to be the
cycle; if both are alive the train simply finds nothing new to do, which costs one API call.

WHAT IT DOES NOT DO
-------------------
It does not merge anything itself and never writes `develop`. `vibey-gh merge-train` merges
pull requests whose head carries a successful `PR automation / gate` (ADR-0028), on the forge,
through the same path a person clicking Merge would take. Writing a second merge policy here
-- one this file's author chose -- is exactly what 10.e forbids and what 12.d means by not
routing around the gate. If nothing merges, the answer is in the pull request's checks.

It also reports what it saw rather than what it hoped. `merged 0, skipped 1` with the reason
is the useful output, and "nothing to do" and "everything is blocked" are different states
that must never print the same way (10.f).
"""

import argparse
import os
import re
import subprocess
import time
from pathlib import Path

# .absolute(), never .resolve(): tools/ is a symlink into the planning worktree, where specs/
# resolve but lanes/ and integration/ exist only in the runtime root.
STORM = Path(__file__).absolute().parent.parent
MAIN = Path("/Users/adam/git/vibey")


def say(message: str) -> None:
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} merge: {message}", flush=True)


def run(argv: list[str], cwd: Path, timeout: int = 1800) -> tuple[int, str]:
    # VIRTUAL_ENV leaks from whatever shell launched the storm and `uv run` obeys it, which
    # resolves vibey-gh from a different checkout than the one being operated on. The same
    # fix lives in lane-publish.py for the same reason.
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    try:
        done = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env
        )
    except FileNotFoundError:
        return 127, f"not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return done.returncode, (done.stdout + done.stderr).strip()


def storm_running() -> bool:
    """Whether a storm is up, judged the way storm-stop.py judges it.

    An empty process table means the probe was refused, not that nothing is running -- `ps`
    returns nothing under the sandbox these tools run in. Treated as "running" on purpose:
    the failure this must not produce is stopping a backstop because it could not look.
    """
    code, out = run(["ps", "-Ao", "args="], STORM, timeout=60)
    rows = [line for line in out.splitlines() if line.strip()]
    if code or len(rows) < 10:
        return True
    return any(
        "storm-queue.sh" in row and not re.match(r"^\S*/?(?:sh|bash|zsh|dash) +-c\b", row)
        for row in rows
    )


def train(dry: bool) -> int:
    if dry:
        code, out = run(["uv", "run", "vibey-gh", "merge-train", "--dry-run"], MAIN)
        if code == 2 or "unrecognized arguments" in out:
            say("no --dry-run on this vibey-gh; reporting open pull requests instead")
            code, out = run(
                ["gh", "pr", "list", "--repo", "the-vibey-project/vibey", "--base", "develop"],
                MAIN,
                timeout=300,
            )
    else:
        code, out = run(["uv", "run", "vibey-gh", "merge-train"], MAIN)
    for line in [line for line in out.splitlines() if line.strip()][-8:]:
        # uv's environment warning is noise on every single line of output; the merge train's
        # own verdict is what anyone reading this came for.
        if "does not match the project environment" not in line:
            print(f"    {line}", flush=True)
    say(f"exit {code}")
    return code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="actually run the train")
    parser.add_argument("--every", type=int, metavar="SECONDS", help="repeat on this interval")
    parser.add_argument(
        "--detached", action="store_true", help="only while a storm runs; exit when it stops"
    )
    args = parser.parse_args()

    if not args.every:
        return train(dry=not args.run)

    while True:
        if args.detached and not storm_running():
            say("no storm is running; the hourly train stops with it")
            return 0
        train(dry=not args.run)
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
