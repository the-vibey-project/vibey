## Title
feat(cli): vibey deploy status names the project's deploy target, and says when a paid declaration resolved it

## Why
ADR-0042 (`docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:108-109`)
says a paid platform "can never arrive silently". Sub-doctrine 8.b's paid defaults
(`src/vibey_tools/gh/docs/doctrines.md:188-194` at `d3b4a388`) resolve `[deploy] target = "paid"`
to AWS (lane `gap-deploy-target-paid`), and gap C2 (`issue-audit/gaps.md:189-200`) asks that the
resolved value be written into status output "so the declaration is visible". Today
`vibey deploy status` (`src/vibey/cli/main.py:965-1008`) prints project, phase, cycle and endpoint,
and never the cloud. Status must be evidence-bounded (10.f, `doctrines.md:419`): a project created
before 3.0.0 stored no `[deploy]` table (lane `openstack-client-p1`, #330 child 3, starts storing
it), and the line says so rather than implying a declaration nobody made.

## Required behaviour
1. `vibey deploy status [PROJECT]` prints one new line, `Target:     <value>`, immediately after
   the `Cycle:` line and before the `Endpoint:` line. The label is padded to the same width as
   its neighbours (`"Target:     "`, 12 characters).
2. `<value>` is:
   - when `project.config` has a `"deploy"` key: `DeployConfig.from_mapping(project.config).target_line()`,
     so a stored `{"deploy": {"target": "paid"}}` prints
     `Target:     aws (declared 'paid': AWS is the default paid cloud, sub-doctrine 8.b)` and a
     stored `{"deploy": {"target": "azure"}}` prints `Target:     azure`;
   - otherwise `f"{DeployConfig().target} (default; this project stored no [deploy] table)"`, i.e.
     `Target:     openstack (default; this project stored no [deploy] table)`.
3. An invalid stored table raises the domain's `ConfigError` (a `VibeyError`). Today
   `deploy_status` ends with a bare `asyncio.run(show_status())` (`main.py:1008`), so the error
   would surface as a traceback. That line becomes
   ```python
       with guard():
           asyncio.run(show_status())
   ```
   as `new_project` does (`main.py:236`), and `guard()` (`src/vibey/cli/errors.py:89-95`) prints
   `Error: deploy.target: ...` and exits with `EXIT_BLOCKED` (3, `errors.py:35`).
4. Every other line of the command's output, and its exit codes, are unchanged.

## Where to change
- `src/vibey/cli/main.py` (1761 lines — `edit_file` only), function `deploy_status`:
  - import `DeployConfig` from `vibey.domain.config` beside the other `vibey.domain` imports if
    `grep -n "from vibey.domain.config import" src/vibey/cli/main.py` does not already show it
    (lane `openstack-client-p2` may have added it);
  - immediately after the line
    `            typer.echo(f"Cycle:      {project.cycle}/{project.max_cycles}")` insert:
    ```python
                # 10.f: a project created before 3.0.0 stored no [deploy] table; say so
                # rather than print a default as if a human had declared it.
                if "deploy" in project.config:
                    target = DeployConfig.from_mapping(project.config).target_line()
                else:
                    target = f"{DeployConfig().target} (default; this project stored no [deploy] table)"
                typer.echo(f"Target:     {target}")
    ```
  - replace the function's last line `    asyncio.run(show_status())` (the one directly after
    `typer.echo(f"Endpoint:   {endpoint}")`'s block, at `:1008`; the text also occurs in no
    other command — check with `grep -n "asyncio.run(show_status())" src/vibey/cli/main.py`)
    with the two-line `with guard():` form of behaviour 3. `guard` is already imported (`:36`).
- `tests/cli/test_deploy_cli.py`: append the tests below (never rewrite the file).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli/test_deploy_cli.py` passes with PostgreSQL stopped.
- [ ] The existing tests in `tests/cli/test_deploy_cli.py` pass unedited.
- [ ] `src/vibey/cli/*` keeps 100% branch coverage.

## Tests to write first (TDD)
Append to `tests/cli/test_deploy_cli.py`. Seed and invoke exactly as that module does after lane
`fakes-cli-ledger-deploy` (the `memory_app` fixture and `invoke` helper from
`tests/cli/ops_support.py`): create each project with
`await resources.projects.create("<name>", tmp_path, max_cycles=5, config=<config>)` inside
`async with memory_app.open_app() as resources:`, then `invoke(memory_app, "deploy", "status", str(project_id))`.
- `test_deploy_status_names_a_paid_declaration` — config `{"project": {"name": "p"}, "deploy": {"target": "paid"}}`;
  exit 0; the output contains
  `Target:     aws (declared 'paid': AWS is the default paid cloud, sub-doctrine 8.b)`.
- `test_deploy_status_names_a_declared_target` — `{"deploy": {"target": "azure"}}`; the output
  contains the line `Target:     azure` and no `declared`.
- `test_deploy_status_says_when_no_target_was_stored` — `{"project": {"name": "p"}}`; the output
  contains `Target:     openstack (default; this project stored no [deploy] table)`.
- `test_deploy_status_target_sits_between_cycle_and_endpoint` — for the paid project, the index of
  `"Cycle:"` < index of `"Target:"` < index of `"Endpoint:"` in the output.
- `test_deploy_status_refuses_an_invalid_stored_target` — `{"deploy": {"target": "gcp"}}`; exit
  code 3 and the output contains `deploy.target`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli/test_deploy_cli.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

One coverage run at a time.

## Out of scope
- The resolution itself (`gap-deploy-target-paid`) and the worker's `deploy_target=` startup line
  (`openstack-client-p2`, #331 child 4).
- `vibey deploy inspect`, `plan`, `cancel`, `rollback` (`gap-deploy-cli-2`).
- The vibey.toml fallback for projects that stored no table (the worker's concern, #331 child 4).
- CHANGELOG.md, docs/ (`docs/reference/cli.md`), ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(cli): vibey deploy status names the deploy target and any paid declaration`. Do not push.

## Lane card
- **Depends on:** `gap-deploy-target-paid`, `gap-deploy-cli-2` (both edit `deploy_*` in `main.py` and
  `tests/cli/test_deploy_cli.py`; this one goes second), `fakes-cli-ledger-deploy`.
- **Files touched:** `src/vibey/cli/main.py`, `tests/cli/test_deploy_cli.py`.
- **Must keep passing unchanged:** every existing test in `tests/cli/`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
