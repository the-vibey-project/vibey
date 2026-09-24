## Title
feat(tracker): create_ticket takes an idempotency key Plane deduplicates, and the Plane adapter bounds every call with a timeout

## Why
Two defects and one ADR decision meet in one adapter:

- **No timeout.** `PlaneTrackerAdapter` calls `self._opener(req)` with no timeout
  (`src/vibey/infrastructure/tracker/plane.py:61`, `:77`), so a hung Plane hangs its caller's
  thread forever (`issue-audit/gaps.md` K3; draft ADR-0047 "Consequences": "Giving the adapters
  socket timeouts is a follow-up defect fix").
- **No idempotency.** Draft ADR-0047 §2 (`specs/ADR-surface-lanes.md`) adds an optional
  `idempotency_key` to the six operations that create or send, so a caller that replays (a job
  handler after its worker died) is answered once. §3 classes `create_ticket` as **native**:
  Plane's work-item create takes `external_source` and `external_id`, and answers a duplicate
  with 409 and the first item's id ("verification owed" — the ADR's last section).

The in-memory tracker must behave the same way, or it is kinder than the backend and fails its
contract (draft amendment A2, `specs/ADR-test-harness-fakes-amendment.md`). ADR-0047 lane S04
(tracker), and gaps K3 for this adapter.

## Required behaviour
1. **The port.** `IssueTrackerPort.create_ticket` (`src/vibey/application/interfaces/tracker.py:11-13`)
   becomes `async def create_ticket(self, title: str, description: str, *, idempotency_key: str | None = None) -> str`.
   Docstring adds: "With a key, a repeat of the same key returns the first ticket's id and
   creates nothing more."
2. **`InMemoryTracker`** (`src/vibey/infrastructure/tracker/in_memory.py`): keeps
   `self._by_key: dict[str, str]`. With a key it has seen, it returns that ticket's id and adds
   nothing; with a new key it creates the ticket and remembers the key; with no key it behaves
   exactly as today.
3. **`PlaneTrackerAdapter`** (`plane.py`):
   - `__init__` gains `timeout: float = 30.0` after `opener`; a value `<= 0` raises
     `ValueError("timeout must be positive")`. Every `self._opener(req)` becomes
     `self._opener(req, timeout=self._timeout)`.
   - `create_ticket(..., *, idempotency_key=None)`: with a key the JSON body is
     `{"name": title, "description": description, "external_source": "vibey", "external_id": idempotency_key}`;
     without a key it is today's body.
   - An `HTTPError` with code 409 **and** a key: read the error body (`exc.read()`), decode it as
     JSON; if it is an object with an `"id"`, return `str(obj["id"])`. Otherwise (or without a
     key) raise `RuntimeError(f"Plane API error {exc.code}: {exc.reason}")` from it, as today.
     Cite the Plane API in a one-line comment: duplicate `external_source` + `external_id`
     returns 409 with the existing work item's `id`.
4. `get_ticket_status` changes only by the timeout.

## Where to change
- `src/vibey/application/interfaces/tracker.py`, `src/vibey/infrastructure/tracker/in_memory.py`,
  `src/vibey/infrastructure/tracker/plane.py`. The interface files under
  `src/vibey/infrastructure/tracker/interfaces/` inherit the port and need no edit.
- New `tests/infrastructure/surfaces/test_plane_adapter.py` (create
  `tests/infrastructure/surfaces/__init__.py`, provenance line only, if it does not exist).
- Append to `tests/contracts/test_surface_contracts.py` (lane `fakes-contracts-surfaces`),
  using that module's existing tracker fixture.

## Acceptance criteria
- [ ] Every request the Plane adapter sends records `timeout == 30.0` by default and the configured value when one is passed (`InMemoryHttpServer.requests[i].timeout`, lane `fakes-http-transport`).
- [ ] With a key, the POST body carries `external_source="vibey"` and `external_id=<key>`; without one it carries neither.
- [ ] A 409 with body `{"id": "abc"}` and a key returns `"abc"`; a 409 without an id, or without a key, raises `RuntimeError`.
- [ ] `InMemoryTracker` returns one id for two creates with the same key and two ids for two different keys; the contract test proves the same on `memory` (and on `real` when `VIBEY_TEST_TRACKER_*` is set).
- [ ] `mypy --strict` accepts `PlaneTrackerAdapter` and `InMemoryTracker` against the port; 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surfaces/test_plane_adapter.py` (no service; `InMemoryHttpServer` from `tests/fakes/http.py`):
- `test_plane_passes_the_timeout_to_every_request`
- `test_plane_create_with_a_key_sends_external_source_and_id`
- `test_plane_create_without_a_key_sends_neither`
- `test_plane_duplicate_key_returns_the_first_ticket`
- `test_plane_409_without_an_id_is_a_runtime_error`
- `test_plane_refuses_a_non_positive_timeout`
- `test_in_memory_tracker_same_key_returns_the_same_ticket`
Append to `tests/contracts/test_surface_contracts.py`:
- `test_tracker_create_with_the_same_key_returns_one_ticket`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surfaces tests/contracts/test_surface_contracts.py tests/infrastructure/test_sovereign_surfaces.py tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Passing the configured timeout from `[surfaces] adapter_timeout_seconds` (`surfaces-direct-factory`).
- Any other adapter. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill
  trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `fakes-sovereign-http` (the adapter's `opener: UrlOpener` and its tests on `InMemoryHttpServer`), `fakes-contracts-surfaces` (the contract module).
- **Shares a file with:** `tests/contracts/test_surface_contracts.py` (the other `surfaces-adapter-*` lanes append too).
- **Must keep passing unchanged:** `tests/infrastructure/test_sovereign_surfaces.py`, the contract suite, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file. Change existing files with `edit_file` or a checked replacement; add tests by appending or in a new file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Substitute only at a declared seam (`opener=`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`. The patching ratchet must not rise.
  - The default run needs no service; a real-backend contract case is `integration` and skips without its `VIBEY_TEST_*` variables.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
