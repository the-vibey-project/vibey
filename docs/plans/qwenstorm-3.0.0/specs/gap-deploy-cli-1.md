## Title
feat(deploy): DeploymentControlRequests turns a plan, cancel or rollback request into one idempotent job, refusing what the phase or the ledger does not allow

## Why
Gap C5 (`issue-audit/gaps.md:232-241`): `vibey deploy plan | cancel | rollback` are placeholders
(`src/vibey/cli/main.py:1059-1152`). The work runs on the worker as `deploy.plan`, `deploy.cancel`
and `deploy.rollback` jobs (lanes `gap-deploy-plan-2`, `gap-deploy-cancel`,
`gap-deploy-rollback-2`), because the worker holds the cloud client (`src/vibey/bootstrap.py:371`)
and a CLI must never wait on a cloud or a human (CLAUDE.md). What the CLI needs is one application
service that decides, before anything is queued, whether the request applies — the right phase, a
spec to plan, a verified state to roll back from — and enqueues exactly one job per request, so a
repeated command is idempotent under replay. The pattern is `enqueue_design_interview`
(`src/vibey/application/project_kickoff.py:21-56`), shared by the CLI and the operator so the two
cannot drift (10.e, `src/vibey_tools/gh/docs/doctrines.md:417` at `d3b4a388`); new code takes the
class-and-interface form (9.b, `doctrines.md:349`). The CLI verbs are `gap-deploy-cli-2`.

## Required behaviour
1. New `src/vibey/application/deployment_control.py` declares:
   - `class DeploymentControlRefused(VibeyError)` (no interface: an exception).
   - `@dataclass(frozen=True, slots=True) class DeploymentControlRequest` with `job_id: UUID`,
     `kind: str`, `phase: Phase`, `subject: str`.
   - `DEPLOYMENT_PHASES: Final = frozenset({Phase.DEPLOY_DESIGN, Phase.DEPLOY_EXECUTE, Phase.DEPLOY_REVIEW})`.
   - `class DeploymentControlRequests` with
     `__init__(self, *, projects: ProjectStore, jobs: JobRepository, ledger: LedgerReader, spec_provider: Callable[[UUID], DeploymentSpec | None], codec: DeploymentSpecCodecInterface = DEPLOYMENT_SPEC_CODEC)`
     and:
     - `async def request_plan(self, project_id: UUID) -> DeploymentControlRequest`;
     - `async def request_cancel(self, project_id: UUID) -> DeploymentControlRequest`;
     - `async def request_rollback(self, project_id: UUID) -> DeploymentControlRequest`;
     - `async def latest_plan(self, project_id: UUID, job_id: UUID) -> Mapping[str, object] | None`:
       the payload of the newest `DECISION_RECORDED` event with that `job_id` whose `decision` is
       `deployment_plan_evaluated` or `deployment_plan_unknown`, else `None`.
2. Each `request_*`:
   1. `project = await projects.get(project_id)`; `None` → `UnknownProject(f"unknown project {project_id}")`
      (`vibey.domain.errors`).
   2. Phase: plan and cancel need `project.phase in DEPLOYMENT_PHASES`; rollback needs
      `Phase.DEPLOY_REVIEW`. Otherwise `WrongPhase(f"deploy {verb} applies in {allowed}; the project is in {phase}")`
      where `allowed` is `"deploy_design, deploy_execute or deploy_review"` (plan, cancel) or
      `"deploy_review"` (rollback), and `phase` is the stored phase's `.value`.
   3. The subject (it becomes the idempotency key's last part, `idempotency_key(project_id, cycle, kind, subject)`,
      `src/vibey/domain/job.py:66-68`):
      - plan: `spec = spec_provider(project_id)`; `None` →
        `DeploymentControlRefused("deploy plan needs a deployment spec; DEPLOY_DESIGN has not synthesized one")`;
        subject `f"plan:{codec.digest(spec)}"` (one plan per spec content per cycle);
      - cancel: subject `"cancel"` (one cancel per cycle);
      - rollback: the newest interpretable `ARTIFACT_PRODUCED` event in `ledger.all_for_project(project_id)`
        with `payload["artifact_type"] == "deployment_verification"`; none, or one without a
        `"spec_digest"` → `DeploymentControlRefused("deploy rollback needs a verified deployment whose spec was recorded")`;
        subject `f"rollback:{spec_digest}"` and the job's payload `{"from_spec_digest": spec_digest}`.
   4. `job = await jobs.enqueue(EnqueueRequest(project_id=project_id, cycle=project.cycle, phase=project.phase, kind=<"deploy.plan" | "deploy.cancel" | "deploy.rollback">, idempotency_key=idempotency_key(project_id, project.cycle, kind, subject), payload=<{} or the rollback payload>, requirement={"effort": Effort.LOW.name.lower()}))`.
   5. Return `DeploymentControlRequest(job_id=job.id, kind=kind, phase=project.phase, subject=subject)`.
   Nothing is written to the ledger here: the handlers record what they do, with their job's id (7.c).
