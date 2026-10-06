# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The daily self-healer's deterministic half (ADR-0083).

    python scripts/self_healer.py survey OUT_DIR    # failing lanes on develop -> OUT_DIR/failures.json
    python scripts/self_healer.py rerun OUT_DIR     # re-run allowlisted flakes -> OUT_DIR/remaining.json
    python scripts/self_healer.py repair            # run every declared repair, in order
    python scripts/self_healer.py guard PATCH       # exit 1 if a repair changed a path it may not
    python scripts/self_healer.py lock-advisories   # take the fixed release of each pip-audit finding
    python scripts/self_healer.py setting KEY       # one [self_healer] value, for the workflow

`repair`, `guard` and `setting` take `--lane TABLE` to read another table of the same shape:
the daily documentation updater is `--lane docs_updater` -- the same runner and the same guard,
declared repairs and allowed paths of its own, rather than a second copy of either.

What it does, and in what order, is declared in `scripts/daily_lanes.toml` `[self_healer]`.
Every failure class it repairs here was a real red develop: a generated page left stale by a
release commit, a new advisory with a fixed release published, a flake that passes on a re-run
(2026-10-05). What it cannot reach, `.github/workflows/self-healer.yml` hands to the
`keep-green` continuation prompt. Nothing here merges, approves, releases or deletes (12.d):
its forge mutations are re-runs of failed jobs, capped, on an allowlist.

