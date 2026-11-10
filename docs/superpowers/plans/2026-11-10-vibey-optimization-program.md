# vibey Optimization Program Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make vibey measurably better (quality first, performance second), make its CI
cheaper and faster, and finish the four workstreams already under way: the security audit,
the sovereign model study, the Krypton chat and the Feynman docs.

**Architecture:** A master plan made of twelve sub-plans (SP0 to SP11). Each sub-plan is
written in full with superpowers:writing-plans immediately before it starts. Each one lands
as its own series of PRs through the merge train. This document fixes the order, the
evidence found, the decisions and the acceptance checks. Every change follows CDD: SDD for
intent, TDD for checks, then converge against the tracked repository. It also follows the
CLAUDE.md non-negotiables.

**Tech Stack:**
- Python 3.12+ uv workspace: asyncpg, PostgreSQL 14 to 18, Starlette hub, Textual TUI
- Ollama and llama.cpp
- TypeScript: `@vibey/core`, the Expo app, the VS Code extension
- C/GTK4 desktop, built with meson
- GitHub Actions on a public repository on the Free plan

**Spec:** this document and the operator's brief of 2026-11-10 (see Context).

**Saved to:** `docs/superpowers/plans/2026-11-10-vibey-optimization-program.md`, on approval.
It is committed on its own `docs/` branch through the merge train.

## Context

Scanned 2026-11-10 at `origin/develop` `010ebc70` plus PR #1866. Sources:
- three read-only scans: quality, performance, CI with measured run data
- one independent critique of the draft
- the earlier session scans

Every item below has a file reference or a measurement. Two critique claims were re-verified
by hand: the telemetry leak and the duplicate index.

The operator asked for four things:
1. Every way to optimize the codebase, quality first and then performance. Use the vibey
   skills as the yardstick and leave no stone unturned.
2. Workflows optimized for cost and time. A feature PR into `develop` should run far less
   than a promotion PR from `develop` into `main`.
3. The four planned workstreams (D security, B model study, A Krypton, C docs), carried in.
4. A hold on model tests. The calibration run that was already going stopped by itself on a
   busy host after 3 of 10 trials (see SP9).

**Headline findings:**
- **Correctness:**
  - The events tail drops half-written lines.
  - The develop channel has failed to publish 19 times out of 20.
  - Every scheduled workflow is disabled.
  - The merge queue has had zero runs in 17 days.
  - In-process telemetry grows without bound.
  - One codexloop 100% coverage floor is hollowed out by 30 `no cover` pragmas.
- **Quality:**
  - 13.7k lines of storm tools and 31k lines of scripts sit outside mypy, and in part outside ruff.
  - Ollama has 11 hand-written clients and secrets have about 9 redactors.
  - About 2,000 lines of orphaned modules exist.
  - 168 functions exceed complexity 10.
  - About 320 suppressions carry no stated reason.
  - 4 checks are required on `develop`, so `tools`, `postgres-compatibility`, `desktop` and `image` can fail and still merge.
- **Performance:**
  - The whole ledger is read at 42 call sites, some of them once per second.
  - Each append costs two round trips.
  - The lane feed walks the filesystem every second.
  - `num_ctx` changes per request.
  - Each DB test re-runs 22 migrations (876 uses).
- **CI:**
  - Billing is $0. The real costs are queueing (20 jobs, 5 macOS) and wall time.
  - About 7,500 job-min/week.
  - All 45 cells run on every PR.
  - The open promotion PR re-runs the full matrix on every develop push.

## Global Constraints

- Quality is never traded for speed unless the task says why it has to be. A performance
  change ships with:
  - proof that behaviour is identical (the existing suite plus a test of the changed path)
  - a deterministic measure where one exists: query count, syscall count, import time,
    memory after N jobs
  - wall-clock before and after numbers, taken only on a quiet host
- Non-negotiables (CLAUDE.md):
  - domain purity
  - the ledger is append-only
  - credits exhausted is not a rate limit
  - jobs are idempotent under replay
  - a worker never blocks on a human
  - new and changed classes get an interface
  - TypeScript only
  - everything-as-code and configurable
  - dogfood the family: reuse first, and write a capability-gap reason at any site that cannot
- 100% branch coverage on `domain/`, `application/`, `infrastructure/` and `cli/`.
- Every structural rule gets a **ratchet**: a `tests/meta` census whose baseline is a TOML
  number that may only fall.
