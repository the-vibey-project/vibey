## Title
feat(config): the surface-lane keys take environment overrides, including the nested [surfaces.cache] table

## Why
Draft ADR-0047 §13 (`specs/ADR-surface-lanes.md`) gives eight `[surfaces]` keys and one
`[surfaces.cache]` key an environment variable ("Environment beats file, and file beats
default"). In a cluster no `vibey.toml` exists (`deploy/helm/vibey/templates/worker.yaml:280`
runs in `/work`), so the chart can only set these through the environment
(`surfaces-chart-lane-deployments`). The overlay is `_SURFACE_ENV_VARS` in
`src/vibey/infrastructure/config_loader.py:17-59`, applied by `apply_env_overrides`
(`:62-80`), which today only writes top-level tables: `data.setdefault(table, {})` would store a
`"surfaces.cache"` key instead of a nested table. Sub-doctrine 12.c. Part of ADR-0047 lane S01.

## Required behaviour
1. `_SURFACE_ENV_VARS` gains these rows, in this order, at the end of the tuple:
   ```python
   ("surfaces", "transport", "VIBEY_SURFACES_TRANSPORT", str),
   ("surfaces", "adapter_timeout_seconds", "VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS", int),
   ("surfaces", "read_timeout_seconds", "VIBEY_SURFACES_READ_TIMEOUT_SECONDS", int),
   ("surfaces", "write_timeout_seconds", "VIBEY_SURFACES_WRITE_TIMEOUT_SECONDS", int),
   ("surfaces", "operation_timeout_seconds", "VIBEY_SURFACES_OPERATION_TIMEOUT_SECONDS", int),
   ("surfaces", "delivery_limit", "VIBEY_SURFACES_DELIVERY_LIMIT", int),
   ("surfaces", "read_prefetch", "VIBEY_SURFACES_READ_PREFETCH", int),
   ("surfaces", "inline_max_bytes", "VIBEY_SURFACES_INLINE_MAX_BYTES", int),
   ("surfaces.cache", "memo_max_entries", "VIBEY_SURFACES_CACHE_MEMO_MAX_ENTRIES", int),
   ```
2. `apply_env_overrides` treats a dotted table name as a path of nested tables:
   `"surfaces.cache"` walks `data["surfaces"]["cache"]`, creating each missing level. A level
   that exists but is not a table raises `ValueError(f"{prefix} must be a table")`, naming the
   dotted path up to that level, as the flat case does today. Flat names behave exactly as
   today. An empty or blank value still counts as unset; a non-integer for an `int` row still
   raises `ValueError(f"{variable} must be an integer")`.
3. Nothing else changes: `load_config_from_path` and (after lane `surfaces-env`)
   `load_config_from_environment` keep calling `apply_env_overrides`.

## Where to change
- `src/vibey/infrastructure/config_loader.py` (the tuple and `apply_env_overrides`).
- Append tests to `tests/infrastructure/test_config_loader.py`. Pass the environment as the
  `environ` argument; never `monkeypatch.setattr`.

## Acceptance criteria
- [ ] `apply_env_overrides({}, {"VIBEY_SURFACES_CACHE_MEMO_MAX_ENTRIES": "7"})` returns `{"surfaces": {"cache": {"memo_max_entries": 7}}}`.
- [ ] A file that sets `[surfaces] transport = "direct"` loses to `VIBEY_SURFACES_TRANSPORT=queue`; an empty variable leaves the file's value.
- [ ] `{"surfaces": "x"}` with a nested variable set raises `ValueError` naming `surfaces`.
- [ ] Every existing config-loader test passes unchanged; 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
Append to `tests/infrastructure/test_config_loader.py`:
- `test_surfaces_env_overrides_win_over_the_file`
- `test_a_dotted_table_nests`
- `test_a_non_table_level_is_refused_by_its_dotted_name`
- `test_surfaces_integer_variables_must_be_integers`
- `test_an_empty_surfaces_variable_is_unset`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/test_config_loader.py tests/domain/test_surfaces_config.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The keys without a variable in ADR §13 (they stay file-only). The chart
  (`surfaces-chart-lane-deployments`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md,
  GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes.
  Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-config` (the keys exist), `surfaces-env` (#323 refactors the same loader; land after it).
- **Shares a file with:** `src/vibey/infrastructure/config_loader.py` (R01 adds bus/queue rows; `surfaces-env` adds `load_config_from_environment`). Keep their rows; append yours last.
- **Must keep passing unchanged:** `tests/infrastructure/test_config_loader.py`, `tests/infrastructure/test_sovereign_surfaces.py`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Substitute only at a declared seam (`environ=`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
