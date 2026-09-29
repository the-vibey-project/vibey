# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A simulated forge and `vibey` CLI for the triaged-delivery bridge's scenario tests.

`scripts/triaged_delivery.py` talks to three things: GitHub through `gh`, Vibey through its
CLI, and PostgreSQL's `triaged_ticket` table. The table is real (a scratch database from
tests/conftest.py). The other two are this world: one object that answers every argv the
bridge sends, and keeps the state a real forge and a real vibey would keep between calls.

A project moves design -> build -> review -> done across worker runs, and it stops where a
person has to act: the DESIGN interview's question gates, the design acceptance, and the
REVIEW verdict gate. `human_turn()` is the person, acting between passes. Every answer is
recorded with who gave it and through which door -- `bridge` (the bridge's own command
runner) or `human` -- which is what the "answered without the opt-in" metric counts.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import asyncpg

TRIAGED = "vibey-gh:triaged"
DESIGN_PROMPTS = ("context_free: What problem does this solve?", "job_story: When ... I want ...")


@dataclass
class FakeIssue:
    number: int
    title: str
    priority: str
    created_at: str
    state: str = "OPEN"
    labels: set[str] = field(default_factory=set)
    comments: list[str] = field(default_factory=list)


@dataclass
class FakeGate:
    gate_id: str
    project_id: str
    kind: str
    prompt: str
    answered_by: str | None = None
    answered_through: str | None = None


@dataclass
class FakeProject:
    project_id: str
    issue_number: int
    repo_path: str
    phase: str = "design"
    interview_started: bool = False
    spec_ready: bool = False
    gates: list[FakeGate] = field(default_factory=list)

    def open_gates(self) -> list[FakeGate]:
        return [gate for gate in self.gates if gate.answered_by is None]


@dataclass
class Answer:
    gate_id: str
    kind: str
    prompt: str
    by: str
    through: str


