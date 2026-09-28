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
import contextlib
import json
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from os import environ
from pathlib import Path

PRIORITIES = ("critical", "high", "medium", "low")
TRIAGED = "vibey-gh:triaged"
BUMPED = "vibey-gh:priority-bumped"
MARKER = "<!-- vibey-delivery-dispatch issue:{number} -->"
EVIDENCE_DIR = ".vibey/delivery-evidence"


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


def _json_command(args: list[str]) -> dict[str, object]:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "command failed: " + " ".join(args))
    value = json.loads(result.stdout or "{}")
    if not isinstance(value, dict):
        raise RuntimeError("command did not return a JSON object: " + " ".join(args))
    return value


def _evidence_path(repo: Path, project_id: str) -> Path:
    path = repo / EVIDENCE_DIR / f"{project_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _record_evidence(repo: Path, project_id: str, **values: object) -> None:
    """Append the latest observed delivery facts; never manufacture completion."""
    path = _evidence_path(repo, project_id)
    prior: dict[str, object] = {}
    if path.exists():
        prior = json.loads(path.read_text())
    prior.update(values)
    prior["updated_at"] = time.time()
    path.write_text(json.dumps(prior, indent=2, sort_keys=True) + "\n")


def _capacity_blocked(status: dict[str, object]) -> bool:
    queue = status.get("queue_depth")
    if isinstance(queue, dict) and int(queue.get("awaiting_capacity", 0)) > 0:
        return True
    circuits = status.get("circuits")
    if not isinstance(circuits, list):
        return False
    return any(
        isinstance(circuit, dict)
        and circuit.get("capacity_state") not in (None, "closed", "available")
        for circuit in circuits
    )


def _cost_output(project_id: str) -> str:
    result = subprocess.run(
        ["uv", "run", "vibey", "cost", project_id], capture_output=True, text=True, check=False
    )
    return (result.stdout + result.stderr).strip()


def _descendants(pid: int) -> list[int]:
    children = subprocess.run(
        ["pgrep", "-P", str(pid)], capture_output=True, text=True, check=False
    ).stdout.split()
    result = [int(child) for child in children]
    return result + [grandchild for child in result for grandchild in _descendants(child)]


def _terminate_worker(process: subprocess.Popen[str]) -> None:
    for pid in reversed(_descendants(process.pid)):
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGTERM)
    with contextlib.suppress(ProcessLookupError):
        os.kill(process.pid, signal.SIGTERM)
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=2)
    if process.poll() is None:
        for pid in reversed(_descendants(process.pid)):
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)
        with contextlib.suppress(ProcessLookupError):
            os.kill(process.pid, signal.SIGKILL)


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


def dispatched_project(number: int) -> str | None:
    comments = gh(
        "issue",
        "view",
        str(number),
        "--json",
        "comments",
        "--jq",
        '[.comments[].body] | join("\\n")',
    )
    match = re.search(
        rf"{re.escape(MARKER.format(number=number))}.*?project `([0-9a-f-]{{36}})`",
        comments,
        re.DOTALL,
    )
    return match.group(1) if match else None


def already_dispatched(number: int) -> bool:
    return dispatched_project(number) is not None


