<!-- split of #331: child 2 of 5; audit: issue-audit/updates/331.md -->

## Title
feat(openstack): OpenStackCliAdapter drives Heat stacks through the `openstack` CLI

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:136-137`) makes self-hosted OpenStack the
cloud default, and ADR-0042
(`docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:61-64`)
promises "a real `openstack` CLI adapter plus the existing in-memory default". Today the only real
cloud client is `AzCliClientAdapter` (`src/vibey/infrastructure/azure/az_cli.py:47-165`), so a
project whose `[deploy].target` is the default `openstack` can only ever deploy into memory. This
lane adds the OpenStack implementation of `CloudClientPort`
(`src/vibey/application/interfaces/azure.py:44-68`) over the `openstack` CLI and Heat, rendering
templates with lane `split-331-1-heat-renderer`'s `HeatTemplateRenderer`. Every refusal happens
before any subprocess, every command goes through the injected `CommandExecutor` (9.b,
`doctrines.md:349`), and `preflight()` gives the worker a declared seam instead of the raw
`subprocess.run` it uses today (`src/vibey/cli/main.py:1488-1490`).

## Required behaviour
1. `src/vibey/infrastructure/openstack/openstack_cli.py` declares
   `class InvalidStackName(VibeyError)`, `class OpenStackCliError(VibeyError)` and
   `class OpenStackCliAdapter`.
2. **Constructor:**
   `OpenStackCliAdapter(*, executor: CommandExecutor | None = None, renderer: HeatTemplateRendererInterface | None = None, image: str = DEFAULT_IMAGE)`.
   - `self._executor = executor or CleanGitEnvSubprocessExecutor()` (as `az_cli.py:54`);
   - `self._renderer = renderer if renderer is not None else HeatTemplateRenderer(image=image)`
     (`image` is used only when no renderer is given).
3. **Class attributes** (`typing.ClassVar`), exactly:
   ```python
   PROVIDER: ClassVar[str] = "openstack"
   PREFLIGHT_ARGV: ClassVar[tuple[str, ...]] = ("openstack", "token", "issue", "-f", "value", "-c", "project_id")
   LOGIN_HINT: ClassVar[str] = (
       "OpenStack credentials: a clouds.yaml entry selected by OS_CLOUD so that "
       "`openstack token issue` succeeds (each deployment's subscription_id names its clouds.yaml entry)"
   )
   STACK_NAME: ClassVar[re.Pattern[str]] = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,254}")
   ```
4. **Refusal order**, the same in every method, all before any command runs:
   1. `self._require_provider(scope)`: when `scope.provider != self.PROVIDER`, raise
      `ScopeProviderMismatchError(f"the openstack adapter deploys provider {self.PROVIDER!r} only; this scope is {scope.provider!r}")`
      (`ScopeProviderMismatchError` is imported from `vibey.application.azure_port`, where lane
      `split-330-4-az-scope-guard` adds it). For `execute_plan` the scope is `spec.target_scope`.
   2. Mutations only (`execute_plan`, `delete_resource`): `self._require_consent(digest, consent)`
      raises `MutationNotAuthorizedError("mutation refused: consent is missing, unauthorized, or bound to a different target scope digest")`
      (imported from `vibey.application.azure_port`) when
      `not consent.explicit_mutation_authorized or consent.target_scope_digest != digest`. The digest
      is `spec.scope_digest()` for `execute_plan` and `scope.digest()` for `delete_resource`.
   3. `self._stack_name(scope) -> str`: returns `scope.resource_group` when
      `self.STACK_NAME.fullmatch(scope.resource_group)`; otherwise raises
      `InvalidStackName(f"resource_group {scope.resource_group!r} is not a Heat stack name: it must start with a letter and hold only letters, digits, '_', '.' and '-' (at most 255 characters)")`.
   4. `execute_plan` only: `template = self._renderer.render(spec)` (raises
      `UnsupportedHeatTopology`, lane `split-331-1-heat-renderer`).
5. **Scope mapping.** These options go on every call, so what is mutated is the scope the consent
   names, never whatever the ambient `OS_CLOUD` points at: `subscription_id` → `--os-cloud` (the
   clouds.yaml entry, the account boundary `az --subscription` selects), `tenant_id` →
   `--os-project-id` (the Keystone project; "tenant" is its old name), `region` →
   `--os-region-name`, and `resource_group` → the Heat stack name (the unit created, updated and
   deleted together, like an Azure resource group).
   `self._argv(scope, *tail)` returns
   `("openstack", "--os-cloud", scope.subscription_id, "--os-project-id", scope.tenant_id, "--os-region-name", scope.region, *tail)`.
6. **Helpers:**
   - `async _checked(self, argv: tuple[str, ...]) -> str`: runs `await self._executor.execute(argv)`;
     a non-zero `returncode` raises `OpenStackCliError(argv, result.stderr)`; otherwise returns stdout.
   - `async _json(self, argv: tuple[str, ...]) -> Any`: `stdout = await self._checked(argv)`, then
     `json.loads(stdout) if stdout.strip() else {}`.
7. **Commands** (STACK is `self._stack_name(scope)`; every argv is `self._argv(scope, *tail)`):

   | method | step | argv tail | on non-zero exit |
   |---|---|---|---|
   | discover_environment | 1 | `token issue -c project_id -f json` (via `_json`) | raise `OpenStackCliError` |
   | | 2 | `stack resource list STACK -f json` (via `_json`) | catch `OpenStackCliError`: resources `[]` (a stack that does not exist yet is a valid first-deploy discovery) |
   | execute_plan | 1 | `stack show STACK -c id -f json` (raw `self._executor.execute`) | take the create branch |
   | | 2 | `stack create --template FILE --wait STACK` when step 1 exited non-zero, else `stack update --template FILE --wait STACK` (via `_checked`) | raise |
   | | 3 | `stack show STACK -f json` (via `_json`) | raise |
   | get_resource_status | 1 | `stack show STACK -c id -c stack_status -f json` (via `_json`) | raise |
   | delete_resource | 1 | `stack delete --yes --wait STACK` (raw `self._executor.execute`) | if `"stack not found"` is in `(result.stdout + result.stderr).lower()`, return None; else raise `OpenStackCliError(argv, result.stderr)` |

   Create-or-update makes a replayed job (for example after a lease expiry) an update rather than a
   failed create, and deleting a stack that is already gone succeeds: every job is idempotent under
   replay. Step 3 exists because `create` and `update` with `--wait` print only a short view
   without outputs.
8. **FILE:** `tempfile.NamedTemporaryFile("w", suffix=".json", prefix="vibey-heat-", delete=False)`,
   `json.dump(template, handle)`, `template_path = Path(handle.name)`, then step 2 inside
   `try:` with `template_path.unlink(missing_ok=True)` in the `finally`, exactly as
   `az_cli.py:114-135`. JSON is valid Heat template input. The template file is written after
   step 1 and is gone before step 3 runs.
9. **Results:**
   - Discovery: `project_id = token.get("project_id") if isinstance(token, dict) else None`, and
     `AzureDiscoveryResult(tenant_id=str(project_id or scope.tenant_id), subscription_id=scope.subscription_id, resource_group=scope.resource_group, location=scope.region, existing_resources=tuple(resources) if isinstance(resources, list) else ())`.
   - Execute: `shown` is the step 3 value, or `{}` when it is not a dict;
     `raw = str(shown.get("stack_status", ""))`; `outputs: dict[str, object]` maps
     `str(item["output_key"])` to `item.get("output_value")` for each `item` in
     `shown.get("outputs") or []` that is a dict holding `"output_key"`, then
     `outputs["stack_status"] = raw`. Return
     `AzureExecutionResult(deployment_id=str(shown.get("id", "")), provisioning_state=self.stack_state(raw), outputs=outputs, applied_at=datetime.now(UTC))`.
   - Status: `raw = str(shown.get("stack_status", "")) if isinstance(shown, dict) else ""`,
     `state = self.stack_state(raw)`, return
     `AzureResourceStatus(resource_id=resource_id, provisioning_state=state, health_state="Healthy" if state == "Succeeded" else "Degraded")`
     (as `az_cli.py:153-157`). The handlers pass `spec.spec_id` as `resource_id`
     (`src/vibey/application/deploy_execute_handler.py:88`); the stack is OpenStack's unit, so the
     stack's status answers for it and `resource_id` is echoed back. `delete_resource` likewise
     deletes the stack and does not use `resource_id`.
10. `@staticmethod stack_state(stack_status: str) -> str` returns `"Succeeded"` for
    `CREATE_COMPLETE` or `UPDATE_COMPLETE` (the word `deploy_execute_handler.py:89` checks),
    `"Running"` for any status ending in `_IN_PROGRESS`, `"Failed"` for any status ending in
    `_FAILED` and for `ROLLBACK_COMPLETE`, and `"Unknown"` for anything else.
11. `OpenStackCliError.__init__(self, argv: tuple[str, ...], stderr: str)` sets `self.argv` and
    `self.stderr` and calls `super().__init__(f"{' '.join(argv)} failed: {stderr.strip()[:500]}")`.
    stdout never goes into an error.
12. **Preflight** (new; replaces the CLI's raw `subprocess.run`):
    ```python
    async def preflight(self) -> bool:
        try:
            result = await self._executor.execute(self.PREFLIGHT_ARGV)
        except OSError:
            return False
        return result.returncode == 0
    ```
    An `OSError` (for example `FileNotFoundError` when the `openstack` CLI is not installed) means
    not ready. It uses ambient credentials; a scope-specific auth failure surfaces later as
    `OpenStackCliError` and goes to DEPLOY_REVIEW triage (`deploy_execute_handler.py:136`).
13. `OpenStackCliAdapterInterface` sits beside the class and `OpenStackCliAdapter()` satisfies both
    it and `CloudClientPort`.

## Where to change
Every new file starts with the provenance header: copy line 1 of
`src/vibey/infrastructure/azure/az_cli.py` byte for byte. Line numbers are from the storm
integration branch at `4317cff6`. The lane touches five files, because the adapter's two names must
also be exported from the package and interfaces package that lane `split-331-1-heat-renderer`
created:
- New `src/vibey/infrastructure/openstack/openstack_cli.py`: Required behaviour 1-12. Module
  docstring in the style of `az_cli.py:2-16` (the real OpenStack cloud port over the `openstack`
  CLI; never a default: bootstrap keeps the in-memory adapter unless `vibey worker --cloud cli`
  selects this one for `[deploy].target = "openstack"`; consent is re-verified here at the last
  boundary; the scope mapping of behaviour 5). Copy the import layout of `az_cli.py:18-33`:
  `json`, `re`, `tempfile`, `datetime.UTC`/`datetime`, `pathlib.Path`, `typing.Any`/`ClassVar`,
  the three result types from `vibey.application.interfaces`,
  `MutationNotAuthorizedError`/`ScopeProviderMismatchError` from `vibey.application.azure_port`,
  `AzureTargetScope`/`DeploymentConsent`/`DeploymentSpec` from `vibey.domain.deployment`,
  `VibeyError` from `vibey.domain.errors`, `CleanGitEnvSubprocessExecutor` from
  `vibey.infrastructure.git.clean_env`, `CommandExecutor` from `vibey.infrastructure.interfaces`,
  `DEFAULT_IMAGE`/`HeatTemplateRenderer` from `vibey.infrastructure.openstack.heat`, and
  `HeatTemplateRendererInterface` from `vibey.infrastructure.openstack.interfaces`. Methods:
  `_argv`, `_checked`, `_json`, `_require_provider`, `_require_consent`, `_stack_name`,
  `stack_state`, `preflight`, and the four port methods. No module-level functions.
- New `src/vibey/infrastructure/openstack/interfaces/openstack_cli_interface.py`, copying
  `src/vibey/infrastructure/secrets/interfaces/openbao_interface.py` (docstring
  "Mirrors `vibey/infrastructure/openstack/openstack_cli.py` (ADR-0016). Interfaces declare; they
  never consume."):
  ```python
  from typing import Protocol, runtime_checkable

  from vibey.application.interfaces.azure import CloudClientPort


  @runtime_checkable
  class OpenStackCliAdapterInterface(CloudClientPort, Protocol):
      """The self-hosted OpenStack implementation of the cloud port, over the `openstack` CLI."""

      async def preflight(self) -> bool:
          """Whether `openstack token issue` succeeds through the injected executor."""
          ...
  ```
- `src/vibey/infrastructure/openstack/interfaces/__init__.py` (edit): add
  `from vibey.infrastructure.openstack.interfaces.openstack_cli_interface import OpenStackCliAdapterInterface`
  and `"OpenStackCliAdapterInterface"` to `__all__`, keeping `__all__` sorted.
- `src/vibey/infrastructure/openstack/__init__.py` (edit): after the `heat` import, add
  `from vibey.infrastructure.openstack.openstack_cli import InvalidStackName, OpenStackCliAdapter, OpenStackCliError`,
  and add the three names to `__all__`, keeping it sorted.
- New `tests/infrastructure/openstack/test_openstack_cli.py` (below). No other file changes.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/infrastructure/openstack` passes.
- [ ] `uv run pytest -q -p no:cacheprovider --noconftest -n 0 tests/infrastructure/openstack/test_openstack_cli.py`
      passes with PostgreSQL stopped.
