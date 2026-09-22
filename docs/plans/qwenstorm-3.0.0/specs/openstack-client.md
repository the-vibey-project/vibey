# OpenStack deployment client (`[deploy].target = "openstack"`) -- two ordered parts

This work is too big for one 14B lane: it touches about 15 source files across four layers,
adds a new package and changes a CLI flag. It is split into **Part 1** and **Part 2**, in that
order. Part 2 starts from a tree where Part 1 is committed. Each part is self-contained, so a
lane reads only its own part. Evidence was taken from `develop` at `d47c196d`. Line numbers
refer to that commit.

---

# Part 1 -- the deployment scope's provider follows `[deploy].target`

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

# Part 2 -- a real OpenStack CLI client, chosen by `[deploy].target` and `vibey worker --cloud`

Prerequisite: Part 1 is committed. That provides `DeployConfig.from_mapping`, the provider
stamped on the scope, `ScopeProviderMismatchError`, and `build_full_worker(deploy=...)`.
This is the larger lane. Work in this order, and commit after each step once it is green:
1. heat.py and its tests.
2. openstack_cli.py and its tests.
3. The interfaces and `.importlinter`.
4. The az_cli class attributes.
5. The CLI and its tests.

## Title
feat(openstack)!: a real OpenStack CLI client, selected by [deploy].target and vibey worker --cloud

## Why
ADR-0042:62-64 promises "the self-hosted OpenStack adapter (a real `openstack` CLI adapter
plus the existing in-memory default)". Only Azure has a real client
(src/vibey/infrastructure/azure/az_cli.py). The worker's only cloud switch is
`--azure {memory,az}` (src/vibey/cli/main.py:1451-1459, 1481-1494). It is hard-wired to
Azure, and it runs its `az` preflight before the project is even resolved, so before its
`[deploy].target` is known.

**CLI decision: add `--cloud {memory,cli}`, and keep `--azure` as a hidden, deprecated
alias.** `--azure memory|az` combined two choices: whether mutations are real, and which cloud
to use. ADR-0042 moved "which cloud" into `[deploy].target`, which is the reviewed and merged
declaration that sub-doctrine 8.b requires for a paid cloud. A flag that also named the cloud
(runbook 03:45 `--cloud {memory|az|aws|gcp}`, written before `[deploy].target` existed) would
be a second source of truth. It could disagree with the declaration, and it would let one
command-line word select a paid cloud without that declaration. So the flag keeps only the
safety switch: `memory` for in-memory, `cli` for the target provider's own CLI. Adding a
cloud later then means adding a target, not a flag value (sub-doctrine 12.c). `--azure az`
still works for one major version and means `--cloud cli`, but only when the project's
target is `"azure"`. That way an old invocation can never mutate OpenStack.

## Required behaviour
**A. `HeatTemplateRenderer` (src/vibey/infrastructure/openstack/heat.py)**
1. `HeatTemplateRenderer(*, image: str = DEFAULT_IMAGE)`, where
   `DEFAULT_IMAGE = "docker.io/library/nginx:stable"`. Its method `render(spec) -> dict[str, Any]`
   returns a HOT template. `render` raises `UnsupportedHeatTopology(ValueError)` when any of
   these holds:
   - `spec.topology.iac_provider.lower() != "heat"`
   - `service_type != "container_app"`
   - `instances < 1`
   The rule is the same as arm.py:13-14: an autonomous deploy never improvises the shape of
   infrastructure.
2. The template shape must match this sample exactly. The sample spec has `spec_id="spec-os-1"`,
   `tags={"owner": "vibey"}`, `environment="dev"`, `instances=2`, `ingress_enabled=True`,
   `tls_enabled=True` and the default image. The name is
   `app = "vibey-" + spec_id[:20].lower().replace("_", "-")`, as in arm.py:38.
   ```json
   {"heat_template_version": "2018-08-31",
    "description": "vibey deployment spec-os-1",
    "parameters": {"image": {"type": "string", "default": "docker.io/library/nginx:stable",
                             "description": "Container image to run"}},
    "resources": {
      "ingress": {"type": "OS::Neutron::SecurityGroup", "properties": {
         "name": "vibey-spec-os-1-ingress",
         "rules": [{"direction": "ingress", "protocol": "tcp", "port_range_min": 443,
                    "port_range_max": 443, "remote_ip_prefix": "0.0.0.0/0"}]}},
      "app_0": {"type": "OS::Zun::Container", "properties": {
         "name": "vibey-spec-os-1-0", "image": {"get_param": "image"}, "restart_policy": "always",
         "labels": {"owner": "vibey", "vibey.spec_id": "spec-os-1", "vibey.environment": "dev"},
         "security_groups": [{"get_resource": "ingress"}]}},
      "app_1": {"...": "same as app_0 with name vibey-spec-os-1-1"}},
    "outputs": {"endpoint": {"description": "Network addresses of the first container",
                             "value": {"get_attr": ["app_0", "addresses"]}}}}
   ```
