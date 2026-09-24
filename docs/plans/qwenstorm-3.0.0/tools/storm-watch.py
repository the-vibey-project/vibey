"""Say whether the storm is healthy, and be honest when it cannot tell.

    python3 storm-watch.py                 # one report, then exit
    python3 storm-watch.py --json          # the same report, machine-readable
    python3 storm-watch.py --watch         # poll until something is wrong, then exit
    python3 storm-watch.py --watch --every 120 --stall 90

Exit codes, so this composes with a background runner or a scheduler:
0 healthy, or the queue finished; 1 something is wrong; 2 it could not tell.

WHY NOT `ps`
------------
The obvious watchdog asks whether the processes are running, and on this machine that
question cannot be answered honestly. `ps -Ao args=` returns nothing under the sandbox these
tools run in, `pgrep` has no `-a` on macOS, and `kill -0` is refused for processes it does not
own. Every one of those failures is silent and every one produces the same output as "the
process is gone" -- so the first version of this watchdog announced that the storm had died
while `storm-queue.sh` was sitting there at one hour seventeen minutes, perfectly fine. A
monitor that reports death when its own probe was blocked is worse than no monitor at all,
because it will be believed. Anything here that cannot be established is reported as UNKNOWN
and never as failure (sub-doctrine 10.f: missing evidence stays unknown).

WHAT IT WATCHES INSTEAD
-----------------------
Heartbeats: the mtimes of the files the storm writes as it works. They need no process
introspection, they survive the sandbox, and they answer a better question. A process that is
alive but wedged -- an engine waiting forever on a socket, a loop spinning on a lock -- passes
every liveness check ever written and fails a heartbeat. "Is it running" is not the question
anyone actually has; "is it still getting anything done" is.

  cycle     scratch/storm-cycle.log, written every pass. The outer loop runs on a ten-minute
            timer, so silence well past that is stalled or dead.
  runner    the newest lanes/*/.qwenstorm/lane.log, written continuously while a model works,
            and progress.log, written when a lane starts or ends. Both quiet for an hour means
            nothing is being produced. Either one moving is enough, because a long lane writes
            only lane.log while a gap between lanes writes only progress.log.
  disk      the lanes are full clones and the models are large; running out stops everything
            in a way that looks like a hundred unrelated failures.
  durable   the storm home and this storm root, resolved through symlinks, are not on storage
            the OS empties (10.h, ADR-0057). A storm under /tmp is healthy right up to the
            reboot that deletes it, so this is TROUBLE, not a footnote.
  thrash    lanes *ending* far faster than a lane takes to run. A dead model backend does not
            make the storm go quiet -- it makes every lane fail in seconds, which keeps every
            heartbeat above looking perfectly fresh while the queue burns down producing
            nothing. It is the one failure the heartbeats alone would call healthy.

The model backend gets a direct probe when one is possible, and UNKNOWN when it is not: from
inside the sandbox a refused connection to Ollama is indistinguishable from Ollama being
down, and guessing between those two is exactly what this file refuses to do.
"""

import argparse
import json
import os
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path

import storm_durability

# .absolute(), never .resolve(): tools/ is a symlink into the planning worktree, where specs/
# resolve but lanes/ and integration/ exist only in the runtime root.
STORM = Path(__file__).absolute().parent.parent
LANES = STORM / "lanes"

OK, TROUBLE, DONE, UNKNOWN = "OK", "TROUBLE", "DONE", "UNKNOWN"

# Defaults, every one overridable on the command line. A threshold that cannot be moved is a
# decision taken away from the next person running this on a slower machine (sub-doctrine
# 12.c), and these are all properties of this hardware rather than of the storm.
CYCLE_STALE_MIN = 35  # the outer loop runs every 10 minutes
STALL_MIN = 60  # no lane output AND no progress for this long
MIN_DISK_GB = 5
THRASH_ENDS = 6  # lane endings inside one thrash window
THRASH_WINDOW_MIN = 10
OLLAMA = "http://127.0.0.1:11434/api/tags"


def minutes_since(path: Path) -> float | None:
    """How long since this file was last written, or None if it is not there to ask."""
    try:
        return (time.time() - path.stat().st_mtime) / 60
    except OSError:
        return None


def newest_lane_log() -> Path | None:
    logs = list(LANES.glob("*/.qwenstorm/lane.log")) if LANES.is_dir() else []
    if not logs:
        return None
    return max(logs, key=lambda p: p.stat().st_mtime if p.exists() else 0)


def tail(path: Path, lines: int) -> list[str]:
    try:
        return path.read_text(errors="replace").splitlines()[-lines:]
    except OSError:
        return []


def count_ends() -> int:
    """How many lanes have ended, ever. The delta between two readings is what matters."""
    return sum(1 for line in tail(STORM / "progress.log", 100000) if " end " in line)


def check_finished(_: argparse.Namespace) -> tuple[str, str]:
    if any("queue empty" in line for line in tail(STORM / "progress.log", 40)):
        settled = len(tail(STORM / "integrated.txt", 100000))
        return DONE, f"queue empty; {settled} lane(s) integrated"
    return OK, "queue still has work"


def check_disk(args: argparse.Namespace) -> tuple[str, str]:
    try:
        free = shutil.disk_usage(str(STORM)).free / 1024**3
    except OSError as exc:
        return UNKNOWN, f"could not read free space ({exc.__class__.__name__})"
    if free < args.min_disk:
        return TROUBLE, f"disk low: {free:.1f}G free, floor is {args.min_disk}G"
    return OK, f"{free:.0f}G free"


