## Title
feat(test-harness): the local backend's requester, with a detached instance per request

## Why
Draft ADR-0045 §3 and §11. The operator requires that a machine without RabbitMQ can still commit
and push. With the `local` backend, the requester writes its request to the store and spawns a
**detached** supervisor (`python -m vibey test-harness execute`, harness-T15) that is the instance
for that request; then it waits for the answer.

The supervisor is detached for a concrete reason: qwenloop's shell kills a command after 120 s
(`src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py:59-64`), and a full suite does not
fit in that. A requester's death must never cancel or orphan an unrecorded run: the run finishes,
and the next identical request is answered from its record (8.e, ratified,
`src/vibey_tools/gh/docs/doctrines.md:279-283`). A requester that stops waiting says so and exits
75, which is neither a pass nor a failure (10.f).

## Required behaviour
Create `src/vibey/infrastructure/test_harness/local_client.py`:
1. **`SupervisorSpawner(*, argv_prefix: tuple[str, ...])`**.
   `async def spawn(self, *, request_file: Path, config_path: Path | None, log_path: Path, env: Mapping[str, str], cwd: Path) -> int`:
   - argv is `argv_prefix + (str(request_file),)`, plus `("--config", str(config_path))` when set;
   - open `log_path` for appending with mode `0o600` (`os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)`);
   - `proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=fd, stderr=subprocess.STDOUT, env=dict(env), cwd=str(cwd), start_new_session=True, close_fds=True)`
     (with a `# nosec B603` comment: the argv is this interpreter plus a fixed module, never a shell);
     close the parent's `fd`; keep `proc` in `self._children` so it is not collected while the
     requester waits; return `proc.pid`. It **never waits** on the process.
2. **`LocalHarnessClient(*, settings: TestHarnessSettingsInterface, store: TestRunStoreInterface, builder: TestRunRequestBuilderInterface, fast_path: ReuseFastPathInterface, spawner: SupervisorSpawnerInterface, lock: MachineLockInterface, clock: Clock, environ: Mapping[str, str], config_path: Path | None = None, poll_seconds: float = 0.5)`**
   (`TestRunRequestBuilderInterface` and `ReuseFastPathInterface` from harness-T14a):
   - `async def request(self, *, cwd: Path, argv: Sequence[str], gates: Sequence[CoverageGate], fresh: bool, grant: bool = False, environ: Mapping[str, str]) -> TestRunResult`:
     `request = await builder.build(cwd=cwd, argv=argv, gates=gates, fresh=fresh, grant=grant, environ=environ)`;
     return `await fast_path.answer(request)` when that is not `None`, else `await self.submit(request)`.
   - `async def submit(self, request: TestRunRequest) -> TestRunResult`:
     1. `store.ensure()`;
     2. `path = store.put_request(request)`;
     3. `await spawner.spawn(request_file=path, config_path=self._config_path, log_path=store.supervisor_log_path(request.request_id), env=self._environ, cwd=settings.state_dir)`;
     4. poll `store.answer(request.request_id)` every `poll_seconds` and return it when it appears;
     5. once `settings.wait_seconds` have passed (`time.monotonic()`), return `STILL_RUNNING`
        (`backend="local"`, `outcome=None`, the rest empty) with the detail
        `"the run is still going; run the same command again to receive its result"`, plus
        `f" (the machine's test lock is held by pid {pid} since {since})"` when `lock.holder()` names one.
3. **Interfaces**, `src/vibey/infrastructure/test_harness/interfaces/local_client_interface.py`:
   `@runtime_checkable` `SupervisorSpawnerInterface` (`spawn`) and `HarnessClientInterface`
   (`request`, `submit`). harness-T24's AMQP requester implements `HarnessClientInterface` too.