class ScratchTickets:
    """The owner's view of the scratch database: set up, age leases, read metrics."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def _run(self, sql: str, *args: object) -> list[asyncpg.Record]:
        async def go() -> list[asyncpg.Record]:
            conn = await asyncpg.connect(self.dsn)
            try:
                return list(await conn.fetch(sql, *args))
            finally:
                await conn.close()

        return asyncio.run(go())

    def reset(self) -> None:
        self._run("DELETE FROM triaged_ticket")

    def insert_project(self, project_id: str, name: str, repo_path: str) -> None:
        self._run(
            "INSERT INTO project (id, name, repo_path, phase, config) "
            "VALUES ($1::uuid, $2, $3, 'design', '{}'::jsonb)",
            project_id,
            name,
            repo_path,
        )

    def delete_projects(self, project_ids: list[str]) -> None:
        if project_ids:
            self._run("DELETE FROM triaged_ticket WHERE project_id = ANY($1::uuid[])", project_ids)
            self._run("DELETE FROM project WHERE id = ANY($1::uuid[])", project_ids)

    def let_leases_expire(self) -> None:
        """Time passes: every lease now held has run out."""
        self._run(
            "UPDATE triaged_ticket SET lease_expires_at = now() - interval '1 second' "
            "WHERE state = 'leased'"
        )

    def rows(self) -> dict[int, dict[str, Any]]:
        return {
            int(row["issue_number"]): dict(row)
            for row in self._run(
                "SELECT issue_number, state::text AS state, project_id::text AS project_id, "
                "lease_expires_at, lease_expires_at < now() AS lease_expired "
                "FROM triaged_ticket"
            )
        }


class FakeWorld:
    """GitHub and the vibey CLI, as the bridge sees them through argv."""

    def __init__(self, tickets: ScratchTickets, repository: str) -> None:
        self.tickets = tickets
        self.repository = repository
        self.issues: dict[int, FakeIssue] = {}
        self.projects: dict[str, FakeProject] = {}
        self.pull_requests: dict[str, dict[str, Any]] = {}
        self.answers: list[Answer] = []
        self.commands: list[list[str]] = []
        self.fail_next_new: set[int] = set()
        self.fail_new_always: set[int] = set()
        self.new_for_closed_issue: list[int] = []
        self.merge_train_calls: list[str] = []
        self.pushes: list[str] = []

    # -- setup ---------------------------------------------------------------------------

    def open_issue(self, number: int, priority: str, *, created_at: str) -> None:
        self.issues[number] = FakeIssue(
            number=number,
            title=f"issue {number}",
            priority=priority,
            created_at=created_at,
            labels={TRIAGED, f"vibey-gh:priority-{priority}"},
        )

    def close_issue(self, number: int) -> None:
        self.issues[number].state = "CLOSED"

    # -- the person ----------------------------------------------------------------------

    def human_turn(self) -> None:
        """A person answers every open gate and accepts every design waiting on them."""
        for project in self.projects.values():
            for gate in project.open_gates():
                self._answer(gate, by="adam", through="human")
            if project.phase == "design" and project.spec_ready and not project.open_gates():
                project.phase = "build"

    # -- metrics -------------------------------------------------------------------------

    def answered_through(self, through: str, *, kinds: tuple[str, ...] = ("question",)) -> int:
        return sum(1 for a in self.answers if a.through == through and a.kind in kinds)

    def active_projects(self) -> int:
        return sum(1 for p in self.projects.values() if p.phase not in {"done", "abandoned"})

    # -- the forge -----------------------------------------------------------------------

    def gh(self, *args: str) -> str:
        argv = list(args)
        self.commands.append(["gh", *argv])
        head = argv[:2]
        if head == ["issue", "list"]:
            fields = argv[argv.index("--json") + 1].split(",")
            listed = [
                self._issue_document(issue, fields)
                for issue in sorted(self.issues.values(), key=lambda i: i.number)
                if issue.state == "OPEN" and TRIAGED in issue.labels
            ]
            return json.dumps(listed)
        if head == ["issue", "view"]:
            issue = self.issues[int(argv[2])]
            if "comments" in argv:
                return "\n".join(issue.comments)
            fields = argv[argv.index("--json") + 1].split(",")
            return json.dumps(self._issue_document(issue, fields))
        if head == ["issue", "comment"]:
            self.issues[int(argv[2])].comments.append(argv[argv.index("--body") + 1])
            return ""
        if head == ["pr", "list"]:
            branch = argv[argv.index("--head") + 1]
            found = self.pull_requests.get(branch)
            return json.dumps([{"url": found["url"]}] if found else [])
        if head == ["pr", "create"]:
            branch = argv[argv.index("--head") + 1]
            url = f"https://github.com/{self.repository}/pull/{1000 + len(self.pull_requests)}"
            self.pull_requests[branch] = {
                "url": url,
                "state": "OPEN",
                "mergedAt": None,
                "isDraft": "--draft" in argv,
                "statusCheckRollup": [],
                "base": argv[argv.index("--base") + 1],
            }
            return url + "\n"
        if head == ["pr", "view"]:
            url = argv[2]
            pr = next(p for p in self.pull_requests.values() if p["url"] == url)
            return json.dumps({k: pr[k] for k in argv[argv.index("--json") + 1].split(",")})
        raise RuntimeError(f"fake gh: unsupported {argv}")

    def _issue_document(self, issue: FakeIssue, fields: list[str]) -> dict[str, Any]:
        document = {
            "number": issue.number,
            "title": issue.title,
            "body": f"body of {issue.number}",
            "labels": [{"name": name} for name in sorted(issue.labels)],
            "createdAt": issue.created_at,
            "updatedAt": issue.created_at,
            "url": f"https://github.com/{self.repository}/issues/{issue.number}",
            "state": issue.state,
        }
        return {name: document[name] for name in fields}

    # -- the vibey CLI, git, and the push gate -------------------------------------------

    def run(self, argv: list[str]) -> tuple[int, str, str]:
        self.commands.append(list(argv))
        if argv[:1] == ["gh"]:
            try:
                return 0, self.gh(*argv[1:]), ""
            except RuntimeError as exc:
                return 1, "", str(exc)
        if argv[:3] == ["uv", "run", "vibey-gh"]:
            self.merge_train_calls.append(argv[-1])
            return 0, "merge train: held", ""
        if argv[:2] == ["uv", "run"]:
            argv = argv[2:]
        if argv[:1] == ["vibey"]:
            return self._vibey(argv[1:])
        if argv[:1] == ["git"]:
            return self._git(argv[1:])
        if argv[:1] == ["python3"] and "push" in argv:
            self.pushes.append(argv[-1])
            return 0, "", ""
        if argv[:1] == ["pgrep"]:
            return 1, "", ""
        raise RuntimeError(f"fake world: unsupported {argv}")

    def _git(self, argv: list[str]) -> tuple[int, str, str]:
        if argv[:2] == ["worktree", "add"]:
            target = Path(argv[3])
            target.mkdir(parents=True, exist_ok=True)
            (target / ".git").write_text("gitdir: fake\n")
            return 0, "", ""
        if argv[0] == "-C" and argv[2:4] == ["worktree", "list"]:
            return (
                0,
                f"worktree {argv[1]}/integration\nHEAD 0123abcd\n"
                "branch refs/heads/vibey/1/integration\n",
                "",
            )
        raise RuntimeError(f"fake git: unsupported {argv}")

    def _vibey(self, argv: list[str]) -> tuple[int, str, str]:
        command = argv[0]
        if command == "new":
            number = int(argv[1].split("#", 1)[1].split(":", 1)[0])
            if self.issues[number].state != "OPEN":
                self.new_for_closed_issue.append(number)
            if number in self.fail_next_new or number in self.fail_new_always:
                self.fail_next_new.discard(number)
                return 1, "", "vibey new: database unavailable"
            project_id = str(uuid.uuid4())
            repo = argv[argv.index("--repo") + 1]
            self.tickets.insert_project(project_id, argv[1], f"{repo}#{project_id}")
            self.projects[project_id] = FakeProject(project_id, number, repo)
            return 0, f"project {project_id}\ndesign job {uuid.uuid4()}\n", ""
        if command == "worker":
            return self._worker(self.projects[argv[argv.index("--project") + 1]])
        if command == "status":
            project = self.projects[argv[1]]
            return 0, json.dumps(self._status(project)), ""
        if command == "gates":
            project = self.projects[argv[1]]
            gates = [
                {
                    "gate_id": g.gate_id,
                    "project_id": g.project_id,
                    "kind": g.kind,
                    "prompt": g.prompt,
                }
                for g in project.open_gates()
            ]
            return 0, json.dumps({"gates": gates}), ""
        if command == "answer":
            gate = next(g for p in self.projects.values() for g in p.gates if g.gate_id == argv[1])
            if gate.answered_by is not None:
                return 3, "", "already answered"
            by = argv[argv.index("--by") + 1] if "--by" in argv else "adam"
            self._answer(gate, by=by, through="bridge")
            return 0, f"answered {gate.gate_id} as {by}\n", ""
        if command == "design" and argv[1] == "accept":
            project = self.projects[argv[2]]
            if project.phase != "design" or not project.spec_ready or project.open_gates():
                return 1, "", "no synthesized spec to accept"
            project.phase = "build"
            return 0, f"accepted design for {project.project_id}; entered build\n", ""
        if command == "cost":
            return 0, "cost: $0.00\n", ""
        if command == "queue" and argv[1] == "reap":
            return 0, "queue reap: nothing expired\n", ""
        raise RuntimeError(f"fake vibey: unsupported {argv}")

    def _answer(self, gate: FakeGate, *, by: str, through: str) -> None:
        gate.answered_by = by
        gate.answered_through = through
        self.answers.append(Answer(gate.gate_id, gate.kind, gate.prompt, by, through))

    def _worker(self, project: FakeProject) -> tuple[int, str, str]:
        """One `vibey worker --once`: runs the project's next job, or finds none."""
        if project.phase == "design":
            if not project.interview_started:
                project.interview_started = True
                for prompt in DESIGN_PROMPTS:
                    project.gates.append(
                        FakeGate(str(uuid.uuid4()), project.project_id, "question", prompt)
                    )
                return 0, "design interview parked on questions\n", ""
            if project.open_gates() or project.spec_ready:
                return 0, "no claimable job\n", ""
            project.spec_ready = True
            return 0, "design spec synthesized\n", ""
        if project.phase == "build":
            project.phase = "review"
            project.gates.append(
                FakeGate(str(uuid.uuid4()), project.project_id, "verdict", "review: accept?")
            )
            return 0, "build done; review parked on a verdict\n", ""
        if project.phase == "review" and not project.open_gates():
            project.phase = "done"
            return 0, "review accepted; done\n", ""
        return 0, "no claimable job\n", ""

    def _status(self, project: FakeProject) -> dict[str, Any]:
        return {
            "project_id": project.project_id,
            "phase": project.phase,
            "cycle": 1,
            "max_cycles": 10,
            "repo_path": project.repo_path,
            "queue_depth": {"ready": 0, "awaiting_capacity": 0},
            "circuits": [],
        }


