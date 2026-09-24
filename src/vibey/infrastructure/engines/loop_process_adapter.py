# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""LoopProcessAdapter: real subprocess runner implementing the full EngineAdapter
protocol.

This is the production adapter that supersedes ClaudeLoopProcess. It spawns real
loop processes, streams their events.jsonl with proper translation, detects
completion via descriptor.done_marker, recognizes exit code 75 (wind-down), and
classifies capacity states using the existing classify.py machinery.

Built to work with claudeloop, codexloop, cursorloop, and agyloop via their
descriptors, not four separate classes.
"""

import asyncio
import json
import re
import shutil
import subprocess  # nosec B404 - fixed argv, never shell=True
from collections.abc import AsyncIterator, Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

import structlog

from vibey.application.dto import (
    EngineEvent,
    PreflightResult,
    RunHandle,
    RunSpec,
    SnapshotRef,
    StopSummary,
)
from vibey.domain.capacity import CapacityState
from vibey.domain.engine import EXIT_CODE_WIND_DOWN, EngineDescriptor, EngineId
from vibey.domain.errors import VibeyError
from vibey.domain.job import FailureClass
from vibey.domain.ledger import EventKind
from vibey.infrastructure.engines.argv import build_argv
from vibey.infrastructure.engines.classify import attribute_failure, classify_capacity
from vibey.infrastructure.engines.engine_environment import EngineEnvironmentPolicy
from vibey.infrastructure.engines.interfaces.engine_environment_interface import (
    EngineEnvironmentPolicyInterface,
)
from vibey.infrastructure.engines.loop_events import translate_event_type
from vibey.infrastructure.process import (
    DEFAULT_KILL_GRACE_SECONDS,
    ChildEnvironment,
    OrchestratorPythonEnv,
    ProcessReaper,
)
from vibey.infrastructure.process.interfaces import (
    OrchestratorPythonEnvInterface,
    ProcessReaperInterface,
)

logger = structlog.get_logger(__name__)

# Global registry to keep subprocess.Process objects alive so they don't get
# garbage collected (which would close stdin and kill the child process).
# Key: run_id (UUID), Value: asyncio.subprocess.Process
_active_processes: dict[object, asyncio.subprocess.Process] = {}
_diagnostic_files: dict[object, tuple[TextIO, TextIO]] = {}

# `<binary> run --help` output, keyed by the resolved executable path. Fetched
# once per process lifetime; --help is static for a given install, so there's
# nothing to invalidate. Resolving once and invoking that exact path matters
# when a bundled entrypoint and a separately installed engine share a name on
# PATH: the help contract must describe the binary that start() will launch.
_help_text_cache: dict[str, str] = {}
_ANSI_ESCAPE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _render_plan(descriptor: EngineDescriptor, prompt: str) -> str:
    """Render a vendor-compatible work plan without dropping prompt detail."""
    if descriptor.engine_id is not EngineId.CODEXLOOP:
        return prompt

    summary = next((line.strip() for line in prompt.splitlines() if line.strip()), "Complete task")
    return f"# Work Plan\n\n- [ ] {summary}\n\n## Instructions\n\n{prompt}\n"


class ProcessError(VibeyError):
    """Raised when a loop process fails in an unexpected way."""

    pass


# Kept importable under its old name: stripping vibey's own Python environment is now
# one step of ChildEnvironment.build(), the one builder every engine spawn goes through.
isolate_python_env = ChildEnvironment.without_python_env


@dataclass(slots=True, frozen=True)
class LoopProcessAdapter:
    """Real subprocess adapter parameterized over EngineDescriptor.

    This replaces the separate per-engine classes with one adapter that uses
    descriptor data to build argv and translate events.
    """

    descriptor: EngineDescriptor
    doctor_timeout: float = 120.0
    """`<binary> doctor` wall-clock budget for preflight. claudeloop's
    doctor verifies credentials over the network and takes ~60s warm --
    the old hardcoded 30s meant every real claudeloop preflight timed out
    into the env-var fallback, which cannot see CLI-credential auth."""
    env_overlay: Mapping[str, str] = field(default_factory=dict)
    """Values vibey sets for this engine's processes -- laid over the allow-listed
    environment last, after the orchestrator's Python environment is stripped, to the
    run and to its preflight alike, so the doctor probes the same backend the run will
    use. How qwenloop learns the one local endpoint (`QWENLOOP_BASE_URL` from
    `VIBEY_OLLAMA_URL`, ADR-0038); empty for every engine whose configuration lives in
    its own files. It can never carry one of vibey's own variables."""
    environment: EngineEnvironmentPolicyInterface = field(
        default_factory=EngineEnvironmentPolicy, compare=False, repr=False
    )
    """What this engine's sessions may see of the worker's environment: an allow-list,
    never a copy. The default is the system basics plus the descriptor's own declared
    variables and credential; `build_full_worker` swaps in the project's policy
    (`engine_environment` in its config record). Every spawn -- the run, the
    `--version` and `doctor` probes, the `--help` fetch -- builds through it."""
    kill_grace_seconds: float = DEFAULT_KILL_GRACE_SECONDS
    """How long a killed preflight probe (`--version`, `doctor`) may take to be
    reaped before the adapter gives up on it and logs `engine_process_not_reaped`
    (#283). The adapter is built without the project's config, so this is a
    constructor value, like `doctor_timeout`."""
    python_env: OrchestratorPythonEnvInterface = field(
        default_factory=OrchestratorPythonEnv, compare=False, repr=False
    )
    """Where vibey's own Python environment lives, stripped from every engine
    session. Shared with the gate runner, so the two apply the same guard."""
    _reaper: ProcessReaperInterface = field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        # The descriptor's passthrough and the overlay are checked against the forbidden
        # rule now, when the adapter is built -- and again whenever a project's policy is
        # applied, since `dataclasses.replace` builds a new one -- rather than on the
        # first spawn, which may be the first BUILD session hours into a run. Building
        # the ChildEnvironment validates both; it reads no environment until build().
        self.environment.environment(
            self.descriptor, overlay=self.env_overlay, python_env=self.python_env
        )
        # Built once, here, so an invalid grace fails when the adapter is built rather
        # than on the first probe that times out.
        object.__setattr__(
            self,
            "_reaper",
            ProcessReaper(
                grace_seconds=self.kill_grace_seconds,
                event="engine_process_not_reaped",
                context={"engine": self.descriptor.engine_id.value},
            ),
        )

    def _engine_environment(self) -> dict[str, str]:
        """The environment every process of this engine starts with: the probes and
        the session alike, built by the engine's environment policy."""
        return self.environment.environment(
            self.descriptor, overlay=self.env_overlay, python_env=self.python_env
        ).build()

    async def _spawn(
        self,
        *argv: str,
        stdout: int | TextIO,
        stderr: int | TextIO,
        cwd: Path | None = None,
        start_new_session: bool = False,
    ) -> asyncio.subprocess.Process:
        """`asyncio.create_subprocess_exec` with the engine's allow-listed environment.

        There is no way to pass another environment, and no way to inherit the
        worker's: a spawn that could would be the one that leaks it.
        `start_new_session=True` makes the child lead a process group of its own, which
        `_communicate`'s kill needs to reach everything the child started.
        """
        return await asyncio.create_subprocess_exec(
            *argv,
            stdout=stdout,
            stderr=stderr,
            cwd=cwd,
            env=self._engine_environment(),
            start_new_session=start_new_session,
        )

    async def _communicate(
        self, process: asyncio.subprocess.Process, *, timeout: float
    ) -> tuple[bytes, bytes]:
        """Collect a probe's output. On a timeout, a cancellation or any other failure,
        kill its whole group and reap it within `kill_grace_seconds`, then re-raise.

        The kill used to reach only the probe itself, and the wait after it had no
        bound. Any helper the probe had started kept its pipes open, so preflight,
        and the worker with it, waited for as long as the helper lived (#283). The
        probe now leads its own group, so the kill reaches its helpers. A helper that
        left the group is logged and left behind, not waited on."""
        communication = asyncio.create_task(process.communicate())
        try:
            return await asyncio.wait_for(communication, timeout=timeout)
        except BaseException:
            communication.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await communication
            await self._reaper.kill_and_reap(process)
            raise

    @property
    def help_text(self) -> str | None:
        """`<binary> run --help` output, for the flags conformance check to
        verify descriptor.effort_projection/isolation_flags against.

        A plain synchronous property, not async: the conformance check reads
        it via getattr(), a sync attribute access. --help never talks to a
        vendor API or touches the filesystem beyond the binary itself, so a
        short blocking subprocess call here is a fixed, small cost, not an
        open-ended one -- unlike preflight()'s doctor/--version calls, which
        do real auth/network work and stay async.
        """
        binary = self.descriptor.binary
        binary_path = shutil.which(binary)
        if binary_path is None:
            return None
        if binary_path in _help_text_cache:
            return _help_text_cache[binary_path]
        try:
            # A wide COLUMNS keeps Rich-based CLIs (typer/click) from
            # truncating flag names/descriptions when stdout isn't a real
            # terminal -- confirmed directly: piped without this, longer
            # flags like --append-system-prompt get cut to
            # "--append-system-pro…", which would make a real, present flag
            # look missing to a substring check.
            # Probe the same environment that start() gives the engine. In
            # particular, an inherited VIRTUAL_ENV/PYTHONPATH can make an
            # editable install resolve a different CLI than the absolute
            # entrypoint we launch, so the help contract can disagree with
            # the process that will actually run.
            env = self._engine_environment()
            env.update({"COLUMNS": "250", "LINES": "50", "NO_COLOR": "1"})
            result = subprocess.run(  # nosec B603 - fixed argv, never shell=True
                [binary_path, "run", "--help"],
                capture_output=True,
                text=True,
                timeout=10.0,
                env=env,
                check=False,
            )
            text = (result.stdout or "") + (result.stderr or "")
        except (OSError, subprocess.TimeoutExpired) as e:
            logger.warning(
                "help_text_fetch_failed",
                engine=self.descriptor.engine_id.value,
                error=str(e),
            )
            return None
        normalized = _ANSI_ESCAPE.sub("", text)
        _help_text_cache[binary_path] = normalized
        return normalized

    async def preflight(self) -> PreflightResult:
        """Check if binary exists and auth is OK (via `doctor`)."""
        binary_path = shutil.which(self.descriptor.binary)
        if not binary_path:
            return PreflightResult(
                installed=False,
                version=None,
                auth_ok=False,
                detail=f"{self.descriptor.binary} not found on PATH",
            )

        # Try to get version
        try:
            proc = await self._spawn(
                binary_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
            stdout, stderr = await self._communicate(proc, timeout=10.0)
            version_output = (stdout or stderr).decode().strip()
            version = version_output.split()[-1] if version_output else None
        except (TimeoutError, Exception) as e:
            logger.warning(
                "version_check_failed",
                engine=self.descriptor.engine_id.value,
                error=str(e),
            )
            version = None

        # Check auth via doctor (if the command exists)
        auth_ok = False
        detail = ""
        try:
            proc = await self._spawn(
                binary_path,
                "doctor",
                *self.descriptor.doctor_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
            stdout, stderr = await self._communicate(proc, timeout=self.doctor_timeout)
            auth_ok = proc.returncode == 0
            if not auth_ok:
                detail = (stderr or stdout).decode().strip()[:500]
        except (TimeoutError, Exception) as e:
            logger.warning(
                "doctor_check_failed",
                engine=self.descriptor.engine_id.value,
                error=str(e),
            )
            # No doctor command or it failed - check the same environment the
            # probe received as a fallback.
            auth_ok = any(self._engine_environment().get(var) for var in self.descriptor.auth_env)
            if not auth_ok:
                detail = f"No {self.descriptor.auth_env} found in environment"

        return PreflightResult(
            installed=True,
            version=version,
            auth_ok=auth_ok,
            detail=detail,
        )

    async def start(self, spec: RunSpec) -> RunHandle:
        """Build argv, write plan, spawn process, return handle."""
        run_dir = spec.worktree_path / self.descriptor.state_dir / "runs" / str(spec.run_id)
        # Don't create run_dir here - let the engine create it (some engines
        # like agyloop use exist_ok=False and will fail if it already exists)

        # Write the plan file if this is a new run
        if spec.session_id is None:
            plan_dir = spec.worktree_path / ".vibey" / "plans"
            plan_dir.mkdir(parents=True, exist_ok=True)
            plan_path = plan_dir / f"{spec.run_id}.md"
            plan_path.write_text(_render_plan(self.descriptor, spec.prompt))

        # Build argv using existing argv.py
        argv = build_argv(self.descriptor, spec)
        # The absorbed runner entrypoints are shipped in vibey's own venv. The
        # child must not inherit that venv on PATH (it could install into and
        # mutate the orchestrator environment), so resolve the executable
        # before applying the isolation below. An absolute path keeps the
        # bundled entrypoint runnable without reintroducing the venv into the
        # child's PATH; separately installed engines continue to work the same
        # way.
        binary_path = shutil.which(argv[0])
        if binary_path is not None:
            argv = (binary_path, *argv[1:])

        # Spawn the process. Output goes to bounded-lifetime files rather than pipes:
        # pipes can deadlock a long-running engine when nobody drains them, while
        # DEVNULL throws away the only diagnostic that can distinguish a failed task
        # from a failed backend (PR #299).
        diagnostic_dir = spec.worktree_path / ".vibey" / "diagnostics"
        diagnostic_dir.mkdir(parents=True, exist_ok=True)
        stdout_file = (diagnostic_dir / f"{spec.run_id}.stdout").open("w", encoding="utf-8")
        stderr_file = (diagnostic_dir / f"{spec.run_id}.stderr").open("w", encoding="utf-8")
        try:
            logger.debug(
                "spawning_process",
                engine=self.descriptor.engine_id.value,
                argv=" ".join(argv),
                stdout=str(stdout_file.name),
                stderr=str(stderr_file.name),
            )
            process = await self._spawn(
                *argv,
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=spec.worktree_path,
            )
        except Exception as e:
            stdout_file.close()
            stderr_file.close()
            raise ProcessError(f"Failed to spawn {self.descriptor.binary}: {e}") from e
        _diagnostic_files[spec.run_id] = (stdout_file, stderr_file)

        logger.info(
            "engine_started",
            engine=self.descriptor.engine_id.value,
            run_id=str(spec.run_id),
            pid=process.pid,
            argv=" ".join(argv),
        )

        # Store the process object globally to prevent garbage collection
        # (which would close stdin and kill the child process)
        _active_processes[spec.run_id] = process
        logger.debug(
            "process_stored",
            run_id=str(spec.run_id),
            pid=process.pid,
            active_count=len(_active_processes),
        )

        return RunHandle(
            run_id=spec.run_id,
            engine_id=self.descriptor.engine_id,
            run_dir=run_dir,
            pid=process.pid,
        )

    async def tail(self, handle: RunHandle) -> AsyncIterator[EngineEvent]:
        """Stream events.jsonl with real-time translation.

        Reads events.jsonl line by line, translates event_type -> kind using
        loop_events.LOOP_EVENT_MAP, yields EngineEvent with the vibey EventKind
        as the kind field.
        """
        events_path = handle.run_dir / "events.jsonl"

        # Wait for events.jsonl to exist
        for _ in range(100):  # 10 seconds max
            if events_path.exists():
                break
            await asyncio.sleep(0.1)
        else:
            logger.warning(
                "events_file_missing",
                run_id=str(handle.run_id),
                path=str(events_path),
            )
            return

        # Tail the file (simplified for now - can be made more sophisticated)
        seen_lines = 0
        process_exited_without_status_since: float | None = None
        while True:
            try:
                lines = (await asyncio.to_thread(events_path.read_text)).splitlines()
                for line in lines[seen_lines:]:
                    if not line.strip():
                        continue
                    try:
                        raw = json.loads(line)
                        # claudeloop/agyloop write {"event_type": ..., "payload": {...}}.
                        # codexloop passes the wrapped codex CLI's own stream
                        # through nearly verbatim, where the key is "type" and
                        # the fields sit at the top level with no payload
                        # envelope. Accepting only event_type/kind meant every
                        # codexloop event was dropped as "event_missing_type" --
                        # its whole entry in LOOP_EVENT_MAP was unreachable, and
                        # conformance failures downstream (no verdict, no
                        # completion) were really this one parse gap.
                        event_type = raw.get("event_type") or raw.get("kind") or raw.get("type")
                        if not event_type:
                            logger.warning(
                                "event_missing_type",
                                run_id=str(handle.run_id),
                                raw=raw,
                            )
                            continue

                        # Translate event_type to EventKind
                        kind = translate_event_type(self.descriptor.engine_id, event_type)
                        if kind is None:
                            logger.info(
                                "unknown_event_type",
                                engine=self.descriptor.engine_id.value,
                                event_type=event_type,
                                detail="skipping gracefully",
                            )
                            continue

                        # Parse timestamp
                        at_str = raw.get("at") or raw.get("timestamp") or raw.get("ts")
                        at = datetime.fromisoformat(at_str) if at_str else datetime.now(UTC)

                        # Enrich payload for verdict events with done_marker.
                        # agyloop's own "finished" event_type covers both
                        # success and failure (see application/runner.py),
                        # distinguished only by payload["success"] -- require
                        # it explicitly True rather than defaulting when
                        # absent, since other engines' verdict payloads use a
                        # different field ("complete", not "success") whose
                        # true/false state this code can't read here. A
                        # missing or falsy "success" must never enrich, or a
                        # failed run could report a false done_marker match.
                        # A flat event (codexloop's shape) is its own payload:
                        # success/complete/done_marker/usage live at the top
                        # level, so an empty dict here would discard exactly
                        # the fields every consumer downstream reads.
                        if "payload" in raw:
                            payload = dict(raw.get("payload", {}))
                        else:
                            payload = {
                                k: v
                                for k, v in raw.items()
                                if k not in {"event_type", "kind", "type", "at", "timestamp", "ts"}
                            }
                        if (
                            kind == EventKind.VERDICT_RENDERED
                            and "done_marker" not in payload
                            and payload.get("success") is True
                        ):
                            payload["done_marker"] = self.descriptor.done_marker
                        # Normalize the completion key: claudeloop/agyloop
                        # verdict payloads say {"success": bool} while every
                        # vibey consumer (run_and_record, the brief builder)
                        # reads {"complete": bool}. Caught live: a real
                        # claudeloop run finished its item, rendered
                        # success=true, and the handler still failed it as
                        # "did not report completion".
                        if (
                            kind == EventKind.VERDICT_RENDERED
                            and "complete" not in payload
                            and "success" in payload
                        ):
                            payload["complete"] = payload.get("success") is True

                        # Yield translated event
                        yield EngineEvent(
                            kind=kind.value,  # EventKind enum value
                            at=at,
                            payload=payload,
                        )
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning(
                            "event_parse_failed",
                            run_id=str(handle.run_id),
                            line=line[:200],
                            error=str(e),
                        )
                        continue

                seen_lines = len(lines)

                # Check if done via meta.json's own status field. Every loop
                # engine's RunMeta documents the same terminal vocabulary
                # (active | stopped | finished | failed) -- none of the four
                # ever write the literal "complete". Checking for that
                # non-existent value meant this loop never broke on its own
                # for any real engine and ran until the read raised (or, if
                # nothing ever raised, forever).
                meta_path = handle.run_dir / "meta.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text())
                    if meta.get("status") in ("finished", "failed", "stopped"):
                        break

                # A well-behaved engine always writes a terminal status
                # before its process exits. A crash, an early validation
                # failure (confirmed real: codexloop exits immediately with
                # "work plan has no checkbox items" and never touches
                # meta.json's status field), or an unhandled signal means
                # nothing will ever flip that status -- without this check
                # the loop above spins forever, exactly the failure mode its
                # own comment already warned about. Give one extra poll
                # interval after first observing the exit, in case the
                # terminal status write and process exit are racing each
                # other, then give up rather than hang indefinitely.
                process = _active_processes.get(handle.run_id)
                if process is not None and process.returncode is not None:
                    now = asyncio.get_running_loop().time()
                    if process_exited_without_status_since is None:
                        process_exited_without_status_since = now
                    elif now - process_exited_without_status_since > 1.0:
                        logger.warning(
                            "process_exited_without_terminal_status",
                            run_id=str(handle.run_id),
                            returncode=process.returncode,
                        )
                        break
                else:
                    process_exited_without_status_since = None

                await asyncio.sleep(0.5)  # Poll interval
            except Exception as e:
                logger.error(
                    "tail_error",
                    run_id=str(handle.run_id),
                    error=str(e),
                )
                break

    async def send_prompt(self, handle: RunHandle, text: str, *, now: bool) -> None:
        """Write prompt to inbox/ directory for mid-run prompting."""
        inbox = handle.run_dir / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        command = "prompt-now" if now else "prompt-at-break"
        prompt_file = inbox / f"{ts}-{command}.json"

        prompt_file.write_text(
            json.dumps(
                {
                    "command": command,
                    "text": text,
                }
            )
        )

        logger.info(
            "prompt_sent",
            run_id=str(handle.run_id),
            now=now,
            file=str(prompt_file),
        )

    def run_exit_code(self, handle: RunHandle) -> int | None:
        """Optional capability (discovered via ``hasattr``): the spawned
        process's exit code, or None while it still runs or once ``stop``
        has released the process reference. Read it after ``tail`` drains
        and before ``stop`` -- EXIT_CODE_WIND_DOWN here is the wind-down
        handoff signal."""
        process = _active_processes.get(handle.run_id)
        return None if process is None else process.returncode

    def diagnostic_tail(self, handle: RunHandle) -> str:
        """Return the child output retained for failure attribution.

        The application owns the policy for classifying this text; this adapter only
        preserves it across a process that exits before writing a structured event.
        """
        parts: list[str] = []
        for label, index in (("stderr", 1), ("stdout", 0)):
            files = _diagnostic_files.get(handle.run_id)
            if files is None:
                continue
            file = files[index]
            path = Path(file.name)
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    parts.append(f"[{label}] {text}")
        return "\n".join(parts)[-8_000:]

    def release_diagnostics(self, handle: RunHandle) -> None:
        """Close and forget the retained child-output handles after it is consumed."""
        files = _diagnostic_files.pop(handle.run_id, None)
        if files is not None:
            for file in files:
                file.close()

    async def stop(self, handle: RunHandle) -> StopSummary:
        """Send stop signal and collect stop-summary.md."""
        # Write stop signal to inbox
        inbox = handle.run_dir / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        stop_file = inbox / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}-stop.json"
        stop_file.write_text(json.dumps({"command": "stop"}))

        # Wait for stop-summary.md (with timeout)
        summary_path = handle.run_dir / "stop-summary.md"
        for _ in range(60):  # 30 seconds max
            if summary_path.exists() and summary_path.stat().st_size > 0:
                break
            await asyncio.sleep(0.5)

        summary = ""
        complete = False
        remaining_work: list[str] = []

        if summary_path.exists():
            summary = summary_path.read_text()
            # Look for done marker in summary
            complete = self.descriptor.done_marker in summary

        # Try to get remaining work from final snapshot
        snapshot_ref = await self.snapshot(handle)
        if snapshot_ref and snapshot_ref.path.exists():
            try:
                snapshot_data = json.loads(snapshot_ref.path.read_text())
                remaining_work = snapshot_data.get("remaining_work", [])
            except Exception:  # noqa: BLE001  # nosec B110
                logger.debug("snapshot_remaining_work_failed", run_id=str(handle.run_id))

        # Clean up the process reference
        self.release_diagnostics(handle)
        process = _active_processes.pop(handle.run_id, None)
        if process is not None:
            if process.returncode is None:
                try:
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except TimeoutError:
                    try:
                        process.terminate()
                        await asyncio.wait_for(process.wait(), timeout=1.0)
                    # The process is already removed from the registry; termination is best-effort.
                    except Exception:  # noqa: BLE001  # nosec B110
                        pass
            else:
                await process.wait()

        return StopSummary(
            run_id=handle.run_id,
            complete=complete,
            summary=summary or f"Stopped run {handle.run_id}",
            remaining_work=tuple(remaining_work),
        )

    async def snapshot(self, handle: RunHandle) -> SnapshotRef | None:
        """Read snapshots/latest.json."""
        snapshot_path = handle.run_dir / "snapshots" / "latest.json"
        if not snapshot_path.exists():
            return None

        try:
            data = json.loads(snapshot_path.read_text())
            return SnapshotRef(
                path=snapshot_path,
                schema_version=data.get("schema_version", 1),
                session_id=data.get("session_id"),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "snapshot_parse_failed",
                run_id=str(handle.run_id),
                error=str(e),
            )
            return None

    def classify(self, raw: Mapping[str, object]) -> CapacityState:
        """Classify capacity state using existing classify.py."""
        return classify_capacity(self.descriptor.engine_id, raw)

    def attribute(self, exit_code: int, tail: str) -> FailureClass:
        """Attribute failure class using existing classify.py."""
        return attribute_failure(exit_code, tail)


__all__ = ["LoopProcessAdapter", "EXIT_CODE_WIND_DOWN"]