3. Ingress rules:
   - A spec with `tls_enabled` opens only port 443, never a plaintext port. The image must
     terminate TLS itself: no Octavia load balancer is created.
   - `tls_enabled=False` opens port 80.
   - With `ingress_enabled=False` there is no `ingress` resource and no `security_groups` key.
   - `OS::Zun::Container` has no port property, so the security group is how ingress is
     exposed. The properties used are from heat/engine/resources/openstack/zun/container.py.

**B. `OpenStackCliAdapter` (src/vibey/infrastructure/openstack/openstack_cli.py) implements `CloudClientPort`**

4. Constructor: `(*, executor: CommandExecutor | None = None, image: str = DEFAULT_IMAGE)`.
   The default executor is `CleanGitEnvSubprocessExecutor()`, as in az_cli.py:48-55. It
   creates a `HeatTemplateRenderer(image=image)`. Class attributes:
   ```python
   PROVIDER: ClassVar[str] = "openstack"
   PREFLIGHT_ARGV: ClassVar[tuple[str, ...]] = ("openstack", "token", "issue", "-f", "value", "-c", "project_id")
   LOGIN_HINT: ClassVar[str] = ("OpenStack credentials: a clouds.yaml entry selected by OS_CLOUD so that "
       "`openstack token issue` succeeds (each deployment's subscription_id names its clouds.yaml entry)")
   ```
5. Refusal order is the same in every method, and every refusal happens before any subprocess:
   1. If `scope.provider != "openstack"`, raise `ScopeProviderMismatchError`.
   2. For mutations only, if consent is missing, unauthorized or bound to another digest,
      raise `MutationNotAuthorizedError`, imported from `vibey.application.azure_port`. The
      digest compared is `spec.scope_digest()` for `execute_plan` and `scope.digest()` for
      `delete_resource`.
   3. If the stack name is invalid, raise `InvalidStackName(VibeyError)`. A valid name
      satisfies `re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,254}", scope.resource_group)`.
   4. For `execute_plan` only, render the template (`UnsupportedHeatTopology`).
6. Scope mapping. These options are passed on every call, so what gets mutated is the scope
   the consent names, never whatever the ambient `OS_CLOUD` points at.
   - `subscription_id` -> `--os-cloud`: the clouds.yaml entry, the same account boundary that
     `az --subscription` selects.
   - `tenant_id` -> `--os-project-id`: the Keystone project ("tenant" is its old name).
   - `region` -> `--os-region-name`.
   - `resource_group` -> the Heat stack name: the unit that is created, updated and deleted
     together, like a resource group on Azure.
   `AUTH = ("--os-cloud", s.subscription_id, "--os-project-id", s.tenant_id, "--os-region-name", s.region)`.
   Every argv is `("openstack", *AUTH, *tail)`.
7. Commands, where STACK is the stack name:

   | method | step | argv tail | Azure analogue | on non-zero exit |
   |---|---|---|---|---|
   | discover_environment | 1 | `token issue -c project_id -f json` | `az account show` | raise |
   | | 2 | `stack resource list STACK -f json` | `az resource list` | `existing_resources=()` (first deploy) |
   | execute_plan | 1 | `stack show STACK -c id -f json` | (existence probe) | take the create branch |
   | | 2 | `stack create --template FILE --wait STACK` if step 1 failed, else `stack update --template FILE --wait STACK` | `az group create` + `az deployment group create` | raise |
   | | 3 | `stack show STACK -f json` | deployment output | raise |
   | get_resource_status | 1 | `stack show STACK -c id -c stack_status -f json` | `az resource show` | raise |
   | delete_resource | 1 | `stack delete --yes --wait STACK` | `az resource delete` | if `"stack not found"` is in `(stdout + stderr).lower()`, return; else raise |

   - Create-or-update makes a replayed job, for example after a lease expiry, an update rather
     than a failed create (CLAUDE.md: every job is idempotent under replay).
   - The same applies to deleting a stack that is already gone.
   - Step 3 exists because `create` and `update` with `--wait` print only a short view without
     outputs.
