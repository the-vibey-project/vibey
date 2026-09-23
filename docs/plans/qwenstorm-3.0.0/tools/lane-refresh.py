"""Carry what has landed on develop into the integration branch and every lane.

    python3 lane-refresh.py                  # report what is stale; change nothing
    python3 lane-refresh.py --refresh        # update the integration branch and every lane
    python3 lane-refresh.py --watch 900      # re-check every 900s, refreshing when develop moves

A lane is a clone of the integration branch, and the integration branch is a copy of develop
taken at a moment. Both go stale the moment anything merges, and a stale lane implements
against a canon and a codebase the repository no longer has -- on 2026-09-22 every lane was
four commits behind, missing the ratified sub-doctrine 8.j, the storm's own runner fixes and
the lane corpus, while implementing specs that cite them.

MERGE, NOT REBASE
-----------------
Most lanes hold uncommitted work: the model writes into the worktree and the runner does not
commit for it. Rebasing would refuse to start, and rebasing after a blind `git add` would
commit whatever half-finished state happened to be on disk as though it were a considered
change. So each lane's uncommitted work is stashed, the new base is merged, and the work is
restored. A lane whose merge or restore conflicts is left exactly where it was, at its old
base, with its work intact and the reason printed -- never half-merged, and never discarded.

WHAT IT WILL NOT TOUCH
----------------------
The lane a runner is working in right now. Merging into a worktree under a live `qwenlane.py`
would move files beneath a model mid-edit and produce a result nobody could review honestly.
That lane is skipped and picked up on the next pass, once it has finished.
"""

import argparse
import re
import subprocess
import time
from pathlib import Path

# .absolute(), never .resolve(): tools/ is a symlink into the planning worktree, where specs/
# resolve but lanes/ and integration/ exist only in the runtime root.
STORM = Path(__file__).absolute().parent.parent
LANES = STORM / "lanes"
INTEGRATION = STORM / "integration"
MAIN = Path("/Users/adam/git/vibey")
BASE = "develop"


def run(argv: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str]:
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, f"not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return done.returncode, (done.stdout + done.stderr).strip()


def busy_lane() -> str | None:
    """The lane a runner is inside right now, read from the running process's own argv.

    `ps -Ao args=`, not `pgrep -af`: macOS pgrep has no `-a`, so it prints bare pids and the
    lane path never appears. That failure is silent and answers "no lane is busy", which is
    the one wrong answer this function must never give -- it would merge into a worktree a
    model is editing. Read the full argv instead, from a flag macOS actually has.
    """
    code, out = run(["ps", "-Ao", "args="], STORM, timeout=30)
    if code:
        return None
    for line in out.splitlines():
        if "qwenlane.py" in line and "/lanes/" in line:
            found = re.search(r"/lanes/([A-Za-z0-9._-]+)", line)
            if found:
                return found.group(1)
    return None


def settled() -> set[str]:
    out: set[str] = set()
    for name in ("integrated.txt", "abandoned.txt"):
        path = STORM / name
        if path.is_file():
            out |= {line.strip() for line in path.read_text().splitlines() if line.strip()}
    return out


def develop_head() -> str | None:
    run(["git", "fetch", "-q", "origin", BASE], MAIN, timeout=600)
    code, sha = run(["git", "rev-parse", f"origin/{BASE}"], MAIN)
    return sha.strip() if not code else None


def refresh_integration(target: str, dry: bool) -> str:
    code, current = run(["git", "rev-parse", "storm/integration"], INTEGRATION)
    if not code and current.strip() == target:
        return "already current"
    behind = "?"
    code, out = run(["git", "rev-list", "--count", f"{current.strip()}..{target}"], MAIN)
    if not code:
        behind = out.strip()
    if dry:
        return f"{behind} commit(s) behind develop"
    run(["git", "fetch", "-q", str(MAIN), f"refs/remotes/origin/{BASE}"], INTEGRATION, 600)
    code, out = run(["git", "checkout", "-q", "-B", "storm/integration", "FETCH_HEAD"], INTEGRATION)
    return f"moved to {target[:9]}" if not code else f"FAILED: {out[:120]}"


def refresh_lane(slug: str, target: str, dry: bool) -> str:
    lane = LANES / slug
    if run(["git", "merge-base", "--is-ancestor", target, "HEAD"], lane)[0] == 0:
        return "already current"
    if dry:
        return "would merge the new base"

    run(["git", "fetch", "-q", str(INTEGRATION), target], lane, 600)
    dirty = bool(run(["git", "status", "--porcelain"], lane)[1].strip())
    stashed = False
    if dirty:
        code, _ = run(["git", "stash", "push", "-u", "-q", "-m", "lane-refresh"], lane)
        stashed = code == 0
        if not stashed:
            return "could not stash its work; left untouched"

    code, out = run(["git", "merge", "--no-edit", "-q", target], lane, 600)
    if code:
        run(["git", "merge", "--abort"], lane)
        if stashed:
            run(["git", "stash", "pop", "-q"], lane)
        return f"CONFLICT merging; left at its old base -- {out.strip().splitlines()[0][:80]}"

    if stashed:
        code, out = run(["git", "stash", "pop", "-q"], lane)
        if code:
            # The merge stands but the lane's own work will not reapply. Say so loudly and
            # leave the stash in place: it is the only copy, and dropping it to make the
            # report tidy would destroy the very work this script exists to preserve.
            return "merged, but ITS WORK IS STASHED and conflicts on pop -- see `git stash list`"
    return "merged, work restored"


def sweep(dry: bool) -> int:
    target = develop_head()
    if not target:
        print("could not read origin/develop")
        return 1
    busy = busy_lane()
    print(f"develop at {target[:9]}")
    print(f"  integration: {refresh_integration(target, dry)}")
    done = settled()
    lanes = sorted(d.name for d in LANES.iterdir() if d.is_dir()) if LANES.is_dir() else []
    moved = 0
    for slug in lanes:
        if slug in done:
            continue
        if slug == busy:
            print(f"  {slug:36} skipped: a runner is working in it now")
            continue
        outcome = refresh_lane(slug, target, dry)
        if outcome != "already current":
            moved += 1
        print(f"  {slug:36} {outcome}")
    print(f"\n{len(lanes)} lane(s), {moved} needed the new base")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="actually move the branches")
    parser.add_argument("--watch", type=int, metavar="SECONDS")
    args = parser.parse_args()
    seen = None
    while True:
        head = develop_head()
        if args.watch and head == seen:
            time.sleep(args.watch)
            continue
        seen = head
        sweep(dry=not args.refresh)
        if not args.watch:
            return 0
        time.sleep(args.watch)


if __name__ == "__main__":
    raise SystemExit(main())