4. **The fake**, new `tests/fakes/harness_client.py`:
   `ScriptedHarnessClient(results: Sequence[TestRunResult] = (), *, backend: str = "memory")`
   implements `HarnessClientInterface` in memory, for the CLI and plugin lanes (harness-T15b onwards):
   - `requests: list[dict[str, object]]` records each `request(...)`'s keyword arguments (with
     `argv` and `gates` as tuples and `environ` as a dict); `submitted: list[TestRunRequest]` records `submit`;
     `fail_next: BaseException | None` is raised once by the next call, then cleared;
   - each call returns the next scripted result with `request_id` replaced (a fresh `uuid4()` for
     `request`, the request's id for `submit`), or, when none is left, a default `EXECUTED`/`PASSED`
     result (`exit_code=0`, a fresh `run_id`, `key="0"*64`, `tested_tree="wt1:"+"0"*64`,
     `recorded_at=datetime(2026, 1, 1, tzinfo=UTC)`, `output_tail="1 passed\n"`, `backend`).
5. **Registry (amendment A4).** In `tests/fakes/registry.py` (lane fakes-registry), import the
   interface module and `tests.fakes.harness_client`, then:
   - append `FakeRegistration(port=local_client_interface.HarnessClientInterface, build=harness_client.ScriptedHarnessClient, note="scripted answers, recorded calls, failure on cue")` to `REGISTRY`;
   - append `SupervisorSpawnerInterface` and `HarnessClientInterface` to `DRIVER_SEAMS`;
   - add `"SupervisorSpawnerInterface": "fakes-test-harness"` to `PENDING` (fakes-test-harness
     registers `RecordingSupervisorSpawner`).

## Where to change
- New `src/vibey/infrastructure/test_harness/local_client.py` and its interface module.
- New `tests/fakes/harness_client.py`; `tests/fakes/registry.py` (with `edit_file`).
- New `tests/infrastructure/test_harness/test_local_client.py`.

## Acceptance criteria
- [ ] A fast-path answer is returned without writing a request or spawning.
- [ ] `request` writes the request file, spawns once with the expected argv (including `--config` when set), and returns the answer the in-test supervisor writes.
- [ ] With no answer, `STILL_RUNNING` comes back after `wait_seconds`, naming the holder when there is one.
- [ ] The real `SupervisorSpawner` starts a detached process that outlives the calling coroutine: it writes a marker, and the test waits for it (at most 3 s).
- [ ] `uv run pytest -q -p no:cacheprovider tests/fakes` passes with the new registration.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_local_client.py`
(`from vibey.infrastructure.test_harness import local_client as lc`). Use the registered fakes
`FixedRequestBuilder` and `ScriptedFastPath` (`tests/fakes/harness_requests.py`, harness-T14a) and
`FakeClock`; the real `FileTestRunStore` and `MachineLock` on `tmp_path`; settings with
`VIBEY_HARNESS_STATE_DIR` under `tmp_path`:
- `test_request_returns_the_fast_path_answer_without_spawning`
- `test_request_spawns_and_returns_the_written_answer` (a plain in-test spawner that reads the request with `store.take_request(request_file)`, writes an answer with `store.put_answer`, records its arguments and returns 4242)
- `test_still_running_after_the_wait_names_the_holder` (settings with `VIBEY_HARNESS_WAIT_SECONDS=1`, `poll_seconds=0.05`; the lock held by a second `MachineLock.acquire` in the test)
- `test_still_running_without_a_holder`
- `test_spawner_detaches` (`argv_prefix=(sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[1] + '.seen').write_text('x')")`)
- `test_spawner_adds_config` (a prefix that writes `repr(sys.argv[1:])` beside the request file)
- `test_scripted_client_records_and_answers`
- `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The supervisor command itself (harness-T15). The AMQP requester (harness-T24).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T06-machine-lock, harness-T10-file-run-store, harness-T14a-request-builder, fakes-registry.
- **Files touched:** the two new source files, `tests/fakes/harness_client.py` (new), `tests/fakes/registry.py`, the new test file.
- **Shares a file with:** `tests/fakes/registry.py` (append only).
- **Must keep passing unchanged:** the harness-T06–T14a tests, `tests/fakes/*`, and the protected tests.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (constructor keywords). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; in-test doubles are plain classes.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out); children of `sys.executable` are inside.
  - Never touch the real machine lock: state directories, locks and stores are under `tmp_path`, and every child environment drops `VIBEY_HARNESS_RUN` and `VIBEY_HARNESS_ROUTE`.
  - No test waits longer than 5 s. POSIX only.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
