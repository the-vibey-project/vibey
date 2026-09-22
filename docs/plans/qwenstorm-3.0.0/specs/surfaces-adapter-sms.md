## Title
feat(sms): send_sms accepts an idempotency key, and the Kannel adapter bounds every call with a timeout

## Why
- **No timeout.** `KannelSmsAdapter` calls `self._opener(req)` with no timeout
  (`src/vibey/infrastructure/sms/kannel.py:55`; `issue-audit/gaps.md` K3).
- **The key.** Draft ADR-0047 §2–§3 (`specs/ADR-surface-lanes.md`) adds an optional
  `idempotency_key` to `send_sms` and classes it **guarded**: Kannel's sendsms CGI has no key,
  so a repeated call is a second message ("What does not fit": "Two backends cannot
  deduplicate"); the lane guards it (§8). The port accepts the key and says so; the in-memory
  outbox does not deduplicate (draft amendment A2).

ADR-0047 lane S05 (sms), and gaps K3 for this adapter.

## Required behaviour
1. **The port.** `SmsPort.send_sms` (`src/vibey/application/interfaces/sms.py:11-13`) becomes
   `async def send_sms(self, phone_number: str, message: str, *, idempotency_key: str | None = None) -> None`.
   Docstring adds: "The key names one logical message. The backend cannot deduplicate it; the
   surface lane guards it (ADR-0047 §8)."
2. **`InMemorySms`** (`src/vibey/infrastructure/sms/in_memory.py`): appends on every call, as
   today, and records the key in a new `self.sent_keys: list[str | None]`.
3. **`KannelSmsAdapter`**: `__init__` gains `timeout: float = 30.0` after `opener` (`<= 0`
   raises `ValueError("timeout must be positive")`); the call becomes
   `self._opener(req, timeout=self._timeout)`; `send_sms` accepts the keyword and does not send
   it (the sendsms query string is unchanged).

## Where to change
- `src/vibey/application/interfaces/sms.py`, `src/vibey/infrastructure/sms/in_memory.py`,
  `src/vibey/infrastructure/sms/kannel.py`.
- New `tests/infrastructure/surfaces/test_kannel_adapter.py` (create
  `tests/infrastructure/surfaces/__init__.py` if missing).
- Append to `tests/contracts/test_surface_contracts.py`, using its SMS fixture.

## Acceptance criteria
- [ ] The sendsms request records the default and a configured timeout.
- [ ] A keyed send issues the same query string as an unkeyed one.
- [ ] `InMemorySms` records both of two keyed sends and both keys.
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surfaces/test_kannel_adapter.py` (no service; `InMemoryHttpServer` with a `route_prefix` for `/cgi-bin/sendsms`):
- `test_kannel_passes_the_timeout`
- `test_kannel_keyed_send_is_the_same_request`
- `test_kannel_refuses_a_non_positive_timeout`
- `test_in_memory_sms_records_every_send_and_its_key`
Append to `tests/contracts/test_surface_contracts.py`:
- `test_sms_send_accepts_an_idempotency_key`

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
- The guard and the configured timeout. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md,
  GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes.
  Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-sovereign-http`, `fakes-contracts-surfaces`.
- **Shares a file with:** `tests/contracts/test_surface_contracts.py`.
- **Must keep passing unchanged:** `tests/infrastructure/test_sovereign_surfaces.py`, the contract suite, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file. Change existing files with `edit_file` or a checked replacement; add tests by appending or in a new file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