- Required checks change only through `.vibey-gh.toml` and its reconciler. A rendered
  workflow changes at its template (`src/vibey_tools/gh/vibey_gh/templates/workflows/`).
- `ci.yml` has a single owner: every change to it is queued into SP1.
- Migrations are only ever added, never edited.
- Governance canon changes go in a separate PR that the operator merges.
- Work lives in the storm home. Draft PRs are pushed every 30 to 45 minutes. Commits use
  Conventional Commits. `git commit` and `git push` run in the foreground.
- No model tests run until SP9. They then run on a quiet host with no other sessions.

## Review Focus

1. A narrowed ledger read returns exactly what the full read plus the Python filter did,
   including across a superseding correction event.
2. On every PR, the aggregate CI check fails when any job fails, is cancelled, or the `plan`
   job fails. It never goes green with nothing run. A docs-only PR never hangs on a pending
   required check.
3. A rounded `num_ctx` never truncates a prompt that the unrounded value would have fit.
4. The events tail never drops a half-written last line and never emits one twice.
5. A per-test database reset leaves no state behind: sequences, advisory locks, LISTEN
   channels, rows. That holds after a failed test too, and an application role can never
   use the owner's TRUNCATE bypass.

---

## Order

SP0 → SP1 → SP2 → SP3 → SP4 → SP5 → SP6 → SP7 → SP8 → SP9 → SP10 → SP11.

SP3 (security) runs unattended in parallel from the start. Two writers never touch the same
files. Hot files keep a fixed order:
- `hub/app.py`: SP5 split, then SP8 (P5/P6), then SP10 (A1).
- `cli/main.py`: SP5 split, then SP8 (P12).
- `ollama_chat.py`, `fit.py`, `slots.py`: SP6 (canonical client), then SP9 (P7/P8).

## SP0 Baseline and correctness (first)

- [ ] **Baseline.** Add a `vibey-gh ci-cost` command, which reuses the Actions readers in
  `branch_health.py` and `review_outcome.py`. It reports job-min per tier, macOS minutes,
  queue time and wall p50/p90. Commit its baseline before any CI change.
- [ ] **Events tail.** `infrastructure/engines/loop_process_adapter.py:496-500` re-reads the
  whole file every 0.5 s. It sets `seen_lines = len(lines)` over an incomplete last line, so
  that line is lost.
  - Fix: tail by byte offset and hold back a partial line.
  - Test: Review Focus 4.
- [ ] **Telemetry leak.** In `infrastructure/otel.py`, `TelemetryTracer._spans` (:53, :89) and
  `TelemetryMetrics` (:172-180) grow forever, and nothing else reads them. They are on by
  default (`bootstrap.py:572-575`).
  - Fix (Decision 4): the real OpenTelemetry API through `vibey_bootstrap.tracing`, with the
    OTLP exporter declared in config and off by default.
  - Test: worker memory stays bounded after N jobs, and nothing is exported while the
    exporter is unset.
- [ ] **Develop never publishes.** 19 of 20 `Release` runs on develop fail at "Publish to
  TestPyPI" (`vibey-engine.yml`), so Release surfaces and GitHub Release are skipped too.
  - Fix: read the log and fix the root cause.
  - Make the failure loud: a branch-health signal plus an issue.
- [ ] **Disabled workflows.** PR evaluate, Merge train, Promote and 11 scheduled workflows are
  `disabled_manually`.
  - Record why for each one.
  - Re-enable the wanted ones behind the release-binaries "unchanged since the last run, so
    skip" guard.
  - Retire the rest in code.
- [ ] **Merge path.** There have been 0 `merge_group` runs in 17 days. The queue applies only
  after a reconcile (`.vibey-gh.toml:229`), and the admin role is in `bypass_actors` (:213).
  Decision 2: enforce the queue on `develop` and remove the admin bypass there, then
  reconcile. Prove it with one PR that lands through a `merge_group` run.
- [ ] **Hollow floors.**
  - codexloop `appserver/gateway.py` has 30 `pragma: no cover`: test each path or record why
    it is unreachable.
  - vibey_bootstrap's floor is measured by line: make it branch.

## SP1 CI pipeline (sole owner of `ci.yml`)

**Measured:**
- 45 cells per run (40 Linux, 5 macOS), about 77 job-min per run.
- PR wall time p50/p90 is 11.2/26.6 min; push is 19.8/35.5 min. One queue wait was 19.9 min.
- The promotion PR re-ran 63 of 81 develop pushes. #1704 stayed open 11 days, about 64 full runs.
- 27 of 77 PR runs failed, after paying for every cell.
- There are no path filters and no fail-fast ordering. Only 2 of 17 jobs have timeouts.
- `ci.yml` has no top-level `permissions:`.
- 90 of 259 `uses:` lines are pinned by tag, including `pypa/gh-action-pypi-publish@release/v1`
  in the publishing jobs.
