## Title
feat(application): one project-status query that `vibey status --json` and the HTTP API both read

## Why
Issue #143 (rewrite: `issue-audit/updates/143.md`, "Proposed child issues" 1: the API's project
routes "are built from the same application queries `vibey status --json` uses"). There is no such
application query yet. `vibey status` (`src/vibey/cli/main.py:709-790`) calls
`fetch_dashboard_state` from the **TUI** (`src/vibey/tui/dashboard.py:90-147`) and builds its JSON
inline (`main.py:737-766`). The layer map forbids the API from reaching either: `.importlinter:10-15`
orders `cli > tui > infrastructure > application > domain`, so `vibey.infrastructure.api` may not
import `vibey.tui` or `vibey.cli`. Runbook 12's risk "Five surfaces drifting"
(`docs/runbooks/expansion/12-integration-surfaces.md:107-111`) is exactly two JSON builders for one
status. This lane moves the projection into `application/`, where every surface can read it, and
switches `vibey status` onto it with byte-identical output. Sub-doctrine 9.b
(`src/vibey_tools/gh/docs/doctrines.md:349`): a class with its interface beside it.
Lands after `roadmap-143-api-read-projects-p2` (the listing) and `fakes-cli-operational-1` (the
in-memory CLI harness and the move of the `status` tests).

## Required behaviour
1. New `src/vibey/application/project_status.py` (provenance header on line 1, copied from
   `src/vibey/application/budget_source.py:1`):
   - `NO_PROJECTS: Final = "no projects found; create one with `vibey new` first"` (the text
     `main.py:724` prints today).
   - `@dataclass(frozen=True, slots=True) class ProjectStatus` with the fields of
     `DashboardState` (`dashboard.py:27-38`) except `ledger_tail`, in the same order and with the
     same names and types: `project_id: UUID`, `project_name: str`, `repo_path: Path`,
     `phase: StoredPhase`, `cycle: int`, `max_cycles: int`, `visual_decision: str | None`,
     `deployment_decision: str | None`, `queue_depth: Mapping[StoredJobState, int]`,
     `circuits: tuple[EngineHealthRecord, ...]`, `active_worktrees: tuple[str, ...]`; and the
     `phase_label` property copied from `dashboard.py:41-45`.
   - `class ProjectStatusQuery` with
     `__init__(self, *, projects: ProjectRepository, jobs: JobRepository, health: EngineHealthRepository, ledger: LedgerReader) -> None`
     (ports from `vibey.application.interfaces.projects`, `.queue`, `.engines`, `.ledger`):
     - `async def project(self, project_id: UUID | None) -> ProjectRecord`: `None` means
       `await projects.get_latest()`, and no project raises `UnknownProject(NO_PROJECTS)`; an id
       that `projects.get` does not find raises `UnknownProject(f"unknown project {project_id}")`.
     - `async def recent(self, *, limit: int) -> tuple[ProjectRecord, ...]`: returns
       `await projects.list_recent(limit=limit)` (lane `-p2`).
     - `async def status(self, project_id: UUID | None) -> ProjectStatus`: resolves the project
       with `self.project(project_id)`, then reads `jobs.queue_depth`, `health.list_for_project`
       and `ledger.all_for_project` for its id; derives `visual_decision` and
       `deployment_decision` with the loop copied verbatim from `dashboard.py:107-123`, and
       `active_worktrees` with the scan copied verbatim from `dashboard.py:125-129`.
     - `async def queue_depth(self, project_id: UUID) -> Mapping[StoredJobState, int]`: resolves
       the project with `self.project(project_id)` (so an unknown id raises), then returns
       `await jobs.queue_depth(project.project_id)`.
     - `def status_json(self, status: ProjectStatusInterface) -> dict[str, object]`: the dict
       `main.py:738-765` builds, copied verbatim with `state.` replaced by `status.` (same keys,
       same order, same expressions, including `"name": status.project_name`).
     - `def summary_json(self, record: ProjectRecord) -> dict[str, object]`: exactly
       `{"project_id": str(record.project_id), "name": record.name, "phase": record.phase.value, "cycle": record.cycle, "max_cycles": record.max_cycles, "repo_path": str(record.repo_path), "created_at": record.created_at.isoformat(), "updated_at": record.updated_at.isoformat()}`.
     - `def queue_json(self, project_id: UUID, queue_depth: Mapping[StoredJobState, int]) -> dict[str, object]`:
       exactly `{"project_id": str(project_id), "queue_depth": {state.value: count for state, count in queue_depth.items()}}`.