- [ ] `grep -n "subprocess\|shell=True" src/vibey/infrastructure/openstack/openstack_cli.py` prints
      nothing: every command goes through the executor.
- [ ] `grep -nE "monkeypatch|mock|patch\(" tests/infrastructure/openstack/test_openstack_cli.py` prints nothing.
- [ ] `uv run lint-imports` is clean and `uv run pytest -q -p no:cacheprovider tests/application/test_interfaces_convention.py tests/meta/test_import_contracts_bind.py` passes.
- [ ] `git diff --stat` names only the five files in "Where to change".
- [ ] `uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100` passes after
      the whole-suite coverage run.

## Tests to write first (TDD)
New `tests/infrastructure/openstack/test_openstack_cli.py` (no database, no network, no marker, no
patching). Every test builds `OpenStackCliAdapter(executor=_ScriptedExecutor(...))`: the
constructor's `executor=` seam. This module defines its own scripted double instead of importing
`ScriptedCommandExecutor` from `tests/fakes/process.py` (lane `fakes-process-executor`): that
shared fake answers by argv prefix and cannot read the template file at the moment the CLI would,
before the adapter deletes it, which the create and update tests must check. Module setup:
```python
AUTH = ("--os-cloud", "cloud-1", "--os-project-id", "proj-1", "--os-region-name", "RegionOne")
PREFLIGHT = ("openstack", "token", "issue", "-f", "value", "-c", "project_id")
NOW = datetime(2026, 9, 22, tzinfo=UTC)


class _ScriptedExecutor:
    """Answers each argv with the next scripted (returncode, stdout, stderr), or raises it.

    Records every argv in `calls`. When an argv carries `--template FILE`, it reads that file at
    that moment (the adapter deletes it afterwards) into `templates` as (path, parsed JSON).
    """

    def __init__(self, *responses: tuple[int, str, str] | BaseException) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, ...]] = []
        self.templates: list[tuple[Path, dict[str, Any]]] = []

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        self.calls.append(argv)
        if "--template" in argv:
            path = Path(argv[argv.index("--template") + 1])
            self.templates.append((path, json.loads(path.read_text())))
        if not self._responses:
            raise AssertionError(f"unscripted command: {argv}")
        response = self._responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        returncode, stdout, stderr = response
        return CommandResult(returncode, stdout, stderr)
```
`CommandResult` is `vibey.infrastructure.engines.claudeloop_process.CommandResult`
(`claudeloop_process.py:27-31`). `_spec(*, provider="openstack", resource_group="rg-vibey-dev", iac_provider="heat")`
builds a `DeploymentSpec` like `_spec()` in `tests/infrastructure/azure/test_az_cli.py:32-71`, with
`spec_id="spec-os-1"`, scope `AzureTargetScope(tenant_id="proj-1", subscription_id="cloud-1", resource_group=resource_group, environment="dev", region="RegionOne", provider=provider, tags={"owner": "vibey"})`
and `TopologyConfig("container_app", iac_provider, "m1.small", instances=2)`.
`_consent(spec, *, authorized=True)` builds `DeploymentConsent(consent_id="consent-1", target_scope_digest=spec.scope_digest(), granted_by="operator", granted_at=NOW, explicit_mutation_authorized=authorized)`.
`SHOW = ("openstack", *AUTH, "stack", "show", "rg-vibey-dev")`.

