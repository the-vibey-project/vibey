## Title
docs(skills): the vibey-quality-gates skill names the Arch Linux and macOS gates, the service-free default run, the harness pre-push and every cluster contract

## Why
The `vibey-quality-gates` skill predates 8.e, 8.h and the fakes standard (`issue-audit/gaps.md`
M3, lines 639-642). In `.claude/skills/vibey-quality-gates/SKILL.md`:
- `:64-66` says "The test run needs a reachable Postgres even for a subset" (false after
  `fakes-ci-no-services`);
- `:115-120` lists a plain pre-push suite plus a separate coverage run (after
  `harness-T28-route-flip`'s T18, the push sends one harness request carrying the four gates);
- `:139` says `ci.yml` "runs seven jobs", and `:146` says `gates` runs "against a `postgres:17`
  service", with no word of `gates (Arch Linux)` or `gates (macOS)` (8.h,
  `src/vibey_tools/gh/docs/doctrines.md:326-333`; `gap-ci-arch-gates`, `gap-ci-macos-gates`);
- `:151` says `cluster-smoke` has "four cluster contracts". At HEAD `4317cff6` it already has
  five (`.github/workflows/ci.yml:904-993`), and `chart-operator-forgejo-p1`/`-p2` and
  `rmq-r32-ci-rabbitmq` add more (`specs/chart-operator-forgejo-p2.md` "For the docs wave").
The same text is in `.agents/skills/vibey-quality-gates/SKILL.md`, `.cursor/rules/vibey-quality-gates.mdc`
and `.agent/rules/vibey-quality-gates.md`; they must stay identical below their headers.

## Required behaviour
1. Read the facts from the tree:
   - `grep -n "name: gates" .github/workflows/ci.yml` shows the display names of the gate jobs
     (expect `gates (Arch Linux)` and `gates (macOS)` beside `gates`). If either is missing,
     STOP and report BLOCKED.
   - `CONTRACTS` = the output of `grep -o "name: Contract - .*" .github/workflows/ci.yml | sed 's/name: Contract - //'`,
     in file order, joined with `; `.
   - `grep -n "vibey test run" .pre-commit-config.yaml` shows the pre-push harness request.
     If it prints nothing, keep the old pre-push bullets (skip pair P below) and report it.
2. Write `.qwenstorm/skill_edit.py` and run it. For each of the four files it applies every
   pair below with `assert text.count(old) == 1`, then writes the file (EDITING-RULES rule 2).
   Pairs (copy each `old` from the `.claude` file; `CONTRACTS` is filled in by the script from
   step 1's command, run with `subprocess`):
   - G4. `old`:
     ```
     The test run needs a reachable Postgres even for a subset: `tests/conftest.py`
     clones a migrated template database per xdist worker at session start. See the
     `vibey-testing` skill.
     ```
     `new`:
     ```
     The default run needs no service: every seam has an in-memory fake, and tests
     that need PostgreSQL or RabbitMQ are the opt-in `integration` tier. See the
     `vibey-testing` skill. `tests/meta/test_raw_sql_budget.py` fails on any new raw-SQL
     site outside the two exemptions (`LISTEN` and the migrator's scripts); persistence
     goes through the ORM seam.
     ```
   - P. `old`: the five lines from `- The plain parallel test suite (` through
     `- Per-layer 100% coverage gates (pytest --cov + four reports)` (lines 115-119: the
     suite's two lines, then `- mypy --strict`, `- lint-imports` and the coverage line).
     `new`:
     ```
     - The suite, run once as one test-harness request that carries the four per-layer
       100% coverage gates (`uv run vibey test run --gate …`; 8.e, ADR-0045)
     - mypy --strict
     - lint-imports
     ```
   - J. `old`: `` `ci.yml` runs seven jobs on every push and PR to `develop`/`main`: ``
     `new`: `` `ci.yml` runs these jobs on every push and PR to `develop`/`main`: ``
   - GATES. `old`: the table row that starts `` | `gates` | The seven gates above, against a `postgres:17` service. ``
     (the whole line). `new`:
     ```
     | `gates`, `gates (Arch Linux)`, `gates (macOS)` | The seven gates above, on Ubuntu, Arch Linux and macOS (sub-doctrine 8.h: every change is proven on both default operating systems). The default tier starts no service. `postgres-compatibility` runs the `integration` tier (`-m "integration and not paid"`) on PostgreSQL 14, 15, 16, 17 and 18. |
     ```
   - SMOKE. `old`: the table row that starts `` | `cluster-smoke` | `` (the whole line). `new`:
     ```
     | `cluster-smoke` | Helm install of `deploy/helm/vibey` on minikube. Each `Contract - …` step asserts one cluster behaviour: CONTRACTS (ADR-0025, ADR-0026). |
     ```
     with `CONTRACTS` replaced by step 1's joined list.
3. The script prints the file names it edited. Every file must be edited; an assertion
   failure means a mirror drifted: STOP and report the file and the pair.

## Where to change
- `.claude/skills/vibey-quality-gates/SKILL.md`, `.agents/skills/vibey-quality-gates/SKILL.md`,
  `.cursor/rules/vibey-quality-gates.mdc`, `.agent/rules/vibey-quality-gates.md`, by the script only.

## Acceptance criteria
- [ ] `grep -c "four cluster contracts\|runs seven jobs\|reachable Postgres even for a subset"` prints 0 in each of the four files.
- [ ] Each of the four files names every step `grep -o "name: Contract - .*" .github/workflows/ci.yml` prints.
- [ ] `grep -c "gates (Arch Linux)"` prints at least 1 in each of the four files.
- [ ] `git diff` changes no line above each file's `# vibey quality gates` title and no SD-01 line.
- [ ] `uv run pytest -q -p no:cacheprovider -n 0 tests/meta` passes.

## Tests to write first (TDD)
None new: the tree-parity and SD-01 carriage meta-tests hold the four trees.

## Checks the lane must run (all must pass)
    grep -n "name: gates\|name: Contract - " .github/workflows/ci.yml
    grep -n "vibey test run" .pre-commit-config.yaml
    python3 .qwenstorm/skill_edit.py
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta
    git diff --stat

## Out of scope
- The tenants' command block of the skill (a runner renamed by ADR-0046 is that lane's).
- CI itself, other skills, CONTRIBUTING.md.

Commit as `docs(skills): the vibey-quality-gates skill names the Arch Linux and macOS gates and every cluster contract`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