8. `FILE`: open `tempfile.NamedTemporaryFile("w", suffix=".json", prefix="vibey-heat-", delete=False)`,
   write the template with `json.dump`, and unlink the file in a `finally`, as at
   az_cli.py:114-135. JSON is valid Heat template input.
9. Results:
   - Discovery returns `AzureDiscoveryResult(tenant_id=str(project_id or scope.tenant_id), subscription_id=..., resource_group=..., location=scope.region, existing_resources=tuple(list) if a list else ())`.
     `project_id` is read from the step 1 dict. If that JSON is not a dict, fall back to `scope.tenant_id`.
   - Execute: from the step 3 value `shown` (if it is not a dict, use `{}`), set
     `raw = str(shown.get("stack_status", ""))`.
     - `outputs` maps `output_key` to `output_value` for each dict in `shown.get("outputs") or []`
       that has an `output_key`, plus `outputs["stack_status"] = raw`.
     - Return `AzureExecutionResult(deployment_id=str(shown.get("id", "")), provisioning_state=self.stack_state(raw), outputs=outputs, applied_at=datetime.now(UTC))`.
   - Status returns
     `AzureResourceStatus(resource_id=resource_id, provisioning_state=state, health_state="Healthy" if state == "Succeeded" else "Degraded")`,
     as at az_cli.py:156.
     - The handlers pass `spec.spec_id` as `resource_id` (deploy_execute_handler.py:88,
       deploy_review_routing.py:147). That value names the deployment. The stack is
       OpenStack's unit, so the stack's status answers for it, and `resource_id` is echoed back.
10. `@staticmethod stack_state(stack_status: str) -> str` returns:
    - `"Succeeded"` for `CREATE_COMPLETE` or `UPDATE_COMPLETE`. This is the word that
      deploy_execute_handler.py:89 checks.
    - `"Running"` for any status ending in `_IN_PROGRESS`.
    - `"Failed"` for any status ending in `_FAILED`, and for `ROLLBACK_COMPLETE`.
    - `"Unknown"` for anything else.
11. A non-zero exit raises `OpenStackCliError(argv, stderr)` with the message
    `f"{' '.join(argv)} failed: {stderr.strip()[:500]}"`. stdout never goes into an error.

**C. az_cli**

12. Add class attributes to `AzCliClientAdapter` (az_cli.py:47):
    - `PROVIDER = "azure"`
    - `PREFLIGHT_ARGV = ("az", "account", "show", "-o", "none")`
    - ``LOGIN_HINT = "a logged-in Azure CLI: run `az login` first"``
    Its `_require_provider` compares against `self.PROVIDER`. At line 5, change the docstring
    to "`vibey worker --cloud cli` with `[deploy].target = "azure"`".

**D. `vibey worker`**

13. Replace the `--azure` option (main.py:1451-1459) with:
    ```python
    cloud: Annotated[str | None, typer.Option("--cloud", help="Cloud client for the deploy stage set: "
        "'memory' (default; touches no real infrastructure) or 'cli' (the [deploy].target provider's "
        "own CLI, `openstack` or `az`, which mutates real resources on consented deploys)")] = None,
    azure: Annotated[str | None, typer.Option("--azure", hidden=True, help="Deprecated alias of "
        "--cloud: 'az' is --cloud cli for a project whose [deploy].target is 'azure'")] = None,
    ```
14. Replace main.py:1481-1494. This check runs synchronously, before `run_worker`, and every
    failure exits with `typer.Exit(2)`:
    ```python
    if azure is not None and azure not in ("memory", "az"):
        -> echo "--azure must be 'memory' or 'az'"
    if cloud is not None and azure is not None:
        -> echo "--azure is a deprecated alias of --cloud; pass only --cloud"
    if cloud is not None and cloud not in ("memory", "cli"):
        -> echo "--cloud must be 'memory' or 'cli'"
    cloud_mode = cloud if cloud is not None else ("cli" if azure == "az" else "memory")
    ```