3. New `src/vibey/application/interfaces/deployment_control_interface.py`:
   `DeploymentControlRequestInterface` (the four fields as read-only properties) and
   `DeploymentControlRequestsInterface` (the four methods), `@runtime_checkable`; both exported from
   `application/interfaces/__init__.py` (an import block kept in sorted order after the
   `deploy_plan_interface` block, and two `__all__` entries after `"DeployPlanHandlerInterface",`);
   `tests/fakes/registry.py` `EXEMPT`s them as `VALUE_CONTRACT` and `CLASS_CONTRACT`.

## Where to change
- New `src/vibey/application/deployment_control.py`, `src/vibey/application/interfaces/deployment_control_interface.py`
  (provenance header of `src/vibey/application/project_kickoff.py`).
- `src/vibey/application/interfaces/__init__.py`, `tests/fakes/registry.py` (`edit_file` only).
- New `tests/application/test_deployment_control.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/application/test_deployment_control.py tests/application/test_interfaces_convention.py tests/fakes` passes with PostgreSQL stopped.
- [ ] `application/` keeps 100% branch coverage.

## Tests to write first (TDD)
`tests/application/test_deployment_control.py`: `InMemoryProjectRepository`, `FakeJobRepository`
over an `InMemoryQueueStore`, `InMemoryLedger` (read directly; appended through
`review_ledger(ledger, phase=Phase.DEPLOY_EXECUTE)` to seed artifacts), an
`InMemoryDeploymentStateStore` whose `load_spec` is the `spec_provider`, `DEPLOYMENT_SPEC_CODEC`.
- `test_plan_enqueues_one_job_per_spec` — in `DEPLOY_DESIGN` with a saved spec: a `deploy.plan`
  job in `DEPLOY_DESIGN`; a second request returns the same `job_id`; after saving a changed spec
  a third returns a new one.
- `test_plan_needs_a_spec` — no spec → `DeploymentControlRefused` with the exact message; no job.
- `test_cancel_enqueues_once_per_cycle` — in each of the three deployment phases: a
  `deploy.cancel` job in that phase; repeating returns the same id.
- `test_rollback_pins_the_state_it_rolls_back_from` — in `DEPLOY_REVIEW` with a verified artifact
  carrying `spec_digest="d-1"`: payload `{"from_spec_digest": "d-1"}` and subject `rollback:d-1`.
- `test_rollback_needs_a_recorded_spec` — no artifact, and an artifact without `spec_digest` →
  `DeploymentControlRefused`.
- `test_each_verb_refuses_the_wrong_phase` — parametrized: plan in `BUILD`, cancel in `DONE`,
  rollback in `DEPLOY_EXECUTE` → `WrongPhase` naming the allowed phases and the current one.
- `test_an_unknown_project_is_refused` — `UnknownProject`.
- `test_latest_plan_reads_the_jobs_newest_plan_event` — two plan events for the job and one for
  another job → the newer of the two; none → `None`.
- `test_nothing_is_written_to_the_ledger` — the ledger's event count is unchanged by every request.
- `test_the_classes_satisfy_their_interfaces`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/application tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

One coverage run at a time.

## Out of scope
- The CLI verbs (`gap-deploy-cli-2`), the handlers (`gap-deploy-plan-2`, `gap-deploy-cancel`,
  `gap-deploy-rollback-2`), and the Kubernetes operator (it may call this service later).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(deploy): DeploymentControlRequests enqueues plan, cancel and rollback jobs`. Do not push.

## Lane card
- **Depends on:** `gap-deploy-rollback-2` (and through it `gap-deploy-rollback-1`, `gap-deploy-cancel`,
  `gap-deploy-plan-2`; they edit the same interfaces `__init__` and registry, so they run first),
  `fakes-deploy-review`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** every test in `tests/application/`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