2. New `src/vibey/application/interfaces/project_status_interface.py` (provenance header;
   `from __future__ import annotations`): `@runtime_checkable class ProjectStatusInterface(Protocol)`
   with one read-only `@property` per `ProjectStatus` field plus `phase_label`, and
   `@runtime_checkable class ProjectStatusQueryInterface(Protocol)` with the seven methods above
   (`status` returns `ProjectStatusInterface`). It imports only `vibey.application.dto`, `vibey.domain`
   and the stdlib (`.importlinter:76-89`). Export both from `vibey.application.interfaces`
   (`src/vibey/application/interfaces/__init__.py`) beside the other re-exports.
3. `vibey status` (`main.py:709-790`, as `fakes-cli-operational-1` left it):
   - replace the two local imports (`main.py:715-716`) with
     `from vibey.application.project_status import ProjectStatusQuery`;
   - inside the `async with ... open_app() as resources:` block, replace the latest-project lookup
     and the `fetch_dashboard_state(...)` call (`main.py:720-735`) with
     `query = ProjectStatusQuery(projects=resources.projects, jobs=resources.jobs, health=resources.engine_health_repo, ledger=resources.ledger)`,
     then `try: state = await query.status(project_id)` /
     `except UnknownProject as exc: typer.echo(str(exc)); raise typer.Exit(1) from exc`
     (`UnknownProject` is already imported, `main.py:40-45`);
   - replace the `data = {...}` literal (`main.py:738-765`) with `data = query.status_json(state)`;
     the `json.dumps(data, indent=2)` line and the whole text branch (`main.py:767-788`) stay as they are.
   Output for an existing project, and for "no projects", is byte-for-byte today's. An unknown id,
   which today dies with a `ValueError` traceback from `dashboard.py:100`, now prints
   `unknown project <id>` and exits 1, like `vibey cost` (`main.py:852-854`).
4. Registry (`tests/fakes/registry.py`, lane `fakes-registry`): add
   `ProjectStatusQueryInterface: ExemptReason.CLASS_CONTRACT` and
   `ProjectStatusInterface: ExemptReason.VALUE_CONTRACT` to `EXEMPT` (the tests use the real query
   over the registered fakes).

## Where to change
- New `src/vibey/application/project_status.py`, `src/vibey/application/interfaces/project_status_interface.py`.
- `src/vibey/application/interfaces/__init__.py` (export), `src/vibey/cli/main.py` (`status` only),
  `tests/fakes/registry.py` (two `EXEMPT` entries).
- New `tests/application/test_project_status.py`, new `tests/cli/test_status_query.py`.
- Not `src/vibey/tui/dashboard.py`: the dashboard keeps its own fetch until a TUI lane moves it.

## Acceptance criteria
- [ ] The `status` tests `fakes-cli-operational-1` moved (`test_status_command_text_and_json`,
      `test_status_uses_latest_project_when_no_id_given`, `test_status_no_projects_exits_with_error`,
      `test_status_with_no_engines_shows_no_engines_message`) pass unchanged.