- Tenant suites `pip install` without a lock (`ci.yml:314-548`, :733).
- The root `properdocs build --strict` runs only after a release (`release-surfaces.yml:426`).

**Tiers.** A `plan` job reads a TOML change-area map through a tested vibey-gh command, not
inline bash. The map yields `full` when `ci.yml`, `pyproject.toml`, `uv.lock`,
`.node-version` or `package-lock.json` changed. Jobs skip through job-level `if:`. There is
never a workflow-level `paths:` filter.

| Tier | Runs | Saving per week |
|---|---|---|
| (a) feature PR into develop | `uv-lock`, `lint`, `gates`, `noloss`, tools on 3.12 only, `tools-lint`, PG 14 and 18. By path: vscode, core, app, krypton-app, desktop (Ubuntu), chart and amd64 image, docs strict build | about 3,800 job-min, about 600 macOS min |
| (b) merge_group | tier (a) without path filtering | proves a merge is green |
| (c) push to develop | `uv-lock`, `gates`, `noloss`, Release; plus a nightly extended run, unless the tip has not changed since the last green run (per Decisions 1) | about 900 net |
| (d) promotion PR, develop to main | full matrix, all Python and PG versions, desktop x4, both vscode OSes, image amd64 and native arm64, cluster-smoke, chart, corpus validation, lowest-direct dependency run, mutation and fuzz smoke | up to 2,000 while the PR is open |
| (e) push to main | `uv-lock`, `gates`, `noloss`, Release chain | about 70 |
| (f) schedules | skip-if-unchanged guard on every schedule; any failure opens an issue (vibey-gh `issue_automation`) | protects future load |

**Tasks, in order:**
- [ ] **CI-A Aggregate required check.**
  - A `ci-result` job that `needs:` every job, runs `if: always()`, and fails on any failure,
    cancellation or failed `plan`.
  - It becomes the single required check, through `.vibey-gh.toml` and then reconcile.
  - A meta test proves every job is in its `needs`. Review Focus 2.
  - This replaces the fixed-name VS Code workaround.
- [ ] **CI-B `lint` job first.** It runs `uv lock --check`, ruff, format, `mypy --strict`,
  lint-imports, the TypeScript artifacts, corpus-index, actionlint and zizmor. Every heavy
  job `needs: lint`. Move those steps out of `gates` (:124-137).
- [ ] **CI-C Hygiene ratchets.**
  - `timeout-minutes` on every job, declared in TOML.
  - A top-level `permissions:` in every workflow.
  - Actions pinned by SHA and Docker bases by digest (`deploy/docker/Dockerfile:30,155`).
  - pre-commit hook repos pinned by SHA.
- [ ] **CI-D Locked tenant installs** from `uv export --frozen` with hashes. Add a nightly
  latest-dependency canary and a lowest-direct run at promotion.
- [ ] **CI-E Strict docs build on PRs**, by path. It must land before SP11.
- [ ] **CI-F Tiers and the change-area map.**
  - Update `tests/meta/test_tools_matrix_covers_every_package.py:66` and
    `test_postgres_support_matrix.py:15-17` to read the union of the tiers.
  - Reword the CI paragraph in CLAUDE.md at its source, `docs/agents/instructions.toml`.
- [ ] **CI-G One promotion run per attempt.** `vibey-gh promote` opens the PR only when it is
  ready (template `promote-to-main.yml`).
- [ ] **CI-H Shard the root suite three ways.** Upload `.coverage.*` as artifacts; one combine
  job computes all four floors in a single pass, so P15 lands here. Run the vibey-gh suite
  with `-n auto` once git-fixture isolation is proven.
- [ ] **CI-I Image built once.** Native arm64 on `ubuntu-24.04-arm` instead of QEMU;
  cluster-smoke loads the amd64 artifact. Attach a CycloneDX SBOM and attest it the way
  `release-binaries.yml:756` does.
- [ ] **CI-J Caches:** pip, Homebrew, ccache, prebuilt Arch/Fedora toolchain images, mypy,
  Tectonic (with per-figure hash skip and parallel compile, `release-surfaces.yml:234-243,535-543`).
