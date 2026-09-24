## Title
test(contracts): every surface port's contract also runs through its lane — queued adapter, in-memory broker, lane host and in-memory backend

## Why
Draft amendment A5 (`specs/ADR-test-harness-fakes-amendment.md`): "one suite binds the fake and
the real adapter"; lane `fakes-contracts-surfaces` wrote one contract per surface port, run on the
production `InMemory*` class always and on the real adapter on opt-in. Draft ADR-0047 §2
(`specs/ADR-surface-lanes.md`) says the queued transport is "one more adapter per port" and "for
the application layer nothing changes". The proof is that the **same** contract passes through a
lane: `Queued<Surface>` → `SurfaceLaneClient` → the in-memory broker → `SurfaceLaneHost` →
`SurfaceOperationHandler` → the `InMemory*` backend. If a lane changed any port behaviour —
a lost not-found, a result of another type, an idempotency key dropped on the way — this suite
fails. It needs no service. ADR-0047 §15's "Every lane lands with `transport = direct`" plus this
suite is the evidence the flip lane (`surfaces-default-flip`) asks for.

## Required behaviour
1. **`tests/fakes/surface_lanes.py`** gains `class InProcessSurfaceLane` (a test helper that is
   itself a fake of a running lane):
   - `__init__(self, surface: SurfaceName, backend: object, *, settings: SurfacesConfig | None = None)`
     builds one shared `InMemoryAmqpClient`, `InMemoryAmqpLeases`, the in-memory stores, an
     `InMemoryLedger`, an `InMemoryProjectRepository`, and — through
     `SurfaceComposition(config=…, environ={"VIBEY_SURFACES_TRANSPORT": "queue", "VIBEY_BUS_AMQP_URL": "amqp://memory/"}, …, amqp_factory=lambda _: broker, leases_factory=lambda _: leases, direct=<a small DirectSurfaceFactoryInterface class in the helper whose build(surface) returns backend and whose bus() is an InMemoryBus>)`
     — a host for `surface` (its `resources` argument is a small object in the helper holding
     the ledger, projects and the two in-memory stores, satisfying
     `SurfaceLaneResourcesInterface`) and the queued port for callers;
   - `async __aenter__` starts the host as a task and waits until it has declared its topology;
     `async __aexit__` sets `stop`, awaits the task and `aclose()`s;
   - `port` property: the queued port; `async settled()` waits until the lane's queues are
     empty and nothing is in flight (poll `broker.inspect_queue` and the dispatcher's `active()`,
     at most 2 s) — for sends, whose effect lands after the call returns.
   Register it nowhere (it is a helper, not a fake of a port).
2. **`tests/contracts/test_surface_contracts.py`**: each surface fixture gains a third
   parameter, `"lane"`, unmarked (default tier): it builds `InProcessSurfaceLane(surface, <the InMemory* class>)`,
   enters it, and yields its `port`. Where a contract observes a send's effect on the backend,
   it `await`s `settled()` first when the backend is `lane` (a helper in the module keeps the
   tests themselves unchanged). The bus fixture gets no `lane` parameter (§11).
3. When a contract fails on `lane` only, do not weaken it: the lane is wrong. Fix it in the lane
   module that owns the behaviour and name the fix in the commit body.

## Where to change
- `tests/fakes/surface_lanes.py` (append the helper), `tests/contracts/test_surface_contracts.py`
  (fixture parameters and the settle helper), `tests/contracts/conftest.py` only if a shared
  helper belongs there.
- A production fix only if a contract proves the lane wrong (see 3).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts/test_surface_contracts.py` runs every surface contract on `memory` and on `lane`, with nothing running, and passes.
- [ ] The idempotency contracts the adapter lanes added (tracker, messaging, SIEM) pass on `lane`, proving the `op_id` reaches the backend as its key.
- [ ] Not-found contracts (`get_ticket_status`, `get_secret`, `get_config`, `download_file`, `get_blob`) raise the same exception type on `lane` as on `memory`.
- [ ] Byte round trips (files, blob) are equal on `lane`.
- [ ] The whole module finishes in under 20 s on the default tier.

## Tests to write first (TDD)
- Add the `lane` parameter to one fixture (the tracker), make it pass, then add it to the rest one at a time.
- `tests/fakes/test_surface_lanes_helper.py`: `test_in_process_lane_answers_and_settles`, `test_in_process_lane_stops_cleanly`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts tests/fakes tests/infrastructure/surface_lanes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- A lane over a real broker and real backends (the opt-in tier and `surfaces-cluster-smoke`).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the Title
  as the subject.

## Lane card
- **Depends on:** `surfaces-composition`, `fakes-contracts-surfaces`, `surfaces-app-records`.
- **Shares a file with:** `tests/contracts/test_surface_contracts.py` (the `surfaces-adapter-*` lanes appended to it), `tests/fakes/surface_lanes.py`.
- **Must keep passing unchanged:** every contract on `memory` and `real`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - A fake never imports `unittest.mock`; substitute only at declared seams.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
