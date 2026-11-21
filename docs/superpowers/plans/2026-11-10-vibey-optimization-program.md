# vibey Optimization Program: What Is Left

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Each sub-plan is written in full with superpowers:writing-plans right before it starts, and lands as its own PRs through the merge train. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make vibey measurably better (quality first, performance second), make its CI cheaper and faster, finish the four workstreams under way (security audit, sovereign model study, Krypton chat, Feynman docs), and add full Agent Client Protocol (ACP) support so a driver LLM can fully drive vibey.

**Architecture:** A master plan of sub-plans. This file lists only the work not yet done, the order, the decisions and the acceptance checks. Every change follows CDD: SDD for intent, TDD for checks, then converge against the tracked repository. It also follows the CLAUDE.md non-negotiables.

**Tech Stack:** Python 3.12+ uv workspace (asyncpg, PostgreSQL 14 to 18, Starlette hub, Textual TUI), Ollama and llama.cpp, TypeScript (`@vibey/core`, the Expo app, the VS Code extension), a C/GTK4 desktop built with meson, GitHub Actions on a public repository on the Free plan.

**Status as of:** 2026-11-20, `origin/develop` at `903bfbde2` (#1931). The original scan was 2026-11-10 at `010ebc70`.

## Landed

Each row was verified against `origin/develop`. Items listed here are not repeated below.

| Item | PR or evidence |
|---|---|
| SP0 events tail reads by byte offset and holds back a partial line | #1869, `infrastructure/engines/events_tail.py` |
| SP0 bounded telemetry buffers (`[telemetry] max_spans`, `max_samples`) | #1869 |
| SP0 smaller sdist and a loud failed-publish issue | #1869, `tests/meta/test_release_failure_is_loud.py` |
| SP0 CI cost baseline script and committed baseline | #1869, `scripts/ci_cost_baseline.py`, `docs/architecture/evidence/ci-cost-baseline-20261110T192053Z.json` |
| Merge path: no admin bypass on develop, `CI result` required, `code_coverage` rule dropped | #1911, #1897 |
| SP1-A aggregate `ci-result`, `lint` first, job time limits, least token permission | #1872 |
| SP1-B `plan` job, small PR matrix, skip unchanged areas, nightly full run | #1874, #1879, #1914 |
| SP1-C time limits on every job | #1929, #1930 |
| SP1-C actions pinned by SHA, bases by digest, hook repos by SHA, `pin-actions` | #1918, #1919, #1921, #1923 |
| SP1-C actionlint and zizmor, ratcheted | #1926 |
| CI-E strict docs build on pull requests | #1931 |
| SP2-A query budgets, contracts and state machines, round trips, replay census, hygiene censuses | #1881, #1882, #1884, #1885, #1886, #1891 |
| SP4-A scripts and storm tools under mypy strict, census of every Python file | #1892, #1893 |
| SP4-B vibey_gh, vibey-skills and vibey_bootstrap under mypy strict | #1894, #1896 |
| Pre-1.0 versioning and the 0.4.0 release | #1898, #1899, #1909 |
| Paper release counts from a tracked ledger | #1913 |
| SP5 architecture review written into the plan, SP1-C plan | #1895, #1917 |

## Global Constraints

- Quality is never traded for speed unless the task says why. A performance change ships with:
  - proof that behaviour is identical (the existing suite plus a test of the changed path)
  - a deterministic measure where one exists: query count, syscall count, import time, memory after N jobs
  - wall-clock before and after numbers, taken only on a quiet host
- Non-negotiables (CLAUDE.md): domain purity, an append-only ledger, credits exhausted is not a rate limit, jobs are idempotent under replay, a worker never blocks on a human, new and changed classes get an interface, TypeScript only, everything-as-code and configurable, dogfood the family (reuse first, and write a capability-gap reason at any site that cannot).
- 100% branch coverage on `domain/`, `application/`, `infrastructure/` and `cli/`.
- Every structural rule gets a **ratchet**: a `tests/meta` census whose baseline is a TOML number that may only fall.
- Required checks change only through `.vibey-gh.toml` and its reconciler. A rendered workflow changes at its template (`src/vibey_tools/gh/vibey_gh/templates/workflows/`).
- `ci.yml` has a single owner: every change to it is queued into SP1.
- Migrations are only ever added, never edited.
- Governance canon changes go in a separate PR that the operator merges.
- Work lives in the storm home. Draft PRs are pushed every 30 to 45 minutes. Commits use Conventional Commits. `git commit` and `git push` run in the foreground.
- No model tests run until SP9. They then run on a quiet host with no other sessions.

## Review Focus

1. A narrowed ledger read returns exactly what the full read plus the Python filter did, including across a superseding correction event (SP7).
2. A rounded `num_ctx` never truncates a prompt that the unrounded value would have fit (SP9).
3. A per-test database reset leaves no state behind: sequences, advisory locks, LISTEN channels, rows. That holds after a failed test too, and an application role can never use the owner's TRUNCATE bypass (SP7).
4. Over ACP, every prompt ends with exactly one stop reason, cancel always resolves pending permission requests, and a spend gate is never offered to the agent (SP-ACP).
5. `ci-result` still fails when any job fails, is cancelled, or the `plan` job fails, after CI-A drops the five older required checks (SP1).

## Order

1. **SP-ACP** (next).
2. **SP0 leftovers.**
3. **SP1 remainder.**
4. **SP2-B, then SP2-C.**
5. **SP3.** It runs unattended in parallel from now on. Start the Claude Security scan when SP-ACP starts.
6. **SP4 remainder.**
7. **SP5, SP6, SP7, SP8, SP9** (quiet host only), **SP10** (reuses ACP sessions), **SP11.**

Hot files keep a fixed order:
- `src/vibey/infrastructure/hub/app.py`: SP5 split, then SP8 (P5/P6), then SP10 (A1).
- `src/vibey/cli/main.py` (2,929 lines): SP-ACP adds one module only, then the SP5 split, then SP8 (P12).
- `ollama_chat.py`, `fit.py`, `slots.py`: SP6 (canonical client), then SP9 (P7/P8).

## SP-ACP (next): full Agent Client Protocol support

Full sub-plan: [`2026-11-20-sp-acp-agent-client-protocol.md`](2026-11-20-sp-acp-agent-client-protocol.md). It is written by a separate agent and lands as its own PRs. This is the summary.

`vibey acp` speaks ACP v1 (JSON-RPC 2.0 over stdio). Vibey is the ACP agent; the editor or driver LLM is the client. The goal: a driver LLM fully drives vibey, and on a machine where nobody ran `vibey doctor` or `vibey connect --yes`, vibey runs both itself and keeps its services running.

- **Prompts and tools.** `session/prompt` goes through the existing `HubChatPlanner` and the hub as the scoped agent principal. Each hub tool call streams as `tool_call` and `tool_call_update`, and replies stream as message chunks.
- **Live project.** While a session is attached, the `/projects/{id}/live` ledger stream becomes `session/update` notifications, and the six phases become a `plan`.
- **Gates.** An open `human_gate` the agent may answer becomes `session/request_permission`. Spend gates (`budget_exhausted`, `deploy_*`) are never offered; the operator is told to answer on the host.
- **Sessions.** `load`, `list`, `close` and `resume` persist in PostgreSQL through a new migration.
- **Bootstrap.** On `session/new`, an idempotent `AcpBootstrap` runs doctor and connect, loads user-level launchd or systemd units for the hub and worker with restart on death, and asks through the permission prompt before any step that needs sudo (installing PostgreSQL). A health probe restarts a dead hub or worker. Everything is configurable under a new `[acp]` table in `vibey.toml`.
- **Build.** Hand-rolled on a shared stdlib JSON-RPC peer factored out of the MCP server. The official `agent-client-protocol` 1.0.0 SDK is a dev-only dependency, used as the conformance client in tests.
- **Governance.** ADR-0101 (the ACP agent and self-installing services) reverses the supervisor's "never load units" rule to "user-level units only, under an explicit grant". The canon sub-doctrine PR is the operator's merge.
- **Done when:** the conformance test drives `vibey acp` as a subprocess through initialize, new, prompt, permission, cancel and load; the existing MCP stdio tests stay green; and a clean-account run shows the units loaded, the hub restarted after a kill, a non-spend gate answered, and a spend gate refused.

## SP0 Leftovers

- [ ] **Telemetry (Decision 4).** Use the real OpenTelemetry API through `vibey_bootstrap.tracing`, with the OTLP exporter declared in config and off by default. `bootstrap.py:1037` still builds `TelemetryTracer`.
  - Test: worker memory stays bounded after N jobs, and nothing is exported while the exporter is unset.
- [ ] **Develop publishing.** #1869 made the failure loud but the root cause was never confirmed. Read the latest develop `Release` runs and confirm "Publish to TestPyPI" now succeeds, or fix the cause. (The operator owns the TestPyPI cleanup, #1870.)
- [ ] **Disabled workflows.** Per the 2026-11-15 ruling only the necessary ones come back: `Release binaries` is enabled and the other 17 stay off. Record a reason for each of the 17 in code, replacing "unknown" in `ci-workflow-state-2026-11-10.md`.
- [ ] **Hollow floors.**
  - codexloop `infrastructure/appserver/gateway.py` still has 25 `pragma: no cover`: test each path or record why it is unreachable.
  - The `vibey_bootstrap` floor is measured by line: make it branch.
- [ ] **`vibey-gh ci-cost`.** The baseline exists as a script only. The command itself lands in CI-L (SP1).

## SP1 CI Pipeline (sole owner of `ci.yml`)

SP1-C is planned in `2026-11-16-sp1c-ci-hygiene.md`, which also names SP1-D to SP1-G.

- [ ] **CI-A, remainder.** `ci-result` exists and is required, but five older checks are still required beside it (`gates`, `Lint and static gates`, `No-loss property suite (10,000 examples)`, and the two fixed-name VS Code checks). Drop the five that `CI result` already covers, through `.vibey-gh.toml` and a reconcile. Review Focus 5.
- [ ] **CI-D Locked tenant installs (SP1-D).** Only the zizmor job uses `uv export --frozen --require-hashes`. Tenant rows still `pip install -e`. Move them to locked installs, add a nightly latest-dependency canary, and a lowest-direct run at promotion.
- [ ] **CI-G One promotion run per attempt.** `vibey-gh promote` opens the PR only when it is ready (template `promote-to-main.yml`).
- [ ] **CI-H Shard the root suite three ways.** Upload `.coverage.*` as artifacts; one combine job computes all four floors in a single pass. Run the vibey-gh suite with `-n auto` once git-fixture isolation is proven.
- [ ] **CI-I Image built once.** Native arm64 on `ubuntu-24.04-arm` instead of QEMU; cluster-smoke loads the amd64 artifact. Attach a CycloneDX SBOM and attest it the way `release-binaries.yml` does.
- [ ] **CI-J Caches, remainder.** uv, npm and Docker gha caches exist. Still to add: pip, Homebrew, ccache, prebuilt Arch and Fedora toolchain images, mypy, Tectonic (with a per-figure hash skip and parallel compile).
- [ ] **CI-K De-duplicate.** One Linux `advisory` job, not three; build the `.vsix` once and smoke-test it on macOS; one krypton-app test job; narrow provenance's push trigger, in its template.
- [ ] **CI-L Re-measure.** Add `vibey-gh ci-cost` (reusing the Actions readers in `branch_health.py` and `review_outcome.py`) and compare against the SP0 baseline.
- [ ] **Release binaries.** Fix the Android job (`Error resolving plugin [id: 'com.facebook.react.settings']`), then re-attach the binaries to `vibey-v0.4.0`.

## SP2 Test Depth, Remainder

SP2-A is landed. Still to do:

- [ ] **SP2-B Hub contract.** ACP reuses this contract.
  - Generate the TypeScript types from `docs/reference/hub-api.json`.
  - A meta test checks that every route and method used by the C client and both TypeScript clients is in the document.
  - The app moves onto `@vibey/core`: `clients/app/src/core/hub-client.ts` duplicates `transport.ts`.
  - RFC 9457 problem+json for the free-text hub errors, with stable `type` codes from `scripts/error_catalog.py`. This fixes `packages/vibey-core/src/transport.ts` mapping 409 to three meanings.
- [ ] **SP2-C Promotion and nightly tiers only:**
  - mutation testing (mutmut) on `domain/noloss.py`, `circuit.py`, `rotation.py`, `ledger_chain.py` and the redactor, with a ratchet on surviving mutants
  - Schemathesis against a test hub
  - libFuzzer on `kr-hub-client.c` and `kr-pairing.c`, under the existing ASan/UBSan build
  - real-process chaos: SIGKILL `vibey worker` subprocesses against Postgres
  - randomised test order
  - a reproducible-wheel check (build twice with `SOURCE_DATE_EPOCH`)
- [ ] **Issue #1883.** A float in jsonb breaks `LedgerChain.verify`; three strict xfails wait on it.
- [ ] **Hygiene, remainder.** 21 assertion-free tests get assertions or are deleted. The coverage-fill file count is already 0. Real sleeps get injected clocks where the census still lists them.

## SP3 Security (unattended, in parallel)

Bandit already runs on `claudeloop`, `codexloop`, `qwenloop` and `vibey_bootstrap`. The gaps:
- **No bandit:** `vibey_gh`, runners-common, `vibey_skills`, `scripts/`, the storm tools.
- **No scanner at all:** the C client, the Expo app, the workflows.

- [ ] Run the Claude Security **scan codebase** job on the whole repository. Its report and patches stay on disk.
- [ ] Seed the threat model with these surfaces:
  - **Compiled-in email:** a personal email is compiled into `clients/desktop/src/app/kr-chat-page.c:634`.
  - **Spend-gate mismatch:** VS Code's gate check (`chat-view-provider.ts`) covers fewer kinds than `SPEND_GATE_KINDS` (`domain/hub_scope.py`).
  - **Hub auth:** pairing, the QR claim, device tokens (`hub/devices.py`) and the scoped `agent` principal. ACP reuses the agent principal.
  - **Engine sessions:** the `ChildEnvironment` allow-list.
  - **Unlocked installs:** tenant installs (SP1 CI-D).
  - **Releases:** release signing and `.github/advisory-exceptions.toml`.
  - **ACP:** a new stdio surface that can install and load services (SP-ACP).
- [ ] Triage with the operator. Each confirmed finding becomes an issue, or a private advisory per `SECURITY.md`, plus a fix PR with a regression test. About 100 Dependabot alerts are open and enter the same triage.
- [ ] Merge the about 9 redactors into one masking module and the 3 structlog setups into one (`vibey_bootstrap/logging/masking.py` is the candidate), with the round-trip property from SP2-A.
- [ ] **Durable gates:** bandit on the uncovered packages; a `tests/meta` scan for secrets and personal data over tracked text (emails, home paths, hostnames, keys), with a designed exemption for the provenance header.

## SP4 Static-Gate Parity, Remainder

SP4-A and SP4-B are landed (scripts, storm tools and the three tenants are under mypy strict).

- [ ] **Suppression census.** A `type: ignore`, `noqa`, `no cover`, `nosec` or broad `except Exception` needs a reason on the same line or the one before. Re-count first; the 2026-11-10 baseline was 162, 50, 71 and 39 without a reason. The baseline ratchets.
- [ ] **RUF100 and `Any`.** Add RUF100 to ruff's selected rules (today `E,F,I,UP,B,SIM`) and ratchet `Any` (70 root, 407 tenants on 2026-11-10).
- [ ] **Floors.** A fifth gate for `src/vibey/bootstrap.py`; a floor for `tui/` or a re-justified exemption in ADR-0023's terms. Cover claudeloop's own `bootstrap.py` and measure every layer of runners-common.
- [ ] **`.importlinter`.** `interfaces-declare-only` exists. Verify it covers every `interfaces` package, generated from `find -name interfaces` so a new package cannot be missed.
- [ ] **TypeScript:** a shared strict base tsconfig with `exactOptionalPropertyTypes` (which ADR-0088 claims); `noUnused*`, `noImplicitReturns` and `noFallthroughCasesInSwitch` for `clients/app`; typescript-eslint or remove the dead disable in `clients/app/src/ui/kit.tsx`; review the `as unknown as` casts.
- [ ] **C:** in `meson.build`, re-enable `-Wunused-parameter` and `-Wmissing-field-initializers`, and add `-Wconversion`, `-Wnull-dereference` and `-Wvla`. Extend coverage to the GTK views.
- [ ] **Stale facts**, fixed in all four agent trees in one PR:
  - the vibey-architecture skill's counts and claims
  - the `ci.yml` comment on the tenant matrix
  - dead `vibey-bootstrap` repository links (`vibey_bootstrap/__init__.py`, `bootstrap/docs/gen_pages.py`)
  - the testing skill's missing `tests/unit/`
  - the quality-gates skill's stale hook line

## SP5 Dead Code and Structure (before SP6 to SP8)

- [ ] **Orphaned modules.** About 18 `src/vibey` modules have no production importer. Confirmed on 2026-11-20:
  - `infrastructure/db/orm_models.py` and `orm.py`, the only reason `sqlmodel` and `sqlalchemy` are runtime dependencies
  - `application/engine_failover.py`, `application/verdict_extraction.py`
  - `infrastructure/ledger/tier_manager.py`, `tier_store.py`
  - `domain/command_guard.py`, `domain/media.py`
  - `infrastructure/aws/adapter.py` (only a test imports it)

  Wire each one in `bootstrap.py` if a sub-plan here needs it; otherwise delete it, after checking entry points and dynamic loading.
- [ ] **Dependencies:** drop `tomli-w`, move `pyyaml` to dev, and drop the ORM's dependencies.
- [ ] **Complexity:** ruff C901 and PLR091x with a ratcheting baseline (168 functions over 10 on 2026-11-10; none enforced yet).
- [ ] **Splits:**
  - `src/vibey/infrastructure/hub/app.py` `build` (starts at line 267): split into route modules.
  - `src/vibey/cli/main.py` (2,929 lines): one module per command, which also sets up P12.
  - `vibey_gh/cli.py` `main`.

  Each class over 500 lines (claudeloop `AutonomousRunner`, `Flattener`, and so on) gets a split note.
- [ ] **ADR-0016 census per package.** 479 module-level functions in `src/vibey` on 2026-11-10, about 46 with a reason; codexloop had 237 with none. Value types are exempt (Decision 3): an ADR-0016 amendment plus a proposed 9.b wording, in a canon PR the operator merges.
- [ ] **Architecture review and target layout.** The operator's rule: all code lives in classes; every class has an interface and implements it; one class per file; every source folder is `<folder>/` plus `<folder>/interfaces/`; the architecture beyond that is optimal and onion-layered. The review is read-only and comes first.
  - **Rulings taken 2026-11-15 (plan defaults):** value types stay exempt from interfaces and module-level functions, but not from one-class-per-file. The folder and onion rules bind all Python under `src/vibey` first, and the tenants converge afterwards. Private helper classes may share a file with their single owner.
  - **Step 1, census:** a `tests/meta` report of each violation per package (module-level functions, files with 0 or 2+ classes, classes with no interface, interfaces with no implementer, folders without `interfaces/`, interfaces that consume), with a committed TOML baseline per rule that may only fall. The 2026-11-12 measure was 1,225 files, 380 with more than one class, 496 with none, and 48 of 195 code folders with an `interfaces/` folder; re-measure first.
  - **Step 2, target architecture:** an ADR draft mapping the five layers to the onion and naming where controllers, services, repositories and the pure core sit. It keeps the non-negotiables, says what the move costs (import-linter contracts, every import path, the 100% gates, the tenants), and proposes a staged migration, one package per PR, behind the ratchets.
  - **Enforcement:** one checker, `scripts/architecture_rules.py`, reads the declared rules and baselines and runs in three places: a pre-commit hook on staged files under `src/`, the pre-push hook (full census), and the CI `lint` job. It reports success only for rules it evaluated. The hooks run report-only until the PR that records the ruling.
  - **Governance:** the rule is a sub-doctrine in the canon, proposed in a separate canon PR the operator merges, plus the ADR-0016 amendment.
  - **Order:** review, then the splits above, then the census gates; the physical move of packages is last.

## SP6 Family Consolidation

- [ ] **One canonical Ollama client** in `vibey_runners.common`, dependency-free. The 2026-11-10 list of 11 clients needs a recount first. Known today:
  - root: `infrastructure/ollama_models.py`, `engines/ollama_chat.py`, `engines/ollama_residency.py`
  - vibey_gh: `fit.py`, `slots.py`, `local_review.py`
  - qwenloop: `ollama_probe.py`, `inference.py`
  - claudeloop: `doctor_env.py`
  - scripts: `sovereign_probe.py`, `model_quality_study.py` (and `minimum_specs.py`, to be confirmed)

  One default-URL key replaces the several constants and the `11434` literal (still in 56 files). `OllamaChatClient`'s public behaviour stays, so ACP and A1 can reuse it.
- [ ] **`MemoryProbe` gains GPU memory.** Route `vibey_gh/slots.py`, `scripts/minimum_specs.py`, `scripts/host_health.py` and `qwenloop/cli/app.py` through it.
- [ ] **Retry and backoff.** Move the 5 hand-written loops outside `domain/` to `vibey_bootstrap.retry`, or record the capability gap at each site.
- [ ] **Runner duplication.** The claude and codex runners share 1,862 identical lines across 72 paths (`forecast.py`, `api/params.py`, `handoff_marker.py`, `verbosity.py`, `git_savepoints.py`). Move them into `vibey-runners-common`.
- [ ] **Hash chains.** Three exist; keep the domain one, and record a reason for any other that stays.
- [ ] **Bootstrap reuse.** src/vibey uses 5 of about 40 `vibey_bootstrap` modules. Adopt health, exceptions and tracing where the SP0 telemetry decision lands. ACP's JSON-RPC peer is built in `src/vibey`, so record why in the capability-gap note if `vibey_bootstrap` has no equivalent.
- [ ] **Hard-coded values (12.c):**
  - `"claude-sonnet-5"` repeated in `vibey_gh/config.py`
  - `"gpt-oss:20b"` defaulted in 39 files, where `domain/sovereign_model.py` should be the only source
  - the repository slug written into 15 files
  - literal timeouts and ad hoc `tomllib` loads
  - `scripts/continuation_prompts.py` hand-parses `.vibey-gh.toml`

  Each moves to its declared source, and a meta test forbids the literal anywhere else.

## SP7 Database

- [ ] **P1 Narrowed ledger reads.** Add `for_project(project_id, *, kinds, after_seq, cycle)` on the repository and its interface, over the `event_kind` index. Move the `all_for_project` callers (47 hits on 2026-11-20, including `budget_source.py`, `project_budget.py`, `tui/dashboard.py` every second and `cli/serve.py`). Review Focus 1, plus query-count budgets from SP2-A.
- [ ] **P2 One round trip per append.** `append_event` returns `(seq, recorded_at)`, so the extra `SELECT *` and JSON re-parse go.
- [ ] **P3 Statement-level NOTIFY** with the highest seq, in a new migration replacing the per-row trigger in `0019`. Tests: a multi-row transaction notifies once, and a listener catches up after a dropped notification.
- [ ] **P4 Indexes.** Drop `event_project_seq`, which duplicates the primary key `(project_id, seq)` (`0013`). Drop `event_payload_gin` if `pg_stat_user_indexes` confirms it is unused and no code issues a `@>` query.
- [ ] **Ledger partitioning ADR (default: keep, revisit when size is measured).** It is `RANGE (seq)`, `seq` is per project, and only a DEFAULT partition exists, so it gives no benefit today.
- [ ] **Vacuum and fillfactor.** Per-table autovacuum and fillfactor for `job` and `event_seq`. Decide retention for finished jobs. Test: claim latency with 100k finished rows.
- [ ] **Pool and session settings.** Add `[database.pool]` keys in TOML (1..10 is hard-coded today). Set `application_name`, `statement_timeout` and `idle_in_transaction_session_timeout` per role.
- [ ] **P14 Per-test reset without re-migrating.** The DB conftests still drop the schema and re-migrate (22 migrations). Replace that with `TRUNCATE ... RESTART IDENTITY` and an owner-only append-only bypass; migration tests keep the drop path. Review Focus 3. Measure suite time. The ACP session table adds a migration, so this lands after it.

## SP8 Runtime and Clients

- [ ] **P5 Lane feed.** The hub walks every worktree, per socket, every second. Validate the requested path directly, cache discovery for a TTL declared in TOML, move the work to `asyncio.to_thread`, and share the cache with `GET /lanes`. Ratchet the syscall count per tick.
- [ ] **P6 Device registry cache** keyed on `(st_mtime_ns, st_ino)`. Test that a revocation takes effect on the next request. Share one `ledger_after` page per project and seq across subscribers.
- [ ] **P11 Writers.** Runner event files stay open and flush per event (qwenloop `run_store.py`, claude `infrastructure/events.py`). The wire log flushes per message, not per chunk. The skills `index inspect` is memoised by manifest mtime.
- [ ] **P12 Lazy imports.** The `vibey` CLI takes about 0.9 s to start (`bootstrap` 271 ms, `cli.serve` 113 ms, `cli.hub_pair` 100 ms, textual through `cli.status`); qwenloop imports `aio_pika` eagerly. Add an import-time budget test in `tests/meta`.
- [ ] **P13 Clients.** Expo chat: memoised entries, the input in its own component, `FlatList`. Desktop: subscribe to `/projects/{id}/live` instead of polling 5 or 6 endpoints every 5 s. This merges into SP10's A2 where the files overlap.
- [ ] **Developer loop.** `MYPY_CACHE_DIR` shared across worktrees per base branch. On push, run `pip-audit` only when `uv.lock` changed (CI still runs it on every PR). Add `--durations=50` to the hook. Keep the full pre-push suite.

## SP9 Model Study (P7 to P10 join it)

Done so far (#1866): the preregistration, the harness, the 30-task corpus and its validator, a live screen of stock gpt-oss (11.93 GiB at 32k), and the create-API and privacy fixes. Calibration so far: stock gpt-oss solved slugify 6 of 6 over two runs; October solved 1 of 3. The intervals overlap, so the status is "not contradicted, not reproduced". The first run's ledger is kept outside the repository because it holds a hostname and a home path.

- [ ] Finish calibration to 10 trials on a quiet host; the evidence explains the October difference.
- [ ] **Candidate field:** pull each candidate and read its licence; pull Heretic v2; screen.
- [ ] **Runs:** screening, then confirmation, then Heretic v2 for the finalists.
- [ ] **Outputs:** an evidence file; a paper section through `paper_evidence.py`; a catalogue quality field; and, if the default changes, a new ADR and one PR that moves every pin (otherwise one PR that fixes the drifted pins).
- [ ] **Measurements gated on the quiet host:**
  - **P7** round `num_ctx` (`ollama_chat.py`, `fit.py`) into buckets declared in TOML, only if reloads are observed (Review Focus 2).
  - **P8** pass vibey-gh's `keep_alive` (`slots.py`, 30m).
  - **P9** llama-server `--parallel 1`, `--cache-reuse`, flash attention (`inference.py`).
  - **P10** chunked trimming (`qwenloop/application/runner.py`, `context_economy.py`), shipped only if solve rate does not drop.

## SP10 Krypton Chat and Polish

- **A1 One streaming chat contract backed by a model.** It reuses the ACP session engine from SP-ACP and the canonical client from SP6, so there is one session and streaming core, not two.
  - The slash-command router stays as the instant path.
  - The model runs as the scoped `agent` principal and can never answer a spend gate.
  - Streamed turns, PostgreSQL sessions and history, ledger narration.
  - Amend ADR-0100 so its names match the code.
  - The contract lives in `packages/vibey-core`; the C client is held to it by a parity test.
- **A2 The pane on every surface:** desktop, app, VS Code, a new Textual screen, and the hub front door serving the Expo web build (with P13).
- **A3 Remove the fake UI:** the model chip shows the model actually serving, from `vibey loops`; the hard-coded name and email go; usage figures come from `vibey_budget`; dead controls are deleted; VS Code reads the gate's `requires_scope`.
- **A4 Beauty Bar:** design tokens everywhere (the C client had 0 token uses against 86 literal margins and 41 `px` values in `custom.css`); fix the `custom.css` load order; BB-1 literal scan and BB-7 command parity; screenshots taken from the running apps.

## SP11 Docs and Textbook

CI-E (the strict docs build on pull requests) is landed, so this can start once SP10 is under way.

- **C0 Foundations:** a separate canon bible for the Feynman and Daniel story; a voice sheet built from `prose-technical-mechanics` and `prose-mechanics`; `scripts/prose_lint.py` with its `.toml` and `tests/meta/test_prose_lint.py` and a shrinking allowlist (README still has 61 em dashes); fix the generators that add dashes (`book.py`, `paper.py`, `release-surfaces.yml`).
- **C1 The rewrite, in book order,** 10k to 20k words per PR: README and index; guides; runbooks; reference, in three batches; ADRs in five groups, filenames kept; the paper, in two batches; CONTRIBUTING, SECURITY, SUPPORT; tenant docs, dash cleanup only.
- **Rules:** generated files change at their source; skill changes go to all four agent trees; the canon goes in a PR the operator merges; a new sub-doctrine and ADR record the house style.

## Decisions

Answered by the operator on 2026-11-20:
- **Always-on services.** ACP installs and loads user-level launchd or systemd units for the hub and worker (no sudo) and restarts them if they die. Steps that need sudo, such as installing PostgreSQL, go through ACP's permission prompt.
- **Build.** The ACP agent is hand-rolled on a shared stdlib JSON-RPC peer factored out of the MCP server (dogfood the family, no runtime dependency). The official `agent-client-protocol` 1.0.0 SDK is a dev-only dependency, used as a conformance client in tests.
- **Order.** ACP next, then the remaining program.

Answered by the operator on 2026-11-15:
- **SP5 architecture review keeps the plan defaults.** Value types are exempt (Decision 3). The folder and onion rules bind `src/vibey` first, and the tenants converge. Private helper classes may share a file with their single owner.
- **Disabled workflows.** Only the necessary ones come back. `Release binaries` is enabled; the other 17 stay off, each with a recorded reason.

Answered by the operator on 2026-11-10:
1. **Push to develop:** core checks (`uv-lock`, `gates`, `noloss`) plus Release, and a nightly extended run on the develop tip, skipped when the tip has not changed. The nightly is shipped (#1914).
2. **Merge path:** enforce the merge queue on `develop` and remove the admin bypass. The bypass is gone (#1911); proving a merge through a `merge_group` run stays open.
3. **ADR-0016:** value types are exempt, as an ADR-0016 amendment plus a proposed sub-doctrine 9.b wording that the operator ratifies by merging, enforced by the census.
4. **Telemetry:** the real OpenTelemetry API through `vibey_bootstrap.tracing`; the OTLP exporter stays off unless a collector is set.

Defaults taken, which the operator can override at any sub-plan:
- locked tenant installs, with a nightly latest-dependency canary and a lowest-direct run at promotion
- the ledger partitioning ADR keeps the partitioning and records that it gives no benefit until the ledger's size is measured
- the full pre-push suite stays (quality first)
- third-party test tools (mutmut, Schemathesis, openapi-typescript) are adopted with a capability-gap reason written at each use

Open and owned by the operator: the TestPyPI cleanup (#1870), the self-hosted-runner question, merge-queue enforcement, the canon PRs (ADR-0016 amendment and 9.b wording, the SP5 sub-doctrine, the pre-1.0 sub-doctrine, ADR-0101's sub-doctrine, the house style), SP3 triage, and a quiet host for SP9.

## Verification

- **Per sub-plan:** `uv run pytest` with the four 100% layer gates, plus each tenant's own suite. Also `uv run vibey-gh corpus-index --check`, ruff, mypy, lint-imports, bandit and pip-audit.
- **Ratchets:** every new census test passes at its committed baseline. Lowering a baseline is an ordinary commit; raising one fails the build.
- **SP-ACP:** the full gates above; the ACP conformance test with the official SDK client; the existing MCP stdio tests unchanged and green; and a manual run in a clean account or fresh container (units loaded, hub restarted after a kill with a notice, a project's phase plan streaming, a non-spend gate answered through the permission prompt, a spend gate refused, cancel mid-turn, session reload).
- **SP0 and SP1:** a test reproduces each bug and passes after its fix. `vibey-gh ci-cost` after CI-L, compared with the baseline: at least 70% fewer job-min per week, at least 85% fewer macOS minutes, PR wall p50 under 9 min. A deliberately broken `plan` job makes `ci-result` fail, and a docs-only PR merges with no pending checks.
- **SP2:** the contract census, Schemathesis and mutation survivors are recorded as the baseline.
- **SP7 and SP8:** query-count, syscall and import-time budgets pass. Suite time is measured before and after P14 on a quiet host.
- **SP9:** calibration is recorded, the ledger verifies, and `tests/meta/test_sovereign_model_agreement.py` passes.
- **SP10:** run each surface (desktop, web in the browser pane, iOS simulator, VS Code, TUI) and hold one streamed conversation that calls a tool, shows a gate and survives a restart.
- **SP11:** `properdocs build --strict`, `vibey-gh book` and `vibey-gh paper` build, and the built `book-print.html` contains zero U+2014 and U+2013.
