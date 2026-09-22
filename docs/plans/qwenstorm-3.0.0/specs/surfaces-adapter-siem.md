## Title
feat(siem): send_event takes an idempotency key that becomes the Wazuh document id, and the Wazuh adapter bounds every call

## Why
- **No timeout.** `WazuhSiemAdapter` calls `self._opener(req)` with no timeout
  (`src/vibey/infrastructure/siem/wazuh.py:51`; `issue-audit/gaps.md` K3).
- **The key.** Draft ADR-0047 §3 (`specs/ADR-surface-lanes.md`) classes `send_event` as
  **native**: "Wazuh indexer `PUT /<index>/_doc/<op_id>`: a repeat overwrites the same
  document." Today the adapter POSTs to `/<index>/_doc`, and the indexer mints a new id for
  every repeat (`wazuh.py:44-49`). With a key, a replayed event is one document. Without a key,
  behaviour is unchanged. The port already says delivery is best effort and never a job
  outcome (`src/vibey/application/interfaces/siem.py:9-14`).

ADR-0047 lane S06 (siem), and gaps K3 for this adapter.

## Required behaviour
1. **The port.** `SiemPort.send_event` (`siem.py:16-18`) becomes
   `async def send_event(self, index: str, event: dict[str, object], *, idempotency_key: str | None = None) -> None`.
   Docstring adds: "With a key, a repeat of the same key overwrites one document."
2. **`InMemorySiem`** (`src/vibey/infrastructure/siem/in_memory.py`): adds
   `self.documents: dict[tuple[str, str], dict[str, object]]`. With a key, the event is stored
   at `(index, key)` (overwriting), and appended to `self.events` only the first time that
   pair is seen. Without a key, it appends exactly as today.
3. **`WazuhSiemAdapter`**:
   - `__init__` gains `timeout: float = 30.0` after `opener` (`<= 0` raises
     `ValueError("timeout must be positive")`); the call becomes
     `self._opener(req, timeout=self._timeout)`.
   - With a key: `PUT {url}/{index}/_doc/{urllib.parse.quote(key, safe="")}`; without: today's
     `POST {url}/{index}/_doc`. Body and headers unchanged. Cite the indexer's document API in a
     one-line comment.

## Where to change
- `src/vibey/application/interfaces/siem.py`, `src/vibey/infrastructure/siem/in_memory.py`,
  `src/vibey/infrastructure/siem/wazuh.py`.
- New `tests/infrastructure/surfaces/test_wazuh_adapter.py` (create
  `tests/infrastructure/surfaces/__init__.py` if missing).
- Append to `tests/contracts/test_surface_contracts.py`, using its SIEM fixture.

## Acceptance criteria
- [ ] With key `k`, the request is `PUT …/vibey-audit/_doc/k`; without a key it is `POST …/vibey-audit/_doc`.
- [ ] The request records the default and a configured timeout.
- [ ] `InMemorySiem` keeps one document and one `events` entry for two sends with the same key, and the second send's content wins in `documents`.
- [ ] The contract test proves the overwrite on `memory` (and on `real` when `VIBEY_TEST_SIEM_*` is set).
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surfaces/test_wazuh_adapter.py` (no service; `InMemoryHttpServer`):
- `test_wazuh_key_puts_to_the_document_id`
- `test_wazuh_without_a_key_posts_as_today`
- `test_wazuh_passes_the_timeout`
- `test_wazuh_refuses_a_non_positive_timeout`
- `test_in_memory_siem_overwrites_one_document_per_key`
Append to `tests/contracts/test_surface_contracts.py`:
- `test_siem_same_key_is_one_document`

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
- The configured timeout (`surfaces-direct-factory`). CHANGELOG.md, docs/, ADRs, CLAUDE.md,
  AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or
  change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-http-transport` (Wazuh's `opener: UrlOpener`), `fakes-contracts-surfaces`.
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
