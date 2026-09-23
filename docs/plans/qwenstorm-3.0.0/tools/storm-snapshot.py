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
HEAVY_HOOKS = "test-suite,coverage-gates"
SNAPSHOT_PATH = "docs/plans/qwenstorm-3.0.0/RUN-STATE.md"


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
unsettled, whatever exists under `lanes/`. `lanes/` lives in /tmp and is wiped between
sessions, so nothing here depends on it surviving.

- queue: **{state["queue"]} lanes** · integrated: **{len(state["integrated"])}** · abandoned: **{len(state["abandoned"])}**
- lane worktrees: **{len(state["lanes"])}** · finished awaiting review: **{len(state["finished"])}** · unsettled: **{len(state["unsettled"])}**
- integration branch: `{state["integration"]}`
- last line of progress.log: `{state["last"]}`

Still running or never finished ({len(unfinished)}): {", ".join(f"`{s}`" for s in unfinished) or "none"}
{note_block}

## How to resume

```bash
cd /private/tmp/claude-501/storm/qwenstorm-3.0.0
touch UNATTENDED                      # batch review; a finished lane does not block the queue
nohup bash tools/storm-queue.sh > scratch/storm-run.log 2>&1 < /dev/null & disown
```

macOS has no `setsid`; `nohup ... & disown` is what survives the launching shell.
`storm-queue.sh` starts `storm-cycle.py` itself, so the outer loop needs no separate command.
A lane with a `.qwenstorm/result.json` is treated as finished and awaiting review; delete that
file to have it run again.

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
        return changed == {SNAPSHOT_PATH}
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


def publish(text: str, commit: bool, push: bool) -> list[str]:
    STATE.write_text(text)
    notes = [f"wrote {STATE.name}"]
    if not commit:
        return notes
    code, _ = run(["git", "add", "--", str(STATE)], PLANS, timeout=120)
    if code:
        return notes + ["could not stage it"]
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
    code, out = run(["git", "push"], PLANS, env=env)
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
