## Title
feat(deploy)!: the deployment scope's provider follows [deploy].target

## Why
Sub-doctrine 8.b (src/vibey_tools/gh/docs/doctrines.md:109-121) makes self-hosted OpenStack
the cloud default and Azure declared-only. ADR-0042
(docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:58-64)
makes the target scope carry its provider "so the digest differs per provider". These gaps
were verified in the code:
- `[deploy]` is parsed (src/vibey/domain/config.py:453-459) but nothing reads it at runtime.
  `RUNTIME_CONFIG_KEYS` (src/vibey/infrastructure/config_loader.py:10) leaves it out, so
  `vibey new` (src/vibey/cli/main.py:217-218) never stores it with the project.
- `build_deployment_spec` (src/vibey/application/deploy_design_handler.py:54-60) never sets
  `provider`. Every scope therefore gets the default `"openstack"`
  (src/vibey/domain/deployment.py:21), including an Azure adopter's.
- `FileDeploymentStateRepository.load_spec` (src/vibey/infrastructure/deploy/state_repository.py:63-70)
  drops `provider` when it reloads a spec. A saved Azure spec would come back as OpenStack,
  and its consent would stop matching.
- Since c67495e4 (#319), `digest()` (deployment.py:24-28) puts the provider first. So every
  consent recorded by 2.0.0 and earlier (#40, #57) stopped matching. Those used the form
  `tenant:subscription:resource_group:environment`.
- `[deploy].iac` defaults to `"bicep"` (config.py:140) even for an OpenStack target, and
  `target` and `iac` accept any string.
- `AzCliClientAdapter` (src/vibey/infrastructure/azure/az_cli.py:64-165) accepts a scope for
  any provider.

**Decision: old Azure consents stay verifiable, because an Azure scope keeps the old digest
form.** Every consent from before #319 is an Azure consent. Runbook 03 also already requires
the Azure alias to be "proven byte-compatible"
(docs/runbooks/expansion/03-multicloud-aws-gcp.md:59). So an Azure scope hashes the old
4-field string, and every other provider hashes the 5-field string that starts with the
provider. Consent still cannot cross clouds, for three reasons:
- `validate()` now forbids `:` inside digest fields. The two forms then differ structurally:
  3 separators against 4.
- An old-form digest can only ever match an Azure scope.
- The Azure adapter refuses any scope that is not Azure (requirement 12).

The rejected alternative was one provider-first form for everything, with a re-consent
documented for 3.0.0. That would also be safe, because a mismatch fails closed
(src/vibey/application/deploy_execute_handler.py:70-72). But it would break Azure deploys
that are already in flight, and it buys no extra security. The cost of the chosen option is
one branch in `digest()`.

One case is left over. A spec.json written by `develop` between #319 and this change says
`"provider": "openstack"`, even for an Azure adopter. With this change it now fails closed at
the Azure adapter, and the operator has to re-run DEPLOY_DESIGN. Say this in the commit body.

## Required behaviour
1. `DeployConfig()` equals `DeployConfig(enabled=False, target="openstack", iac="heat")`.
2. `[deploy].target` must be a key of `DEPLOY_IAC_BY_TARGET`, which means `"openstack"` or
   `"azure"`. Any other value raises `ConfigError("deploy.target", ...)`.
3. `[deploy].iac` defaults to the first format listed for the target, and must be one of the
   target's formats: `openstack -> ("heat",)` and `azure -> ("bicep", "arm")`. Any other
   value raises `ConfigError("deploy.iac", ...)`. `target = "azure"` with no `iac` gives
   `"bicep"`, exactly as before.
4. `DeployConfig.from_mapping(config)` returns the `[deploy]` table from a mapping shaped like
   a parsed vibey.toml or a project's stored config, and validates it the same way as
   requirements 2 and 3. An empty mapping `{}` gives the defaults. A `deploy` value that is
   not a table raises `ConfigError("deploy", ...)`.
5. `AzureTargetScope.digest()` works like this:
   - When `provider == "azure"`, it returns `sha256("tenant:subscription:resource_group:environment")`.
   - Otherwise it returns `sha256("provider:tenant:subscription:resource_group:environment")`.
   The non-Azure form produces the same bytes as today's code.
6. `DeploymentSpec.validate()` also reports two new errors:
   - `"provider is required"` when the provider is blank.
   - `"<name> must not contain ':'"` for each of `provider`, `tenant_id`, `subscription_id`,
     `resource_group` and `environment` that contains `:`.
7. `build_deployment_spec(..., deploy: DeployConfig | None = None)` sets these fields
   (`None` means `DeployConfig()`):
   - `provider=deploy.target`. An answer key `"provider"` is ignored, because only the
     declaration picks the cloud.
   - The default `region` comes from `DEPLOY_REGION_BY_TARGET`: `openstack -> "RegionOne"`
     and `azure -> "eastus"`.
   - The default `iac_provider` is `deploy.iac`.
   Answers can still override `region` and `iac_provider`.
8. `DeploySynthesizeHandler(..., deploy: DeployConfig | None = None)` passes its config to
   `build_deployment_spec`.
9. `load_spec` restores `provider`. A spec.json without that key loads as `"azure"`, because
   every such file predates the field and was written by the Azure-only pipeline.
10. `load_runtime_config_from_path` also returns the `[deploy]` table and validates it, so
    `vibey new` stores it in the project's config.
11. `build_full_worker(..., deploy: DeployConfig | None = None)`: `None` means
    `DeployConfig.from_mapping(project.config)`. The result is passed to `DeploySynthesizeHandler`.
12. A new `ScopeProviderMismatchError(Exception)` lives in `vibey.application.azure_port`.
    `AzCliClientAdapter` raises it in all four port methods when `scope.provider != "azure"`.
    The check runs before any subprocess starts.
13. These do not change: the in-memory adapter accepts any provider, and the protected
    `tests/system/test_delivery_stage_set.py` passes without being edited.

## Where to change
- `src/vibey/domain/config.py`
  - Imports (lines 9-11): add `from collections.abc import Mapping`.
  - After line 35 (`DEFAULT_LOCAL_CONTEXT_WINDOW`), add:
    ```python
    # Implemented deploy targets (ADR-0042, sub-doctrine 8.b) -> the IaC formats their
    # adapter runs; the first entry is the target's default `iac`.
    DEPLOY_IAC_BY_TARGET = {"openstack": ("heat",), "azure": ("bicep", "arm")}
    # The region a synthesized spec uses when the deploy interview names none.
    DEPLOY_REGION_BY_TARGET = {"openstack": "RegionOne", "azure": "eastus"}
    ```
  - `DeployConfig` (lines 136-140): change the default to `iac: str = "heat"`, and add:
    ```python
    @classmethod
    def from_mapping(cls, config: Mapping[str, object]) -> "DeployConfig":
        """The [deploy] table of a parsed vibey.toml or a project's stored config."""
        return _parse_deploy(dict(config))
    ```
  - `_parse_deploy` (lines 453-459) should do the following, in order:
    1. Read `target` with a default of `"openstack"`.
    2. Look up `formats = DEPLOY_IAC_BY_TARGET.get(target)`. If it is `None`, raise
       `ConfigError("deploy.target", f"must be one of {', '.join(sorted(DEPLOY_IAC_BY_TARGET))}, got {target!r}")`.
    3. Read `iac = _optional(table, "iac", "deploy.iac", str, formats[0])`.
    4. If `iac not in formats`, raise
       `ConfigError("deploy.iac", f"target {target!r} runs {', '.join(formats)}, got {iac!r}")`.
    5. Read `enabled` exactly as the code does today.
- `src/vibey/domain/interfaces/config_interface.py`: add `DeployConfigInterface` with the
  read-only properties `enabled: bool`, `target: str` and `iac: str`. Copy the layout of
  `TelemetryConfigInterface` (lines 31-36). Export it from
  `src/vibey/domain/interfaces/__init__.py`: add it to the import block (lines 2-6) and to
  `__all__`, keeping both sorted.
- `src/vibey/domain/deployment.py`
  - Above `class AzureTargetScope` (line 13), add a constant `LEGACY_DIGEST_PROVIDER = "azure"`.
    Give it a comment saying that pre-#319 consents hash the 4-field form, and that all of
    them are Azure consents.
  - `digest()` (lines 24-28) becomes:
    ```python
    fields = [self.tenant_id, self.subscription_id, self.resource_group, self.environment]
    if self.provider != LEGACY_DIGEST_PROVIDER:
        fields.insert(0, self.provider)
    return hashlib.sha256(":".join(fields).encode()).hexdigest()
    ```
  - `validate()`: after line 107 (the region check), add a check that the provider is not
    blank. Then loop over
    `("provider", "tenant_id", "subscription_id", "resource_group", "environment")` and use
    `getattr(t, name)` to check each field for `:`.
- `src/vibey/application/deploy_design_handler.py`
  - `build_deployment_spec` (lines 36-76) gains the keyword-only parameter
    `deploy: DeployConfig | None = None`, with `config = deploy if deploy is not None else DeployConfig()`.
  - The scope gets `region=_get("region", DEPLOY_REGION_BY_TARGET.get(config.target, "RegionOne"))`
    and `provider=config.target`.
  - The topology gets `iac_provider=_get("iac_provider", config.iac)`.
  - Make the docstring at lines 41-45 neutral about the provider.
  - `DeploySynthesizeHandler.__init__` (lines 156-167) gains
    `deploy: DeployConfig | None = None`, stored as `self._deploy`. At lines 185-187 (the `build_deployment_spec(` call), pass
    `deploy=self._deploy`.
- `src/vibey/infrastructure/deploy/state_repository.py:63-70`: add
  `provider=str(scope.get("provider", "azure")),` with a comment explaining the legacy default.
- `src/vibey/infrastructure/config_loader.py:10`: change to
  `RUNTIME_CONFIG_KEYS = ("notifications", "telemetry", "deploy")`, and update the docstring
  at lines 104-111.
- `src/vibey/application/azure_port.py:14-26`: add
  `class ScopeProviderMismatchError(Exception)` with the docstring "Raised when a cloud adapter
  is handed a target scope for another provider." Add it to `__all__`. Exception classes get
  no interface file here, as with `src/vibey/infrastructure/cache/redis.py:20` and
  `az_cli.py:36-44`.
- `src/vibey/infrastructure/azure/az_cli.py`
  - Import `ScopeProviderMismatchError` from `vibey.application.azure_port`.
  - Add this method:
    ```python
    def _require_provider(self, scope: AzureTargetScope) -> None:
        if scope.provider != "azure":
            raise ScopeProviderMismatchError(
                f"the az adapter deploys provider 'azure' only; this scope is {scope.provider!r}"
            )
    ```
  - Call it as the first statement of `discover_environment` (line 64), `execute_plan`
    (lines 97-100, on `spec.target_scope`, before `_require_consent`), `get_resource_status`
    (line 145) and `delete_resource` (lines 159-162, before `_require_consent`).
- `src/vibey/bootstrap.py`
  - Import `DeployConfig` next to `VibeyConfig` (line 77).
  - `build_full_worker` (lines 341-352) gains `deploy: DeployConfig | None = None`.
  - Next to line 371, add
    `deploy_config = deploy if deploy is not None else DeployConfig.from_mapping(project.config)`.
  - Pass `deploy=deploy_config` to `DeploySynthesizeHandler` (lines 568-573), and extend the
    docstring.
- Do not rename `AzureTargetScope`. Its aliases `TargetScope` and `CloudTargetScope` already
  exist.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_deploy_target_config.py tests/domain/test_scope_digest.py` passes.
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_config.py tests/domain/test_deployment_domain.py tests/domain/test_domain_purity.py` passes unchanged.
- [ ] `uv run pytest -q -p no:cacheprovider tests/application/test_deploy_design_and_acceptance.py tests/application/test_interfaces_convention.py` passes.
- [ ] `uv run pytest -q -p no:cacheprovider tests/infrastructure/deploy tests/infrastructure/test_config_loader.py tests/infrastructure/azure` passes.
- [ ] `uv run pytest -q -p no:cacheprovider -m system tests/system/test_delivery_stage_set.py` passes, and `git diff develop -- tests/system/test_delivery_stage_set.py` is empty.
- [ ] The 4-field Azure digest is pinned by a literal in a test: `a3aca17c2ecbacc58a642eebf46c8698516c80b467e177e1bd5afa8c9cb94fe9`.
- [ ] All four layers keep 100% branch coverage (see Checks).

## Tests to write first (TDD)
- New `tests/domain/test_deploy_target_config.py`:
  - `test_default_deploy_config_is_sovereign`: checks `DeployConfig()`, and that parsing
    `'[project]\nname = "x"\n'` gives `DeployConfig()`.
  - `test_azure_target_defaults_its_iac_to_bicep` and `test_azure_accepts_arm`.
  - `test_unknown_target_is_refused`: `target = "aws"` raises `ConfigError` matching `deploy.target`.
  - `test_iac_must_match_the_target`: parametrize over `openstack`/`bicep` and `azure`/`heat`;
    both raise matching `deploy.iac`.
  - `test_from_mapping_reads_a_stored_project_config`: the input
    `{"project": {"name": "p"}, "deploy": {"target": "azure"}}` gives target `"azure"`; the
    input `{}` gives the defaults; the input `{"deploy": "azure"}` raises `ConfigError`.
  - `test_deploy_config_satisfies_its_interface`: checks
    `isinstance(DeployConfig(), DeployConfigInterface)`.
- New `tests/domain/test_scope_digest.py`. The fields are `tenant-123`, `sub-456`,
  `rg-vibey-dev`, `dev`, region `eastus`.
  - `test_azure_scope_keeps_the_pre_provider_digest`: with `provider="azure"` the digest equals
    `a3aca17c2ecbacc58a642eebf46c8698516c80b467e177e1bd5afa8c9cb94fe9`.
  - `test_openstack_scope_digest_carries_the_provider`: with the default provider the digest
    equals `57d727a9ffb8ec9eb505422ed834872e36ca66ee3072d0c8e110b69b66b66cb9`.
  - `test_digest_never_crosses_providers`: providers `azure`, `openstack` and `aws` with the
    same fields give 3 distinct digests.
  - `test_legacy_consent_verifies_an_azure_spec_only`: a consent holding the `a3ac...` digest
    passes `matches_spec` for the Azure spec and fails for the OpenStack spec.
  - `test_validate_requires_a_provider`: `provider="  "` gives `"provider is required"`.
  - `test_validate_refuses_colons_in_digest_fields`: parametrize over the 5 field names; each
    gives `"<name> must not contain ':'"`.
- Append to `tests/application/test_deploy_design_and_acceptance.py`, copying the fakes used
  by the test at lines 548-587:
  - `test_spec_provider_follows_the_configured_target`: with
    `deploy=DeployConfig(target="azure", iac="bicep")` the spec has provider `azure`, region
    `eastus` and iac `bicep`.
  - `test_default_spec_is_openstack_heat_regionone`: with no `deploy` the spec has provider
    `openstack`, region `RegionOne` and iac `heat`, and `validate() == []`.
  - `test_answers_cannot_switch_the_provider`: the answer `{"provider": "azure"}` still gives
    provider `openstack`.
  - `test_synthesize_handler_stamps_the_configured_target`: a
    `DeploySynthesizeHandler(..., deploy=DeployConfig(target="azure", iac="bicep"))` saves a
    spec with provider `"azure"`.
- Append to `tests/infrastructure/deploy/test_state_repository.py`:
  - `test_provider_round_trips`: an Azure spec is saved and loads back as Azure.
  - `test_legacy_spec_loads_as_azure_and_its_consent_still_matches`: save a spec, then delete
    the `"provider"` key from spec.json. Write consent.json with
    `hashlib.sha256(b"t-1:s-1:rg-one:dev").hexdigest()`. After loading, the provider is
    `"azure"` and `load_consent(...).matches_spec(loaded)` is true.
- Append to `tests/infrastructure/test_config_loader.py`:
  - `test_deploy_table_is_stored_for_project_creation`: the input `[deploy]\ntarget = "azure"\n`
    gives `{"deploy": {"target": "azure"}}`.
  - Add the case `('[deploy]\ntarget = "aws"\n', "deploy.target")` to the parametrize list of
    `test_runtime_tables_are_validated_before_persistence`.
- `tests/infrastructure/azure/test_az_cli.py`:
  - In `_spec()` (lines 36-43), add `provider="azure"`.
  - New test `test_every_method_refuses_a_non_azure_scope`: build the scope with
    `dataclasses.replace(scope, provider="openstack")`. All four methods raise
    `ScopeProviderMismatchError`, and `executor.calls == []`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/domain tests/application tests/infrastructure/deploy tests/infrastructure/azure tests/infrastructure/test_config_loader.py tests/system/test_delivery_stage_set.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=   # needs Postgres 17
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Part 2 owns these: the OpenStack adapter, the Heat renderer, `vibey worker --cloud`, and
  the worker's CLI resolution of `[deploy]` (including the vibey.toml fallback for older
  projects).
- The deploy interview wording ("Please provide Azure target", deploy_design_handler.py:102)
  and the Azure-shaped placeholders for identity and SKU.
- The Kubernetes operator's project config (src/vibey/infrastructure/operator/handlers.py:53-68).
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or the skill trees;
  the docs wave owns them. For example, docs/reference/configuration.md:228 still says the
  default is `"azure"`.
- Do not push, open PRs, or change git remotes. When done, commit locally with a Conventional
  Commit message; the hooks add the `Made-With:` trailer, so do not bypass them.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.
- Never edit tests/system/test_delivery_stage_set.py (protected path, .vibey-gh.toml:78-85).

---

## Context shared by every part of this work
# OpenStack deployment client (`[deploy].target = "openstack"`) -- two ordered parts

This work is too big for one 14B lane: it touches about 15 source files across four layers,
adds a new package and changes a CLI flag. It is split into **Part 1** and **Part 2**, in that
order. Part 2 starts from a tree where Part 1 is committed. Each part is self-contained, so a
lane reads only its own part. Evidence was taken from `develop` at `d47c196d`. Line numbers
refer to that commit.

---
