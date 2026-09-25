# vibey-quality-gates (Antigravity mirror of `.claude/skills/vibey-quality-gates/SKILL.md`)

# vibey quality gates

CI runs a 7-gate sweep over the root `vibey` package, as the `gates` job in
`.github/workflows/ci.yml`. **All seven must pass** — together with the other CI
jobs below — before a PR can merge. Run them locally with
`pre-commit run --all-files --hook-stage pre-push` (a plain
`pre-commit run --all-files` runs only the ruff hooks) or individually:

## Gate 1: ruff check

Linter. Catches unused imports, undefined names, syntax errors, and common
anti-patterns.

```bash
uv run ruff check .
```

Root ruff covers `src/**/*.py` and `tests/**/*.py`, so it also lints the
workspace tenants under `src/vibey_runners/` and `src/vibey_tools/`.

## Gate 2: ruff format --check

Formatter. Ensures consistent code style across the repo. Fails if any file
would be reformatted.

```bash
uv run ruff format --check .
```

To fix: `uv run ruff format .`

## Gate 3: mypy --strict

Type checker. Enforces `--strict` mode across `src/vibey/`. Catches type
errors, missing type annotations, and `Any` usage.

```bash
uv run mypy --strict src/vibey
```

## Gate 4: pytest per-layer coverage (100%)

One test run produces a combined `.coverage` file; four per-layer reports
enforce 100% branch coverage. Each must pass or the build fails.

```bash
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
uv run coverage report --include='src/vibey/application/*' --fail-under=100
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
uv run coverage report --include='src/vibey/cli/*' --fail-under=100
```

**Why per-layer, not aggregate?** Because `domain/` is the safety-critical
layer and must never drop below 100%. An aggregate gate would allow a 95%
domain to hide behind a 100% infrastructure. See ADR-0023.

The test run needs a reachable Postgres even for a subset: `tests/conftest.py`
clones a migrated template database per xdist worker at session start. See the
`vibey-testing` skill.

## Gate 5: lint-imports

Onion architecture enforcer. Verifies dependencies point inward only, and
that `domain/` imports nothing but stdlib.

```bash
uv run lint-imports
```

If it fails, the error names the contract and the violating import. See
`.importlinter` for the contracts: `onion-layers`, `domain-independence`,
`application-independence`, and the declare-only contracts that keep each
`interfaces/` package from importing its consumers (`interfaces-declare-only`
for `application/interfaces`, `infrastructure-interfaces-declare-only`,
`vibey-gh-interfaces-declare-only`). The declare-only rule applies to every
`interfaces/` package. See ADR-0016.

See the `vibey-architecture` skill before fixing a violation.

## Gate 6: bandit

Security linter. Scans for common security issues: hardcoded passwords, SQL
injection, insecure temp files, weak crypto, shell=True, etc.

```bash
uv run bandit -q -r src/vibey
```

## Gate 7: pip-audit

Dependency vulnerability scanner. Checks for known CVEs in pinned
dependencies.

```bash
uv run pip-audit
```

## Hook diet

The seven gates are split across git hook stages so commits stay fast
(`.pre-commit-config.yaml`):

**Pre-commit stage** (runs on every `git commit`):
- ruff (`--fix`) + ruff format, on changed files

**Pre-push stage** (runs on every `git push`):
- The plain parallel test suite (`uv run pytest -q -p no:cacheprovider`) — kept
  so a test failure reports as itself rather than as a coverage-gate failure
- mypy --strict
- lint-imports
- Per-layer 100% coverage gates (pytest --cov + four reports)
- bandit
- pip-audit

**Commit-msg stage**: Conventional Commits enforcement.

**Pushing**: push through the push gate, never with a bare `git push`. Run
`python3 <storm>/tools/push_gate.py run -- git push origin HEAD:<branch>`, or from a
checkout with no storm, set `VIBEY_PUSH_LOCK=<dir>` and run the tracked
`docs/plans/qwenstorm-3.0.0/tools/push_gate.py`. It lets one pre-push run happen at a time
across every lane on the machine. Exit 124 (`reaped: hang`) means the reaper stopped a hung
gate run; it is not a test failure. CONTRIBUTING.md, "Pushing in this repository", has the
rest.

Install all three hook types once, then the provenance hooks. The order matters,
because `pre-commit install` refuses to run while `core.hooksPath` is set:

```bash
pre-commit install && pre-commit install --hook-type pre-push && pre-commit install --hook-type commit-msg
uv run vibey-gh install
```

`vibey-gh install` points `core.hooksPath` at `.githooks`. The tracked shims there
(`pre-commit`, `commit-msg.local`, `pre-push.local`) chain back to the framework
through `git rev-parse --git-common-dir`, so one install covers the main checkout
and every linked worktree (`git worktree add`). If a shim prints
`warning: the pre-commit framework's <stage> hook is not installed`, the commit or
push went ahead but none of that stage's gates ran. Run them by hand before you push.

