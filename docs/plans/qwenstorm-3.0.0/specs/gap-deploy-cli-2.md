## Title
feat(cli)!: vibey deploy plan, cancel and rollback stop being placeholders — each queues its job and says what happens next

## Why
`src/vibey/cli/main.py:1059-1152` holds three placeholders: `deploy plan` prints "Status: NOT
EVALUATED — this command is a placeholder" (`:1084`), `deploy cancel` prints "deploy cancel is not
yet implemented" (`:1115-1118`), `deploy rollback` prints "deploy rollback is not yet implemented"
(`:1147-1150`). Gap C5 (`issue-audit/gaps.md:232-241`). The work now exists as worker jobs
(`gap-deploy-plan-2`, `gap-deploy-cancel`, `gap-deploy-rollback-2`) behind one request service
(`gap-deploy-cli-1`, `DeploymentControlRequests`). The CLI's job is to ask that service, print what
was queued and what the worker will do, and — for `plan` — show the newest evaluation the worker has
recorded for this request. It never waits on the cloud or on a human (CLAUDE.md), and status is
evidence-bounded (10.f, `src/vibey_tools/gh/docs/doctrines.md:419` at `d3b4a388`): no evaluation yet
reads PENDING, a client that cannot preview reads UNKNOWN, and the budget line says cost was not
estimated. Breaking: the three commands' output changes, and a refused request now exits 3.

