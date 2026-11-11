# SP2-A Test Depth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Python core the test depth the later refactors (SP5 to SP8) will lean on: replay proofs for every job handler, contract and model-based tests for the job and ledger repositories, round-trip properties, a query-count fixture with ratcheted budgets, replayable Hypothesis failures, and honest test hygiene.

**Architecture:** Tests and test support only. A production change is made only when a new test exposes a real bug, in its own commit, with the failing test first. Contract tests run one body against an in-memory reference and the real PostgreSQL repository (the `tests/contracts` pattern); state machines drive both through random operation sequences; every structural rule is a `tests/meta` census whose TOML baseline may only fall.

**Tech Stack:** pytest, pytest-asyncio, Hypothesis (`RuleBasedStateMachine`), asyncpg 0.31 (`Connection.add_query_logger`), PostgreSQL 14 to 18.

**Spec:** `docs/superpowers/plans/2026-11-10-vibey-optimization-program.md`, section SP2. This plan implements the Python half of SP2 only (see "Scope" below).

## Scope

SP2 in the master plan bundles four unrelated subsystems; this plan is SP2-A. Not in it:
- **SP2-B, hub contract** (TypeScript types from `docs/reference/hub-api.json`, route census, RFC 9457 problem+json). It edits `hub/app.py`, whose order is fixed (SP5 split, then SP8, then SP10), so it waits.
- **SP2-C, promotion and nightly tiers** (mutmut, Schemathesis, libFuzzer, real-process chaos, randomised order, reproducible wheel). They run on the nightly and promotion tiers, which wait on the operator-gated SP1-B Task 4.

## Grounding (read at origin/develop 43baaa6a8 + 9d91a8e45; these corrected the master plan)

- 21 test functions have no check at all (the master plan said 85); no file is a coverage-filler by name (it said 20). The 94 `sleep(` hits under `tests/` are mostly inside subprocess script text, not real waits; only 3 of the big ones were checked.
- No `JobKind` enum exists: job kinds are strings (`"build.implement"`, ...). `JobRepository` (`src/vibey/application/interfaces/queue.py:93`) has `enqueue, enqueue_batch, list_for_cycle, claim, claimable_projects, heartbeat, ack, nack, defer, park, grant_attempts, reap, assign_engine, count_unsettled, queue_depth, get`; `bump`/`unbump` live on `job_priority_repository.py`.
- There is no job-repository or ledger-repository contract test, and no shared ledger fake (five ad hoc ones). `FakeJobRepository` is `tests/application/fakes.py:24`.
- Handlers with a replay test: `build_decompose`, `design`. No replay test: `build_implement`, `build_integrate`, `build_verify`, `deploy_acceptance`, `deploy_design`, `deploy_execute`, `deploy_review`, `design_research`, `design_synthesis`, `review_collect`, `review_demo`, `review_deployment_choice`, `review_publish`, `review_triage`, `visual`. (`bus_dead_letter` replays a dead letter, a different thing.) Existing replay tests compare event COUNTS only.
- `redact_payload` (`src/vibey/infrastructure/ledger/redact.py:54`), `LedgerRecordCodec` (`domain/ledger_record.py:63,81`), `EventRowMapper.to_event`/`to_drafts` (`infrastructure/db/ledger_repository.py:63,195`) have no property tests. `test_digest_event_never_raises` (`tests/domain/test_ledger.py:141`) asserts nothing about the value.
- `tests/conftest.py` registers profiles `vibey` and `noloss` with no `print_blob`; CI uploads no `.hypothesis`. No query counting exists anywhere.

## Global Constraints

