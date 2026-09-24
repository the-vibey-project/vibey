## Title
feat(deploy): DEPLOY_EXECUTE plans before it applies, stops for a requested cancel, and records the spec it verified

## Why
`DeployExecuteHandler` (`src/vibey/application/deploy_execute_handler.py:38-172`) is where three
gap-C5 behaviours (`issue-audit/gaps.md:232-241`) must meet the running deploy:
1. **Plan.** Its step 2 is a comment — "Plan & 3. Validate (Validated during design phase…)"
   (`:78-79`) — though ADR-0013 requires `what-if` before mutation and makes "unexpected deletes …
   or cost-bound violations require user input"
   (`docs/architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md:64-66`). Lane
   `gap-deploy-plan-2` built the evaluator; here it runs before `execute_plan`. An unsafe or unknown
   plan raises, and the handler's existing failure path (`:136-172`) records a finding and
   enqueues `deploy.triage`, whose handler parks a human gate (`deploy_review_handler.py:144-162`) —
   ambiguity parks a gate, and no worker waits (CLAUDE.md non-negotiable; ADR-0013 `:97-98`).
2. **Cancel.** ADR-0013 `:95`: "Any nonterminal phase may enter `ABANDONED` on explicit user
   cancellation". The job queue claims regardless of project phase
   (`src/vibey/infrastructure/db/job_repository.py:188-196`), so a queued `deploy.execute` would still
   mutate the cloud after a cancel. The handler must look for a `deploy.cancel` job of its cycle
   (lane `gap-deploy-cancel`) before discovery and again right before the apply.
3. **Rollback evidence.** A rollback needs the state vibey last verified (lane
   `gap-deploy-rollback-2`). The verification artifact (`:96-106`) records only `deployment_id` and
   `outputs`; it now also records the spec, through `DeploymentSpecCodec` (lane
   `gap-deploy-rollback-1`). The spec holds secret *references*, never values (7.c,
   `src/vibey_tools/gh/docs/doctrines.md:82-91` at `d3b4a388`).

Everything new is opt-in by constructor, so the protected `tests/system/test_delivery_stage_set.py`
(which builds the handler directly, `:1022-1030`) is unchanged; production turns the plan check on
in `bootstrap.py`.

## Required behaviour
1. `DeployExecuteHandler.__init__` gains keyword-only
   `evaluator: DeploymentPlanEvaluatorInterface | None = None` and
   `codec: DeploymentSpecCodecInterface = DEPLOYMENT_SPEC_CODEC`.
2. New in the module: `class UnsafeDeploymentPlan(Exception)` with
   `__init__(self, message: str, *, failure_class: DeploymentFailureClass)` storing `failure_class`
   (no interface: an exception).
3. New private method `async def _cancel_request(self, job: JobRecord) -> JobRecord | None`:
   `self._jobs.list_for_cycle(job.project_id, cycle=job.cycle, kind="deploy.cancel")`; keep those
   whose `state` is not `JobState.FAILED` or `JobState.CANCELLED`; if none, return `None` without
   reading the ledger; otherwise read `self._ledger.all_for_project(job.project_id)` and drop every
   cancel whose id is the `job_id` of a `DECISION_RECORDED` event with
   `payload["decision"] == "deployment_cancel_withdrawn"`; return the first remaining, or `None`.
4. New private method `_skip_for_cancel(job, cancel) -> Outcome` appends `DECISION_RECORDED`
   `{"decision": "deployment_execute_skipped", "reason": "a deploy.cancel job was requested for this cycle", "cancel_job_id": str(cancel.id)}`
   and returns `Success({"status": "cancelled", "cancel_job_id": str(cancel.id)})`. No cloud call,
   no transition, no enqueue.
5. `handle`: directly after the kind check (`:63-64`), `if (cancel := await self._cancel_request(job)) is not None: return await self._skip_for_cancel(job, cancel)`.
   Inside the `try`, directly before `exec_result = await self._azure.execute_plan(spec, consent)`
   (`:82`), the same two lines again.
6. `handle`, step 1 (`:75-76`): when `self._evaluator is None` keep
   `await self._azure.discover_environment(spec.target_scope)`; otherwise
   `report = await self._evaluator.evaluate(spec, self._azure)` (it discovers), append
   `DECISION_RECORDED` with `report.to_payload()`, and when `report.blocking_class()` is not `None`
   raise `UnsafeDeploymentPlan(report.summary(), failure_class=report.blocking_class())`. Replace the
   comment at `:78-79` with `# 2. Plan & 3. Validate: the evaluator above (ADR-0013 what-if)`.
7. The failure path's finding (`:143-148`) uses
   `e.failure_class.value if isinstance(e, UnsafeDeploymentPlan) else DeploymentFailureClass.POLICY_DENIAL.value`
   as `failure_class`. Everything else on that path is unchanged.
8. The verification artifact payload (`:101-105`) gains `"spec_id": spec.spec_id`,
   `"scope_digest": spec.scope_digest()`, `"spec": self._codec.to_payload(spec)` and
   `"spec_digest": self._codec.digest(spec)`.
9. `DeployExecuteHandlerInterface(JobHandler, Protocol)` (`handle`) is added to
   `src/vibey/application/interfaces/class_contracts.py` after `DeployReviewTriageHandlerInterface`
   (`:286-288`), exported from `application/interfaces/__init__.py` (the `class_contracts` import
   block and `__all__`, beside `"DeployReviewTriageHandlerInterface",` at `:261`), and listed in
   `tests/fakes/registry.py`'s `EXEMPT` as `ExemptReason.CLASS_CONTRACT`.
