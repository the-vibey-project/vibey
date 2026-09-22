<!-- split of #330: child 1 of 4; audit: issue-audit/updates/330.md -->
## Title
feat(config)!: [deploy].target names a cloud with an adapter, and [deploy].iac follows it

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:136-137`) makes self-hosted OpenStack the
cloud default and Azure, AWS and GCP declared-only. ADR-0042
(`docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:58-64`)
sets `deploy.target` to default to `openstack`. The configuration does not hold that shape:
`DeployConfig` (`src/vibey/domain/config.py:136-140`) defaults `iac` to `"bicep"`, an Azure format,
even for the OpenStack target; `_parse_deploy` (`config.py:453-459`) accepts any string for `target`
and `iac`, so `target = "aws"`, or `target = "openstack"` with `iac = "bicep"`, loads without
complaint, and a typo in the one declaration that selects a paid cloud passes unseen; and no reader
turns a project's stored config (a plain mapping) into a `DeployConfig`, which lane
`split-330-3-spec-follows-target` needs. Only two targets have an adapter today: `openstack` (the
sovereign default; its real CLI adapter is #331) and `azure`
(`src/vibey/infrastructure/azure/az_cli.py`). 8.b names **AWS** as the default paid cloud
(doctrines.md:188-194), but no AWS adapter exists, so `aws` is refused rather than accepted and
silently deployed nowhere; when an AWS adapter lands, it joins the map below. Nothing here makes
Azure the default paid cloud: it is only the one paid target with an adapter. This lane changes only
the pure `[deploy]` configuration; nothing reads `[deploy]` at runtime yet.

## Required behaviour
1. `DeployConfig()` equals `DeployConfig(enabled=False, target="openstack", iac="heat")`.
2. `[deploy].target` must be a key of `DEPLOY_IAC_BY_TARGET`, which means `"openstack"` or
   `"azure"`. Any other value raises
   `ConfigError("deploy.target", f"must be one of {', '.join(sorted(DEPLOY_IAC_BY_TARGET))} (the targets with an adapter), got {target!r}")`,
   whose text for `aws` is
   `deploy.target: must be one of azure, openstack (the targets with an adapter), got 'aws'`.
3. `[deploy].iac` defaults to the first format listed for the target, and must be one of the
   target's formats: `openstack -> ("heat",)` and `azure -> ("bicep", "arm")`. Any other value
   raises `ConfigError("deploy.iac", f"target {target!r} runs {', '.join(formats)}, got {iac!r}")`
   (for example `deploy.iac: target 'openstack' runs heat, got 'bicep'`). `target = "azure"` with no
   `iac` gives `"bicep"`, exactly as before.
4. `DeployConfig.from_mapping(config)` returns the `[deploy]` table from a mapping shaped like a
   parsed vibey.toml or a project's stored config, validated as in 2 and 3. An empty mapping `{}`
   gives the defaults. A `deploy` value that is not a table raises `ConfigError("deploy", ...)` (the
   existing `_optional` message, `config.py:358-364`: `'deploy' must be a dict, got str`). It does
   not require `[project].name`.
5. `DEPLOY_REGION_BY_TARGET = {"openstack": "RegionOne", "azure": "eastus"}` is declared beside
   `DEPLOY_IAC_BY_TARGET` (12.c: data, not a constant buried in a handler). Lane
   `split-330-3-spec-follows-target` reads it for a synthesized spec's default region; this lane
   only declares it and pins it in a test.
6. A new interface `DeployConfigInterface` (read-only `enabled: bool`, `target: str`, `iac: str`)
   sits in `src/vibey/domain/interfaces/config_interface.py` and is exported from
   `src/vibey/domain/interfaces/__init__.py`; `DeployConfig()` satisfies it.
7. Everything else in `config.py` is unchanged: `tests/domain/test_config.py` (whose example declares
   `target = "azure"`, `iac = "bicep"` at `:50-54`, asserted at `:107-108`) passes unedited, and
   domain purity holds (`tests/domain/test_domain_purity.py`).

## Where to change
Line numbers are from the storm integration branch at `4317cff6` (unchanged since `739536ea`); if one
has moved, find the quoted text. Use `edit_file` for every existing file (`config.py` is 724 lines).

- `src/vibey/domain/config.py`
  - Imports (lines 9-11): after `import tomllib` add `from collections.abc import Mapping`, so the
    block reads `import tomllib` / `from collections.abc import Mapping` /
    `from dataclasses import dataclass, field` / `from typing import Any`.
  - After line 35 (`DEFAULT_LOCAL_CONTEXT_WINDOW = 32_768`), add:
    ```python
    # Deploy targets with an adapter (ADR-0042, sub-doctrine 8.b) -> the IaC formats that
    # adapter runs; the first entry is the target's default `iac`. A declared-only cloud
    # with no adapter yet (8.b's paid default, AWS, among them) is refused, not accepted
    # and deployed nowhere; it joins this map with its adapter.
    DEPLOY_IAC_BY_TARGET: dict[str, tuple[str, ...]] = {
        "openstack": ("heat",),
        "azure": ("bicep", "arm"),
    }
    # The region a synthesized spec uses when the deploy interview names none.
    DEPLOY_REGION_BY_TARGET: dict[str, str] = {"openstack": "RegionOne", "azure": "eastus"}
    ```
  - `DeployConfig` (lines 136-140): change the default to `iac: str = "heat"`, and add inside the
    class, after the three fields:
    ```python
        @classmethod
        def from_mapping(cls, config: Mapping[str, object]) -> "DeployConfig":
            """The [deploy] table of a parsed vibey.toml or a project's stored config."""
            return _parse_deploy(dict(config))
    ```
  - `_parse_deploy` (lines 453-459) becomes, in order:
    ```python
    def _parse_deploy(data: dict[str, Any]) -> DeployConfig:
        table = _optional(data, "deploy", "deploy", dict, {})
        target = _optional(table, "target", "deploy.target", str, "openstack")
        formats = DEPLOY_IAC_BY_TARGET.get(target)
        if formats is None:
            raise ConfigError(
                "deploy.target",
                f"must be one of {', '.join(sorted(DEPLOY_IAC_BY_TARGET))} "
                f"(the targets with an adapter), got {target!r}",
            )
        iac = _optional(table, "iac", "deploy.iac", str, formats[0])
        if iac not in formats:
            raise ConfigError(
                "deploy.iac", f"target {target!r} runs {', '.join(formats)}, got {iac!r}"
            )
        return DeployConfig(
            enabled=_optional(table, "enabled", "deploy.enabled", bool, False),
            target=target,
            iac=iac,
        )
    ```
- `src/vibey/domain/interfaces/config_interface.py` (36 lines): change the docstring (line 2) to
  `"""Contracts for the project notification, telemetry and deploy configuration values."""` and
  append `DeployConfigInterface`, copying the layout of `TelemetryConfigInterface` (lines 30-36):
  ```python


  @runtime_checkable
  class DeployConfigInterface(Protocol):
      @property
      def enabled(self) -> bool: ...

      @property
      def target(self) -> str: ...

      @property
      def iac(self) -> str: ...
  ```
- `src/vibey/domain/interfaces/__init__.py`: in the `config_interface` import block (lines 3-7) add
  `    DeployConfigInterface,` as the first name (before `NotificationsConfigInterface,`); in
  `__all__` add `"DeployConfigInterface",` between `"DeliveryCorrelationInterface",` (line 103) and
  `"EngineFailurePolicyInterface",` (line 104).
- **Registry (only if present).** If `tests/fakes/registry.py` exists on the integration branch when
  the lane starts and its meta test demands an entry for the new interface, add
  `DeployConfigInterface` to `EXEMPT` as `ExemptReason.VALUE_CONTRACT` (a read-only view of a frozen
  config record). Otherwise change nothing there. (At `4317cff6` the file does not exist.)
- New test file `tests/domain/test_deploy_target_config.py` (below). No other file changes.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_deploy_target_config.py` passes (8 test
      functions, 9 cases).
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_config.py tests/domain/test_domain_purity.py tests/domain/test_deployment_domain.py`
      passes with those files unedited.
- [ ] `git diff --stat` names only the three source files above (plus `tests/fakes/registry.py`, if
      the registry step applied) and the new test file.
- [ ] `src/vibey/domain/*` keeps 100% branch coverage, and every line this lane adds to
      `config.py` is covered by `tests/domain` alone.

## Tests to write first (TDD)
New `tests/domain/test_deploy_target_config.py` (pure domain: no database, no network, no marker,
no patching). Line 1 is the provenance line copied from `tests/domain/test_config.py`. Imports:
`pytest`; `ConfigError`, `DeployConfig`, `DEPLOY_IAC_BY_TARGET`, `DEPLOY_REGION_BY_TARGET` and
`load_config_from_string` from `vibey.domain.config`; `DeployConfigInterface` from
`vibey.domain.interfaces`. A helper
`_deploy(toml: str) -> DeployConfig` returns `load_config_from_string('[project]\nname = "x"\n\n' + toml).deploy`
(`parse_config` requires `[project].name`).
- `test_default_deploy_config_is_sovereign`:
  `DeployConfig() == DeployConfig(enabled=False, target="openstack", iac="heat")`, and
  `load_config_from_string('[project]\nname = "x"\n').deploy == DeployConfig()`.
- `test_azure_target_defaults_its_iac_to_bicep`: `_deploy('[deploy]\ntarget = "azure"\n').iac == "bicep"`.
- `test_azure_accepts_arm`: `_deploy('[deploy]\ntarget = "azure"\niac = "arm"\n').iac == "arm"`.
- `test_unknown_target_is_refused`: `_deploy('[deploy]\ntarget = "aws"\n')` raises `ConfigError`
  whose `.path == "deploy.target"` and whose `.message` contains `"the targets with an adapter"`
  and `"got 'aws'"`.
- `test_iac_must_match_the_target`: parametrized over `("openstack", "bicep")` and
  `("azure", "heat")`; `_deploy(f'[deploy]\ntarget = "{target}"\niac = "{iac}"\n')` raises
  `ConfigError` whose `.path == "deploy.iac"`.
- `test_from_mapping_reads_a_stored_project_config`:
  `DeployConfig.from_mapping({"project": {"name": "p"}, "deploy": {"target": "azure"}})` has target
  `"azure"` and iac `"bicep"`; `DeployConfig.from_mapping({}) == DeployConfig()`;
  `DeployConfig.from_mapping({"deploy": "azure"})` raises `ConfigError` whose `.path == "deploy"`.
- `test_every_target_declares_a_default_region_and_iac`:
  `set(DEPLOY_REGION_BY_TARGET) == set(DEPLOY_IAC_BY_TARGET)`, every formats tuple is non-empty,
  `DEPLOY_REGION_BY_TARGET["openstack"] == "RegionOne"` and
  `DEPLOY_REGION_BY_TARGET["azure"] == "eastus"`.
- `test_deploy_config_satisfies_its_interface`: `isinstance(DeployConfig(), DeployConfigInterface)`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
# Focused tests (default tier: no service needed)
uv run pytest -q -p no:cacheprovider tests/domain
# Every added line of config.py is covered by the domain tests alone
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/domain
uv run coverage report -m --include='src/vibey/domain/config.py,src/vibey/domain/interfaces/config_interface.py'
# Per-layer 100% branch coverage over the whole suite (the CI gate)
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
uv run coverage report --include='src/vibey/application/*' --fail-under=100
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
uv run coverage report --include='src/vibey/cli/*' --fail-under=100
```
After the focused coverage report, none of the lines this lane added (the two maps, `from_mapping`,
the new `_parse_deploy` branches, `DeployConfigInterface`) may appear in its `Missing` column. One
coverage run at a time. Until lane `fakes-harness-decouple` lands, `tests/conftest.py:146-156`
connects to PostgreSQL at session start, so the whole-suite coverage run needs it; the focused
domain commands need nothing and can run with `--noconftest -n 0` added.

## Out of scope
- Lanes `split-330-2-scope-digest`, `split-330-3-spec-follows-target` and
  `split-330-4-az-scope-guard`: the scope digest, the spec builder and its persistence, the runtime
  config keys, bootstrap, and the az adapter's provider check. Do not touch `domain/deployment.py`,
  `application/`, `infrastructure/` or `bootstrap.py` here.
- An AWS or GCP adapter (a follow-up; 8.b's default paid cloud is AWS), and #331's OpenStack CLI
  adapter.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or the skill trees; the docs
  wave owns them (for example, `docs/reference/configuration.md:228` still says the default is
  `"azure"`, and CLAUDE.md still speaks of "an opt-in Azure deployment stage set"). Do not push, open
  PRs, or change git remotes. Commit locally as
  `feat(config)!: [deploy].target names a cloud with an adapter, and [deploy].iac follows it`, with
  the footer
  `BREAKING CHANGE: [deploy].iac defaults to "heat" for the default openstack target (azure still defaults to "bicep"); a [deploy].target with no adapter, or an iac its target does not run, is refused.`

## Standing constraints
- `domain/` stays pure: stdlib only (`collections.abc.Mapping` is stdlib), no I/O, no async, no
  clock (`tests/domain/test_domain_purity.py` walks the AST).
- Tests patch nothing: no `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`
  (sub-doctrine 9.b).
- Sovereign by default (8.b): the default target is `openstack` with `heat`; a paid cloud is only
  ever a declared value.
- Configurable (12.c): targets, their IaC formats and their default regions are data in two maps,
  not branches in code.
- OpenCode is repealed (8.b): no new test names it. No SQL anywhere (this lane is pure).
- Arch Linux and macOS (8.h): nothing here is platform-specific; the same check block is the proof
  on both.
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py` (protected path,
  `.vibey-gh.toml:78-85`), `tests/live/**`.
- Change existing files with `edit_file` (or a checked replacement); never rewrite an existing file
  with `write_file` (`STORM/EDITING-RULES.md`).

**Depends on:** none
- Nothing unmerged: every file named here is as it stands on the integration branch.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