- Tests may be slow only where they must: PostgreSQL-backed state machines use `max_examples <= 25`, `stateful_step_count <= 20`, `deadline=None`, and the added wall time is MEASURED and recorded in the PR.
- No `# pragma: no cover`, no `skip` to hide a failure, no loosened assertion. A test that finds a bug stays and the bug is fixed (own commit, failing test first).
- `tests/contracts/conftest.py` already marks DB tests `integration` and builds `migrated_pool`; reuse it, do not re-migrate per test.
- A baseline TOML only falls (copy `tests/meta/test_single_source_paper_and_book.py` + `single_source.toml`: stale entries fail, so an entry is removed in the same change that fixes it).
- Conventional Commits ending `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; never `--no-verify`; foreground `git commit`/`git push`; no file edits while a hook runs. A `ci.yml` change gets its own commit (it runs the full CI tier).

## Review Focus

1. **Replay equivalence:** delivering a job twice (lease expiry, then redelivery) leaves the ledger events, job rows and fan-out exactly as one delivery did; compare content, not counts.
2. **Reference fidelity:** a state machine that passes because the reference copies a bug is worthless; each machine invariant is stated from the interface docstring/ADR, and one deliberately wrong reference makes the machine fail.
3. **A budget that can rise:** the query budget ratchet must fail on both a higher AND a lower count (lower means: tighten the budget), so it can only fall.
4. **Redaction is idempotent and total:** `redact(redact(x)) == redact(x)` and `contains_secret(redact(x))` is false for secrets in any nesting, without altering text that holds no secret.
5. **No DB, no false pass:** DB-backed tests skip cleanly when `VIBEY_TEST_DATABASE_URL` is absent and are never silently collected as passing.

---

### Task 1: Hypothesis failures are replayable

**Files:**
- Modify: `tests/conftest.py` (profiles at ~L30-52), `.github/workflows/ci.yml` (`gates` and `noloss` jobs)
- Create: `tests/meta/test_hypothesis_failures_are_replayable.py`

**Interfaces:** Produces: both Hypothesis profiles set `print_blob=True`; `gates` and `noloss` upload `.hypothesis/` as artifact `hypothesis-examples-<job>` with `if: failure()`, `retention-days: 7`, `if-no-files-found: ignore`.

- [ ] **Step 1: Write the failing meta test** asserting (a) each registered profile's `print_blob` is true (read `settings.get_profile(name)`), (b) `ci.yml` has an `actions/upload-artifact` step with `if: failure()` and `path: .hypothesis` in `gates` and `noloss`, pinned like the other uploads.
- [ ] **Step 2: Run it, confirm FAIL.** `uv run pytest tests/meta/test_hypothesis_failures_are_replayable.py -q`
- [ ] **Step 3: Set `print_blob=True` in both profiles; add the two upload steps** (same pin style as the existing `upload-artifact` steps, version copied from them).
- [ ] **Step 4: Run the meta test and `uv run actionlint`-equivalent (the repo's workflow lint) and confirm PASS.**
- [ ] **Step 5: Commit** `test(meta): make a failing Hypothesis example replayable from the log and the run`.

### Task 2: A query-count fixture with ratcheted budgets

**Files:**
- Create: `tests/infrastructure/db/query_counter.py` (the helper), `tests/infrastructure/db/query_budgets.toml`, `tests/infrastructure/db/test_query_budgets.py`
- Modify: `tests/infrastructure/db/conftest.py` (add the `query_counter` fixture)

**Interfaces:**
- Produces: `class QueryCounter` with `async def count(self, pool: asyncpg.Pool) -> AsyncIterator[QueryLog]` (an async context manager) where `QueryLog.statements: list[str]` and `QueryLog.count: int`; it registers `Connection.add_query_logger` on every connection the block acquires from the pool and removes it on exit. Fixture `query_counter -> QueryCounter`.
- `query_budgets.toml` keys, one per operation, each an integer: `ledger_append`, `job_claim`, `job_enqueue`, `job_ack`.

- [ ] **Step 1: Write the failing tests** in `test_query_budgets.py`: for each operation, run it once against `migrated_pool` inside `query_counter.count(...)` and assert `log.count == budget` with a message that says "raise a budget only with a written reason in the commit; if the count fell, lower the budget". The message makes the ratchet two-sided (Review Focus 3). Add a unit test of `QueryCounter` itself against a pool running `SELECT 1` twice (expects 2) and a test that the logger is removed on exit.
- [ ] **Step 2: Run, confirm FAIL** (module missing).
- [ ] **Step 3: Implement `QueryCounter`** with `asyncpg`'s `add_query_logger`/`remove_query_logger` (0.31). **Measure the real counts first** and write them into the TOML (the master plan expects `ledger_append` to be 2 today: the function call plus the `SELECT *`; record what is measured, not what is expected).
- [ ] **Step 4: Run and confirm PASS**, and run the DB suite to confirm no fixture interaction.
- [ ] **Step 5: Commit** `test(db): count queries per append, claim, enqueue and ack, and ratchet the budgets`.

### Task 3: Job repository contract (in-memory reference vs PostgreSQL)

**Files:**
- Create: `tests/contracts/test_job_repository_contract.py`
- Modify: `tests/contracts/conftest.py` only if a fixture is missing (a `job_repo` factory)

**Interfaces:**
- Consumes: `JobRepository` (`src/vibey/application/interfaces/queue.py:93`), `FakeJobRepository` (`tests/application/fakes.py:24`), `PostgresJobRepository` (`src/vibey/infrastructure/db/job_repository.py`), `migrated_pool`, `project_id`.
- Produces: fixture `repo` parametrised `["fake", "postgres"]` yielding a `JobRepository` bound to one project (pattern: `tests/contracts/test_rotation_cursor_contract.py`).

- [ ] **Step 1: Write the failing contract tests** (one body, both implementations), each stating its source in a comment (the interface docstring or the SQL): claim returns the highest-priority eligible job and none when empty; a claimed job is invisible to a second owner until its lease lapses; `ack`/`nack`/`defer`/`park` by a non-owner return `False` and change nothing; `heartbeat` extends the lease only for the owner; `reap` returns the count of lapsed leases and makes them claimable; `grant_attempts` raises `max_attempts` only for the owner; `enqueue_batch` is all-or-nothing; `count_unsettled` honours `exclude`. If the fake disagrees with the real repository, that is a finding: fix the FAKE (it is the reference) unless the real behaviour is the bug, and say which in the commit.
- [ ] **Step 2: Run, confirm the failures are real disagreements or missing code, not typos.**
- [ ] **Step 3: Make the fake faithful** (edit `tests/application/fakes.py`; keep its existing users passing).
- [ ] **Step 4: Run** `uv run pytest tests/contracts/test_job_repository_contract.py tests/application -q` and confirm PASS.
- [ ] **Step 5: Commit** `test(contracts): hold the job repository fake and the PostgreSQL repository to one contract`.

### Task 4: Job repository state machine

**Files:** Create `tests/contracts/test_job_repository_machine.py`.

**Interfaces:** Consumes Task 3's `repo` fixture (both implementations). Produces `class JobRepositoryMachine(RuleBasedStateMachine)` run as a `TestCase` with `max_examples=25, stateful_step_count=20, deadline=None`.

- [ ] **Step 1: Write the machine**: rules `enqueue`, `claim(owner)`, `heartbeat`, `ack`, `nack`, `defer`, `park`, `reap`, `advance_lease` (the clock: use short or already-expired leases so no real sleep is needed; if the PostgreSQL repository reads the DB clock, expiry is driven with a negative-or-zero `lease`, documented in the file); each rule is applied to BOTH the fake and the real repository and the machine asserts equal results. Invariants: no job is claimed by two owners at once; a job is in exactly one state; `queue_depth` equals the number of unsettled jobs; `ack` is terminal.
- [ ] **Step 2: Add the negative control:** a test that builds the machine over a deliberately wrong reference (a fake whose `claim` ignores the lease) and asserts Hypothesis FINDS the divergence (`pytest.raises` around `run_state_machine_as_test`). This proves Review Focus 2.
- [ ] **Step 3: Run** with and without a database; confirm the no-DB run skips and the DB run passes; record the measured added seconds.
- [ ] **Step 4: Commit** `test(contracts): drive the job repository fake and PostgreSQL through random operation sequences`.

### Task 5: Ledger repository fake, contract and state machine

**Files:** Create `tests/fakes/ledger_repository.py` (class `InMemoryLedgerRepository`), `tests/contracts/test_ledger_repository_contract.py`, `tests/contracts/test_ledger_repository_machine.py`.

**Interfaces:** Consumes `PostgresLedgerRepositoryInterface` (`src/vibey/infrastructure/interfaces/class_contracts.py:132`: `append(draft)`, `range(project_id, *, from_seq, to_seq)`, `all_for_project(project_id)`, `latest_seq(project_id)`), `LedgerChain` (`domain/ledger_chain.py:117`). Produces `InMemoryLedgerRepository` implementing it with per-project seq starting at 1.

- [ ] **Step 1: Write the failing contract tests:** seq is contiguous per project and independent across projects; `range(a, b)` equals the matching slice of `all_for_project`; `latest_seq` equals the length; the digest chain verifies over `all_for_project`; append is the only write (there is no update/delete method; assert the repository object exposes none and that a direct `UPDATE`/`DELETE` on the real table is refused for the app role, copying the guard test's approach from `tests/infrastructure/db/test_ledger_guard.py`).
- [ ] **Step 2: Implement `InMemoryLedgerRepository`.**
- [ ] **Step 3: Write the machine** (`append`, `range`, `latest_seq`; invariants: contiguity, chain verifies, a correction event supersedes without mutating the original) with its own negative control (a reference that reuses a seq is caught).
- [ ] **Step 4: Run, measure time, commit** `test(contracts): a shared in-memory ledger and a contract plus state machine for the ledger repository`. Do NOT migrate the five existing ad hoc ledger fakes (YAGNI; list them in the PR as a follow-up).

### Task 6: Round-trip properties

**Files:** Create `tests/infrastructure/ledger/test_redact_properties.py`, `tests/domain/test_ledger_record_properties.py`, `tests/infrastructure/db/test_ledger_row_mapper_properties.py`; Modify `tests/domain/test_ledger.py:141` (replace the value-less test).

**Interfaces:** Consumes `redact_payload`, `contains_secret` (`infrastructure/ledger/redact.py:54,61`), `LedgerRecordCodec.to_fields`/`from_fields` (`domain/ledger_record.py:63,81`), `EventRowMapper.to_event`, `to_drafts` (`infrastructure/db/ledger_repository.py:63,195`), `canonical_bytes`, `digest_event` (`domain/ledger.py:297,301`).

- [ ] **Step 1: Write the failing properties** (Hypothesis strategies built from the repo's own event strategies if they exist, else new ones next to the tests): `redact_payload(redact_payload(x)) == redact_payload(x)`; `not contains_secret(redact_payload(x))` for payloads with a planted secret at any depth; a payload with no secret is returned unchanged; `from_fields(to_fields(r)) == r`; `to_drafts(events)` then re-appending reproduces the events (use the in-memory ledger from Task 5, not a database); `digest_event` is stable under key order and changes when any field changes; replace `test_digest_event_never_raises` with a test that asserts the digest value's shape and stability.
- [ ] **Step 2: Run; a property that fails is a finding.** Fix the code (own commit, failing test first) or narrow the strategy with a written reason.
- [ ] **Step 3: Commit** `test: pin redaction, the ledger record codec, the row mapper and the digest with properties`.

### Task 7: Replay census and the build-handler replay cases

**Files:**
- Create: `tests/application/replay/__init__.py`, `tests/application/replay/harness.py`, `tests/application/replay/test_build_handlers_replay.py`, `tests/meta/test_every_handler_has_a_replay_case.py`, `tests/meta/handler_replay_exemptions.toml`

**Interfaces:**
- Produces in `harness.py`: `@dataclass(frozen=True) class ReplayCase` with `name: str`, `kind: str`, `build: Callable[[], ReplayRig]`; `@dataclass class ReplayRig` with `handler`, `job`, `snapshot: Callable[[], Mapping[str, object]]` (ledger events as content, job rows and any fan-out, all comparable); `async def assert_replay_is_idempotent(case: ReplayCase) -> None`: deliver once, capture `snapshot()`, simulate lease expiry (new handler instance over the same persisted fakes, the way `test_build_decompose_handler.py:202` does), deliver again, assert the second snapshot equals the first (Review Focus 1: content, not counts).
- The census test finds every `src/vibey/application/*_handler.py`, requires each to be named by a registered `ReplayCase` OR listed in `handler_replay_exemptions.toml` (`exempt = [...]`, may only shrink, stale entries fail), and fails if the TOML lists a handler that has a case.

- [ ] **Step 1: Write the census test and the harness test** (a self-test of `assert_replay_is_idempotent` with a deliberately non-idempotent toy handler, which must FAIL the assertion, and an idempotent one, which must pass).
- [ ] **Step 2: Seed `handler_replay_exemptions.toml`** with the 13 handlers that have no replay test after the two that do (`build_decompose`, `design`) are given cases that wrap their existing fakes; confirm the census passes at that baseline.
- [ ] **Step 3: Write cases for `build_implement`, `build_integrate`, `build_verify`** (their handlers' existing test files show how to construct each; reuse their fakes), remove those three names from the exemptions, run `uv run pytest tests/application tests/meta/test_every_handler_has_a_replay_case.py -q`.
- [ ] **Step 4: If a handler is not idempotent, that is a bug:** commit the failing case, then the fix, separately; the idempotency law is in `CLAUDE.md` ("Every job is idempotent under replay").
- [ ] **Step 5: Commit** `test(application): replay every handler and census the ones not yet covered` (build handlers).

### Task 8: Remaining handler replay cases

**Files:** Create `tests/application/replay/test_design_deploy_review_handlers_replay.py`; Modify `tests/meta/handler_replay_exemptions.toml`.

**Interfaces:** Consumes Task 7's `ReplayCase`/`assert_replay_is_idempotent`. Handlers: `deploy_acceptance`, `deploy_design`, `deploy_execute`, `deploy_review`, `design_research`, `design_synthesis`, `review_collect`, `review_demo`, `review_deployment_choice`, `review_publish`, `review_triage`, `visual`.

- [ ] **Step 1: Add a replay case per handler** (a handler that parks on a human gate must show the gate row is not duplicated on redelivery; one that writes a file or runs a command uses its existing fakes for the I/O). One test per handler so a failure names it.
- [ ] **Step 2: Empty the exemptions list as each case lands; the final state is `exempt = []`.** `bus_dead_letter` is exempt for a stated reason (it replays a dead letter, not a delivered job): keep it in the list with that reason as a comment and make the census accept a reason-bearing entry for it only.
- [ ] **Step 3: Run the application suite and the census; fix non-idempotent handlers as in Task 7 Step 4.**
- [ ] **Step 4: Commit** `test(application): replay the design, deploy, review and visual handlers`.

### Task 9: Test hygiene census

**Files:** Create `tests/meta/test_tests_assert_something.py`, `tests/meta/assertion_free_tests.toml`, `tests/meta/test_no_real_sleeps_in_process.py`, `tests/meta/real_sleeps.toml`.

**Interfaces:** Produces two AST censuses over `tests/**`: (1) a test function with no assertion, `raises`/`warns`/`fail`, or `assert*`/`expect*`/`verify*` call is listed in `assertion_free_tests.toml` as `file::name` (today 21; the scout's rule is the definition, copied into the test); (2) a `time.sleep(`/`asyncio.sleep(` whose literal argument is greater than 0.05 and that is NOT inside a string literal (subprocess script text) is listed in `real_sleeps.toml` as `file:line`, with the count by directory recorded.

- [ ] **Step 1: Write both censuses** with their baselines at today's counts (measure; the 94 hits are an upper bound and most should classify as script text).
- [ ] **Step 2: Fix what is cheap and meaningful:** give the 21 assertion-free tests an assertion or delete them with a reason (shrink the baseline in the same commit); replace an in-process real sleep over 1 s with an injected clock where the code under test already takes one.
- [ ] **Step 3: Run `uv run pytest tests/meta -q -n 6`** and confirm both baselines are exact.
- [ ] **Step 4: Commit** `test(meta): census assertion-free tests and in-process sleeps, and ratchet them down`.

---

## Delivery

Five pull requests, each queued through the merge train, in this order: (1) Tasks 1-2, (2) Tasks 3-5, (3) Task 6, (4) Tasks 7-8, (5) Task 9. Task 1's `ci.yml` edit makes PR 1 run the full tier. SP2-B and SP2-C follow after SP5 and SP1-B Task 4. Findings that are production bugs are fixed in their own commits and listed in the PR.