- `test_discovery_reads_the_token_project_and_stack_resources`: responses
  `(0, '{"project_id": "p-real"}', "")`, `(0, '[{"resource_name": "app_0"}]', "")`. Asserts
  `calls == [("openstack", *AUTH, "token", "issue", "-c", "project_id", "-f", "json"), ("openstack", *AUTH, "stack", "resource", "list", "rg-vibey-dev", "-f", "json")]`,
  `tenant_id == "p-real"`, `subscription_id == "cloud-1"`, `resource_group == "rg-vibey-dev"`,
  `location == "RegionOne"`, `existing_resources == ({"resource_name": "app_0"},)`.
- `test_discovery_treats_a_missing_stack_as_empty`: `(0, '{"project_id": "p-real"}', "")`,
  `(1, "", "Stack not found")` → `existing_resources == ()`.
- `test_discovery_falls_back_to_the_scope_tenant`: `(0, "[]", "")`, `(0, "{}", "")` →
  `tenant_id == "proj-1"` and `existing_resources == ()`.
- `test_execute_plan_creates_a_missing_stack_and_reports_outputs`: responses `(1, "", "Stack not found")`,
  `(0, "", "")`, `(0, json.dumps({"id": "stack-1", "stack_status": "CREATE_COMPLETE", "outputs": [{"output_key": "endpoint", "output_value": {"private": ["10.0.0.5"]}}]}), "")`.
  Asserts `calls[0] == (*SHOW, "-c", "id", "-f", "json")`; `calls[1][7:10] == ("stack", "create", "--template")`
  and `calls[1][11:] == ("--wait", "rg-vibey-dev")`; `calls[2] == (*SHOW, "-f", "json")`;
  `result.deployment_id == "stack-1"`; `result.provisioning_state == "Succeeded"`;
  `result.outputs == {"endpoint": {"private": ["10.0.0.5"]}, "stack_status": "CREATE_COMPLETE"}`;
  `executor.templates[0][1]["heat_template_version"] == "2018-08-31"`;
  `executor.templates[0][0].name.startswith("vibey-heat-")`; `not executor.templates[0][0].exists()`.