15. After main.py:1575 (`provider = _resolve_provider(...)`), resolve the declaration. Put the
    reason in a comment: projects created before 3.0.0 stored no `[deploy]`, so the
    repository's own vibey.toml answers for them.
    ```python
    stored_deploy = project.config.get("deploy")
    if stored_deploy is None:
        stored_deploy = load_runtime_config_from_path(
            Path(project.repo_path) / "vibey.toml"
        ).get("deploy", {})
    deploy = DeployConfig.from_mapping({"deploy": stored_deploy})
    ```
    `load_runtime_config_from_path` is already imported (main.py:59). A `ConfigError`
    propagates to `guard()` (main.py:1762), which exits with code 3.
16. Then select the client:
    - If `cloud_mode == "cli"`:
      1. If `azure == "az"` and `deploy.target != "azure"`, echo
         `--azure az requires [deploy].target = "azure"; this project's target is '<target>' -- use --cloud cli`
         and exit with `EXIT_USAGE`.
      2. Import both adapter classes lazily and pick one:
         `adapters: dict[str, type[AzCliClientAdapter] | type[OpenStackCliAdapter]] = {"azure": ..., "openstack": ...}`
         and `adapter_cls = adapters[deploy.target]`. The explicit annotation is required by mypy.
      3. Run `subprocess.run(list(adapter_cls.PREFLIGHT_ARGV), capture_output=True, text=True)`
         with the comment `# nosec B603 B607 - fixed argv, never shell=True`. Treat `OSError`
         (the CLI is not installed) as not ready.
      4. If not ready, echo
         `--cloud cli with [deploy].target = '<target>' requires <adapter_cls.LOGIN_HINT>`
         and `typer.Exit(1)`.
      5. Otherwise set `cloud_client = adapter_cls()`.
    - Otherwise `cloud_client = None`, which means in-memory. Annotate it as
      `cloud_client: CloudClientPort | None`.
17. `build_full_worker(..., azure_client=cloud_client, deploy=deploy)` (main.py:1702-1711).
    Append ` deploy_target={deploy.target} cloud={cloud_mode}` to the "worker started:" line
    (main.py:1718-1721).
    - Existing tests assert substrings of that line, so they keep passing.
    - The preflight uses ambient credentials. A scope-specific auth failure surfaces later as
      `OpenStackCliError` and goes to DEPLOY_REVIEW triage (deploy_execute_handler.py:136).

## Where to change
- New files, each starting with the same provenance header line 1 as az_cli.py:
  - `src/vibey/infrastructure/openstack/__init__.py`: a docstring plus exports of
    `HeatTemplateRenderer`, `OpenStackCliAdapter`, `OpenStackCliError`, `InvalidStackName`,
    `UnsupportedHeatTopology` and `DEFAULT_IMAGE`.
  - `src/vibey/infrastructure/openstack/heat.py`: requirements A1-A3.
  - `src/vibey/infrastructure/openstack/openstack_cli.py`: requirements B4-B11. Copy
    az_cli.py:18-62 for imports, the error class and the JSON helper. The skeleton is
    `_argv(scope, *tail)`, `async _checked(argv) -> str` (raises on non-zero),
    `async _json(argv) -> Any` (returns `json.loads(stdout) if stdout.strip() else {}`),
    `_require_provider`, `_require_consent`, `_stack_name`, `stack_state`, and the 4 port
    methods from the table.
  - `src/vibey/infrastructure/openstack/interfaces/__init__.py`: exports both interfaces,
    following the pattern of `src/vibey/infrastructure/secrets/interfaces/__init__.py`.
  - `src/vibey/infrastructure/openstack/interfaces/openstack_cli_interface.py`:
    `@runtime_checkable class OpenStackCliAdapterInterface(CloudClientPort, Protocol)`. Copy
    `src/vibey/infrastructure/secrets/interfaces/openbao_interface.py`.
  - `src/vibey/infrastructure/openstack/interfaces/heat_interface.py`:
    `@runtime_checkable class HeatTemplateRendererInterface(Protocol)` with
    `def render(self, spec: DeploymentSpec) -> dict[str, Any]: ...`.
- `.importlinter:125`: add `    vibey.infrastructure.openstack.interfaces` to the
  `infrastructure-interfaces-declare-only` source list (lines 113-129).
- `src/vibey/infrastructure/azure/az_cli.py`: lines 5 and 47, as in C12.
- `src/vibey/cli/main.py`: lines 1451-1459, 1481-1494, after 1575, 1702-1711 and 1718-1721
  (D13-D17). Import `DeployConfig` from `vibey.domain.config`, and `CloudClientPort` from
  `vibey.application.interfaces`.
