## Title
fix(surfaces): the Infisical, Garage and RabbitMQ-management adapters bound every call with a timeout

## Why
`issue-audit/gaps.md` K3: every sovereign adapter must pass a bounded timeout, from config, to
every network call. Today these three pass none:
- `InfisicalConfigStoreAdapter` (`src/vibey/infrastructure/config_store/infisical.py:54`, `:81`);
- `GarageBlobAdapter._send` (`src/vibey/infrastructure/blob/garage.py:112`), used by every put and get;
- `RabbitMqBusAdapter._request` (`src/vibey/infrastructure/bus/rabbitmq.py:50`), used by every
  bus call. The bus has no lane (draft ADR-0047 §11 and sub-doctrine 8.f's own text), but it is
  still a sovereign adapter, and K3 applies to it.

This lane adds the constructor keyword; `surfaces-direct-factory` passes
`[surfaces] adapter_timeout_seconds` (lane `surfaces-config`).

## Required behaviour
For each of `InfisicalConfigStoreAdapter`, `GarageBlobAdapter` and `RabbitMqBusAdapter`:
1. `__init__` gains `timeout: float = 30.0` after `opener`; a value `<= 0` raises
   `ValueError("timeout must be positive")`; stored as `self._timeout`.
2. Every `self._opener(req)` becomes `self._opener(req, timeout=self._timeout)` (Infisical's
   two calls, Garage's one in `_send`, the bus's one in `_request`).
3. Nothing else changes.

## Where to change
- `src/vibey/infrastructure/config_store/infisical.py`, `src/vibey/infrastructure/blob/garage.py`,
  `src/vibey/infrastructure/bus/rabbitmq.py`.
- New `tests/infrastructure/surfaces/test_platform_adapter_timeouts.py` (create
  `tests/infrastructure/surfaces/__init__.py` if missing).

## Acceptance criteria
- [ ] Infisical create and get, Garage's bucket PUT, object PUT and GET, and a bus declare, publish and consume each record `timeout == 30.0` by default and `2.5` when configured (`InMemoryHttpServer.requests[i].timeout`).
- [ ] `timeout=0` raises `ValueError` for all three.
- [ ] Every existing test of the three adapters passes unchanged.
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surfaces/test_platform_adapter_timeouts.py` (no service; `InMemoryHttpServer`, with `handler(...)` for Garage's signed requests if exact routes are awkward):
- `test_infisical_calls_carry_the_timeout` (parametrized default / configured)
- `test_garage_calls_carry_the_timeout` (parametrized)
- `test_bus_calls_carry_the_timeout` (parametrized)
- `test_all_three_refuse_a_non_positive_timeout`

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
- The Redis adapter (it already takes `timeout`; the lane's cache client is
  `surfaces-pipelined-redis`). The configured value (`surfaces-direct-factory`). CHANGELOG.md,
  docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do
  not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-sovereign-http` (Infisical over `UrlOpener`), `fakes-http-transport` (Garage and the bus over `UrlOpener`).
- **Must keep passing unchanged:** `tests/infrastructure/test_sovereign_surfaces.py`, the contract suite, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file. Change existing files with `edit_file` or a checked replacement; add tests in a new file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Substitute only at a declared seam (`opener=`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