- `test_execute_plan_updates_an_existing_stack`: `(0, '{"id": "stack-1"}', "")`, `(0, "", "")`,
  `(0, json.dumps({"id": "stack-1", "stack_status": "UPDATE_COMPLETE"}), "")` →
  `calls[1][7:9] == ("stack", "update")`, state `"Succeeded"`,
  `outputs == {"stack_status": "UPDATE_COMPLETE"}`.
- `test_execute_plan_surfaces_a_failed_create`: `(1, "", "Stack not found")`,
  `(1, "", "Stack rg-vibey-dev CREATE_FAILED: quota exceeded")` → raises `OpenStackCliError` whose
  message contains `CREATE_FAILED`; `len(executor.calls) == 2`; the recorded template path no
  longer exists.
- `test_execute_plan_tolerates_malformed_show_output`, parametrized over
  `("[]", "", {"stack_status": ""}, "Unknown")` and
  `(json.dumps({"id": "stack-1", "stack_status": "CREATE_COMPLETE", "outputs": ["junk", {"no_key": 1}]}), "stack-1", {"stack_status": "CREATE_COMPLETE"}, "Succeeded")`
  as `(show_stdout, deployment_id, outputs, state)`: responses `(0, '{"id": "stack-1"}', "")`,
  `(0, "", "")`, `(0, show_stdout, "")`; the result's `deployment_id`, `outputs` and
  `provisioning_state` equal the expected values.
