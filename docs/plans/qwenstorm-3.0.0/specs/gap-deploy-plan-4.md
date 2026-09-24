## Title
feat(azure): the az client previews a plan with ARM what-if, normalized by the existing IacValidator

## Why
Azure is a declared-only cloud (sub-doctrine 8.b, `src/vibey_tools/gh/docs/doctrines.md:136-137` at
`d3b4a388`), and a declared cloud must be plannable like the default (gap C5,
`issue-audit/gaps.md:232-241`). ADR-0013 names the Azure mechanism outright: "Run static IaC
checks, ARM preflight validation, and `what-if` before mutation"
(`docs/architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md:64-66`). The family
already normalizes what-if output: `IacValidator.normalize_arm_what_if`
(`src/vibey/infrastructure/azure/iac.py:43-80`) maps each `changes[]` entry's `changeType` and
`resourceId` to a `NormalizedResourceChange`. Nothing calls it (10.e, `doctrines.md:417`: use the
family's, do not write a second). This lane implements lane `gap-deploy-plan-1`'s
`CloudPlanPreviewPort.preview_plan` on `AzCliClientAdapter` (`src/vibey/infrastructure/azure/az_cli.py:47-165`).

`az deployment group what-if` fails on a resource group that does not exist yet, and a preview
must not create one (`execute_plan` does, `az_cli.py:103-112`). So the preview first asks
`az group exists`; for a first deploy every rendered resource is a create, normalized by the same
`IacValidator` so both paths report types identically.

## Required behaviour
1. `AzCliClientAdapter` gains
   `async def preview_plan(self, spec: DeploymentSpec) -> tuple[NormalizedResourceChange, ...]`:
   1. `self._require_provider(spec.target_scope)` (added by #330 child 4, filed under
      `openstack-client-p1`), before anything else.
   2. `template = render_template(spec, image=self._image)` (`UnsupportedTopology` before any subprocess).
   3. `exists = await self._az_json("group", "exists", "--name", scope.resource_group, "--subscription", scope.subscription_id)`
      (argv `("az", "group", "exists", "--name", RG, "--subscription", SUB, "-o", "json")`, stdout `true`/`false`).
   4. When `exists is not True`: return
      `tuple(IacValidator().normalize_arm_what_if({"changes": [{"resourceId": f"/subscriptions/{SUB}/resourceGroups/{RG}/providers/{r['type']}/{r['name']}", "changeType": "Create"} for r in template["resources"]]}))`.
   5. Otherwise write the template to a temporary file exactly as `execute_plan` does
      (`az_cli.py:114-119`, prefix `vibey-arm-`), and in a `try`/`finally` that unlinks it
      (`:134-135`) run
      `self._az_json("deployment", "group", "what-if", "--resource-group", RG, "--subscription", SUB, "--name", f"vibey-{spec.spec_id[:40]}", "--template-file", str(template_path), "--no-pretty-print")`;
      return `tuple(IacValidator().normalize_arm_what_if(result if isinstance(result, dict) else {}))`.
   6. A non-zero exit anywhere raises `AzCliError` as every verb does. No consent is read or needed;
      no `create`, `delete` or `deployment group create` argv is ever issued.
2. `AzCliClientAdapter()` satisfies `CloudPlanPreviewPort` (structurally; `isinstance` is true).

## Where to change
- `src/vibey/infrastructure/azure/az_cli.py`: add the method after `delete_resource` (line 159);
  import `IacValidator` from `vibey.infrastructure.azure.iac`, and `NormalizedResourceChange`
  from `vibey.domain.deployment` (line 29).
- Append to `tests/infrastructure/azure/test_az_cli.py` (never rewrite it).

Precondition: `grep -n "_require_provider" src/vibey/infrastructure/azure/az_cli.py` finds the
method. If it does not, #330 child 4 has not landed: stop and report; do not add your own check.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/infrastructure/azure` passes with no `az` binary and no network.
- [ ] `tests/infrastructure/azure/test_iac_validator.py` passes unedited.
- [ ] `src/vibey/infrastructure/*` keeps 100% branch coverage.

## Tests to write first (TDD)
Append to `tests/infrastructure/azure/test_az_cli.py`, building the spec with its `_spec()` helper
(provider `"azure"`) and scripting the executor the way its existing tests do
(`ScriptedCommandExecutor`, lane `fakes-process-executor`):
- `test_preview_of_a_missing_group_creates_every_rendered_resource` — `group exists` answers
  `(0, "false", "")`; the result is two `CREATE` changes whose `resource_id`s end in
  `/Microsoft.App/managedEnvironments/<env>` and `/Microsoft.App/containerApps/<app>`, and the
  only recorded argv is the `group exists` one.
- `test_preview_runs_what_if_on_an_existing_group` — `group exists` → `true`; what-if answers
  stdout `{"status": "Succeeded", "changes": [{"resourceId": "/subscriptions/s/resourceGroups/rg/providers/Microsoft.App/containerApps/a", "changeType": "Modify"}, {"resourceId": "/subscriptions/s/resourceGroups/rg/providers/Microsoft.App/managedEnvironments/e", "changeType": "NoChange"}]}`
  → `(MODIFY, NO_CHANGE)`; the what-if argv carries `--no-pretty-print` and `--template-file`, and
  the template file no longer exists afterwards.
- `test_preview_reports_a_what_if_delete` — a `"Delete"` change comes back as `ChangeAction.DELETE`.
- `test_preview_tolerates_a_non_object_what_if` — stdout `[]` → an empty tuple.
- `test_preview_surfaces_az_failures` — what-if exits 1 with stderr `AuthorizationFailed` →
  `AzCliError` containing it, and the template file is still deleted.
- `test_preview_refuses_before_any_command` — provider `"openstack"` → `ScopeProviderMismatchError`;
  `service_type="kubernetes_fleet"` → `UnsupportedTopology`; both with no recorded call.
- `test_preview_never_mutates` — no recorded argv contains `create` or `delete`.
- `test_the_az_client_speaks_the_preview_protocol` — `isinstance(AzCliClientAdapter(), CloudPlanPreviewPort)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/azure tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

One coverage run at a time.

## Out of scope
- `AzureCliAdapter` in `adapter.py` (a simulated client; it stays unable to preview).
- Changing `IacValidator` (reuse it as it is), Bicep, pricing.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(azure): the az client previews a deployment plan with ARM what-if`. Do not push.

## Lane card
- **Depends on:** `gap-deploy-plan-1`, `openstack-client-p1`, `fakes-process-executor`.
- **Files touched:** `src/vibey/infrastructure/azure/az_cli.py`, `tests/infrastructure/azure/test_az_cli.py`.
- **Must keep passing unchanged:** every existing test in `tests/infrastructure/azure/`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
