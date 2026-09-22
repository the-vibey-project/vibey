## Title
feat(loop-service): a loop runs one request as its own adapter's subprocess, and nothing else
ADR-0046 lane L24 (slug `loops-local-run-executor`).

## Why
Draft ADR-0046 (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md`, §3 step 7 and §10) has each run executed by a loop's **seat host**, which runs the binaries of its own loop's adapters. The superseded R21 (`specs/rmq-r21-local-run-executor.md`, behaviours 2–3; closing note `issue-audit/updates/368.md`) specified this executor for one binary per engine service; ADR-0046 keeps its name and role (`local_run_executor.py`) and widens it to "the binaries of **its own** adapters" (*Security impact*): `args[0]` is validated by `RunArgsPolicy`, `cwd` must lie under `[loop_services] root`, and the environment comes only from the loop's configuration, never from a message.

It reuses what the family already has (10.e, `src/vibey_tools/gh/docs/doctrines.md:417`): the spawner and resolver seams and `isolate_python_env` of R20's child 2 (`specs/split-367-2-process-launcher.md`), `RunInbox` of R20's child 1 (`specs/split-367-1-run-dir.md`), and the bounded kill-and-reap `ProcessReaper` (`src/vibey/infrastructure/process/reaper.py:45-98` at integration `d3b4a388`). Its output handling copies `LoopProcessAdapter.start` (`src/vibey/infrastructure/engines/loop_process_adapter.py:361-378`): a RUN writes stdout and stderr to `<cwd>/.vibey/diagnostics/<run_id>.stdout|.stderr` (pipes nobody drains deadlock a long run, PR #299), and a probe captures them. Substitution is through injected seams only (9.b, `doctrines.md:349`).

## Required behaviour
1. **`class LocalRunExecutor`** in `src/vibey/infrastructure/loop_service/local_run_executor.py`, built with keyword arguments:
   `LocalRunExecutor(*, binaries: Mapping[str, str], root: Path, policy: RunArgsPolicyInterface, spawner: ProcessSpawnerInterface, resolver: ExecutableResolverInterface, reaper: ProcessReaperInterface, base_environ: Mapping[str, str], python_env: OrchestratorPythonEnvInterface | None = None)`.
   `binaries` maps an engine id to its binary name (claudeloop-local maps to the claudeloop binary; the composition lane builds it). It keeps `dict(binaries)`, `root.resolve()`, and `python_env` defaulting to `OrchestratorPythonEnv(base_environ)`. (`python_env` is one keyword beyond the design sheet: `isolate_python_env` needs the venv prefixes, and `OrchestratorPythonEnv` is the one place that knows them.)
2. **`reason_to_reject(self, request: RunRequest) -> str | None`**, checked in this order, first match wins:
   - `request.engine_id not in binaries` → `f"engine {request.engine_id} is not an adapter of this loop"`;
   - `policy.reason(request.purpose, request.args)` is not `None` → that reason, unchanged;
   - `cwd = Path(request.cwd).resolve()`; `not cwd.is_relative_to(self._root)` → `f"cwd {request.cwd} is outside the loop root {self._root}"` (a symlink out of the root is refused, because `resolve()` follows it);
   - `request.run_dir is not None and not (cwd / request.run_dir).resolve().is_relative_to(cwd)` → `f"run_dir {request.run_dir} is outside cwd {request.cwd}"`;
   - otherwise `None`.
   The domain already refuses a relative `cwd` (`RunRequest.__post_init__`, lane `loops-run-protocol-messages`), so the executor has no branch for it.
3. **`async start(self, request: RunRequest, *, env_overlay: Mapping[str, str]) -> LocalRun`** (call it only after `reason_to_reject` returned `None`):
   ```python
   binary = self._binaries[request.engine_id]
   argv = (self._resolver.which(binary) or binary, *request.args)
   environment = isolate_python_env(self._base_environ, venv_prefixes=self._python_env.venv_prefixes())
   environment.update(env_overlay)
   cwd = Path(request.cwd)
   run_dir = None if request.run_dir is None else cwd / request.run_dir
   stdout: int | TextIO = asyncio.subprocess.PIPE
   stderr: int | TextIO = asyncio.subprocess.PIPE
   files: tuple[TextIO, TextIO] | None = None
   if request.purpose is RunPurpose.RUN and not request.capture_output:
       diagnostics = cwd / ".vibey" / "diagnostics"
       diagnostics.mkdir(parents=True, exist_ok=True)
       files = (
           (diagnostics / f"{request.run_id}.stdout").open("w", encoding="utf-8"),
           (diagnostics / f"{request.run_id}.stderr").open("w", encoding="utf-8"),
       )
       stdout, stderr = files
   try:
       process = await self._spawner.spawn(
           argv, env=environment, stdout=stdout, stderr=stderr, cwd=cwd, start_new_session=True
       )
   except BaseException:
       for handle in files or ():
           handle.close()
       raise
   return LocalRun(process=process, run_dir=run_dir, reaper=self._reaper, files=files)
   ```
   `start_new_session=True` makes the run lead its own process group, which the reaper's `killpg` needs. A missing binary raises the spawner's `FileNotFoundError` (an `OSError`), which the seat host turns into a rejection.
4. **`class LocalRun`**, in the same module, built as `LocalRun(*, process: asyncio.subprocess.Process, run_dir: Path | None, reaper: ProcessReaperInterface, files: tuple[TextIO, TextIO] | None)`. Class constant `OUTPUT_CAP_BYTES = 64 * 1024`. `__init__` keeps the four arguments and sets `self._capture = files is None` (the output is captured through pipes; `_files` later becomes `None` when the files are closed, so never test `_files` for this). Last in `__init__` it starts one task that owns the process's end: `self._exited: asyncio.Task[tuple[bytes, bytes]] = asyncio.create_task(self._settle())`, where
   ```python
   async def _settle(self) -> tuple[bytes, bytes]:
       if self._capture:
           return await self._process.communicate()
       await self._process.wait()
       return (b"", b"")
   ```
   (so a captured pipe is always drained). Its members:
   - property `pid -> int` (`process.pid`) and property `run_dir -> Path | None`;
   - `async wait(self, timeout: float | None) -> int | None`: `await asyncio.wait_for(asyncio.shield(self._exited), timeout)`; on `TimeoutError` return `None`; otherwise close the output files and return `process.returncode`;
   - `async stop(self, grace_seconds: float) -> None`: when `run_dir` is set, `RunInbox(run_dir).write_stop()`; then `if await self.wait(grace_seconds) is None:` call `await self._reaper.kill_and_reap(self._process)` and `await self.wait(self._reaper.grace_seconds)`; finally close the output files;
   - `control(self, command: RunControlCommand, text: str | None) -> bool`: `False` when `run_dir` is `None` or `command is RunControlCommand.SUPERSEDE` (not a per-run command); `PROMPT_NOW` → `RunInbox(run_dir).write_prompt(text or "", now=True)`; `PROMPT_AT_BREAK` → `write_prompt(text or "", now=False)`; any other command (`STOP`, `WIND_DOWN`) → `write_command(command.value)`; then `True`;
   - `output(self) -> tuple[str | None, str | None]`: `if not (self._capture and self._exited.done()): return (None, None)`; otherwise the last `OUTPUT_CAP_BYTES` of each stream of `self._exited.result()`, decoded with `decode("utf-8", errors="replace")`;
   - `meta_status(self) -> str | None`: `None` without a `run_dir`; else read `run_dir / "meta.json"` with `json.loads`, returning `None` on `OSError` or `ValueError`, and the `"status"` value only when the JSON is a `dict` and the value is a `str`.
   - A private `_close_files(self) -> None` closes and forgets the two files (`files, self._files = self._files, None`, then `for handle in files or (): handle.close()`). Calling it twice is harmless.
5. **Interfaces** in `src/vibey/infrastructure/loop_service/interfaces/local_run_executor_interface.py`, both `@runtime_checkable`, one-line docstring per member:
   - `LocalRunInterface`: properties `pid -> int`, `run_dir -> Path | None`; `async wait(self, timeout: float | None) -> int | None`; `async stop(self, grace_seconds: float) -> None`; `control(self, command: RunControlCommand, text: str | None) -> bool`; `output(self) -> tuple[str | None, str | None]`; `meta_status(self) -> str | None`.
   - `LocalRunExecutorInterface`: `reason_to_reject(self, request: RunRequest) -> str | None`; `async start(self, request: RunRequest, *, env_overlay: Mapping[str, str]) -> LocalRunInterface`.
6. **In-memory fakes**, appended to `tests/fakes/loops.py`:
   ```python
   class FakeLocalRun:
       """LocalRunInterface whose end the test scripts: it has exited at start unless `hang`;
       `finish(code)` ends a hanging run; `stop` ends it with `stop_exit_code`."""

       def __init__(
           self,
           request: RunRequest,
           *,
           pid: int = 4242,
           exit_code: int = 0,
           stdout: str | None = None,
           stderr: str | None = None,
           meta_status: str | None = None,
           hang: bool = False,
           stop_exit_code: int = -9,
       ) -> None:
           self.request = request
           self._pid = pid
           self.exit_code: int | None = None
           self.stdout = stdout
           self.stderr = stderr
           self._meta_status = meta_status
           self.stop_exit_code = stop_exit_code
           self.stops: list[float] = []
           self.controls: list[tuple[RunControlCommand, str | None]] = []
           self._finished = asyncio.Event()
           if not hang:
               self.finish(exit_code)

       @property
       def pid(self) -> int:
           return self._pid

       @property
       def run_dir(self) -> Path | None:
           if self.request.run_dir is None:
               return None
           return Path(self.request.cwd) / self.request.run_dir

       def finish(self, exit_code: int) -> None:
           if not self._finished.is_set():
               self.exit_code = exit_code
               self._finished.set()

       async def wait(self, timeout: float | None) -> int | None:
           try:
               await asyncio.wait_for(self._finished.wait(), timeout)
           except TimeoutError:
               return None
           return self.exit_code

       async def stop(self, grace_seconds: float) -> None:
           self.stops.append(grace_seconds)
           self.finish(self.stop_exit_code)

       def control(self, command: RunControlCommand, text: str | None) -> bool:
           self.controls.append((command, text))
           return self.request.run_dir is not None

       def output(self) -> tuple[str | None, str | None]:
           return (self.stdout, self.stderr)

       def meta_status(self) -> str | None:
           return self._meta_status


   class FakeLocalRunExecutor:
       """LocalRunExecutorInterface in memory. Every start builds a FakeLocalRun from the
       scripted values (change them between starts); `reject` and `start_error` script refusals."""

       def __init__(
           self,
           *,
           reject: str | None = None,
           start_error: Exception | None = None,
           exit_code: int = 0,
           stdout: str | None = None,
           stderr: str | None = None,
           meta_status: str | None = None,
           hang: bool = False,
       ) -> None:
           self.reject = reject
           self.start_error = start_error
           self.exit_code = exit_code
           self.stdout = stdout
           self.stderr = stderr
           self.meta_status = meta_status
           self.hang = hang
           self.checked: list[UUID] = []
           self.starts: list[tuple[RunRequest, dict[str, str]]] = []
           self.runs: list[FakeLocalRun] = []

       def reason_to_reject(self, request: RunRequest) -> str | None:
           self.checked.append(request.run_id)
           return self.reject

       async def start(self, request: RunRequest, *, env_overlay: Mapping[str, str]) -> FakeLocalRun:
           self.starts.append((request, dict(env_overlay)))
           if self.start_error is not None:
               raise self.start_error
           run = FakeLocalRun(
               request,
               pid=4242 + len(self.runs),
               exit_code=self.exit_code,
               stdout=self.stdout,
               stderr=self.stderr,
               meta_status=self.meta_status,
               hang=self.hang,
           )
           self.runs.append(run)
           return run
   ```
7. **Registry**: `LocalRunExecutorInterface` is appended to `DRIVER_SEAMS`, and `REGISTRY` gains `FakeRegistration(port=LocalRunExecutorInterface, build=FakeLocalRunExecutor)`. (`LocalRunInterface` is a product of the seam, not an injected seam; its fake is checked by `isinstance` in this lane's tests.)
8. 8.g: the executor records nothing itself; the seat host records each run (lane `loops-seat-host-core`, subject RUN).

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of `src/vibey/infrastructure/process/reaper.py`.
- **Precondition.** `test -f src/vibey/infrastructure/engines/process_launcher.py && test -f src/vibey/infrastructure/engines/run_dir.py && grep -n "def isolate_python_env" src/vibey/infrastructure/process/python_env.py` must succeed. If not, stop and report `blocked: R20's run-dir or process-launcher lane has not landed`.
- **New** `src/vibey/infrastructure/loop_service/local_run_executor.py`. Imports: `asyncio`, `json`, `from collections.abc import Mapping`, `from pathlib import Path`, `from typing import TextIO`, `from vibey.domain.interfaces.run_args_policy_interface import RunArgsPolicyInterface`, `from vibey.domain.run_protocol import RunControlCommand, RunPurpose, RunRequest`, `from vibey.infrastructure.engines.interfaces.process_launcher_interface import ExecutableResolverInterface, ProcessSpawnerInterface`, `from vibey.infrastructure.engines.run_dir import RunInbox`, `from vibey.infrastructure.process import OrchestratorPythonEnv`, `from vibey.infrastructure.process.interfaces import OrchestratorPythonEnvInterface, ProcessReaperInterface`, `from vibey.infrastructure.process.python_env import isolate_python_env`. `__all__ = ["LocalRun", "LocalRunExecutor"]`. Module docstring: this is ADR-0046 §3's run executor; it runs only the loop's own adapters' binaries, under `[loop_services] root`, with the environment from the loop's configuration only (*Security impact*).
- **New** `src/vibey/infrastructure/loop_service/interfaces/local_run_executor_interface.py` (behaviour 5). Copy the style of `src/vibey/infrastructure/process/interfaces/reaper_interface.py`.
- **`tests/fakes/loops.py`**: add to its import block (with `edit_file`, after its last import line) `import asyncio`, `from collections.abc import Mapping`, `from vibey.domain.run_protocol import RunControlCommand, RunRequest` (plus `Path`/`UUID` if not already imported); append the two classes of behaviour 6 at the end with `edit_file`. Never rewrite the file.
- **`tests/fakes/registry.py`**: run the registration script of lane `loops-result-store` ("Where to change", the `register_fakes.py` block) with only these three lists:
  ```python
  IMPORTS = [
      "from tests.fakes.loops import FakeLocalRunExecutor",
      "from vibey.infrastructure.loop_service.interfaces.local_run_executor_interface import LocalRunExecutorInterface",
  ]
  SEAMS = ["LocalRunExecutorInterface"]
  ENTRIES = ["FakeRegistration(port=LocalRunExecutorInterface, build=FakeLocalRunExecutor)"]
  ```
  Save it as `register_fakes.py` in the repository root, run `["python3", "register_fakes.py"]`, delete it with `["rm", "register_fakes.py"]`.
- Then `uv run ruff check --fix tests/fakes/loops.py tests/fakes/registry.py src/vibey/infrastructure/loop_service` and `uv run ruff format` on the same paths plus `tests/infrastructure/loop_service`.
- **New** `tests/infrastructure/loop_service/test_local_run_executor.py`.

## Acceptance criteria
- [ ] The scripted fake engines run for real: exit code, stdout diagnostics file, `meta_status`, capped probe output, stop-then-kill.
- [ ] Every rejection reason of behaviour 2 has a test, including a symlink out of the root.
- [ ] No test lets a `FakeProcess` reach the real `ProcessReaper` (it would `killpg` a real pid): the fake-spawner tests never call `stop` on a run still going.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `monkeypatch.setenv("PATH", ...)` is the only environment change. `tests/meta/patching_baseline.json` does not change.
- [ ] `tests/fakes/test_port_parity.py` passes with the new registration.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_local_run_executor.py`. Every test finishes in under 5 s. Helpers (module functions in a test module are fine):
```python
NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)