## The other CI jobs

`ci.yml` runs seven jobs on every push and PR to `develop`/`main`:

| Job | What it checks |
|---|---|
| `uv-lock` | `uv lock --check`. `gates`, `tools` and `tools-lint` depend on it. The lock carries vibey's own version, so a version bump without `uv lock` fails here first. |
| `gates` | The seven gates above, against a `postgres:17` service. `postgres-compatibility` additionally runs the database suite on PostgreSQL 14, 15, 16, 17, and 18. |
| `tools` | Each absorbed tenant's own suite on its own Python floors, plus, on its floor row, its own static gates from the row's `static` key: its mypy, `lint-imports` and bandit. agyloop, codexloop and vibey-skills also run their own strict docs builds (the `docs` key) (ADR-0022). |
| `tools-lint` | vibey-gh's own linters and its managed-automation drift check. |
| `image` | Builds `deploy/docker/Dockerfile` for amd64 and arm64 and asserts each `Image contract - …` step: the entrypoint runs, it runs as non-root uid 10001, it has no compiler/uv/pip, migrations ship in the image, and every console script is on PATH. |
| `chart` | Render-only: `deploy/helm/golden/render.sh` runs `helm lint --strict` and `helm template` for each profile (defaults, `ollama.enabled`, the GPU + gptossloop wiring with qwenloop switched on beside it, and the KEDA query unbound and bound to a project) and diffs each render against its committed golden under `deploy/helm/golden/`, with helm pinned. After an intended chart change, regenerate with `deploy/helm/golden/render.sh --update`. |
| `cluster-smoke` | Helm install of `deploy/helm/vibey` on minikube and four cluster contracts: a projectless worker parks instead of crash-looping, the worker picks up a project created in-cluster, the KEDA ScaledObject reconciles against real Postgres, and a worker drains promptly on SIGTERM (ADR-0025, ADR-0026). |

Other workflows also gate a merge: `provenance.yml` (runs on every push and PR),
and `pr-automation.yml`, which re-evaluates a PR each time `CI` or `Provenance`
completes (`[pr_automation] scan_workflows` in `.vibey-gh.toml`) and hands ready
PRs to `merge-train.yml` (see the `vibey-releasing` skill).

## Workspace tenants: their own checks

The tenants under `src/vibey_runners/` and `src/vibey_tools/` keep the gates they
arrived with (ADR-0021, ADR-0022). The root `mypy`, `bandit` and coverage gates
cover `src/vibey` only. Run a tenant's checks from its own directory, with plain
pip and a Python at its floor — every tenant now shares the 3.12 floor, so the
matrix exercises the common 3.12–3.14 range. Plain pip knows nothing
about `[tool.uv.sources] workspace = true`, so a tenant that needs a sibling
installs that sibling **from the tree first** -- no family package may be
requested from an index, because none of them is published any more (ADR-0037).
These are the `tools` and `tools-lint` commands, verbatim:

```bash
# vibey-gh (CI: Python 3.12, 3.13, 3.14; 100% branch floor in its own addopts)
cd src/vibey_tools/gh
pip install -e ".[dev]"
python -m pytest -q
python -m black --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh

# vibey-skills (CI: Python 3.12, 3.13, 3.14)
cd src/vibey_tools/skills
pip install -e .
python3 tools/validate_manifests.py && python3 tools/check_links.py \
  && PYTHONPATH=src python3 -m unittest discover -s tests

# vibey-bootstrap (CI: Python 3.12, 3.13, 3.14). It imports vibey_gh, so install that first.
cd src/vibey_tools/bootstrap
pip install -e ../gh && pip install -e ".[test,all]"
pytest test/ -m "not integration" --cov=vibey_bootstrap --cov-report=term

# claudeloop (CI: Python 3.12, 3.13, 3.14 -- the common library floor)
cd src/vibey_runners/claude
pip install -e ../common && pip install -e ".[dev]"
pytest tests/domain --cov=claudeloop.domain --cov-branch --cov-report=term-missing --cov-fail-under=100
pytest tests/application --cov=claudeloop.application --cov-branch --cov-report=term-missing --cov-fail-under=100
pytest tests/infrastructure -n auto --maxprocesses=8 --cov=claudeloop.infrastructure --cov-branch --cov-report=term-missing --cov-fail-under=100
pytest tests/cli -n auto --maxprocesses=8 --cov=claudeloop.cli --cov-branch --cov-report=term-missing --cov-fail-under=100

# codexloop (CI: Python 3.12, 3.13). cursorloop and agyloop are the same with the package
# name swapped, minus `pip install -e ../common` (neither depends on it) and with
# `pytest tests` in place of `pytest -q`; agyloop then ends on `pytest -m system`.
cd src/vibey_runners/codex
pip install -e ../common && pip install -e ".[dev]"
pytest -q --cov=codexloop --cov-branch --cov-report=
coverage report --include='src/codexloop/domain/*' --fail-under=100
coverage report --include='src/codexloop/application/*' --fail-under=100
coverage report --include='src/codexloop/infrastructure/*' --fail-under=100
coverage report --include='src/codexloop/cli/*' --fail-under=100

# qwenloop (CI: Python 3.12, 3.13, 3.14; its floor is already in its addopts)
cd src/vibey_runners/qwen
pip install -e ".[dev]"
python -m pytest -q
```