- [ ] **CI-K De-duplicate:**
  - one Linux `advisory` job, not three
  - build the `.vsix` once and smoke-test it on macOS
  - one krypton-app test job
  - narrow provenance's push trigger, in its template
- [ ] **CI-L Re-measure** with `vibey-gh ci-cost` against the SP0 baseline, and record the
  result as evidence.

## SP2 Test depth (before any refactor or performance change)

- [ ] **Replay census.** About 13 of 18 `application/*_handler.py` have no replay test. Add one
  parametrised harness over every job kind: run the job, redeliver it, and assert the
  projections are unchanged.
- [ ] **Model-based state machines** in `tests/contracts`, for the job repository (claim, ack,
  nack, defer, bump, reap) and the ledger, each checked against an in-memory reference.
  Today only `tests/domain/test_queue_priority.py` uses `RuleBasedStateMachine`.
- [ ] **Round-trip properties:**
  - redacting twice equals redacting once
  - the digest is stable
  - row to event to row is lossless
- [ ] **Query-count fixture** using asyncpg `add_query_logger`. Budgets per append, per claim
  and per hub route are deterministic and ratcheted; P1 to P6 report against them.
- [ ] **Hub contract.**
  - Generate the TypeScript types from `docs/reference/hub-api.json`.
  - A meta test checks that every route and method used by the C client (20 hard-coded) and
    both TypeScript clients is in the document.
  - The app moves onto `@vibey/core`: `clients/app/src/core/hub-client.ts`, 549 lines,
    duplicates `transport.ts`.
- [ ] **RFC 9457 problem+json** for the 39 free-text hub errors (`hub/app.py:571,628,633,690`),
  with stable `type` codes from `scripts/error_catalog.py`. This fixes
  `packages/vibey-core/src/transport.ts:251` mapping 409 to three meanings.
- [ ] **Promotion and nightly tiers only:**
  - mutation testing (mutmut) on `domain/noloss.py`, `circuit.py`, `rotation.py`,
    `ledger_chain.py` and the redactor, with a ratchet on surviving mutants
  - Schemathesis against a test hub
  - libFuzzer on `kr-hub-client.c` and `kr-pairing.c`, under the existing ASan/UBSan build
  - real-process chaos: SIGKILL `vibey worker` subprocesses against Postgres
  - randomised test order
  - a reproducible-wheel check (build twice with `SOURCE_DATE_EPOCH`)
- [ ] **Hypothesis replay:** add `print_blob=True` to the noloss profile
  (`tests/conftest.py:46-51`) and upload `.hypothesis` when a run fails.
- [ ] **Test hygiene:**
  - 85 tests with no assertions get assertions or are deleted.
  - 20 coverage-fill files become behaviour tests.
  - Real sleeps (`tests/meta/test_storm_push_gate.py:902`, `test_db_reaper.py:494`, 21 in
    bootstrap) get injected clocks.
  - Duplicated fixtures move to `conftest.py`.

## SP3 Security (D; unattended, starts in parallel with SP0)

Correction to the original plan: bandit already runs on `claudeloop`, `codexloop`,
`qwenloop` and `vibey_bootstrap` (`ci.yml:357,425,460,538`). The gaps are elsewhere:
- **No bandit:** `vibey_gh` (:315), runners-common (:401-413), `vibey_skills`, `scripts/`, the storm tools.
- **No scanner at all:** the C client, the Expo app, the workflows.

- [ ] Run the Claude Security **scan codebase** job on the whole repository. Its report and
  patches stay on disk.
- [ ] Seed the threat model with these surfaces:
  - **Compiled-in email:** a personal email is compiled into `clients/desktop/src/app/kr-chat-page.c:631`.
  - **Spend-gate mismatch:** VS Code's gate check (`chat-view-provider.ts:319`) covers fewer
    kinds than `SPEND_GATE_KINDS` (`domain/hub_scope.py:155`).
  - **Hub auth:** pairing, the QR claim, device tokens (`hub/devices.py`) and the scoped
    `agent` principal.
  - **Engine sessions:** the `ChildEnvironment` allow-list.
  - **Unlocked installs:** tenant installs and tag-pinned publish actions (SP1 CI-C, CI-D).
  - **Workflows and releases:** release signing and `.github/advisory-exceptions.toml`.
- [ ] Triage with the operator. Each confirmed finding becomes an issue, or a private advisory
  per `SECURITY.md`, plus a fix PR with a regression test.
