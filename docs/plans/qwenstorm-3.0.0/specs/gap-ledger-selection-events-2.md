## Title
feat(ledger): every engine health or circuit transition is an EngineHealthChanged event, written in the upsert's transaction

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) asks for every "capacity signal"
and "decision". An engine's circuit opening on a capacity rejection, half-opening for a probe,
closing on a success, or losing its conformance is what every later selection rests on, but it
is only a row update: `PostgresEngineHealthRepository.upsert`
(`src/vibey/infrastructure/db/engine_health_repository.py:76-136`) overwrites the row and the
previous state is gone. `EngineHealthService` (`src/vibey/application/engine_health_service.py`)
makes every such change through that one upsert, whoever classified the signal, so ledgering
there covers every caller in both invocation modes (ADR-0046 §2: "the inner circuit break is
written by the caller that classified the signal"; the loop never writes health).

This lane reads the row as it was (locked), runs the upsert (`orm-engine-health`), and when a
tracked field changed appends `EngineHealthChanged` on the same connection, in the same
transaction, filed under the project's current cycle and phase.

**Credits ≠ rate limit, a fourth time.** `CreditsExhausted` has no `resets_at` at the type
(`src/vibey/domain/capacity.py`), a property test (`tests/domain/test_capacity.py:28-31`) and the
DB CHECK `credits_never_have_a_deadline` (`migrations/0007_engine_health_rotation.sql:21-23`). None
of the three changes. The event's snapshot of a side whose `capacity_state` is
`"CreditsExhausted"` has **no `resets_at` key at all**, and a property test pins it.

## Required behaviour
1. `src/vibey/domain/ledger.py`: after `DELIVERY_ESTIMATE_RECORDED` (`:70`) add
   `ENGINE_HEALTH_CHANGED = "EngineHealthChanged"` (next to `ENGINE_SELECTED` if
   `gap-ledger-selection-events-1` landed first).
2. In `engine_health_repository.py`, `class EngineHealthChangedDraftBuilder`:
   - `TRACKED: ClassVar[tuple[str, ...]] = ("installed", "version", "conformance_ok", "auth_ok", "circuit", "capacity_state", "resets_at", "probe_next_at", "probe_attempt", "consecutive_fail", "ewma_failure")`.
     `selected_count` and `cost_usd_cycle` are not tracked: selections are ledgered as
     `EngineSelected` and spend as the turn and budget events the meter sums. `auth_ok_at` and
     `conformance_at` are tracked only through `auth_ok` (`auth_ok_at is not None`) and
     `conformance_ok`, so a routine re-check that only moves a timestamp is not a transition.
     The class docstring says all of this.
   - `__init__(self, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION)`.
   - `_raw(self, record: EngineHealthRecord) -> dict[str, object]`: the eleven tracked values,
     JSON-native (`str(record.circuit)`, datetimes `.isoformat()` or `None`).
   - `state_of(self, record: EngineHealthRecord) -> dict[str, object]`: `_raw(record)`, minus the
     `resets_at` key when `record.capacity_state == "CreditsExhausted"`.
   - `changed(self, before: EngineHealthRecord | None, after: EngineHealthRecord) -> tuple[str, ...]`:
     every tracked name when `before is None`; otherwise the names whose `_raw` values differ; in
     `TRACKED` order.
   - `build(self, *, before: EngineHealthRecord | None, after: EngineHealthRecord, cycle: int, phase: StoredPhase, produced_at: datetime) -> LedgerEventDraft`:
     raises `ValueError(f"project is in phase {phase.value!r}, which this vibey does not know; it will not ledger engine health in it")`
     when `phase` is not a `Phase`, and `ValueError("no tracked engine health field changed")`
     when `changed(...)` is empty. Payload:
     `{"engine_id": str(after.engine_id), "changed": list(changed), "before": self.state_of(before) if before is not None else None, "after": self.state_of(after)}`.
     Draft: `engine_id=None`, `job_id=None`, `causation_id=None`, `provenance=Provenance.TRUSTED`,
     `kind=EventKind.ENGINE_HEALTH_CHANGED`, the correlation for `after.project_id`,
     `digest=digest_event(payload)`.
   - `ENGINE_HEALTH_DRAFTS: Final[EngineHealthChangedDraftBuilderInterface] = EngineHealthChangedDraftBuilder()`.
3. `EngineHealthChangedDraftBuilderInterface` in
   `interfaces/engine_health_repository_interface.py` (declaring `state_of`, `changed`, `build`),
   exported from `interfaces/__init__.py` (import block and `__all__`, sorted).
4. `PostgresEngineHealthRepository.__init__` gains keywords
   `events: EventAppenderInterface = DEFAULT_EVENT_APPENDER` and
   `drafts: EngineHealthChangedDraftBuilderInterface = ENGINE_HEALTH_DRAFTS`.
5. `upsert`: the two refusals stay first and unchanged. Inside the existing
   `self._orm.transaction()`, before the insert:
   `before_row = (await conn.execute(select(HEALTH).where(HEALTH.c["project_id"] == record.project_id, HEALTH.c["engine_id"] == engine_id.value).with_for_update())).mappings().first()`.
   After the insert returns `row` (and its `LookupError` check): `after = self._rows.to_record(row)`;
   `before = self._rows.to_record(before_row) if before_row is not None else None`; if
   `self._drafts.changed(before, after)`: read
   `select(PROJECTS.c["cycle"], PROJECTS.c["phase"], func.now().label("now")).where(PROJECTS.c["id"] == record.project_id)`
   (`PROJECTS = TABLES.table("project")`), then append
   `self._drafts.build(before=before, after=after, cycle=p["cycle"], phase=PHASE_PARSER.parse(str(p["phase"])), produced_at=p["now"])`.
   Return `after`. (The project row exists: `engine_health.project_id` references it,
   `migrations/0007_engine_health_rotation.sql:4`.)
6. **The fake.** `FakeEngineHealthRepository` (`tests/fakes/engines.py`, lane `fakes-engines`)
   gains keywords `ledger: LedgerRepositoryInterface | None = None`,
   `projects: ProjectStore | None = None`, `drafts: EngineHealthChangedDraftBuilderInterface = ENGINE_HEALTH_DRAFTS`,
   `clock: Clock | None = None`. `ledger` without `projects` raises
   `ValueError("a ledgered health fake needs the projects its events are filed under")`. With a
   ledger, `upsert` builds the same draft (`produced_at` from `clock.now()`, else
   `datetime.now(UTC)`) and appends it before storing. Without one, it behaves as today.

## Where to change
- `src/vibey/domain/ledger.py` (one insertion).
- `src/vibey/infrastructure/db/engine_health_repository.py`, `interfaces/engine_health_repository_interface.py`,
  `interfaces/__init__.py` (edit_file only).
- `tests/fakes/engines.py` (`FakeEngineHealthRepository`).
- New `tests/infrastructure/orm/test_engine_health_changed_drafts.py` (no database); append to
  `tests/infrastructure/db/test_engine_health_repository.py` and `tests/fakes/test_fake_engines.py`.

## Acceptance criteria
- [ ] `record_capacity_rejection(..., CreditsExhausted())` through the real repository ledgers one
      `EngineHealthChanged` with `changed` containing `circuit` and `capacity_state`, `after.circuit
      == "open"`, and no `resets_at` key in `after`.
- [ ] `record_success` after it ledgers `circuit` back to `closed`.
- [ ] `record_selection` (only `selected_count` moves) and a `record_preflight` that changes only
      `auth_ok_at` from one time to another ledger nothing.
- [ ] The first upsert of an engine ledgers `before: null` and every tracked name in `changed`.
- [ ] A refused `CreditsExhausted` + `resets_at` write still raises `IntegrityError` (SQLSTATE
      `23514`) and ledgers nothing.
- [ ] Property (hypothesis): for any two records, a side with `capacity_state == "CreditsExhausted"`
      has no `resets_at` key in the payload.
- [ ] 100% branch coverage of `src/vibey/domain/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_engine_health_changed_drafts.py`:
- `test_a_first_row_changes_every_tracked_field`
- `test_only_tracked_fields_count_as_a_change` (`selected_count`, `cost_usd_cycle`, a moved `auth_ok_at`)
- `test_a_credits_side_never_carries_resets_at` (a `@given` property over capacity states and optional deadlines)
- `test_an_unknown_phase_is_refused`
- `test_building_without_a_change_is_refused`
- `test_the_builder_is_its_declared_seam`
Append to `tests/infrastructure/db/test_engine_health_repository.py` (through `EngineHealthService`):
- `test_a_credits_rejection_ledgers_the_circuit_opening_without_a_deadline`
- `test_a_success_ledgers_the_circuit_closing`
- `test_a_selection_count_or_auth_refresh_ledgers_nothing`
- `test_a_refused_credits_deadline_ledgers_nothing`
Append to `tests/fakes/test_fake_engines.py` the first three with the same outcomes, plus
`test_a_ledgered_health_fake_needs_projects`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm tests/fakes tests/application tests/domain
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_engine_health_repository.py tests/infrastructure/db/test_forward_compatibility_columns.py tests/infrastructure/db/test_end_to_end_forced_rotation.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- `EngineHealthService` (unchanged: every transition goes through the upsert), the selection event
  (`gap-ledger-selection-events-1`), the migration and the CHECK.
- Publishing health events (not in `DEFAULT_ALLOWLIST`; withheld and counted).
- Docs, CHANGELOG.

Commit as `feat(ledger): engine health and circuit transitions are ledger events`. Do not push.

## Lane card
- **Depends on:** `orm-engine-health`, `orm-ledger`, `fakes-engines`, `fakes-ledger`, `fakes-projects`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