- `test_mutations_are_refused_without_digest_bound_consent`: a stale consent
  (`target_scope_digest="a-different-digest"`, authorized) and an unauthorized one
  (`_consent(spec, authorized=False)`) each make `execute_plan` raise `MutationNotAuthorizedError`;
  the stale one makes `delete_resource(spec.target_scope, "spec-os-1", stale)` raise it too;
  `executor.calls == []`.
- `test_every_method_refuses_a_scope_for_another_provider`: `spec = _spec(provider="azure")`; all
  four methods (with `_consent(spec)` for the mutations) raise `ScopeProviderMismatchError` whose
  message is `"the openstack adapter deploys provider 'openstack' only; this scope is 'azure'"`;
  `executor.calls == []`.
- `test_invalid_stack_name_is_refused_before_any_command`: `spec = _spec(resource_group="9 bad")`;
  all four methods (with `_consent(spec)`) raise `InvalidStackName` matching `is not a Heat stack name`;
  `executor.calls == []`.
- `test_unsupported_topology_is_refused_before_any_command`: `spec = _spec(iac_provider="bicep")`
  with `_consent(spec)` → `execute_plan` raises `UnsupportedHeatTopology`; `executor.calls == []`.
- `test_status_maps_heat_states`, parametrized over `(stdout, state, health)`:
  `(json.dumps({"id": "s", "stack_status": "CREATE_COMPLETE"}), "Succeeded", "Healthy")`,
  `(... "UPDATE_COMPLETE" ..., "Succeeded", "Healthy")`, `(... "CREATE_IN_PROGRESS" ..., "Running", "Degraded")`,
  `(... "UPDATE_FAILED" ..., "Failed", "Degraded")`, `(... "ROLLBACK_COMPLETE" ..., "Failed", "Degraded")`,
  `(... "DELETE_COMPLETE" ..., "Unknown", "Degraded")`, `("{}", "Unknown", "Degraded")`,
  `("", "Unknown", "Degraded")` and `("[]", "Unknown", "Degraded")`. One response `(0, stdout, "")`;
  asserts `calls == [(*SHOW, "-c", "id", "-c", "stack_status", "-f", "json")]`,
  `status.resource_id == "spec-os-1"`, and the state and health.
