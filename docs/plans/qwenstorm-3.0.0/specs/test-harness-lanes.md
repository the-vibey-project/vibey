# The test harness: implementation lanes (T01–T28)

Design: `specs/ADR-test-harness-queue.md` (ADR-0045 draft). It implements sub-doctrine 8.e,
which is drafted for ratification. Evidence cutoff: `develop` at `702b1490`, read
2026-09-22 (checkout `/private/tmp/claude-501/storm/qwenstorm-3.0.0/integration`). Every
`file:line` below is at that commit. ADR-0044's lanes R01–R34
(`specs/rabbitmq-lanes.md`) are specifications, not code: when a T-lane needs one, its
card says so under **Depends on**, and it must not start before that R-lane has merged.

## How to file these

This file holds 28 lanes. Each starts at a `# Lane Tnn — <slug>` heading, and the lanes
are separated by `---`. Before you run `file-issue.py`, split the file at those headings
into `specs/harness-Tnn-<slug>.md`, one lane per file. The script reads the first
`## Title`, so each lane must be its own file.

Each lane is the full template (`SPEC-TEMPLATE.md`), in order, preceded by a **lane card**
giving:

- the lanes it depends on, T-lanes and R-lanes both;
- its wave;
- the files it touches;
- the files it shares with other lanes, which only affects order;
- the existing tests that must keep passing **unchanged**.

## Order, waves and shared files

A lane can start once every lane it depends on has merged. The storm runs one lane at a
time from the integration branch (`storm-queue.sh:2-10`), so a shared file only fixes an
*order*. It never causes a merge between two lanes in flight.

| lane | slug | depends on | wave |
|---|---|---|---|
| T01 | test-run-key | — | 1 |
| T05 | test-harness-config | — | 1 |
| T20 | qwenloop-shell-timeout | — | 1 |
| T21 | amqp-consumer-count | **R04** | 1 (after R04) |
| T02 | test-reuse-policy | T01 | 2 |
| T03 | test-harness-messages | T01 | 2 |
| T06 | machine-lock | T05 | 2 |
| T08 | working-tree-digest | T05 | 2 |
| T09 | environment-probe | T01 T05 | 2 |
| T11 | run-executor | T01 T05 | 2 |
| T22 | harness-topology | **R04** T05 | 2 (after R04) |
| T04 | test-run-records | T02 T03 | 3 |
| T07 | pytest-lock-route | T05 T06 | 3 |
| T12 | coverage-gates | T03 T05 | 3 |
| T10 | file-run-store | T04 T05 | 4 |
| T13 | harness-instance | T02 T04 T06 T08 T10 T11 T12 | 5 |
| T14 | local-client | T02 T06 T08 T09 T10 | 5 |
| T15 | test-run-cli | T13 T14 | 6 |
| T23 | harness-service | **R04** T13 T22 | 6 |
| T24 | harness-amqp-client | **R04** T14 T21 T22 | 6 |
| T16 | test-inspect-cli | T15 | 7 |
| T17 | pytest-queue-route | T07 T15 | 7 |
| T18 | hooks-route | T15 | 7 |
| T19 | ci-route | T15 | 7 |
| T25 | harness-backend-selection | **R01 R17** T15 T23 T24 | 8 (after R17) |
| T26 | engine-route-env | **R20 R27 R28** T05 | 8 (after R28) |
| T27 | chart-test-harness | **R29 R30** T25 T26 | 9 (after R30) |
| T28 | route-flip | T16 T17 T18 T19 T25 T26 T27 | 10 |

**The early win.** T05 → T06 → T07 serializes every root pytest run on a machine (the
`locked` mode) before any queue exists. Land that chain first.

**Files shared with other lanes.** When the earlier lane has landed, rebase on it.

