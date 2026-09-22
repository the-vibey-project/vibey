## Title
feat(deploy): a deploy.rollback job re-applies the last verified deployment state, and parks a gate when there is none or its consent does not cover it

## Why
`vibey deploy rollback` is a placeholder (`src/vibey/cli/main.py:1123-1152`: "does not call
AzureClientPort.delete_resource or any other real rollback operation"). Gap C5
(`issue-audit/gaps.md:232-241`): rollback "returns to the last accepted deployment state", through
`CloudClientPort`, writing ledger events and parking a gate on ambiguity. Sub-doctrine 10.d
(`src/vibey_tools/gh/docs/doctrines.md:395-410` at `d3b4a388`) makes recoverability a clearance
criterion; ADR-0013 (`docs/architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md:78-80`)
says to "roll back … only according to the accepted recovery policy".

The last accepted state is the ledger's: lane `gap-deploy-execute-control` records every verified
deployment's spec (`"spec"`, `"spec_digest"`) in its `deployment_verification` artifact, and lane
`gap-deploy-rollback-1`'s `DeploymentSpecCodec` reads it back. A rollback re-applies the most recent
earlier verified spec that differs from what is deployed now — the clients' `execute_plan` is
create-or-update, so re-applying is the rollback. Two cases are the human's to decide, and park a
gate (CLAUDE.md: never block a worker): there is no earlier state to return to, or the recorded
consent does not cover the earlier spec's scope (consent is digest-bound; ADR-0013 `:50-54`). The
rollback is a DEPLOY_REVIEW action (the CLI, lane `gap-deploy-cli-2`, enqueues it only there), and the
phase does not change.

## Required behaviour
1. New `src/vibey/application/deploy_rollback_handler.py` declares
   `NO_TARGET_GATE_KIND: Final = "deploy_rollback_no_target"` (options `("cancel_deployment", "keep_current")`),
   `NEEDS_CONSENT_GATE_KIND: Final = "deploy_rollback_needs_consent"` (options `("loop_deploy_design", "keep_current")`),
   both with default answer `"keep_current"`, and `class DeployRollbackHandler` with
   `__init__(self, *, ledgers: Mapping[Phase, PhaseLedger], jobs: JobRepository, gates: HumanGateRepository, cloud_client: CloudClientPort, spec_store: DeploymentSpecStore, consent_provider: Callable[[UUID], DeploymentConsent | None] | None = None, codec: DeploymentSpecCodecInterface = DEPLOYMENT_SPEC_CODEC)`.
2. `async def handle(self, job: JobRecord) -> Outcome`, in order ("record" means `DECISION_RECORDED`
   through the job's phase ledger with `job_id=job.id`, as in `deploy_execute_handler.py:96-106`):
   1. `job.kind != "deploy.rollback"` → `Failure(FailureClass.VIBEY, "expected deploy.rollback job")`;
      no ledger for `job.phase` → `Failure(FailureClass.VIBEY, f"deploy.rollback has no ledger for phase {job.phase}")`.
   2. **Replay.** A recorded `deployment_rolled_back`, `deployment_rollback_withdrawn` or
      `deployment_rollback_refused` with this `job_id` → `Success({"status": "replayed"})`. A
      `deployment_verification` artifact with this `job_id` but no `deployment_rolled_back` (a crash
      between the two appends) → record the decision of step 9 from that artifact's fields and
      return `Success({"status": "rolled_back", "replayed": True})`.
   3. **A gate.** `gate = await gates.latest_for_job(job.id)`: unanswered → `Park` with the gate's
      request rebuilt (as `deploy_review_handler.py:164-172`). Answered, with
      `choice = str(gate.answer.get("choice", "")).strip().lower()`:
      - kind `deploy_rollback_no_target`, `cancel_deployment` → enqueue
        `EnqueueRequest(project_id=job.project_id, cycle=job.cycle, phase=Phase.DEPLOY_REVIEW, kind="deploy.cancel", idempotency_key=idempotency_key(job.project_id, job.cycle, "deploy.cancel", f"rollback:{job.id}"), requirement={"effort": Effort.LOW.name.lower()})`;
      - kind `deploy_rollback_needs_consent`, `loop_deploy_design` → enqueue
        `kind="deploy.route"`, `payload={"action": "loop_deploy_design"}`, key subject `f"rollback:{job.id}"`
        (the existing routing handler moves ④ and enqueues the interview, `deploy_review_routing.py:77-108`);
      - then, whatever the choice, record
        `{"decision": "deployment_rollback_withdrawn", "reason": f"gate {gate.kind} answered {choice!r}"}`
        and return `Success({"status": "rollback_withdrawn", "choice": choice})`.
   4. `verified` = the ledger's interpretable `ARTIFACT_PRODUCED` events with
      `payload["artifact_type"] == "deployment_verification"`, in `seq` order. None → record
      `{"decision": "deployment_rollback_refused", "reason": "no verified deployment is recorded"}` →
      `Success({"status": "refused"})`.
   5. `current = verified[-1]`; `current_digest = str(current.payload.get("spec_digest", ""))`. When
      it differs from `str(job.payload.get("from_spec_digest", ""))` → record refused with
      `reason=f"the deployed state changed since the rollback was requested ({job.payload.get('from_spec_digest')} -> {current_digest})"`
      → `Success({"status": "refused"})`.
   6. **Target.** Walk `verified[:-1]` newest first; for each with a `"spec"` payload whose
      `spec_digest` differs from `current_digest`, try `codec.from_payload(payload["spec"])`; the
      first that parses is the target. Entries without `"spec"` or that raise
      `InvalidDeploymentPayload` are counted as `unreadable`. No target → raise the
      `deploy_rollback_no_target` gate with prompt
      `f"### Deployment rollback: no earlier state\n\nNo earlier verified deployment state is recorded to return to ({unreadable} earlier verification(s) carry no readable spec).\n\nAnswer `cancel_deployment` to cancel and release this deployment, or `keep_current` to keep it."`,
      record `{"decision": "deployment_rollback_needs_decision", "reason": "no earlier verified deployment state", "gate_id": str(raised.gate_id)}`,
      return `Park(request, gate=raised)`.
   7. **Consent.** `consent` absent or `not consent.matches_spec(target)` → raise the
      `deploy_rollback_needs_consent` gate with prompt
      `f"### Deployment rollback: consent does not cover the earlier state\n\nThe earlier verified spec {target.spec_id} targets scope digest {target.scope_digest()}, which the recorded consent does not authorize.\n\nAnswer `loop_deploy_design` to return to deployment design and consent again, or `keep_current` to keep the current deployment."`,
      record `{"decision": "deployment_rollback_needs_decision", "reason": "the recorded consent does not cover the earlier spec", "gate_id": ...}`,
      return `Park(request, gate=raised)`.
   8. **Apply.** In a `try`: `result = await cloud_client.execute_plan(target, consent)`, then
      `status = await cloud_client.get_resource_status(target.target_scope, target.spec_id)`; a state
      other than `Succeeded`/`Healthy` raises `RuntimeError(f"rollback verification failed: {status.provisioning_state}/{status.health_state}")`.
      On any exception: append `FINDING_RAISED`
      `{"finding_id": f"rollback-{job.id}", "failure_class": DeploymentFailureClass.RECOVERY_OUTSIDE_RUNBOOK.value, "error": str(exc)}`
      and return `Failure(FailureClass.WORK, str(exc))`.
   9. **Record.** `await spec_store.save_spec(job.project_id, target)`; append `ARTIFACT_PRODUCED`
      `{"artifact_type": "deployment_verification", "deployment_id": result.deployment_id, "outputs": dict(result.outputs), "spec_id": target.spec_id, "scope_digest": target.scope_digest(), "spec": codec.to_payload(target), "spec_digest": codec.digest(target), "rolled_back_from": current_digest}`;
      record `{"decision": "deployment_rolled_back", "from_spec_digest": current_digest, "to_spec_digest": codec.digest(target), "spec_id": target.spec_id}`;
      return `Success({"status": "rolled_back", "to_spec_digest": codec.digest(target)})`.
3. `DeployRollbackHandlerInterface(JobHandler, Protocol)` joins `class_contracts.py` after
   `DeployCancelHandlerInterface`, is exported, and is `EXEMPT` as `ExemptReason.CLASS_CONTRACT`.
4. `src/vibey/bootstrap.py`: after the `"deploy.cancel"` entry add
   `"deploy.rollback": DeployRollbackHandler(ledgers=deploy_ledgers, jobs=resources.jobs, gates=resources.gates, cloud_client=azure, spec_store=deploy_state, consent_provider=deploy_state.load_consent),`.

## Where to change
- New `src/vibey/application/deploy_rollback_handler.py` (provenance header of
  `src/vibey/application/deploy_review_routing.py`).
- `src/vibey/application/interfaces/class_contracts.py`, `src/vibey/application/interfaces/__init__.py`,
  `tests/fakes/registry.py`, `src/vibey/bootstrap.py` (`edit_file` only).
- New `tests/application/test_deploy_rollback_handler.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/application/test_deploy_rollback_handler.py tests/fakes` passes with PostgreSQL stopped.
- [ ] `grep -n '"deploy.rollback": DeployRollbackHandler(' src/vibey/bootstrap.py` prints one line.
- [ ] `application/` keeps 100% branch coverage.

## Tests to write first (TDD)
`tests/application/test_deploy_rollback_handler.py`, with the shared fakes named in
`specs/gap-deploy-cancel.md`'s tests (queue store, job and gate repositories, one `InMemoryLedger`
with phase views, `inner = InMemoryAzureClientAdapter(); client = FaultyCloudClient(inner)`,
`InMemoryDeploymentStateStore`). Specs A and B share a scope and differ in `topology.instances`;
"verified X" means appending, through the `DEPLOY_EXECUTE` view, the artifact
`gap-deploy-execute-control` writes, built with `DEPLOYMENT_SPEC_CODEC`. The job is a
`deploy.rollback` in `DEPLOY_REVIEW` with `payload={"from_spec_digest": digest(B)}`.
- `test_rollback_reapplies_the_last_earlier_verified_state` — verified A, verified B, consent for
  the shared scope → `Success` with `to_spec_digest == digest(A)`; `APPLY` and `VERIFY` ran;
  the state store's spec is A; the newest artifact has `spec_digest == digest(A)` and
  `rolled_back_from == digest(B)`; one `deployment_rolled_back` event.
- `test_an_identical_earlier_state_is_skipped` — verified A, verified B, verified B again →
  the target is A.
- `test_no_earlier_state_parks_the_no_target_gate` — verified B only → `Park`, gate kind
  `deploy_rollback_no_target`, the exact prompt with `0 earlier verification(s)`, no apply.
- `test_verifications_without_a_spec_count_as_unreadable` — one legacy artifact (no `"spec"`),
  then verified B → the prompt says `1 earlier verification(s)`.
- `test_consent_that_does_not_cover_the_earlier_scope_parks` — A's scope differs from B's and the
  consent matches only B → gate kind `deploy_rollback_needs_consent`, no apply.
- `test_answering_cancel_deployment_enqueues_a_cancel` and
  `test_answering_loop_deploy_design_enqueues_the_route` — the enqueued job's kind, phase, payload
  and idempotency key; a `deployment_rollback_withdrawn` event; `keep_current` enqueues nothing.
- `test_a_stale_request_is_refused` — `from_spec_digest` names A while B is current → refused event, no apply.
- `test_nothing_verified_is_refused`.
- `test_a_failed_apply_records_a_finding` — `FaultyCloudClient(inner, fail_at=DeployStep.APPLY)` →
  `Failure(FailureClass.WORK, ...)` and a `FINDING_RAISED` with `recovery_outside_runbook`;
  `degrade_at_verify=True` → the same with `rollback verification failed: Failed/Degraded`.
- `test_a_replay_after_success_changes_nothing` and `test_a_replay_after_the_artifact_records_only_the_decision`.
- `test_wrong_kind_and_missing_ledger_are_our_bug`, `test_the_handler_satisfies_its_interface`.

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
- IaC-native rollbacks (Heat `stack cancel`, CloudFormation `rollback-stack`); the CLI verb
  (`gap-deploy-cli-2`); automatic rollback on health failure (`evaluate_retry_ladder`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(deploy): a deploy.rollback job re-applies the last verified deployment state`. Do not push.

## Lane card
- **Depends on:** `gap-deploy-cancel`, `gap-deploy-rollback-1`, `gap-deploy-execute-control`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/system/test_delivery_stage_set.py` and every deploy handler test.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
