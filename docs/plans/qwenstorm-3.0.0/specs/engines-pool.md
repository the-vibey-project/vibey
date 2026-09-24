## Title
feat(engines)!: each project's engine pool follows ratified sub-doctrine 8.b

## Why
Sub-doctrine 8.b (src/vibey_tools/gh/docs/doctrines.md, "8.b", ratified by the merge of #319)
makes `qwenloop` and `opencode` always on and the paid engines (`claudeloop`, `codexloop`,
`cursorloop`, `agyloop`) declared-only. The config schema already says so
(src/vibey/domain/config.py:21 `DEFAULT_ENGINES = ("qwenloop", "opencode")`, :405-409 always
appends both), but nothing at runtime reads `[engines].enabled`:
- src/vibey/bootstrap.py:735-738 builds an adapter for every `DEFAULT_DESCRIPTORS` engine
  (src/vibey/infrastructure/engines/descriptors.py:404-410: the paid four plus `OPENCODE`);
- src/vibey/bootstrap.py:364-370 adds `qwenloop` only when its feature switch is on
  (src/vibey/infrastructure/engines/local_engines.py:99-107 `LocalEngineSettings.enabled`);
- `vibey doctor` checks `DEFAULT_DESCRIPTORS` plus switched-on local engines (src/vibey/cli/main.py:1275);
- cluster preflight defaults its pool to `DEFAULT_DESCRIPTORS` (src/vibey/infrastructure/cluster_preflight.py:140).
So a config that lists `qwenloop` without its switch loads (config.py:680-681 exempts it) but
never runs, and undeclared paid engines still run.

## Required behaviour
1. For a project, the candidate engine pool is: `qwenloop` and `opencode` (always), plus each
   paid engine the project declares, plus `claudeloop-local` only when its own switch
   (`VIBEY_FEATURE_CLAUDELOOP_LOCAL` / `[features] claudeloop_local`) is on.
2. "Declares" means: the project's stored config (`project.config`) has `engines` as a table
   whose `enabled` list names it (from `vibey.toml [engines]`), OR has `engines` as a list
   (the VibeyProject CR allow-list written by src/vibey/infrastructure/operator/handlers.py:61-62)
   that names it. Unknown names are ignored here (config validation already refuses them).
3. `qwenloop` cannot be switched off: `LocalEngineSettings.enabled(EngineId.QWENLOOP)` returns
   True whatever `VIBEY_FEATURE_QWENLOOP` or `[features] qwenloop` says. When either explicitly
   says false, log one warning: "qwenloop cannot be switched off (sub-doctrine 8.b); ignoring
   <source>". `claudeloop-local` keeps its switch unchanged.
4. `vibey worker --engines a,b` still narrows the pool this worker serves, after (1). An
   `--engines` list that names nothing in the pool keeps today's error (cli/main.py ~1655-1665).
5. `vibey doctor` checks exactly the pool from (1) for the `./vibey.toml` in the working
   directory (no file = the sovereign pair only).
6. Cluster preflight's default pool (cluster_preflight.py:140) is the sovereign pair; engines
   passed explicitly still add their auth requirements as today.
7. Selection is otherwise unchanged: LOCAL tier first (ADR-0038), recorded conformance still
   required before an engine is selected.

## Where to change
- New class `EnginePool` in `src/vibey/infrastructure/engines/engine_pool.py` with interface
  `src/vibey/infrastructure/engines/interfaces/engine_pool_interface.py` (copy the layout of
  `local_engines.py` + its interface). Method: `for_project(config: Mapping[str, object]) ->
  tuple[EngineId, ...]` implementing (1)-(2), taking a `LocalEngineSettings`.
- `local_engines.py:99-107`: make qwenloop always enabled (3); keep `enabled_engines` ordering.
- `bootstrap.py:364-370`: filter `adapters` to `EnginePool.for_project(project.config)` before
  adding local adapters (an injected adapter from the faked harness still wins — keep
  `setdefault` semantics for local ones and do not drop injected adapters in tests).
- `cli/main.py:1275` (doctor): use the pool.
- `cluster_preflight.py:140`: default pool = sovereign pair.

## Acceptance criteria
- [ ] A project with no `engines` config gets exactly {qwenloop, opencode} (+ claudeloop-local if switched on).
- [ ] A project whose `[engines].enabled` names `codexloop` gets {qwenloop, opencode, codexloop}.
- [ ] A project whose CR list is `["claudeloop"]` gets {qwenloop, opencode, claudeloop}.
- [ ] `VIBEY_FEATURE_QWENLOOP=0` still yields qwenloop in the pool and logs the warning once.
- [ ] `vibey doctor` with no vibey.toml checks qwenloop and opencode only.
- [ ] All checks below pass; 100% branch coverage per layer.

## Tests to write first (TDD)
- `tests/infrastructure/engines/test_engine_pool.py`: one test per acceptance item above
  (table form, list form, no config, claudeloop-local switch on/off, unknown name ignored).
- `tests/infrastructure/engines/test_local_engines.py`: qwenloop enabled with switch false/absent/true; warning logged once.
- `tests/test_bootstrap.py`: a project without engines config builds adapters only for the pool.
- Update `tests/cli/test_operational_commands.py` (doctor) and the cluster preflight tests to the new default pool.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/test_bootstrap.py tests/cli tests/infrastructure/test_config_loader.py tests/system/test_full_worker_faked.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
The DESIGN/DECOMPOSE `--provider` default (lane engines-provider). Docs, CHANGELOG, ADRs,
CLAUDE.md/AGENTS.md/GEMINI.md, skill trees (docs wave). Helm chart. Do not push or change remotes.
Commit locally as `feat(engines)!: ...` with a `BREAKING CHANGE:` footer stating that paid
engines now run only when declared and qwenloop can no longer be switched off.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