- `test_consented_delete_runs_stack_delete`: `(0, "", "")` → returns None and
  `calls[0][7:] == ("stack", "delete", "--yes", "--wait", "rg-vibey-dev")`.
- `test_delete_of_an_already_deleted_stack_is_idempotent`:
  `(1, "Stack not found: rg-vibey-dev\n", "Unable to delete 1 of the 1 stacks.")` → returns None.
- `test_delete_failure_raises`: `(1, "", "Forbidden: policy does not allow stack delete")` →
  `OpenStackCliError` whose message contains `Forbidden`.
- `test_openstack_failures_surface_argv_and_stderr`: discovery with
  `(1, "secret-stdout", "The request you have made requires authentication. (HTTP 401)")` raises
  `OpenStackCliError`; `str(exc) == " ".join(("openstack", *AUTH, "token", "issue", "-c", "project_id", "-f", "json")) + " failed: The request you have made requires authentication. (HTTP 401)"`;
  `"secret-stdout" not in str(exc)`; `exc.argv` and `exc.stderr` are the argv and the stderr. Also
  `str(OpenStackCliError(("openstack", "x"), "e" * 600)) == "openstack x failed: " + "e" * 500`.
- `test_preflight_reports_a_missing_cli_as_not_ready`, parametrized over
  `((0, "proj-1\n", ""), True)`, `((1, "", "Missing value auth-url required for auth plugin password"), False)`
  and `(FileNotFoundError(2, "No such file or directory", "openstack"), False)`: one response;
  `await adapter.preflight()` equals the expected bool and `executor.calls == [PREFLIGHT]`.