- [ ] `grep -n "fetch_dashboard_state\|PostgresEngineHealthRepository" src/vibey/cli/main.py` shows
      no line inside `status` (the `watch` command's use stays).
- [ ] `uv run lint-imports` passes; `tests/fakes/test_port_parity.py::test_every_application_port_is_accounted_for` passes.
- [ ] 100% branch coverage of `src/vibey/application/` and `src/vibey/cli/`.

## Tests to write first (TDD)
`tests/application/test_project_status.py` (fakes: `InMemoryProjectRepository` from
`tests/fakes/projects.py`, `FakeJobRepository` from `tests/fakes/queue.py`,
`FakeEngineHealthRepository` from `tests/fakes/engines.py`, `InMemoryLedger` from
`tests/fakes/ledger.py`, `FakeClock` from `tests/fakes/system.py`; ledger drafts are
`LedgerEventDraft` from `vibey.infrastructure.engines.tailer`, built like `main.py:159-173`):
- `test_status_reads_phase_queue_circuits_decisions_and_worktrees` — a project at `tmp_path`; one
  job enqueued with `EnqueueRequest(project_id=p.project_id, cycle=p.cycle, phase=Phase.INTAKE, kind="design.interview", idempotency_key=idempotency_key(p.project_id, p.cycle, "design.interview", "1"), requirement={})`
  (`idempotency_key` from `vibey.domain.job`); one `EngineHealthRecord` for `EngineId.CLAUDELOOP` upserted; ledger events
  `VISUAL_DESIGN_OPTED_IN` then `DEPLOYMENT_DECLINED`; directories `tmp_path/.vibey/worktrees/1/b`
  and `.../1/a` and a file `.../1/notes.txt`. Asserts `project_name`, `phase is Phase.INTAKE`,
  `queue_depth[JobState.READY] == 1`, one circuit, `visual_decision == "OPTED_IN"`,
  `deployment_decision == "DECLINED"`, `active_worktrees == ("a", "b")`.
- `test_status_without_an_id_reads_the_latest_project` — two projects, `clock.advance` between them.
- `test_an_absent_or_unknown_project_is_named` — empty repository: `status(None)` raises
  `UnknownProject` whose text equals `NO_PROJECTS`; `status(UUID(int=7))` and
  `queue_depth(UUID(int=7))` raise `UnknownProject("unknown project 00000000-0000-0000-0000-000000000007")`.
- `test_status_json_is_the_object_vibey_status_prints` — a hand-built `ProjectStatus`
  (`project_id=UUID(int=1)`, `phase=Phase.BUILD`, `cycle=2`, `max_cycles=5`, `repo_path=Path("/r")`,
  `visual_decision="DECLINED"`, `deployment_decision=None`,
  `queue_depth={JobState.READY: 1, JobState.LEASED: 0}`, one `CLAUDELOOP` circuit with
  `circuit=CircuitState.CLOSED`, `capacity_state=None`, `cost_usd_cycle=1.5`, `selected_count=3`,
  `active_worktrees=("c1-a",)`); `status_json(...)` equals the literal dict with keys
  `project_id, name, phase, cycle, max_cycles, repo_path, visual_decision, deployment_decision, queue_depth, circuits, active_worktrees`
  and `"phase": "build"`, `"queue_depth": {"ready": 1, "leased": 0}`, `"circuit": "closed"`.
- `test_summary_and_queue_json_have_their_fixed_shapes` — exact dict equality for both.
- `test_recent_lists_newest_first` — three projects, `recent(limit=2)` names the newest two.
- `test_the_query_and_its_status_satisfy_their_interfaces` — `isinstance` checks for both.
`tests/cli/test_status_query.py` (default tier: the `memory_app` fixture and `ops.invoke` from
`tests/cli/ops_support.py`, imported as `tests/cli/test_ops_status_ledger.py` imports them):
- `test_status_json_is_the_querys_projection` — seed one project through
  `async with memory_app.open_app() as r:`; `ops.invoke(memory_app, "status", "--json", str(pid))`
  exits 0 and `json.loads(result.stdout)` equals `query.status_json(await query.status(pid))`
  computed over a second `open_app()`.
- `test_status_of_an_unknown_project_exits_1_and_names_it` — `status <UUID(int=9)>` exits 1 and
  prints `unknown project 00000000-0000-0000-0000-000000000009`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_project_status.py tests/cli/test_status_query.py tests/cli/test_ops_status_ledger.py tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/application tests/cli
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The HTTP routes (`roadmap-143-api-read-projects-p4`); `vibey watch` and `tui/dashboard.py`.
- Per-job rows with lease ages: `JobRepository` lists jobs only by cycle and kind
  (`src/vibey/application/interfaces/queue.py:109-114`); a whole-project job listing is a new port
  method no lane owns yet.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the agent-surface trees. Do not
  push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