- Update the existing tests in `tests/cli/test_operational_commands.py`:
  - `test_worker_azure_az_requires_a_logged_in_cli` (lines 1989-2001): first seed a project
    with `config={"deploy": {"target": "azure"}}`. The check now runs after the project is
    resolved.
  - `test_worker_azure_az_builds_the_real_adapter_when_logged_in` (lines 2004-2025): change
    its seeded config to `{"deploy": {"target": "azure"}}`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/infrastructure/openstack tests/infrastructure/azure` passes.
- [ ] `uv run pytest -q -p no:cacheprovider tests/cli/test_operational_commands.py -k "worker"` passes (needs Postgres 17).
- [ ] `uv run lint-imports` reports the infrastructure interfaces contract, including
      `vibey.infrastructure.openstack.interfaces`, as KEPT.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_import_contracts_bind.py tests/application/test_interfaces_convention.py` passes.
- [ ] `grep -rn "openstack" src/vibey/cli/main.py` shows the adapter selection. `vibey worker --help`
      lists `--cloud` and does not list `--azure`.
- [ ] `infrastructure/` and `cli/` stay at 100% branch coverage.

## Tests to write first (TDD)
- New `tests/infrastructure/openstack/__init__.py`, holding only the header line, as in
  tests/infrastructure/deploy/__init__.py.
- New `tests/infrastructure/openstack/test_heat_renderer.py`:
  - `test_render_matches_the_sample_template` (A2, the whole dict)
  - `test_plain_ingress_opens_port_80`
  - `test_no_ingress_means_no_security_group`
  - `test_custom_image_is_the_parameter_default`
  - `test_render_refuses_what_it_cannot_run`, parametrized over iac `"bicep"`, service_type
    `"kubernetes_fleet"` and `instances=0`
  - `test_renderer_satisfies_its_interface`
- New `tests/infrastructure/openstack/test_openstack_cli.py`.
  - Test setup:
    - The scope is `tenant_id="proj-1"`, `subscription_id="cloud-1"`,
      `resource_group="rg-vibey-dev"`, `environment="dev"`, `region="RegionOne"`,
      `provider="openstack"`, with `iac_provider="heat"`.
    - `AUTH = ("--os-cloud", "cloud-1", "--os-project-id", "proj-1", "--os-region-name", "RegionOne")`.
    - Use a `ScriptedExecutor(responses)`. Each `execute(argv)` records `argv`. If `--template`
      is in `argv`, it also records `(path, json.loads(path.read_text()))`. It then pops the
      next `(returncode, stdout, stderr)` and returns a `CommandResult` from
      `vibey.infrastructure.engines.claudeloop_process`.
  - `test_discovery_reads_the_token_project_and_stack_resources`: `calls[0] == ("openstack", *AUTH, "token", "issue", "-c", "project_id", "-f", "json")`; tenant is `"p-real"`; resources come back as given.
  - `test_discovery_treats_a_missing_stack_as_empty` and `test_discovery_falls_back_to_the_scope_tenant` (stdout `[]`).
  - `test_execute_plan_creates_a_missing_stack_and_reports_outputs`:
    - Responses: probe `(1, "", "Stack not found")`, create `(0, "", "")`, then show with
      `CREATE_COMPLETE` and one `endpoint` output.
    - Asserts: `calls[1][7:9] == ("stack", "create")`; the result is `"Succeeded"`;
      `outputs["endpoint"]` and `outputs["stack_status"]` are set; the recorded template has
      `heat_template_version`; the file no longer exists.
  - `test_execute_plan_updates_an_existing_stack` (`UPDATE_COMPLETE`).
  - `test_execute_plan_surfaces_a_failed_create`: `OpenStackCliError` mentions `CREATE_FAILED`, the template is deleted, and there are only 2 calls.
  - `test_execute_plan_tolerates_malformed_show_output`: parametrize over stdout `[]` and outputs `["junk", {"no_key": 1}]`; `deployment_id` handling and `outputs == {"stack_status": ...}`.
  - `test_mutations_are_refused_without_digest_bound_consent`: stale, unauthorized, and a stale delete; `calls == []`.
  - `test_every_method_refuses_a_scope_for_another_provider`: provider `"azure"`, 4 methods, `calls == []`.
  - `test_invalid_stack_name_is_refused_before_any_command`: `resource_group="9 bad"`.
  - `test_unsupported_topology_is_refused_before_any_command`: iac `"bicep"`, `calls == []`.
  - `test_status_maps_heat_states`, parametrized:

    | stack_status | state | health |
    |---|---|---|
    | CREATE_COMPLETE | Succeeded | Healthy |
    | UPDATE_COMPLETE | Succeeded | Healthy |
    | CREATE_IN_PROGRESS | Running | Degraded |
    | UPDATE_FAILED | Failed | Degraded |
    | ROLLBACK_COMPLETE | Failed | Degraded |
    | DELETE_COMPLETE | Unknown | Degraded |
    | stdout `{}` | Unknown | Degraded |

    The `resource_id` is echoed back.
  - `test_consented_delete_runs_stack_delete`: `calls[0][7:] == ("stack", "delete", "--yes", "--wait", "rg-vibey-dev")`.
  - `test_delete_of_an_already_deleted_stack_is_idempotent`: `(1, "Stack not found: rg-vibey-dev\n", "Unable to delete 1 of the 1 stacks.")` returns None.
  - `test_delete_failure_raises` (`Forbidden`).
  - `test_openstack_failures_surface_argv_and_stderr`.
  - `test_adapter_satisfies_the_cloud_port`: `isinstance` against both `OpenStackCliAdapterInterface` and `CloudClientPort`.
