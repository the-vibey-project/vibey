"""One QwenStorm lane: qwenloop's own storm item loop, pointed at one issue and one clone.

`qwenloop run --storm` sweeps every open issue and PR of a repository in one shared checkout.
This driver reuses the same pieces -- `build_plan` for the item plan, `_run_plan` for each
bounded run, and the storm's CDD repair prompt for attempts 2..N -- but for a single issue in
an isolated clone, so several lanes can run side by side without touching each other or the
operator's main checkout.

Usage: python qwenlane.py LANE_DIR ISSUE_NUMBER TITLE BODY_FILE [--max-attempts 3]

Each attempt runs in a child process of this same script (`--attempt SPEC`), watched by
`lane_watchdog`: a per-attempt and a per-lane wall clock and a stall watchdog, declared in
storm.toml `[lane]`, so one hung attempt can no longer hang the storm.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Dogfood the latest *verified* qwenloop: the integration branch's own source, not the
# installed release. A lane's edit_file tool (#346) exists only there.
sys.path.insert(0, str(Path(__file__).parent.parent / "integration/src/vibey_runners/qwen/src"))

import storm_paths
from lane_watchdog import REPORT_FD_ENV, ChildGuard, LaneAttempts, LaneLimits
from qwenloop.application.storm import build_plan
from qwenloop.cli.app import _load_config, _run_plan, _server_for, _tracked_repository_context
from qwenloop.domain.model import RepoItem, RunStatus

# The storm root, for storm.toml's `[lane]` limits and progress.log. .absolute(), never
# .resolve(): tools/ is a symlink, and storm_paths explains what resolving it costs.
STORM = storm_paths.storm(__file__)

# Verbatim from qwenloop.cli.app._run_storm, so a lane repairs exactly the way the storm does.
REPAIR = (
    "\n## CDD repair iteration\n"
    "This is repair attempt {attempt} of {max_attempts} for the same item. "
    "Inspect the current worktree and the prior evidence, preserve sound "
    "changes, diagnose the failed criterion, and redirect any divergence "
    "towards convergence. Do not abandon this item for another backlog item.\n"
)


def restore_destroyed_files(lane: Path) -> list[str]:
    """Restore tracked files a whole-file rewrite gutted (lost over half of 40+ lines).

    A small model with only `write_file` tends to "add a test" by writing just the test,
    deleting the rest of the file. That is never an intended change in this storm.
    """
    import subprocess

    changed = subprocess.run(
        ["git", "diff", "--numstat"], cwd=lane, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    restored = []
    for row in changed:
        added, deleted, path = row.split("\t", 2)
        if added == "-":  # binary
            continue
        before = subprocess.run(
            ["git", "show", f"HEAD:{path}"], cwd=lane, capture_output=True, text=True
        ).stdout.count("\n")
        if before >= 40 and int(deleted) - int(added) > before // 2:
            subprocess.run(["git", "checkout", "--", path], cwd=lane, check=True)
            restored.append(path)
    return restored


def attempt_argv(spec: Path) -> list[str]:
    """How one attempt is started: this script again, as its own watched process.

    The same script rather than a new one, so everything that finds a lane by its
    `qwenlane.py` argv -- storm-queue.sh's wait, storm-stop.py -- finds its attempt too.
    """
    return [sys.executable, str(Path(__file__).absolute()), "--attempt", str(spec)]


def run_attempt(spec_path: Path) -> int:
    """The child half: run one plan with qwenloop and leave the verdict for the parent.

    In-process qwenloop could not be bounded -- a model call blocks on a worker thread no
    one can cancel -- so an attempt is a process of its own that the parent can stop.
    """
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    # Popped, not read: the commands this attempt starts inherit its environment, and the
    # report channel is for the attempt alone.
    guard = ChildGuard(int(os.environ.pop(REPORT_FD_ENV)), float(spec["poll_seconds"]))
    guard.record_escaping_subprocesses()
    if "parent_pid" in spec:
        guard.die_with(int(spec["parent_pid"]))
    config = _load_config()
    server, profile = _server_for(config)
    try:
        state = asyncio.run(
            _run_plan(
                server,
                profile,
                Path(spec["lane"]),
                spec["run_id"],
                spec["plan"],
                config.max_turns,
                startup_timeout_seconds=config.startup_timeout_seconds,
                desktop_notifications=True,
            )
        )
    except (OSError, RuntimeError) as exc:
        # The storm treats these as "unavailable" and stops. A lane keeps the worktree and
        # spends its next attempt instead: qwenloop's chat call has a fixed 300 s read
        # timeout, which a long prompt on a laptop can exceed without anything being wrong.
        guard.report({"status": "unavailable", "error": str(exc)[:300]})
        return 0
    guard.report({"status": state.status.value, "turns": state.turns})
    return 0


def main() -> None:
    import os

    # The storm's model is chosen in one file beside this driver, not per lane.
    storm_config = Path(__file__).parent.parent / "qwen-storm.toml"
    if storm_config.is_file():
        os.environ.setdefault("QWENLOOP_CONFIG", str(storm_config))
    parser = argparse.ArgumentParser()
    parser.add_argument("lane_dir", type=Path)
    parser.add_argument("issue", type=int)
    parser.add_argument("title")
    parser.add_argument("body_file", type=Path)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--author", default="Adam Matthew Steinberger")
    args = parser.parse_args()

    lane = args.lane_dir.resolve()
    rules = (Path(__file__).parent.parent / "EDITING-RULES.md").read_text()
    item = RepoItem(number=args.issue, title=args.title, body=args.body_file.read_text() + rules)
    plan_text = build_plan(
        repo="vibey",
        issues=[item],
        pull_requests=[],
        author=args.author,
        repository_context=_tracked_repository_context(lane),
    )
    state_dir = lane / ".qwenstorm"
    state_dir.mkdir(exist_ok=True)
    (state_dir / "plan.md").write_text(plan_text)

    # Loaded here only so a bad qwen-storm.toml fails the lane at once, before an attempt.
    _load_config()
    lanes = LaneAttempts(
        lane,
        slug=lane.name,
        issue=args.issue,
        max_attempts=args.max_attempts,
        limits=LaneLimits.declared(STORM),
        progress_log=STORM / "progress.log",
        child_argv=attempt_argv,
    )
    attempts: list[dict[str, object]] = []
    completed = False
    for attempt in range(1, args.max_attempts + 1):
        text = plan_text
        if attempt > 1:
            text += REPAIR.format(attempt=attempt, max_attempts=args.max_attempts)
        record = lanes.run(attempt, text)
        if record is None:
            break  # the lane's wall clock is spent; LaneAttempts said so in progress.log
        if record["status"] == "stopped":
            # Signalled (storm-stop.py). No result.json: an unfinished lane is run again on
            # restart, exactly as it was before attempts had a process of their own.
            raise SystemExit(143)
        attempts.append(record)
        if record["status"] in {"unavailable", "crashed"}:
            print(
                f"issue#{args.issue}\tattempt {attempt}/{args.max_attempts}\t"
                f"{record['status']}\t{record.get('error', '')}",
                flush=True,
            )
            continue
        restored = restore_destroyed_files(lane)
        if restored:
            record["restored"] = restored
            plan_text += (
                "\n## Files restored after the previous attempt\n"
                "These files lost most of their lines to a whole-file rewrite and were restored "
                "from git: " + ", ".join(restored) + ". Re-apply only your intended change to "
                "each, using the targeted replacement in the Lane editing rules.\n"
            )
        print(
            f"issue#{args.issue}\tattempt {attempt}/{args.max_attempts}\t{record['status']}\t{record['turns']}",
            flush=True,
        )
        if record["status"] == RunStatus.COMPLETED.value:
            # A verdict is never completion evidence by itself (CDD, sub-doctrine 9.c): a run
            # that claims completion with no surviving change -- nothing written, or its only
            # writes gutted a file and were restored -- has not done the item.
            import subprocess

            diff = subprocess.run(
                [
                    "git",
                    "status",
                    "--porcelain",
                    "--untracked-files=all",
                    "--",
                    ".",
                    ":!.qwenstorm",
                    ":!.qwenloop",
                    ":!.venv",
                ],
                cwd=lane,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            if not diff or restored:
                attempts[-1]["status"] = "claimed-complete-without-surviving-changes"
                plan_text += (
                    "\n## The previous attempt claimed completion but changed nothing that survived\n"
                    "Completion needs a real, tested change in the files named under 'Where to change'. "
                    "Make the change with targeted replacements, run the checks, then report.\n"
                )
                continue
            completed = True
            break
    (state_dir / "result.json").write_text(
        json.dumps({"issue": args.issue, "completed": completed, "attempts": attempts}, indent=2)
    )
    print(f"issue#{args.issue}\t{'completed' if completed else 'failed'}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--attempt":
        raise SystemExit(run_attempt(Path(sys.argv[2])))
    main()
