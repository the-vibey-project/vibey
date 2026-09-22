<!-- split of #367: child 2 of 2; audit: issue-audit/updates/367.md -->

## Title
refactor(engines): the engine process launcher, with injected spawner and executable-resolver seams

## Why
ADR-0044 §14's code table (`docs/architecture/decisions/0044-job-queue-port-and-loop-services.md:541`) names `infrastructure/engines/process_launcher.py` (`EngineProcessLauncher`), extracted from `LoopProcessAdapter` with no behaviour change; lane T26 of draft ADR-0045 (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/test-harness-lanes.md:3273`) already reads its `environment()`. Child lane 1 (`split-367-1-run-dir`) extracted the run-directory classes. This lane extracts the other half: the engine environment (`_engine_environment`, `src/vibey/infrastructure/engines/loop_process_adapter.py:160-164` at integration `4317cff6`), the spawn (`_spawn`, `:166-192`) and the binary resolution in `start` (`:357-359`).

The original R20 kept module-attribute patching (`monkeypatch.setattr(module.asyncio, "create_subprocess_exec", ...)`) as the test seam. Sub-doctrine 9.b (`src/vibey_tools/gh/docs/doctrines.md:349`: "Substitution happens at the declared seam, never by patching an import") forbids that for new tests, so the launcher takes two **injected seams**, `ProcessSpawnerInterface` and `ExecutableResolverInterface`. Their production defaults call `asyncio.create_subprocess_exec` and `shutil.which` **at call time**, through the module attribute, which is why the unedited legacy tests that still patch those globals (`tests/infrastructure/engines/test_loop_process_adapter.py:1565-1566`, `:1607-1608`, `:1679`, `:1922`) keep passing.

A launcher that imported `isolate_python_env` from `loop_process_adapter.py` (`:87-111`) while the adapter imports the launcher would be an import cycle. So `isolate_python_env` moves into `src/vibey/infrastructure/process/python_env.py`, whose module docstring already names it (`python_env.py:4-5`), and the adapter re-exports it so `src/vibey/infrastructure/build/gate_runner.py:45` and `tests/infrastructure/process/test_python_env.py:12` keep working unedited. Sub-doctrine 10.e (`doctrines.md:417`) forbids a second copy of any of this.

Line numbers above are at `4317cff6`, before child 1. Child 1 removed three import lines near the top of the adapter and added one, so every anchor in the adapter has moved up by about two lines: **find each one with `grep -n`** (commands below), never by number.

## Required behaviour
1. **`isolate_python_env` moves, unchanged.** Its whole definition (signature, docstring and body; `loop_process_adapter.py:87-111` at `4317cff6`) is cut from `loop_process_adapter.py` and appended to `src/vibey/infrastructure/process/python_env.py`, after `class OrchestratorPythonEnv`. On the line after its signature's last line (`) -> dict[str, str]:`), before the existing docstring, add this comment, which is the written reason 9.b asks of a module function:
   `# A module function because callers import it by this name (build/gate_runner.py, the adapter's re-export); it moved here unchanged from loop_process_adapter.py so the launcher and the adapter can share it without an import cycle.`
   `python_env.py` already imports `os` and `Mapping`.