## Required behaviour
1. New `src/vibey/cli/deploy_presenter.py`: `class DeployPlanPresenter` with
   `lines(self, project_name: str, job_id: UUID, plan: Mapping[str, object] | None) -> list[str]`
   returning, in order:
   - `f"Plan Evaluation for {project_name}:"`;
   - `f"  • Job:     {job_id} (deploy.plan; a worker evaluates it through its cloud client)"`;
   - status: `plan is None` → `"  • Status:  PENDING — no evaluation is recorded yet; run 'vibey worker' and ask again"`;
     `plan["previewed"]` falsy → `f"  • Status:  UNKNOWN — {plan.get('reason', '')}"`; otherwise
     `"  • Status:  SAFE"` when `plan.get("is_safe_for_automated_apply") is True`, else `"  • Status:  BLOCKED"`;
   - when previewed: `f"  • Changes: {c} create, {m} modify, {d} delete, {u} unchanged"` (counted
     over `plan["changes"]` entries that are dicts, by `action` `create`/`modify`/`delete`/`no_change`;
     a non-list counts nothing), then
     `f"  • Destructive Deletions: {'yes' if plan.get('has_destructive_deletions') is True else 'no'}"`,
     then one `f"  • Blocking: {reason}"` per string in `plan.get("blocking_reasons")` (when a list);
   - always last: `"  • Budget:  not estimated (vibey has no pricing source; the spec's cost boundary is not checked against a price)"`.
   `DEPLOY_PLAN_PRESENTER: Final[DeployPlanPresenterInterface] = DeployPlanPresenter()`, and
   `src/vibey/cli/interfaces/deploy_presenter_interface.py` declares `DeployPlanPresenterInterface`
   (copy `src/vibey/cli/interfaces/ledger_search_interface.py:1-25`'s shape).
2. `deploy_plan` (`main.py:1059-1088`): keep the project resolution (`:1069-1081`) as it is; replace
   the three placeholder `typer.echo` lines (`:1083-1086`) with
   ```python
               requests = DeploymentControlRequests(
                   projects=resources.projects,
                   jobs=resources.jobs,
                   ledger=resources.ledger,
                   spec_provider=FileDeploymentStateRepository(Path(project.repo_path)).load_spec,
               )
               request = await requests.request_plan(project.project_id)
               plan = await requests.latest_plan(project.project_id, request.job_id)
               for line in DEPLOY_PLAN_PRESENTER.lines(project.name, request.job_id, plan):
                   typer.echo(line)
   ```
   and the docstring (`:1063-1065`) with
   `"""Queue a plan evaluation for the deployment spec, and show the newest one a worker has recorded."""`.
3. `deploy_cancel` (`:1091-1120`): same resolution; the placeholder echo (`:1115-1118`) becomes a
   `request_cancel` call and two lines:
   `f"cancel requested for {project.name}: job {request.job_id} (deploy.cancel, phase {request.phase.value})"` and
   `"A worker abandons the deployment and releases its resources under the recorded consent; if it cannot, it parks a gate that 'vibey status' lists."`.
   Docstring: `"""Queue the cancellation of this project's deployment (ADR-0013: any deployment phase may be abandoned)."""`.
4. `deploy_rollback` (`:1123-1152`): same resolution; the placeholder echo (`:1147-1150`) becomes a
   `request_rollback` call and two lines:
   `f"rollback requested for {project.name}: job {request.job_id} (deploy.rollback, from spec digest {request.subject.removeprefix('rollback:')[:12]})"` and
   `"A worker re-applies the last earlier verified state; if there is none, or the recorded consent does not cover it, it parks a gate that 'vibey status' lists."`.
   Docstring: `"""Queue a rollback to the last earlier verified deployment state (DEPLOY_REVIEW only)."""`.
5. Each of the three commands' final `asyncio.run(...)` line (`:1088`, `:1120`, `:1152`) becomes
   `with guard():` around it, as `new_project` does (`:236`), so `WrongPhase`, `UnknownProject` and
   `DeploymentControlRefused` print `Error: …` and exit 3 (`src/vibey/cli/errors.py:84-95`). The
   commands' existing "no projects found" and "unknown project" exits (code 1) are unchanged.
6. Imports in `main.py`: `DeploymentControlRequests` from `vibey.application.deployment_control`,
   `FileDeploymentStateRepository` from `vibey.infrastructure.deploy.state_repository`,
   `DEPLOY_PLAN_PRESENTER` from `vibey.cli.deploy_presenter`.

## Where to change
- New `src/vibey/cli/deploy_presenter.py`, `src/vibey/cli/interfaces/deploy_presenter_interface.py`
  (provenance header of `src/vibey/cli/ledger_search.py`); export the interface from
  `src/vibey/cli/interfaces/__init__.py` as its siblings are.
- `src/vibey/cli/main.py` (`edit_file` only; the lines named above).
- `tests/cli/test_deploy_cli.py`: in the module's seed helper (the one that builds `spec-cli`), save
  the spec it builds with `await FileDeploymentStateRepository(<the project's repo path>).save_spec(project_id, spec)`;
  change `test_deploy_cancel_cli`'s assertion to `"cancel requested" in res.output`; change
  `test_deploy_rollback_cli` to expect exit code 3 and `deploy_review` in the output (its project is
  in DEPLOY_EXECUTE); keep `test_deploy_plan_cli` as it is; then append the tests below.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli/test_deploy_cli.py` passes with PostgreSQL stopped.
- [ ] `grep -n "NOT YET IMPLEMENTED\|not yet implemented\|placeholder" src/vibey/cli/main.py` finds none of the three deploy commands.
- [ ] `src/vibey/cli/*` keeps 100% branch coverage.

## Tests to write first (TDD)
Append to `tests/cli/test_deploy_cli.py` (the `memory_app` fixture and `invoke` helper of
`tests/cli/ops_support.py`, seeding through `async with memory_app.open_app() as resources:`):
- `test_presenter_pending_unknown_safe_and_blocked` — `DEPLOY_PLAN_PRESENTER.lines(...)` for `None`,
  an unpreviewed payload (`reason` shown), a safe payload with one `create`, and a blocked payload
  with a `delete` and a blocking reason: the exact lines of behaviour 1, the budget line last.
- `test_presenter_tolerates_malformed_payloads` — `changes="x"` and `blocking_reasons=None` count
  nothing and print no blocking line.
- `test_deploy_plan_queues_a_job_and_says_pending` — a `DEPLOY_DESIGN` project with a saved spec:
  exit 0; `Status:  PENDING`; one `deploy.plan` job in the queue; running the command again queues
  no second job.
- `test_deploy_plan_shows_the_recorded_evaluation` — after the first run, append a
  `deployment_plan_evaluated` event with that job's id (through a `DEPLOY_DESIGN` phase view); the
  second run prints `Status:  SAFE` and `Changes: 1 create`.
- `test_deploy_plan_without_a_spec_exits_3` — output contains `needs a deployment spec`.
- `test_deploy_cancel_queues_one_cancel` — exit 0, `cancel requested`, one `deploy.cancel` job.
- `test_deploy_cancel_outside_a_deployment_phase_exits_3` — a `BUILD` project; output names `deploy_design, deploy_execute or deploy_review`.
- `test_deploy_rollback_queues_from_the_verified_state` — a `DEPLOY_REVIEW` project with a verified
  artifact whose `spec_digest` is `"abcdef0123456789"`: exit 0; output contains `from spec digest abcdef012345`;
  the job's payload is `{"from_spec_digest": "abcdef0123456789"}`.
- `test_deploy_rollback_without_a_recorded_spec_exits_3`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

One coverage run at a time.

## Out of scope
- `deploy status` and `deploy inspect` (`gap-deploy-target-status` owns status's target line).
- Waiting for the worker, or a `--wait` flag (a CLI never blocks on a job).
- CHANGELOG.md, docs/ (`docs/reference/cli.md`'s deploy section), ADRs, CLAUDE.md, AGENTS.md,
  GEMINI.md and the skill trees.

The commit body carries the footer `BREAKING CHANGE: the three commands' output changes, and a request the phase or ledger does not allow exits 3.`

Commit as `feat(cli)!: vibey deploy plan, cancel and rollback queue real work`. Do not push.

## Lane card
- **Depends on:** `gap-deploy-cli-1`, `fakes-cli-ledger-deploy`.
  Note: the lane that edits the same deploy section and test module runs *after* this one and
  declares that dependency from its own side, so this lane waits on no AWS work. Its slug is
  deliberately not written on the line above: a slug named there is read as a dependency, and
  naming it would close a cycle.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** every other test in `tests/cli/`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
