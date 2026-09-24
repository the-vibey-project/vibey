## Title
fix(surfaces): apply the surface environment overlay when no vibey.toml exists

## Why
src/vibey/infrastructure/config_loader.py:12-16 says set environment variables beat the file
"so no vibey.toml has to exist at all" — but src/vibey/bootstrap.py:740-747 only calls
`load_config_from_path` when `./vibey.toml` is a file, so without one `resolved_config` is None
and every surface falls back to its in-memory adapter (bootstrap.py:751+). The Helm worker runs
in `/work` (deploy/helm/vibey/templates/worker.yaml:280) with no vibey.toml, so the
`VIBEY_TRACKER_*` / `VIBEY_DOCS_*` variables the chart injects (worker.yaml:118-150) are ignored.
Also, a malformed vibey.toml is swallowed with `except Exception: pass` (bootstrap.py:748-749):
startup must not block, but the operator must be told.

## Required behaviour
1. New `load_config_from_environment(environ=os.environ) -> VibeyConfig` in config_loader.py:
   starts from an empty document, applies the same local-engine switch overlay and
   `apply_env_overrides` as `load_config_from_path`, then `parse_config`. Refactor so both
   functions share one private overlay step (no duplicated switch loop).
2. bootstrap.py:740-747: if `./vibey.toml` is a file, use `load_config_from_path` (unchanged);
   otherwise use `load_config_from_environment()`. An explicitly passed `config=` still wins.
3. If loading `./vibey.toml` raises, log a warning naming the file and the error (logger of the
   bootstrap module), then fall back to `load_config_from_environment()` — not to None.
4. A process with neither file nor variables behaves exactly as today (all in-memory).

## Where to change
- src/vibey/infrastructure/config_loader.py:83-100 (`load_config_from_path`) — extract the overlay.
- src/vibey/bootstrap.py:740-749.

## Acceptance criteria
- [ ] With no vibey.toml and `VIBEY_TRACKER_URL/TOKEN/WORKSPACE_SLUG/PROJECT_ID` set, build_app wires `PlaneTrackerAdapter`.
- [ ] With no vibey.toml and no variables, every surface is in-memory.
- [ ] A malformed vibey.toml logs one warning and the env-only config is used.
- [ ] Checks pass; infrastructure/ and the root layers stay at 100% branch coverage.

## Tests to write first (TDD)
- tests/infrastructure/test_config_loader.py: `load_config_from_environment` with and without variables; invalid integer variable raises the same ValueError as the file path.
- tests/test_bootstrap.py (or tests/infrastructure/test_sovereign_surfaces.py): the three acceptance scenarios, using `monkeypatch.chdir(tmp_path)` and `monkeypatch.setenv`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_config_loader.py tests/infrastructure/test_sovereign_surfaces.py tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
Injecting more surface variables from the Helm chart (a later lane). Engine pool changes. Docs.
Do not push. Commit as `fix(surfaces): ...`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
