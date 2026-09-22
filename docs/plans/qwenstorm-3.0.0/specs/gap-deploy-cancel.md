## Title
feat(deploy): a deploy.cancel job abandons the deployment, releases what it created under the recorded consent, and parks a gate when it cannot

## Why
`vibey deploy cancel` is a placeholder (`src/vibey/cli/main.py:1091-1120`: "does not call
AzureClientPort.delete_resource or otherwise touch any real cloud resource, ledger event, or
job/phase state"). Gap C5 (`issue-audit/gaps.md:232-241`): cancel "stops a DEPLOY_EXECUTE and
releases created resources", through `CloudClientPort`, writing ledger events and parking a gate on
ambiguity. ADR-0013 (`docs/architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md:95`):
"Any nonterminal phase may enter `ABANDONED` on explicit user cancellation", and every deployment
phase has that edge (`src/vibey/domain/phase.py:101-113`). Releasing is a mutation, so it needs the
consent the acceptance gate recorded (`DeploymentConsent.matches_spec`,
`src/vibey/domain/deployment.py:161-170`; ADR-0013 `:50-54`: "Consent is ledger evidence, not a CLI
flag"). When resources exist and no matching consent does, vibey cannot decide for the human: it
parks a gate (CLAUDE.md: never block a worker on a human; ADR-0009) and releases its lease.

The job runs on the worker, where the cloud client is (`src/vibey/bootstrap.py:371`). It waits,
without blocking, for an in-flight `deploy.execute` to release its lease (a `Defer`), and lane
`gap-deploy-execute-control` makes a queued `deploy.execute` stand down once this job exists. Every
effect is idempotent under replay (CLAUDE.md), and every step is in the ledger (7.c,
`src/vibey_tools/gh/docs/doctrines.md:82-91` at `d3b4a388`).

## Required behaviour
1. New `src/vibey/application/deploy_cancel_handler.py` declares
   `CANCEL_GATE_KIND: Final = "deploy_cancel_unreleased"`,
   `CANCEL_GATE_OPTIONS: Final = ("abandon_keep_resources", "keep_deployment")` and
   `class DeployCancelHandler` with
   `__init__(self, *, ledgers: Mapping[Phase, PhaseLedger], jobs: JobRepository, gates: HumanGateRepository, projects: ProjectStore, cloud_client: CloudClientPort, clock: Clock, spec_provider: Callable[[UUID], DeploymentSpec | None] | None = None, consent_provider: Callable[[UUID], DeploymentConsent | None] | None = None, in_flight_retry: timedelta = timedelta(seconds=30))`.
2. `async def handle(self, job: JobRecord) -> Outcome`, in order. "Record X" means
   `ledger.append_event(project_id=job.project_id, cycle=job.cycle, job_id=job.id, kind=EventKind.DECISION_RECORDED, payload=X)`.
   1. `job.kind != "deploy.cancel"` → `Failure(FailureClass.VIBEY, "expected deploy.cancel job")`.
   2. `ledger = self._ledgers.get(job.phase)` (only when `isinstance(job.phase, Phase)`); missing →
      `Failure(FailureClass.VIBEY, f"deploy.cancel has no ledger for phase {job.phase}")`.
   3. **Replay.** If the ledger already holds a `DECISION_RECORDED` event with this `job_id` whose
      `decision` is `deployment_cancelled`, `deployment_cancel_withdrawn` or
      `deployment_cancel_refused` → `Success({"status": "replayed"})`, no other effect.
   4. **In flight.** For `kind` in `("deploy.execute", "deploy.graph")`, the first record of
      `jobs.list_for_cycle(job.project_id, cycle=job.cycle, kind=kind)` whose
      `state is JobState.LEASED` → `Defer(retry_at=self._clock.now() + self._in_flight_retry, detail=f"deploy.cancel waits for DEPLOY_EXECUTE job {record.id} to release its lease")`.
   5. **An answered gate.** `gate = await gates.latest_for_job(job.id)`. An unanswered gate →
      `Park(HumanGateRequest(kind=gate.kind, prompt=gate.prompt, options=gate.options, default_answer=gate.default_answer))`
      (as `deploy_review_handler.py:164-172`). An answered one:
      `choice = str(gate.answer.get("choice", "")).strip().lower()`; `"abandon_keep_resources"` →
      finish (step 9) with `released=False`,
      `reason="consent is missing or stale; the operator chose to abandon and keep the resources"`;
      anything else → record `{"decision": "deployment_cancel_withdrawn", "reason": f"answer {choice!r}: the deployment is kept"}`
      and return `Success({"status": "cancel_withdrawn"})`.
   6. No spec (`spec_provider` absent or returning `None`) → finish with `released=False`,
      `reason="no deployment spec was synthesized; nothing was deployed"`.
   7. `discovery = await cloud_client.discover_environment(spec.target_scope)`. No
      `existing_resources` → finish with `released` = whether the ledger holds a
      `deployment_resources_released` decision with this `job_id` (a replay after the release),
      and `reason` `"released with the recorded consent"` when it does, else
      `"discovery found no deployed resources"`.
   8. Resources exist:
      - consent present and `consent.matches_spec(spec)` →
        `await cloud_client.delete_resource(spec.target_scope, spec.spec_id, consent)`, record
        `{"decision": "deployment_resources_released", "spec_id": spec.spec_id, "scope_digest": spec.scope_digest(), "existing_resources": n}`,
        then finish with `released=True`, `reason="released with the recorded consent"`;
      - otherwise raise a gate: `HumanGateRequest(kind=CANCEL_GATE_KIND, prompt=<below>, options=CANCEL_GATE_OPTIONS, default_answer="keep_deployment")`,
        `raised = await gates.raise_gate(job.project_id, job.id, request)`, record
        `{"decision": "deployment_cancel_needs_decision", "reason": "no recorded consent matches this spec's scope digest", "existing_resources": n, "gate_id": str(raised.gate_id)}`,
        and return `Park(request, gate=raised)`. The prompt is exactly:
        `f"### Deployment cancel: resources remain\n\n- **Spec**: {spec.spec_id} ({spec.target_scope.provider})\n- **Resources found**: {n}\n- **Why vibey will not release them**: no recorded consent matches this spec's scope digest, and releasing is a mutation that needs one.\n\nAnswer `abandon_keep_resources` to abandon the deployment and remove the resources yourself, or `keep_deployment` to withdraw the cancel."`
   9. **Finish** (a private method): `project = await projects.get(job.project_id)`; `None` →
      `Failure(FailureClass.VIBEY, f"unknown project {job.project_id}")`. When `project.phase` is
      `Phase.ABANDONED`, skip the transition (a replay). When it is `DEPLOY_DESIGN`,
      `DEPLOY_EXECUTE` or `DEPLOY_REVIEW`, `await projects.transition(job.project_id, expected=project.phase, to=Phase.ABANDONED)`.
      Any other phase → record `{"decision": "deployment_cancel_refused", "reason": f"the project is in {phase}, not a deployment phase"}`
      and return `Success({"status": "refused"})`. Then record
      `{"decision": "deployment_cancelled", "released": released, "reason": reason, "next_phase": "ABANDONED"}`
      and return `Success({"status": "cancelled", "released": released})`. The transition comes
      before the record, so a replay that finds the record also finds the project abandoned.
   A cloud error propagates (the worker retries; delete is idempotent on the real clients).
3. `DeployCancelHandlerInterface(JobHandler, Protocol)` (`handle`) is added to
   `src/vibey/application/interfaces/class_contracts.py` after `DeployReviewTriageHandlerInterface`,
   exported from `application/interfaces/__init__.py`, and listed in `tests/fakes/registry.py`'s
   `EXEMPT` as `ExemptReason.CLASS_CONTRACT`.
4. `src/vibey/bootstrap.py`: after the `"deploy.plan"` entry (lane `gap-deploy-plan-2`) add
   `"deploy.cancel": DeployCancelHandler(ledgers=deploy_ledgers, jobs=resources.jobs, gates=resources.gates, projects=resources.projects, cloud_client=azure, clock=clock, spec_provider=deploy_state.load_spec, consent_provider=deploy_state.load_consent),`.

## Where to change
- New `src/vibey/application/deploy_cancel_handler.py` (line 1: the provenance header of
  `src/vibey/application/deploy_review_handler.py`). Import `Defer, Failure, Outcome, Park, Success`
  from `vibey.application.worker`; `HumanGateRequest`, `JobRecord` from `vibey.application.dto`;
  `JobState`, `FailureClass` from `vibey.domain.job`.
- `src/vibey/application/interfaces/class_contracts.py`, `src/vibey/application/interfaces/__init__.py`,
  `tests/fakes/registry.py`, `src/vibey/bootstrap.py` (`edit_file` only).
- New `tests/application/test_deploy_cancel_handler.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/application/test_deploy_cancel_handler.py tests/fakes` passes with PostgreSQL stopped.
- [ ] `grep -n '"deploy.cancel": DeployCancelHandler(' src/vibey/bootstrap.py` prints one line.
- [ ] `application/` keeps 100% branch coverage.

## Tests to write first (TDD)
`tests/application/test_deploy_cancel_handler.py`, shared fakes only: `store = InMemoryQueueStore(clock=clock)`,
`FakeJobRepository(store=store)`, `FakeHumanGateRepository(store=store)` (`tests/fakes/queue.py`),
`InMemoryProjectRepository()` (`tests/fakes/projects.py`; create the project, then move it with one
`transition(pid, expected=Phase.INTAKE, to=<the phase under test>)`, as `tests/cli/test_deploy_cli.py`'s
seed does — the repository compare-and-sets and does not walk the edge graph), `FakeClock` (`tests/fakes/system.py`), one `InMemoryLedger`
with `review_ledger(ledger, phase=...)` views for the three deployment phases,
`inner = InMemoryAzureClientAdapter(); client = FaultyCloudClient(inner)` and `InMemoryDeploymentStateStore` (`tests/fakes/deploy.py`). Jobs are
enqueued through `jobs.enqueue(...)` and handled as returned.
- `test_cancel_releases_resources_under_the_recorded_consent` — spec and matching consent saved,
  `execute_plan` run on the client first; outcome `Success({"status": "cancelled", "released": True})`;
  `inner.resources == {}` afterwards; events `deployment_resources_released` then
  `deployment_cancelled`; the project is `ABANDONED`.
- `test_cancel_with_nothing_deployed_just_abandons` — spec saved, nothing applied → `released False`,
  reason `discovery found no deployed resources`, no delete.
- `test_cancel_without_a_spec_abandons` — no spec → reason `no deployment spec was synthesized; nothing was deployed`.
- `test_cancel_parks_when_resources_exist_without_matching_consent` — applied, then the consent
  replaced by one with another digest → `Park` whose gate has kind `deploy_cancel_unreleased`, the
  two options, default `keep_deployment`, and the exact prompt; one `deployment_cancel_needs_decision`
  event; the project did not move; no delete ran.
- `test_the_operator_abandons_and_keeps_the_resources` — answer the gate with
  `{"choice": "abandon_keep_resources"}` (`gates.answer(gate_id, answer=..., answered_by="operator")`),
  handle the job again → `released False`, the operator's reason, `ABANDONED`.
- `test_the_operator_withdraws_the_cancel` — answer `{"choice": "keep_deployment"}` →
  `Success({"status": "cancel_withdrawn"})`, a `deployment_cancel_withdrawn` event, the phase unchanged.
- `test_an_unanswered_gate_parks_again` — handle twice without answering → the second is a `Park`
  with the same kind and no second gate raised.
- `test_cancel_defers_while_deploy_execute_holds_its_lease` — a `deploy.execute` job claimed
  (`jobs.claim(pid, owner="w", lease=timedelta(minutes=2))`) → `Defer` with
  `retry_at == clock.now() + timedelta(seconds=30)` and the job id in `detail`; nothing recorded.
- `test_a_replay_after_finishing_changes_nothing` — handle to completion, handle again →
  `Success({"status": "replayed"})`, no new event.
- `test_cancel_outside_a_deployment_phase_is_refused` — project in `REVIEW` → `Success({"status": "refused"})`
  and a `deployment_cancel_refused` event; no transition.
- `test_wrong_kind_and_missing_ledger_are_our_bug` — both return `Failure(FailureClass.VIBEY, ...)`.
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
- DEPLOY_EXECUTE standing down for a cancel (`gap-deploy-execute-control`); the CLI verb (`gap-deploy-cli-2`).
- Deleting per-resource: the cloud clients delete the deployment unit (`spec.spec_id` → the stack
  or resource group), as `deploy_review_routing.py:146-147` already does.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(deploy): a deploy.cancel job abandons the deployment and releases its resources`. Do not push.

## Lane card
- **Depends on:** `gap-deploy-execute-control` (which already depends on `gap-deploy-plan-2`; it also
  edits `class_contracts.py`, the interfaces `__init__`, the registry and `bootstrap.py`, so the two
  lanes must not run side by side), `fakes-deploy-review`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/system/test_delivery_stage_set.py` and every deploy handler test.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