- `test_the_template_comes_from_the_renderer`: two cases in one test. With
  `renderer=HeatTemplateRenderer(image="registry.local/app:1")`, and separately with
  `image="registry.local/app:2"` and no renderer, run the create flow
  (`(1, "", "Stack not found")`, `(0, "", "")`, `(0, "{}", "")`) and assert
  `executor.templates[0][1]["parameters"]["image"]["default"]` is that image.
- `test_adapter_satisfies_the_cloud_port`: `OpenStackCliAdapter()` is an instance of both
  `OpenStackCliAdapterInterface` and `CloudClientPort`; `OpenStackCliAdapter.PROVIDER == "openstack"`,
  `OpenStackCliAdapter.PREFLIGHT_ARGV == PREFLIGHT`, and `"openstack token issue"` is in
  `OpenStackCliAdapter.LOGIN_HINT`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/openstack tests/application/test_interfaces_convention.py tests/meta/test_import_contracts_bind.py
uv run pytest -q -p no:cacheprovider --noconftest -n 0 tests/infrastructure/openstack/test_openstack_cli.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
```
One coverage run at a time. Until lane `fakes-harness-decouple` lands, `tests/conftest.py:146-156`
connects to PostgreSQL at session start, so every run except the `--noconftest` one needs
PostgreSQL 17 reachable. If `ruff check` reports only import order (`I001`), run
`uv run ruff check --select I --fix` on the files you changed, then `uv run ruff format` on them.

## Out of scope
- `vibey worker --cloud` and the selection of this adapter (lane `split-331-4-worker-cloud-flag`);
  the az adapter's preflight (lane `split-331-3-az-preflight`); installing the CLI (lane
  `split-331-5-openstack-installer`).
- Any live OpenStack run: `tests/live/**` is protected, and these tests fake only the executor.
- TLS termination through Octavia/Barbican, mapping SKU to Zun cpu/memory, choosing a network.
- `deploy_execute_handler`'s `resource_id` contract (it passes `spec.spec_id`, which
  `az resource show --ids` cannot resolve on a real Azure run): a pre-existing bug; leave it.
- The in-memory adapter (`src/vibey/infrastructure/azure/adapter.py`), `bootstrap.py`, `cli/`.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md, README.md or the skill
  trees. Do not push, open PRs, or change git remotes. Commit locally as
  ``feat(openstack): OpenStackCliAdapter drives Heat stacks through the `openstack` CLI``; the hooks
  add the `Made-With:` trailer.

## Standing constraints
- Exception classes carry no behaviour beyond their message and get no interface, as
  `src/vibey/infrastructure/cache/redis.py:20` and `az_cli.py:36-44`.
- Never shell out with `shell=True`; every argv is a tuple built by `_argv`, as in `az_cli.py`.
- Tests substitute only at the constructor seam: never `monkeypatch.setattr`, `mock.patch`,
  `MagicMock` or `AsyncMock` (9.b).
- Edit the two `__init__.py` files with `edit_file`; never rewrite an existing file
  (EDITING-RULES.md).
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.

**Depends on:** split-331-1-heat-renderer, split-330-4-az-scope-guard
- split-331-1-heat-renderer: `HeatTemplateRenderer`, `DEFAULT_IMAGE`, `UnsupportedHeatTopology`,
  `HeatTemplateRendererInterface`, and the `openstack` package and interfaces package this lane
  extends.
- split-330-4-az-scope-guard: `ScopeProviderMismatchError` in `vibey.application.azure_port`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