- `tests/infrastructure/azure/test_az_cli.py`: `test_az_preflight_is_declared_on_the_adapter`.
- `tests/cli/test_operational_commands.py`. Tests that seed a project follow
  `test_worker_azure_az_builds_the_real_adapter_when_logged_in`: use
  `@pytest.mark.usefixtures("_fast_engine_preflight")`, patch `vibey.cli.main.subprocess.run`
  and patch `PostgresJobReadyNotifier`.
  - `test_worker_rejects_unknown_cloud_mode` (`--cloud gcp` gives exit 2).
  - `test_worker_rejects_cloud_with_the_deprecated_azure_flag` (exit 2).
  - `test_worker_azure_az_refuses_a_project_targeting_openstack`: config `{}`; exit 2; the output contains `target = "azure"`.
  - `test_worker_cloud_cli_preflights_openstack_for_the_default_target`: exit 0; some call to the patched `subprocess.run` has `args[0] == ["openstack", "token", "issue", "-f", "value", "-c", "project_id"]`; the output contains `deploy_target=openstack cloud=cli`.
  - `test_worker_cloud_cli_refuses_without_openstack_credentials`: exit 1; the output contains `openstack token issue`.
  - `test_worker_cloud_cli_reports_a_missing_cli`: `side_effect=FileNotFoundError`; exit 1.
  - `test_worker_reads_deploy_from_the_repository_for_a_project_that_stored_none`: `tmp_path/"vibey.toml"` holds `[deploy]\ntarget = "azure"\n`; config `{}`; `--once` gives exit 0 and `deploy_target=azure`.
  - `test_worker_prefers_the_stored_deploy_table`: vibey.toml says azure and config is `{"deploy": {"target": "openstack"}}`, giving `deploy_target=openstack`.
  - `test_worker_refuses_an_invalid_deploy_declaration`: vibey.toml has `target = "aws"`; exit 3; the output contains `deploy.target`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/openstack tests/infrastructure/azure tests/cli/test_operational_commands.py tests/meta/test_import_contracts_bind.py tests/application/test_interfaces_convention.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=   # needs Postgres 17
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Any live OpenStack or Azure run: `tests/live/**` is protected, and the tests fake only the
  subprocess boundary.
- TLS termination through Octavia/Barbican, mapping SKU to Zun cpu/memory, and choosing a network.
- AWS and GCP targets, and the Kubernetes operator's project config.
- `deploy_execute_handler`'s `resource_id` contract. It passes `spec.spec_id`, which
  `az resource show --ids` cannot resolve on a real Azure run. That bug predates this change;
  record it and leave it alone.
- The in-memory adapter, `AzureCliAdapter` in azure/adapter.py, and the deploy interview wording.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md, README.md or the
  skill trees; the docs wave owns them. For example, docs/reference/cli.md:375 still documents
  `--azure`.
- Do not push, open PRs, or change git remotes. When done, commit locally with a Conventional
  Commit message; the hooks add the `Made-With:` trailer.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
  Exception classes carry no behaviour and follow the existing precedent of having no interface
  (cache/redis.py:20).
- Every job idempotent under replay (hence create-or-update and the not-found delete); the ledger is append-only.
- Never shell out with `shell=True`. Every argv is a fixed tuple, as in az_cli.py.
