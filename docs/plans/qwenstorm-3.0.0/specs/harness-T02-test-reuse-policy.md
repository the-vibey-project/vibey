## Title
feat(domain): when a recorded test result answers a repeat request

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:279-286`): "a repeat request
receives the recorded result, while that result is still valid, instead of a second
execution; a request may always ask for a fresh run", and a dead-lettered run "is never
retried forever". Draft ADR-0045 §7 bounds reuse:
- a cached FAIL is reused only inside a short window (`fail_ttl`), a PASS inside a longer one;
- a key that has both passed and failed is contradictory evidence, so it runs again
  (sub-doctrine 10.f: "missing or contradictory evidence stays unknown");
- a key whose last run was dead-lettered stays **parked** until someone requeues it
  (ADR-0024: every bounded ladder parks with a grant).

The decision is pure (`now` is an argument), so it lives in `src/vibey/domain/`, which
`tests/domain/test_domain_purity.py` keeps free of I/O, async and clock reads.

## Required behaviour
Create `src/vibey/domain/test_reuse.py`. It imports `TestOutcome` from
`vibey.domain.test_harness` (lane harness-T01).

1. **`RecordedAttempt`**, `@dataclass(frozen=True, slots=True)`:
   - `run_id: str`
   - `attempt: int` (≥ 1)
   - `outcome: TestOutcome | None` (`None` means still running)
   - `recorded_at: datetime | None` — required and timezone-aware when `outcome` is set
   - `reusable: bool`
   - `answered: bool = False`

   Violations raise `ValueError`.
2. **`ReuseVerdict(StrEnum)`**: `EXECUTE = "execute"`, `REUSE = "reuse"`, `PARKED = "parked"`.
3. **`ReuseDecision`**, frozen and slotted: `verdict: ReuseVerdict`,
   `attempt: RecordedAttempt | None`, `flaky: bool`, `flaky_runs: tuple[str, ...]`, `reason: str`.
4. **`TestReusePolicy(pass_ttl: timedelta, fail_ttl: timedelta)`**. A negative ttl raises
   `ValueError`.

   `decide(self, attempts: Sequence[RecordedAttempt], *, now: datetime, fresh: bool, grant: bool) -> ReuseDecision`
   raises `ValueError` for a naive `now`. It sorts attempts by `attempt` (not by list position),
   keeps the **terminal** ones (`outcome is not None`), and lets `latest` be the last terminal
   one. It then applies these rules in order:
   1. `latest` exists, `latest.outcome.is_dead_letter()`, `not latest.answered` and
      `not grant` → `PARKED`, `attempt=latest`, reason
      ``f"run {latest.run_id} ended {latest.outcome.value}; requeue it with `vibey test requeue {latest.run_id}`"``.
   2. `grant` → `EXECUTE`, reason `"a requeue granted a new run"`. Otherwise `fresh` →
      `EXECUTE`, reason `"a fresh run was requested"`.
   3. Among terminal attempts with `reusable` set and `outcome.is_reusable()`: when both
      `PASSED` and `FAILED` occur → `EXECUTE` with `flaky=True`, `flaky_runs = (<run_id of the latest passed>, <run_id of the latest failed>)`
      and reason
      `f"this input has both passed (run {p}) and failed (run {f}); the evidence is contradictory, so it runs again"`.
   4. No `latest` → `EXECUTE`, reason `"no recorded result for this input"`.
   5. `latest.reusable` is false, or `latest.outcome.is_reusable()` is false → `EXECUTE`,
      reason `"the latest recorded run of this input is not reusable"`.
   6. `ttl = pass_ttl` when `latest.outcome is TestOutcome.PASSED`, else `fail_ttl`. When
      `now - latest.recorded_at <= ttl` → `REUSE`, `attempt=latest`, reason
      `f"reusing run {latest.run_id}, recorded {latest.recorded_at.isoformat()}"`. Otherwise
      `EXECUTE`, reason `f"the recorded result from {latest.recorded_at.isoformat()} has expired"`.

   `flaky` is `False` and `flaky_runs` is `()` in every rule except 3; `attempt` is `None`
   except in rules 1 and 6's `REUSE`.
5. **The interface** `src/vibey/domain/interfaces/test_reuse_interface.py` declares
   `TestReusePolicyInterface`, a `@runtime_checkable` Protocol with `decide` (same signature).
   It does not import `vibey.domain.test_reuse` at run time.

## Where to change
- New `src/vibey/domain/test_reuse.py` and `src/vibey/domain/interfaces/test_reuse_interface.py`,
  in the style of `src/vibey/domain/circuit.py` and its interface.
- New `tests/domain/test_test_reuse.py`.

## Acceptance criteria
- [ ] Every rule has a test, and rule order is proven: a grant beats parked; fresh does not beat parked; parked beats flaky.
- [ ] Running attempts (`outcome is None`) never influence the decision.
- [ ] Attempts are ordered by `attempt`, not by list position.
- [ ] 100% coverage of `src/vibey/domain/`; `tests/domain/test_domain_purity.py` passes.

## Tests to write first (TDD)
`tests/domain/test_test_reuse.py` imports `from vibey.domain import test_reuse as tr` and
`from vibey.domain import test_harness as th`, with a fixed aware `NOW`:
- `test_unanswered_dead_letter_parks_the_key`
- `test_answered_dead_letter_does_not_park`
- `test_grant_runs_a_parked_key`
- `test_fresh_does_not_run_a_parked_key`
- `test_fresh_executes_otherwise`
- `test_pass_and_fail_mark_the_key_flaky` (checks `flaky_runs` order)
- `test_no_record_executes`
- `test_unreusable_latest_executes`
- `test_pass_inside_its_window_is_reused`
- `test_fail_inside_its_shorter_window_is_reused`
- `test_expired_results_execute` (parametrized pass and fail)
- `test_running_attempts_are_ignored`
- `test_attempts_are_sorted_by_number`
- `test_naive_now_and_negative_ttl_are_rejected`
- `test_recorded_attempt_invariants` (parametrized: attempt 0, outcome without `recorded_at`, naive `recorded_at`)
- `test_policy_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Where attempts come from (the file store, harness-T10).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T01-test-run-key.
- **Files touched:** the three files above.
- **Shares a file with:** none.
- **Must keep passing unchanged:** `tests/domain/test_domain_purity.py`, harness-T01's tests, and the protected tests.
- **Registry (amendment A4):** nothing. `TestReusePolicy` is a pure policy (`PURE_POLICY`), not a seam.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
