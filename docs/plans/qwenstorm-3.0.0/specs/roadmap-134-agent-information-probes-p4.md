## Title
feat(config): `[secrets] required` declares the credentials a project needs, and `build_app` wires the information probe into the startup preflight

## Why
Issue #134, "Proposed child issues" 5 (rewrite `issue-audit/updates/134.md`). This is the last
of four lanes. `-p2` gave `ConductorPreflight` a `probes=` seam, and `-p3` wrote
`InformationProbe`. Production still passes no probe:
`ConductorPreflight(health=engine_health_service, feasibility=VibeyGhFeasibilityAdapter())` in
`build_app` (`src/vibey/bootstrap.py:724-727`). So `information.availability` stays `unknown`
at every worker start (`src/vibey/cli/main.py:1666-1694` prints the verdict).

The probe needs two things:
- the list of secrets a project's work needs. Nothing declares one:
  `SecretsConfig` has only `url` and `token` (`src/vibey/domain/config.py:226-231`, parsed at
  `:556-561`). Sub-doctrine 12.c (`src/vibey_tools/gh/docs/doctrines.md:455`) makes it a key,
  not a constant. The default is empty, which states "none declared" and invents no decision.
- the secrets port. `build_app` builds `secrets_port` only after the preflight
  (`bootstrap.py:782-788`), so the preflight's construction moves below it.

8.b (`doctrines.md:120-195`) keeps OpenBao the sovereign secrets default. Unconfigured, the
port is `InMemorySecrets` (`:787-788`), where every declared key reads missing: a measured
shortfall, stated loudly (10 decomposition clarification, `:371-383`).

## Required behaviour
1. `src/vibey/domain/config.py`:
   - `SecretsConfig` (`:226-231`) gains `required: tuple[str, ...] = ()`. Extend its docstring
     with: "`required`: the secret keys a project's work needs; the startup preflight's
     information probe checks each one is present (#134)."
   - `_parse_secrets` (`:556-561`):
     `required = _optional(table, "required", "secrets.required", list, [])`, then for each
     `key` in it, if `not isinstance(key, str) or not key.strip()`,
     `raise ConfigError("secrets.required", f"every entry must be a non-empty string, got {key!r}")`.
     Pass `required=tuple(required)` to `SecretsConfig(...)`.
2. `src/vibey/bootstrap.py`. Find each place by its text, because other lanes move lines in
   this file. The line numbers are today's.
   - Delete the four-line statement
     `conductor_preflight = ConductorPreflight(health=engine_health_service, feasibility=VibeyGhFeasibilityAdapter(),)`
     (`:724-727`). Nothing reads `conductor_preflight` before the `AppResources(...)` call (`:930`).
   - Directly after the `secrets_port` if/else (`:782-788`), add:
     ```python
     design_specs = FileDesignSpecRepository(projects)
     conductor_preflight = ConductorPreflight(
         health=engine_health_service,
         feasibility=VibeyGhFeasibilityAdapter(),
         probes=(
             InformationProbe(
                 projects=projects,
                 specs=design_specs,
                 secrets=secrets_port,
                 required_secrets=resolved_config.secrets.required if resolved_config else (),
             ),
         ),
     )
     ```
     Here `projects` is the value passed as `AppResources(projects=...)`.
   - In the `AppResources(...)` call, `design_specs=FileDesignSpecRepository(projects)` (`:922`)
     becomes `design_specs=design_specs`, so the handlers and the probe share one repository.
   - Import `InformationProbe` from `vibey.application.information_probe`, beside the
     `ConductorPreflight` import (`:68`).

## Where to change
- `src/vibey/domain/config.py` (use `edit_file`).
- `src/vibey/bootstrap.py` (use `edit_file`; three edits and one import).
- Append to `tests/domain/test_config.py`. Do not rewrite it.
- New `tests/test_bootstrap_information_probe.py`. Line 1 is the provenance header, copied
  byte-for-byte from `tests/test_bootstrap.py:1`. It runs on `InMemoryApp` from
  `tests/fakes/app.py` (lane `fakes-bootstrap-seam`), built with the config below. It uses the
  real `build_app` composition over the in-memory persistence. Patch nothing.

## Acceptance criteria
- [ ] `[secrets] required = ["forge-token"]` parses to `("forge-token",)`. No key gives `()`.
      `required = [""]` and `required = [3]` raise `ConfigError` naming `secrets.required`.
- [ ] Through `build_app`, a BUILD project with a stored spec reports
      `required_measured == 3` at preflight with `adapters={}`: software, agent and now
      information. Without the wiring it is 2.
- [ ] `grep -n "FileDesignSpecRepository(projects)" src/vibey/bootstrap.py` prints one line.
- [ ] `tests/test_bootstrap.py` and `tests/infrastructure/test_sovereign_surfaces.py` pass
      unchanged. 100% branch coverage of `src/vibey/domain/`.

## Tests to write first (TDD)
Append to `tests/domain/test_config.py` (`load_config_from_string` is already imported, `:4`):
- `test_secrets_required_parses_a_list_of_keys`:
  `'[project]\nname = "w"\n[secrets]\nrequired = ["forge-token", "openbao-root"]\n'` gives
  `config.secrets.required == ("forge-token", "openbao-root")`.
- `test_secrets_required_defaults_to_none_declared`: `config.secrets.required == ()`.
- `test_secrets_required_refuses_a_blank_or_non_string_entry`: parametrized over `'[""]'` and
  `'[3]'`, each raising `pytest.raises(ConfigError, match="secrets.required")`.

`tests/test_bootstrap_information_probe.py` (default tier). The config is
`load_config_from_string('[project]\nname = "w"\n[secrets]\nrequired = ["forge-token"]\n')`,
and `repo = tmp_path`. In one `async with app.open_app() as r:`:
1. `project = await r.projects.create("w", repo, max_cycles=3, config={})`.
2. Transition it INTAKE → DESIGN → BUILD.
3. `await r.design_specs.save(project.project_id, 1, DesignSpec(objective="greet", constraints=(), non_goals=(), criteria=(), nfrs=(), walking_skeleton="hello"))`.
4. `missing = await r.conductor_preflight.run(project_id=project.project_id, adapters={})`.
5. `await r.secrets.set_secret("forge-token", "t")`.
6. `present = await r.conductor_preflight.run(...)` again.

Tests:
- `test_the_information_probe_is_wired_into_the_startup_preflight`:
  `missing.feasibility.required_measured == 3` and `present.feasibility.required_measured == 3`.
- `test_the_handlers_and_the_probe_share_one_spec_repository`: after step 3,
  `(repo / ".vibey" / "runs" / "1" / "design" / "spec.json").is_file()`. That is the file
  repository's path (`src/vibey/infrastructure/db/design_spec_repository.py:25-29`).

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_config.py tests/test_bootstrap_information_probe.py tests/test_bootstrap.py tests/infrastructure/test_sovereign_surfaces.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/domain
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- A `VIBEY_SECRETS_REQUIRED` environment override (`src/vibey/infrastructure/config_loader.py:26-27`
  maps scalars only), and `docs/reference/configuration.md`.
- Other probes. The four vibey-gh probes are `roadmap-134-agency-probe`,
  `roadmap-134-software-probe`, `roadmap-134-network-probe` and `roadmap-134-hardware-series`.
- Printing every coordinate at worker start.
- CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
