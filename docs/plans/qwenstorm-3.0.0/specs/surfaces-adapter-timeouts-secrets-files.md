## Title
fix(surfaces): the OpenBao and Nextcloud adapters bound every call with a timeout

## Why
`issue-audit/gaps.md` K3: "Every sovereign adapter passes a bounded timeout, from config, to
every network call." Today `OpenBaoSecretsAdapter` and `NextcloudFilesAdapter` call
`self._opener(req)` with none (`src/vibey/infrastructure/secrets/openbao.py:47`, `:70`;
`src/vibey/infrastructure/files/nextcloud.py:47`, `:61`), so an unresponsive server blocks the
caller's thread forever. In a surface lane that is worse: draft ADR-0047 "Consequences"
(`specs/ADR-surface-lanes.md`) notes that an adapter call which outlives
`operation_timeout_seconds` "keeps running in its thread … The effect may land after the lane
replied `error`." A socket timeout no longer than the operation bound
(`[surfaces] adapter_timeout_seconds`, lane `surfaces-config`) closes most of that gap. This
lane adds the constructor keyword; `surfaces-direct-factory` passes the configured value.

## Required behaviour
For each of `OpenBaoSecretsAdapter` and `NextcloudFilesAdapter`:
1. `__init__` gains the keyword `timeout: float = 30.0` after `opener`. A value `<= 0` raises
   `ValueError("timeout must be positive")`. It is stored as `self._timeout`.
2. Every `self._opener(req)` becomes `self._opener(req, timeout=self._timeout)`.
3. Nothing else changes: URLs, headers, bodies, error mapping (`KeyError`,
   `FileNotFoundError`, `RuntimeError`) are as today.

## Where to change
- `src/vibey/infrastructure/secrets/openbao.py`, `src/vibey/infrastructure/files/nextcloud.py`.
- New `tests/infrastructure/surfaces/test_store_adapter_timeouts.py` (create
  `tests/infrastructure/surfaces/__init__.py` if missing).

## Acceptance criteria
- [ ] Each of the four requests (OpenBao get and set, Nextcloud upload and download) records `timeout == 30.0` by default and `2.5` when constructed with `timeout=2.5` (`InMemoryHttpServer.requests[i].timeout`).
- [ ] `timeout=0` raises `ValueError` for both adapters.
- [ ] Every existing OpenBao and Nextcloud test passes unchanged.
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surfaces/test_store_adapter_timeouts.py` (no service; `InMemoryHttpServer`):
- `test_openbao_get_and_set_carry_the_timeout` (parametrized default / configured)
- `test_nextcloud_upload_and_download_carry_the_timeout` (parametrized)
- `test_both_refuse_a_non_positive_timeout`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surfaces tests/infrastructure/test_sovereign_surfaces.py tests/contracts/test_surface_contracts.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The ports (unchanged: neither operation takes a key). The configured value
  (`surfaces-direct-factory`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and
  the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit
  locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-sovereign-http` (both adapters typed over `UrlOpener` and tested on `InMemoryHttpServer`).
- **Must keep passing unchanged:** `tests/infrastructure/test_sovereign_surfaces.py`, the contract suite, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file. Change existing files with `edit_file` or a checked replacement; add tests in a new file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Substitute only at a declared seam (`opener=`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