| file | lanes, in landing order |
|---|---|
| `src/vibey/domain/config.py` | R01 → T05 → R34 → T28 |
| `src/vibey/domain/errors.py` | R06, R19, T03, T15 (each adds one exception; append at the end) |
| `.importlinter` | R03, R21, R12, T05 (T05 appends one line at the end of `infrastructure-interfaces-declare-only`'s `source_modules`) |
| `pyproject.toml` | R03 → T07 → T28 |
| `src/vibey/bootstrap.py`, `src/vibey/bootstrap_interface.py` | R02 → T15 → R17 → T25 → R27 → R28 → T26 (T15 adds new classes only) |
| `src/vibey/cli/main.py` | T15 adds two registration lines only; R02, R17, R27, R28 and R33 edit other parts |
| `src/vibey/cli/pytest_route.py` | T07 → T17 |
| `src/vibey/cli/test_harness.py` | T15 → T16 → T25 |
| `src/vibey/infrastructure/test_harness/file_store.py` | T10 only; later lanes call it |
| `.github/workflows/ci.yml` | R32, R34, T19 |
| the chart and its goldens | R29 → R30 → R31 → R34 → T27 → T28 |

## Standing constraints (every lane restates them in its card)

- **Protected tests are never edited.** These are `tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
  `tests/system/test_delivery_stage_set.py` and `tests/live/**` (`.vibey-gh.toml:71-78`).
  They must keep passing.
- **The provenance line.** The first line of every new source file is copied
  byte-for-byte from line 1 of a sibling file (`vibey-gh check` compares it exactly).
- **Import modules, not `Test*` names, in test files.** pytest collects every class whose
  name starts with `Test` that it finds in a test module's namespace, and the harness has
  many (`TestSelection`, `TestRunRequest`, …). Write
  `from vibey.domain import test_harness as th`, then use `th.TestSelection(...)`. Never
  write `from vibey.domain.test_harness import TestSelection` in a test.
- **Never touch the real machine lock in a test.** From T07 on, the suite itself runs
  under the machine lock at the user's real `state_dir`. Two rules follow:
  - Every test that builds settings, a lock or a store, or spawns `vibey` or `pytest`,
    points `VIBEY_HARNESS_STATE_DIR` (or `state_dir`) at a directory under `tmp_path`.
  - Every child environment a test builds removes `VIBEY_HARNESS_RUN` and
    `VIBEY_HARNESS_ROUTE`.

  A test that waits on the real lock deadlocks until the wait bound.
- **Hermetic commands.** Configure the test command as `(sys.executable, "-c", ...)` or
  `(sys.executable, "-m", "pytest", "-p", "no:cacheprovider", ...)`. Never call `uv` in a
  test, except the one T11 test that checks `uv run --no-sync`, which skips when `uv` or
  the repository's `.venv` is missing.
- **No broker needed.** Unit tests use R04's `vibey_bootstrap.amqp.memory.InMemoryAmqpClient`.
  A test against a real broker is marked `@pytest.mark.integration` and skips unless
  `VIBEY_TEST_AMQP_URL` is set.
- **POSIX only.** The machine lock is `fcntl.flock`, and vibey supports neither Windows
  nor non-POSIX hosts.
- **Keep tests fast.** No test sleeps or waits longer than 5 s.
- **Defaults.** Nothing routes until T07 sets the root ini to `locked`. Queue routing is
  the default only after T28. `[test_harness] backend` defaults to `auto`.

---

# Lane T01 — test-run-key

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/domain/test_harness.py` (new)
  - `src/vibey/domain/interfaces/test_harness_interface.py` (new)
  - `tests/domain/test_test_harness.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - `tests/domain/test_domain_purity.py`
  - every test under `tests/domain/`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(domain): what a test run is, how it is keyed, and how its outcome is classified

## Why
Sub-doctrine 8.e (drafted for ratification) says: "a run is identified by what it tests —
the tree, the selection of tests and the environment — so the same run asked for twice is
answered once". ADR-0045 §5 defines that key exactly, and §6 defines how an exit code
becomes an outcome, using pytest's documented exit codes (0, 1, 2, 3, 4, 5).

Both are pure rules, so they belong in `domain/` (CLAUDE.md: no I/O, no async, no clock).
`tests/domain/test_domain_purity.py` walks every file there. `hashlib` and `json` are
stdlib and do no I/O.

## Required behaviour
1. **`CoverageGate`**, a frozen, slotted dataclass:
   - `include: str`, which must be non-empty and contain neither NUL nor `=`;
   - `fail_under: int`, which must be 0–100.

   Any violation raises `ValueError`. The classmethod `parse(text: str) -> CoverageGate`
   splits on the **last** `=`, so `"src/vibey/domain/*=100"` gives
   `("src/vibey/domain/*", 100)`. A malformed value raises
   `ValueError(f"a gate is INCLUDE=MIN, got {text!r}")`.
2. **`TestSelection`**, a frozen, slotted dataclass:
   - `command: tuple[str, ...]`, which must be non-empty;
   - `argv: tuple[str, ...]`;
   - `gates: tuple[CoverageGate, ...] = ()`.

   Any string containing `"\x00"` raises `ValueError`. It has a
   `CACHE_DEPENDENT_FLAGS: ClassVar[frozenset[str]]`, which is exactly `--lf`,
   `--last-failed`, `--ff`, `--failed-first`, `--nf`, `--new-first`, `--sw`,
   `--stepwise`, `--sw-skip` and `--stepwise-skip`. It has two properties:
   - `reusable -> bool` is `False` when any argv item is in that set;
   - `collects_coverage -> bool` is `True` when any argv item is `--cov` or starts with
     `--cov=`.
3. **`EnvNamePatterns`**, a frozen, slotted dataclass with `patterns: tuple[str, ...]`.
   - Each pattern must match `^[A-Za-z_][A-Za-z0-9_]*\*?$`, else `ValueError`.
   - `matches(name: str) -> bool`: a pattern ending in `*` is a prefix match; any other
     pattern is an exact match.
   - `select(environ: Mapping[str, str]) -> tuple[tuple[str, str], ...]` returns the
     matching `(name, value)` pairs, sorted by name.
4. **`ValueDigest`**, with a static method `of(value: str) -> str` that returns
   `hashlib.sha256(value.encode("utf-8")).hexdigest()`.
5. **`TestEnvironment`**, a frozen, slotted dataclass:
   - `python: str`
   - `distributions: str`
   - `database: str`
   - `env: tuple[tuple[str, str], ...]`, which is `(name, digest)`; names must be sorted
     and unique, else `ValueError`

   The classmethod
   `from_values(*, python, distributions, database, values: Sequence[tuple[str, str]])`
   digests each value with `ValueDigest.of` and sorts the result by name.
6. **`TestRunKey`**:
   - `SCHEMA: ClassVar[str] = "vibey.test.key/1"`.
   - `canonical(tree: str, selection, environment) -> str` returns
     `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)` of:
     ```python
     {"schema": "vibey.test.key/1", "tree": tree,
      "selection": {"command": list(command), "argv": list(argv),
                    "gates": [[g.include, g.fail_under] for g in gates]},
      "environment": {"python": ..., "distributions": ..., "database": ...,
                      "env": {name: digest for name, digest in env}}}
     ```
   - `derive(tree, selection, environment) -> str` returns the sha256 hex of `canonical(...)`.
7. **`MachineLoad`**, a frozen, slotted dataclass:
   - `load1: float`, `load5: float`, `load15: float`, each ≥ 0;
   - `cpu_count: int | None`.
8. **`TestOutcome(StrEnum)`**: `PASSED="passed"`, `FAILED="failed"`, `CRASHED="crashed"`,
   `TIMED_OUT="timed_out"`, `UNEXECUTABLE="unexecutable"`, `ABANDONED="abandoned"`. It has
   two methods:
   - `is_reusable()` is true for `PASSED` and `FAILED` only;
   - `is_dead_letter()` is true for `CRASHED`, `TIMED_OUT` and `UNEXECUTABLE` only.
9. **`TestOutcomePolicy.classify(exit_code: int | None, *, timed_out: bool, gate_failures: int) -> TestOutcome`**,
   checked in this order:
   1. `timed_out` → `TIMED_OUT`;
   2. `exit_code is None`, or `exit_code < 0` (a signal), or `exit_code == 3` → `CRASHED`;
   3. `exit_code == 0` and `gate_failures == 0` → `PASSED`;
   4. any other value → `FAILED`. That covers 0 with a gate failure, 1, 2, 4, 5 and every
      other positive code.
10. **`TestRouteMode(StrEnum)`**: `OFF="off"`, `LOCKED="locked"`, `QUEUE="queue"`. The
    classmethod `parse(text: str)` strips and lower-cases its input. Anything else raises
    `ValueError("vibey_harness_route must be one of off, locked, queue; got '<text>'")`.
11. **Interfaces.** `domain/interfaces/test_harness_interface.py` declares runtime-checkable
    Protocols:
    - `TestSelectionInterface` (the three fields and the two properties);
    - `TestEnvironmentInterface`;
    - `EnvNamePatternsInterface` (`matches`, `select`);
    - `ValueDigestInterface`;
    - `TestRunKeyInterface` (`canonical`, `derive`);
    - `TestOutcomePolicyInterface` (`classify`).

## Where to change
- The two new modules. Copy the frozen, slotted dataclass style and the interface layout
  of `src/vibey/domain/circuit.py` and `src/vibey/domain/interfaces/circuit_interface.py`.
- Put `StrEnum` classes in the same module, as R19 does for its enums.

## Acceptance criteria
- [ ] The canonical string for a fixed small example equals a literal in the test.
- [ ] The key changes when any one component changes: the tree, a command item, an argv item, a gate, `python`, `distributions`, `database`, or one env value.
- [ ] The key does not change when the env values are given in a different order.
- [ ] The outcome table holds for every row.
- [ ] 100% domain coverage; `test_domain_purity.py` passes.

## Tests to write first (TDD)
- `tests/domain/test_test_harness.py` (it imports `from vibey.domain import test_harness as th`):
  - `test_gate_parse_splits_on_the_last_equals_sign`
  - `test_gate_bounds_and_malformed_text` (parametrized)
  - `test_selection_rejects_nul_and_an_empty_command`
  - `test_selection_is_not_reusable_with_a_cache_flag` (parametrized over the ten flags)
  - `test_selection_collects_coverage`
  - `test_env_patterns_prefix_and_exact_matches`
  - `test_env_patterns_reject_a_bad_pattern`
  - `test_environment_from_values_digests_and_sorts`
  - `test_environment_rejects_unsorted_or_duplicate_names`
  - `test_canonical_json_is_exact`
  - `test_key_changes_with_each_component` (parametrized)
  - `test_key_ignores_env_order`
  - `test_machine_load_rejects_negative_load`
  - `test_outcome_table` (parametrized: `(None, False, 0)` → crashed, `(-9, False, 0)` → crashed, `(3, False, 0)` → crashed, `(0, False, 0)` → passed, `(0, False, 1)` → failed, 1, 2, 4, 5 and 7 → failed, `(0, True, 0)` → timed_out)
  - `test_outcome_reusable_and_dead_letter_sets`
  - `test_route_mode_parse`
  - `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Any I/O: git (T08), probes (T09), files (T10).
- The reuse policy (T02).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees; the docs wave owns them.

Do not push or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T02 — test-reuse-policy

**Lane card.**

- **Depends on:** T01.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/domain/test_reuse.py` (new)
  - `src/vibey/domain/interfaces/test_reuse_interface.py` (new)
  - `tests/domain/test_test_reuse.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - `tests/domain/test_domain_purity.py`
  - T01's tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(domain): when a recorded test result answers a repeat request

## Why
8.e: "a repeat request receives the recorded result instead of a second execution", and
"never retried forever". ADR-0045 §7 bounds the first clause:
- a cached FAIL is reused only inside a short window;
- a key that has both passed and failed is contradictory evidence, so it is re-run
  (sub-doctrine 10.f: "missing or contradictory evidence stays unknown");
- a key whose last run was dead-lettered stays **parked** until someone requeues it
  (ADR-0024: every bounded ladder parks with a grant).

The decision is pure: `now` is an argument.

## Required behaviour
1. **`RecordedAttempt`**, a frozen, slotted dataclass:
   - `run_id: str`
   - `attempt: int`, ≥ 1
   - `outcome: TestOutcome | None`, where `None` means running
   - `recorded_at: datetime | None`, which is required and must be timezone-aware when
     `outcome` is set
   - `reusable: bool`
   - `answered: bool = False`

   Violations raise `ValueError`.
2. **`ReuseVerdict(StrEnum)`**: `EXECUTE="execute"`, `REUSE="reuse"`, `PARKED="parked"`.
3. **`ReuseDecision`**, a frozen, slotted dataclass:
   - `verdict: ReuseVerdict`
   - `attempt: RecordedAttempt | None`
   - `flaky: bool`
   - `flaky_runs: tuple[str, ...]`
   - `reason: str`
4. **`TestReusePolicy(pass_ttl: timedelta, fail_ttl: timedelta)`.** A negative ttl raises
   `ValueError`.

   `decide(self, attempts: Sequence[RecordedAttempt], *, now: datetime, fresh: bool, grant: bool) -> ReuseDecision`
   requires a timezone-aware `now`, else `ValueError`. It sorts attempts by `attempt`, and
   takes the **terminal** attempts, those whose `outcome is not None`. `latest` is the
   last terminal attempt. It then applies these rules in order:
   1. `latest` exists, `latest.outcome.is_dead_letter()`, `not latest.answered` and
      `not grant` → `PARKED`, with `attempt=latest` and the reason
      ``f"run {latest.run_id} ended {latest.outcome.value}; requeue it with `vibey test requeue {latest.run_id}`"``.
   2. `grant` → `EXECUTE`, "a requeue granted a new run". Otherwise `fresh` → `EXECUTE`,
      "a fresh run was requested".
   3. Among the terminal attempts with `reusable` set and `outcome.is_reusable()`: if both
      `PASSED` and `FAILED` occur → `EXECUTE` with `flaky=True`. `flaky_runs` is the run
      ids of the latest passed and the latest failed attempt, in that order. The reason is
      `f"this input has both passed (run {p}) and failed (run {f}); the evidence is contradictory, so it runs again"`.
   4. No `latest` → `EXECUTE`, "no recorded result for this input".
   5. `latest.reusable` is false, or `latest.outcome.is_reusable()` is false → `EXECUTE`,
      "the latest recorded run of this input is not reusable".
   6. The ttl is `pass_ttl` when `latest.outcome is PASSED`, else `fail_ttl`.
      `now - latest.recorded_at <= ttl` → `REUSE` with `attempt=latest`, and the reason
      `f"reusing run {latest.run_id}, recorded {latest.recorded_at.isoformat()}"`.
      Otherwise → `EXECUTE`,
      `f"the recorded result from {latest.recorded_at.isoformat()} has expired"`.

   `flaky` is `False` and `flaky_runs` is empty in every rule except 3.
5. **The interface** is `TestReusePolicyInterface`, a runtime-checkable Protocol with
   `decide`.

## Where to change
- The new module and its interface, in the style of T01.

## Acceptance criteria
- [ ] Every rule has a test, and rule order is proven: grant beats parked; fresh does not beat parked; parked beats flaky.
- [ ] Running attempts (`outcome is None`) never influence the decision.
- [ ] Attempts are ordered by `attempt`, not by list position.
- [ ] 100% domain coverage.

## Tests to write first (TDD)
- `tests/domain/test_test_reuse.py`:
  - `test_unanswered_dead_letter_parks_the_key`
  - `test_answered_dead_letter_does_not_park`
  - `test_grant_runs_a_parked_key`
  - `test_fresh_does_not_run_a_parked_key`
  - `test_fresh_executes_otherwise`
  - `test_pass_and_fail_mark_the_key_flaky`
  - `test_no_record_executes`
  - `test_unreusable_latest_executes`
  - `test_pass_inside_its_window_is_reused`
  - `test_fail_inside_its_shorter_window_is_reused`
  - `test_expired_results_execute` (parametrized pass and fail)
  - `test_running_attempts_are_ignored`
  - `test_attempts_are_sorted_by_number`
  - `test_naive_now_and_negative_ttl_are_rejected`
  - `test_policy_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Where attempts come from (T10).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T03 — test-harness-messages

**Lane card.**

- **Depends on:** T01.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/domain/test_harness_protocol.py` (new)
  - `src/vibey/domain/interfaces/test_harness_protocol_interface.py` (new)
  - `src/vibey/domain/errors.py` (one new exception, appended at the end)
  - `tests/domain/test_test_harness_protocol.py` (new)
- **Shares a file with:** `domain/errors.py` (R06, R19 and T15 also append one exception each).
- **Must keep passing unchanged:**
  - `tests/domain/test_domain_purity.py`
  - every test under `tests/domain/`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(domain): the test harness's request and answer, and their strict codec

## Why
ADR-0045 §4 and §12. A request crosses a process boundary in both backends:
- as a file handed to a detached supervisor (`local`);
- as an AMQP message (`rabbitmq`).

The answer comes back the same way. Like ADR-0044's run protocol (lane R19), the
messages are pure, versioned and strictly decoded. An unknown key is refused rather than
guessed at, so nothing can smuggle a field in.

The raw values of the pass-through variables travel in the request, because the child
needs them. The request also proves its own digests: `environment.env` must be the
digests of those values.

## Required behaviour
1. **`AnswerStatus(StrEnum)`**: `EXECUTED="executed"`, `REUSED="reused"`,
   `PARKED="parked"`, `SATURATED="saturated"`, `STILL_RUNNING="still_running"`.
2. **`GateReport`**, a frozen, slotted dataclass:
   - `include: str`
   - `fail_under: int`
   - `passed: bool`
   - `exit_code: int`
   - `output: str`
3. **`TestRunRequest`**, a frozen, slotted dataclass:
   - `request_id: UUID`
   - `cwd: str`, which must be absolute (`PurePosixPath(cwd).is_absolute()`)
   - `selection: TestSelection`
   - `environment: TestEnvironment`
   - `env: tuple[tuple[str, str], ...]`, which is `(name, raw value)`, sorted and unique
   - `fresh: bool`
   - `grant: bool`
   - `requested_at: datetime`, timezone-aware
   - `start_by: datetime`, timezone-aware and ≥ `requested_at`
   - `requester: str`, non-empty

   `environment.env` must equal `tuple((n, ValueDigest.of(v)) for n, v in env)`, else
   `ValueError("the environment's digests do not match the request's values")`.
4. **`TestRunResult`** (the answer), a frozen, slotted dataclass:
   - `request_id: UUID`
   - `status: AnswerStatus`
   - `backend: str`, non-empty
   - `run_id: UUID | None`
   - `key: str | None`
   - `outcome: TestOutcome | None`
   - `exit_code: int | None`
   - `flaky: bool`
   - `flaky_runs: tuple[str, ...]`
   - `recorded_at: datetime | None`, timezone-aware when set
   - `tested_tree: str | None`
   - `output_tail: str`
   - `gate_reports: tuple[GateReport, ...]`
   - `detail: str`
   - `log_path: str | None`

   Consistency, else `ValueError`:
   - `EXECUTED` and `REUSED` need `run_id`, `key` and `outcome`;
   - `PARKED` needs `run_id`;
   - `SATURATED` and `STILL_RUNNING` need `outcome is None`.
5. **`TestHarnessCodec`**:
   - `encode(message: TestRunRequest | TestRunResult) -> dict[str, object]`;
   - `decode(raw: Mapping[str, object]) -> TestRunRequest | TestRunResult`, which
     dispatches on `schema`: `vibey.test.request/1` or `vibey.test.result/1`;
   - `to_bytes(message) -> bytes` (UTF-8 JSON, `sort_keys=True`);
   - `from_bytes(data: bytes)`;
   - the public helpers `encode_selection`, `decode_selection`, `encode_environment`,
     `decode_environment`, `encode_gate_report` and `decode_gate_report`, which T04 reuses.

   The encoded shapes are exact:
   ```json
   {"schema": "vibey.test.request/1", "request_id": "<uuid>", "cwd": "/abs",
    "selection": {"command": ["uv","run","--no-sync","pytest"], "argv": ["-q"],
                  "gates": [{"include": "src/vibey/domain/*", "fail_under": 100}]},
    "environment": {"python": "cpython-3.12.7-darwin-arm64", "distributions": "<hex>",
                    "database": "17.2", "env": [["VIBEY_TEST_DATABASE_URL", "<hex>"]]},
    "env": [["VIBEY_TEST_DATABASE_URL", "postgresql://..."]],
    "fresh": false, "grant": false,
    "requested_at": "2026-09-22T12:00:00+00:00", "start_by": "2026-09-22T13:00:00+00:00",
    "requester": "adam@laptop:4242"}
   ```
   ```json
   {"schema": "vibey.test.result/1", "request_id": "<uuid>", "status": "executed",
    "backend": "local", "run_id": "<uuid>", "key": "<hex>", "outcome": "passed",
    "exit_code": 0, "flaky": false, "flaky_runs": [],
    "recorded_at": "2026-09-22T12:04:19+00:00", "tested_tree": "wt1:<hex>",
    "output_tail": "...", "gate_reports": [{"include": "src/vibey/domain/*",
    "fail_under": 100, "passed": true, "exit_code": 0, "output": "..."}],
    "detail": "", "log_path": "/.../logs/<uuid>.log"}
   ```
   Datetimes are written with `isoformat()` and read with `datetime.fromisoformat`.
6. **Strict decoding.** The following raise the new
   `MalformedTestHarnessMessage(VibeyError)` (add it to `src/vibey/domain/errors.py`,
   copying the style of the existing classes):
   - an unknown schema;
   - a missing key;
   - **any extra key**;
   - a wrong JSON type (a bool is not an int);
   - an invalid UUID or enum value;
   - a naive datetime;
   - a `ValueError` from a constructor.

   `from_bytes` also raises it on invalid UTF-8 or JSON.
7. **The interface** is `TestHarnessCodecInterface`, with every public method.

## Where to change
- The new module and interface. Copy the strict-codec style R19 specifies
  (`specs/rabbitmq-lanes.md`, lane R19, behaviour 4). If R19 has landed, read
  `src/vibey/domain/run_protocol.py` and copy it. It is not a dependency.
- `src/vibey/domain/errors.py`: append the exception.

## Acceptance criteria
- [ ] Both message types round-trip through `to_bytes` and `from_bytes`, with every optional field both set and `None`.
- [ ] Every malformation in behaviour 6 is rejected, each by its own test case.
- [ ] A request whose digests do not match its values is rejected, both at construction and on decode.
- [ ] 100% domain coverage.

## Tests to write first (TDD)
- `tests/domain/test_test_harness_protocol.py`:
  - `test_request_round_trip`
  - `test_result_round_trip_for_each_status` (parametrized)
  - `test_decode_rejects_each_malformation` (parametrized: unknown schema, missing key, extra key, bool for int, bad uuid, bad enum, naive datetime)
  - `test_request_digests_must_match_values`
  - `test_result_status_consistency` (parametrized)
  - `test_from_bytes_rejects_invalid_json`
  - `test_codec_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Records and dead letters (T04).
- Any transport (T10, T23, T24).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T04 — test-run-records

**Lane card.**

- **Depends on:** T02, T03.
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/domain/test_run_record.py` (new)
  - `src/vibey/domain/interfaces/test_run_record_interface.py` (new)
  - `tests/domain/test_test_run_record.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - `tests/domain/test_domain_purity.py`
  - T01–T03 tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(domain): the record of a test run's attempt, its dead letter and the answer to it

## Why
ADR-0045 §9 keeps the evidence of every attempt, and moves a crashed, timed-out or
unexecutable run to a dead letter "with its evidence, where a human or a repair lane can
see it" (8.e).

A record is mutable only while it is running. Once terminal it is never rewritten, and
an answer to a dead letter is a separate object, never an edit. That is the same
discipline the ledger keeps (CLAUDE.md, "the ledger is append-only"), although these
records are not the ledger.

## Required behaviour
1. **`TestRunRecord`**, a frozen, slotted dataclass, with fields in this order:
   - `run_id: UUID`
   - `request_id: UUID`
   - `key: str`
   - `attempt: int`, ≥ 0 (0 means "not yet numbered"; the store assigns the number)
   - `cwd: str`
   - `selection: TestSelection`
   - `environment: TestEnvironment`
   - `requester: str`
   - `instance: str`
   - `pid: int`
   - `delivery_count: int`
   - `started_at: datetime`, timezone-aware
   - `tree_before: str`
   - `load_before: MachineLoad | None`
   - `log_path: str`
   - `outcome: TestOutcome | None = None`
   - `exit_code: int | None = None`
   - `timed_out: bool = False`
   - `reusable: bool = False`
   - `tree_after: str | None = None`
   - `finished_at: datetime | None = None`
   - `duration_seconds: float | None = None`
   - `load_after: MachineLoad | None = None`
   - `output_tail: str = ""`
   - `gate_reports: tuple[GateReport, ...] = ()`
   - `detail: str = ""`
   - `coverage_data: str | None = None`

   Invariants, else `ValueError`:
   - a running record (`outcome is None`) has `finished_at is None` and `reusable is False`;
   - a terminal record has a timezone-aware `finished_at` ≥ `started_at`;
   - `reusable` implies `outcome.is_reusable()`, `tree_after == tree_before` and
     `selection.reusable`.
2. **`TestRunRecord.finish(...)`** takes these keyword arguments: `outcome`, `exit_code`,
   `timed_out`, `tree_after`, `finished_at`, `duration_seconds`, `load_after`,
   `output_tail`, `gate_reports`, `detail` and `coverage_data`. It returns a
   `dataclasses.replace` copy with
   `reusable = outcome.is_reusable() and tree_after == self.tree_before and self.selection.reusable`.
   Finishing a terminal record raises `ValueError`.
3. **`TestRunRecord.as_attempt(*, answered: bool = False) -> RecordedAttempt`** returns
   `RecordedAttempt(str(run_id), attempt, outcome, finished_at, reusable, answered)`.
4. **`DeadLetter`**, a frozen, slotted dataclass:
   - `run_id: UUID`
   - `request_id: UUID`
   - `cwd: str`
   - `selection: TestSelection`
   - `env_names: tuple[str, ...]`
   - `requester: str`
   - `outcome: TestOutcome`, which must satisfy `is_dead_letter()`
   - `reason: str`, non-empty
   - `record: TestRunRecord | None`
   - `dead_lettered_at: datetime`, timezone-aware

   The classmethod `from_request(request, *, run_id, outcome, reason, record, at)` copies
   `cwd`, `selection`, the env **names** only, and `requester`.
5. **`DeadLetterAnswer`**, a frozen, slotted dataclass:
   - `run_id: UUID`
   - `answered_by: str`
   - `answered_at: datetime`, timezone-aware
   - `requeued_request_id: UUID`
6. **`TestRunRecordCodec(messages: TestHarnessCodecInterface)`**:
   - `encode` and `decode` for all three types, under the schemas `vibey.test.record/1`,
     `vibey.test.dead_letter/1` and `vibey.test.dead_letter_answer/1`;
   - `to_bytes` and `from_bytes`;
   - `MachineLoad` is encoded as `{"load1": ..., "load5": ..., "load15": ..., "cpu_count": ...}`
     or `null`;
   - nested selections, environments and gate reports use T03's helpers.

   It is as strict as T03, raising `MalformedTestHarnessMessage`.
7. **The interface** is `TestRunRecordCodecInterface`.

## Where to change
- The new module and interface.
- Reuse T03's codec helpers by composition. Do not copy them.

## Acceptance criteria
- [ ] `finish` computes `reusable` for each combination of outcome, tree change and selection reusability.
- [ ] Each invariant is enforced.
- [ ] All three types round-trip, and a record round-trips both while running and when finished.
- [ ] A dead letter never carries a raw env value (`from_request` keeps names only).
- [ ] 100% domain coverage.

## Tests to write first (TDD)
- `tests/domain/test_test_run_record.py`:
  - `test_finish_computes_reusable` (parametrized)
  - `test_finishing_a_terminal_record_is_refused`
  - `test_record_invariants` (parametrized)
  - `test_as_attempt_carries_the_answered_flag`
  - `test_dead_letter_requires_a_dead_letter_outcome`
  - `test_dead_letter_from_request_keeps_env_names_only`
  - `test_round_trips` (parametrized over the three types, and over a running and a finished record)
  - `test_decode_rejects_extra_and_missing_keys`
  - `test_codec_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Storing records (T10).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T05 — test-harness-config

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/domain/config.py`
  - `src/vibey/domain/interfaces/config_interface.py`
  - `src/vibey/infrastructure/test_harness/__init__.py` (new; a docstring only)
  - `src/vibey/infrastructure/test_harness/settings.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/__init__.py` (new; a docstring only)
  - `src/vibey/infrastructure/test_harness/interfaces/settings_interface.py` (new)
  - `.importlinter`
  - `tests/domain/test_config.py` (new tests, appended)
  - `tests/infrastructure/test_harness/__init__.py` (new, empty)
  - `tests/infrastructure/test_harness/test_settings.py` (new)
- **Shares a file with:**
  - `domain/config.py` (R01 before, R34 and T28 after);
  - `.importlinter` (R03, R21, R12). Append your line at the end of the list.
- **Must keep passing unchanged:**
  - every existing test in `tests/domain/test_config.py` and `tests/infrastructure/test_config_loader.py`
  - `tests/infrastructure/test_sovereign_surfaces.py`
  - `tests/meta/test_import_contracts_bind.py`
  - `tests/domain/test_domain_purity.py`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(config): declare the test harness's keys and resolve them without a vibey.toml

## Why
Sub-doctrine 12.c (`src/vibey_tools/gh/docs/doctrines.md:320`) says every tunable is a key.
ADR-0045 §14 lists the harness's keys.

The harness must also run where no `vibey.toml` exists, which includes this repository's
own root: a push hook has no project file. So resolution is its own step:
- the environment beats the file, and the file beats the default;
- the default `state_dir` follows `$XDG_STATE_HOME`;
- the default instance name is the sanitized host name.

This lane only declares and resolves the keys. Nothing reads them until T06 onwards. It
also creates the `infrastructure/test_harness/` package and its `interfaces` package,
which every later infrastructure lane adds to.

## Required behaviour
1. **`TestHarnessConfig`** in `domain/config.py`, a frozen, slotted dataclass with these
   defaults and constraints. Every violation raises `ConfigError("test_harness.<key>", ...)`.

   | field | default | constraint |
   |---|---|---|
   | `backend: str` | `"auto"` | `auto`, `local` or `rabbitmq` |
   | `state_dir: str \| None` | `None` | when set, absolute after `~` expansion (`os.path.expanduser` is not I/O; use `PurePosixPath` for the check) |
   | `root: str` | `"/"` | absolute |
   | `instance: str \| None` | `None` | when set, matches `^[a-z0-9][a-z0-9-]{0,62}$` |
   | `command: tuple[str, ...]` | `("uv", "run", "--no-sync", "pytest")` | non-empty |
   | `coverage_command: tuple[str, ...]` | `("uv", "run", "--no-sync", "coverage")` | non-empty |
   | `base_env: tuple[str, ...]` | `("PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_*", "TMPDIR", "TZ", "SHELL", "TERM", "XDG_*", "UV_*")` | valid `EnvNamePatterns` (T01) |
   | `pass_env: tuple[str, ...]` | `("VIBEY_TEST_*", "VIBEY_QUEUE_BACKEND", "VIBEY_ENGINE_INVOCATION", "PYTEST_ADDOPTS")` | valid patterns, and none may match the name `VIBEY_HARNESS_RUN` |
   | `database_env: str` | `"VIBEY_TEST_DATABASE_URL"` | an env-var name, or `""` |
   | `tree_exclude: tuple[str, ...]` | `(".hypothesis/",)` | each relative (does not start with `/`) |
   | `pass_ttl_seconds: int` | `86400` | ≥ 0 |
   | `fail_ttl_seconds: int` | `900` | ≥ 0 |
   | `run_bound_seconds: int` | `3600` | ≥ 60 |
   | `queue_wait_seconds: int` | `3600` | ≥ 1 |
   | `wait_seconds: int` | `7200` | ≥ 1 |
   | `output_tail_bytes: int` | `65536` | 1024–10485760 |
   | `retention_days: int` | `14` | ≥ 1 |
   | `delivery_limit: int` | `3` | 1–100 |
   | `reconcile_interval_seconds: int` | `30` | ≥ 1 |
   | `route_engines: str` | `"off"` | `off`, `locked` or `queue` (use `TestRouteMode.parse`) |
   | `engine_wait_seconds: int` | `110` | ≥ 1 |

   It is parsed from `[test_harness]` by a new `_parse_test_harness(data)`, using
   `_optional` (`config.py:358-364`); lists become tuples. `VibeyConfig` (`:319-342`)
   gains `test_harness: TestHarnessConfig = field(default_factory=TestHarnessConfig)`,
   and `parse_config` (`:652`) fills it.
2. **`TestHarnessConfigInterface`** in `config_interface.py`: read-only property Protocols,
   copying `TelemetryConfigInterface` (`:31-36`).
3. **`TestHarnessSettings`** in `infrastructure/test_harness/settings.py`, a frozen,
   slotted dataclass of *resolved* values:
   - `backend: str`
   - `state_dir: Path`
   - `root: Path`
   - `instance: str`
   - `command`, `coverage_command`
   - `base_env: EnvNamePatterns`, `pass_env: EnvNamePatterns`
   - `database_env: str`
   - `tree_exclude`
   - `pass_ttl: timedelta`, `fail_ttl: timedelta`
   - `run_bound_seconds`, `queue_wait_seconds`, `wait_seconds`
   - `output_tail_bytes`
   - `retention: timedelta`
   - `delivery_limit`, `reconcile_interval_seconds`
   - `route_engines: TestRouteMode`
   - `engine_wait_seconds`

   It has the property `lock_path -> Path` (`state_dir / "machine.lock"`) and the
   classmethod
   `from_sources(config: VibeyConfig | None, environ: Mapping[str, str], *, hostname: str | None = None) -> TestHarnessSettings`.
   The base is `config.test_harness`, or `TestHarnessConfig()` when `config` is `None`.

   These environment variables override the base. An empty or whitespace-only value
   counts as unset, and a bad value raises `ValueError` naming the variable.

   | variable | overrides |
   |---|---|
   | `VIBEY_HARNESS_BACKEND` | `backend`, validated as in behaviour 1 |
   | `VIBEY_HARNESS_STATE_DIR` | `state_dir` |
   | `VIBEY_HARNESS_ROOT` | `root` |
   | `VIBEY_HARNESS_INSTANCE` | `instance` |
   | `VIBEY_HARNESS_WAIT_SECONDS` | `wait_seconds`, an int ≥ 1 |

   The defaults resolve like this:
   - `state_dir`: `Path(environ["XDG_STATE_HOME"]) / "vibey" / "test-harness"` when that
     variable is set and absolute; otherwise `Path(environ.get("HOME") or Path.home()) / ".local" / "state" / "vibey" / "test-harness"`.
     A configured value is `Path(value).expanduser()`.
   - `instance`: `InstanceName.sanitize(hostname or socket.gethostname())`.
4. **`InstanceName.sanitize(raw: str) -> str`**, a static method in `settings.py`:
   1. lower-case the input;
   2. replace every character outside `[a-z0-9-]` with `-`;
   3. strip leading and trailing `-`;
   4. truncate to 63 characters;
   5. return `"localhost"` if the result is empty.
5. **Interfaces.** `interfaces/settings_interface.py` declares
   `TestHarnessSettingsInterface` and `InstanceNameInterface`.
6. **`.importlinter`.** Append `vibey.infrastructure.test_harness.interfaces` as the last
   line of `source_modules` in `[importlinter:contract:infrastructure-interfaces-declare-only]`
   (`.importlinter:108-120` and onwards).
7. **No rows in `_SURFACE_ENV_VARS`** (`infrastructure/config_loader.py:17-58`). The
   harness resolves its own environment, because it must work with no file at all.

## Where to change
- `src/vibey/domain/config.py`: copy `TelemetryConfig` (`:166-171`) and `_parse_telemetry`
  (`:484-493`); wire into `VibeyConfig` and `parse_config`.
- The new package. Copy the package-docstring style of `src/vibey/infrastructure/bus/__init__.py`.
- `.importlinter`.

## Acceptance criteria
- [ ] `parse_config({"project": {"name": "x"}}).test_harness == TestHarnessConfig()`.
- [ ] Each constraint in behaviour 1 raises `ConfigError` naming `test_harness.<key>`.
- [ ] `pass_env = ["VIBEY_*"]` is refused, because it would match `VIBEY_HARNESS_RUN`.
- [ ] `from_sources` precedence (env > file > default) holds for each overridable key.
- [ ] `state_dir` follows `XDG_STATE_HOME`, and otherwise `HOME`.
- [ ] `lint-imports` and `tests/meta/test_import_contracts_bind.py` pass.
- [ ] 100% coverage on `domain/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/domain/test_config.py` (appended):
  - `test_test_harness_defaults`
  - `test_test_harness_rejects_each_bad_value` (parametrized over every row of behaviour 1)
  - `test_test_harness_pass_env_may_not_reach_the_run_marker`
  - `test_test_harness_config_satisfies_its_interface`
- `tests/infrastructure/test_harness/test_settings.py`:
  - `test_defaults_without_a_config`
  - `test_env_beats_config_beats_default` (parametrized over the five variables)
  - `test_blank_env_values_are_unset`
  - `test_bad_env_values_name_the_variable`
  - `test_state_dir_follows_xdg_then_home`
  - `test_instance_sanitize_table` (parametrized: `"Adams-MacBook.local"` → `"adams-macbook-local"`, `"___"` → `"localhost"`, a 70-character name → 63 characters)
  - `test_lock_path_is_under_the_state_dir`
  - `test_settings_satisfy_their_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_config.py tests/infrastructure/test_config_loader.py tests/infrastructure/test_sovereign_surfaces.py tests/infrastructure/test_harness tests/meta/test_import_contracts_bind.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Reading the keys at runtime (T06 onwards).
- Any `[bus]` key; R01 owns them.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T06 — machine-lock

**Lane card.**

- **Depends on:** T05.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/machine_lock.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/machine_lock_interface.py` (new)
  - `tests/infrastructure/test_harness/test_machine_lock.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - T05's tests
  - `tests/infrastructure/process/*`
  - all protected tests
- **Standing constraints:** see the header list. Every test uses a lock path under `tmp_path`.

## Title
feat(test-harness): one test run at a time on a machine, held by every process of the run

## Why
8.e: "one test run at a time on one machine". ADR-0045 §2 makes an exclusive `flock` on
`<state_dir>/machine.lock` the floor that both backends and the pytest plugin take.

The descriptor is handed to the run's child through `pass_fds`. The lock is therefore
held until the **last** process of the run exits, even if the process that took it is
SIGKILLed. That gives the invariant the whole design relies on: *a lock holder that
finds an attempt recorded `running` knows its recorder is dead*.

A holder file names who holds the lock, so `vibey test status` and a waiting requester
can say whom they are waiting for.

## Required behaviour
1. **`MachineLock(path: Path, *, poll_seconds: float = 0.2)`.**
   `async def acquire(self, *, timeout_seconds: float, holder: Mapping[str, object]) -> MachineLockHold | None`:
   1. `path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)`;
   2. `fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)`;
   3. in a loop, try `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)`. On
      `BlockingIOError`, if `time.monotonic() - start >= timeout_seconds`, then
      `os.close(fd)` and return `None`. Otherwise `await asyncio.sleep(poll_seconds)`;
   4. on success, write `<path>.holder.json` atomically (a temporary file in the same
      directory, then `os.replace`), mode 0o600, as
      `{"pid": os.getpid(), "since": <UTC isoformat>, **holder}`;
   5. return `MachineLockHold(fd, holder_path, os.getpid())`.

   `timeout_seconds == 0` means a single try.
2. **`MachineLockHold`** has:
   - the property `fd -> int`;
   - `release(self) -> None`, which is idempotent. It removes the holder file only if that
     file still names this pid, then calls `fcntl.flock(fd, fcntl.LOCK_UN)` and
     `os.close(fd)`.

   Put this in a docstring: `release()` must be called only after every process that
   inherited the descriptor has exited, because `LOCK_UN` releases the open file
   description they share.
3. **`holder(self) -> dict[str, object] | None`** reads and parses the holder file, and
   adds `"alive": bool` from `os.kill(pid, 0)`: `ProcessLookupError` gives `False`,
   `PermissionError` gives `True`. It returns `None` when the file is missing or
   malformed.
4. **Interfaces.** `MachineLockInterface` (`acquire`, `holder`) and
   `MachineLockHoldInterface` (`fd`, `release`).

## Where to change
- The new module and its interface.
- Use `fcntl` and `os` from the stdlib; no new dependency.

## Acceptance criteria
- [ ] A second descriptor on the same path cannot take the lock while the first holds it. That is true within one process, because `flock` locks an open file description.
- [ ] A child that inherited the descriptor (`pass_fds`) keeps the lock after the parent closes its own descriptor **without** `LOCK_UN`, and the lock frees when the child exits.
- [ ] The holder file names the pid and the given fields, and reports liveness.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_machine_lock.py`:
  - `test_acquire_and_release_round_trip`
  - `test_second_acquire_times_out_while_held`
  - `test_zero_timeout_is_a_single_try`
  - `test_lock_survives_the_parent_when_a_child_inherits_it`: acquire, spawn
    `subprocess.Popen([sys.executable, "-c", "import time; time.sleep(2)"], pass_fds=(hold.fd,))`,
    then `os.close(hold.fd)`. Assert a fresh `acquire(timeout_seconds=0.3)` returns
    `None`. Wait for the child, then assert `acquire(timeout_seconds=1)` succeeds.
  - `test_holder_reports_pid_fields_and_liveness`
  - `test_holder_is_none_when_missing_or_malformed`
  - `test_release_is_idempotent_and_keeps_a_foreign_holder_file`
  - `test_lock_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Using the lock (T07, T13, T14).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T07 — pytest-lock-route

**Lane card.**

- **Depends on:** T05, T06.
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/cli/pytest_route.py` (new)
  - `src/vibey/cli/interfaces/pytest_route_interface.py` (new)
  - `pyproject.toml` (an entry-point table and one ini value)
  - `tests/cli/test_pytest_route.py` (new)
- **Shares a file with:** `pyproject.toml` (R03 before; T28 after); `cli/pytest_route.py` (T17 after).
- **Must keep passing unchanged:**
  - **the whole suite.** The plugin loads in every pytest run in this venv, and after this lane every root run takes the machine lock.
  - `tests/meta/*`, in particular `test_githooks_reach_the_framework.py`
  - `tests/cli/*`
  - `uv lock --check`
  - all protected tests
- **Standing constraints:** see the header list. The subprocess tests use a `tmp_path` state dir and strip `VIBEY_HARNESS_RUN` and `VIBEY_HARNESS_ROUTE` from the child environment.

## Title
feat(test-harness): every root pytest run takes the machine's test lock

## Why
8.e: "Nothing starts a second test run beside a running one". Two concurrent runs are
the operator's evidence:
- two coverage runs in one directory consumed each other's shards
  (`[tool.coverage.run] parallel = true`, `pyproject.toml:304-307`);
- a pre-push suite collided with other work.

The pre-push hook runs the suite up to three times per push (`.pre-commit-config.yaml:20-23`),
and storm lanes run `uv run pytest` through qwenloop's shell, beside the operator's pushes.

ADR-0045 §10 and §15 make a pytest plugin the one route every invocation passes through,
wherever vibey is installed. This lane ships its `locked` mode, which serializes whole
runs before any queue exists, and switches it on for this repository. The plugin works
like this:
- **Registration.** It is registered through a `pytest11` entry point as a class
  *instance*, so its hooks are methods (9.b).
- **Short-circuit.** It runs in `pytest_cmdline_main` with `tryfirst=True`, which is
  before any conftest's `pytest_configure`, so no database has been cloned yet.
- **Mode.** An ini key sets its mode, and `VIBEY_HARNESS_ROUTE` overrides the ini.
- **Re-entrancy.** It marks its own process with `VIBEY_HARNESS_RUN`, so xdist workers
  and nested pytest runs pass through.

## Required behaviour
1. **`class PytestHarnessRoute`** in `src/vibey/cli/pytest_route.py`:
   - `INI_NAME: ClassVar[str] = "vibey_harness_route"`.
   - `PASS_THROUGH: ClassVar[frozenset[str]]` is exactly `--help`, `-h`, `--version`,
     `-V`, `--fixtures`, `--fixtures-per-test`, `--markers`, `--collect-only` and `--co`.
   - `__init__(self, environ: MutableMapping[str, str] | None = None, *, settings_loader: Callable[[Mapping[str, str]], TestHarnessSettingsInterface] | None = None, lock_factory: Callable[[Path], MachineLockInterface] | None = None, stderr: TextIO | None = None)`.
     The defaults are `os.environ`,
     `lambda env: TestHarnessSettings.from_sources(None, env)`, `MachineLock` and
     `sys.stderr`. The environment is read at call time, never cached.
   - `pytest_addoption(self, parser: pytest.Parser) -> None` calls
     `parser.addini(self.INI_NAME, "how pytest runs reach vibey's test harness: off, locked or queue (ADR-0045)", default="off")`.
   - `mode(self, config: pytest.Config) -> TestRouteMode` uses `VIBEY_HARNESS_ROUTE` when
     it is set and non-blank, otherwise `config.getini(INI_NAME)`, and parses the value
     with `TestRouteMode.parse`. A `ValueError` becomes `pytest.UsageError(str(exc))`.
   - `@pytest.hookimpl(tryfirst=True) def pytest_cmdline_main(self, config) -> int | None`
     applies these steps in order:
     1. `"VIBEY_HARNESS_RUN"` is in the environment → `None`;
     2. any item of `config.invocation_params.args` is in `PASS_THROUGH` → `None`;
     3. `OFF` → `None`. When the ini value is not `off` and the environment forced
        `off`, first write one line to stderr:
        `vibey test-harness: routing bypassed by VIBEY_HARNESS_ROUTE=off`;
     4. `LOCKED` → `self._locked(config)`;
     5. `QUEUE` → raise `pytest.UsageError("vibey_harness_route = queue is not available in this build; use off or locked")`.
   - `_locked(config) -> int | None` does the following:
     1. It builds `settings = settings_loader(environ)` and
        `lock = lock_factory(settings.lock_path)`.
     2. It calls
        `hold = asyncio.run(lock.acquire(timeout_seconds=settings.wait_seconds, holder={"mode": "locked", "cwd": str(config.invocation_params.dir), "argv": list(config.invocation_params.args)}))`.
     3. If `hold` is `None`, it writes
        `vibey test-harness: the machine's test lock is held by pid <pid> since <since>; waited <n>s. Run the same command again, or bypass with VIBEY_HARNESS_ROUTE=off.`
        to stderr, using `lock.holder()` (or "an unknown process" when that is `None`),
        and returns `75`.
     4. Otherwise it keeps `self._hold = hold` (never released: the OS releases the lock
        when this pytest process exits), sets
        `environ["VIBEY_HARNESS_RUN"] = f"locked-{os.getpid()}"`, writes
        `vibey test-harness: locked (one test run at a time on this machine)` to stderr,
        and returns `None`.
2. **`PLUGIN = PytestHarnessRoute()`**, a module-level binding, with a comment giving the
   reason: "pytest11 entry points name an object; pluggy registers this instance's
   methods as hooks (ADR-0045 §10)".
3. **`pyproject.toml`.**
   - Immediately after the `[project.scripts]` table (`:69-81`), add:
     ```toml
     # The test harness's pytest route (ADR-0045 §10): inert unless an ini or
     # VIBEY_HARNESS_ROUTE switches it on.
     [project.entry-points.pytest11]
     vibey_harness_route = "vibey.cli.pytest_route:PLUGIN"
     ```
   - In `[tool.pytest.ini_options]` (`:259-270`), add
     `vibey_harness_route = "locked"`, with a comment: 8.e's one run at a time on a
     machine; `VIBEY_HARNESS_ROUTE=off` bypasses it.
   - Then run `uv sync --extra dev`, so the editable install registers the entry point.
     If `uv lock --check` fails, run `uv lock` and say so in the commit body.
4. **The interface** is `PytestHarnessRouteInterface`, with `mode`, `pytest_addoption`
   and `pytest_cmdline_main`.

## Where to change
- The new module and interface. The `cli/` layer may import `vibey.infrastructure`, as
  `cli/main.py:30-49` does.
- `pyproject.toml`.

## Acceptance criteria
- [ ] `importlib.metadata.entry_points(group="pytest11")` holds `vibey_harness_route = vibey.cli.pytest_route:PLUGIN`.
- [ ] A subprocess pytest in a scratch project with `vibey_harness_route = locked` sees `VIBEY_HARNESS_RUN` starting with `locked-`, and exits 0.
- [ ] While the test process holds the same (tmp) lock, that subprocess, with `VIBEY_HARNESS_WAIT_SECONDS=1`, exits 75 and names the holder's pid.
- [ ] The whole suite passes with the root ini set to `locked`.
- [ ] 100% `cli/` coverage.

## Tests to write first (TDD)
- `tests/cli/test_pytest_route.py`. The unit tests use a fake config,
  `SimpleNamespace(invocation_params=SimpleNamespace(args=(...), dir=tmp_path), getini=lambda name: value)`,
  and an injected `environ` dict:
  - `test_inside_a_run_passes_through`
  - `test_pass_through_flags` (parametrized over `PASS_THROUGH`)
  - `test_off_passes_through`
  - `test_env_beats_the_ini`
  - `test_forced_off_names_the_bypass`
  - `test_an_invalid_mode_is_a_usage_error`
  - `test_queue_is_refused_in_this_build`
  - `test_locked_holds_the_lock_and_marks_the_process`: a real `MachineLock` on `tmp_path`; afterwards a second `acquire(timeout_seconds=0.2)` returns `None`.
  - `test_locked_times_out_with_75_and_names_the_holder`
  - `test_the_entry_point_is_registered`
  - `test_end_to_end_locked_run` (a subprocess): a scratch dir with `pytest.ini`
    (`[pytest]\nvibey_harness_route = locked`) and
    `test_x.py` asserting `os.environ["VIBEY_HARNESS_RUN"].startswith("locked-")`. Run
    `[sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]` with
    `VIBEY_HARNESS_STATE_DIR` under `tmp_path` and the two variables stripped. Expect 0.
  - `test_end_to_end_waits_for_a_held_lock` (a subprocess): hold the tmp lock in the
    test, and pass `VIBEY_HARNESS_WAIT_SECONDS=1`. Expect 75 and "held by pid".

## Checks the lane must run (all must pass)
    uv lock --check
    uv sync --extra dev
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_pytest_route.py tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- `queue` mode (T17).
- `.pre-commit-config.yaml` (T18). The pre-push hooks' `uv run pytest` is serialized by this lane's ini, with no hook change.
- Tenant `pyproject.toml` files. Their CI rows have no vibey installed, and an unknown ini key would warn there.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T08 — working-tree-digest

**Lane card.**

- **Depends on:** T05.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/tree_digest.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/tree_digest_interface.py` (new)
  - `.gitignore` (one line)
  - `tests/infrastructure/test_harness/test_tree_digest.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - `tests/infrastructure/git/*` (`test_clean_env.py` in particular)
  - `tests/meta/test_githooks_reach_the_framework.py`
  - all protected tests
- **Standing constraints:** see the header list. Scratch repositories live under `tmp_path`, and their setup commands run with every `GIT_*` variable stripped.

## Title
feat(test-harness): a digest of the working tree a test run reads

## Why
8.e keys a run by "the tree" it tests. ADR-0045 §5 defines that as what `git add -A`
would record: the index, plus each modified, deleted and untracked-but-not-ignored path.

That is what a storm lane actually tests: uncommitted edits, and new test files it never
added. A HEAD tree id would miss both. The digest must also:
- write nothing to `.git` and never touch the real index, so it is safe inside a hook;
- run git with every `GIT_*` variable stripped, because a hook exports `GIT_DIR`
  (`.githooks/framework-hook.sh:35-53`).

`CleanGitEnvSubprocessExecutor` (`src/vibey/infrastructure/git/clean_env.py:22-37`)
already does that. It is the family's, so it is used (10.e).

`.hypothesis/` is not in the root `.gitignore` (`.gitignore:1-20`), although the four
runner tenants ignore it (for example `src/vibey_runners/claude/.gitignore:22`). A
Hypothesis run writes there, so without an exclusion every run would look as if it had
changed the tree it tested.

## Required behaviour
1. **`WorkingTreeDigest(executor: CommandExecutor | None = None, *, exclude: tuple[str, ...] = (".hypothesis/",), batch_size: int = 200)`.**
   `executor` defaults to `CleanGitEnvSubprocessExecutor()`. `CommandExecutor` is the
   Protocol at `src/vibey/infrastructure/interfaces/__init__.py:71-73`.

   `async def digest(self, cwd: Path) -> str`:
   1. `git -C <cwd> rev-parse --show-toplevel`. A non-zero exit returns
      `"untracked:" + uuid.uuid4().hex`, which never matches anything, so it is never
      reused. Otherwise `top` is the stripped stdout.
   2. `pathspec = (".", *(f":(exclude){p}" for p in exclude))`.
   3. `git -C <top> ls-files -s -z -- <pathspec>`. Parse each NUL-terminated record,
      `"<mode> <blob> <stage>\t<path>"`, into `entries[path] = (mode, blob if stage == "0" else f"{blob}:{stage}")`.
      For a conflicted path, keep every stage by suffixing the path with `\x00<stage>` in
      the key.
   4. `git -C <top> ls-files -z -m -d -o --exclude-standard -- <pathspec>` gives the
      changed paths. De-duplicate them. For each one:
      - if `os.path.lexists(top / path)` is false, remove `entries[path]`;
      - if the path ends with `/` (a nested repository), skip it;
      - if it is a symlink, set it to
        `("120000", "link:" + hashlib.sha256(os.readlink(...).encode()).hexdigest())`;
      - otherwise, collect it for hashing.
   5. Hash the collected paths in batches of `batch_size` with
      `git -C <top> hash-object -- <paths...>`, which prints one id per line in input
      order. The mode is `"100755"` if `os.access(p, os.X_OK)`, else `"100644"`.
   6. Build the lines `f"{mode} {blob}\t{path}"` and return
      `"wt1:" + hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()`.
   7. Any git command after step 1 that exits non-zero raises
      `WorkingTreeDigestError(RuntimeError)` carrying its stderr.
2. **The interface** is `WorkingTreeDigestInterface`, with `digest`.
3. **`.gitignore`**: add `.hypothesis/` on the line after `.coverage.*`.

## Where to change
- The new module and interface. Use `CleanGitEnvSubprocessExecutor` from
  `vibey.infrastructure.git.clean_env`, whose `execute(argv)` returns
  `CommandResult(returncode, stdout, stderr)` (`infrastructure/engines/claudeloop_process.py:28-31`).
- `.gitignore`.

## Acceptance criteria
- [ ] The same content gives the same digest. Each kind of change gives a different one: a modified tracked file, a new untracked file, a deleted file, a flipped executable bit.
- [ ] An ignored file and an excluded path (`.hypothesis/…`) do not change the digest.
- [ ] The digest equals one computed from `git add -A`'s view. In the test, build that with a temporary index: `GIT_INDEX_FILE=<tmp> git read-tree HEAD && git add -A && git ls-files -s`, then apply the same line format.
- [ ] A `GIT_DIR` in the caller's environment, pointing at another repository, does not change the result.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_tree_digest.py`. Write a helper `ScratchRepo`
  class that runs `git init -q -b main`, sets `user.name` and `user.email`, and commits.
  It uses `subprocess.run` with `{k: v for k, v in os.environ.items() if not k.startswith("GIT_")}`
  plus `GIT_CONFIG_NOSYSTEM=1`.
  - `test_same_tree_same_digest`
  - `test_modified_tracked_file_changes_the_digest`
  - `test_untracked_file_changes_it_and_an_ignored_file_does_not`
  - `test_deleted_file_changes_the_digest`
  - `test_executable_bit_changes_the_digest`
  - `test_excluded_path_does_not_change_the_digest`
  - `test_digest_matches_git_add_all_view`
  - `test_outside_a_work_tree_is_untracked_and_unique`
  - `test_callers_git_dir_is_ignored` (`monkeypatch.setenv("GIT_DIR", <another scratch repo>/.git)`)
  - `test_git_failure_raises` (a fake `CommandExecutor` that fails the second call)
  - `test_digest_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/infrastructure/git
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The key itself (T01) and its use (T13, T14).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T09 — environment-probe

**Lane card.**

- **Depends on:** T01, T05.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/environment_probe.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/environment_probe_interface.py` (new)
  - `tests/infrastructure/test_harness/test_environment_probe.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - T05's tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(test-harness): probe the environment a test run is keyed by

## Why
8.e keys a run by "the environment". ADR-0045 §5 names its parts:
- the interpreter;
- the installed distributions, which is what the run imports (`uv.lock` is tracked, so
  it is already in the tree, and a stale venv is caught only here);
- the test database's server version;
- the digests of the pass-through variables.

The probe runs in the *requester's* process, which is the interpreter the tests run in.
A database that cannot be reached is keyed as `unreachable`, so the failure it causes
stops matching once the database is back.

## Required behaviour
1. **`EnvironmentProbe(*, pass_env: EnvNamePatternsInterface, database_env: str, connector: Callable[[str], Awaitable[Any]] | None = None, distributions: Callable[[], Iterable[importlib.metadata.Distribution]] | None = None, timeout_seconds: float = 2.0)`.**
   The defaults are `asyncpg.connect` and `importlib.metadata.distributions`.
   - `python_identity(self) -> str` returns
     `f"{sys.implementation.name}-{platform.python_version()}-{sys.platform}-{platform.machine()}"`.
   - `distributions_digest(self) -> str` builds one line per distribution,
     `f"{name}=={dist.version}"`, where `name` is `dist.metadata["Name"]` lower-cased with
     runs of `-`, `_` and `.` replaced by `-`. It skips distributions with no name,
     de-duplicates and sorts the lines, and returns the sha256 hex of
     `"\n".join(lines)`.
   - `async def database_version(self, environ: Mapping[str, str]) -> str`:
     - `"unset"` when `database_env` is `""` or the variable is missing or blank;
     - otherwise, `conn = await asyncio.wait_for(connector(dsn), timeout_seconds)`, then
       `str(await conn.fetchval("SHOW server_version"))`, then `await conn.close()`;
     - any exception, including a timeout, gives `"unreachable"`.
   - `async def probe(self, environ: Mapping[str, str]) -> tuple[TestEnvironment, tuple[tuple[str, str], ...]]`
     selects `values = pass_env.select(environ)` and returns
     `(TestEnvironment.from_values(python=..., distributions=..., database=..., values=values), values)`.
2. **The interface** is `EnvironmentProbeInterface`.

## Where to change
- The new module and interface. `asyncpg` is already a runtime dependency.

## Acceptance criteria
- [ ] The distributions digest does not depend on iteration order, and changes when one version changes.
- [ ] `unset`, `unreachable` (a raising connector, and a slow one) and a version string are each produced.
- [ ] Against the suite's real test database (`VIBEY_TEST_DATABASE_URL`, which `tests/conftest.py:146-156` sets for every session), the version starts with a digit.
- [ ] Only `pass_env` names are selected.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_environment_probe.py`:
  - `test_python_identity_format` (a regex)
  - `test_distributions_digest_is_order_independent`
  - `test_distributions_digest_changes_with_a_version`
  - `test_database_unset` (parametrized: `database_env=""`, missing, blank)
  - `test_database_unreachable_on_error_and_on_timeout`
  - `test_database_version_from_a_fake_connection`
  - `test_database_version_against_the_test_database`
  - `test_probe_selects_only_pass_env_names`
  - `test_probe_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Building requests (T14).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T10 — file-run-store

**Lane card.**

- **Depends on:** T04, T05.
- **Wave:** 4.
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/file_store.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/file_store_interface.py` (new)
  - `tests/infrastructure/test_harness/test_file_store.py` (new)
- **Shares a file with:** none. Later lanes call it and do not edit it.
- **Must keep passing unchanged:**
  - T01–T05 tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(test-harness): one store per machine for requests, answers, attempts and dead letters

## Why
ADR-0045 §3 and §9:
- both backends on a machine share one store under `state_dir`, so choosing either can
  never split the record;
- a dead letter is kept "with its evidence, where a human or a repair lane can see it" (8.e);
- a terminal attempt is never rewritten;
- an answer to a dead letter is a new file.

Readers run outside the lock (the requester's fast path, `vibey test status`), so every
write is atomic. An attempt number is claimed with `os.link`, which is atomic and fails
if the name is taken, so no reader ever sees a half-written file.

## Required behaviour
1. **`FileTestRunStore(root: Path, *, messages: TestHarnessCodecInterface, records: TestRunRecordCodecInterface)`.**
   `ensure(self) -> None` creates `root` and its subdirectories `requests`, `answers`,
   `runs`, `running`, `logs`, `data`, `dead` and `malformed`, each with mode `0o700`.
   Every file is written with mode `0o600`. `AtomicFile.write(path: Path, data: bytes)`,
   a small class in the same module, writes a temporary file in the same directory, then
   calls `os.replace`.
2. **Requests** (the `local` hand-off):
   - `put_request(request) -> Path` writes `requests/<request_id>.json`;
   - `take_request(path) -> TestRunRequest` decodes it. A malformed file raises
     `MalformedTestHarnessMessage`.
3. **Answers**:
   - `put_answer(result)` writes `answers/<request_id>.json`;
   - `answer(request_id) -> TestRunResult | None`;
   - `recent_answers(limit: int) -> tuple[TestRunResult, ...]`, newest first by mtime.
     It skips files that fail to decode, and logs a warning for each.
4. **Attempts** live at `runs/<key[:2]>/<key>/<attempt:06d>.json`:
   - `begin(record) -> TestRunRecord`. It takes `n = 1 + (highest existing attempt, or 0)`,
     writes `dataclasses.replace(record, attempt=n)` to a temporary file, and calls
     `os.link(tmp, final)`. On `FileExistsError` it tries `n + 1`. It then unlinks the
     temporary file and writes the marker `running/<run_id>.json` holding
     `{"key": key, "attempt": n}`.
   - `finish(record)` requires `record.outcome is not None`. It writes the attempt file
     with `AtomicFile`, then removes the running marker.
   - `attempts(key) -> tuple[TestRunRecord, ...]`, sorted by attempt.
   - `attempts_as_recorded(key) -> tuple[RecordedAttempt, ...]`, which is
     `record.as_attempt(answered=self.is_answered(record.run_id))` for each attempt.
   - `running() -> tuple[TestRunRecord, ...]`, the attempts that have a running marker.
5. **Paths**:
   - `log_path(run_id) -> Path` is `logs/<run_id>.log`;
   - `supervisor_log_path(request_id) -> Path` is `logs/supervisor-<request_id>.log`;
   - `data_dir(run_id) -> Path` is `data/<run_id>/`, created with mode `0o700`.
6. **Dead letters**:
   - `dead_letter(letter)` creates `dead/<run_id>.json` with the same `os.link` method. If
     the file already exists, it does nothing.
   - `dead_letter_by_run(run_id) -> DeadLetter | None`.
   - `dead_letter_for_request(request_id) -> DeadLetter | None` scans `dead/*.json`,
     skipping `*.answer.json`.
   - `dead_letters(*, include_answered: bool = False) -> tuple[DeadLetter, ...]`, oldest
     first.
   - `answer_dead_letter(answer)` creates `dead/<run_id>.answer.json` with `os.link`. If
     it already exists, it raises `ValueError(f"dead letter {run_id} is already answered")`.
   - `is_answered(run_id) -> bool`.
7. **Malformed messages** (from T23):
   - `put_malformed(raw: bytes, *, message_id: str | None, reason: str, received_at: datetime) -> Path`
     writes `malformed/<uuid4>.bin` and a `.json` sidecar holding
     `{"message_id", "reason", "received_at"}`;
   - `malformed() -> tuple[Path, ...]` lists the `.bin` files.
8. **Retention.** `prune(self, *, older_than: datetime) -> int` removes files older than
   the cutoff, by mtime, and returns how many it removed. It prunes:
   - finished attempt files (never one with a running marker);
   - logs and data directories;
   - answers and requests;
   - dead letters **that are answered**, together with their answer files.

   It never removes an unanswered dead letter.
9. **The interface** is `TestRunStoreInterface`, declaring every public method above.
   Later lanes type against it.

## Where to change
- The new module and interface. Use T03's and T04's codecs.

## Acceptance criteria
- [ ] `begin` numbers attempts 1, 2, 3 per key. Two `begin` calls that race for one number, simulated by pre-creating the next file, both succeed with different numbers.
- [ ] `finish` removes the running marker, and `running()` stops listing the attempt.
- [ ] A dead letter is written once. A second write is a no-op. A second answer raises.
- [ ] `prune` keeps unanswered dead letters and running attempts, and removes everything else past the cutoff.
- [ ] Every file is `0o600` and every directory `0o700`.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_file_store.py`, with a helper that builds
  records and requests through T03 and T04:
  - `test_request_round_trip_and_malformed_request`
  - `test_answer_round_trip_and_recent_answers_order`
  - `test_begin_numbers_attempts_per_key`
  - `test_begin_survives_a_taken_number`
  - `test_finish_requires_an_outcome_and_clears_running`
  - `test_attempts_as_recorded_marks_answered_dead_letters`
  - `test_dead_letter_is_written_once`
  - `test_dead_letter_lookup_by_run_and_by_request`
  - `test_answering_twice_raises`
  - `test_malformed_messages_are_kept`
  - `test_prune_keeps_unanswered_dead_letters_and_running_attempts`
  - `test_file_modes`
  - `test_store_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- A PostgreSQL store. ADR-0045 §3 explains why the file store is the design; the port admits one later.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T11 — run-executor

**Lane card.**

- **Depends on:** T01, T05.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/executor.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/executor_interface.py` (new)
  - `tests/infrastructure/test_harness/test_executor.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - `tests/infrastructure/process/*` (`test_reaper.py` in particular)
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(test-harness): execute one test run, bounded, logged and killed as a group

## Why
ADR-0045 §4 fixes how a run executes:
- the configured command plus argv, in `cwd`;
- in a session of its own, so the whole group can be killed;
- all output to one log file;
- bounded by `run_bound_seconds`;
- in an environment that is **exactly** `base_env` from the instance, plus the
  request's pass-through values, plus the run marker, plus a private `COVERAGE_FILE`.

A private `COVERAGE_FILE` is what removes the second piece of evidence: two coverage
runs in one directory merged each other's `.coverage.*` shards
(`pyproject.toml:304-307`, `parallel = true`).

The group kill is the family's `ProcessReaper` (`src/vibey/infrastructure/process/reaper.py:45-100`),
not a new one (10.e). The machine lock's descriptor is passed to the child
(`pass_fds`), so the lock outlives a dead instance (T06).

## Required behaviour
1. **`MachineLoadReader.read(self) -> MachineLoad | None`** reads `os.getloadavg()` and
   `os.cpu_count()`. An `OSError` gives `None`.
2. **`ExecutionOutcome`**, a frozen, slotted dataclass:
   - `exit_code: int | None`
   - `timed_out: bool`
   - `unexecutable: bool`
   - `detail: str`
   - `duration_seconds: float`
   - `output_tail: str`
   - `load_before: MachineLoad | None`
   - `load_after: MachineLoad | None`
3. **`ChildEnvironment(base_env: EnvNamePatternsInterface)`.**
   `build(self, *, instance_environ: Mapping[str, str], request_env: Sequence[tuple[str, str]], run_id: UUID, coverage_file: Path) -> dict[str, str]`
   returns:
   - `base_env.select(instance_environ)`;
   - updated with `request_env`;
   - then every name starting with `GIT_` removed;
   - then `VIBEY_HARNESS_RUN=str(run_id)` and `COVERAGE_FILE=str(coverage_file)` set.
4. **`TestRunExecutor(*, reaper: ProcessReaperInterface, load: MachineLoadReader | None = None, tail_bytes: int = 65536)`.**
   - `async def run(self, *, argv: tuple[str, ...], cwd: Path, env: Mapping[str, str], bound_seconds: float, log_path: Path, pass_fds: tuple[int, ...] = ()) -> ExecutionOutcome`:
     1. Read `load_before` and start `time.monotonic()`.
     2. Open `log_path` for binary writing, creating it with mode `0o600`.
     3. Call `asyncio.create_subprocess_exec(*argv, cwd=str(cwd), env=dict(env), stdin=asyncio.subprocess.DEVNULL, stdout=<log fd>, stderr=asyncio.subprocess.STDOUT, start_new_session=True, pass_fds=pass_fds)`.
        An `OSError` (a missing binary, a missing `cwd`, a permission error) returns
        `unexecutable=True`, with `detail=f"cannot execute {argv[0]}: {exc}"` and
        `exit_code=None`.
     4. Wait with `asyncio.wait_for(process.wait(), bound_seconds)`. On timeout, call
        `await reaper.kill_and_reap(process)` and set `timed_out=True`, with
        `detail=f"exceeded the run bound of {bound_seconds:g}s"`.
     5. `exit_code = process.returncode`, which is negative for a signal.
     6. Close the log, read `load_after`, and set `output_tail = self.tail(log_path)`.
   - `tail(self, log_path: Path) -> str` returns the last `tail_bytes` bytes of the file,
     decoded as UTF-8 with `errors="replace"`, or `""` when the file is missing.
   - `async def stop(self) -> bool` kills the process group of the run in flight through
     the reaper. It returns `False` when nothing is running.
5. **Interfaces**: `TestRunExecutorInterface`, `ChildEnvironmentInterface` and
   `MachineLoadReaderInterface`.

## Where to change
- The new module and interface.
- Use `ProcessReaper` (`infrastructure/process/reaper.py`) and its interface
  (`infrastructure/process/interfaces/reaper_interface.py:13-26`).

## Acceptance criteria
- [ ] A fake command, `(sys.executable, "-c", ...)`, returns its exit code, and its output lands in the log.
- [ ] `output_tail` is capped at `tail_bytes`.
- [ ] A command that sleeps past the bound is killed with its whole group, and returns `timed_out`.
- [ ] A missing binary returns `unexecutable`.
- [ ] A descriptor in `pass_fds` is valid in the child.
- [ ] The child's environment is exactly the built one: no `GIT_*`, no name outside `base_env` or the request.
- [ ] pytest-cov honours `COVERAGE_FILE` under xdist with `parallel = true`. In a scratch project with `[tool.coverage.run] parallel = true`, run `(sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-n", "2", "--cov=pkg")` with the built environment. The combined data file exists at `COVERAGE_FILE`, and the scratch directory holds no `.coverage*` file.
- [ ] `uv run --no-sync python -c "import sys; print(sys.prefix)"`, run in `src/vibey_runners/qwen`, prints the repository's `.venv`. This test skips when `uv` or `<repo>/.venv` is absent.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_executor.py`:
  - `test_exit_code_and_log`
  - `test_signal_exit_is_negative`
  - `test_output_tail_is_capped`
  - `test_bound_kills_the_group` (a child that spawns a grandchild sleeper; both are gone afterwards)
  - `test_missing_binary_is_unexecutable`
  - `test_pass_fds_reach_the_child`
  - `test_stop_kills_the_run_in_flight`
  - `test_child_environment_is_exact`
  - `test_coverage_file_is_private_under_xdist`
  - `test_uv_run_no_sync_uses_the_workspace_venv` (skip-if)
  - `test_load_reader_handles_oserror`
  - `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/infrastructure/process
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Coverage gates (T12).
- Deciding whether to run (T13).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T12 — coverage-gates

**Lane card.**

- **Depends on:** T03, T05.
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/coverage.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/coverage_interface.py` (new)
  - `tests/infrastructure/test_harness/test_coverage.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(test-harness): coverage gates run inside the run, and the run's data is kept for reuse

## Why
ADR-0045 §8. The pre-push hook runs four `coverage report --fail-under=100` gates after
the suite (`.pre-commit-config.yaml:40-45`). CI runs the same four as separate steps that
read `.coverage` in the checkout (`.github/workflows/ci.yml:75-85`).

If the gates ran outside the harness, a cached answer would leave them reading whatever
`.coverage` the last execution in that directory wrote. So:
- the gates are part of the request, and run under the same lock against the run's
  **private** data file;
- the run's data file is kept with its record, and restored to `<cwd>/.coverage` both
  after execution and on reuse. A later `coverage report` then reads the data of the run
  that answered.

## Required behaviour
1. **`CoverageGates(*, coverage_command: tuple[str, ...], output_cap: int = 16384, timeout_seconds: float = 300.0)`.**
   `async def check(self, *, cwd: Path, data_file: Path, gates: Sequence[CoverageGateInterface], env: Mapping[str, str]) -> tuple[GateReport, ...]`:
   - When `data_file` does not exist, return one failing `GateReport` per gate, with
     `exit_code=-1` and `output=f"no coverage data at {data_file}"`. Spawn nothing.
   - Otherwise, for each gate in order, run
     `coverage_command + ("report", f"--data-file={data_file}", f"--include={gate.include}", f"--fail-under={gate.fail_under}")`
     with `cwd`, `env`, stdout and stderr combined, bounded by `timeout_seconds`. A
     timeout kills it with `exit_code=-1`. The report is
     `GateReport(include, fail_under, passed=(returncode == 0), exit_code=returncode, output=<last output_cap characters>)`.
2. **`CoverageDataKeeper`**:
   - `keep(self, *, data_file: Path, keep_dir: Path) -> Path | None` copies an existing
     `data_file` to `keep_dir / "coverage"` (mode `0o600`) and returns that path. A
     missing file returns `None`.
   - `restore(self, *, kept: Path | None, cwd: Path) -> bool` copies `kept` to
     `cwd / ".coverage"` atomically (a temporary file in `cwd`, then `os.replace`). It
     returns `False` when `kept` is `None` or missing.
3. **Interfaces**: `CoverageGatesInterface` and `CoverageDataKeeperInterface`.

## Where to change
- The new module and interface.

## Acceptance criteria
- [ ] With real data (made in the test with `(sys.executable, "-m", "coverage", "run", "--data-file=<tmp>", "-m", "<tmp module>")`), a gate of 100 on a module with an uncovered line fails with exit code 2, and a gate of 0 passes. This checks the upstream facts that `--data-file` is accepted and that exit 2 means below `--fail-under`.
- [ ] Missing data fails every gate without spawning anything.
- [ ] The keeper round-trips, and a restore of nothing returns `False`.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_coverage.py`:
  - `test_gate_passes_and_fails_on_real_data`
  - `test_missing_data_fails_every_gate_without_spawning`
  - `test_gate_output_is_capped`
  - `test_gate_timeout_fails`
  - `test_keeper_round_trip`
  - `test_restore_of_nothing_is_false`
  - `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- When gates run (T13).
- The hook's gate list (T18).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T13 — harness-instance

**Lane card.**

- **Depends on:** T02, T04, T06, T08, T10, T11, T12.
- **Wave:** 5.
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/instance.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/instance_interface.py` (new)
  - `tests/infrastructure/test_harness/test_instance.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - T06–T12 tests
  - all protected tests
- **Standing constraints:** see the header list. Every test uses a `tmp_path` store and lock.

## Title
feat(test-harness): the instance runs a request once, answers repeats, and parks what dies

## Why
This is the core of 8.e and ADR-0045 §2–§9. Both backends feed requests to one class, so
a run means the same thing whichever backend carried it. The class:
- answers a request it has already answered;
- refuses a request it cannot execute, as a dead letter;
- takes the machine lock, or answers `saturated`;
- under the lock, first marks every attempt still recorded `running` as `crashed`. The
  lock guarantees that its recorder is dead (T06);
- keys the run from the tree it will actually test;
- reuses, parks or executes, as T02 decides;
- runs the gates, keeps the coverage data, records the attempt, and dead-letters the
  three dead-letter outcomes with their evidence.

## Required behaviour
1. **`HarnessInstance`**, built with these keywords:
   - `settings: TestHarnessSettingsInterface`
   - `store: TestRunStoreInterface`
   - `lock: MachineLockInterface`
   - `digest: WorkingTreeDigestInterface`
   - `executor: TestRunExecutorInterface`
   - `child_env: ChildEnvironmentInterface`
   - `gates: CoverageGatesInterface`
   - `keeper: CoverageDataKeeperInterface`
   - `reuse: TestReusePolicyInterface`
   - `outcomes: TestOutcomePolicyInterface`
   - `clock: Clock` (`application/interfaces/system.py:11-12`)
   - `instance_environ: Mapping[str, str]`
   - `backend: str`
   - `pid: int`
2. **`async def handle(self, request: TestRunRequest, *, delivery_count: int = 0) -> TestRunResult`**
   works in this order. Every returned result is first written with `store.put_answer`.
   The only exception is a result whose outcome is `ABANDONED`, which is returned but not
   stored, so that a redelivery runs it again.
   1. **A request already answered.** If `store.answer(request.request_id)` returns an
      answer whose outcome is not `ABANDONED`, return it unchanged.
   2. **Validation**, without the lock. The request is unexecutable if any of these holds:
      - `cwd` does not exist, or `Path(cwd).resolve()` is not under `settings.root.resolve()`;
      - an `env` name does not match `settings.pass_env`;
      - `request.selection.command != settings.command`, with the detail
        "the request's command differs from this instance's configured command".

      Then write
      `DeadLetter.from_request(request, run_id=uuid4(), outcome=UNEXECUTABLE, reason=<why>, record=None, at=now)`
      and return `EXECUTED` with outcome `UNEXECUTABLE`, `exit_code=None` and the reason
      as `detail`.
   3. **The lock.** Call
      `hold = await lock.acquire(timeout_seconds=max(0.0, (request.start_by - now).total_seconds()), holder={"run_id": None, "request_id": str(request.request_id), "cwd": request.cwd, "backend": backend})`.
      If it returns `None`, return `SATURATED`, with the detail
      "the machine's test lock was not free before start_by".
   4. **Under the lock**, inside `try:` with `hold.release()` in the `finally:`:
      1. **The crash sweep.** For each `r` in `store.running()`:
         - `finished = r.finish(outcome=CRASHED, exit_code=None, timed_out=False, tree_after=None, finished_at=now, duration_seconds=None, load_after=None, output_tail=executor.tail(Path(r.log_path)), gate_reports=(), detail="the instance recording this run died before it finished", coverage_data=None)`;
         - `store.finish(finished)`;
         - `store.dead_letter(DeadLetter(run_id=r.run_id, request_id=r.request_id, cwd=r.cwd, selection=r.selection, env_names=tuple(n for n, _ in r.environment.env), requester=r.requester, outcome=CRASHED, reason=finished.detail, record=finished, dead_lettered_at=now))`;
         - if `r.request_id` has no answer yet, `put_answer` an `EXECUTED` / `CRASHED` result for it.
      2. **Retention.** `store.prune(older_than=now - settings.retention)`.
      3. **Again, a request already answered.** Repeat step 1. This is how a request
         redelivered after its instance crashed is answered from that crash's dead
         letter. **It is not run again.**
      4. **The key.** `tree = await digest.digest(Path(request.cwd))`, then
         `key = TestRunKey.derive(tree, request.selection, request.environment)`.
      5. **The decision.** `decision = reuse.decide(store.attempts_as_recorded(key), now=clock.now(), fresh=request.fresh, grant=request.grant)`.
      6. **`PARKED`** → return `PARKED`, with `run_id` and `outcome` from the parked
         attempt's record, `key`, and the decision's reason as `detail`.
      7. **`REUSE`** → take the record for `decision.attempt`. If
         `selection.collects_coverage`, call `keeper.restore(kept=<record.coverage_data as a Path, or None>, cwd=Path(request.cwd))`.
         Return `REUSED`, carrying the record's `run_id`, `key`, `outcome`, `exit_code`,
         `output_tail`, `gate_reports` and `log_path`, with `recorded_at=record.finished_at`,
         `tested_tree=record.tree_before` and the decision's reason as `detail`.
      8. **`EXECUTE`**:
         1. `run_id = uuid4()`.
         2. `record = store.begin(TestRunRecord(run_id=..., request_id=..., key=key, attempt=0, cwd=..., selection=..., environment=..., requester=..., instance=settings.instance, pid=pid, delivery_count=delivery_count, started_at=now, tree_before=tree, load_before=None, log_path=str(store.log_path(run_id))))`.
         3. `data_file = store.data_dir(run_id) / ".coverage"`.
         4. `env = child_env.build(instance_environ=..., request_env=request.env, run_id=run_id, coverage_file=data_file)`.
         5. `out = await executor.run(argv=selection.command + selection.argv, cwd=Path(cwd), env=env, bound_seconds=settings.run_bound_seconds, log_path=store.log_path(run_id), pass_fds=(hold.fd,))`.
         6. The gates run only when `out.exit_code == 0`, `not out.timed_out`,
            `not out.unexecutable` and `selection.gates` is non-empty:
            `reports = await gates.check(cwd=..., data_file=data_file, gates=selection.gates, env=env)`.
            Otherwise `reports = ()`.
         7. `tree_after = await digest.digest(Path(cwd))`.
         8. `kept = keeper.keep(data_file=data_file, keep_dir=store.data_dir(run_id)) if selection.collects_coverage else None`.
            If `kept` is set, call `keeper.restore(kept=kept, cwd=Path(cwd))`.
         9. The outcome is `ABANDONED` if `abandon_current()` was called during this run;
            `UNEXECUTABLE` if `out.unexecutable`; otherwise
            `outcomes.classify(out.exit_code, timed_out=out.timed_out, gate_failures=sum(not r.passed for r in reports))`.
         10. `finished = record.finish(...)`, carrying `out`'s fields, `reports`,
             `tree_after`, `coverage_data=str(kept) if kept else None`, and
             `load_after=out.load_after`. Also carry `load_before` from `out`: use
             `dataclasses.replace` before `finish`. Then `store.finish(finished)`.
         11. If `outcome.is_dead_letter()`, call
             `store.dead_letter(DeadLetter.from_request(request, run_id=run_id, outcome=outcome, reason=out.detail or outcome.value, record=finished, at=now))`.
         12. Return `EXECUTED`, with `flaky` and `flaky_runs` from `decision`,
             `recorded_at=finished.finished_at`, `tested_tree=tree` and
             `log_path=finished.log_path`.
3. **`async def abandon_current(self) -> None`** sets the abandon flag and calls
   `await executor.stop()`.
4. **The interface** is `HarnessInstanceInterface` (`handle`, `abandon_current`).

## Where to change
- The new module and interface. Nothing else.

## Acceptance criteria
Each is a test using the real `FileTestRunStore`, `MachineLock`, `CoverageDataKeeper`, `TestReusePolicy` and `TestOutcomePolicy` on `tmp_path`, with fakes for the digest, executor and gates, and a fixed clock:
- [ ] A passing run is executed, recorded and answered. The same request again returns the stored answer.
- [ ] A second, identical request is answered `REUSED`, and the executor is not called.
- [ ] An unexecutable request (outside the root, a foreign env name, a different command) is dead-lettered without taking the lock.
- [ ] A held lock gives `SATURATED` once `start_by` has passed.
- [ ] A `running` attempt left by a dead recorder is marked `CRASHED`, dead-lettered with its log tail, and its request is answered. A redelivery of that request is answered from it and not run again.
- [ ] A parked key is answered `PARKED`, and a grant runs it.
- [ ] A timeout is dead-lettered with its evidence.
- [ ] Gates run only after a clean exit, and a failing gate makes the outcome `FAILED`.
- [ ] A tree that changed during the run makes the attempt unreusable.
- [ ] Coverage data is kept, and restored to `<cwd>/.coverage` on execution and on reuse.
- [ ] The lock's fd is passed to the executor.
- [ ] `abandon_current()` gives `ABANDONED`, which is not stored as an answer.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_instance.py`:
  - `test_executes_records_and_answers_a_passing_run`
  - `test_answered_request_is_returned_as_is`
  - `test_identical_request_is_reused_without_executing`
  - `test_unexecutable_requests_are_dead_lettered_without_the_lock` (parametrized)
  - `test_saturated_after_start_by`
  - `test_crash_sweep_dead_letters_and_answers_a_dead_recorders_attempt`
  - `test_redelivery_after_a_crash_is_answered_not_rerun`
  - `test_parked_key_is_answered_and_a_grant_runs_it`
  - `test_timeout_is_a_dead_letter_with_evidence`
  - `test_gates_run_only_after_a_clean_exit`
  - `test_tree_changed_during_the_run_is_not_reusable`
  - `test_coverage_data_is_kept_and_restored_on_reuse`
  - `test_lock_fd_is_passed_to_the_child`
  - `test_abandoned_is_returned_but_not_stored`
  - `test_instance_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- How requests arrive (T14, T23).
- The CLI (T15).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T14 — local-client

**Lane card.**

- **Depends on:** T02, T06, T08, T09, T10.
- **Wave:** 5.
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/local_client.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/local_client_interface.py` (new)
  - `tests/infrastructure/test_harness/test_local_client.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - T06–T10 tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(test-harness): the local backend's requester, with a detached instance per request

## Why
ADR-0045 §3 and §11. A machine without RabbitMQ must still commit and push (the operator's
requirement). With the `local` backend, the requester writes its request and spawns a
**detached** supervisor (`vibey test-harness execute`, T15) that is the instance for that
request. It then waits for the answer.

The supervisor is detached for a concrete reason. qwenloop's shell kills a command after
120 s (`src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py:55-59`), and a full
suite does not fit in that. A requester's death must never cancel or orphan an
unrecorded run: the run finishes, and the next identical request is answered from its
record.

Two pieces are shared with the `rabbitmq` requester (T24), so they are classes of their
own:
- **the request builder**;
- **the fast path.** It answers a repeat from the store without spawning anything, and
  skips any selection that collects coverage, so that `.coverage` is only restored under
  the lock (ADR-0045 §8).

## Required behaviour
1. **`TestRunRequestBuilder(*, settings, probe: EnvironmentProbeInterface, clock: Clock, requester: str)`.**
   `async def build(self, *, cwd: Path, argv: Sequence[str], gates: Sequence[CoverageGate], fresh: bool, grant: bool, environ: Mapping[str, str]) -> TestRunRequest`:
   - `request_id=uuid4()`;
   - `cwd=str(cwd.resolve())`;
   - `selection=TestSelection(settings.command, tuple(argv), tuple(gates))`;
   - `environment, env = await probe.probe(environ)`;
   - `requested_at=clock.now()` and `start_by = requested_at + timedelta(seconds=settings.queue_wait_seconds)`;
   - `requester` as given.
2. **`ReuseFastPath(*, store, digest, reuse, clock, backend: str)`.**
   `async def answer(self, request) -> TestRunResult | None` returns `None` when
   `request.fresh`, `request.grant` or `request.selection.collects_coverage`. Otherwise:
   1. `tree = await digest.digest(Path(request.cwd))`;
   2. `key = TestRunKey.derive(tree, selection, environment)`;
   3. `decision = reuse.decide(store.attempts_as_recorded(key), now=clock.now(), fresh=False, grant=False)`.

   `REUSE` returns a `REUSED` result built from the record, as T13 behaviour 2.4.7 does.
   `PARKED` returns a `PARKED` result. `EXECUTE` returns `None`. The fast path **writes
   nothing** to the store.
3. **`SupervisorSpawner(*, argv_prefix: tuple[str, ...])`.**
   `async def spawn(self, *, request_file: Path, config_path: Path | None, log_path: Path, env: Mapping[str, str], cwd: Path) -> int`:
   - the argv is `argv_prefix + (str(request_file),)`, plus `("--config", str(config_path))`
     when `config_path` is set;
   - it spawns with `start_new_session=True`, stdin `DEVNULL`, stdout and stderr appended
     to `log_path` (mode `0o600`), `env=dict(env)` and `cwd=str(cwd)`;
   - it returns the pid, and **never waits** on the process.
4. **`LocalHarnessClient(*, settings, store, builder, fast_path, spawner, lock: MachineLockInterface, clock, environ: Mapping[str, str], config_path: Path | None = None, poll_seconds: float = 0.5)`**:
   - `async def request(self, *, cwd, argv, gates, fresh, grant=False, environ) -> TestRunResult`
     builds the request, returns the fast-path answer if there is one, and otherwise
     returns `await self.submit(request)`.
   - `async def submit(self, request) -> TestRunResult`:
     1. `store.ensure()`;
     2. `path = store.put_request(request)`;
     3. spawn the supervisor with `request_file=path`, `log_path=store.supervisor_log_path(request.request_id)`,
        `env=self._environ` and `cwd=settings.state_dir`;
     4. poll `store.answer(request.request_id)` every `poll_seconds`, and return it when it
        appears;
     5. after `settings.wait_seconds`, return `STILL_RUNNING` (backend `"local"`) with the
        detail
        `"the run is still going; run the same command again to receive its result"`,
        plus `f" (the machine's test lock is held by pid {pid} since {since})"` when
        `lock.holder()` names one.
5. **Interfaces**: `TestRunRequestBuilderInterface`, `ReuseFastPathInterface`,
   `SupervisorSpawnerInterface` and `HarnessClientInterface` (with `request` and
   `submit`). T24 implements the last one too.

## Where to change
- The new module and interface. Nothing else.

## Acceptance criteria
- [ ] The builder fills every field, and `start_by` follows `queue_wait_seconds`.
- [ ] The fast path answers `REUSED` and `PARKED` without writing anything, and skips fresh, granted and coverage-collecting requests.
- [ ] `request` writes the request file, spawns once with the expected argv (including `--config` when set), and returns the answer the fake supervisor writes.
- [ ] With no answer, `STILL_RUNNING` comes back after `wait_seconds`, naming the holder.
- [ ] The real `SupervisorSpawner` starts a detached process that outlives the calling coroutine. It writes a marker, and the test waits for it.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_local_client.py`:
  - `test_builder_fills_every_field`
  - `test_fast_path_reuses_without_writing`
  - `test_fast_path_answers_parked`
  - `test_fast_path_skips_fresh_granted_and_coverage` (parametrized)
  - `test_request_spawns_and_returns_the_written_answer`
  - `test_still_running_after_the_wait_names_the_holder` (settings with `wait_seconds=1`, `poll_seconds=0.05`)
  - `test_spawner_detaches` (argv prefix `(sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[1] + '.seen').write_text('x')")`)
  - `test_spawner_adds_config`
  - `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The supervisor command itself (T15).
- The rabbitmq requester (T24).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T15 — test-run-cli

**Lane card.**

- **Depends on:** T13, T14.
- **Wave:** 6.
- **Files touched:**
  - `src/vibey/cli/test_harness.py` (new)
  - `src/vibey/cli/interfaces/test_harness_interface.py` (new)
  - `src/vibey/cli/main.py` (two registration lines and one import)
  - `src/vibey/bootstrap.py` (new classes and a new function only)
  - `src/vibey/bootstrap_interface.py` (one new Protocol)
  - `src/vibey/domain/errors.py` (one new exception, appended)
  - `src/vibey/__main__.py` (new)
  - `tests/cli/test_test_harness_cli.py` (new)
  - `tests/test_bootstrap.py` (new tests, appended)
- **Shares a file with:**
  - `bootstrap.py`, `bootstrap_interface.py` and `cli/main.py`, the ADR-0044 chain (R02, R17, R27, R28, R33). This lane adds only; if any of those has landed, rebase and keep their code;
  - `domain/errors.py`.
- **Must keep passing unchanged:**
  - `tests/cli/*`
  - `tests/test_bootstrap.py`
  - the image contract "every console script is on PATH" (`.github/workflows/ci.yml:822`); **no console script is added**, because `python -m vibey` is not a script
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(cli): vibey test run puts a run on the harness and waits for its answer

## Why
8.e: "a commit hook, a storm lane, a reviewer and the command line all put their run on
the queue and wait for its result". ADR-0045 §10 and §11 give that a command. It prints
the answer with a first line that says what happened (executed, reused, flaky, parked,
saturated, still running), then exits with a code a hook or a model can act on.

The `local` backend's detached instance also needs an entry point:
`vibey test-harness execute`, spawned as `python -m vibey` so that no console script is
added. The composition lives in `bootstrap.py`, the sole composition root (CLAUDE.md).

## Required behaviour
1. **`TestHarnessNotConfigured(VibeyError)`**, appended to `src/vibey/domain/errors.py`.
2. **`bootstrap.py`: `class TestHarnessComposition`**, built with
   `(*, settings: TestHarnessSettings, environ: Mapping[str, str], clock: Clock, config_path: Path | None = None)`.
   It builds lazily and caches each piece:
   - `store()` is `FileTestRunStore(settings.state_dir, messages=TestHarnessCodec(), records=TestRunRecordCodec(TestHarnessCodec()))`,
     after `ensure()`;
   - `lock()` is `MachineLock(settings.lock_path)`;
   - `digest()` is `WorkingTreeDigest(exclude=settings.tree_exclude)`;
   - `probe()` is `EnvironmentProbe(pass_env=settings.pass_env, database_env=settings.database_env)`;
   - `reuse()` is `TestReusePolicy(settings.pass_ttl, settings.fail_ttl)`;
   - `instance(backend: str = "local") -> HarnessInstance` wires T11's `TestRunExecutor`
     (`ProcessReaper()`, `tail_bytes=settings.output_tail_bytes`), `ChildEnvironment`,
     `CoverageGates(coverage_command=settings.coverage_command)`, `CoverageDataKeeper`,
     `TestOutcomePolicy()`, `instance_environ=environ` and `pid=os.getpid()`;
   - `async def client(self) -> HarnessClientInterface`:
     - backend `local` or `auto` → `LocalHarnessClient`, whose `SupervisorSpawner` has
       `argv_prefix=(sys.executable, "-m", "vibey", "test-harness", "execute", "--request-file")`
       and whose `requester=f"{getpass.getuser()}@{settings.instance}:{os.getpid()}"`;
     - backend `rabbitmq` → raise `TestHarnessNotConfigured`. Its message names the
       remedy: `export VIBEY_HARNESS_BACKEND=local`. T25 replaces this branch;
   - the property `announcement -> str | None`, which is `None` in this lane.

   Add `def build_test_harness(config: VibeyConfig | None, environ: Mapping[str, str], *, config_path: Path | None = None) -> TestHarnessComposition`,
   using `TestHarnessSettings.from_sources` and `SystemClock()` (`bootstrap.py:174-176`).
   `bootstrap_interface.py` gains `TestHarnessCompositionInterface`.
3. **`src/vibey/cli/test_harness.py`**. Follow `cli/ledger_search.py`: a command class
   holds the logic, and thin module-level typer functions carry the reason comment used
   at `cli/ledger_search.py:275-276`.
   - **`TestRunReport`**:
     - `render(self, result: TestRunResult, *, announcement: str | None, full_log: str | None = None) -> str`
       builds these lines, in order:
       1. `vibey test-harness: backend=<result.backend> run=<run_id or -> key=<first 12 of key or -> <word>`,
          where `<word>` is `executed`, `reused`, `flaky`, `parked`, `saturated` or
          `still running`. It is `flaky` when `result.flaky`;
       2. the announcement, if any;
       3. `full_log` if given, else `result.output_tail`;
       4. one line per gate, `gate <include> >= <n>%: passed` or `gate <include> >= <n>%: FAILED (exit <c>)`,
          with the gate's output after a failed one;
       5. `result.detail`, if any;
       6. for a dead-letter outcome, or `PARKED`:
          `dead-lettered: <outcome> — see "vibey test dead-letters"; requeue with "vibey test requeue <run_id>"`;
       7. for `REUSED`:
          `(recorded <recorded_at>; add --fresh to run it again)`.
     - `exit_code(self, result) -> int`:
       - `SATURATED` and `STILL_RUNNING` → 75;
       - `PARKED`, or any dead-letter outcome → 3 (`EXIT_BLOCKED`, `cli/errors.py:35`);
       - `PASSED` → 0;
       - `FAILED` → `result.exit_code` when that is set and non-zero, else 1;
       - `ABANDONED` → 1.
   - **`TestRunCommand`** runs `vibey test run`.
   - **`test_app = typer.Typer(name="test", no_args_is_help=True)`**, with the command
     `run`, declared with
     `context_settings={"allow_extra_args": True, "ignore_unknown_options": True}`:
     ```
     vibey test run [--gate INCLUDE=MIN]... [--fresh] [--backend auto|local|rabbitmq]
                    [--wait-seconds N] [--cwd DIR] [--config FILE] [--full-output] -- PYTEST_ARGS...
     ```
     1. `environ = dict(os.environ)`. `--backend` sets `VIBEY_HARNESS_BACKEND`, and
        `--wait-seconds` sets `VIBEY_HARNESS_WAIT_SECONDS`. `--fresh` is also on when
        `VIBEY_HARNESS_FRESH == "1"`.
     2. The config is `load_config_from_path(--config)` when given, else `./vibey.toml`
        when that exists, else `None`. The config path used is passed to the composition,
        so the supervisor reads the same file.
     3. `gates = [CoverageGate.parse(g) for g in --gate]`. A `ValueError` exits 2
        (`EXIT_USAGE`) with the message.
     4. `result = asyncio.run(<await composition.client(); await client.request(cwd=(--cwd or Path.cwd()).resolve(), argv=tuple(ctx.args), gates=gates, fresh=fresh, grant=False, environ=environ)>)`.
     5. Print `render(result, announcement=composition.announcement, full_log=<the full log text when --full-output and result.log_path exists>)`,
        then exit with `exit_code(result)`.
     6. `TestHarnessNotConfigured` exits 2 with its message.
   - **`harness_app = typer.Typer(name="test-harness", no_args_is_help=True)`**, with a
     hidden command `execute --request-file PATH [--config FILE]`:
     1. It builds the composition from `os.environ` and the given config.
     2. It installs `loop.add_signal_handler` for `SIGTERM` and `SIGINT`, each calling
        `instance.abandon_current()`.
     3. It runs `await instance.handle(store.take_request(path))`.
     4. It exits 0. The answer is in the store.
     5. Any exception is printed to stderr, and it exits 1.
4. **`cli/main.py`**: import `test_app` and `harness_app`, then add
   `app.add_typer(test_app, name="test")` and `app.add_typer(harness_app, name="test-harness")`
   next to the existing `add_typer` lines (`:52-59`).
5. **`src/vibey/__main__.py`**: the provenance line, then a docstring giving the reason
   ("the entry `python -m vibey` needs a module-level call; the supervisor is spawned
   this way so that no console script is added (ADR-0037)"), then:
   ```python
   from vibey.cli.main import app

   if __name__ == "__main__":
       app(prog_name="vibey")
   ```
6. **Interfaces**: `TestRunReportInterface`, `TestRunCommandInterface` and
   `TestHarnessExecuteCommandInterface`.

## Where to change
- The files on the card.
- The CLI tests use `typer.testing.CliRunner`, as `tests/cli/test_ledger_search_cli.py` does.

## Acceptance criteria
- [ ] `vibey test run` renders and exits correctly for every status and outcome, against a fake composition whose client returns scripted results.
- [ ] A bad `--gate` exits 2. `--backend rabbitmq` exits 2 and names `VIBEY_HARNESS_BACKEND=local`.
- [ ] **End to end** (a subprocess, marked `slow`): in a scratch git repository under `tmp_path`, with one passing test and a `vibey.toml` holding
  ```toml
  [project]
  name = "scratch"
  [test_harness]
  state_dir = "<tmp>/state"
  root = "<tmp>"
  command = ["<sys.executable>", "-m", "pytest", "-p", "no:cacheprovider"]
  ```
  run `[sys.executable, "-m", "vibey", "test", "run", "--config", <file>, "--", "-q"]`, with `VIBEY_HARNESS_RUN` and `VIBEY_HARNESS_ROUTE` stripped. It exits 0, and line 1 matches `^vibey test-harness: backend=local run=\S+ key=[0-9a-f]{12} executed$`. A second run prints `reused`. `--fresh` prints `executed` again.
- [ ] 100% coverage on `cli/`.

## Tests to write first (TDD)
- `tests/cli/test_test_harness_cli.py`:
  - `test_report_first_line_for_each_status` (parametrized)
  - `test_exit_code_table` (parametrized)
  - `test_run_passes_args_after_the_double_dash`
  - `test_bad_gate_exits_2`
  - `test_rabbitmq_backend_is_not_configured_in_this_build`
  - `test_fresh_from_the_environment`
  - `test_full_output_prints_the_log`
  - `test_execute_handles_the_request_file` (a real composition on `tmp_path`; the command is `(sys.executable, "-c", "print('ok')")` through a `--config` file)
  - `test_end_to_end_executes_then_reuses` (`slow`)
- `tests/test_bootstrap.py` (appended):
  - `test_build_test_harness_composes_a_local_client`
  - `test_test_harness_composition_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli tests/test_bootstrap.py tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- `status`, `dead-letters` and `requeue` (T16).
- The plugin's `queue` mode (T17).
- The rabbitmq backend and `serve` (T25).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T16 — test-inspect-cli

**Lane card.**

- **Depends on:** T15.
- **Wave:** 7.
- **Files touched:**
  - `src/vibey/cli/test_harness.py` (three commands and their classes)
  - `src/vibey/cli/interfaces/test_harness_interface.py`
  - `tests/cli/test_test_harness_cli.py` (new tests, appended)
- **Shares a file with:** `cli/test_harness.py` (T15 before, T25 after).
- **Must keep passing unchanged:**
  - T15's tests
  - `tests/cli/*`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(cli): vibey test status, dead-letters and requeue — see the harness and grant a parked run

## Why
8.e: a dead letter is kept "with its evidence, where a human or a repair lane can see
it". ADR-0045 §9 makes `vibey test requeue` the grant that answers a park, the ADR-0024
pattern: "every bounded ladder parks with a grant".

`vibey test status` says who holds the machine's lock, and how to stop an unwanted run
(ADR-0045 §11: send the holder `SIGTERM`, and the instance records the run `abandoned`).

## Required behaviour
1. **`vibey test status [--json]`**:
   - `holder: pid <pid> (alive|dead) request <id> since <since> — stop it with: kill <pid>`,
     or `holder: none` (from `composition.lock().holder()`);
   - one line per `store.running()` attempt:
     `running: run <run_id> key <12> cwd <cwd> argv <argv joined>`;
   - up to 10 `store.recent_answers(10)`:
     `recent: <status> <outcome or -> run <run_id or -> key <12 or -> <requester>`.

   `--json` prints one JSON object, `{"holder": ..., "running": [...records...], "recent": [...answers...]}`,
   using the codecs.
2. **`vibey test dead-letters [--json] [--all]`** prints one line per letter:
   `<run_id> <outcome> <dead_lettered_at> <cwd> <argv joined> — <reason>`.
   - `--all` includes answered letters, marked `(answered)`.
   - When `store.malformed()` is non-empty, it adds a final line:
     `malformed messages: <n> in <state_dir>/malformed`.
   - `--json` prints a JSON list of encoded dead letters.
   - It exits 0, whatever it finds.
3. **`vibey test requeue RUN_ID [--wait-seconds N] [--full-output]`**:
   - An unknown `RUN_ID` exits 2 with "no dead letter <run_id>". An answered one exits 2
     with "dead letter <run_id> is already answered".
   - It builds `environ` from `os.environ`. For each name in `letter.env_names` that is
     unset, it warns `<name> is not set in this environment`.
   - `request = await builder.build(cwd=Path(letter.cwd), argv=letter.selection.argv, gates=letter.selection.gates, fresh=False, grant=True, environ=environ)`.
   - When `letter.record` is set and `request.environment != letter.record.environment`,
     it warns: `the environment differs from the dead-lettered run's; this is a new key`.
   - It calls `store.answer_dead_letter(DeadLetterAnswer(run_id, answered_by=<requester>, answered_at=now, requeued_request_id=request.request_id))`,
     then `result = await client.submit(request)`, prints it through `TestRunReport`, and
     exits with its code.
4. The command classes `TestStatusCommand`, `TestDeadLettersCommand` and
   `TestRequeueCommand` get interfaces.

## Where to change
- `src/vibey/cli/test_harness.py` and its interface. The composition (T15) already exposes every piece used here.

## Acceptance criteria
- [ ] `status` shows a holder, running attempts and recent answers from a seeded `tmp_path` store, and `--json` parses.
- [ ] `dead-letters` lists only unanswered letters by default, and all with `--all`. It counts malformed messages.
- [ ] `requeue` answers the letter once, submits a granted request, and exits with the answer's code. A second requeue exits 2.
- [ ] 100% coverage on `cli/`.

## Tests to write first (TDD)
- `tests/cli/test_test_harness_cli.py` (appended):
  - `test_status_text_and_json`
  - `test_status_without_a_holder`
  - `test_dead_letters_default_and_all`
  - `test_dead_letters_counts_malformed`
  - `test_requeue_grants_once` (a fake client; assert `grant=True` and the answer file)
  - `test_requeue_unknown_and_answered_exit_2`
  - `test_requeue_warns_on_missing_env_and_a_new_key`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- A cancel command. ADR-0045 §11 stops a run with `kill <pid>`, which `status` prints.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T17 — pytest-queue-route

**Lane card.**

- **Depends on:** T07, T15.
- **Wave:** 7.
- **Files touched:**
  - `src/vibey/cli/pytest_route.py`
  - `src/vibey/cli/interfaces/pytest_route_interface.py`
  - `tests/cli/test_pytest_route.py` (new tests, appended; T07's `test_queue_is_refused_in_this_build` is replaced, the only edit to an existing test)
- **Shares a file with:** `cli/pytest_route.py` (T07 before).
- **Must keep passing unchanged:**
  - every other T07 test
  - the whole suite (the root ini is still `locked`)
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(test-harness): pytest's queue mode puts the run on the harness and prints its answer

## Why
ADR-0045 §10. With `vibey_harness_route = queue`, a plain `uv run pytest …` builds a
request from its own argv and working directory, puts it on the harness, prints the
answer and exits with its code. pytest itself runs nothing.

That is how a storm lane's model, a reviewer, or `build.verify` in a vibey worktree
reaches the queue **without knowing** (8.e: "a storm lane … put[s] [its] run on the
queue").

The plugin short-circuits in `pytest_cmdline_main` with `tryfirst=True`. No conftest's
`pytest_configure` runs in the requester, so no database is cloned for a run that is
answered from its record.

## Required behaviour
1. **The `QUEUE` branch** of `pytest_cmdline_main` calls `self._queued(config)` and
   returns its value. It replaces T07's `UsageError`.
2. **`_queued(config) -> int`**:
   1. `composition = self._composition_factory(environ, config)`. The default builds
      `build_test_harness(<load_config_from_path(config.rootpath / "vibey.toml") if that file exists, else None>, environ, config_path=<that path or None>)`.
   2. Run
      `result = asyncio.run(<await composition.client(); await client.request(cwd=Path(config.invocation_params.dir), argv=tuple(config.invocation_params.args), gates=(), fresh=environ.get("VIBEY_HARNESS_FRESH") == "1", grant=False, environ=dict(environ))>)`.
   3. Write `TestRunReport().render(result, announcement=composition.announcement)` to
      `sys.stdout`, flushed.
   4. Return `TestRunReport().exit_code(result)`.
   5. Any exception prints
      `vibey test-harness: <exc>; bypass with VIBEY_HARNESS_ROUTE=off` to stderr, and
      returns 3. A broken harness must neither pass silently nor run unrouted.
3. **`__init__`** gains `composition_factory: Callable[[Mapping[str, str], pytest.Config], TestHarnessCompositionInterface] | None = None`.

## Where to change
- `src/vibey/cli/pytest_route.py` and its interface.

## Acceptance criteria
- [ ] In unit tests with a fake composition, queue mode renders the answer, returns its code, and never calls anything that would run pytest.
- [ ] **End to end** (a subprocess, marked `slow`): a scratch git project with `pytest.ini` (`vibey_harness_route = queue`), a `vibey.toml` as in T15's end-to-end test, one passing test, and a `conftest.py` whose `pytest_configure` appends a line to `<tmp>/configured.txt`.
  1. Run `[sys.executable, "-m", "pytest", "-q"]` in the project. Stdout starts `vibey test-harness: backend=local`, contains the child's `1 passed`, and the exit code is 0.
  2. `configured.txt` has **one** line, written by the child. The requester did not run `pytest_configure`, which checks the tryfirst short-circuit.
  3. Run it again. The output says `reused`, and `configured.txt` still has one line.
- [ ] The output printed from `pytest_cmdline_main` reaches the subprocess's stdout, which checks that global capture is suspended by then.
- [ ] A composition that raises gives exit 3 and names the bypass.
- [ ] 100% `cli/` coverage.

## Tests to write first (TDD)
- `tests/cli/test_pytest_route.py` (appended):
  - `test_queue_renders_the_answer_and_returns_its_code`
  - `test_queue_honours_fresh_from_the_environment`
  - `test_queue_failure_is_exit_3_and_names_the_bypass`
  - `test_end_to_end_queue_runs_once_then_reuses` (`slow`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_pytest_route.py tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Switching the root ini to `queue` (T28).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T18 — hooks-route

**Lane card.**

- **Depends on:** T15.
- **Wave:** 7.
- **Files touched:**
  - `.pre-commit-config.yaml`
  - `tests/meta/test_hooks_route_tests_through_the_harness.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - `tests/meta/test_githooks_reach_the_framework.py`
  - `tests/infrastructure/test_worktree_hooks.py`
  - the vibey-gh suite, `(cd src/vibey_tools/gh && python -m pytest -q)`: `installed()` compares only `.githooks/commit-msg` and `.githooks/pre-push` (`src/vibey_tools/gh/vibey_gh/install.py:34`, `:639`), and neither changes
  - all protected tests
- **Standing constraints:** see the header list. Do not edit anything under `.githooks/`, nor vibey-gh's templates.

## Title
build(hooks): a push runs the suite once, as one harness request with its four coverage gates

## Why
- **Today.** The pre-push stage runs the whole suite twice, `test-suite` (`.pre-commit-config.yaml:11-24`)
  and `coverage-gates` (`:40-45`). The file's own comment says one push once ran it
  three times (`:20-23`), and that `test-suite` survives only so that a plain test
  failure is reported as itself.
- **Under 8.e** those are two selections, and so two runs, one after the other.
- **Under ADR-0045 §8 and §10,** one request carries the four gates, and its answer
  reports test failures and gate failures separately. So `test-suite`'s one reason is
  met, and it goes.
- **Where the change lives.** The hooks chain (ADR-0028):
  `.githooks/pre-push` → `pre-push.local` → `framework-hook.sh` → the framework
  (`.githooks/pre-push:116-118`, `.githooks/pre-push.local:5`, `.githooks/framework-hook.sh:56-58`).
  So the routing belongs in the framework config the chain reaches, and **no vibey-gh
  template changes**.

## Required behaviour
1. **Remove** the `test-suite` hook (`:11-24`), with its comment.
2. **Replace** the `coverage-gates` hook (`:40-45`) with the block below. Keep a comment
   above it saying:
   - why one request (8.e and ADR-0045 §8);
   - that the answer separates test failures from gate failures;
   - that `SKIP=coverage-gates git push` is the framework's bypass.
   ```yaml
         - id: coverage-gates
           name: test suite and per-layer 100% coverage gates (one test-harness run)
           entry: >-
             uv run vibey test run
             --gate src/vibey/domain/*=100
             --gate src/vibey/application/*=100
             --gate src/vibey/infrastructure/*=100
             --gate src/vibey/cli/*=100
             -- -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
           language: system
           pass_filenames: false
           stages: [pre-push]
   ```
   pre-commit splits `entry` with shlex, and runs no shell, so the `*` is never globbed.
3. **The other hooks** (`mypy`, `lint-imports`, `bandit`, `pip-audit`, ruff and
   `conventional-pre-commit`) are unchanged.
4. **`tests/meta/test_hooks_route_tests_through_the_harness.py`** uses module-level test
   functions, for the reason `tests/meta/test_adr_counts.py` gives. It loads the file
   with `yaml.safe_load`:
   - `test_every_test_run_goes_through_the_harness`: for every hook in a `local` repo
     whose `entry` contains `pytest`, the entry starts with `uv run vibey test run`;
   - `test_the_plain_test_suite_hook_is_gone`: no hook id is `test-suite`;
   - `test_the_gates_match_ci`: the four `--gate` includes equal the four
     `--include='…'` globs in `.github/workflows/ci.yml`'s Gate 4a–4d steps, read from
     the file, each at `=100`.

## Where to change
- `.pre-commit-config.yaml` and the new meta test.

## Acceptance criteria
- [ ] `uv run pre-commit validate-config` passes.
- [ ] The meta tests pass.
- [ ] `uv run pre-commit run coverage-gates --hook-stage pre-push` exits 0 on a clean tree, and its first line reads `vibey test-harness: backend=local … executed` (or `reused`).

## Tests to write first (TDD)
- `tests/meta/test_hooks_route_tests_through_the_harness.py` (above).

## Checks the lane must run (all must pass)
    uv run pre-commit validate-config
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta tests/infrastructure/test_worktree_hooks.py
    (cd src/vibey_tools/gh && uv run python -m pytest -q -p no:cacheprovider)
    uv run pre-commit run coverage-gates --hook-stage pre-push

## Out of scope
- `.githooks/*` and vibey-gh's templates. ADR-0028's chain already reaches this file.
- CI (T19).
- Docs and CHANGELOG. CONTRIBUTING.md's hook section is the docs wave's.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T19 — ci-route

**Lane card.**

- **Depends on:** T15.
- **Wave:** 7.
- **Files touched:** `.github/workflows/ci.yml`.
- **Shares a file with:** `ci.yml` (R32 and R34). If they have landed, rebase.
- **Must keep passing unchanged:**
  - `tests/meta/test_postgres_support_matrix.py` (it pins the matrix and the image, not the command)
  - `tests/meta/test_tools_matrix_covers_every_package.py`
  - every job name. `noloss` is a required check (`ci.yml:98-103`), so no job is renamed
  - all protected tests
- **Standing constraints:** see the header list.

## Title
ci: the root suites run through the test harness, always fresh

## Why
There are two reasons, both in ADR-0045 §10 and under *Where the drafted rule conflicts*,
item 3:
- **10.e says the family is dogfooded "in CI".** A project that ships a test harness it
  does not run in CI has not tested it.
- **8.b's sovereign forge default is self-hosted Forgejo,** whose runners *do* share a
  machine between jobs. There, the harness's machine lock is what keeps 8.e.

A verifier must produce its own evidence and never take a cached answer, so every CI
request is `--fresh`.

The four per-layer coverage steps (`:75-85`) stay as they are. The harness restores
`.coverage` in the checkout from the run's private data (ADR-0045 §8).

The tenant rows (`:195-548`) are unchanged. Their venvs are built with plain pip and
hold no vibey, and each row is a machine of its own.

## Required behaviour
1. **The jobs `gates`, `noloss` and `postgres-compatibility`** each gain the job-level env
   `VIBEY_HARNESS_STATE_DIR: ${{ runner.temp }}/vibey-test-harness`.
2. **`gates`**. The step "Run test suite with coverage" (`:72-73`) becomes:
   ```yaml
         - name: Run test suite with coverage
           run: uv run vibey test run --backend local --fresh --full-output -- -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
   ```
   Put a comment above it naming 10.e, the self-hosted-runner reason, and why `--fresh`.
3. **`noloss`** (`:138-139`):
   ```yaml
           run: uv run vibey test run --backend local --fresh --full-output -- -m noloss --hypothesis-profile=noloss --hypothesis-show-statistics -p no:cacheprovider
   ```
   `--full-output` keeps the statistics this job exists to print (`:98-103`) in full,
   beyond the output tail.
4. **`postgres-compatibility`** (`:188-193`):
   ```yaml
           run: >-
             uv run vibey test run --backend local --fresh --full-output --
             -q -p no:cacheprovider
             tests/infrastructure/db
             tests/infrastructure/test_cluster_preflight.py
             tests/cli/test_main_integration.py
   ```
5. **Each of the three jobs** gains a last step:
   ```yaml
         - name: Test-harness dead letters (evidence)
           if: failure()
           run: uv run vibey test dead-letters
   ```
   Only once T16 has landed. This lane depends on T15; if T16 is not yet merged, omit
   this step and say so in the commit body.

## Where to change
- `.github/workflows/ci.yml` only.

## Acceptance criteria
- [ ] `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` passes.
- [ ] The meta tests pass.
- [ ] Locally, with `VIBEY_HARNESS_STATE_DIR` pointing at a temporary directory, `uv run vibey test run --backend local --fresh -- -q -p no:cacheprovider tests/domain` exits 0.
- [ ] Afterwards `.coverage` is present when `--cov` was given. Check with `uv run vibey test run --backend local --fresh -- -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/domain && uv run coverage report --include='src/vibey/domain/*'`.

## Tests to write first (TDD)
- No new test file. The meta tests and the manual checks above are the tests.

## Checks the lane must run (all must pass)
    uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
    uv run pytest -q -p no:cacheprovider tests/meta
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The tenant rows.
- A RabbitMQ service in CI (R32).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T20 — qwenloop-shell-timeout

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey_runners/qwen/src/qwenloop/domain/config.py`
  - `src/vibey_runners/qwen/src/qwenloop/infrastructure/settings.py`
  - `src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py`
  - `src/vibey_runners/qwen/src/qwenloop/cli/app.py`
  - `src/vibey_runners/qwen/tests/test_domain.py`, `test_settings.py` and `test_runner.py` (new tests, appended)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - the whole qwenloop suite, `(cd src/vibey_runners/qwen && uv run python -m pytest -q)`. Its addopts carry `--cov-fail-under=100` (`src/vibey_runners/qwen/pyproject.toml:68`)
  - the storm driver's call, `_run_plan(server, profile, lane, run_id, text, max_turns, startup_timeout_seconds=..., desktop_notifications=True)` (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/qwenlane.py:90-100`). The new parameter must be keyword-only with a default
  - all protected tests
- **Standing constraints:** see the header list. This lane changes a runner tenant, and runs that tenant's own gates (ADR-0022).

## Title
feat(qwenloop): the shell tool's timeout is a key, not 120 seconds

## Why
`SandboxTools.execute` kills every shell command after a hard-coded 120 s
(`src/qwenloop/infrastructure/tools.py:55-59`). A constant that could have been a key
breaks sub-doctrine 12.c ("a hard-coded value that could have been a key is a decision
taken away from the next adopter").

It also collides with 8.e. A storm lane's full-suite run measured 259 s
(`.pre-commit-config.yaml:18`), so it can never finish inside the tool. Waiting in the
test harness's queue makes that worse. ADR-0045 §11 needs the limit configurable, so
that an operator can let a lane wait for its run.

## Required behaviour
1. **`QwenConfig`** (`src/qwenloop/domain/config.py:19-34`) gains
   `shell_timeout_seconds: int = 120`. `QwenConfigParser.parse` (`:58-92`) reads it with
   `int(data.get("shell_timeout_seconds", defaults.shell_timeout_seconds))`, and the
   existing positivity check (`:83-89`) covers it.
2. **`SettingsLoader.ENVIRONMENT_KEYS`** (`src/qwenloop/infrastructure/settings.py:33`)
   gains `"QWENLOOP_SHELL_TIMEOUT_SECONDS": "shell_timeout_seconds"`. Declare that name as
   a module constant with a `#:` comment, like the others (`:14-22`).
3. **`SandboxTools(worktree, *, allow_network=False, shell_timeout_seconds: float = 120.0)`**:
   a value ≤ 0 raises `ValueError`. It replaces the literal `timeout=120` at `:55`. The
   error text stays exactly `"command timed out"`.
4. **`_run_plan`** (`src/qwenloop/cli/app.py:251-282`) gains the keyword-only
   `shell_timeout_seconds: float = 120.0`, and constructs
   `SandboxTools(cwd, shell_timeout_seconds=shell_timeout_seconds)` at `:271`. Both call
   sites (`:231`, `:395`) pass `config.shell_timeout_seconds`.

## Where to change
- The four files on the card.

## Acceptance criteria
- [ ] The default is 120. A file value and `QWENLOOP_SHELL_TIMEOUT_SECONDS` each override it, and 0 or less is refused.
- [ ] `SandboxTools(..., shell_timeout_seconds=0.5)` times out `[sys.executable, "-c", "import time; time.sleep(5)"]` with `"command timed out"`.
- [ ] `_run_plan` passes the value through.
- [ ] The tenant's gates pass, with 100% coverage.

## Tests to write first (TDD)
- `tests/test_domain.py`: `test_shell_timeout_default_and_validation`
- `tests/test_settings.py`: `test_shell_timeout_from_file_and_environment`
- `tests/test_runner.py`:
  - `test_sandbox_shell_timeout_is_configurable`
  - `test_sandbox_rejects_a_non_positive_timeout`
  - `test_run_plan_passes_the_shell_timeout` (monkeypatch `SandboxTools` in `qwenloop.cli.app` to record its kwargs)

## Checks the lane must run (all must pass)
    (cd src/vibey_runners/qwen && uv run python -m pytest -q -p no:cacheprovider)
    (cd src/vibey_runners/qwen && uv run mypy --strict src/qwenloop && uv run lint-imports && uv run bandit -q -r src/qwenloop)
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The storm driver (it lives outside the repository).
- Any vibey code.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T21 — amqp-consumer-count

**Lane card.**

- **Depends on:** **R04** (`vibey_bootstrap.amqp`).
- **Wave:** 1 (after R04).
- **Files touched:**
  - `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/client.py`
  - `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/memory.py`
  - `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/interfaces/client_interface.py`
  - `src/vibey_tools/bootstrap/test/amqp/test_memory_client.py`, `test_client_unit.py` and `test_client_integration.py` (new tests, appended)
- **Shares a file with:** R04's module (it lands first).
- **Must keep passing unchanged:**
  - every R04 test
  - the whole vibey-bootstrap suite, `(cd src/vibey_tools/bootstrap && pytest test/ -m "not integration")`
  - all protected tests
- **Standing constraints:** see the header list. This lane changes the vibey-bootstrap tenant and runs its own gates (ADR-0022).

## Title
feat(bootstrap): vibey_bootstrap.amqp can say whether anyone consumes a queue

## Why
ADR-0045 §3: `auto` uses the RabbitMQ backend only when a harness service consumes the
machine's queue. Otherwise it degrades, announced, to the machine lock, so that a push
never waits on a queue nobody reads.

"Does anyone consume this queue?" is a passive `queue.declare`, whose reply carries the
consumer count. The family's AMQP client (lane R04) does not offer it. Sub-doctrine 10.e
says a capability gap is closed by teaching the family, not by a private copy in vibey.

## Required behaviour
1. **`AmqpClient.consumer_count(self, queue: str) -> int | None`** (it connects lazily, as
   the other methods do):
   1. it opens a **temporary** channel;
   2. `q = await channel.declare_queue(queue, passive=True)`;
   3. it returns `q.declaration_result.consumer_count`;
   4. a missing queue (`aio_pika.exceptions.ChannelNotFoundEntity`) returns `None`;
   5. it always closes the temporary channel, ignoring an already-closed one.
2. **`InMemoryAmqpClient.consumer_count(queue)`** returns the number of active consumers
   on a declared queue, or `None` for an undeclared one. A cancelled consumer no longer
   counts.
3. **`AmqpClientInterface`** gains the method.

## Where to change
- The three source files on the card. Follow R04's structure.

## Acceptance criteria
- [ ] In memory: an undeclared queue gives `None`, a declared one `0`, one after `consume` `1`, and after `cancel` `0` again.
- [ ] Unit test with R04's fake connector: a passive declare happens on a separate channel, which is then closed; the not-found error maps to `None`.
- [ ] Integration test (`@pytest.mark.integration`, skipped without `VIBEY_TEST_AMQP_URL`): against the pinned `rabbitmq:4-management-alpine`, the count follows a real consumer. This checks the ADR-0045 *Verification owed* item.
- [ ] The tenant's static gates pass.

## Tests to write first (TDD)
- `test/amqp/test_memory_client.py`: `test_consumer_count_follows_consume_and_cancel`
- `test/amqp/test_client_unit.py`: `test_consumer_count_uses_a_passive_declare_on_its_own_channel`, `test_consumer_count_of_a_missing_queue_is_none`
- `test/amqp/test_client_integration.py`: `test_consumer_count_against_a_real_broker`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/amqp -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)
    uv run lint-imports

## Out of scope
- Anything under `src/vibey/`.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T22 — harness-topology

**Lane card.**

- **Depends on:** **R04**, T05.
- **Wave:** 2 (after R04).
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/amqp_topology.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/amqp_topology_interface.py` (new)
  - `tests/infrastructure/test_harness/conftest.py` (new)
  - `tests/infrastructure/test_harness/test_amqp_topology.py` (new)
  - `tests/infrastructure/test_harness/test_amqp_topology_integration.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - T05's tests
  - `tests/meta/test_import_contracts_bind.py`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(test-harness): the RabbitMQ topology of one machine's test queue

## Why
8.e: the harness "takes its work from a queue on the bus surface", which 8.b makes
RabbitMQ. ADR-0045 §12 names each object:
- one quorum queue per machine, so each machine's runs execute where their worktrees are;
- `x-single-active-consumer`, so a second service on a machine is a standby that executes
  nothing (8.c: "a restart, never a second copy");
- a delivery limit and a dead-letter exchange, the backstop for a service that dies
  before it can record anything;
- a consumer timeout longer than the longest run.

The topology is declared in code at start (12.c: declared, not clicked), in the style of
ADR-0044's lane R12.

## Required behaviour
1. **`TestHarnessNames(*, prefix: str, instance: str)`**:
   - `exchange()` → `f"{prefix}.tests"`
   - `request_queue()` → `f"{prefix}.tests.{instance}"`
   - `routing_key()` → `instance`
   - `dead_exchange()` → `f"{prefix}.tests.dlx"`
   - `dead_queue()` → `f"{prefix}.tests.{instance}.dead"`
2. **`TestHarnessTopology(*, client: AmqpClientInterface, names: TestHarnessNamesInterface, settings: TestHarnessSettingsInterface)`.**
   - `request_queue_arguments(self) -> dict[str, object]` returns **exactly**:
     ```python
     {"x-queue-type": "quorum", "x-single-active-consumer": True,
      "x-delivery-limit": settings.delivery_limit,
      "x-dead-letter-exchange": names.dead_exchange(),
      "x-dead-letter-strategy": "at-least-once", "x-overflow": "reject-publish",
      "x-consumer-timeout": (settings.run_bound_seconds + 600) * 1000}
     ```
   - `async def declare(self) -> None` declares, once per instance (idempotent):
     - `names.exchange()` as `direct`;
     - `names.dead_exchange()` as `direct`;
     - `names.request_queue()` with those arguments, bound to the exchange on
       `names.routing_key()`;
     - `names.dead_queue()` with `{"x-queue-type": "quorum"}`, bound to the dead exchange
       on `names.routing_key()`.
3. **`tests/infrastructure/test_harness/conftest.py`** provides two fixtures:
   - `memory_amqp`, a fresh `InMemoryAmqpClient()`;
   - `amqp_url`, which calls `pytest.skip` unless `VIBEY_TEST_AMQP_URL` is set.
4. **Interfaces**: `TestHarnessNamesInterface` and `TestHarnessTopologyInterface`.

## Where to change
- The new module and interface. Copy R12's shape (`infrastructure/queue/rabbitmq_topology.py`) if it has landed; it is not a dependency.

## Acceptance criteria
- [ ] Against the in-memory client, each exchange, queue, argument and binding is declared once, however often `declare` runs.
- [ ] A message published to the exchange on the routing key lands in the request queue. A `dead_letter()` of it lands in the dead queue with its routing key kept.
- [ ] Integration test: a real broker accepts every argument, including `x-single-active-consumer` on a quorum queue, and a second consumer stays idle while the first holds the queue. Both are ADR-0045 *Verification owed* items.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `test_amqp_topology.py`:
  - `test_names`
  - `test_request_queue_arguments_are_exact`
  - `test_declare_is_idempotent`
  - `test_routing_and_dead_lettering`
  - `test_classes_satisfy_their_interfaces`
- `test_amqp_topology_integration.py` (integration):
  - `test_real_broker_accepts_every_argument`
  - `test_single_active_consumer_idles_the_second`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/meta/test_import_contracts_bind.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Consuming (T23) and publishing (T24).
- The chart (T27).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T23 — harness-service

**Lane card.**

- **Depends on:** **R04**, T13, T22.
- **Wave:** 6.
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/amqp_service.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/amqp_service_interface.py` (new)
  - `tests/infrastructure/test_harness/test_amqp_service.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - T13's and T22's tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(test-harness): the harness service consumes one machine's queue, one run at a time

## Why
8.e: "a single instance per deployment … takes its work from a queue on the bus surface".
ADR-0045 §9 and §12 set out how the service handles each request:
1. it consumes the machine's queue with prefetch 1;
2. it hands each request to the same `HarnessInstance` the `local` backend uses (T13),
   so a run means the same thing on both backends;
3. it writes the answer (the instance does), **then** publishes it to the requester's
   reply queue, **then** settles the delivery. That is ADR-0044 §13's order;
4. a dead-letter outcome settles with `dead_letter()`, which moves the request, literally,
   to a dead-letter queue.

A reconcile tick drains that queue into the store. A request that died before anything
was recorded still becomes a visible dead letter, so it is "never silently dropped"
(8.e). On SIGTERM, a run cut short is abandoned and requeued, never answered as a result.

## Required behaviour
1. **`TestHarnessService`**, built with these keywords:
   - `client: AmqpClientInterface`
   - `names: TestHarnessNamesInterface`
   - `topology: TestHarnessTopologyInterface`
   - `instance: HarnessInstanceInterface`
   - `codec: TestHarnessCodecInterface`
   - `store: TestRunStoreInterface`
   - `clock: Clock`
   - `settings: TestHarnessSettingsInterface`
   - `logger: Logger`
2. **`async def start(self) -> None`**:
   1. `await topology.declare()`;
   2. `self._tag = await client.consume(names.request_queue(), prefetch=1, handler=self._on_delivery)`;
   3. start a background task that calls `reconcile()` every `settings.reconcile_interval_seconds`.
3. **`_on_delivery(delivery)`**:
   1. Decode with `codec.from_bytes(delivery.body)`. A `MalformedTestHarnessMessage`, or a
      message that is not a `TestRunRequest`, is logged with its message id and
      `await delivery.dead_letter()`.
   2. Otherwise:
      1. `result = await instance.handle(request, delivery_count=delivery.delivery_count)`.
      2. If `delivery.properties.reply_to` is set, publish to exchange `""` with routing
         key `reply_to`, body `codec.to_bytes(result)`,
         `AmqpProperties(correlation_id=str(request.request_id), type="test.result")` and
         `mandatory=False`. A publish error (the requester is gone) is logged, not raised.
      3. Settle:
         - `outcome is ABANDONED` → `await delivery.abandon()`, so it is requeued and runs
           again after the restart;
         - `status is EXECUTED` and `outcome.is_dead_letter()` → `await delivery.dead_letter()`;
         - otherwise → `await delivery.complete()`.
4. **`async def reconcile(self) -> int`** loops over `await client.get(names.dead_queue())`
   until it returns `None`:
   - Undecodable → `store.put_malformed(delivery.body, message_id=..., reason="undecodable request in the dead queue", received_at=clock.now())`,
     then `complete()`.
   - `store.dead_letter_for_request(request.request_id)` exists → `complete()`.
   - Otherwise:
     1. write `DeadLetter.from_request(request, run_id=uuid4(), outcome=CRASHED, reason=f"the request exceeded the delivery limit ({delivery.delivery_count} deliveries) before the service recorded it", record=None, at=now)`;
     2. `put_answer` an `EXECUTED` / `CRASHED` result;
     3. reply as in 3.2.2;
     4. `complete()`.

   It returns the number handled.
5. **`async def stop(self, *, grace_seconds: float) -> None`**:
   1. `await client.cancel(self._tag)`, and stop the reconcile task;
   2. if a delivery is in flight, wait up to `grace_seconds` for it;
   3. then call `await instance.abandon_current()`, and wait for the handler to settle.
6. **The interface** is `TestHarnessServiceInterface`.

## Where to change
- The new module and interface. Use R04's `AmqpDelivery` settle vocabulary: `complete`, `abandon`, `dead_letter`.

## Acceptance criteria
All with `InMemoryAmqpClient`, a real `tmp_path` store and a fake instance:
- [ ] A request is handled, its answer is published to its reply queue with the right correlation id, and the delivery is completed.
- [ ] A dead-letter outcome moves the message to the dead queue.
- [ ] `reconcile` turns an unrecorded dead message into a dead letter and an answer, completes one that is already recorded, and keeps an undecodable one as malformed.
- [ ] `stop` abandons an in-flight run, and the message is requeued with its delivery count incremented.
- [ ] A reply to a missing `reply_to` is skipped without error.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_amqp_service.py`:
  - `test_handles_replies_and_completes`
  - `test_dead_letter_outcome_moves_the_message`
  - `test_malformed_request_is_dead_lettered`
  - `test_reconcile_records_an_unrecorded_dead_message`
  - `test_reconcile_completes_a_recorded_one`
  - `test_reconcile_keeps_undecodable_messages`
  - `test_stop_abandons_and_requeues`
  - `test_missing_reply_to_is_skipped`
  - `test_service_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The requester (T24) and the CLI `serve` command (T25).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T24 — harness-amqp-client

**Lane card.**

- **Depends on:** **R04**, T14, T21, T22.
- **Wave:** 6.
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/amqp_client.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/amqp_client_interface.py` (new)
  - `tests/infrastructure/test_harness/test_amqp_client.py` (new)
- **Shares a file with:** none.
- **Must keep passing unchanged:**
  - T14's and T22's tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(test-harness): the requester puts a run on the machine's queue and waits for its answer

## Why
8.e: "a commit hook, a storm lane, a reviewer and the command line all put their run on
the queue and wait for its result". ADR-0045 §3 and §12 set out what the `rabbitmq`
requester does:
- it uses the same request builder and fast path as the `local` one (T14), so a repeat
  is answered without touching the broker;
- before publishing, it checks that a service consumes the queue (T21), so `auto` can
  degrade, announced, instead of waiting on a queue nobody reads;
- it publishes persistent, mandatory, with no expiration, and waits on its own exclusive
  reply queue, correlated by request id.

## Required behaviour
1. **`AmqpHarnessClient`**, built with these keywords:
   - `client: AmqpClientInterface`
   - `names: TestHarnessNamesInterface`
   - `codec: TestHarnessCodecInterface`
   - `builder: TestRunRequestBuilderInterface`
   - `fast_path: ReuseFastPathInterface`
   - `settings: TestHarnessSettingsInterface`

   It implements `HarnessClientInterface` (T14).
2. **`async def unavailable_reason(self) -> str | None`** returns:
   - `f"broker unreachable: {exc}"` for any connection error;
   - `f"no harness service has declared {names.request_queue()}"` when the count is `None`;
   - `f"no harness service consumes {names.request_queue()}"` when it is `0`;
   - otherwise `None`.
3. **`async def request(self, *, cwd, argv, gates, fresh, grant=False, environ) -> TestRunResult`**
   builds the request, returns the fast path's answer if there is one, and otherwise
   returns `await self.submit(request)`.
4. **`async def submit(self, request) -> TestRunResult`**:
   1. On first use, declare the reply queue:
      `reply = await client.declare_queue("", durable=False, exclusive=True, auto_delete=True)`.
      Consume it with prefetch 16, routing each reply by `correlation_id` to a pending
      future. An unknown or undecodable reply is completed and dropped with a log line.
   2. Publish `codec.to_bytes(request)` to `names.exchange()` on `names.routing_key()`,
      with `AmqpProperties(message_id=str(request_id), correlation_id=str(request_id), reply_to=reply, type="test.request", delivery_mode=2)`
      and `mandatory=True`. Set no expiration.
   3. Wait for the future, up to `settings.wait_seconds`. On timeout, return
      `STILL_RUNNING` (backend `"rabbitmq"`) with the detail
      `"the run is queued or running; run the same command again to receive its result"`.
5. **`async def close(self) -> None`** cancels the reply consumer.

## Where to change
- The new module and interface.

## Acceptance criteria
With `InMemoryAmqpClient`, and a stub responder that consumes the request queue and answers with `TestRunResult`s:
- [ ] A request round-trips.
- [ ] Two concurrent requests never receive each other's answers.
- [ ] The fast path answers without publishing anything.
- [ ] `unavailable_reason` returns each of its four values.
- [ ] A missing answer gives `STILL_RUNNING` after `wait_seconds` (1 s in the test).
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_amqp_client.py`:
  - `test_request_round_trip`
  - `test_concurrent_requests_do_not_cross`
  - `test_fast_path_publishes_nothing`
  - `test_unavailable_reasons` (parametrized)
  - `test_still_running_after_the_wait`
  - `test_unknown_reply_is_dropped`
  - `test_client_satisfies_its_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Choosing between backends (T25).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T25 — harness-backend-selection

**Lane card.**

- **Depends on:** **R01, R17, R04**, T15, T23, T24.
- **Wave:** 8 (after R17).
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/backend.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/backend_interface.py` (new)
  - `src/vibey/bootstrap.py` (`TestHarnessComposition` only)
  - `src/vibey/bootstrap_interface.py`
  - `src/vibey/cli/test_harness.py` (the `serve` command)
  - `src/vibey/cli/interfaces/test_harness_interface.py`
  - `tests/infrastructure/test_harness/test_backend.py` (new)
  - `tests/test_bootstrap.py` and `tests/cli/test_test_harness_cli.py` (new tests, appended; T15's `test_rabbitmq_backend_is_not_configured_in_this_build` is replaced, the only edit to an existing test)
- **Shares a file with:**
  - `bootstrap.py` (after R17, before R27);
  - `cli/test_harness.py` (after T16).
- **Must keep passing unchanged:**
  - T15's and T16's other tests
  - `tests/test_bootstrap.py`
  - `tests/cli/*`
  - all protected tests
- **Standing constraints:** see the header list. Tests inject `InMemoryAmqpClient` through the composition's `amqp_factory` seam.

## Title
feat(test-harness): auto uses the queue when a service consumes it, and vibey test-harness serve runs that service

## Why
ADR-0045 §3 defines the three backends:
- **`auto`** (the default) uses the machine's queue when `[bus] amqp_url` resolves, the
  broker answers, and a service consumes the queue. Otherwise it uses the machine lock,
  and **says so, and why**, on the second line of the answer. It is not a silent fallback,
  because both paths take the same machine lock and write the same store.
- **`rabbitmq`** never degrades. Without a URL it fails, naming the remedies, as ADR-0044
  §1 does for `QueueBackendNotConfigured`.
- **`local`** never touches the broker.

The AMQP URL's precedence (environment, then file, then default) is already R17's
`QueueBackendSettings`, and it is reused (10.e). The service needs an entry point a
laptop or a chart can run: `vibey test-harness serve`. It drains on SIGTERM, copying the
worker (`cli/main.py:1519-1540`: `add_signal_handler` at `:1525`, the latch release at `:1537`).

## Required behaviour
1. **`TestHarnessBackendResolver`**, in `backend.py`:
   `async def resolve(self, *, backend: str, amqp_url: str | None, probe: Callable[[], Awaitable[str | None]]) -> tuple[str, str | None]`:
   - `local` → `("local", None)`;
   - `rabbitmq` with no URL → raise `TestHarnessNotConfigured`, naming both remedies
     verbatim: `export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/` and
     `export VIBEY_HARNESS_BACKEND=local`;
   - `rabbitmq` with a URL → `("rabbitmq", None)`, without probing;
   - `auto` with no URL → `("local", "backend=local (auto: no [bus] amqp_url is configured)")`;
   - `auto` with a URL → `reason = await probe()`. If `reason is None`, then
     `("rabbitmq", None)`, otherwise `("local", f"backend=local (auto: {reason})")`.
2. **`TestHarnessComposition`** gains:
   - the constructor keywords `config: VibeyConfig | None = None` and
     `amqp_factory: Callable[[str], AmqpClientInterface] | None = None`. The default is
     `lambda url: AmqpClient(AmqpSettings(url=url))` (R04);
   - `amqp_url` and `prefix`, from R17's `QueueBackendSettings.from_sources(config, environ)`;
   - `names()` is `TestHarnessNames(prefix=..., instance=settings.instance)`, and
     `topology()` is built from it;
   - `client()` resolves through the resolver. The probe builds an `AmqpHarnessClient`
     and returns its `unavailable_reason()`. `rabbitmq` returns that client, `local`
     returns T15's `LocalHarnessClient`, and `announcement` is the resolver's second value;
   - `service() -> TestHarnessService`, which requires a URL, else raises
     `TestHarnessNotConfigured` as in behaviour 1, and uses `instance(backend="rabbitmq")`;
   - `async def aclose(self)`, which closes the AMQP client if one was built.

   `build_test_harness` passes `config` through.
3. **`vibey test-harness serve`**, in `cli/test_harness.py`, through a
   `TestHarnessServeCommand` class:
   1. build the composition and the service, then `await service.start()`;
   2. print `test-harness started: instance=<instance> queue=<request queue> state_dir=<dir>`;
   3. install `loop.add_signal_handler(SIGTERM, ...)` and `SIGINT`, setting a stop event,
      then release the early latch with `SIGTERM_LATCH.release()`. If
      `SIGTERM_LATCH.fired`, stop at once, as the worker does;
   4. wait for the event, then `await service.stop(grace_seconds=settings.run_bound_seconds)`
      and `await composition.aclose()`, and exit 0;
   5. `TestHarnessNotConfigured` exits 2 with its message.

## Where to change
- The files on the card.

## Acceptance criteria
- [ ] The resolver table holds for every row.
- [ ] `auto` with no URL composes the local client, and announces why.
- [ ] `auto` with a URL but no consumer composes the local client, and announces "no harness service consumes …".
- [ ] `auto` with a consumer (an in-memory stub consumer) composes `AmqpHarnessClient`.
- [ ] `rabbitmq` without a URL fails naming both remedies. `vibey test run --backend rabbitmq` exits 2 with that message.
- [ ] `serve` starts, handles one request from the in-memory queue, and drains on a simulated SIGTERM, exiting 0.
- [ ] 100% coverage on `cli/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_backend.py`: `test_resolver_table` (parametrized)
- `tests/test_bootstrap.py`:
  - `test_auto_without_a_url_is_local_and_says_why`
  - `test_auto_without_a_consumer_is_local_and_says_why`
  - `test_auto_with_a_consumer_is_rabbitmq`
  - `test_rabbitmq_without_a_url_names_both_remedies`
- `tests/cli/test_test_harness_cli.py`:
  - `test_serve_starts_handles_and_drains`
  - `test_serve_without_a_url_exits_2`
  - `test_run_with_rabbitmq_backend_and_no_url_exits_2`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/cli tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The chart (T27).
- `vibey install --rabbitmq` (R33).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T26 — engine-route-env

**Lane card.**

- **Depends on:** **R20, R27, R28**, T05.
- **Wave:** 8 (after R28).
- **Files touched:**
  - `src/vibey/infrastructure/test_harness/routing_env.py` (new)
  - `src/vibey/infrastructure/test_harness/interfaces/routing_env_interface.py` (new)
  - `src/vibey/infrastructure/engines/adapter_factory.py` (R28's `SubprocessAdapterFactory`: one keyword)
  - `src/vibey/bootstrap.py` (where the factory and `build_loop_service` are composed)
  - `tests/infrastructure/test_harness/test_routing_env.py` (new)
  - `tests/infrastructure/engines/test_adapter_factory.py` and `tests/test_bootstrap.py` (new tests, appended)
- **Shares a file with:** `bootstrap.py` (after R28, the end of the ADR-0044 chain).
- **Must keep passing unchanged:**
  - `tests/infrastructure/engines/*`, including `test_loop_process_adapter.py` and `test_local_engines.py`
  - `tests/system/*`
  - `tests/live/**` (protected)
  - every R27 and R28 test
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(engines): engine sessions carry the test-harness route, so a model's pytest is queued without it knowing

## Why
8.e covers "a storm lane", which is a model running `uv run pytest` through its shell.
ADR-0045 §10 routes that through the pytest plugin, which reads `VIBEY_HARNESS_ROUTE`
from its environment. So every engine vibey launches must carry the route in its
environment:
- BUILD sessions, spawned as subprocesses today (`bootstrap.py:736-738`);
- local engines, which get an overlay (`infrastructure/engines/local_engines.py:144-148`);
- runs inside a loop service (ADR-0044 §13, R27's `build_loop_service`).

It also carries `VIBEY_HARNESS_WAIT_SECONDS` below qwenloop's shell limit
(`engine_wait_seconds`, default 110, against `tools.py:55`'s 120). A model then reads
"still running; run the same command again" instead of a killed command, and its retry
is answered from the record (ADR-0045 §11).

After R28, every engine adapter is built by `SubprocessAdapterFactory` or
`ServiceAdapterFactory`, and a loop service builds its runners' environment in
`build_loop_service`. Those are the two places to change.

## Required behaviour
1. **`HarnessRoutingEnvironment(settings: TestHarnessSettingsInterface)`.**
   `overlay(self) -> dict[str, str]` returns:
   - `{}` when `settings.route_engines is TestRouteMode.OFF`;
   - otherwise
     `{"VIBEY_HARNESS_ROUTE": settings.route_engines.value, "VIBEY_HARNESS_WAIT_SECONDS": str(settings.engine_wait_seconds)}`.
2. **`SubprocessAdapterFactory`** (R28) gains the keyword
   `routing_overlay: Mapping[str, str] | None = None`. Each adapter's `env_overlay`
   becomes `{**routing_overlay, **<the overlay it has today>}`, so the engine's own keys
   win.
3. **`bootstrap.py`** builds `HarnessRoutingEnvironment(TestHarnessSettings.from_sources(config, environ)).overlay()`
   once, and passes it:
   - to `SubprocessAdapterFactory(routing_overlay=...)`;
   - merged *under* `LocalEndpointEnvironment(environ).overlay_for(engine_id)` in
     `build_loop_service` (R27), so it reaches a service's runners.

   Find the construction sites with `grep -n "SubprocessAdapterFactory\|build_loop_service\|env_overlay" src/vibey/bootstrap.py src/vibey/infrastructure/engines/*.py`.
4. With the default `route_engines = "off"`, every environment is byte-identical to today's.
5. **The interface** is `HarnessRoutingEnvironmentInterface`.

## Where to change
- The files on the card.

## Acceptance criteria
- [ ] The overlay is empty when the mode is off, and carries both variables when it is `locked` or `queue`.
- [ ] With `[test_harness] route_engines = "queue"`, a composed subprocess adapter's launcher environment (R20's `EngineProcessLauncher.environment()`) contains both variables, for a paid and for a local engine. An engine key of the same name would win.
- [ ] `build_loop_service`'s runner environment contains them.
- [ ] With the default, the existing engine and system tests pass unchanged.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/test_harness/test_routing_env.py`: `test_overlay_table` (parametrized), `test_routing_env_satisfies_its_interface`
- `tests/infrastructure/engines/test_adapter_factory.py`: `test_routing_overlay_sits_under_the_engine_overlay`
- `tests/test_bootstrap.py`: `test_engines_carry_the_route_when_configured`, `test_loop_service_runners_carry_the_route`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/infrastructure/test_harness tests/test_bootstrap.py tests/system tests/live
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Changing the default (T28).
- Adopter projects without vibey in their venv. ADR-0045 names that as a follow-up.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T27 — chart-test-harness

**Lane card.**

- **Depends on:** **R29, R30**, T25, T26.
- **Wave:** 9 (after R30).
- **Files touched:**
  - `deploy/helm/vibey/templates/test-harness.yaml` (new)
  - `deploy/helm/vibey/templates/loop-services.yaml` (R30's; env additions only)
  - `deploy/helm/vibey/values.yaml`
  - `deploy/helm/golden/render.sh` (one profile)
  - `deploy/helm/golden/test-harness.yaml` (new, generated)
  - the other goldens, regenerated. They must stay byte-identical, because `testHarness.enabled` defaults to `false`
  - `tests/infrastructure/test_chart_test_harness_golden.py` (new)
- **Shares a file with:** the chart and its goldens (R29 → R30 → R31 → R34 → this lane → T28).
- **Must keep passing unchanged:**
  - every existing golden, including the `keda-*` goldens
  - `tests/infrastructure/db/test_keda_scaler_query.py`
  - R29's and R30's chart tests
  - all protected tests
- **Standing constraints:** see the header list. Use helm v4.2.4, as R30 does. Never hand-edit a golden: run `deploy/helm/golden/render.sh --update`.

## Title
feat(chart): one test-harness Deployment per cluster, and loop services route their engines' pytest to it

## Why
8.e counts a cluster as one deployment. ADR-0045 §1 and §12 make its instance one
Deployment:
- **`replicas: 1`** is a literal, not a value, because 8.e fixes the number (12.c: a key
  that could only be set to what the law forbids is not configurability);
- **`strategy: Recreate`**, so a rollout never runs two;
- it consumes `vibey.tests.cluster`;
- it mounts the worktrees PVC at `/work`, like the loop services (R30), because a run
  executes in the requester's worktree.

The loop services' engines then carry `VIBEY_HARNESS_ROUTE`, and their models' pytest
runs go to it.

## Required behaviour
1. **`values.yaml`** gains:
   ```yaml
   testHarness:
     enabled: false          # T28 turns this on
     instance: cluster
     runBoundSeconds: 3600
     routeEngines: queue
     engineWaitSeconds: 110
     resources: {}
     testDatabase:           # the tests' own PostgreSQL; unset leaves VIBEY_TEST_DATABASE_URL unset
       existingSecret: ""
       key: ""
   ```
2. **`templates/test-harness.yaml`**, rendered when `testHarness.enabled`. It is a
   `Deployment` named `<fullName>-test-harness`, with:
   - `replicas: 1` (a literal) and `strategy: {type: Recreate}`;
   - the vibey image and pull policy, as the worker has;
   - `args: ["vibey", "test-harness", "serve"]`;
   - `terminationGracePeriodSeconds: {{ add .Values.testHarness.runBoundSeconds 60 }}`;
   - the worktrees PVC `<fullName>-worktrees` at `/work`, with R30's
     `vibey.dev/worktrees` label and, for `ReadWriteOnce`, its required pod affinity
     (copy from `loop-services.yaml`);
   - this environment:
     - `VIBEY_HARNESS_BACKEND=rabbitmq`
     - `VIBEY_HARNESS_INSTANCE={{ .Values.testHarness.instance }}`
     - `VIBEY_HARNESS_STATE_DIR=/work/.vibey-test-harness`
     - `VIBEY_HARNESS_ROOT=/work`
     - `VIBEY_BUS_AMQP_URL` from R29's broker Secret key `amqp-url`, or
       `broker.existingSecret` / `broker.existingSecretUrlKey`
     - `VIBEY_TEST_DATABASE_URL` from `testHarness.testDatabase` when both fields are set.

   The render **fails**, with `fail`, when `testHarness.enabled` and neither
   `broker.enabled` nor `broker.existingSecret` is set. The message is: "testHarness needs
   a broker: set broker.enabled=true or broker.existingSecret".
3. **`templates/loop-services.yaml`**: when `testHarness.enabled`, each loop-service
   container also gets `VIBEY_HARNESS_ROUTE={{ .Values.testHarness.routeEngines }}`,
   `VIBEY_HARNESS_WAIT_SECONDS`, `VIBEY_HARNESS_BACKEND=rabbitmq`,
   `VIBEY_HARNESS_INSTANCE` and `VIBEY_HARNESS_STATE_DIR` (the same path). Its runners
   inherit the service's environment (R20's launcher).
4. **`render.sh`** gains
   `profile test-harness --show-only templates/test-harness.yaml -- --set testHarness.enabled=true`,
   next to the existing profiles (`render.sh`, the `profile` lines).
5. **`tests/infrastructure/test_chart_test_harness_golden.py`** skips when `helm` is not
   on `PATH`. It renders with `helm template` and asserts the fields in behaviour 2. It
   asserts the `fail` message with `broker.enabled=false`. With `testHarness.enabled=true`,
   it asserts that the loop-service containers carry the five variables.

## Where to change
- The files on the card. Copy R30's template for the PVC mount, the label, the affinity and the broker Secret wiring.

## Acceptance criteria
- [ ] `deploy/helm/golden/render.sh` passes, and the only new golden is `test-harness.yaml`.
- [ ] The new test passes.
- [ ] `helm lint --strict` passes with `testHarness.enabled=true`.

## Tests to write first (TDD)
- `tests/infrastructure/test_chart_test_harness_golden.py`:
  - `test_one_recreated_replica_serving_the_cluster_queue`
  - `test_it_mounts_the_worktrees_like_the_loop_services`
  - `test_it_needs_a_broker`
  - `test_loop_services_route_their_engines_when_enabled`

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_test_harness_golden.py tests/infrastructure/db/test_keda_scaler_query.py
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Turning it on (T28).
- Cluster-smoke contracts for it ("the test-harness Deployment consumes `vibey.tests.cluster`"). That is a follow-up to R32's cluster job, not part of this lane.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane T28 — route-flip

**Lane card.**

- **Depends on:** T16, T17, T18, T19, T25, T26, T27, **and the operator's ratification of sub-doctrine 8.e**, with the reuse-window amendment ADR-0045 asks for. Do not start before both.
- **Wave:** 10.
- **Files touched:**
  - `pyproject.toml` (the ini value and its comment)
  - `src/vibey/domain/config.py` (one default)
  - `tests/domain/test_config.py` (T05's `test_test_harness_defaults`, the only edit to an existing assertion)
  - `deploy/helm/vibey/values.yaml` (`testHarness.enabled: true`)
  - `deploy/helm/golden/*` (regenerated)
- **Shares a file with:**
  - `pyproject.toml` (after T07);
  - `domain/config.py` (after R34);
  - the chart (after T27).
- **Must keep passing unchanged:**
  - the entire suite, now run *through* the harness, including all protected tests
  - the `keda-*` goldens
  - `tests/infrastructure/db/test_keda_scaler_query.py`
- **Standing constraints:** see the header list.

## Title
feat(test-harness)!: pytest runs, engine sessions and the cluster route test runs through the harness queue

## Why
ADR-0045 §15: first serialize, then queue. By this lane, the machine lock (T07), the
single gated push request (T18), CI's always-fresh route (T19), the `rabbitmq` backend
with its announced `auto` degrade (T25), the engine route (T26) and the cluster
Deployment (T27) have each landed behind their defaults, and are green.

This lane flips only defaults, so reverting it restores the `locked` behaviour exactly.
That is CDD's bounded divergence (sub-doctrine 9.c). It must not land before 8.e is
ratified (ADR-0045, non-negotiable 7).

## Required behaviour
1. **`pyproject.toml`**: `vibey_harness_route = "queue"` in `[tool.pytest.ini_options]`.
   Update its comment to name 8.e, ADR-0045, and the bypass (`VIBEY_HARNESS_ROUTE=off`
   runs directly, and `=locked` serializes only).
2. **`TestHarnessConfig.route_engines`** defaults to `"queue"`. T05's
   `test_test_harness_defaults` asserts the new default. That is the only edit to an
   existing assertion.
3. **`values.yaml`**: `testHarness.enabled: true`. Regenerate the goldens with
   `render.sh --update`. `default.yaml` gains the Deployment and the loop-service
   variables. The `keda-*` goldens stay byte-identical.
4. **The commit carries a `BREAKING CHANGE:` footer**:
   - a root `pytest` run is now a test-harness request: it is answered from the record
     while that record is valid, and otherwise executed once per machine;
   - `VIBEY_HARNESS_ROUTE=off` restores a direct run;
   - engine sessions carry the route;
   - the chart runs a `test-harness` Deployment by default (`testHarness.enabled=false`
     opts out), and it needs a broker.

## Where to change
- The files on the card.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain`, run twice, prints `executed` and then `reused` on its first line, with exit 0 both times.
- [ ] The whole-suite coverage run and the four per-layer reports pass. `.coverage` is restored by the harness (ADR-0045 §8).
- [ ] `VIBEY_HARNESS_ROUTE=off uv run pytest -q -p no:cacheprovider tests/cli/test_pytest_route.py` runs directly.
- [ ] `render.sh` passes, and the `keda-*` goldens are unchanged.
- [ ] `git diff --stat` shows no protected file.

## Tests to write first (TDD)
- Update T05's default test (behaviour 2).
- `tests/cli/test_pytest_route.py` (appended): `test_the_repository_ini_routes_to_the_queue`, which reads `pyproject.toml` with `tomllib` and asserts `vibey_harness_route == "queue"`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    VIBEY_HARNESS_ROUTE=off uv run pytest -q -p no:cacheprovider tests/cli/test_pytest_route.py
    deploy/helm/golden/render.sh
    git diff --stat HEAD~1 -- tests/domain/test_noloss*.py tests/domain/test_briefing.py tests/infrastructure/db/test_chaos.py tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- Docs, ADRs, CHANGELOG, CONTRIBUTING.md and the agent-surface trees. The docs wave owns them, as ADR-0045's *Owes* line lists.
- The canon text of 8.e. It is the operator's to ratify.

Do not push. Commit locally as `feat(test-harness)!: …` with the `BREAKING CHANGE:` footer.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
