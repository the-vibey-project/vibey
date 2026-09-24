## Title
feat(docs): create_page accepts an idempotency key, and the BookStack adapter bounds every call with a timeout

## Why
- **No timeout.** `BookStackDocsAdapter` calls `self._opener(req)` with no timeout
  (`src/vibey/infrastructure/docs/bookstack.py:53`, `:73`; `issue-audit/gaps.md` K3).
- **The key.** Draft ADR-0047 §2 (`specs/ADR-surface-lanes.md`) adds an optional
  `idempotency_key` to `create_page`. §3 classes it **guarded**: "BookStack has no key", so the
  backend cannot deduplicate; the lane guards it with an intent record (§8, lane
  `surfaces-guarded-execution`). The port therefore accepts the key and says plainly that this
  backend may create twice if called twice. The in-memory store must not deduplicate either:
  a fake kinder than its backend fails its contract (draft amendment A2).

ADR-0047 lane S05 (docs), and gaps K3 for this adapter.

## Required behaviour
1. **The port.** `DocsPort.create_page` (`src/vibey/application/interfaces/docs.py:11-13`)
   becomes `async def create_page(self, title: str, content: str, *, idempotency_key: str | None = None) -> str`.
   Docstring adds: "The key identifies one logical create. The backend may not deduplicate it;
   the surface lane guards it (ADR-0047 §8)."
2. **`InMemoryDocs`** (`src/vibey/infrastructure/docs/in_memory.py`): creates a page on every
   call, key or not, and records the key per page in a new
   `self.create_keys: dict[str, str | None]` (page id → key). `self.pages` keeps its shape.
3. **`BookStackDocsAdapter`**: `__init__` gains `timeout: float = 30.0` after `opener`
   (`<= 0` raises `ValueError("timeout must be positive")`); every `self._opener(req)` becomes
   `self._opener(req, timeout=self._timeout)`; `create_page` accepts the keyword and does not
   send it (BookStack's page API has no idempotency field). Nothing else changes.

## Where to change
- `src/vibey/application/interfaces/docs.py`, `src/vibey/infrastructure/docs/in_memory.py`,
  `src/vibey/infrastructure/docs/bookstack.py`.
- New `tests/infrastructure/surfaces/test_bookstack_adapter.py` (create
  `tests/infrastructure/surfaces/__init__.py` if missing).
- Append to `tests/contracts/test_surface_contracts.py`, using its docs fixture.

## Acceptance criteria
- [ ] Both BookStack requests record the default and a configured timeout.
- [ ] `create_page(..., idempotency_key="k")` sends the same body as without a key.
- [ ] `InMemoryDocs` creates two pages for two calls with the same key and records the key for each.
- [ ] The contract test asserts only what the port promises: a create returns an id and `update_page` changes its content. It does **not** assert deduplication.
- [ ] 100% `infrastructure/` branch coverage; mypy accepts both implementations.

## Tests to write first (TDD)
`tests/infrastructure/surfaces/test_bookstack_adapter.py` (no service; `InMemoryHttpServer`):
- `test_bookstack_passes_the_timeout_to_every_request`
- `test_bookstack_create_sends_no_key_field`
- `test_bookstack_refuses_a_non_positive_timeout`
- `test_in_memory_docs_does_not_deduplicate_and_records_keys`
Append to `tests/contracts/test_surface_contracts.py`:
- `test_docs_create_accepts_an_idempotency_key`

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
- The guard itself (`surfaces-guarded-execution`); the configured timeout
  (`surfaces-direct-factory`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and
  the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit
  locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-sovereign-http`, `fakes-contracts-surfaces`.
- **Shares a file with:** `tests/contracts/test_surface_contracts.py` (every `surfaces-adapter-*` lane appends).
- **Must keep passing unchanged:** `tests/infrastructure/test_sovereign_surfaces.py`, the contract suite, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file. Change existing files with `edit_file` or a checked replacement; add tests by appending or in a new file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
