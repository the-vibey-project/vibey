"""Pause the storm the way a pause should go: quiet the watch, stop it softly, record it.

    python3 storm-stop.py                  # say what it would do; change nothing
    python3 storm-stop.py --stop           # do it, and push the snapshot
    python3 storm-stop.py --stop --no-push # do it, commit the snapshot, leave it local

Four things happen, and the order is the whole point.

1. THE WATCH GOES FIRST. `storm-watch.py --watch` exists to shout when the storm stops
   producing, so stopping the storm while it is armed produces exactly the alarm it was
   built for — at 3am, on the operator's phone, about something the operator asked for.
   A monitor that cries during a planned shutdown is a monitor that gets muted, and a muted
   monitor is worse than none. It is quieted before anything else is touched.

2. THE STATE IS READ BEFORE ANYTHING DIES. Which lane was in flight, how far the ledger got,
   where integration was pointing: all of it is only true while the processes are alive. A
   snapshot taken after the kill is a snapshot of the wreckage, which is the one thing nobody
   needs. Read first, then stop, then write what was read.

3. THE STOP IS SOFT AND ORDERED. SIGTERM to `storm-queue.sh` first, so that no new lane starts
   while the rest is being brought down; then the in-flight `qwenlane.py`; then
   `storm-cycle.py`. Nothing is ever SIGKILLed here and no lane directory is touched. A lane
   without a `.qwenstorm/result.json` is simply unfinished and runs again on resume, which is
   the whole reason the runner keeps its record in files rather than in memory.

4. THE SNAPSHOT IS COMMITTED AND PUSHED. A pause recorded only on the machine that paused is
   not recorded: /tmp is wiped between sessions and `lanes/` goes with it. The durable record
   is `integrated.txt`, `abandoned.txt` and this file in git.

WHAT IT WILL NOT DO
-------------------
It never SIGKILLs, and it never claims a process stopped that it cannot see stop. If the
process probe itself is unavailable — `ps` returns nothing under the sandbox these tools run
in, and `kill -0` is refused for processes this one does not own — it stops and says so rather
than reporting a clean shutdown it never observed (sub-doctrine 10.f). And if the push is
refused it says that too, plainly: the commit is safe in git either way, and a snapshot
reported as pushed when it was not is the failure this whole file exists to avoid.
"""

import argparse
import re
import shutil
import subprocess
import time
from pathlib import Path

# .absolute(), never .resolve(): tools/ is a symlink into the planning worktree, where specs/
# resolve but lanes/ and integration/ exist only in the runtime root.
STORM = Path(__file__).absolute().parent.parent
LANES = STORM / "lanes"
INTEGRATION = STORM / "integration"
# The worktree that actually owns RUN-STATE.md -- tools/ is a symlink into it, so resolving
# this file (rather than .absolute()) is the one place the real path is wanted.
PLANS = Path(__file__).resolve().parent.parent

# Stopped in this order, and the order is load-bearing: the watch is quieted before the thing
# it watches, and the queue is stopped before the lane so nothing new starts mid-shutdown.
ORDER = (
    ("watch", "storm-watch.py"),
    ("queue", "storm-queue.sh"),
    ("lane", "qwenlane.py"),
    ("cycle", "storm-cycle.py"),
)


def run(argv: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str]:
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return 127, ""
    return done.returncode, (done.stdout + done.stderr).strip()


def process_table() -> list[tuple[int, str]] | None:
    """(pid, argv) for everything running, or None when the question cannot be asked.

    None is a real answer and is never confused with "nothing is running". Under the sandbox
    these tools run in, `ps` returns nothing at all -- and a shutdown script that reads that
    as "already stopped" reports a clean pause over a storm that is still going.
    """
    code, out = run(["ps", "-Ao", "pid,args="], STORM, timeout=60)
    rows = [line.strip() for line in out.splitlines() if line.strip()]
    if code or len(rows) < 10:  # a real machine always has more than ten processes
        return None
    table = []
    for line in rows:
        found = re.match(r"(\d+)\s+(.*)", line)
        if found:
            table.append((int(found.group(1)), found.group(2)))
    return table


