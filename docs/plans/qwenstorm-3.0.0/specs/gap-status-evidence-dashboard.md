## Title
feat(tui): the dashboard state carries an evidence claim, and the TUI shows its object, source and cutoff

## Why
10.f (`src/vibey_tools/gh/docs/doctrines.md:419` at integration HEAD `4317cff6`) and ADR-0040
(`docs/architecture/decisions/0040-evidence-bounded-status.md:25-30`) require every status claim
to name its object, its evidence source, and its scope and cutoff. The dashboard shows none of
them:
- `DashboardState` (`src/vibey/tui/dashboard.py:26-46`) has no field for them;
- `fetch_dashboard_state` (`:90-147`) reads the project, the queue, engine health and the ledger
  and records no read time;
- `StatusPanel` (`:150-166`) prints project, phase, cycle and repo;
- the replay (`build_replay_states`, `:319-381`; `VibeyReplayApp._update_ui`, `:448-469`) builds
  its states from ledger events and never says which event a frame stands on.
`vibey status` and `vibey watch` render this same state (`src/vibey/cli/main.py:594-658`,
`:709-790`), so this lane is the one place the claim is built. `gap-status-cli-evidence` then
prints it. Gap N6, `issue-audit/gaps.md:749-755`.

## Required behaviour
1. `src/vibey/tui/dashboard.py` (edit with edit_file only; the file is 480 lines):
   - Add imports: `from datetime import UTC, datetime`, and
     `from vibey.domain.status_claim import STATUS_POLICY, EvidenceSource, StatusClaim`
     (lane `gap-status-vocabulary`).
   - `DashboardState` gains a last field `evidence: tuple[StatusClaim, ...] = ()`. Every existing
     constructor call stays valid.
   - `DashboardState` gains a property `status_line -> str`: `self.evidence[0].render()` when
     `evidence` is not empty, else `"unknown (no evidence read yet)"`.
   - `fetch_dashboard_state` gains a keyword `observed_at: datetime | None = None`. The cutoff is
     `observed_at if observed_at is not None else datetime.now(UTC)`. Say in a comment that the
     CLI passes its composed clock and a direct caller gets the wall clock. It builds one claim:
     ```python
     status, detail = STATUS_POLICY.for_project(project.phase, queue_depth)
     ledger = f"ledger through seq {events[-1].seq}" if events else "ledger empty"
     claim = StatusClaim(
         subject=f"project {project.project_id}",
         status=status,
         source=EvidenceSource.STORE_SNAPSHOT,
         locator=f"project, job and engine_health rows; {ledger}",
         scope=f"cycle {project.cycle}",
         cutoff=cutoff,
         detail=detail,
     )
     ```
     and returns it as `evidence=(claim,)`.
   - `build_replay_states`: the initial state keeps `evidence=()`. Each state built after an event
     `ev` carries one claim:
     - `subject=f"project {project.project_id}"`;
     - `status` and `detail` from `STATUS_POLICY.for_project(current_phase, queue_counts)`;
     - `source=EvidenceSource.EVENT_STREAM`, `locator=f"ledger through seq {ev.seq}"`;
     - `scope=f"cycle {ev.cycle}"`, `cutoff=ev.produced_at`.
     When `ev.produced_at.utcoffset() is None`, that state's `evidence` is `()`: never invent a
     timezone.
   - `StatusPanel.watch_state` appends a fourth line, `f"\n[bold cyan]Status:[/] {state.status_line}"`,
     after the `Repo:` line.
   - `VibeyReplayApp._update_ui` appends the line `f"\nStatus:  {state.status_line}"` after its
     `Repo:` line.
2. `src/vibey/tui/interfaces/class_contracts.py`: `DashboardStateInterface` gains
   `@property def evidence(self) -> tuple[object, ...]: ...` and
   `@property def status_line(self) -> str: ...`.
3. No other file changes. The CLI keeps calling without `observed_at` until `gap-status-cli-evidence`.

## Where to change
- `src/vibey/tui/dashboard.py`, `src/vibey/tui/interfaces/class_contracts.py`.
- Tests: append to `tests/tui/test_dashboard.py`. Never rewrite it (EDITING-RULES rule 3).
- `tui/` is outside the coverage floor (ADR-0023). The tests are still required.

## Acceptance criteria
- [ ] A `DashboardState` built without `evidence` has `status_line == "unknown (no evidence read yet)"`.
- [ ] `fetch_dashboard_state(..., observed_at=datetime(2026, 9, 22, 15, 10, tzinfo=UTC))` over a
      project with one READY job gives a claim: `status is ACTIVE`,
      `detail == "ready 1, leased 0"`, `source is STORE_SNAPSHOT`, `scope == "cycle 1"`, `cutoff`
      equal to that datetime, and `locator` starting `"project, job and engine_health rows; ledger"`.
- [ ] Replay states after the first carry `EVENT_STREAM` claims whose `locator` names that event's seq.
- [ ] The status panel's render contains `Status:` and `source: store-snapshot`.
- [ ] Every existing test in `tests/tui/test_dashboard.py` passes unchanged. mypy strict passes.

## Tests to write first (TDD)
Append to `tests/tui/test_dashboard.py`:
- `test_a_state_without_evidence_says_unknown`
- `test_the_status_line_is_the_first_claims_rendering`
- `test_fetch_records_a_store_snapshot_claim_at_the_given_cutoff`. It seeds over the in-memory
  app, the way `test_fetch_dashboard_state_from_db` does after `fakes-tui-system`: `InMemoryApp()`
  from `tests.fakes.app`, `async with app.open_app() as resources:`, `resources.projects.create(...)`,
  and one `resources.jobs.enqueue(EnqueueRequest(...))` shaped like the `design.interview` job in
  `tests/cli/test_operational_commands.py:78-90`. It then passes `health=resources.engine_health_repo`.
- `test_replay_states_carry_event_stream_evidence` (reuse the events of
  `test_build_replay_states_and_replay_app`)
- `test_a_naive_event_time_gives_a_replay_state_no_evidence`
- `test_the_status_panel_shows_the_status_line` (`app.run_test()`, as `test_dashboard_app_renders_state` does)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/tui tests/domain/test_status_claim.py
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Printing the claim in `vibey status`, and passing the composed clock from `status` and
  `watch` (`gap-status-cli-evidence`).
- Rebuilding the queue or the circuits in replay (the replay honestly reports `unknown` for them).
- Docs, CHANGELOG.md.

Commit as `feat(tui): the dashboard state carries an evidence claim`. Do not push.

## Lane card
- **Depends on:** `gap-status-vocabulary`, `fakes-tui-system` (the in-memory fetch test).
- **Kind:** one source file plus its interface, one test file.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
