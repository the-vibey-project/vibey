## Title
feat(surfaces): QueuedTracker, QueuedDocs and QueuedConfigStore implement their ports by putting each call on the surface's lane

## Why
Draft ADR-0047 §2 (`specs/ADR-surface-lanes.md`): "For the application layer nothing changes. The
transport is one more adapter per port." In `queue` transport, `AppResources.<surface>` holds
`Queued<Surface>` adapters "that publish to the lane", thin classes over `SurfaceLaneClient`
(§6, lanes S20–S22). "The caller never falls back to calling the backend directly" (§6). This
lane is the three record-keeping surfaces: the tracker (Plane), documentation (BookStack) and
configuration (Infisical). ADR-0047 lane S20.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/queued_records.py`, three classes, each
`__init__(self, client: SurfaceLaneClientInterface)` and nothing else:

1. `QueuedTracker(IssueTrackerPort)`:
   - `create_ticket(title, description, *, idempotency_key=None) -> str` =
     `await client.call(SurfaceName.TRACKER, "create_ticket", {"title": title, "description": description}, idempotency_key=idempotency_key)`;
   - `get_ticket_status(ticket_id) -> str` = `call(TRACKER, "get_ticket_status", {"ticket_id": ticket_id})`.
2. `QueuedDocs(DocsPort)`: `create_page(title, content, *, idempotency_key=None) -> str`
   (`{"title", "content"}`); `update_page(page_id, content) -> None` (`{"page_id", "content"}`).
3. `QueuedConfigStore(ConfigStorePort)`: `create_config(key, value) -> None`
   (`{"key", "value"}`); `get_config(key) -> str` (`{"key"}`), on `SurfaceName.CONFIGURATION`.
4. A result that should be a `str` and is not raises
   `RuntimeError(f"{surface}.{operation} answered {type(result).__name__}, not str")`; exceptions
   from the client (`KeyError`, `RuntimeError`, `SurfaceLaneUnavailable`,
   `SurfaceOperationParked`, `ValueError`) propagate unchanged, so callers handle them as they
   handle the direct adapters' errors.
5. **Interfaces** in `surface_lanes/interfaces/queued_records_interface.py`:
   `QueuedTrackerInterface(IssueTrackerPort, Protocol)`, `QueuedDocsInterface(DocsPort, Protocol)`,
   `QueuedConfigStoreInterface(ConfigStorePort, Protocol)`, `@runtime_checkable`, exported (the
   style of `src/vibey/infrastructure/tracker/interfaces/plane_interface.py`).
6. **Registry.** Each interface → its class over a fresh `RecordingSurfaceLaneClient`
   (`tests/fakes/surface_lanes.py`), in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/queued_records.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/queued_records_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_queued_records.py`.

## Acceptance criteria
- [ ] Each of the six methods calls the client exactly once with the surface, operation, argument mapping and key shown above (asserted on `RecordingSurfaceLaneClient.calls`), and returns the scripted result.
- [ ] A non-`str` result raises `RuntimeError`; a scripted `KeyError` and `SurfaceOperationParked` propagate unchanged.
- [ ] `isinstance(QueuedTracker(c), IssueTrackerPort)` (and the other two); `mypy --strict` accepts each class against its port, `idempotency_key` included.
- [ ] 100% `infrastructure/` branch coverage; the fakes parity test passes.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_queued_records.py` (no service; `RecordingSurfaceLaneClient`):
- `test_each_method_is_one_lane_call` (parametrized over the six methods)
- `test_the_idempotency_key_is_passed_through`
- `test_a_wrongly_typed_answer_is_an_error`
- `test_lane_errors_propagate_unchanged`
- `test_queued_records_satisfy_their_ports`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surface_lanes tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The other surfaces (`surfaces-queued-stores`, `surfaces-queued-sends`); choosing the transport
  (`surfaces-transport-selection`); end-to-end contracts (`surfaces-contracts-lane`).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the Title
  as the subject.

## Lane card
- **Depends on:** `surfaces-lane-client` (`SurfaceLaneClientInterface`, `RecordingSurfaceLaneClient`), `surfaces-adapter-tracker`, `surfaces-adapter-docs` (the ports' `idempotency_key`).
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
