## Title
feat(messaging): send_message takes an idempotency key that becomes Matrix's transaction id, and the Matrix adapter bounds every call

## Why
- **No timeout.** `MatrixMessagingAdapter` calls `self._opener(req)` with no timeout
  (`src/vibey/infrastructure/messaging/matrix.py:44`; `issue-audit/gaps.md` K3).
- **The key.** Draft ADR-0047 §2–§3 (`specs/ADR-surface-lanes.md`) classes `send_message` as
  **native**: Matrix deduplicates `PUT …/send/m.room.message/{txnId}` per access token, so
  `txnId = vibey-<key>` makes a replayed send idempotent at the homeserver. Today the adapter
  mints `vibey-<uuid4>` per call on purpose (`matrix.py:29-33`): deriving it from the text would
  swallow a genuinely repeated message. A caller-supplied key is exactly the case where the
  repeat **is** the same message, so it is the right transaction id. Without a key, behaviour is
  unchanged.

This is also the first surface a production caller will use (`surfaces-consumer-notifications`).
ADR-0047 lane S06 (messaging), and gaps K3 for this adapter.

## Required behaviour
1. **The port.** `MessagingPort.send_message` (`src/vibey/application/interfaces/messaging.py:11-13`)
   becomes `async def send_message(self, channel_id: str, message: str, *, idempotency_key: str | None = None) -> None`.
   Docstring adds: "With a key, a repeat of the same key is delivered once (Matrix
   deduplicates the transaction id)."
2. **`InMemoryMessaging`** (`src/vibey/infrastructure/messaging/in_memory.py`): keeps
   `self._seen_keys: set[str]`; a send whose key was seen appends nothing; a new key or no key
   appends exactly as today.
3. **`MatrixMessagingAdapter`**:
   - `__init__` gains `timeout: float = 30.0` after `opener` (`<= 0` raises
     `ValueError("timeout must be positive")`); the call becomes
     `self._opener(req, timeout=self._timeout)`.
   - `txn_id = f"vibey-{idempotency_key}"` when a key is given, else today's
     `f"vibey-{uuid.uuid4()}"`. The URL path segment is
     `urllib.parse.quote(txn_id, safe="")`. Keep the existing comment and add one line saying a
     caller's key names one logical message, so reusing it is the intended deduplication.

## Where to change
- `src/vibey/application/interfaces/messaging.py`, `src/vibey/infrastructure/messaging/in_memory.py`,
  `src/vibey/infrastructure/messaging/matrix.py`.
- New `tests/infrastructure/surfaces/test_matrix_adapter.py` (create
  `tests/infrastructure/surfaces/__init__.py` if missing).
- Append to `tests/contracts/test_surface_contracts.py`, using its messaging fixture.

## Acceptance criteria
- [ ] With key `op.1:a`, the request URL ends in `/send/m.room.message/vibey-op.1%3Aa`; two sends with that key use the same URL.
- [ ] Without a key two sends use two different transaction ids.
- [ ] The request records the default and a configured timeout.
- [ ] `InMemoryMessaging` records one message for two sends with the same key; the contract test proves it on `memory` (and on `real` when `VIBEY_TEST_MESSAGING_*` is set).
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surfaces/test_matrix_adapter.py` (no service; `InMemoryHttpServer` with a `route_prefix` for the send path):
- `test_matrix_key_becomes_the_transaction_id`
- `test_matrix_without_a_key_mints_a_fresh_transaction_id_per_send`
- `test_matrix_passes_the_timeout`
- `test_matrix_refuses_a_non_positive_timeout`
- `test_in_memory_messaging_delivers_a_keyed_message_once`
Append to `tests/contracts/test_surface_contracts.py`:
- `test_messaging_same_key_is_delivered_once`

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
- The configured timeout (`surfaces-direct-factory`); notifications (`surfaces-consumer-notifications`).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `fakes-sovereign-http`, `fakes-contracts-surfaces`.
- **Shares a file with:** `tests/contracts/test_surface_contracts.py`.
- **Must keep passing unchanged:** `tests/infrastructure/test_sovereign_surfaces.py` (its test that two unkeyed sends use two ids stays true), the contract suite, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file. Change existing files with `edit_file` or a checked replacement; add tests by appending or in a new file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
