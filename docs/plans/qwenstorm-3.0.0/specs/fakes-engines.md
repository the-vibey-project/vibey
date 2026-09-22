## Title
test(fakes): one family of engine fakes — health, rotation cursors, adapters, provider, preflight — replaces nine private copies

## Why
The engine seams are faked privately over and over:
- `FakeEngineHealthRepository` is written 4 times: in `tests/application/test_engine_health_service.py`,
  `test_engine_selector.py` and `test_rotation_handoff.py`, and in the shared
  `tests/fakes/engines.py`.
- `FakeRotationCursorRepository` is written 3 times.
- `FakeHealthRepo` appears in `tests/application/test_forward_compatibility_columns.py`.
- `tests/application/test_preflight.py:4,47-56` builds the preflight health service and
  engine adapters from `AsyncMock`/`Mock`.

Nothing faked `EngineProvider` or `EngineAdapter` in one shared place. The production
`ScriptedEngine` (`src/vibey/infrastructure/engines/scripted.py:57-58`) is already an honest
in-memory `EngineAdapter`, because it writes the real run-directory shape. It has never been
registered as the fake for that port.

`fakes-registry` lists `EngineProvider`, `EngineAdapter`,
`RunFeasibilityEvaluatorInterface` and `PreflightHealthServiceInterface` as `PENDING`
under this lane.

## Required behaviour
1. **`tests/fakes/engines.py`** keeps its two repositories and makes them complete:
   - `FakeEngineHealthRepository.get` and `upsert` key on `engine_id.value` when given an
     `EngineId`, and on the string otherwise, exactly as today. `list_for_project` returns
     the records sorted by `engine_id`.
   - `FakeRotationCursorRepository` keeps its current behaviour, and `update_many` returns
     the stored cursors.
2. **`class StaticEngineProvider`** (implements `EngineProvider`, `application/interfaces/engines.py:28-41`):
   - `__init__(self, adapters: Mapping[EngineId, EngineAdapter])`;
   - `pool()` returns `frozenset(adapters)`;
   - `async select_for(job)` returns the adapter for `EngineId(job.assigned_engine)` when it
     is set and pooled. Otherwise it returns the adapter of the first engine in
     `sorted(pool, key=lambda e: e.value)`. It appends `(job.id, engine_id)` to
     `self.selections`. An empty pool raises `LookupError("no engine in the pool")`.
3. **`class RecordingPreflightHealthService`** (implements `PreflightHealthServiceInterface`):
   - `record_preflight(...)` stores the result per `(project_id, engine_id)` and appends to
     `self.recorded`;
   - `list_for_project` returns `EngineHealthRecord`s built from what was recorded. Copy the
     field defaults that `EngineHealthService.get_or_create` uses.
4. **`class ScriptedFeasibilityEvaluator`** (implements `RunFeasibilityEvaluatorInterface`)
   returns the `FeasibilityAssessment` it was constructed with, and records each call's
   arguments in `self.calls`.
5. **Registry.**
   - `EngineAdapter → lambda: ScriptedEngine(descriptor=CLAUDELOOP, base_dir=Path(tempfile.mkdtemp(prefix="vibey-fake-engine-")))`,
     with the note "production in-memory adapter".
   - `EngineProvider → StaticEngineProvider({})`. For parity, build it with one
     `ScriptedEngine`.
   - Register the other two classes, and delete the four `PENDING` lines.
6. **Switch the tests to the shared family:**
   - delete the private classes in `test_engine_health_service.py`, `test_engine_selector.py`,
     `test_rotation_handoff.py` and `test_forward_compatibility_columns.py`, and import from
     `tests.fakes.engines`;
   - replace every `AsyncMock`, `Mock` and `SimpleNamespace(preflight=AsyncMock(...))` in
     `tests/application/test_preflight.py` with `ScriptedEngine` instances or
     `RecordingPreflightHealthService`;
   - lower those files' entries in `tests/meta/patching_baseline.json`.
   `tests/live/test_faked_rotation.py` keeps its private copies, because it is protected.

## Where to change
- `tests/fakes/engines.py`, `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`.
- `tests/application/test_engine_health_service.py`, `test_engine_selector.py`,
  `test_rotation_handoff.py`, `test_forward_compatibility_columns.py`, `test_preflight.py`.
- New `tests/fakes/test_fake_engines.py`.

## Acceptance criteria
- [ ] `grep -n "class Fake" tests/application/test_engine_health_service.py tests/application/test_engine_selector.py tests/application/test_rotation_handoff.py tests/application/test_forward_compatibility_columns.py` prints nothing.
- [ ] `grep -n "Mock" tests/application/test_preflight.py` prints nothing.
- [ ] The parity, ratchet and registry tests pass. No `PENDING` entry names `fakes-engines`.
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/application` passes.

## Tests to write first (TDD)
`tests/fakes/test_fake_engines.py`:
- `test_health_repository_round_trips_and_lists_sorted`
- `test_cursor_repository_initialize_is_idempotent`
- `test_static_provider_honours_the_assigned_engine`
- `test_static_provider_falls_back_to_the_first_pooled_engine`
- `test_static_provider_with_an_empty_pool_raises`
- `test_preflight_health_service_lists_what_it_recorded`
- `test_feasibility_evaluator_returns_its_assessment_and_records_the_call`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/application
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Production code. `ScriptedEngine` is registered as it is.
- `tests/live/**` (protected).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/live/**`, `tests/system/**` and the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