# A shell running a command string, `/bin/zsh -c '...'`. Its argv contains every script name
# the command mentions, so a substring match finds the launcher as readily as the thing
# launched -- and SIGTERMing the launcher kills the caller's own shell while leaving the storm
# running. Whoever is being stopped is a process whose own argv is the script, never a shell
# quoting it.
WRAPPER = re.compile(r"^\S*/?(?:sh|bash|zsh|dash|ksh)\s+-c\b")


def is_invocation(argv: str, needle: str) -> bool:
    if WRAPPER.match(argv) or "storm-stop.py" in argv or "grep" in argv.split()[:1]:
        return False
    # the script must be a whole argument -- `tools/storm-watch.py`, not a mention inside one
    return any(token == needle or token.endswith("/" + needle) for token in argv.split())


def targets(table: list[tuple[int, str]]) -> list[tuple[str, int, str]]:
    found = []
    for kind, needle in ORDER:
        for pid, argv in table:
            if is_invocation(argv, needle):
                found.append((kind, pid, argv))
    return found


def lane_in_flight(table: list[tuple[int, str]]) -> str | None:
    """Which lane a runner is actually inside — judged the same way as everything else.

    `is_invocation`, not a substring test. A plain `"qwenlane.py" in argv` matches any process
    that merely mentions it, and during development this reported a lane named `foo` out of a
    test process's own arguments. A snapshot that names the wrong lane as in flight is worse
    than one that names none: it is the line a person reads first on resume.
    """
    for _, argv in table:
        if is_invocation(argv, "qwenlane.py"):
            found = re.search(r"/lanes/([A-Za-z0-9._-]+)", argv)
            if found:
                return found.group(1)
    return None


def lines_of(name: str) -> list[str]:
    path = STORM / name
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if line.strip()]


def gather(table: list[tuple[int, str]]) -> dict:
    """Everything worth recording, read while the storm is still alive."""
    lanes = sorted(d.name for d in LANES.iterdir() if d.is_dir()) if LANES.is_dir() else []
    settled = set(lines_of("integrated.txt")) | set(lines_of("abandoned.txt"))
    code, head = run(["git", "rev-parse", "--short", "HEAD"], INTEGRATION)
    return {
        "when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "in_flight": lane_in_flight(table),
        "queue": len(lines_of("queue.txt")),
        "integrated": lines_of("integrated.txt"),
        "abandoned": lines_of("abandoned.txt"),
        "lanes": lanes,
        "unsettled": [s for s in lanes if s not in settled],
        "unfinished": [s for s in lanes if not (LANES / s / ".qwenstorm/result.json").is_file()],
        "integration": head.strip() if not code else "unknown",
        "running": [(kind, pid) for kind, pid, _ in targets(table)],
    }


def stop(table: list[tuple[int, str]], dry: bool) -> list[str]:
    """SIGTERM in ORDER, then verify. Never SIGKILL, and never claim an unobserved stop."""
    notes = []
    for kind, pid, _ in targets(table):
        if dry:
            notes.append(f"would SIGTERM {kind} ({pid})")
            continue
        try:
            import os
            import signal

            os.kill(pid, signal.SIGTERM)
            notes.append(f"SIGTERM {kind} ({pid})")
        except (ProcessLookupError, PermissionError) as exc:
            notes.append(f"{kind} ({pid}): {exc.__class__.__name__}")
    if dry:
        return notes
    time.sleep(6)
    after = process_table()
    if after is None:
        notes.append("cannot re-read the process table; NOT claiming a clean stop")
        return notes
    still = targets(after)
    if still:
        notes.append(
            "still alive after SIGTERM: "
            + ", ".join(f"{k}({p})" for k, p, _ in still)
            + " -- left running deliberately; this never escalates to SIGKILL"
        )
    else:
        notes.append("all stopped")
    return notes