- [ ] Merge the ~9 redactors into one masking module and the 3 structlog setups into one
  (`vibey_bootstrap/logging/masking.py` is the candidate), with the round-trip property from SP2.
- [ ] **Durable gates:**
  - bandit on the uncovered packages
  - a `tests/meta` scan for secrets and personal data over tracked text: emails, home paths,
    hostnames, keys
  - the scan's designed exemption for the provenance header in every file

## SP4 Static-gate parity (Q1, Q5, Q10)

- [ ] Bring `docs/plans/qwenstorm-3.0.0/tools/` (39 files, 13.7k lines, including the mandatory
  `push_gate.py`) under ruff and mypy, as a package or through ruff's include.
- [ ] `scripts/` (31k lines): add `mypy scripts`, bandit and a scripts coverage floor.
- [ ] **Tenants to root strength:**
  - vibey_gh: mypy strict.
  - bootstrap: `disallow_untyped_defs` and a branch floor.
  - vibey-skills: coverage and mypy.
  - runners-common: measure every layer.
  - claudeloop: cover its own `bootstrap.py`.
  - Root: a fifth gate for `src/vibey/bootstrap.py` (1,424 lines); bring `tui/` under a floor
    or re-justify its exemption in ADR-0023's terms.
- [ ] `.importlinter`: a declare-only contract over all eight `interfaces` packages, generated
  from `find -name interfaces` so a new package cannot be missed.
- [ ] **Suppression census.** A `type: ignore`, `noqa`, `no cover`, `nosec` or broad
  `except Exception` needs a reason on the same line or the one before. Today 162, 50, 71
  and 39 have none, with 32 and 139 unexplained broad excepts. The baseline ratchets.
- [ ] RUF100 in `lint` (31 dead `noqa` today). Ratchet `Any` (70 root, 407 tenants).
- [ ] **TypeScript:**
  - a shared strict base tsconfig, with `exactOptionalPropertyTypes` (which ADR-0088 claims)
  - `noUnused*`, `noImplicitReturns` and `noFallthroughCasesInSwitch` for `clients/app`
  - typescript-eslint, or remove the dead disable at `clients/app/src/ui/kit.tsx:169`
  - review the 30 `as unknown as` casts
- [ ] **C:** in `meson.build`, re-enable `-Wunused-parameter` and `-Wmissing-field-initializers`,
  and add `-Wconversion`, `-Wnull-dereference` and `-Wvla`. Extend coverage to the GTK views.
- [ ] **Stale facts:**
  - the vibey-architecture skill's counts and claims
  - the `ci.yml:376-378` comment
  - dead `vibey-bootstrap` repository links (`vibey_bootstrap/__init__.py:26`, `bootstrap/docs/gen_pages.py:24`)
  - the testing skill's missing `tests/unit/`
  - the quality-gates skill's stale hook line (126-128)

  Fix all of these in all four agent trees, in one PR.

## SP5 Dead code and structure (Q3, Q4, Q6), before SP6 to SP8

- [ ] **Orphaned modules.** 18 `src/vibey` modules (about 2,000 lines) have no production
  importer, for example:
  - `db/orm_models.py` and `orm.py`, the only reason `sqlmodel` and `sqlalchemy` are runtime dependencies
  - `application/engine_failover.py`, `verdict_extraction.py`
  - `ledger/tier_*`, `domain/command_guard.py`, `domain/media.py`, `aws/adapter.py`

  Wire each one in `bootstrap.py` if a sub-plan here needs it; otherwise delete it, after
  checking entry points and dynamic loading.
- [ ] **Dependencies:** drop `tomli-w`, move `pyyaml` to dev, and drop the ORM's dependencies.
- [ ] **Complexity:** ruff C901 and PLR091x with a ratcheting baseline (168 over 10 today).
- [ ] **Splits:**
  - `hub/app.py:267` `build`: complexity 69, 504 lines; split into route modules.
  - `cli/main.py`: 2,919 lines, with `worker` at 64/731 and `run_worker` at 48; one module
    per command, which also sets up P12.
  - `vibey_gh/cli.py:1956` `main`: 1,153 lines.

  Each of the 12 classes over 500 lines (claudeloop `AutonomousRunner` 1,509, `Flattener`
  1,115, and so on) gets a split note.
- [ ] **ADR-0016 census per package.**
  - Today: 479 module-level functions in src/vibey, about 46 with a reason; codexloop 237 with none.
  - Value types are exempt (Decision 3): ADR-0016 amendment plus a proposed 9.b wording,
    in a canon PR the operator merges.
  - Hot spots: `cli/main.py` (49), `domain/config.py` (31), `claudeloop/bootstrap_ops.py` (46),
    `vibey_gh/cli.py` (64).