class DeliveryScenario:
    """The measured scenario: the same four issues, the same faults, the same person.

    - #1 (critical): its first `vibey new` fails, so the pass that claimed it dies mid-flight.
    - #2 (high), #3 (medium): ordinary work.
    - #4 (low): open and triaged when the first pass reconciles, closed straight after.

    Between passes time passes (every lease runs out) and the person takes a turn: answers
    every open gate and accepts every design waiting on them. `run_pass` is one bridge pass;
    an exception from it is recorded as a crashed pass, as a supervisor would log it.
    """

    def __init__(self, world: FakeWorld, tickets: ScratchTickets) -> None:
        self.world = world
        self.tickets = tickets

    def arrange(self) -> None:
        self.world.open_issue(1, "critical", created_at="2026-09-01T00:00:00Z")
        self.world.open_issue(2, "high", created_at="2026-09-02T00:00:00Z")
        self.world.open_issue(3, "medium", created_at="2026-09-03T00:00:00Z")
        self.world.open_issue(4, "low", created_at="2026-09-04T00:00:00Z")
        self.world.fail_next_new.add(1)

    def run(self, run_pass: Callable[[], object], passes: int) -> dict[str, Any]:
        self.arrange()
        crashes: list[str] = []
        max_active = 0
        for k in range(passes):
            if k:
                self.tickets.let_leases_expire()
            try:
                run_pass()
            except Exception as exc:  # noqa: BLE001 - a crashed pass is a measured outcome
                crashes.append(f"pass {k + 1}: {str(exc).splitlines()[0]}")
            max_active = max(max_active, self.world.active_projects())
            if k == 0:
                self.world.close_issue(4)
            self.world.human_turn()
        return self.metrics(passes, crashes, max_active)

    def metrics(self, passes: int, crashes: list[str], max_active: int) -> dict[str, Any]:
        rows = self.tickets.rows()
        dispatched = {p.issue_number for p in self.world.projects.values()}
        published = {
            n
            for n, issue in self.world.issues.items()
            if any("Delivery PR:" in comment for comment in issue.comments)
        }
        return {
            "passes": passes,
            "crashed_passes": crashes,
            "stale_leased_after_expiry": sum(
                1 for r in rows.values() if r["state"] == "leased" and r["lease_expired"]
            ),
            "issues_dispatched": sorted(dispatched),
            "issues_published": sorted(published),
            "tickets_completed": sorted(n for n, r in rows.items() if r["state"] == "completed"),
            "ticket_states": {n: rows[n]["state"] for n in sorted(rows)},
            "design_gates_answered_by_bridge": self.world.answered_through("bridge"),
            "bridge_answer_labels": sorted(
                {a.by for a in self.world.answers if a.through == "bridge"}
            ),
            # Distinct closed issues the bridge took: a lease or later on the ticket, or a
            # `vibey new` for it.
            "closed_issue_claimed": len(
                {
                    n
                    for n, r in rows.items()
                    if self.world.issues[n].state == "CLOSED"
                    and r["state"] in {"leased", "dispatched", "completed"}
                }
                | set(self.world.new_for_closed_issue)
            ),
            "max_concurrent_active_projects": max_active,
            "draft_prs": [p["isDraft"] for p in self.world.pull_requests.values()],
        }