def snapshot(state: dict, notes: list[str]) -> str:
    settled = "\n".join(
        [f"integrated  {s}" for s in state["integrated"]]
        + [f"abandoned   {s}" for s in state["abandoned"]]
    )
    flight = state["in_flight"]
    flight_note = (
        f"`{flight}` was in flight and has no `result.json`, so it is unfinished and runs "
        "again on resume."
        if flight
        else "No lane was in flight."
    )
    unfinished = state["unfinished"]
    return f"""# QwenStorm 3.0.0 — run state

Snapshot {state["when"]}, written by `tools/storm-stop.py` at a deliberate pause.

The runner's durable record is `integrated.txt` and `abandoned.txt`: a lane in neither is
unsettled, whatever exists under `lanes/`. `lanes/` lives in /tmp and is wiped between
sessions, so nothing here depends on it surviving.

- queue: **{state["queue"]} lanes** · integrated: **{len(state["integrated"])}** · abandoned: **{len(state["abandoned"])}**
- lane worktrees at the pause: **{len(state["lanes"])}** · unsettled: **{len(state["unsettled"])}**
- integration branch: `{state["integration"]}`

## How it was stopped

{chr(10).join("- " + n for n in notes)}

{flight_note}

Unfinished at the pause ({len(unfinished)}): {", ".join(f"`{s}`" for s in unfinished) or "none"}

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
python3 tools/storm-watch.py --watch    # silent until something is wrong
```

## Settled

```
{settled}
```
"""


def publish(text: str, dry: bool, push: bool) -> list[str]:
    target = PLANS / "RUN-STATE.md"
    if dry:
        return [f"would write {target.name}, commit it, and {'push' if push else 'stop there'}"]
    target.write_text(text)
    notes = [f"wrote {target}"]
    code, _ = run(["git", "add", "--", str(target)], PLANS)
    if code:
        return notes + ["could not stage the snapshot"]
    code, out = run(
        ["git", "commit", "-q", "-m", "docs(storm): snapshot the run at a pause"], PLANS
    )
    if code and "nothing to commit" not in out:
        return notes + [f"commit refused: {out.splitlines()[-1][:90] if out else code}"]
    notes.append("committed")
    if not push:
        return notes + ["not pushed (--no-push); the snapshot is safe in git"]
    code, out = run(["git", "push"], PLANS, timeout=2400)
    if code:
        # Said plainly rather than smoothed over: the gate refusing is a normal outcome, and a
        # snapshot reported as pushed when it was not is the one failure that matters here.
        notes.append(f"PUSH REFUSED: {out.splitlines()[-1][:90] if out else code}")
        notes.append("the commit is local and safe; push it once the gate is happy")
    else:
        notes.append("pushed")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop", action="store_true", help="actually stop, record and push")
    parser.add_argument("--no-push", action="store_true", help="commit the snapshot, do not push")
    args = parser.parse_args()

    if shutil.which("ps") is None:
        print("storm-stop: no `ps` on PATH; cannot see what is running, so nothing is touched")
        return 2
    table = process_table()
    if table is None:
        print(
            "storm-stop: the process table came back empty, which means the probe was refused "
            "rather than that nothing is running (the sandbox blocks `ps`). Nothing has been "
            "signalled. Re-run outside the sandbox."
        )
        return 2

    state = gather(table)
    running = state["running"]
    print(
        f"storm-stop: {len(running)} storm process(es): "
        + (", ".join(f"{k}({p})" for k, p in running) or "none")
    )
    if state["in_flight"]:
        print(f"  in flight: {state['in_flight']}")
    print(
        f"  queue {state['queue']} · integrated {len(state['integrated'])} · lanes {len(state['lanes'])}"
    )

    notes = stop(table, dry=not args.stop)
    for note in notes:
        print(f"  {note}")
    for note in publish(snapshot(state, notes), dry=not args.stop, push=not args.no_push):
        print(f"  {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