def _fake_binary(tmp_path: Path, name: str, script: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    binary = bin_dir / name
    binary.write_text(f"#!/bin/sh\n{script}\n")
    binary.chmod(0o755)
    return bin_dir

def _request(tmp_path: Path, **overrides: object) -> RunRequest:
    cwd = tmp_path / "work" / "wt"
    cwd.mkdir(parents=True, exist_ok=True)
    fields: dict[str, object] = dict(
        run_id=uuid4(), loop_id=LoopId.SOVEREIGNLOOP, engine_id="sovereignloop", route_id=None,
        model_pin=None, purpose=RunPurpose.RUN, args=("run", "plan.md"), cwd=str(cwd),
        run_dir=None, supersedes=None, deadline_seconds=60, start_by=NOW + timedelta(minutes=5),
        capture_output=False, requested_at=NOW, caller="test",
    )
    fields.update(overrides)
    return RunRequest(**fields)
```
An executor for real processes: `LocalRunExecutor(binaries={"sovereignloop": "fakeloop", "ghost": "vibey-no-such-binary-l24"}, root=tmp_path / "work", policy=RunArgsPolicy(), spawner=AsyncioProcessSpawner(), resolver=ShutilExecutableResolver(), reaper=ProcessReaper(grace_seconds=2.0), base_environ=dict(os.environ))`, built **after** `monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")`. `AsyncioProcessSpawner`/`ShutilExecutableResolver` come from `vibey.infrastructure.engines.process_launcher`; `FakeProcess`, `FakeProcessSpawner`, `FakeExecutableResolver` from `tests.fakes.process`.
- `test_runs_the_fake_engine_and_returns_its_exit_code`: script `echo "ran $*"`, `mkdir -p "$PWD/.fakeloop/runs/r1"`, `printf '{"status": "finished"}' > "$PWD/.fakeloop/runs/r1/meta.json"`, `exit 3`; request `run_dir=".fakeloop/runs/r1"`. `await run.wait(10) == 3`; `run.meta_status() == "finished"`; `run.run_dir == cwd / ".fakeloop/runs/r1"`; `run.pid > 0`; `run.output() == (None, None)`; `(cwd / ".vibey" / "diagnostics" / f"{run_id}.stdout").read_text() == "ran run plan.md\n"`.
- `test_probe_output_is_captured_and_capped`: script `"head -c 70000 /dev/zero | tr '\\000' x\nprintf tail\nprintf warn >&2"` (a Python string; `tr '\000'` works on GNU and BSD alike); request `purpose=RunPurpose.PROBE, args=("--version",), capture_output=True`. `await run.wait(10) == 0`; `stdout, stderr = run.output()`; `len(stdout) == 65536`, `stdout.endswith("tail")`, `stderr == "warn"`; no diagnostics directory was created.
- `test_stop_writes_the_inbox_then_kills_after_grace`: script `sleep 30`; `run_dir=".fakeloop/runs/r2"`. `await run.stop(0.2)`; exactly one `inbox/*-stop.json` under the run dir, holding `{"command": "stop"}`; `await run.wait(5) == -signal.SIGKILL`.
- `test_stop_does_not_kill_a_run_that_exits_within_grace`: script `sleep 0.2` then `exit 5`, no `run_dir`. `await run.stop(5.0)` returns; `await run.wait(1) == 5`; no `.fakeloop` directory exists.
- `test_start_resolves_the_binary_isolates_the_environment_and_starts_a_session`: `FakeProcessSpawner()`, `FakeExecutableResolver({"fakeloop": "/opt/engines/fakeloop"})`, `base_environ={"PATH": "/orch/.venv/bin:/usr/bin", "VIRTUAL_ENV": "/orch/.venv", "KEEP": "1", "SOVEREIGNLOOP_MODEL": "old"}`, `python_env=OrchestratorPythonEnv({"VIRTUAL_ENV": "/orch/.venv"})`, `env_overlay={"SOVEREIGNLOOP_MODEL": "gpt-oss:20b"}`. The one `SpawnCall` has `argv == ("/opt/engines/fakeloop", "run", "plan.md")`, no `VIRTUAL_ENV`, `env["PATH"] == "/usr/bin"`, `env["KEEP"] == "1"`, `env["SOVEREIGNLOOP_MODEL"] == "gpt-oss:20b"`, `cwd == Path(request.cwd)`, `start_new_session is True`, and `stdout.name` ends with `f"{run_id}.stdout"`. After `await run.wait(1) == 0`, `call.stdout.closed is True`. A second executor with `FakeExecutableResolver()` (no paths) spawns `argv[0] == "fakeloop"`.
- `test_a_missing_binary_raises_file_not_found`: the real executor, `engine_id="ghost"`: `await executor.start(...)` raises `FileNotFoundError`.
- `test_control_maps_commands_to_inbox_files`: a `FakeProcessSpawner` run with `run_dir=".fakeloop/runs/r3"`: `control(STOP, None)`, `control(WIND_DOWN, None)`, `control(PROMPT_NOW, "a")` and `control(PROMPT_AT_BREAK, "b")` each return `True`, and the inbox holds `{"command": "stop"}`, `{"command": "wind_down"}`, `{"command": "prompt-now", "text": "a"}`, `{"command": "prompt-at-break", "text": "b"}`; `control(SUPERSEDE, None)` is `False`; a run without `run_dir` answers `False` to `STOP`. Finish with `await run.wait(1) == 0`.
- `test_rejects_each_unsafe_request`: with `root = tmp_path / "work"`: engine `"codexloop"` → `"engine codexloop is not an adapter of this loop"`; `args=("rm", "-rf")` → `RunArgsPolicy().reason(RunPurpose.RUN, ("rm", "-rf"))` (not `None`); `cwd=str(tmp_path / "elsewhere")` → `f"cwd {cwd} is outside the loop root {root.resolve()}"`; a symlink `root / "escape"` → `tmp_path / "elsewhere"` used as `cwd` → the same message form; `run_dir="../../outside"` → `f"run_dir ../../outside is outside cwd {request.cwd}"`; a safe request → `None`.
- `test_meta_status_reads_only_a_status_string`: a `FakeProcessSpawner` run with a `run_dir`: no `meta.json` → `None`; `not json` → `None`; `["x"]` → `None`; `{"status": 7}` → `None`; `{"status": "failed"}` → `"failed"`; a run without `run_dir` → `None`.
- `test_classes_and_fakes_satisfy_their_interfaces`: `isinstance` of the executor and `FakeLocalRunExecutor()` against `LocalRunExecutorInterface`, and of a started `LocalRun` and a `FakeLocalRun` against `LocalRunInterface`. The fake: `FakeLocalRunExecutor(hang=True)` gives a run whose `await wait(0.01)` is `None`; after `await run.stop(1.0)`, `await run.wait(1) == -9` and `run.stops == [1.0]`; `FakeLocalRunExecutor(reject="no")` rejects with `"no"`; `FakeLocalRunExecutor(start_error=OSError("gone"))` raises it from `start`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/infrastructure/engines tests/infrastructure/process tests/fakes tests/meta/test_patching_ratchet.py tests/application/test_interfaces_convention.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
git status --short
```
The real-process tests use `/bin/sh`, `sleep`, `mkdir`, `printf`, `head` and `tr`, which exist on Arch Linux and macOS alike (8.h, `doctrines.md:326-334`).

## Out of scope
- The seat host that drives this executor, its rules and its replies (lanes `loops-seat-host-core`, `-fence`, `-drain`).
- The result store and the measurement log (lane `loops-result-store`, landed).
- `LoopProcessAdapter` and its tests (unchanged).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests (`tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`) are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow `STORM/EDITING-RULES.md`.

**Depends on:** `loops-result-store`, `loops-run-args-policy`, `split-367-1-run-dir`, `split-367-2-process-launcher`
- `loops-result-store`: the `loop_service` package, its `.importlinter` entry and the loop fakes module.
- `loops-run-args-policy`: `RunArgsPolicy` and `RunArgsPolicyInterface`.
- `split-367-1-run-dir` and `split-367-2-process-launcher` (the design sheet's D13 names; the unfiled specs are `specs/split-367-1-run-dir.md` and `specs/split-367-2-process-launcher.md`, slugs `split-367-1-run-dir` and `split-367-2-process-launcher`): `RunInbox`, the spawner and resolver seams, `isolate_python_env` in `process/python_env.py`, and `tests/fakes/process.py`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
