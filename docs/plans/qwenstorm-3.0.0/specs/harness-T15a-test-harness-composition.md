## Title
feat(bootstrap): compose the test harness in the one composition root

## Why
CLAUDE.md: `bootstrap.py` is "the sole composition root". Draft ADR-0045 §13 puts the harness's
composition there (`build_test_harness(config, environ)`), so the CLI commands (harness-T15b,
T15, T16), the pytest plugin's queue mode (harness-T17) and, later, the service (harness-T25b)
get every piece from one place and wire nothing themselves.

This lane builds the `local` backend only. `rabbitmq` fails with `TestHarnessNotConfigured`
(harness-T05, `src/vibey/infrastructure/test_harness/settings.py`) naming the remedy, until
harness-T25b composes it. The composition is a declared seam — the CLI and the plugin receive it
through a factory — so it gets a registered in-memory fake in this lane (amendment A4), built over
the harness fakes that lane fakes-test-harness registered.

## Required behaviour
1. **`class TestHarnessComposition`** in `src/vibey/bootstrap.py` (add new code only; place it
   after `class SystemClock` at `:174-176`), built with
   `(*, settings: TestHarnessSettings, environ: Mapping[str, str], clock: Clock, config_path: Path | None = None)`.
   Each piece is built lazily and cached on first use:
   - properties `settings`, `clock`, `config_path`, `requester`
     (`f"{getpass.getuser()}@{settings.instance}:{os.getpid()}"`) and `announcement` (`None` in this lane);
   - `store()`: `FileTestRunStore(settings.state_dir, messages=TestHarnessCodec(), records=TestRunRecordCodec(TestHarnessCodec()))`, with `ensure()` called once;
   - `lock()`: `MachineLock(settings.lock_path)`;
   - `digest()`: `WorkingTreeDigest(exclude=settings.tree_exclude)`;
   - `probe()`: `EnvironmentProbe(pass_env=settings.pass_env, database_env=settings.database_env)`;
   - `reuse()`: `TestReusePolicy(settings.pass_ttl, settings.fail_ttl)`;
   - `builder()`: `TestRunRequestBuilder(settings=settings, probe=self.probe(), clock=clock, requester=self.requester)`;
   - `fast_path(backend: str = "local")`: `ReuseFastPath(store=self.store(), digest=self.digest(), reuse=self.reuse(), clock=clock, backend=backend)`;
   - `instance(backend: str = "local")`: `HarnessInstance(settings=settings, store=self.store(), lock=self.lock(), digest=self.digest(), executor=TestRunExecutor(reaper=ProcessReaper(), tail_bytes=settings.output_tail_bytes), child_env=ChildEnvironment(settings.base_env), gates=CoverageGates(coverage_command=settings.coverage_command), keeper=CoverageDataKeeper(), reuse=self.reuse(), outcomes=TestOutcomePolicy(), clock=clock, instance_environ=environ, backend=backend, pid=os.getpid())`;
   - `async def client(self) -> HarnessClientInterface`:
     - backend `local` or `auto` → `LocalHarnessClient(settings=..., store=self.store(), builder=self.builder(), fast_path=self.fast_path("local"), spawner=SupervisorSpawner(argv_prefix=(sys.executable, "-m", "vibey", "test-harness", "execute", "--request-file")), lock=self.lock(), clock=clock, environ=environ, config_path=config_path)`;
     - backend `rabbitmq` → raise `TestHarnessNotConfigured("the rabbitmq test-harness backend is not available in this build; export VIBEY_HARNESS_BACKEND=local")`.
2. **`def build_test_harness(config: VibeyConfig | None, environ: Mapping[str, str], *, config_path: Path | None = None) -> TestHarnessComposition`**,
   a module function beside the other `build_*` functions, returning
   `TestHarnessComposition(settings=TestHarnessSettings.from_sources(config, environ), environ=environ, clock=SystemClock(), config_path=config_path)`.
3. **`TestHarnessCompositionInterface`** in `src/vibey/bootstrap_interface.py`
   (`@runtime_checkable`, after `AppResourcesInterface`): every property and method above, with
   return types named by their interfaces (`TestRunStoreInterface`, `MachineLockInterface`,
   `WorkingTreeDigestInterface`, `EnvironmentProbeInterface`, `TestReusePolicyInterface`,
   `TestRunRequestBuilderInterface`, `ReuseFastPathInterface`, `HarnessInstanceInterface`,
   `HarnessClientInterface`, `TestHarnessSettingsInterface`, `Clock`).