## SP6 Family consolidation (Q2, Q7)

- [ ] **One canonical Ollama client** in `vibey_runners.common`, dependency-free, replacing 11:
  - root: `ollama_models.py`, `ollama_chat.py`, `ollama_residency.py`
  - vibey_gh: `fit.py`, `slots.py`, `local_review.py`
  - qwenloop: `ollama_probe.py`, `inference.py`
  - claudeloop: `doctor_env.py`
  - scripts: `sovereign_probe.py`, `minimum_specs.py`, `model_quality_study.py`

  One default-URL key replaces today's 3 constants and the 11434 literal in 15 files.
  `OllamaChatClient`'s public behaviour stays, so A1 can reuse it.
- [ ] **`MemoryProbe` gains GPU memory.** Route `vibey_gh/slots.py:256,303`,
  `scripts/minimum_specs.py:407,430`, `scripts/host_health.py:1019` and
  `qwenloop/cli/app.py:921` through it.
- [ ] **Retry and backoff.** Move the 5 hand-written loops outside `domain/` to
  `vibey_bootstrap.retry`, or record the capability gap at each site.
- [ ] **Runner duplication.** The claude and codex runners share 1,862 identical lines across
  72 paths (`forecast.py`, `api/params.py`, `handoff_marker.py`, `verbosity.py`,
  `git_savepoints.py`). Move them into `vibey-runners-common`.
- [ ] **Hash chains.** Three exist; keep the domain one, and record a reason for any other that stays.
- [ ] **Bootstrap reuse.** src/vibey uses 5 of about 40 `vibey_bootstrap` modules. Adopt
  health, exceptions and tracing where SP0's telemetry decision lands.
- [ ] **Hard-coded values (12.c):**
  - `"claude-sonnet-5"` appears 6 times in `vibey_gh/config.py`
  - `"gpt-oss:20b"` is re-defaulted in 5 places outside `domain/sovereign_model.py:35`
  - the repository slug is written into 15 files
  - 86 literal timeouts
  - 30 ad hoc `tomllib` loads
  - `scripts/continuation_prompts.py:1055` hand-parses `.vibey-gh.toml`

  Each moves to its declared source, and a meta test forbids the literal anywhere else.

## SP7 Database (P1-P4, P14, pool, vacuum)

- [ ] **P1 Narrowed ledger reads.** Add `for_project(project_id, *, kinds, after_seq, cycle)`
  on the repository and its interface, over the `event_kind` index (`0013:56`). Move the 42
  `all_for_project` callers (`budget_source.py:112`, `engine_failover.py` if it survives SP5,
  `project_budget.py:135`, `tui/dashboard.py:105` every second, `cli/serve.py:212-220`).
  Review Focus 1, plus query-count budgets.
- [ ] **P2 One round trip per append.** `ledger_repository.py:111-136`: `append_event` returns
  `(seq, recorded_at)`, so the extra `SELECT *` and JSON re-parse go.
- [ ] **P3 Statement-level NOTIFY** with the highest seq, in a new migration replacing the
  per-row trigger in `0019`. Tests:
  - a multi-row transaction notifies once
  - a listener catches up after a dropped notification
- [ ] **P4 Indexes.**
  - Drop `event_project_seq`: it duplicates the primary key `(project_id, seq)` (`0013:33,55`),
    so every append writes both.
  - Drop `event_payload_gin` (`0013:58`) if `pg_stat_user_indexes` confirms it is unused and
    no code issues a `@>` query.
- [ ] **Ledger partitioning ADR (default: keep, revisit when size is measured).** It is `RANGE (seq)`, `seq` is per project, and
  only a DEFAULT partition exists, so it gives no benefit today.
- [ ] **Vacuum and fillfactor.** Set per-table autovacuum and fillfactor for `job` and
  `event_seq` (every claim churns the partial `job_claim` index; every append updates
  `event_seq`). Decide retention for finished jobs. Test: claim latency with 100k finished rows.
- [ ] **Pool and session settings.** Add `[database.pool]` keys in TOML. Today 1..10 is
  hard-coded at `bootstrap.py:996` and `cli/gate_notices.py:165`. Set `application_name`,
  `statement_timeout` and `idle_in_transaction_session_timeout` per role.
