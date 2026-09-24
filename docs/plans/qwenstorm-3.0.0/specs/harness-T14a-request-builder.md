## Title
feat(test-harness): build a test-run request, and answer a repeat without spawning anything

## Why
Draft ADR-0045 §4, §7 and §8. Both requesters, the `local` one (harness-T14) and the `rabbitmq`
one (harness-T24), share two pieces, so they are classes of their own, in a module of their own:
- **the request builder** turns a command line into a `TestRunRequest` (harness-T03): the
  selection, the requester's environment as probed in the requester's own interpreter
  (harness-T09), the raw pass-through values, and the `start_by` bound (`queue_wait_seconds`);
- **the fast path** answers a repeat straight from the store (harness-T10) without spawning a
  supervisor or touching the broker. Sub-doctrine 8.e (ratified,
  `src/vibey_tools/gh/docs/doctrines.md:279-283`): "a repeat request receives the recorded result,
  while that result is still valid, instead of a second execution". It skips any fresh, granted or
  coverage-collecting request, so `.coverage` is only ever restored under the machine lock (§8), and
  it **writes nothing**.

The original lane list put both classes in `local_client.py`; they get their own module here so
that each lane is one source file, and harness-T24 imports them without importing the local client.

## Required behaviour
Create `src/vibey/infrastructure/test_harness/request_builder.py`:
1. **`TestRunRequestBuilder(*, settings: TestHarnessSettingsInterface, probe: EnvironmentProbeInterface, clock: Clock, requester: str)`**.
   `async def build(self, *, cwd: Path, argv: Sequence[str], gates: Sequence[CoverageGate], fresh: bool, grant: bool, environ: Mapping[str, str]) -> TestRunRequest`:
   - `request_id=uuid4()`, `cwd=str(cwd.resolve())`;
   - `selection=TestSelection(settings.command, tuple(argv), tuple(gates))`;
   - `environment, env = await probe.probe(environ)`;
   - `requested_at=clock.now()`, `start_by=requested_at + timedelta(seconds=settings.queue_wait_seconds)`;
   - `fresh`, `grant` and `requester` as given.
2. **`ReuseFastPath(*, store: TestRunStoreInterface, digest: WorkingTreeDigestInterface, reuse: TestReusePolicyInterface, clock: Clock, backend: str)`**.
   `async def answer(self, request: TestRunRequest) -> TestRunResult | None` returns `None` when
   `request.fresh`, `request.grant` or `request.selection.collects_coverage`. Otherwise:
   1. `tree = await digest.digest(Path(request.cwd))`;
   2. `key = TestRunKey.derive(tree, request.selection, request.environment)`;
   3. `decision = reuse.decide(store.attempts_as_recorded(key), now=clock.now(), fresh=False, grant=False)`;
   4. `REUSE` → the record of `decision.attempt` (found in `store.attempts(key)` by `run_id`) gives
      a `REUSED` result: `backend`, the record's `run_id`, `outcome`, `exit_code`, `output_tail`,
      `gate_reports` and `log_path`, the `key`, `recorded_at=record.finished_at`,
      `tested_tree=record.tree_before`, `flaky=False`, `flaky_runs=()` and the decision's reason as `detail`;
   5. `PARKED` → a `PARKED` result with the parked record's `run_id`, `outcome` and `exit_code`,
      the `key` and the reason;
   6. `EXECUTE` → `None`.

   It never calls a store write method (`put_*`, `begin`, `finish`, `dead_letter`, `answer_dead_letter`, `prune`).
3. **Interfaces**, `src/vibey/infrastructure/test_harness/interfaces/request_builder_interface.py`:
   `@runtime_checkable` `TestRunRequestBuilderInterface` (`build`) and `ReuseFastPathInterface` (`answer`).
