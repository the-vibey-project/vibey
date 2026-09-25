# vibey-testing (Antigravity mirror of `.claude/skills/vibey-testing/SKILL.md`)

# vibey testing

## Coverage floors — not targets

Every layer carries a **100% branch coverage floor**, enforced in CI as one
test run and four per-layer reports:

```bash
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
uv run coverage report --include='src/vibey/application/*' --fail-under=100
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
uv run coverage report --include='src/vibey/cli/*' --fail-under=100
```

The build **fails** if any layer drops below 100%. This is not aspirational
(ADR-0023). `tui/` has tests under `tests/tui/` but no floor of its own.

## Running locally

The default `addopts` are `-m 'not paid' -n auto --maxprocesses=8`: paid tests are
excluded and everything runs under pytest-xdist.

**Every session needs Postgres**, including a run of pure domain tests:
`tests/conftest.py` connects at `pytest_configure`, migrates a
`vibey_test_template` database once, clones it into a database per xdist worker,
and repoints `VIBEY_TEST_DATABASE_URL` at the clone. The role in the DSN must be
able to connect to the `postgres` database and run `CREATE DATABASE`.

For a local server, `vibey install --postgres` installs/starts PostgreSQL 18
through Homebrew, apt, or dnf. The runtime floor is PostgreSQL 14; CI's
`postgres-compatibility` matrix runs the database suite on every current major
14 through 18.

The template is migrated from the running checkout and then reused, so two
checkouts whose `migrations/` differ -- parallel worktrees, one adding a migration
-- must not share it: set `VIBEY_TEST_TEMPLATE_DB` to a name of the checkout's own
(default `vibey_test_template`).

A killed run cannot drop its databases, so the harness reaps them: each session holds a lock
on its database while it lives and marks it with the process that created it, and every run
drops, in the background, the test databases no live session holds (`tests/db_reaper.py`). A
database is kept while its lock is held or while that process is alive on this machine. See what would go with
`uv run python -m tests.db_reaper --dry-run`; `VIBEY_TEST_REAP=0` turns the reap off.

```bash
export VIBEY_TEST_DATABASE_URL="postgresql://$(whoami)@localhost:5432/vibey_test"
uv run pytest tests/domain -p no:cacheprovider            # one area, xdist on
uv run pytest tests/domain -o addopts="" -m "not paid"    # serial, for a debugger
```

Overriding `addopts` also drops the paid-test exclusion; keep `-m "not paid"`.
CI uses `postgresql://vibey:vibey@localhost:5432/vibey_test` on a `postgres:17`
service for the main gates, and the `postgres-compatibility` matrix exercises
PostgreSQL 14, 15, 16, 17, and 18.

## Test tree

| Path | What lives there |
|---|---|
| `tests/domain/` | Pure unit and Hypothesis property tests, plus `test_domain_purity.py` |
| `tests/application/` | Use cases and handlers against fakes |
| `tests/infrastructure/` | Adapters; `db/` runs against real Postgres, `engines/` holds argv golden files and classifier tests (the fixtures live in `infrastructure/engines/classify.py`) |
| `tests/cli/`, `tests/tui/` | Typer commands; the Textual dashboard |
| `tests/fakes/` | Shared fakes and `test_port_parity.py`, which fails when a fake misses a Protocol method |
| `tests/contracts/` | The same contract run against a fake and the Postgres implementation |
| `tests/live/` | The two-mode live harness (ADR-0030): faked mode (`live`; `ScriptedEngine` and scripted stand-in binaries, no model calls) and paid mode (`paid`; real binaries against real models) |
| `tests/system/` | Delivery-stage-set and full-worker end-to-end tests (`system`) |
| `tests/meta/` | Repository invariants: `test_adr_counts.py`, `test_container_context.py` |
| `tests/test_bootstrap.py` | The composition root |

`tests/meta/test_adr_counts.py` fails when an ADR is added without updating the
"(N ADRs" count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md` and
`docs/index.md`, when ADR numbering has a gap, or when an ADR is missing from the
`properdocs.yml` nav. `tests/meta/test_container_context.py` fails when
`.dockerignore` excludes a tracked file the Dockerfile copies.

## Tenant suites

The root `pytest` (`testpaths = ["tests"]`) never runs the workspace tenants'
tests. Each has its own suite and configuration: `src/vibey_tools/gh/test/`,
`src/vibey_tools/bootstrap/test/`, `src/vibey_tools/skills/tests/`, and
`src/vibey_runners/<engine>/tests/`. See the `vibey-quality-gates` skill for the
exact commands and which of them CI runs.

## Postgres integration tests — never mocked

All `tests/infrastructure/db/` tests run against a **real ephemeral Postgres**
via the `migrated_pool` and `project_id` fixtures in
`tests/infrastructure/db/conftest.py`. Every test drops and recreates the
`public` schema before running.

**Why real Postgres, never mocked:** because `SELECT ... FOR UPDATE SKIP
LOCKED` semantics are the thing under test. A mock cannot faithfully represent
concurrent worker contention, lease expiry, or the reaper reclaiming expired
leases. See ADR-0002.

Set `VIBEY_TEST_DATABASE_URL` (see "Running locally"); without it the root
conftest falls back to `postgresql://<current user>@localhost:5432/vibey_test`.