vibey-gh's suite drives real git history and shells out to `gh`, so it needs
both on `PATH` and a full clone -- a shallow one fails. It does **not** need
`uv`: the single test that drives a real `uv lock` is marked `network`, below.

Tests that leave the machine (a real package index, a real remote) carry
`@pytest.mark.network` and are **skipped unless `VIBEY_GH_NETWORK_TESTS=1`**.
Marker and variable are two halves of one mechanism -- the marker declares, and
`test/conftest.py` does the skipping -- so a plain offline `python -m pytest`
reaches the package's 100% branch floor with no flag to remember, and a run that
reports `4 skipped` is correct rather than degraded. Every branch a `network`
test touches must also be reachable offline, or that floor fails. Where an index
is reachable, ask for them by name:

```bash
cd src/vibey_tools/gh
VIBEY_GH_NETWORK_TESTS=1 python -m pytest -q -m network --no-cov
```

CI runs that on one matrix row with `continue-on-error`: it reports on somebody
else's service, so it must never gate a merge.

The runners (`src/vibey_runners/{claude,codex,cursor,agy,qwen}`) carry their own
`tests/`, ruff, mypy and import-linter configuration in their `pyproject.toml`.
Since 2026-09-15 the root `tools` matrix runs all five -- thirteen rows of it -- so a
runner regression turns the `tools` job red. It reports rather than blocks: `tools`
is not named in `required_checks` in `.vibey-gh.toml`, and no tools row ever has been.
Read a runner's `[tool.pytest.ini_options]` before running anything by hand. agyloop's
and cursorloop's addopts exclude `live` and `system` tests (agyloop's system harness is
re-selected with `pytest -m system`, which is what the matrix does), and only qwenloop's
addopts carry a coverage floor. The other four deliberately leave `--cov=` and
`--cov-fail-under` out, because pytest-cov unions every `--cov=` it sees and one baked
in there would widen the explicitly-scoped per-layer runs back out to the whole package
-- so for them a bare `pytest` runs the tests but enforces no floor. Use the commands
above, which are their own.

## Where work lives, and how often it is saved

Keep every clone and worktree on storage a reboot keeps (sub-doctrine 10.h, ADR-0057). Never
use `/tmp`, `/private/tmp`, `/var/tmp`, `/var/folders`, `/dev/shm`, `/run/user` or `$TMPDIR`:
the OS empties them. On 2026-09-24 a reboot emptied `/private/tmp` mid-storm and took every
uncommitted worktree, measurement and draft with it. Worktrees go in the storm home:
`VIBEY_STORM_HOME`, else `~/git/vibey-storm` on macOS, `$XDG_DATA_HOME/vibey/storm` (else
`~/.local/share/vibey/storm`) on Linux.

```bash
python3 docs/plans/qwenstorm-3.0.0/tools/storm_durability.py status   # durable or not
git worktree add "$(python3 docs/plans/qwenstorm-3.0.0/tools/storm_durability.py worktree fix-x)" \
  -b fix/x origin/develop
```

- Commit as soon as a change is coherent, not when it is finished.
- Push work in progress to a draft PR (`gh pr create --draft`) at least every 30–45 minutes;
  the merge train never merges a draft, and the pre-push gates still run.
- A long measurement writes each step as it finishes and resumes (`StepJournal` in
  `docs/plans/qwenstorm-3.0.0/tools/storm_checkpoint.py`).
- The storm tools refuse volatile storage with exit 78 and name the key to change.
  CONTRIBUTING.md, "Where your work lives", has the rest.

## What each gate catches

| Gate | Catches |
|---|---|
| ruff check | Unused imports, undefined names, syntax errors, anti-patterns |
| ruff format | Inconsistent code style |
| mypy --strict | Type errors, missing annotations, `Any` usage |
| pytest (per-layer 100%) | Untested branches, logic errors, regressions |
| lint-imports | Onion violations, forbidden imports |
| bandit | Security issues, hardcoded secrets, insecure patterns |
| pip-audit | Dependency CVEs |