def active_project(issue_list: list[Issue]) -> str | None:
    for issue in issue_list:
        project_id = dispatched_project(issue.number)
        if project_id is None:
            continue
        status = json.loads(
            subprocess.run(
                ["uv", "run", "vibey", "status", project_id, "--json"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            or "{}"
        )
        if status.get("phase") not in {"done", "abandoned"}:
            return project_id
    return None


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


def drive_project(
    project_id: str,
    *,
    repo: Path,
    max_steps: int = 100,
    worker_timeout: float = 900.0,
) -> None:
    """Run the normal worker and answer only DESIGN gates with their declared defaults."""
    for _ in range(max_steps):
        try:
            worker_process = subprocess.Popen(
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            worker_process.communicate(timeout=worker_timeout)
            worker_returncode = worker_process.returncode
        except subprocess.TimeoutExpired:
            _terminate_worker(worker_process)
            worker_process.communicate()
            print(
                f"project {project_id} worker exceeded {worker_timeout:g}s; "
                "leaving the durable lease for queue.reap"
            )
            _record_evidence(repo, project_id, outcome="worker_timeout", capacity_safe=True)
            return
        status = _json_command(["uv", "run", "vibey", "status", project_id, "--json"])
        gates = _json_command(["uv", "run", "vibey", "gates", project_id, "--json"]).get(
            "gates", []
        )
        _record_evidence(
            repo,
            project_id,
            status=status,
            gates=gates,
            cost=_cost_output(project_id),
            review_observed=status.get("phase") in {"review", "done"},
        )
        if _capacity_blocked(status):
            _record_evidence(repo, project_id, outcome="awaiting_capacity", status=status)
            print(f"project {project_id} paused: capacity evidence requires retry")
            return
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
        if gates or worker_returncode != 0:
            if gates:
                print(f"project {project_id} paused at human gate(s)")
            return
        if status.get("phase") != "design":
            _record_evidence(repo, project_id, outcome="worker_progress", status=status)
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


def publish_project(project_id: str, issue: Issue, *, repo: Path) -> str | None:
    """Publish the canonical integration branch once the project is DONE."""
    status = json.loads(
        subprocess.run(
            ["uv", "run", "vibey", "status", project_id, "--json"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    if status.get("phase") != "done":
        _record_evidence(repo, project_id, outcome="not_done", status=status)
        return None
    branch = f"vibey/{int(status['cycle'])}/integration"
    worktree = Path(str(status["repo_path"]))
    listed = subprocess.run(
        ["git", "-C", str(worktree), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    match = re.search(
        rf"worktree (.+)\nHEAD [^\n]+\nbranch refs/heads/{re.escape(branch)}",
        listed,
    )
    if match is None:
        raise RuntimeError(f"project {project_id} has no integration worktree for {branch}")
    integration_path = Path(match.group(1))
    push_gate = environ.get(
        "VIBEY_PUSH_GATE",
        str(repo / "docs" / "plans" / "qwenstorm-3.0.0" / "tools" / "push_gate.py"),
    )
    push_gate_command = [
        "python3",
        push_gate,
        "run",
        "--",
        "git",
        "-C",
        str(integration_path),
        "push",
        "-u",
        "origin",
        branch,
    ]
    subprocess.run(push_gate_command, check=True)
    existing = json.loads(gh("pr", "list", "--head", branch, "--base", "develop", "--json", "url"))
    if existing:
        pull_request = str(existing[0]["url"])
    else:
        pull_request = gh(
            "pr",
            "create",
            "--base",
            "develop",
            "--head",
            branch,
            "--title",
            f"delivery: #{issue.number} {issue.title}",
            "--body",
            f"Automated delivery for GitHub issue #{issue.number}.\n\nVibey project: `{project_id}`.",
        ).strip()
    pr = json.loads(
        gh("pr", "view", pull_request, "--json", "url,state,mergedAt,statusCheckRollup")
    )
    _record_evidence(repo, project_id, outcome="pr_created", status=status, pull_request=pr)
    if pr.get("state") == "MERGED":
        return pull_request
    checks = pr.get("statusCheckRollup")
    if (
        not isinstance(checks, list)
        or not checks
        or any(
            isinstance(check, dict) and check.get("conclusion") not in ("SUCCESS", "SKIPPED")
            for check in checks
        )
    ):
        print(f"project {project_id} PR is not merge-ready; evidence recorded")
        return pull_request
    merge_train = subprocess.run(
        ["uv", "run", "vibey-gh", "merge-train", "--pr", pull_request.rsplit("/", 1)[-1]],
        capture_output=True,
        text=True,
        check=False,
    )
    _record_evidence(
        repo,
        project_id,
        merge_train_returncode=merge_train.returncode,
        merge_train_stdout=merge_train.stdout,
        merge_train_stderr=merge_train.stderr,
    )
    return pull_request


def run_once(repo: Path) -> int:
    issue_list = issues()
    current = active_project(issue_list)
    if current is not None:
        print(f"active dispatched project {current}; waiting before selecting another issue")
        return 0
    for issue in issue_list:
        if already_dispatched(issue.number):
            continue
        project_id = dispatch(issue, repo=repo)
        print(f"dispatched #{issue.number} ({issue.priority}) -> project {project_id}")
        drive_project(project_id, repo=repo)
        pull_request = publish_project(project_id, issue, repo=repo)
        if pull_request:
            gh("issue", "comment", str(issue.number), "--body", f"Delivery PR: {pull_request}")
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