- [ ] **P14 Per-test reset without re-migrating.** `tests/infrastructure/db/conftest.py:50-89`
  and `tests/contracts/conftest.py:42-50` re-migrate for every test (876 uses). Replace that
  with `TRUNCATE ... RESTART IDENTITY`, with an owner-only append-only bypass; migration tests
  keep the drop path. Review Focus 5. Measure suite time.

## SP8 Runtime and clients (P5, P6, P11-P13, P16-P18)

- [ ] **P5 Lane feed.** `hub/app.py:755-765` walks every worktree, per socket, every second
  (`lanes.py:109,135-145`). Fix:
  - validate the requested path directly
  - cache discovery for a TTL declared in TOML
  - move the work to `asyncio.to_thread`
  - share the cache with `GET /lanes`

  Ratchet the syscall count per tick.
- [ ] **P6 Device registry cache** keyed on `(st_mtime_ns, st_ino)` (`hub/devices.py:65-74`).
  Test that a revocation takes effect on the next request. Share one `ledger_after` page per
  project and seq across subscribers (`app.py:726`).
- [ ] **P11 Writers:**
  - Runner event files stay open and flush per event: qwenloop `run_store.py:29-32`, claude
    `infrastructure/events.py`.
  - The wire log flushes per message, not per chunk (`wire_log.py:113-122,166-167`).
  - The skills `index inspect` is memoised by manifest mtime (`skills_context.py:144-158`).
- [ ] **P12 Lazy imports.**
  - `vibey` CLI: 0.9 s today; `bootstrap` 271 ms, `cli.serve` 113 ms, `cli.hub_pair` 100 ms,
    textual through `cli.status`.
  - qwenloop: `aio_pika`.
  - An import-time budget test in `tests/meta`.
- [ ] **P13 Clients.**
  - Expo chat: memoised entries, the input in its own component, `FlatList`
    (`clients/app/src/screens/chat.tsx:188,196,445`).
  - Desktop: subscribe to `/projects/{id}/live` instead of polling 5 or 6 endpoints every 5 s
    (`main.c:14,179-195`).

  This merges into SP10's A2 where the files overlap.
- [ ] **Developer loop.** `MYPY_CACHE_DIR` shared across worktrees per base branch. On push,
  run `pip-audit` only when `uv.lock` changed (CI still runs it on every PR). Add
  `--durations=50` to the hook. Keep the full pre-push suite (default: quality first).

## SP9 Model study (B; P7-P10 join it)

