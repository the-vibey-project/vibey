"""One QwenStorm lane: qwenloop's own storm item loop, pointed at one issue and one clone.

`qwenloop run --storm` sweeps every open issue and PR of a repository in one shared checkout.
This driver reuses the same pieces -- `build_plan` for the item plan, `_run_plan` for each
bounded run, and the storm's CDD repair prompt for attempts 2..N -- but for a single issue in
an isolated clone, so several lanes can run side by side without touching each other or the
operator's main checkout.

Usage: python qwenlane.py LANE_DIR ISSUE_NUMBER TITLE BODY_FILE [--max-attempts 3]
"""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

# Dogfood the latest *verified* qwenloop: the integration branch's own source, not the
# installed release. A lane's edit_file tool (#346) exists only there.
sys.path.insert(0, str(Path(__file__).parent.parent / "integration/src/vibey_runners/qwen/src"))

from qwenloop.application.storm import build_plan
from qwenloop.cli.app import _load_config, _run_plan, _server_for, _tracked_repository_context
from qwenloop.domain.model import RepoItem, RunStatus

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

    config = _load_config()
    server, profile = _server_for(config)
    attempts: list[dict[str, object]] = []
    completed = False
    for attempt in range(1, args.max_attempts + 1):
        text = plan_text
        if attempt > 1:
            text += REPAIR.format(attempt=attempt, max_attempts=args.max_attempts)
        try:
            state = asyncio.run(
                _run_plan(
                    server,
                    profile,
                    lane,
                    str(uuid.uuid4()),
                    text,
                    config.max_turns,
                    startup_timeout_seconds=config.startup_timeout_seconds,
                    desktop_notifications=True,
                    max_empty_reply_retries=config.max_empty_reply_retries,
                    max_recorded_argument_chars=config.max_recorded_argument_chars,
                    empty_reply_reasoning_excerpt_chars=config.empty_reply_reasoning_excerpt_chars,
                )
            )
        except (OSError, RuntimeError) as exc:
            # The storm treats these as "unavailable" and stops. A lane keeps the worktree and
            # spends its next attempt instead: qwenloop's chat call has a fixed 300 s read
            # timeout, which a long prompt on a laptop can exceed without anything being wrong.
            attempts.append({"attempt": attempt, "status": "unavailable", "error": str(exc)[:300]})
            print(
                f"issue#{args.issue}\tattempt {attempt}/{args.max_attempts}\tunavailable\t{exc}",
                flush=True,
            )
            continue
        attempts.append({"attempt": attempt, "status": state.status.value, "turns": state.turns})
        restored = restore_destroyed_files(lane)
        if restored:
            attempts[-1]["restored"] = restored
            plan_text += (
                "\n## Files restored after the previous attempt\n"
                "These files lost most of their lines to a whole-file rewrite and were restored "
                "from git: " + ", ".join(restored) + ". Re-apply only your intended change to "
                "each, using the targeted replacement in the Lane editing rules.\n"
            )
        print(
            f"issue#{args.issue}\tattempt {attempt}/{args.max_attempts}\t{state.status.value}\t{state.turns}",
            flush=True,
        )
        if state.status is RunStatus.COMPLETED:
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
    main()