10. `src/vibey/bootstrap.py`: the `"deploy.execute": DeployExecuteHandler(...)` entry (`:583-591`)
    gains `evaluator=DEPLOYMENT_PLAN_EVALUATOR` (imported from `vibey.application.deploy_plan_handler`).

## Where to change
- `src/vibey/application/deploy_execute_handler.py` (behaviours 1-8). Imports:
  `JobState` from `vibey.domain.job` (beside `FailureClass`, `:22`);
  `DeploymentPlanEvaluatorInterface` from `vibey.application.interfaces`;
  `DEPLOYMENT_SPEC_CODEC` from `vibey.domain.deployment_codec` and
  `DeploymentSpecCodecInterface` from `vibey.domain.interfaces`; `Outcome` is already imported (`:15`).
- `src/vibey/application/interfaces/class_contracts.py`, `src/vibey/application/interfaces/__init__.py`,
  `tests/fakes/registry.py`, `src/vibey/bootstrap.py` (`edit_file` only, the lines named).
- Append to `tests/application/test_deploy_execute_handler.py` (never rewrite it).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/application/test_deploy_execute_handler.py tests/system/test_delivery_stage_set.py tests/fakes` passes; the system test is unedited.
- [ ] `grep -n "evaluator=DEPLOYMENT_PLAN_EVALUATOR" src/vibey/bootstrap.py` prints one line.
- [ ] `application/` keeps 100% branch coverage.

## Tests to write first (TDD)
Append to `tests/application/test_deploy_execute_handler.py`, using the module's shared fakes as
lane `fakes-deploy` left them (`FaultyCloudClient`, `InMemoryDeploymentStateStore`, `FakeClock`,
`review_ledger(InMemoryLedger(), phase=Phase.DEPLOY_EXECUTE)`, `InMemoryProjectRepository`), with
`store = InMemoryQueueStore(); jobs = FakeJobRepository(store=store)` (`tests/fakes/queue.py`).
Two small evaluators may be written in the module, both injected through the `evaluator=` seam:
`_FixedReportEvaluator(report)` (returns the report after calling the client's
`discover_environment`) and `_CancelDuringPlanEvaluator(jobs)` (enqueues a `deploy.cancel` job for
the same project and cycle, then delegates to `DEPLOYMENT_PLAN_EVALUATOR`).
- `test_a_requested_cancel_skips_everything` — a `deploy.cancel` job is enqueued first; the
  outcome is `Success` with `status == "cancelled"`; `client.steps_run == []`; one
  `deployment_execute_skipped` event names the cancel's id; the project did not move.
- `test_a_withdrawn_cancel_does_not_block` — a `deployment_cancel_withdrawn` event with the
  cancel's id as `job_id` is in the ledger; the deploy runs to `status == "verified"`.
- `test_a_failed_cancel_does_not_block` — the cancel's record in `store.jobs` is replaced with
  `state=JobState.FAILED`; the deploy runs.
- `test_a_cancel_requested_during_the_plan_stops_the_apply` — `_CancelDuringPlanEvaluator`;
  `status == "cancelled"`; `DeployStep.APPLY` not in `client.steps_run`.
- `test_a_safe_plan_is_recorded_then_applied` — `evaluator=DEPLOYMENT_PLAN_EVALUATOR`,
  `FaultyCloudClient()`; steps `DISCOVER, PLAN, APPLY, VERIFY`; a `deployment_plan_evaluated` event
  precedes the `deployment_verification` artifact.
- `test_an_unknown_plan_goes_to_triage` — the production `AzureCliAdapter()` (cannot preview) with
  the real evaluator: `Failure(FailureClass.WORK, ...)`; a `FINDING_RAISED` with
  `failure_class == "ambiguous_configuration"`; a `deploy.triage` job enqueued; no verification artifact.
- `test_a_destructive_plan_goes_to_triage_as_destructive` — `_FixedReportEvaluator` with a report
  whose evaluation holds a `DELETE` → finding `failure_class == "destructive_data_migration"`, no apply.
- `test_an_over_budget_plan_goes_to_triage_as_cap_exhausted` — a CREATE costing 500.0 against
  `CostBoundary(100.0, 10.0)` → `"cap_exhausted"`.
- `test_the_verification_artifact_carries_the_spec` — the artifact's `spec == DEPLOYMENT_SPEC_CODEC.to_payload(spec)`,
  `spec_digest == DEPLOYMENT_SPEC_CODEC.digest(spec)`, `spec_id` and `scope_digest` match.
- `test_without_an_evaluator_the_graph_is_as_before` — `evaluator` omitted: steps
  `DISCOVER, APPLY, VERIFY` and no plan event.
- `test_the_handler_satisfies_its_interface`.

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

One coverage run at a time.

## Out of scope
- The cancel and rollback handlers (`gap-deploy-cancel`, `gap-deploy-rollback-2`), the CLI (`gap-deploy-cli-2`).
- Steps 5-7 of the graph (configure, migrate, release) and progressive exposure.
- `tests/system/test_delivery_stage_set.py` (protected), CHANGELOG.md, docs/, ADRs, CLAUDE.md,
  AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(deploy): DEPLOY_EXECUTE plans first, honours a cancel, and records the verified spec`. Do not push.

## Lane card
- **Depends on:** `gap-deploy-plan-2`, `gap-deploy-plan-3`, `gap-deploy-plan-4`, `gap-deploy-rollback-1`, `fakes-deploy`.
  (Plans 3 and 4 first, so no real OpenStack or Azure deploy is ever blocked as "cannot preview".)
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/system/test_delivery_stage_set.py`, every deploy handler test.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