4. **The fake**, new `tests/fakes/harness_composition.py`:
   `InMemoryTestHarnessComposition(*, settings=None, clock=None, store=None, lock=None, instance=None, client=None, announcement: str | None = None, fail_client: BaseException | None = None)`
   implements `TestHarnessCompositionInterface` over the registered fakes, with no I/O:
   - `settings` defaults to `TestHarnessSettings.from_sources(None, {"HOME": "/memory", "VIBEY_HARNESS_STATE_DIR": "/memory/test-harness"}, hostname="memory")` (pure resolution, nothing is opened);
   - `clock` defaults to `FakeClock()` (`tests/fakes/system.py`);
   - `store()`, `lock()`, `digest()` and `probe()` return one zero-argument `InMemoryTestRunStore()`,
     `InMemoryMachineLock()`, `ScriptedTreeDigest()` and `ScriptedEnvironmentProbe()` each, from the
     module lane fakes-test-harness created (`grep -rln "class InMemoryTestRunStore" tests/fakes`
     finds it), unless a store or lock was given;
   - `reuse()` is the real `TestReusePolicy(settings.pass_ttl, settings.fail_ttl)` (a pure policy);
   - `builder()` is `FixedRequestBuilder(command=settings.command)` and `fast_path(backend)` a
     `ScriptedFastPath()` (`tests/fakes/harness_requests.py`);
   - `instance(backend)` returns the given instance or one `ScriptedHarnessInstance()` (`tests/fakes/harness_instance.py`);
   - `async client()` increments `self.client_calls`, raises `fail_client` when set, and returns
     the given client or one `ScriptedHarnessClient()` (`tests/fakes/harness_client.py`);
   - `requester` is `"memory@memory:0"`, `config_path` is `None`, `announcement` as given.
5. **Registry (amendment A4).** In `tests/fakes/registry.py`, import `vibey.bootstrap_interface`
   and `tests.fakes.harness_composition`, append
   `FakeRegistration(port=bootstrap_interface.TestHarnessCompositionInterface, build=harness_composition.InMemoryTestHarnessComposition, note="the harness composition over the in-memory harness fakes")`
   to `REGISTRY`, and the interface to `DRIVER_SEAMS`.

## Where to change
- `src/vibey/bootstrap.py` (new class and function only; 962 lines — use `edit_file`, never `write_file`)
  and `src/vibey/bootstrap_interface.py` (one new Protocol).
- New `tests/fakes/harness_composition.py`; `tests/fakes/registry.py`.
- `tests/test_bootstrap.py`: add any new import to the import block at the top (`:2-32`; `from vibey import bootstrap` is already at `:13`), then append the tests.

## Acceptance criteria
- [ ] `build_test_harness(None, {"HOME": str(tmp_path), "VIBEY_HARNESS_STATE_DIR": str(tmp_path / "state")})` composes a `LocalHarnessClient` whose spawner's argv prefix is `(sys.executable, "-m", "vibey", "test-harness", "execute", "--request-file")`, and the store directories exist.
- [ ] With `VIBEY_HARNESS_BACKEND=rabbitmq` (and no `VIBEY_BUS_AMQP_URL`), `client()` raises `TestHarnessNotConfigured` whose message contains `VIBEY_HARNESS_BACKEND=local`.
- [ ] Each piece is built once per composition.
- [ ] `uv run pytest -q -p no:cacheprovider tests/fakes` passes: the fake matches the interface's signatures and is not a stub.
- [ ] 100% coverage of `src/vibey/infrastructure/` and `src/vibey/cli/` is unchanged (bootstrap sits outside the per-layer floors; its new code is still fully exercised by the tests below).

## Tests to write first (TDD)
Appended to `tests/test_bootstrap.py`:
- `test_build_test_harness_composes_a_local_client`
- `test_rabbitmq_test_harness_backend_is_not_configured_in_this_build`
- `test_test_harness_pieces_are_built_once`
- `test_test_harness_instance_is_wired_with_the_settings` (the instance's backend and pid)
- `test_test_harness_composition_satisfies_its_interface` (the real one and the in-memory fake)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/fakes tests/meta tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Any CLI command (harness-T15b, T15c, T15, T16). The AMQP backend (harness-T25b).
- Existing composition code in `bootstrap.py` (the ADR-0044 chain edits it).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T13-harness-instance, harness-T14-local-client, fakes-test-harness (the in-memory store, lock, digest and probe the fake composition is built over).
- **Files touched:** `src/vibey/bootstrap.py`, `src/vibey/bootstrap_interface.py`, `tests/fakes/harness_composition.py` (new), `tests/fakes/registry.py`, `tests/test_bootstrap.py`.
- **Shares a file with:** `bootstrap.py` and `bootstrap_interface.py` (rmq-r02, rmq-r17, rmq-r27, rmq-r28 edit other code; this lane only adds). `tests/fakes/registry.py` (append only).
- **Must keep passing unchanged:** every existing test in `tests/test_bootstrap.py`, `tests/cli/*`, `tests/fakes/*`, and the protected tests.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names (`bootstrap.TestHarnessComposition`).
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; environments are passed as dicts.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Never touch the real machine lock: every composition a test builds points `HOME` and `VIBEY_HARNESS_STATE_DIR` under `tmp_path`.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