## Property tests — the safety-critical invariants

**Rotation fairness** (`tests/domain/test_rotation.py`):
- Over any eligible set and any weight vector, every engine is selected at
  least once per `sum(weights)` selections (no starvation).
- Determinism: identical candidate state produces identical selection.
- Exclusion honored: an engine in `requirement.excluded` is never returned.

**No-loss gate soundness** (`tests/domain/test_noloss.py`):
- For any ledger and any brief that *omits* owed items, the gate names each
  omitted item under its own rule, and nothing else. The expected brief comes
  from the independent reference model in `tests/domain/test_noloss_reference.py`
  -- never from `open_items`, which the gate itself uses -- over ledgers with
  arbitrary ids, interleaved kinds, answers, resolutions and supersedes, several
  verdicts, and a presentation order unrelated to seq.
- The suite is marked `noloss`. `gates` runs it at Hypothesis' default 100
  examples; the required CI check `No-loss property suite (10,000 examples)`
  runs `uv run pytest -m noloss --hypothesis-profile=noloss
  --hypothesis-show-statistics -p no:cacheprovider`. Never add a per-test
  `@settings(max_examples=...)` there: it overrides the profile.
- These files are protected (`.github/CODEOWNERS`, `[merge_train]
  protected_paths`): the merge train will not merge a change to them.

**Credits-never-have-a-deadline** (`tests/domain/test_circuit.py`):
- `schedule_probe(CreditsExhausted(...), ...)` can only return a `BackoffProbe`,
  never a `DeadlineProbe`. This is the single most important property test in
  the codebase.

**Deterministic brief is provably lossless** (`tests/domain/test_briefing.py`):
- `build_deterministic_brief()` (the floor brief producer) is built from the
  same projections (`domain/projections.py`) that `domain/noloss.py::verify()`
  checks -- its decisions from `open_items` itself -- so it passes the gate by
  construction. Property tests over the same adversarial ledgers assert
  `verify(...).ok` and that it carries exactly what the reference model says
  is owed.

## The chaos test

`tests/infrastructure/db/test_chaos.py` runs 8 concurrent asyncio "workers"
against real Postgres, each randomly abandoning a claimed job mid-flight (the
observable effect of a kill: no ack, no nack, lease just expires), with a
concurrent reaper reclaiming expired leases. It proves the property that
matters: **zero double-commit, zero lost jobs** across 500 jobs.

Delivery is at-least-once. On a loaded machine claim-to-ack outlives the 150 ms
lease, the job is reaped and claimed again, and the work runs twice. The ack is
fenced on `lease_owner`, so the stale ack is refused and exactly one ack per job
returns `True`. The test therefore counts *committed* executions (acks that
returned `True`), fails if any job is committed twice or never, and only prints
the raw execution count (`pytest -rP` shows the tally). Don't lengthen the lease
to quiet a failure: that hides the fence the test exists to exercise.

This is a scoped-down substitute for the implementation plan's literal spec
(8 OS processes, `SIGKILL` every 2s via testcontainers) — no Docker daemon
was available in the build environment. If you have Docker available, upgrade
this test to the real testcontainers version.

## The flagship end-to-end test

`tests/infrastructure/db/test_end_to_end_forced_rotation.py` is the **single
most important test in the repo**. It runs `ScriptedEngine` A through a
simulated 40-turn run, hits `CreditsExhausted`, builds the deterministic
floor brief from the real (Postgres-persisted) ledger, runs it through the
actual gate escalation state machine, and proves every closable id open when
A died is verbatim in engine B's first seed prompt — with a negative control
proving the gate would have caught a dropped item.

Read this test before touching `noloss.py`, `briefing.py`, or
`handoff_orchestration.py`.

## Markers

- `@pytest.mark.integration` — requires Postgres (auto-applied to everything
  under `tests/infrastructure/db/` by conftest).
- `@pytest.mark.slow` — takes more than a couple seconds.
- `@pytest.mark.system` — delivery-stage-set end-to-end system test.
- `@pytest.mark.live` — tests against real loop binaries in faked mode (scripted
  agents, no model calls), in `tests/live/`.
- `@pytest.mark.paid` — real models, real API keys, real money. **Excluded by
  default**; opt in with `-m paid`.
