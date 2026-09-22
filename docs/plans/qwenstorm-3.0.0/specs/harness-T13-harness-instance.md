## Title
feat(test-harness): the instance runs a request once, answers repeats, and parks what dies

## Why
This is the core of sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:271-286`)
and draft ADR-0045 §2–§9. Both backends feed requests to this one class, so a run means the same
thing whichever backend carried it. It:
- answers a request it has already answered (idempotent under redelivery, CLAUDE.md);
- refuses a request it cannot execute, as a dead letter;
- takes the machine lock (harness-T06), or answers `saturated`;
- under the lock, first marks every attempt still recorded `running` as `crashed` — the lock
  guarantees its recorder is dead (ADR-0045 §2);
- keys the run from the tree it will actually test (harness-T08);
- reuses, parks or executes, as harness-T02 decides;
- runs the gates (harness-T12), keeps the coverage data, records the attempt (harness-T10), and
  dead-letters the three dead-letter outcomes with their evidence ("never retried forever and never
  silently dropped", 8.e).

## Required behaviour
Create `src/vibey/infrastructure/test_harness/instance.py`:
1. **`HarnessInstance`**, built with keyword-only arguments: `settings: TestHarnessSettingsInterface`,
   `store: TestRunStoreInterface`, `lock: MachineLockInterface`, `digest: WorkingTreeDigestInterface`,
   `executor: TestRunExecutorInterface`, `child_env: ChildEnvironmentInterface`,
   `gates: CoverageGatesInterface`, `keeper: CoverageDataKeeperInterface`,
   `reuse: TestReusePolicyInterface`, `outcomes: TestOutcomePolicyInterface`,
   `clock: Clock` (`src/vibey/application/interfaces/system.py:11-12`),
   `instance_environ: Mapping[str, str]`, `backend: str`, `pid: int`.
2. **`async def handle(self, request: TestRunRequest, *, delivery_count: int = 0) -> TestRunResult`**,
   in this order. `now = clock.now()` at entry. Every returned result is first written with
   `store.put_answer`, except a result whose outcome is `ABANDONED`, which is returned but not
   stored, so that a redelivery runs it again.
   1. **Already answered.** If `store.answer(request.request_id)` returns an answer whose outcome
      is not `ABANDONED`, return it unchanged.
   2. **Validation**, without the lock. The request is unexecutable, with its reason, if:
      - `cwd` does not exist, or `Path(cwd).resolve()` is not `settings.root.resolve()` or under it
        ("the request's cwd is outside this instance's root");
      - an `env` name does not match `settings.pass_env` ("the request passes a variable this
        instance does not accept: <name>");
      - `request.selection.command != settings.command` ("the request's command differs from this
        instance's configured command").

      Then `store.dead_letter(DeadLetter.from_request(request, run_id=uuid4(), outcome=UNEXECUTABLE, reason=<why>, record=None, at=now))`
      and return `EXECUTED` with outcome `UNEXECUTABLE`, that `run_id`, `key="unkeyed"` (no tree
      was digested), `exit_code=None` and the reason as `detail`.
   3. **The lock.** `hold = await lock.acquire(timeout_seconds=max(0.0, (request.start_by - now).total_seconds()), holder={"run_id": None, "request_id": str(request.request_id), "cwd": request.cwd, "backend": self._backend})`.
      `None` → return `SATURATED` (outcome `None`) with the detail
      `"the machine's test lock was not free before start_by"`.
   4. **Under the lock**, inside `try:` with `hold.release()` in `finally:`:
      1. **Crash sweep.** For each `r` in `store.running()`:
         `finished = r.finish(outcome=CRASHED, exit_code=None, timed_out=False, tree_after=None, finished_at=now, duration_seconds=None, load_after=None, output_tail=executor.tail(Path(r.log_path)), gate_reports=(), detail="the instance recording this run died before it finished", coverage_data=None)`;
         `store.finish(finished)`;
         `store.dead_letter(DeadLetter(run_id=r.run_id, request_id=r.request_id, cwd=r.cwd, selection=r.selection, env_names=tuple(n for n, _ in r.environment.env), requester=r.requester, outcome=CRASHED, reason=finished.detail, record=finished, dead_lettered_at=now))`;
         and when `store.answer(r.request_id)` is `None`, `put_answer` an `EXECUTED` result with
         outcome `CRASHED`, `run_id=r.run_id`, `key=r.key`, the tail and the detail.
      2. **Retention.** `store.prune(older_than=now - settings.retention)`.
      3. **Answered after all.** Repeat step 1: a request redelivered after its instance crashed is
         answered from that crash. **It is not run again.**
      4. **The key.** `tree = await digest.digest(Path(request.cwd))`;
         `key = TestRunKey.derive(tree, request.selection, request.environment)`.
      5. **The decision.** `decision = reuse.decide(store.attempts_as_recorded(key), now=clock.now(), fresh=request.fresh, grant=request.grant)`.
      6. **`PARKED`** → find the record of `decision.attempt` in `store.attempts(key)` (by `run_id`)
         and return `PARKED` with its `run_id`, `outcome` and `exit_code`, the `key`, and the
         decision's reason as `detail`.
      7. **`REUSE`** → take the record of `decision.attempt`. If `request.selection.collects_coverage`,
         `keeper.restore(kept=Path(record.coverage_data) if record.coverage_data else None, cwd=Path(request.cwd))`.
         Return `REUSED` with the record's `run_id`, `outcome`, `exit_code`, `output_tail`,
         `gate_reports` and `log_path`, the `key`, `recorded_at=record.finished_at`,
         `tested_tree=record.tree_before` and the decision's reason as `detail`.
      8. **`EXECUTE`**:
         1. `run_id = uuid4()`;
         2. `record = store.begin(TestRunRecord(run_id=run_id, request_id=request.request_id, key=key, attempt=0, cwd=request.cwd, selection=request.selection, environment=request.environment, requester=request.requester, instance=settings.instance, pid=self._pid, delivery_count=delivery_count, started_at=now, tree_before=tree, load_before=None, log_path=str(store.log_path(run_id))))`;
         3. `data_file = store.data_dir(run_id) / ".coverage"`;
         4. `env = child_env.build(instance_environ=self._instance_environ, request_env=request.env, run_id=run_id, coverage_file=data_file)`;
         5. `out = await executor.run(argv=request.selection.command + request.selection.argv, cwd=Path(request.cwd), env=env, bound_seconds=settings.run_bound_seconds, log_path=store.log_path(run_id), pass_fds=(hold.fd,))`;
         6. gates run only when `out.exit_code == 0`, `not out.timed_out`, `not out.unexecutable` and
            `request.selection.gates` is non-empty:
            `reports = await gates.check(cwd=Path(request.cwd), data_file=data_file, gates=request.selection.gates, env=env)`; otherwise `reports = ()`;
         7. `tree_after = await digest.digest(Path(request.cwd))`;
         8. `kept = keeper.keep(data_file=data_file, keep_dir=store.data_dir(run_id)) if request.selection.collects_coverage else None`;
            when `kept` is set, `keeper.restore(kept=kept, cwd=Path(request.cwd))`;
         9. outcome: `ABANDONED` if `abandon_current()` was called during this run; else
            `UNEXECUTABLE` if `out.unexecutable`; else
            `outcomes.classify(out.exit_code, timed_out=out.timed_out, gate_failures=sum(not r.passed for r in reports))`;
         10. `finished = dataclasses.replace(record, load_before=out.load_before).finish(outcome=outcome, exit_code=out.exit_code, timed_out=out.timed_out, tree_after=tree_after, finished_at=clock.now(), duration_seconds=out.duration_seconds, load_after=out.load_after, output_tail=out.output_tail, gate_reports=reports, detail=out.detail, coverage_data=str(kept) if kept else None)`;
             `store.finish(finished)`;
         11. if `outcome.is_dead_letter()`: `store.dead_letter(DeadLetter.from_request(request, run_id=run_id, outcome=outcome, reason=out.detail or outcome.value, record=finished, at=now))`;
         12. return `EXECUTED` with `run_id`, `key`, `outcome`, `exit_code=out.exit_code`,
             `flaky`/`flaky_runs` from `decision`, `recorded_at=finished.finished_at`,
             `tested_tree=tree`, `output_tail=out.output_tail`, `gate_reports=reports`,
             `detail=out.detail` and `log_path=finished.log_path`. Clear the abandon flag.
3. **`async def abandon_current(self) -> None`** sets the abandon flag and awaits `executor.stop()`.
4. **The interface** `src/vibey/infrastructure/test_harness/interfaces/instance_interface.py`
   declares `@runtime_checkable` `HarnessInstanceInterface` (`handle`, `abandon_current`).
5. **The fake**, new `tests/fakes/harness_instance.py`:
   `ScriptedHarnessInstance(results: Sequence[TestRunResult] = (), *, backend: str = "memory", block_until_abandoned: bool = False)`
   implements `HarnessInstanceInterface` in memory, for the service and CLI lanes that consume the
   instance (harness-T15, T23):
   - attributes `handled: list[tuple[TestRunRequest, int]]` (request, delivery count),
     `abandoned: int`, `started: asyncio.Event` (set when a `handle` begins) and
     `fail_next: BaseException | None` (raised once by the next `handle`, then cleared);
   - `handle` records the call, sets `started`, raises `fail_next` if set; when
     `block_until_abandoned`, waits until `abandon_current()` is called; after an abandon it returns
     an `EXECUTED` result with outcome `ABANDONED` (and clears the abandon); otherwise it pops the
     next scripted result and returns it with `request_id` replaced by the request's
     (`dataclasses.replace`), or, when none is left, a default `EXECUTED`/`PASSED` result
     (`exit_code=0`, a fresh `run_id`, `key="0"*64`, `tested_tree="wt1:"+"0"*64`,
     `recorded_at=datetime(2026, 1, 1, tzinfo=UTC)`, `output_tail="1 passed\n"`);
   - `abandon_current` increments `abandoned` and signals the abandon.
6. **Registry (amendment A4).** In `tests/fakes/registry.py` (lane fakes-registry), import the
   interface module and `tests.fakes.harness_instance`, append
   `FakeRegistration(port=instance_interface.HarnessInstanceInterface, build=harness_instance.ScriptedHarnessInstance, note="scripted answers, abandon and failure on cue")`
   to `REGISTRY`, and `HarnessInstanceInterface` to `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/test_harness/instance.py` and its interface module.
- New `tests/fakes/harness_instance.py`; `tests/fakes/registry.py` (with `edit_file`).
- New `tests/infrastructure/test_harness/test_instance.py`.

## Acceptance criteria
Each is a test using the real `FileTestRunStore`, `MachineLock`, `CoverageDataKeeper`,
`TestReusePolicy` and `TestOutcomePolicy` on `tmp_path`, `FakeClock` from `tests/fakes/system.py`
(lane fakes-observability), and plain in-test classes for the digest, executor and gates (their
registered fakes arrive with fakes-test-harness, which depends on this lane):
- [ ] A passing run is executed, recorded and answered; the same request again returns the stored answer.
- [ ] A second, identical request is answered `REUSED`, and the executor is not called.
- [ ] An unexecutable request (outside the root, a foreign env name, a different command) is dead-lettered without taking the lock.
- [ ] A held lock gives `SATURATED` once `start_by` has passed.
- [ ] A `running` attempt left by a dead recorder is marked `CRASHED`, dead-lettered with its log tail, and its request answered; a redelivery of that request is answered from it and not run again.
- [ ] A parked key is answered `PARKED`, and a grant runs it.
- [ ] A timeout is dead-lettered with its evidence.
- [ ] Gates run only after a clean exit, and a failing gate makes the outcome `FAILED`.
- [ ] A tree that changed during the run makes the attempt unreusable.
- [ ] Coverage data is kept, and restored to `<cwd>/.coverage` on execution and on reuse.
- [ ] The lock's fd is passed to the executor.
- [ ] `abandon_current()` gives `ABANDONED`, which is not stored as an answer.
- [ ] `uv run pytest -q -p no:cacheprovider tests/fakes` passes with the new registration.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_instance.py` (`from vibey.infrastructure.test_harness import instance as hi`;
settings from `TestHarnessSettings.from_sources(None, {"HOME": str(tmp_path), "VIBEY_HARNESS_STATE_DIR": str(tmp_path / "state"), "VIBEY_HARNESS_ROOT": str(tmp_path)}, hostname="test")`,
and requests whose `selection.command` equals `settings.command`; nothing is spawned):
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
- `test_scripted_instance_answers_abandons_and_fails_on_cue` (the new fake's behaviour)
- `test_instance_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- How requests arrive (harness-T14, T23). The CLI (harness-T15).
- The default-tier variants over the registered fakes (fakes-test-harness adds them).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T02-test-reuse-policy, harness-T04-test-run-records, harness-T06-machine-lock, harness-T08-working-tree-digest, harness-T10-file-run-store, harness-T11-run-executor, harness-T12-coverage-gates, fakes-observability (`FakeClock`).
- **Files touched:** the two new source files, `tests/fakes/harness_instance.py` (new), `tests/fakes/registry.py`, the new test file.
- **Shares a file with:** `tests/fakes/registry.py` (append only).
- **Must keep passing unchanged:** the harness-T06–T12 tests, `tests/fakes/*`, and the protected tests.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (the constructor keywords). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; in-test doubles are plain classes with real behaviour.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Never touch the real machine lock: every store, lock and state directory is under `tmp_path`.
  - No test waits longer than 5 s. POSIX only.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
