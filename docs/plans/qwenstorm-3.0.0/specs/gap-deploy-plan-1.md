## Title
feat(deploy): the cloud protocol gains a read-only preview verb, CloudPlanPreviewPort, with the in-memory client and its fake implementing it

## Why
`vibey deploy plan` is a placeholder (`src/vibey/cli/main.py:1059-1088`: "NOT YET IMPLEMENTED …
Status: NOT EVALUATED"), gap C5 (`issue-audit/gaps.md:232-241`). ADR-0013's safety model
(`docs/architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md:64-66`) requires a
`what-if` before any mutation, and makes "unexpected deletes … or cost-bound violations require
user input". The domain can already judge a change set (`evaluate_iac_plan`,
`src/vibey/domain/deployment.py:229-255`, over `NormalizedResourceChange`, `:210-217`), but
`CloudClientPort` (`src/vibey/application/interfaces/azure.py:44-68`) has no verb that produces
one, so nothing can be evaluated. Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:168-172`
at `d3b4a388`) says every cloud speaks one vibey-owned protocol: the preview is that protocol's
fifth verb.

It is a **separate Protocol beside `CloudClientPort`**, not a new method on it: adding a method to
`CloudClientPort` would break every implementation at once (`InMemoryAzureClientAdapter`,
`AzureCliAdapter`, `AzCliClientAdapter`, the coming `OpenStackCliAdapter`, the shared
`FaultyCloudClient`). Each client opts in, in its own lane (`gap-deploy-plan-3` OpenStack,
`gap-deploy-plan-4` Azure, `gap-aws-cli-client` AWS), and a client without it is reported as
"cannot preview" rather than guessed at (10.f, `doctrines.md:419`). This lane adds the Protocol,
the production in-memory implementation, and the shared fake (9.b, `doctrines.md:349`: the fake
exists from the first day).

## Required behaviour
1. `src/vibey/application/interfaces/azure.py` declares, directly after the line
   `AzureClientPort = CloudClientPort` (line 71):
   ```python
   @runtime_checkable
   class CloudPlanPreviewPort(Protocol):
       """The cloud protocol's read-only preview verb (ADR-0013: what-if before mutation).

       A client that can say what `execute_plan` would change implements this beside
       `CloudClientPort`. It never mutates and needs no consent. A client without it is
       reported as unable to preview, never guessed at (sub-doctrine 10.f)."""

       async def preview_plan(self, spec: DeploymentSpec) -> Sequence[NormalizedResourceChange]:
           """The normalized changes `execute_plan` would make for this spec; nothing is applied."""
           ...
   ```
   and adds `NormalizedResourceChange` to its `from vibey.domain.deployment import (...)` block
   (lines 12-16). `Sequence` is already imported (line 6).
2. `CloudPlanPreviewPort` is exported from `src/vibey/application/interfaces/__init__.py`: add it
   to the `from vibey.application.interfaces.azure import (...)` block (lines 14-22, after
   `CloudClientPort,`) and to `__all__` directly after `"CloudClientPort",` (line 171).
3. `InMemoryAzureClientAdapter` (`src/vibey/infrastructure/azure/adapter.py:16-77`) gains, after
   `delete_resource` (line 65):
   ```python
       async def preview_plan(self, spec: DeploymentSpec) -> tuple[NormalizedResourceChange, ...]:
           """Read-only: what execute_plan would change. Never mutates; needs no consent."""
           action = ChangeAction.MODIFY if spec.spec_id in self.resources else ChangeAction.CREATE
           return (
               NormalizedResourceChange(
                   resource_id=spec.spec_id, resource_type="vibey/deployment", action=action
               ),
           )
   ```
   importing `ChangeAction` and `NormalizedResourceChange` from `vibey.domain.deployment` (line 13).
   It never touches `self.resources` or `self.deployments`.
   In the same class, `discover_environment` (lines 23-31) stops claiming an empty cloud: its
   `existing_resources=()` becomes
   `existing_resources=tuple({"resource_id": key, **value} for key, value in sorted(self.resources.items()))`,
   so the in-memory cloud reports what it holds (10.f) and the plan and cancel lanes can reason over
   it. A fresh adapter still reports `()`.
4. The shared fake `FaultyCloudClient` (`tests/fakes/deploy.py`, lane `fakes-deploy`) gains
   `async def preview_plan(self, spec)`, written like its `execute_plan`: append `DeployStep.PLAN`
   (`src/vibey/application/deploy_execute_handler.py:29`) to `steps_run`; when `fail_at` is
   `DeployStep.PLAN` raise the scripted failure; otherwise delegate to the wrapped client when it
   is a `CloudPlanPreviewPort` (`isinstance`), and raise
   `TypeError(f"{type(inner).__name__} cannot preview a plan")` when it is not.
5. `tests/fakes/registry.py` registers
   `FakeRegistration(port=CloudPlanPreviewPort, build=FaultyCloudClient, note="delegates to InMemoryAzureClientAdapter.preview_plan")`
   in `REGISTRY`, so `tests/fakes/test_port_parity.py` accounts for the new Protocol.
6. `InMemoryAzureClientAdapter()` satisfies both `CloudClientPort` and `CloudPlanPreviewPort`;
   `AzureCliAdapter` and `AzCliClientAdapter` are untouched and satisfy only `CloudClientPort`.

## Where to change
- `src/vibey/application/interfaces/azure.py`, `src/vibey/application/interfaces/__init__.py`
  (276 lines — `edit_file` only), `src/vibey/infrastructure/azure/adapter.py`.
- `tests/fakes/deploy.py`, `tests/fakes/registry.py` (the lines above only).
- New `tests/infrastructure/azure/test_in_memory_preview.py`; append to `tests/fakes/test_fake_deploy.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/infrastructure/azure tests/fakes tests/application/test_interfaces_convention.py` passes.
- [ ] `tests/fakes/test_port_parity.py` passes with `CloudPlanPreviewPort` in `REGISTRY`.
- [ ] `tests/system/test_delivery_stage_set.py` passes unedited.
- [ ] `application/` and `infrastructure/` keep 100% branch coverage.

## Tests to write first (TDD)
New `tests/infrastructure/azure/test_in_memory_preview.py` (build the spec as
`tests/infrastructure/azure/test_azure_adapter.py` does):
- `test_a_first_deploy_previews_one_create` — a fresh adapter previews
  `(NormalizedResourceChange(spec.spec_id, "vibey/deployment", ChangeAction.CREATE),)`.
- `test_a_redeploy_previews_a_modify` — after a consented `execute_plan`, the preview's single
  change has `ChangeAction.MODIFY`.
- `test_preview_never_mutates` — preview twice on a fresh adapter; `adapter.resources == {}` and
  `adapter.deployments == []`.
- `test_preview_needs_no_consent` — no consent object exists in the test; the call succeeds.
- `test_discovery_reports_what_the_in_memory_cloud_holds` — fresh: `existing_resources == ()`;
  after a consented `execute_plan`: `({"resource_id": spec.spec_id, "provisioning_state": "Succeeded", "health_state": "Healthy"},)`;
  after a consented `delete_resource`: `()` again.
- `test_the_in_memory_client_speaks_both_protocols` — `isinstance(InMemoryAzureClientAdapter(), CloudPlanPreviewPort)`
  and `CloudClientPort`; `isinstance(AzCliClientAdapter(), CloudPlanPreviewPort) is False`.

Append to `tests/fakes/test_fake_deploy.py`:
- `test_cloud_preview_records_the_plan_step_and_delegates` — `steps_run == [DeployStep.PLAN]` and
  the result equals the inner client's preview.
- `test_cloud_preview_fails_at_plan_on_cue` — `fail_at=DeployStep.PLAN` raises the scripted failure.
- `test_cloud_preview_refuses_an_inner_client_that_cannot_preview` — wrapping an
  `AzCliClientAdapter()` (constructing it runs nothing) raises `TypeError` matching `cannot preview a plan`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/azure tests/fakes tests/meta tests/application/test_interfaces_convention.py tests/system/test_delivery_stage_set.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

One coverage run at a time.

## Out of scope
- Evaluating or recording a plan (`gap-deploy-plan-2`), real previews (`gap-deploy-plan-3`,
  `gap-deploy-plan-4`, `gap-aws-cli-client`), DEPLOY_EXECUTE's use of it (`gap-deploy-execute-control`).
- Cost estimation: every preview reports `estimated_monthly_cost_usd=0.0`, and `gap-deploy-plan-2`
  records that cost was not estimated.
- `tests/system/test_delivery_stage_set.py` (protected), CHANGELOG.md, docs/, ADRs, CLAUDE.md,
  AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(deploy): CloudPlanPreviewPort, the cloud protocol's read-only preview verb`. Do not push.

## Lane card
- **Depends on:** `fakes-deploy`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/system/test_delivery_stage_set.py`, `tests/infrastructure/azure/test_az_cli.py`.
- **Standing constraints:** a fake is a plain class with real behaviour, never `unittest.mock`;
  substitute at declared seams only; never raise a `tests/meta/patching_baseline.json` count.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
