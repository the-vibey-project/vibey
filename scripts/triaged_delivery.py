# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Dispatch one ordered GitHub issue into Vibey's durable delivery queue.

This is intentionally a bounded bridge: it claims one issue by an idempotent GitHub
comment, creates the normal Vibey project and DESIGN job, and leaves the existing worker
to drive BUILD and REVIEW.  It never edits a branch or bypasses a human/deployment gate.
Run with ``--once`` from the repository checkout, or ``--interval SECONDS`` for a local
supervisor loop.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from dataclasses import dataclass
from os import environ
from pathlib import Path

PRIORITIES = ("critical", "high", "medium", "low")
TRIAGED = "vibey-gh:triaged"
BUMPED = "vibey-gh:priority-bumped"
MARKER = "<!-- vibey-delivery-dispatch issue:{number} -->"


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    bumped: bool
    priority: str
    created_at: str

    @property
    def rank(self) -> tuple[int, int, str, int]:
        return (
            0 if self.bumped else 1,
            PRIORITIES.index(self.priority),
            self.created_at,
            self.number,
        )


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "gh command failed")
    return result.stdout


def issues() -> list[Issue]:
    raw = json.loads(
        gh(
            "issue",
            "list",
            "--state",
            "open",
            "--label",
            TRIAGED,
            "--limit",
            "1000",
            "--json",
            "number,title,body,labels,createdAt",
        )
    )
    result: list[Issue] = []
    for item in raw:
        labels = {label["name"] for label in item.get("labels", [])}
        priority = next(
            (value for value in PRIORITIES if f"vibey-gh:priority-{value}" in labels),
            "low",
        )
        result.append(
            Issue(
                number=int(item["number"]),
                title=str(item.get("title") or ""),
                body=str(item.get("body") or ""),
                bumped=BUMPED in labels,
                priority=priority,
                created_at=str(item.get("createdAt") or ""),
            )
        )
    return sorted(result, key=lambda issue: issue.rank)


def already_dispatched(number: int) -> bool:
    return MARKER.format(number=number) in gh(
        "issue",
        "view",
        str(number),
        "--json",
        "comments",
        "--jq",
        '[.comments[].body] | join("\\n")',
    )


def _worktree(repo: Path, issue: Issue) -> Path:
    storm_home = Path(
        environ.get("VIBEY_STORM_HOME", str(Path.home() / "git" / "vibey-storm"))
    ).expanduser()
    target = storm_home / f"triaged-{issue.number}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not (target / ".git").exists():
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(target), "develop"],
            cwd=repo,
            check=True,
        )
    return target


def dispatch(issue: Issue, *, repo: Path) -> str:
    marker = MARKER.format(number=issue.number)
    worktree = _worktree(repo, issue)
    output = subprocess.run(
        [
            "uv",
            "run",
            "vibey",
            "new",
            f"github#{issue.number}: {issue.title}",
            "--repo",
            str(worktree),
            "--intake",
            f"GitHub issue #{issue.number}: {issue.title}\n\n{issue.body}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if output.returncode:
        raise RuntimeError(output.stderr.strip() or output.stdout.strip() or "vibey new failed")
    match = re.search(r"project ([0-9a-f-]{36})", output.stdout)
    if match is None:
        raise RuntimeError(f"vibey new returned no project id: {output.stdout.strip()}")
    project_id = match.group(1)
    gh(
        "issue",
        "comment",
        str(issue.number),
        "--body",
        f"{marker}\n\nVibey delivery dispatched: project `{project_id}`. DESIGN is queued; BUILD and REVIEW remain governed by the normal phase gates.",
    )
    return project_id


def drive_project(project_id: str, *, max_steps: int = 100, worker_timeout: float = 900.0) -> None:
    """Run the normal worker and answer only DESIGN gates with their declared defaults."""
    for _ in range(max_steps):
        try:
            worker = subprocess.run(
                [
                    "uv",
                    "run",
                    "vibey",
                    "worker",
                    "--once",
                    "--project",
                    project_id,
                    "--provider",
                    "gptossloop",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=worker_timeout,
            )
        except subprocess.TimeoutExpired:
            print(
                f"project {project_id} worker exceeded {worker_timeout:g}s; "
                "leaving the durable lease for queue.reap"
            )
            return
        gates = json.loads(
            subprocess.run(
                ["uv", "run", "vibey", "gates", project_id, "--json"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        ).get("gates", [])
        design_gates = [
            gate
            for gate in gates
            if str(gate.get("kind", "")) == "question"
            and str(gate.get("prompt", "")).split(":", 1)[0]
            in {
                "context_free",
                "job_story",
                "laddering",
                "example_mapping",
                "walking_skeleton",
                "nfr_planguage",
                "premortem",
            }
        ]
        if design_gates:
            for gate in design_gates:
                subprocess.run(
                    ["uv", "run", "vibey", "answer", str(gate["gate_id"]), "--defaults"],
                    check=True,
                )
            continue
        if gates or worker.returncode != 0:
            if gates:
                print(f"project {project_id} paused at human gate(s)")
            return
        accepted = subprocess.run(
            ["uv", "run", "vibey", "design", "accept", project_id],
            capture_output=True,
            text=True,
            check=False,
        )
        if accepted.returncode == 0:
            print(accepted.stdout.strip())
            continue
        return
    raise RuntimeError(f"project {project_id} exceeded dispatch step limit")


def run_once(repo: Path) -> int:
    for issue in issues():
        if already_dispatched(issue.number):
            continue
        project_id = dispatch(issue, repo=repo)
        print(f"dispatched #{issue.number} ({issue.priority}) -> project {project_id}")
        drive_project(project_id)
        return 0
    print("no eligible triaged issue without a dispatch marker")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--interval", type=float, default=300.0, help="Seconds between bounded dispatch attempts"
    )
    args = parser.parse_args()
    if args.once:
        return run_once(args.repo.resolve())
    while True:
        run_once(args.repo.resolve())
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
