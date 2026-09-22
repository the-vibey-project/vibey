## Title
feat(engines)!: opencode is refused by name, pointing at its replacements

ADR-0046 lane L38a (slug `loops-retire-opencode-refusals`).

## Why
Sub-doctrine 8.b as ratified by #392: "**OpenCode is repealed** as an engine of either loop;
VS Code takes its place in both, and the runner that drove OpenCode is retired once the VS Code
adapter carries its work." ADR-0046 §9 (`specs/ADR-two-loops.md:289-293`): "**L38 runs only
after `vscode` passes the live conformance suite.** It then retires the engine id …; takes
`opencode` out of the defaults, the providers and the descriptors; makes config and the CLI
refuse it by name." The Migration table (`:415`): `opencode` as an engine or provider is
"refused by name with the replacement". Until now it has been declarable, transitionally, with a
warning (lane `engines-pool`, updates/321.md behaviour 1).

The ADR records this as a move to a less configurable state (12.c) that needs the operator's
explicit acceptance in the ratifying merge (`:346`); the gate below is that acceptance's
evidence half.

This is the first of three retirement lanes: refusals here; the infrastructure removal in
`loops-retire-opencode-infra`; the enum member in `loops-retire-opencode-id`. Each leaves the
tree green.

## Required behaviour
0. **Gate (ADR-0046 §9: live conformance first).** Before any edit run
   `grep -c "V-VS CONFORMANCE: PASS" /private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
   Unless the lines for **both** Arch Linux and macOS are present (`grep "V-VS CONFORMANCE: PASS" … | grep -ci arch` and `… | grep -ci macos` each ≥ 1), change nothing and report
   `gated: vscode has not passed live conformance on both OSes`.
1. **Config** (`src/vibey/domain/config.py`): `"opencode"` leaves `KNOWN_ENGINES`. An
   `"opencode"` in `[engines] enabled`, a key of `[engines] weights`, or any `[phases.*].engines`
   raises `ConfigError(<dotted key>, "opencode was retired (sub-doctrine 8.b, ADR-0046 §9); use vscode")`
   — checked before the generic "unknown engine" check, so the message names the replacement.
   Delete the comment at `:17-19` (at integration `d3b4a388`) about the `opencode` id.
2. **Pool** (`src/vibey/infrastructure/engines/engine_pool.py`, lane `engines-pool`): delete the
   transitional branch that admits a declared `opencode` and its repeal warning; a CR list that
   names `opencode` is ignored there (the operator handler warns, lane `loops-retire-opencode-infra`).
3. **CLI** (`src/vibey/cli/main.py`):
   - `_PROVIDERS` (`:365` at `d3b4a388`, already `("scripted", "claudeloop", "sovereignloop", "opencode")`
     after lane `loops-cli-provider-name`) becomes `("scripted", "claudeloop", "sovereignloop")`;
   - `--provider opencode` is refused before anything is built: add a class
     `RetiredProviderGuard` to `src/vibey/cli/main.py`'s neighbour module
     `src/vibey/cli/retired_providers.py` (+ `cli/interfaces/retired_providers_interface.py`)
     with `refusal(self, provider: str | None) -> str | None` returning
     `provider 'opencode' was retired (sub-doctrine 8.b, ADR-0046 §9); use --provider sovereignloop`
     for `"opencode"` and None otherwise; call it as the first statement of `work_once`
     (`@app.command("work")`, `:478-494` at `d3b4a388`) and of `worker` (before
     `allow_list` is computed, `:1470`), echoing the message and raising
     `typer.Exit(EXIT_USAGE)` (2). Nothing touches the database first;
   - delete the two `provider == "opencode"` branches (in `_work_once`, `:452-467`, and in
     `worker`, `:1607-1631`) and their local imports of `opencodeloop_design`,
     `opencodeloop_decompose` and `opencodeloop_process`;
   - `_PROVIDER_HELP` no longer names opencode.
4. **Cluster preflight** (`src/vibey/infrastructure/cluster_preflight.py`): `"opencode"` leaves
   `PROVIDER_ENGINES` (`:53-58`), so `EngineAuthCheck(provider="opencode")` raises its existing
   "provider must be one of …" ValueError; nothing else there changes in this lane.
5. **Tests that asserted OpenCode works now assert the refusal** — edit only these, and list them
   in the commit body:
   - `tests/cli/test_sovereign_provider_options.py::test_an_explicit_opencode_provider_on_work` →
     renamed `test_the_opencode_provider_is_refused_on_work`, asserting exit 2 and the message;
   - `tests/cli/test_operational_commands.py::test_worker_provider_opencode_constructs_live_providers` →
     renamed `test_the_opencode_provider_is_refused_on_worker`, same assertions;
   - the `_UNKNOWN_PROVIDER` message assertions (`test_sovereign_provider_options.py:473`, `:484`;
     `test_operational_commands.py:1429` at `d3b4a388`) drop `, or 'opencode'` and end
     `'claudeloop', or 'sovereignloop'`;
   - any `tests/domain/test_config.py` assertion that declares `opencode` expects the new
     ConfigError instead.
   Stop rule: any other failing test → stop and report.

## Where to change
- `src/vibey/domain/config.py`, `src/vibey/infrastructure/engines/engine_pool.py`,
  `src/vibey/cli/main.py`, `src/vibey/infrastructure/cluster_preflight.py` (edit_file each).
- New: `src/vibey/cli/retired_providers.py`, `src/vibey/cli/interfaces/retired_providers_interface.py`.
- The tests named in behaviour 5, and new `tests/cli/test_opencode_refused.py`.

## Acceptance criteria
- [ ] `parse_config({"project": {"name": "x"}, "engines": {"enabled": ["opencode"]}})` raises `ConfigError` with path `engines.enabled` and the message naming `vscode`.
- [ ] `vibey work <id> --provider opencode` and `vibey worker --once --provider opencode` exit 2 with the message naming `--provider sovereignloop`.
- [ ] `grep -n "opencodeloop_design\|opencodeloop_decompose\|opencodeloop_process" src/vibey/cli/main.py` prints nothing.
- [ ] The rest of the suite passes; 100% branch coverage on `domain/`, `infrastructure/`, `cli/`.

## Tests to write first (TDD)
`tests/cli/test_opencode_refused.py` (CliRunner; the refusals happen before `build_app`, so no
database is needed — assert that by passing no `VIBEY_DATABASE_URL`):
- `test_config_refuses_opencode_in_every_engine_list` (parametrized: enabled, weights, phases.build.engines)
- `test_work_refuses_the_opencode_provider`
- `test_worker_refuses_the_opencode_provider`
- `test_provider_help_and_error_no_longer_name_opencode`
- `test_cluster_preflight_refuses_the_opencode_provider`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli tests/domain/test_config.py tests/infrastructure/test_cluster_preflight.py tests/infrastructure/engines
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

The CLI tests in `tests/cli/test_operational_commands.py` and `test_sovereign_provider_options.py`
need PostgreSQL today (`VIBEY_TEST_DATABASE_URL`); run them where it is available and record it.

## Out of scope
- Deleting the opencode provider modules, descriptor, classifier and event map
  (`loops-retire-opencode-infra`), the enum member (`loops-retire-opencode-id`) and the tenant
  (`loops-remove-opencode-tenant`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally as `feat(engines)!: …` with a `BREAKING CHANGE:`
  footer: "opencode is retired (sub-doctrine 8.b, ADR-0046 §9): it is refused in config and as a
  --provider; use vscode (engine) or sovereignloop (provider)".

**Depends on:** `loops-vscode-vibey-wiring`, `loops-invocation-cli`, `loops-paidloop-keyword`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