2. **`loop_process_adapter.py` re-exports it** with exactly
   `from vibey.infrastructure.process.python_env import isolate_python_env as isolate_python_env`
   (the explicit re-export form that mypy `--strict`'s no-implicit-reexport requires). `from vibey.infrastructure.engines.loop_process_adapter import isolate_python_env` keeps working, and returns the same function object as `from vibey.infrastructure.process.python_env import isolate_python_env`.
3. **New `src/vibey/infrastructure/engines/process_launcher.py`** holds three classes, `__all__ = ["AsyncioProcessSpawner", "EngineProcessLauncher", "ShutilExecutableResolver"]`:
   - `class AsyncioProcessSpawner` with
     `async def spawn(self, argv: Sequence[str], *, env: Mapping[str, str] | None, stdout: int | TextIO, stderr: int | TextIO, cwd: Path | None, start_new_session: bool) -> asyncio.subprocess.Process`,
     whose body is exactly
     `return await asyncio.create_subprocess_exec(*argv, stdout=stdout, stderr=stderr, cwd=cwd, env=env, start_new_session=start_new_session)`.
     The module does `import asyncio` and calls `asyncio.create_subprocess_exec` through the attribute at call time. Never write `from asyncio import create_subprocess_exec`.
   - `class ShutilExecutableResolver` with `def which(self, name: str) -> str | None: return shutil.which(name)`. The module does `import shutil`; never `from shutil import which`.
   - `class EngineProcessLauncher`, built as
     `EngineProcessLauncher(descriptor: EngineDescriptor, *, env_overlay: Mapping[str, str], python_env: OrchestratorPythonEnvInterface, spawner: ProcessSpawnerInterface, resolver: ExecutableResolverInterface)`.
     It keeps all five, exposes `descriptor` as a read-only property, and has three methods:
     - `environment(self) -> dict[str, str]`: the body of `_engine_environment` today:
       `environment = isolate_python_env(os.environ, venv_prefixes=self._python_env.venv_prefixes())`, then `environment.update(self._env_overlay)`, then `return environment`. It reads `os.environ` at call time.
     - `async def spawn(self, *argv: str, env: Mapping[str, str] | None = None, stdout: int | TextIO, stderr: int | TextIO, cwd: Path | None = None, start_new_session: bool = False) -> asyncio.subprocess.Process`: the body of `_spawn` today, calling the injected spawner:
       ```python
       merged: dict[str, str] | None = None
       if env is not None or self._env_overlay:
           merged = {**(os.environ if env is None else env), **self._env_overlay}
       return await self._spawner.spawn(
           argv,
           env=merged,
           stdout=stdout,
           stderr=stderr,
           cwd=cwd,
           start_new_session=start_new_session,
       )
       ```
       Keep `_spawn`'s docstring on it.
     - `resolve(self, argv: tuple[str, ...]) -> tuple[str, ...]`: the lines in `start` today:
       `binary_path = self._resolver.which(argv[0])`; return `argv` unchanged when it is `None`, else `(binary_path, *argv[1:])`.
4. **New `src/vibey/infrastructure/engines/interfaces/process_launcher_interface.py`** declares three `@runtime_checkable` Protocols with exactly these members:
   - `ProcessSpawnerInterface`: `async def spawn(self, argv: Sequence[str], *, env: Mapping[str, str] | None, stdout: int | TextIO, stderr: int | TextIO, cwd: Path | None, start_new_session: bool) -> asyncio.subprocess.Process`.
   - `ExecutableResolverInterface`: `def which(self, name: str) -> str | None`. (This is the same shape as `ExecutableLocator.which` in lane `fakes-process-executor`, so one fake can serve both.)
   - `EngineProcessLauncherInterface`: the `descriptor` property, `environment()`, `spawn(...)` and `resolve(argv)` with the signatures in behaviour 3.
5. **`LoopProcessAdapter` gains two fields and one private field**, and delegates:
   - After the `python_env` field (and its docstring) add:
     ```python
     spawner: ProcessSpawnerInterface = field(
         default_factory=AsyncioProcessSpawner, compare=False, repr=False
     )
     """Starts every engine and probe process. A test passes a fake here instead of
     patching `asyncio.create_subprocess_exec` (sub-doctrine 9.b)."""
     resolver: ExecutableResolverInterface = field(
         default_factory=ShutilExecutableResolver, compare=False, repr=False
     )
     """Resolves the engine binary `start` launches. A test passes a fake here instead
     of patching `shutil.which`."""
     ```
   - After `_reaper: ProcessReaperInterface = field(init=False, compare=False, repr=False)` add
     `_launcher: EngineProcessLauncherInterface = field(init=False, compare=False, repr=False)`.
   - At the end of `__post_init__` add
     ```python
     object.__setattr__(
         self,
         "_launcher",
         EngineProcessLauncher(
             self.descriptor,
             env_overlay=self.env_overlay,
             python_env=self.python_env,
             spawner=self.spawner,
             resolver=self.resolver,
         ),
     )
     ```
   - `_engine_environment` keeps its name, signature and docstring; its body becomes `return self._launcher.environment()`.
   - `_spawn` keeps its name, signature and docstring; its body becomes
     `return await self._launcher.spawn(*argv, env=env, stdout=stdout, stderr=stderr, cwd=cwd, start_new_session=start_new_session)`.
     `_spawn`, `_communicate` and `_engine_environment` stay adapter methods because `tests/infrastructure/engines/test_loop_process_adapter.py:680` and `:696` call them.
   - In `start`, the three lines
     ```python
     binary_path = shutil.which(argv[0])
     if binary_path is not None:
         argv = (binary_path, *argv[1:])
     ```
     become `argv = self._launcher.resolve(argv)`. The comment above them stays.
   - `help_text` and `preflight` keep their own `shutil.which` calls (`:228`, `:269` at `4317cff6`); they are not in this lane.
   - `loop_process_adapter.py` keeps `import asyncio`, `import os` and `import shutil` (still used), so the legacy tests' `module.asyncio` and `module.shutil` still resolve.
6. With the defaults, nothing observable changes: the same argv, environment, keyword arguments to `asyncio.create_subprocess_exec`, log events and timeouts. `LoopProcessAdapter(descriptor=CLAUDELOOP) == LoopProcessAdapter(descriptor=CLAUDELOOP)` still holds (every new field is `compare=False`).
7. **In-memory fakes** in `tests/fakes/process.py`, each with real behaviour for every method:
   - `@dataclass(frozen=True, slots=True) class SpawnCall` with `argv: tuple[str, ...]`, `env: dict[str, str] | None`, `stdout: object`, `stderr: object`, `cwd: Path | None`, `start_new_session: bool`.
   - `class FakeProcess(pid: int = 4242, *, exit_code: int = 0, stdout: bytes = b"", stderr: bytes = b"")` with attributes `pid` and `returncode` (starts `None`); `async def wait(self) -> int` sets `returncode` to `exit_code` when it is still `None` and returns it; `async def communicate(self) -> tuple[bytes, bytes]` awaits `wait()` and returns `(stdout, stderr)`; `terminate()` sets `returncode = -15` and `kill()` sets `returncode = -9`, each only while `returncode` is `None`.
   - `class FakeProcessSpawner(process: FakeProcess | None = None)` (`ProcessSpawnerInterface`): keeps `self.process` (a new `FakeProcess()` when none is given) and `self.calls: list[SpawnCall]`; `spawn(...)` (same parameter names and kinds as the interface) appends `SpawnCall(tuple(argv), None if env is None else dict(env), stdout, stderr, cwd, start_new_session)` and returns `self.process`.
   - `class FakeExecutableResolver(paths: Mapping[str, str] | None = None)` (`ExecutableResolverInterface`): `which(name)` appends `name` to `self.lookups` and returns `paths.get(name)`.

## Where to change
Step 0: `grep -n "def isolate_python_env\|def _engine_environment\|async def _spawn\|binary_path = shutil.which(argv\[0\])\|_reaper: ProcessReaperInterface\|python_env: OrchestratorPythonEnvInterface\|def __post_init__" src/vibey/infrastructure/engines/loop_process_adapter.py` gives today's line numbers. Child 1 (`split-367-1-run-dir`) must have landed: `test -f src/vibey/infrastructure/engines/run_dir.py` must succeed; if it does not, stop and report "blocked: split-367-1-run-dir has not landed".

This lane spans four source files, not one, because moving `isolate_python_env` is what breaks the import cycle (launcher → adapter → launcher):
- `src/vibey/infrastructure/process/python_env.py` (37 lines): append the function (behaviour 1). Use `edit_file` or append; do not rewrite the class above it.
- **New** `src/vibey/infrastructure/engines/process_launcher.py` (behaviour 3). Imports: `asyncio`, `os`, `shutil`, `from collections.abc import Mapping, Sequence`, `from pathlib import Path`, `from typing import TextIO`, `from vibey.domain.engine import EngineDescriptor`, `from vibey.infrastructure.engines.interfaces.process_launcher_interface import ExecutableResolverInterface, ProcessSpawnerInterface`, `from vibey.infrastructure.process.interfaces import OrchestratorPythonEnvInterface`, `from vibey.infrastructure.process.python_env import isolate_python_env`. No Protocol is declared in this file (`tests/application/test_interfaces_convention.py:130-146` refuses one outside an `interfaces` package).
- **New** `src/vibey/infrastructure/engines/interfaces/process_launcher_interface.py` (behaviour 4). Copy the style of `src/vibey/infrastructure/engines/interfaces/local_engines_interface.py` (module docstring "Mirrors `vibey/infrastructure/engines/process_launcher.py` (ADR-0016). Interfaces declare; they never consume."). Imports: `asyncio`, `from collections.abc import Mapping, Sequence`, `from pathlib import Path`, `from typing import Protocol, TextIO, runtime_checkable`, `from vibey.domain.engine import EngineDescriptor`. The package is already in `.importlinter`'s `infrastructure-interfaces-declare-only` contract (`.importlinter:115`). Do not edit `interfaces/__init__.py`.
- `src/vibey/infrastructure/engines/loop_process_adapter.py` (about 700 lines after child 1: `edit_file` only, never `write_file`): delete the `isolate_python_env` definition, add the re-export (behaviour 2), add the imports of `AsyncioProcessSpawner`, `EngineProcessLauncher`, `ShutilExecutableResolver` (from `vibey.infrastructure.engines.process_launcher`) and of `EngineProcessLauncherInterface`, `ExecutableResolverInterface`, `ProcessSpawnerInterface` (from `vibey.infrastructure.engines.interfaces.process_launcher_interface`), and make the edits of behaviour 5.
- After editing, run `uv run ruff check --fix` and `uv run ruff format` on the four source files, so the import order passes.
- **New or appended** `tests/fakes/process.py` (behaviour 7). If the file does not exist, create it with the provenance line 1 and a module docstring. If it exists (lane `fakes-process-executor` may have created it), append your classes with `open(path, "a")` and change no existing line; if it already defines a class with one of your names, stop and report the clash.
- **If `tests/fakes/registry.py` exists** (lane `fakes-registry`): append `ProcessSpawnerInterface` and `ExecutableResolverInterface` to `DRIVER_SEAMS`, and add `FakeRegistration(port=ProcessSpawnerInterface, build=FakeProcessSpawner)` and `FakeRegistration(port=ExecutableResolverInterface, build=FakeExecutableResolver)` to `REGISTRY`. If it does not exist, skip this step.
- **New** `tests/infrastructure/engines/test_process_launcher.py` and `tests/infrastructure/engines/test_loop_process_adapter_seams.py`.
- Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of `loop_process_adapter.py`: `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`

## Acceptance criteria
- [ ] `tests/infrastructure/engines/test_loop_process_adapter.py`, `tests/infrastructure/process/test_python_env.py` and `tests/live` pass **with no edits** (the `git diff --stat HEAD~1 -- ...` line of the check block prints nothing after the commit).
- [ ] `tests/infrastructure/process/test_call_sites.py` (including `test_the_reaper_does_not_change_how_adapters_compare`), `tests/infrastructure/test_gate_runner.py` and `tests/application/test_conformance.py` pass unedited; `src/vibey/infrastructure/build/gate_runner.py` is not edited.
- [ ] `grep -n "def isolate_python_env" src/vibey/infrastructure/engines/loop_process_adapter.py` prints nothing, and `grep -n "def isolate_python_env" src/vibey/infrastructure/process/python_env.py` prints one line.
- [ ] `grep -n "from asyncio import\|from shutil import" src/vibey/infrastructure/engines/process_launcher.py` prints nothing.
- [ ] The new tests inject `FakeProcessSpawner` and `FakeExecutableResolver` and use no `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`. If `tests/meta/patching_baseline.json` exists, it does not change.
- [ ] `uv run lint-imports` passes (no cycle; the interfaces package imports nothing from `vibey.cli`, `vibey.tui` or `vibey.bootstrap`).
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/engines/test_process_launcher.py`:
- `test_environment_strips_the_orchestrator_venv_and_applies_the_overlay`: using `monkeypatch.setenv` only, set `VIRTUAL_ENV=/orchestrator/.venv`, `PATH=/orchestrator/.venv/bin:/usr/bin` and `QWENLOOP_MODEL=inherited`. A launcher with `env_overlay={"QWENLOOP_MODEL": "q"}` and `python_env=OrchestratorPythonEnv()` returns an environment with no `VIRTUAL_ENV`, `PATH == "/usr/bin"` and `QWENLOOP_MODEL == "q"`.
- `test_resolve_uses_the_injected_resolver_and_keeps_an_unresolved_name`: with `FakeExecutableResolver({"claudeloop": "/opt/engines/claudeloop"})`, `resolve(("claudeloop", "run"))` is `("/opt/engines/claudeloop", "run")`, `resolve(("missing", "run"))` is `("missing", "run")`, and `lookups == ["claudeloop", "missing"]`.
- `test_spawn_merges_the_overlay_last`: with `env_overlay={"QWENLOOP_MODEL": "q"}`, `await launcher.spawn("x", env={"A": "1", "QWENLOOP_MODEL": "inherited"}, stdout=PIPE, stderr=PIPE)` records `env == {"A": "1", "QWENLOOP_MODEL": "q"}`. With an empty overlay and `env=None`, the recorded `env` is `None`. With the overlay and `env=None`, the recorded env is `os.environ` plus the overlay.
- `test_spawn_passes_cwd_streams_and_the_session_flag`: `await launcher.spawn("a", "b", stdout=PIPE, stderr=DEVNULL, cwd=tmp_path, start_new_session=True)` returns the spawner's `FakeProcess`, and the one `SpawnCall` has `argv == ("a", "b")`, `stdout == PIPE`, `stderr == DEVNULL`, `cwd == tmp_path` and `start_new_session is True` (`PIPE`/`DEVNULL` from `asyncio.subprocess`).
- `test_default_spawner_runs_sys_executable`: `AsyncioProcessSpawner().spawn((sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"), env=None, stdout=PIPE, stderr=PIPE, cwd=None, start_new_session=False)`, then `communicate()`, gives `(b"out\n", b"err\n")` and `returncode == 3`. This is a real, hermetic child of the test's own interpreter.
- `test_default_resolver_uses_the_path`: `ShutilExecutableResolver().which(sys.executable) == sys.executable`, and `which("vibey-no-such-binary-367")` is `None`.
- `test_fakes_behave_like_a_process`: `FakeProcess(7, exit_code=2, stdout=b"o")` communicates `(b"o", b"")` with `returncode == 2`; a fresh one after `terminate()` has `returncode == -15`, and after `kill()` on another fresh one `-9`.
- `test_classes_satisfy_their_interfaces`: `isinstance` of `AsyncioProcessSpawner()` and `FakeProcessSpawner()` against `ProcessSpawnerInterface`, of `ShutilExecutableResolver()` and `FakeExecutableResolver()` against `ExecutableResolverInterface`, and of an `EngineProcessLauncher` against `EngineProcessLauncherInterface`; the launcher's `descriptor is CLAUDELOOP`.

`tests/infrastructure/engines/test_loop_process_adapter_seams.py`:
- `test_adapter_starts_through_injected_seams`: `adapter = LoopProcessAdapter(descriptor=CLAUDELOOP, spawner=FakeProcessSpawner(FakeProcess(4321)), resolver=FakeExecutableResolver({"claudeloop": "/opt/engines/claudeloop"}))`; `handle = await adapter.start(RunSpec(run_id=uuid4(), worktree_path=tmp_path, prompt="do the thing", effort=Effort.LOW, isolation=IsolationLevel.WORKTREE))` (`RunSpec` from `vibey.application.dto`, `Effort` from `vibey.domain.effort`, `IsolationLevel` from `vibey.domain.engine`). Then `handle.pid == 4321`, and the one `SpawnCall` has `argv[0] == "/opt/engines/claudeloop"`, `cwd == tmp_path`, `start_new_session is False`, and an `env` with no `VIRTUAL_ENV`. Clean up with `_active_processes.pop(handle.run_id, None)` and `adapter.release_diagnostics(handle)`.
- `test_isolate_python_env_is_one_function`: the name imported from `vibey.infrastructure.engines.loop_process_adapter` `is` the one imported from `vibey.infrastructure.process.python_env`.
- `test_default_seams_do_not_change_how_adapters_compare`: `LoopProcessAdapter(descriptor=CLAUDELOOP) == LoopProcessAdapter(descriptor=CLAUDELOOP)`, and the default `spawner` and `resolver` are `AsyncioProcessSpawner` and `ShutilExecutableResolver` instances.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/infrastructure/process tests/infrastructure/test_gate_runner.py tests/application/test_conformance.py tests/application/test_interfaces_convention.py tests/fakes tests/meta tests/live
uv run pytest -q -p no:cacheprovider tests/system/test_full_worker_faked.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
# after the local commit, this must print nothing:
git diff --stat HEAD~1 -- tests/infrastructure/engines/test_loop_process_adapter.py tests/infrastructure/process/test_python_env.py tests/live src/vibey/infrastructure/build/gate_runner.py
```
`tests/system/test_full_worker_faked.py` needs PostgreSQL today (the root `tests/conftest.py` opens it at session start, defaulting to `postgresql://$USER@localhost:5432/vibey_test`). It is never this lane's only proof.

## Out of scope
- The run-directory classes (child 1, already landed).
- Routing `help_text` and `preflight`'s `shutil.which` (`:228`, `:269` at `4317cff6`) and `subprocess.run` through seams, the stop timeouts, and converting the legacy adapter tests away from patching: lane `fakes-process-spawner` owns those, and must reuse this lane's `ProcessSpawnerInterface` rather than declare a second one (10.e).
- The `CommandExecutor` seam and its fake (lane `fakes-process-executor`, a different seam).
- Any loop-service, router, seat-host or queue code (ADR-0046's lanes).
- Changing any behaviour.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject.

## Standing constraints
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`. They must keep passing; `tests/live/**` spawns the in-tree loop binaries through the production `AsyncioProcessSpawner`.
- **Line 1 of every new file** is the provenance comment, copied byte for byte from a sibling file.
- **Substitution at a declared seam only:** constructor or keyword injection. Never `monkeypatch.setattr` on a module or class attribute, `mock.patch`, `MagicMock` or `AsyncMock` in any new test (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` are allowed. The legacy tests that still patch are left exactly as they are.
- **A fake is a plain class with real in-memory behaviour for every method.** `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only `pass`, only `return None`, or only `raise NotImplementedError`.
- **Editing:** change existing files with `edit_file` (an exact, unique `old_string` copied from `read_file`), never `write_file`, for any existing file over 100 lines. Never rewrite an existing test file. After each change, run the focused tests.
- **Arch Linux and macOS (8.h):** the real-process test runs `sys.executable`, which exists on both; nothing else touches the OS.

**Depends on:** split-367-1-run-dir
- split-367-1-run-dir: the same file, `loop_process_adapter.py`, with its tail, inbox and stop-summary bodies already extracted; this lane runs after it so the two edits never conflict.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
