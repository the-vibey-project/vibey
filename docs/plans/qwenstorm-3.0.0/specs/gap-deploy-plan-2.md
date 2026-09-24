## Title
feat(deploy): a deploy.plan job evaluates the accepted spec's plan through the cloud protocol and records it in the ledger

## Why
Gap C5 (`issue-audit/gaps.md:232-241`): "Deployment can be planned … through `CloudClientPort`
… Each writes ledger events". `vibey deploy plan` prints "Status: NOT EVALUATED"
(`src/vibey/cli/main.py:1083-1086`). Lane `gap-deploy-plan-1` added the preview verb
(`CloudPlanPreviewPort`); the domain already judges a change set (`evaluate_iac_plan`,
`src/vibey/domain/deployment.py:229-255`). This lane joins them in one evaluator and runs it as a
queued job on the worker, because the worker is where the cloud client lives
(`src/vibey/bootstrap.py:371`: `build_full_worker(azure_client=…)`): the plan is evaluated by the
same client, with the same credentials, that would apply it. The CLI verb that enqueues the job is
`gap-deploy-cli-2`; DEPLOY_EXECUTE's own use of the evaluator is `gap-deploy-execute-control`.

Evidence-bounded (10.f, `src/vibey_tools/gh/docs/doctrines.md:419` at `d3b4a388`): a client that
cannot preview yields "unknown", never "safe"; no pricing source exists, so every record says
`"cost_estimated": false` rather than letting a `0.0` read as "within budget". The ledger records
every evaluation (7.c, `doctrines.md:82-91`). A plan job is read-only, so it never parks: ambiguity
parks where a mutation waits on it (`gap-deploy-execute-control` routes an unsafe plan into
DEPLOY_REVIEW's triage gate).

## Required behaviour
1. New `src/vibey/application/deploy_plan_handler.py` declares:
   - `@dataclass(frozen=True, slots=True) class DeploymentPlanReport` with fields `spec_id: str`,
     `scope_digest: str`, `provider: str`, `existing_resources: int`, `previewed: bool`,
     `evaluation: PlanEvaluation | None`, `reason: str`, and:
     - property `safe_for_apply -> bool`: `self.previewed and self.evaluation is not None and self.evaluation.is_safe_for_automated_apply`;
     - `blocking_class(self) -> DeploymentFailureClass | None`: `None` when `safe_for_apply`;
       else `AMBIGUOUS_CONFIGURATION` when not previewed; else `DESTRUCTIVE_DATA_MIGRATION` when
       `has_destructive_deletions`; else `CAP_EXHAUSTED` (over budget);
     - `summary(self) -> str`: not previewed → `f"plan unknown: {self.reason}"`; previewed →
       `f"plan: {n} change(s) — {c} create, {m} modify, {d} delete, {u} unchanged; cost not estimated"`,
       followed by `f"; blocked: {'; '.join(blocking_reasons)}"` when there are blocking reasons;
     - `to_payload(self) -> dict[str, object]`: `decision` (`"deployment_plan_evaluated"` when
       previewed, else `"deployment_plan_unknown"`), `spec_id`, `scope_digest`, `provider`,
       `existing_resources`, `previewed`, `reason`, `"cost_estimated": False`, and, when previewed,
       `changes` (a list of `{"resource_id", "resource_type", "action": change.action.value}`),
       `has_destructive_deletions`, `exceeds_budget`, `is_safe_for_automated_apply`,
       `blocking_reasons` (a list).
   - `class DeploymentPlanEvaluator` with
     `async def evaluate(self, spec: DeploymentSpec, client: CloudClientPort) -> DeploymentPlanReport`:
     `discovery = await client.discover_environment(spec.target_scope)`; the base fields are
     `spec.spec_id`, `spec.scope_digest()`, `spec.target_scope.provider`,
     `len(discovery.existing_resources)`. When `isinstance(client, CloudPlanPreviewPort)`:
     `changes = await client.preview_plan(spec)` and
     `evaluation = evaluate_iac_plan(changes, spec.cost_boundary)`, `previewed=True`, `reason=""`.
     Otherwise `previewed=False`, `evaluation=None`,
     `reason=f"the {type(client).__name__} cloud client cannot preview a plan"`.
     It holds no state; a client error propagates.
   - `DEPLOYMENT_PLAN_EVALUATOR: Final[DeploymentPlanEvaluatorInterface] = DeploymentPlanEvaluator()`.
   - `class DeployPlanHandler` (a `JobHandler`), `__init__(self, *, ledgers: Mapping[Phase, PhaseLedger], cloud_client: CloudClientPort, spec_provider: Callable[[UUID], DeploymentSpec | None] | None = None, evaluator: DeploymentPlanEvaluatorInterface = DEPLOYMENT_PLAN_EVALUATOR)`;
     `async def handle(self, job: JobRecord) -> Outcome`:
     1. `job.kind != "deploy.plan"` → `Failure(FailureClass.VIBEY, "expected deploy.plan job")`.
     2. `ledger = self._ledgers.get(job.phase)` when `isinstance(job.phase, Phase)`; `None` →
        `Failure(FailureClass.VIBEY, f"deploy.plan has no ledger for phase {job.phase}")`.
     3. No spec → append `DECISION_RECORDED` `{"decision": "deployment_plan_unknown", "reason": "no deployment spec has been synthesized", "previewed": False, "cost_estimated": False}`
        and return `Success({"status": "no_spec"})` (retrying cannot help; the ledger says why).
     4. Otherwise `report = await evaluator.evaluate(spec, cloud_client)`, append
        `DECISION_RECORDED` with `report.to_payload()`, and return
        `Success({"status": "planned" if report.previewed else "unknown", "safe_for_apply": report.safe_for_apply, "summary": report.summary()})`.
     Every append uses `ledger.append_event(project_id=job.project_id, cycle=job.cycle, job_id=job.id, kind=EventKind.DECISION_RECORDED, payload=...)`.
     A replay appends a second evaluation: it is a new observation at a new moment, not a
     correction, and the ledger is append-only.
2. New `src/vibey/application/interfaces/deploy_plan_interface.py` declares, `@runtime_checkable`:
   `DeploymentPlanReportInterface` (the seven fields as read-only properties, `safe_for_apply`,
   `blocking_class`, `summary`, `to_payload`), `DeploymentPlanEvaluatorInterface` (`evaluate`) and
   `DeployPlanHandlerInterface(JobHandler, Protocol)` (`handle`). All three are exported from
   `src/vibey/application/interfaces/__init__.py` (a new import block directly after the
   `from vibey.application.interfaces.config_store import ConfigStorePort` line, keeping the
   imports sorted, and three `__all__` entries after `"CloudPlanPreviewPort",`).
3. `tests/fakes/registry.py`'s `EXEMPT` gains `DeploymentPlanReportInterface: ExemptReason.VALUE_CONTRACT`,
   `DeploymentPlanEvaluatorInterface: ExemptReason.CLASS_CONTRACT` and
   `DeployPlanHandlerInterface: ExemptReason.CLASS_CONTRACT`.
4. `src/vibey/bootstrap.py`'s `build_full_worker`:
   - after `deploy_execute_ledger = PostgresReviewLedger(...)` (line 380) add
     ```python
         # One phase ledger per deployment phase, for the jobs that may run in any of them.
         deploy_ledgers: dict[Phase, PhaseLedger] = {
             Phase.DEPLOY_DESIGN: deploy_design_ledger,
             Phase.DEPLOY_EXECUTE: deploy_execute_ledger,
             Phase.DEPLOY_REVIEW: resources.deploy_review_ledger,
         }
     ```
     importing `PhaseLedger` in the `from vibey.application.interfaces import (...)` block (line 45);
   - after the `"deploy.route": DeployReviewRoutingHandler(...)` entry (lines 604-611) add
     ```python
             "deploy.plan": DeployPlanHandler(
                 ledgers=deploy_ledgers,
                 cloud_client=azure,
                 spec_provider=deploy_state.load_spec,
             ),
     ```
     importing `DeployPlanHandler` from `vibey.application.deploy_plan_handler`.

## Where to change
- New `src/vibey/application/deploy_plan_handler.py`, `src/vibey/application/interfaces/deploy_plan_interface.py`
  (line 1 of each: the provenance header of `src/vibey/application/deploy_execute_handler.py`).
- `src/vibey/application/interfaces/__init__.py`, `src/vibey/bootstrap.py` (`edit_file` only),
  `tests/fakes/registry.py`.
- New `tests/application/test_deploy_plan_handler.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/application/test_deploy_plan_handler.py tests/application/test_interfaces_convention.py tests/fakes` passes with PostgreSQL stopped.
- [ ] `grep -n '"deploy.plan": DeployPlanHandler(' src/vibey/bootstrap.py` prints one line.
- [ ] `tests/system/test_delivery_stage_set.py` passes unedited; `application/` keeps 100% branch coverage.

## Tests to write first (TDD)
`tests/application/test_deploy_plan_handler.py` — shared fakes only: `FaultyCloudClient`
(`tests/fakes/deploy.py`), `InMemoryLedger` and `review_ledger` (`tests/fakes/ledger.py`),
`make_job` (`tests/fakes/queue.py`, jobs built as `dataclasses.replace(make_job(pid), kind="deploy.plan", phase=Phase.DEPLOY_DESIGN)`),
the production `AzureCliAdapter()` (`infrastructure/azure/adapter.py:79`, which cannot preview and
runs no subprocess). The spec: `DeploymentSpec("spec-plan", "1", AzureTargetScope("t", "s", "rg-plan", "dev", "RegionOne"), IdentityAuthority("managed_identity", "p"), TopologyConfig("container_app", "heat", "m1.small"), RecoveryPolicy("canary"), VerificationContract(), CostBoundary(100.0, 10.0))`.
- `test_a_previewable_first_deploy_is_safe_and_recorded` — one `deployment_plan_evaluated` event:
  `previewed is True`, `changes == [{"resource_id": "spec-plan", "resource_type": "vibey/deployment", "action": "create"}]`,
  `is_safe_for_automated_apply is True`, `cost_estimated is False`; outcome `Success` with
  `status == "planned"` and `safe_for_apply is True`; `client.steps_run` contains `DISCOVER` then `PLAN`.
- `test_a_client_that_cannot_preview_is_unknown_not_safe` — `AzureCliAdapter()`: one
  `deployment_plan_unknown` event whose `reason == "the AzureCliAdapter cloud client cannot preview a plan"`; `safe_for_apply is False`.
- `test_a_missing_spec_is_recorded_and_not_retried` — `spec_provider` returns `None` → `Success({"status": "no_spec"})`
  and one `deployment_plan_unknown` event naming the reason.
- `test_the_event_lands_in_the_jobs_phase` — a job in `DEPLOY_REVIEW` appends through the
  `DEPLOY_REVIEW` ledger view (the recorded event's `phase is Phase.DEPLOY_REVIEW`).
- `test_a_phase_with_no_ledger_is_our_bug` — `ledgers` without `DEPLOY_EXECUTE`, a job in it →
  `Failure(FailureClass.VIBEY, ...)`, nothing appended.
- `test_a_wrong_kind_is_refused` — kind `"deploy.execute"` → `Failure(FailureClass.VIBEY, "expected deploy.plan job")`.
- `test_a_discovery_failure_propagates` — `FaultyCloudClient(fail_at=DeployStep.DISCOVER)` → the scripted error is raised, nothing appended.
- `test_report_blocking_class_and_summary` — reports built directly from `evaluate_iac_plan`:
  a DELETE change → `DESTRUCTIVE_DATA_MIGRATION` and the summary contains `1 delete` and `blocked:`;
  a CREATE costing 500.0 against `CostBoundary(100.0, 10.0)` → `CAP_EXHAUSTED`; not previewed →
  `AMBIGUOUS_CONFIGURATION` and `summary() == "plan unknown: <reason>"`; safe → `None`.
- `test_the_classes_satisfy_their_interfaces`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/application tests/fakes tests/meta tests/system/test_delivery_stage_set.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

One coverage run at a time. `bootstrap.py` sits outside the layer floors; its new lines are checked by the grep above.

## Out of scope
- The CLI verb (`gap-deploy-cli-2`), DEPLOY_EXECUTE's plan check (`gap-deploy-execute-control`),
  real previews (`gap-deploy-plan-3`, `gap-deploy-plan-4`), pricing.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(deploy): a deploy.plan job evaluates and records the deployment plan`. Do not push.

## Lane card
- **Depends on:** `gap-deploy-plan-1`, `fakes-deploy-review`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/system/test_delivery_stage_set.py` and every deploy handler test.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
