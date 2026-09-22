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

## Context shared by every part of this work
# OpenStack deployment client (`[deploy].target = "openstack"`) -- two ordered parts

This work is too big for one 14B lane: it touches about 15 source files across four layers,
adds a new package and changes a CLI flag. It is split into **Part 1** and **Part 2**, in that
order. Part 2 starts from a tree where Part 1 is committed. Each part is self-contained, so a
lane reads only its own part. Evidence was taken from `develop` at `d47c196d`. Line numbers
refer to that commit.

---
