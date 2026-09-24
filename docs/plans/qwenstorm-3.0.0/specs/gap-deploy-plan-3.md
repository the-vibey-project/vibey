## Title
feat(openstack): the OpenStack client previews a plan by comparing the rendered Heat template with the stack's resources

## Why
OpenStack is the cloud default (sub-doctrine 8.b, `src/vibey_tools/gh/docs/doctrines.md:136-137`
at `d3b4a388`), so the default deploy must be plannable (gap C5, `issue-audit/gaps.md:232-241`;
ADR-0013's "what-if before mutation",
`docs/architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md:64-66`). Lane
`gap-deploy-plan-1` added the read-only verb `CloudPlanPreviewPort.preview_plan`; this lane
implements it on the real OpenStack client, `OpenStackCliAdapter`
(`src/vibey/infrastructure/openstack/openstack_cli.py`, lane `openstack-client-p2`, #331 child 2),
without mutating anything and without consent.

The preview needs no Heat dry-run parser. Both halves are already known exactly:
- what vibey would deploy: the logical resource names of `HeatTemplateRenderer.render(spec)`
  (#331 child 1: `ingress`, `app_0`…`app_{n-1}`);
- what exists: `openstack stack resource list STACK -f json`, the argv #331's discovery already
  runs, whose rows carry `resource_name` and `resource_type` (python-heatclient
  `heatclient/osc/v1/resource.py`, `ResourceList.take_action`: columns `resource_name`,
  `physical_resource_id`, `resource_type`, `resource_status`, `updated_time`; a missing stack is
  `CommandError('Stack not found: %s')`).
A resource in both is reported `MODIFY` ("present in both; Heat decides whether it changes"): the
preview never claims a `NO_CHANGE` it cannot prove (10.f, `doctrines.md:419`).

## Required behaviour
1. `OpenStackCliAdapter` gains
   `async def preview_plan(self, spec: DeploymentSpec) -> tuple[NormalizedResourceChange, ...]`,
   with the adapter's refusal order and no subprocess before it: the provider check
   (`ScopeProviderMismatchError` for `spec.target_scope.provider != "openstack"`), the stack-name
   check (`InvalidStackName`), then `self`'s renderer's `render(spec)` (`UnsupportedHeatTopology`).
   No consent is read or required.
2. It runs exactly one command through the injected executor:
   `("openstack", "--os-cloud", scope.subscription_id, "--os-project-id", scope.tenant_id, "--os-region-name", scope.region, "stack", "resource", "list", STACK, "-f", "json")`
   (the same argv as discovery's second step), calling the executor directly so both streams are
   visible:
   - exit 0 → the parsed JSON; a value that is not a list counts as no resources;
   - non-zero with `"stack not found"` in `(stdout + stderr).lower()` → no resources (a first deploy);
   - any other non-zero → `OpenStackCliError(argv, stderr)`, as every other verb.
3. `existing` maps `str(row["resource_name"])` to `str(row.get("resource_type", ""))` for each row
   that is a dict with a `resource_name`; other rows are ignored.
4. `desired` is `template["resources"]` (name → resource dict with `"type"`).
5. The result, in this order:
   - for each name in `sorted(desired)`: `NormalizedResourceChange(resource_id=f"{STACK}/{name}", resource_type=desired[name]["type"], action=ChangeAction.MODIFY if name in existing else ChangeAction.CREATE, details={"stack": STACK, "resource_name": name})`;
   - then for each name in `sorted(set(existing) - set(desired))`: the same with
     `resource_type=existing[name]`, `action=ChangeAction.DELETE`.
   `estimated_monthly_cost_usd` stays at its default `0.0` (lane `gap-deploy-plan-2` records that
   cost was not estimated).
6. `OpenStackCliAdapterInterface` (`src/vibey/infrastructure/openstack/interfaces/openstack_cli_interface.py`)
   also inherits `CloudPlanPreviewPort`: `class OpenStackCliAdapterInterface(CloudClientPort, CloudPlanPreviewPort, Protocol)`.
7. Nothing else in the adapter changes.

## Where to change
- `src/vibey/infrastructure/openstack/openstack_cli.py`: add the method after `delete_resource`.
  Use the adapter's own helpers as #331 child 2 built them — the argv builder (`_argv`), the provider
  check (`_require_provider`), the stack-name check (`_stack_name`), the renderer it holds, and the
  executor it holds — reading the file first; the test pins the argv and the refusals, so any
  helper that does that job is the one to call. Import `ChangeAction` and `NormalizedResourceChange`
  from `vibey.domain.deployment`.
- `src/vibey/infrastructure/openstack/interfaces/openstack_cli_interface.py` (behaviour 6); import
  `CloudPlanPreviewPort` from `vibey.application.interfaces`.
- Append to `tests/infrastructure/openstack/test_openstack_cli.py` (never rewrite it).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/infrastructure/openstack` passes with no `openstack` binary and no network.
- [ ] `isinstance(OpenStackCliAdapter(), CloudPlanPreviewPort)` is true.
- [ ] `src/vibey/infrastructure/*` keeps 100% branch coverage.

## Tests to write first (TDD)
Append to `tests/infrastructure/openstack/test_openstack_cli.py`, reusing its scope, `AUTH` tuple,
spec helper (`instances=2`, ingress and TLS on) and scripted executor exactly as its existing tests
do (`ScriptedCommandExecutor` from `tests/fakes/process.py`, or the module's own scripted executor
if that is what they use; either records `calls`):
- `test_preview_of_a_first_deploy_creates_every_template_resource` — the list command answers
  `(1, "", "Stack not found: rg-vibey-dev")`; the result is `CREATE` for `app_0`, `app_1`, `ingress`
  in that order, with `resource_id`s `rg-vibey-dev/app_0` …, and `executor.calls == [("openstack", *AUTH, "stack", "resource", "list", "rg-vibey-dev", "-f", "json")]`.
- `test_preview_modifies_what_exists_and_deletes_what_the_template_dropped` — stdout
  `[{"resource_name": "app_0", "resource_type": "OS::Zun::Container"}, {"resource_name": "old_lb", "resource_type": "OS::Octavia::LoadBalancer"}]`
  → `app_0` MODIFY, `app_1` CREATE, `ingress` CREATE, then `old_lb` DELETE with type
  `OS::Octavia::LoadBalancer`.
- `test_preview_ignores_malformed_rows` — stdout `[{"no_name": 1}, "junk"]` and stdout `{}` both
  give only CREATEs.
- `test_preview_surfaces_other_failures` — `(1, "", "Forbidden")` raises `OpenStackCliError`
  whose message contains `Forbidden`.
- `test_preview_refuses_before_any_command` — provider `"azure"` → `ScopeProviderMismatchError`;
  `resource_group="9 bad"` → `InvalidStackName`; iac `"bicep"` → `UnsupportedHeatTopology`; each
  with `executor.calls == []`.
- `test_preview_needs_no_consent_and_never_mutates` — every recorded argv's tail is
  `stack resource list …`: no `create`, `update` or `delete`.
- `test_the_adapter_speaks_the_preview_protocol` — `isinstance` against `CloudPlanPreviewPort` and
  `OpenStackCliAdapterInterface`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/openstack tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

One coverage run at a time.

## Out of scope
- Heat's own `stack create|update --dry-run` output (not needed; not parsed).
- The Azure and AWS previews (`gap-deploy-plan-4`, `gap-aws-cli-client`); evaluation and recording
  (`gap-deploy-plan-2`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(openstack): the OpenStack client previews a deployment plan`. Do not push.

## Lane card
- **Depends on:** `gap-deploy-plan-1`, `openstack-client-p2`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** every existing test in `tests/infrastructure/openstack/`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
