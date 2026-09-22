## Title
test(fakes): the test harness's seams — lock, store, tree digest, environment probe, executor, gates, spawner — get in-memory fakes, registered like every other port

## Why
The test harness (draft ADR-0045, lanes T01–T28) declares its own seams under
`src/vibey/infrastructure/test_harness/interfaces/` (ADR-0045 §13). `HarnessInstance` (T13) is
built from:
- `MachineLockInterface` (T06), `TestRunStoreInterface` (T10), `WorkingTreeDigestInterface` (T08);
- `TestRunExecutorInterface` (T11), `CoverageGatesInterface`, `CoverageDataKeeperInterface` and
  `ChildEnvironmentInterface` (T11, T12);
- `TestReusePolicyInterface` (T02) and `TestOutcomePolicyInterface` (T01), which are pure;
- `Clock`.

`LocalHarnessClient` (T14) adds `EnvironmentProbeInterface` (T09) and `SupervisorSpawner`.

The T-lanes test these adapters against `tmp_path`, a real `flock`, real git and real child
processes. That is right for the adapters themselves. But every *consumer* test (the
instance, the client, the CLI and the pytest plugin) then pays for real I/O. The draft
ADR-0045 amendment (A2, A7) puts the harness under the same standard as the rest of vibey:
every seam has a registered in-memory fake. `DRIVER_SEAMS` in `tests/fakes/registry.py` lists
them from this lane on.

## Required behaviour
Precondition: T13 and T14 have landed. Use the interface names exactly as they landed, and
list them in the commit body.

1. **`tests/fakes/harness_fakes.py`**:
   - `InMemoryMachineLock` (`MachineLockInterface`):
     - one process-wide `asyncio.Lock`-like state per instance;
     - `acquire(timeout_seconds=..., holder=...)` returns an `InMemoryHold`
       (`MachineLockHoldInterface`: `fd` is `-1`, and `release()` frees the lock), or `None`
       after the timeout;
     - `holder()` returns the holder mapping;
     - `seize(holder)` simulates another process holding the lock.
   - `ScriptedTreeDigest` (`WorkingTreeDigestInterface`) returns a scripted sequence of
     digests per `cwd` (the last one repeats), so a test can simulate "the tree changed during
     the run". It records its calls.
   - `ScriptedEnvironmentProbe` (`EnvironmentProbeInterface`) returns a fixed
     `TestEnvironment` and selects `pass_env` values with the real `EnvNamePatterns`.
   - `InMemoryTestRunStore` (`TestRunStoreInterface`) implements every public method T10
     declares over dicts. It keeps T10's rules:
     - an attempt number is claimed once;
     - a terminal attempt is never rewritten;
     - a dead letter is never rewritten, and an answer to it is a separate entry;
     - `prune` never removes an unanswered dead letter.
     It stores values, not paths, and returns them from the path-returning methods as
     `PurePosixPath("memory://…")`.
   - `ScriptedTestRunExecutor` (`TestRunExecutorInterface`):
     - scripted by argv: exit code, `timed_out`, output bytes, and "raise at spawn";
     - it records the exact child environment and argv it was given;
     - `tail(path)` returns the scripted output's last bytes.
   - `ScriptedCoverageGates`, `InMemoryCoverageDataKeeper` and `RecordingSupervisorSpawner`,
     the last of which returns a fake pid and records the argv, env and cwd.
2. **Registry.** Register every fake above for its interface, and add each interface to
   `DRIVER_SEAMS`. Keep the pure policies (`TestReusePolicyInterface`,
   `TestOutcomePolicyInterface`, the codecs) out: they are `PURE_POLICY` and not seams.
3. **Switch the consumer tests.** In `tests/infrastructure/test_harness/test_instance.py` (T13)
   and `test_local_client.py` (T14), add a default-tier variant for every case that does not
   test a real adapter's I/O, using the fakes. That covers reuse, parking, flaky detection,
   the crash sweep, the tree changing during a run, saturation and coalescing. Keep the
   existing real-adapter cases. Mark none of them `integration`, because `tmp_path`, `flock`
   and `sys.executable` children are local. Only move the cases that were slow, over 1 s, to
   the fakes.
4. **The not-a-stub check** (`tests/fakes/test_port_parity.py`) passes for every new fake.

## Where to change
- New `tests/fakes/harness_fakes.py`, `tests/fakes/test_fake_test_harness.py`.
- `tests/fakes/registry.py`, `tests/infrastructure/test_harness/test_instance.py`, `test_local_client.py` (appended variants).

## Acceptance criteria
- [ ] Every harness interface consumed by `HarnessInstance` or `LocalHarnessClient`, except the pure policies, is in `DRIVER_SEAMS` with a registered fake.
- [ ] The instance's crash-sweep case runs on `InMemoryTestRunStore` and `InMemoryMachineLock` in under 100 ms.
- [ ] The T-lane tests still pass unchanged.

## Tests to write first (TDD)
`tests/fakes/test_fake_test_harness.py`:
- `test_lock_times_out_while_seized_and_reports_the_holder`
- `test_store_claims_an_attempt_once_and_never_rewrites_a_terminal_one`
- `test_store_prune_keeps_unanswered_dead_letters`
- `test_tree_digest_scripts_a_change_during_the_run`
- `test_executor_records_the_child_environment`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The AMQP side. `vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (R04) is already the
  in-memory bus fake for T22–T24. Register it for the AMQP client interface in this lane if
  that interface is importable from `src/vibey`; otherwise note it in the commit body.
- Production code, and the T-lanes' own tests.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry`, `harness-T13-harness-instance`, `harness-T14-local-client`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** every T-lane test, and the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).
  - The T-lanes' standing constraints apply too:
    - import modules, not `Test*` names, in test files;
    - point `VIBEY_HARNESS_STATE_DIR` at `tmp_path` in every test that builds settings, a
      lock or a store, and strip `VIBEY_HARNESS_RUN` and `VIBEY_HARNESS_ROUTE` from every
      child environment, so that no test touches the real machine lock;
    - use hermetic commands (`sys.executable`), and no test waits longer than 5 s.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