4. **The fakes**, new `tests/fakes/harness_requests.py`, both with valid zero-argument construction:
   - `FixedRequestBuilder(*, command: tuple[str, ...] = ("uv", "run", "--no-sync", "pytest"), pass_env: tuple[str, ...] = ("VIBEY_TEST_*",), now: datetime = datetime(2026, 1, 1, tzinfo=UTC), queue_wait_seconds: int = 3600, requester: str = "memory@memory:0")`
     implements `TestRunRequestBuilderInterface` with no I/O: `values = EnvNamePatterns(pass_env).select(environ)`,
     `environment = TestEnvironment.from_values(python="memory", distributions="0" * 64, database="unset", values=values)`,
     `cwd=str(cwd)` (no `resolve()`), `requested_at=now`, `start_by=now + timedelta(seconds=queue_wait_seconds)`;
     it appends every request to `self.built`.
   - `ScriptedFastPath(answers: Mapping[tuple[str, tuple[str, ...]], TestRunResult] | None = None)`
     implements `ReuseFastPathInterface`: it appends each request to `self.asked`; returns `None`
     for a fresh, granted or coverage-collecting request (the real rule); otherwise returns the
     answer scripted for `(request.cwd, request.selection.argv)` with `request_id` replaced by the
     request's (`dataclasses.replace`), or `None`.
5. **Registry (amendment A4).** In `tests/fakes/registry.py` (lane fakes-registry), import the
   interface module and `tests.fakes.harness_requests`, append
   `FakeRegistration(port=request_builder_interface.TestRunRequestBuilderInterface, build=harness_requests.FixedRequestBuilder, note="builds requests with a fixed environment and clock")`
   and `FakeRegistration(port=request_builder_interface.ReuseFastPathInterface, build=harness_requests.ScriptedFastPath, note="scripted repeat answers")`
   to `REGISTRY`, and both interfaces to `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/test_harness/request_builder.py` and its interface module.
- New `tests/fakes/harness_requests.py`; `tests/fakes/registry.py` (with `edit_file`).
- New `tests/infrastructure/test_harness/test_request_builder.py`.

## Acceptance criteria
- [ ] The builder fills every field; `start_by` follows `queue_wait_seconds`; `cwd` is resolved.
- [ ] The fast path answers `REUSED` and `PARKED` without writing anything (the store directory's file listing is identical before and after), and returns `None` for fresh, granted and coverage-collecting requests and for an `EXECUTE` decision.
- [ ] `uv run pytest -q -p no:cacheprovider tests/fakes` passes with both registrations.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_request_builder.py`
(`from vibey.infrastructure.test_harness import request_builder as rb`). The builder uses the
real `EnvironmentProbe(pass_env=..., database_env="", distributions=lambda: [])` (harness-T09) and
`FakeClock` (`tests/fakes/system.py`); the fast path uses the real `FileTestRunStore` on
`tmp_path`, the real `TestReusePolicy`, and a plain in-test digest class returning a fixed tree:
- `test_builder_fills_every_field`
- `test_fast_path_reuses_without_writing`
- `test_fast_path_answers_parked`
- `test_fast_path_skips_fresh_granted_and_coverage` (parametrized)
- `test_fast_path_executes_when_nothing_is_recorded`
- `test_fixed_builder_and_scripted_fast_path_behave` (the two fakes)
- `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Spawning a supervisor and waiting (harness-T14). The AMQP requester (harness-T24).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T02-test-reuse-policy, harness-T04-test-run-records, harness-T08-working-tree-digest, harness-T09-environment-probe, harness-T10-file-run-store, fakes-observability (`FakeClock`), fakes-registry.
- **Files touched:** the two new source files, `tests/fakes/harness_requests.py` (new), `tests/fakes/registry.py`, the new test file.
- **Shares a file with:** `tests/fakes/registry.py` (append only).
- **Must keep passing unchanged:** the harness-T02–T10 tests, `tests/fakes/*`, and the protected tests.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam. Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out): `database_env=""` keeps the probe off the network.
  - Never touch the real machine state: every store is under `tmp_path`.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