Status is evidence-bounded (10.f): the survey names its object (the newest run of each workflow
on the branch), its source (the Actions API) and its cutoff (the window's start), and a failure
it could not read is reported, never counted as green.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from scripts.continuation_prompts import GitPatchPaths
    from scripts.interfaces.self_healer_interface import (
        AdvisoryLockInterface,
        ArgvRunnerInterface,
        RunForgeInterface,
        SelfHealerInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from continuation_prompts import GitPatchPaths  # type: ignore[import-not-found,no-redef]
    from interfaces.self_healer_interface import (  # type: ignore[import-not-found,no-redef]
        AdvisoryLockInterface,
        ArgvRunnerInterface,
        RunForgeInterface,
        SelfHealerInterface,
    )

REPO = Path(__file__).resolve().parents[1]
CONFIG = "scripts/daily_lanes.toml"
FAILED = {"failure", "timed_out", "startup_failure"}


class GhRunForge(RunForgeInterface):
    """The Actions API through `gh`. A failed read raises: an unread forge is not green."""

    def runs(self, branch: str, since: datetime) -> list[dict[str, Any]]:
        proc = subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "GET",
                "repos/{owner}/{repo}/actions/runs",
                "-f",
                f"created=>={since.strftime('%Y-%m-%dT%H:%M:%SZ')}",
                "-f",
                "per_page=100",
                "--paginate",
                "--jq",
                ".workflow_runs[] | @json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        proc.check_returncode()
        # Filtered to the branch here, not by the API's `branch` filter, which answered with
        # weeks-old runs for some events (2026-10-06): the window bounds the read instead.
        runs = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        return [run for run in runs if run.get("head_branch") == branch]

    def rerun_failed(self, run_id: int) -> bool:
        proc = subprocess.run(
            ["gh", "run", "rerun", str(run_id), "--failed"],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode == 0


class SubprocessArgvRunner(ArgvRunnerInterface):
    """Runs an argv list in a directory and keeps its output."""

    def run(self, argv: list[str], cwd: Path) -> tuple[int, str]:
        try:
            proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
        except OSError as missing:  # a declared tool that is not installed is a failed repair
            return 127, str(missing)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


class SelfHealer(SelfHealerInterface):
    """Finds what is red on the branch, re-runs what it may, applies the scripted repairs."""

    def __init__(
        self,
        forge: RunForgeInterface,
        runner: ArgvRunnerInterface,
        settings: dict[str, Any],
        root: Path,
    ) -> None:
        self._forge = forge
        self._runner = runner
        self._root = root
        self.branch = str(settings.get("branch", "develop"))
        self.window = timedelta(hours=float(settings.get("window_hours", 24)))
        self._events = {str(e) for e in settings.get("events", ["push", "schedule"])}
        self._rerun = {str(w) for w in settings.get("rerun_workflows", [])}
        self._max_attempts = int(settings.get("max_attempts", 1))
        self._max_reruns = int(settings.get("max_reruns", 5))
        self._repairs = [dict(r) for r in settings.get("repair", [])]
        guard = settings.get("guard", {})
        self._allowed = [re.compile(str(p)) for p in guard.get("allowed_paths", [])]

    def failing(self, now: datetime) -> list[dict[str, Any]]:
        newest: dict[str, dict[str, Any]] = {}
        for run in self._forge.runs(self.branch, now - self.window):
            if run.get("status") != "completed" or run.get("event") not in self._events:
                continue
            workflow = Path(str(run.get("path", ""))).name
            if workflow not in newest or str(run.get("created_at")) > str(
                newest[workflow].get("created_at")
            ):
                newest[workflow] = run
        return [
            {
                "workflow": workflow,
                "name": run.get("name", workflow),
                "id": int(run["id"]),
                "attempt": int(run.get("run_attempt", 1)),
                "event": run.get("event"),
                "conclusion": run.get("conclusion"),
                "created_at": run.get("created_at"),
                "url": run.get("html_url", ""),
            }
            for workflow, run in sorted(newest.items())
            if run.get("conclusion") in FAILED
        ]

    def rerun(self, failing: list[dict[str, Any]]) -> list[dict[str, Any]]:
        done: list[dict[str, Any]] = []
        for lane in failing:
            if len(done) >= self._max_reruns:
                break
            if (
                lane["workflow"] in self._rerun
                and lane["attempt"] <= self._max_attempts
                and self._forge.rerun_failed(int(lane["id"]))
            ):
                done.append(lane)
        return done

    def repair(self) -> list[dict[str, Any]]:
        results = []
        sha = ""
        for spec in self._repairs:
            argv = [str(part) for part in spec["argv"]]
            if any("{integration_sha}" in part for part in argv):
                # Resolved, not declared: the tip of the integration branch as this run sees
                # it, which is always an ancestor of the branch the result merges into.
                if not sha:
                    code, out = self._runner.run(
                        ["git", "rev-parse", f"origin/{self.branch}"], self._root
                    )
                    sha = out.strip() if code == 0 else ""
                if not sha:
                    results.append(
                        {"name": spec.get("name", argv[0]), "code": 1, "tail": out[-600:]}
                    )
                    continue
                argv = [part.replace("{integration_sha}", sha) for part in argv]
            code, output = self._runner.run(argv, self._root / str(spec.get("cwd", ".")))
            results.append(
                {"name": spec.get("name", " ".join(argv)), "code": code, "tail": output[-600:]}
            )
        return results

    def refused(self, touched: list[tuple[str, str]] | None) -> list[str]:
        # Fails closed, as the continuation lane's guard does: what git cannot read, or
        # reads as changing nothing, is not let through.
        if touched is None:
            return ["(a patch git cannot apply to HEAD)"]
        if not touched:
            return ["(a patch that changes no path)"]
        paths = {path for _, path in touched}
        return sorted(p for p in paths if not any(rule.search(p) for rule in self._allowed))


class AdvisoryLock(AdvisoryLockInterface):
    """Takes the fixed release of every Python dependency pip-audit reports, in `uv.lock`.

    Only a finding that names a fixed version is acted on; one without is the business of a
    declared, expiring exception a person approves (keep-green's step 3), never of this."""

    def __init__(self, runner: ArgvRunnerInterface, root: Path) -> None:
        self._runner = runner
        self._root = root

    def fixable(self, report: str) -> list[str]:
        data = json.loads(report)
        return sorted(
            {
                str(dep["name"])
                for dep in data.get("dependencies", [])
                if any(v.get("fix_versions") for v in dep.get("vulns", []))
            }
        )

    def run(self) -> int:
        # pip-audit exits 1 when it finds something; its JSON is the evidence either way.
        _, report = self._runner.run(
            [
                "uv",
                "run",
                "pip-audit",
                "--skip-editable",
                "--progress-spinner",
                "off",
                "-f",
                "json",
            ],
            self._root,
        )
        start = report.find("{")
        try:
            names = self.fixable(report[start:] if start >= 0 else report)
        except json.JSONDecodeError:
            print("lock-advisories: pip-audit produced no readable report", file=sys.stderr)
            return 1
        if not names:
            print("lock-advisories: no Python advisory with a fixed release")
            return 0
        argv = ["uv", "lock"] + [arg for name in names for arg in ("--upgrade-package", name)]
        code, output = self._runner.run(argv, self._root)
        print(f"lock-advisories: {' '.join(argv)} -> exit {code}\n{output[-600:]}")
        return code


def settings(root: Path, lane: str = "self_healer") -> dict[str, Any]:
    """One lane's table (`[self_healer]` unless named). Module-level: the CLI's one loader,
    shared with the tests."""
    data = tomllib.loads((root / CONFIG).read_text(encoding="utf-8"))
    return dict(data[lane])


def table(lanes: list[dict[str, Any]], since: datetime, branch: str) -> str:
    """The survey as Markdown for the step summary. Module-level beside `settings`."""
    head = (
        f"### Failing on `{branch}` — newest run per workflow since "
        f"{since.strftime('%Y-%m-%dT%H:%MZ')} (Actions API)\n\n"
    )
    if not lanes:
        return head + "Nothing failing in the window.\n"
    rows = "\n".join(
        f"| {x['name']} | {x['event']} | {x['conclusion']} | {x['attempt']} | [run]({x['url']}) |"
        for x in lanes
    )
    return (
        head
        + "| Workflow | Event | Conclusion | Attempt | Run |\n|---|---|---|---|---|\n"
        + rows
        + "\n"
    )


def main(argv: list[str]) -> int:
    """Entry point. Module-level as every script's is."""
    commands = {"survey", "rerun", "repair", "guard", "lock-advisories", "setting"}
    lane = "self_healer"
    if len(argv) >= 2 and argv[-2] == "--lane":
        lane, argv = argv[-1], argv[:-2]
    if not argv or argv[0] not in commands:
        print(__doc__, file=sys.stderr)
        return 2
    config = settings(REPO, lane)
    runner = SubprocessArgvRunner()
    if argv[0] == "setting":
        print(config[argv[1]])
        return 0
    if argv[0] == "lock-advisories":
        return AdvisoryLock(runner, REPO).run()
    healer = SelfHealer(GhRunForge(), runner, config, REPO)
    if argv[0] == "survey":
        now = datetime.now(UTC)
        lanes = healer.failing(now)
        out = Path(argv[1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "failures.json").write_text(json.dumps(lanes, indent=2) + "\n", encoding="utf-8")
        print(table(lanes, now - healer.window, healer.branch))
        return 0
    if argv[0] == "rerun":
        out = Path(argv[1])
        lanes = json.loads((out / "failures.json").read_text(encoding="utf-8"))
        done = healer.rerun(lanes)
        rerun_ids = {lane["id"] for lane in done}
        remaining = [lane for lane in lanes if lane["id"] not in rerun_ids]
        (out / "remaining.json").write_text(
            json.dumps(remaining, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Re-ran {len(done)}: " + (", ".join(x["name"] for x in done) or "none") + ".")
        print(f"Left for the keep-green prompt: {len(remaining)}.")
        return 0
    if argv[0] == "repair":
        results = healer.repair()
        print("### Scripted repairs\n\n| Repair | Exit |\n|---|---|")
        for r in results:
            print(f"| {r['name']} | {r['code']} |")
        for r in results:
            if r["code"]:
                print(f"\n<details><summary>{r['name']} — exit {r['code']}</summary>\n\n```text")
                print(r["tail"])
                print("```\n</details>")
        return 0
    # What the patch changes as git applies it, not as a pattern guesses (GitPatchPaths).
    refused = healer.refused(GitPatchPaths(REPO).touched(Path(argv[1])))
    for path in refused:
        if path.startswith("("):  # not a path: the patch itself was refused
            print(f"::error::refused {path}")
        else:
            print(f"::error::a scripted repair changed {path}, which [{lane}.guard] does not allow")
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