def check_durable(_: argparse.Namespace) -> tuple[str, str]:
    """The home and this storm root are on storage a reboot keeps (10.h)."""
    home, source = storm_durability.StormHome(os.environ, STORM).resolve()
    gate = storm_durability.DurabilityGate(
        storm_durability.VolatileLocations(os.environ), disposable_root=STORM
    )
    hits = gate.inspect({"home": home, "storm root": STORM})
    if hits:
        where = "; ".join(f"{hit.name} under {hit.location}" for hit in hits)
        return TROUBLE, f"VOLATILE: {where}, lost at reboot; move with {storm_durability.MOVE_IT}"
    return OK, f"durable: home {home} ({source})"


def check_cycle(args: argparse.Namespace) -> tuple[str, str]:
    age = minutes_since(STORM / "scratch/storm-cycle.log")
    if age is None:
        return UNKNOWN, "no cycle log yet -- the outer loop may never have started"
    if age > args.cycle_stale:
        return TROUBLE, f"publish/merge cycle silent {age:.0f}min (it writes every 10)"
    return OK, f"cycle wrote {age:.0f}min ago"


def check_runner(args: argparse.Namespace) -> tuple[str, str]:
    """Either heartbeat moving is enough; a long lane writes only one of them."""
    newest = newest_lane_log()
    lane_age = minutes_since(newest) if newest else None
    prog_age = minutes_since(STORM / "progress.log")
    if lane_age is None and prog_age is None:
        return UNKNOWN, "no lane log and no progress log to read"
    freshest = min(a for a in (lane_age, prog_age) if a is not None)
    if freshest > args.stall:
        last = tail(STORM / "progress.log", 1)
        return TROUBLE, f"stalled {freshest:.0f}min; last: {(last[0] if last else '?')[:70]}"
    where = newest.parent.parent.name if newest else "?"
    return OK, f"producing, {freshest:.0f}min ago ({where})"


def check_backend(_: argparse.Namespace) -> tuple[str, str]:
    """Probe Ollama, and refuse to guess when the probe itself may be what failed."""
    try:
        with urllib.request.urlopen(OLLAMA, timeout=15) as response:  # noqa: S310 - fixed localhost
            body = json.loads(response.read().decode("utf-8", "replace"))
        names = [m.get("name", "?") for m in body.get("models", [])]
        return OK, f"ollama up, {len(names)} model(s)"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        # A refused connection from inside the sandbox looks exactly like Ollama being down.
        # Saying "the backend is dead" here would be a guess between two very different
        # worlds, so it is not said; the thrash check is what actually catches a dead engine,
        # from evidence that does not depend on reaching the network at all.
        return UNKNOWN, f"cannot reach ollama from here ({exc.__class__.__name__}); see thrash"


CHECKS = (
    ("finished", check_finished),
    ("disk", check_disk),
    ("durable", check_durable),
    ("cycle", check_cycle),
    ("runner", check_runner),
    ("backend", check_backend),
)


def report(args: argparse.Namespace, thrash: tuple[str, str] | None = None) -> dict:
    results = {name: check(args) for name, check in CHECKS}
    if thrash is not None:
        results["thrash"] = thrash
    if any(state == TROUBLE for state, _ in results.values()):
        overall = TROUBLE
    elif results["finished"][0] == DONE:
        overall = DONE
    else:
        overall = OK
    return {
        "overall": overall,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": {
            name: {"state": state, "detail": detail} for name, (state, detail) in results.items()
        },
    }


def render(result: dict) -> str:
    lines = [f"{result['at']}  {result['overall']}"]
    for name, item in result["checks"].items():
        lines.append(f"  {item['state']:8} {name:9} {item['detail']}")
    return "\n".join(lines)


def exit_code(result: dict) -> int:
    if result["overall"] == TROUBLE:
        return 1
    if all(item["state"] == UNKNOWN for item in result["checks"].values()):
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="poll until something is wrong")
    parser.add_argument("--every", type=int, default=120, metavar="SECONDS")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--cycle-stale", type=float, default=CYCLE_STALE_MIN, metavar="MIN")
    parser.add_argument("--stall", type=float, default=STALL_MIN, metavar="MIN")
    parser.add_argument("--min-disk", type=float, default=MIN_DISK_GB, metavar="GB")
    parser.add_argument("--thrash", type=int, default=THRASH_ENDS, metavar="N")
    parser.add_argument("--thrash-window", type=float, default=THRASH_WINDOW_MIN, metavar="MIN")
    args = parser.parse_args()

    if not args.watch:
        result = report(args)
        print(json.dumps(result, indent=2) if args.json else render(result))
        return exit_code(result)

    # In --watch nothing is printed while everything is fine: this is meant to be run by
    # something that treats a line of output as an event worth waking someone for, and a
    # reassuring heartbeat every two minutes at 3am is how a person learns to ignore it.
    baseline, marked = count_ends(), time.time()
    thrash: tuple[str, str] | None = None
    while True:
        elapsed = (time.time() - marked) / 60
        if elapsed >= args.thrash_window:
            ended = count_ends() - baseline
            if ended >= args.thrash:
                thrash = (
                    TROUBLE,
                    f"{ended} lanes ended in {elapsed:.0f}min -- far faster than a lane runs, "
                    "so the engine is almost certainly failing instantly",
                )
            else:
                thrash = (OK, f"{ended} lane(s) ended in the last {elapsed:.0f}min")
            baseline, marked = count_ends(), time.time()
        result = report(args, thrash)
        if result["overall"] != OK:
            print(json.dumps(result, indent=2) if args.json else render(result), flush=True)
            return exit_code(result)
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