Done so far (PR #1866):
- the preregistration
- the harness
- the 30-task corpus and its validator
- a live screen of stock gpt-oss: 11.93 GiB at 32k
- the create-API fix and the privacy fix

Calibration so far: stock gpt-oss solved slugify 6 of 6 over two runs; October solved 1 of 3.
The intervals overlap, so the status is "not contradicted, not reproduced". The first run's
ledger is kept outside the repository because it holds a hostname and a home path.

- [ ] Finish calibration to 10 trials on a quiet host; the evidence explains the October difference.
- [ ] **Candidate field:** pull each candidate and read its licence; pull Heretic v2; screen.
- [ ] **Runs:** screening, then confirmation, then Heretic v2 for the finalists.
- [ ] **Outputs:**
  - an evidence file
  - a paper section through `paper_evidence.py`
  - a catalogue quality field
  - if the default changes: a new ADR and one PR that moves every pin; otherwise one PR that
    fixes the drifted pins
- [ ] **Measurements gated on the quiet host:**
  - **P7** round `num_ctx` (`ollama_chat.py:480-483`, `fit.py:764`) into buckets declared in
    TOML, only if reloads are observed (Review Focus 3).
  - **P8** pass vibey-gh's `keep_alive` (`slots.py:925`, 30m).
  - **P9** llama-server `--parallel 1`, `--cache-reuse`, flash attention
    (`inference.py:296-313`).
  - **P10** chunked trimming (`qwenloop/application/runner.py:150-170,374-381`,
    `context_economy.py:158-163`), shipped only if solve rate does not drop.

## SP10 Krypton chat and polish (A, carried in)

- **A1 One streaming chat contract backed by a model:**
  - a hub chat service reusing the canonical client from SP6
  - the slash-command router stays as the instant path
  - the model runs as the scoped `agent` principal and can never answer a spend gate
  - streamed turns, PostgreSQL sessions and history, ledger narration
  - amend ADR-0100 so its names match the code
  - the contract lives in `packages/vibey-core`; the C client is held to it by a parity test
- **A2 The pane on every surface:** desktop, app, VS Code, a new Textual screen, and the hub
  front door serving the Expo web build (with P13).
- **A3 Remove the fake UI:**
  - the model chip shows the model actually serving, from `vibey loops`
  - the hard-coded name and email go
  - usage figures come from `vibey_budget`
  - dead controls are deleted
  - VS Code reads the gate's `requires_scope`
- **A4 Beauty Bar:**
  - design tokens everywhere: the C client has 0 token uses against 86 literal margins and
    41 `px` values in `custom.css`
  - fix the `custom.css` load order (`main.c:1112`)
  - BB-1 literal scan and BB-7 command parity
  - screenshots taken from the running apps

## SP11 Docs and textbook (C, carried in)

- **C0 Foundations:**
  - a separate canon bible for the Feynman and Daniel story
  - a voice sheet built from `prose-technical-mechanics` and `prose-mechanics`
  - `scripts/prose_lint.py`, its `.toml` and `tests/meta/test_prose_lint.py`, with a shrinking allowlist
  - fix the generators that add dashes: `book.py`, `paper.py:704`, `release-surfaces.yml:407,485`
- **C1 The rewrite, in book order,** 10k to 20k words per PR:
  - README and index
  - guides
  - runbooks
  - reference, in three batches
  - ADRs in five groups, filenames kept
  - the paper, in two batches
  - CONTRIBUTING, SECURITY, SUPPORT
  - tenant docs, dash cleanup only
- **Rules:**
  - generated files change at their source
  - skill changes go to all four agent trees
  - the canon goes in a PR the operator merges
  - a new sub-doctrine and ADR record the house style

## Decisions

Answered by the operator on 2026-11-10:
1. **Push to develop:** run the core checks (`uv-lock`, `gates`, `noloss`) plus Release, and a
   nightly extended run on the develop tip. The nightly is skipped when the tip has not
   changed, and opens an issue when it fails.
2. **Merge path:** enforce the merge queue on `develop`. Reconcile it and remove the admin
   bypass there; tier (b) then proves every merge green.
3. **ADR-0016:** value types (dataclasses, Enums, Exceptions, TypedDicts) are exempt. This is
   recorded as an ADR-0016 amendment plus a proposed sub-doctrine 9.b wording that the
   operator ratifies by merging, and enforced by the census.
4. **Telemetry:** the real OpenTelemetry API through `vibey_bootstrap.tracing`. The OTLP
   exporter is declared in config and stays off unless a collector is set.

Defaults taken, which the operator can override at any sub-plan:
- one aggregate `ci-result` required check
- locked tenant installs, with a nightly latest-dependency canary and a lowest-direct run at promotion
- the ledger partitioning ADR keeps the partitioning and records that it gives no benefit
  until the ledger's size is measured
- the full pre-push suite stays (quality first)
- third-party test tools (mutmut, Schemathesis, openapi-typescript, actionlint, zizmor) are
  adopted with a capability-gap reason written at each use

## Verification

- **Per sub-plan:** `uv run pytest` with the four 100% layer gates, plus each tenant's own
  suite. Also `uv run vibey-gh corpus-index --check`, ruff, mypy, lint-imports, bandit and
  pip-audit.
- **Ratchets:** every new census test passes at its committed baseline. Lowering a baseline
  is an ordinary commit; raising one fails the build.
- **SP0:** a test reproduces each bug and passes after its fix. The telemetry memory test is
  bounded. `vibey-gh ci-cost` baseline is committed.
- **SP1:**
  - `vibey-gh ci-cost` after CI-L, compared with the baseline: target at least 70% fewer
    job-min per week and at least 85% fewer macOS minutes, with PR wall p50 under 9 min.
  - A deliberately broken `plan` job makes `ci-result` fail.
  - A docs-only PR merges with no pending checks.
- **SP2:** the state machines and the replay harness pass. Mutation survivors are recorded
  as the baseline.
- **SP7 and SP8:** query-count, syscall and import-time budgets pass. Suite time is measured
  before and after P14 on a quiet host.
- **SP9:** calibration is recorded, the ledger verifies, and
  `tests/meta/test_sovereign_model_agreement.py` passes.
- **SP10:** run each surface (desktop, web in the browser pane, iOS simulator, VS Code, TUI)
  and hold one streamed conversation that calls a tool, shows a gate and survives a restart.
- **SP11:** `properdocs build --strict`, `vibey-gh book` and `vibey-gh paper` build, and the
  built `book-print.html` contains zero U+2014 and U+2013.
