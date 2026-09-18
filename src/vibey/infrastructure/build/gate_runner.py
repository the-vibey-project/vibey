# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs build.verify's gate commands (and its `git diff`), build.integrate's
integration gates and REVIEW's automated checks as real subprocesses in a
work item's worktree. No shell=True: commands are already split into argv by
the caller, so there is no injection surface from a decomposer-produced
command string.

Three things hold for every command this runner executes (#212).

**It does not run in vibey's environment.** GIT_* is stripped unconditionally,
not just for the `git diff` call -- infrastructure/git/clean_env.py's docstring
explains why (GIT_DIR et al. leak in from a `git commit` hook and override
`-C`/`cwd` entirely), and a gate command can invoke git indirectly (a test that
shells out, a pre-commit hook inside the worktree). By default the
orchestrator's own Python environment goes too, through the same
`isolate_python_env` the engine spawn uses: left in place, a gate's bare
`pip install -e .` lands inside vibey's venv and its bare `python` or `pytest`
resolves to vibey's interpreter -- the venv-isolation leak from the greeter
campaign. `gates.isolate_python_env = false` opts out, for a project whose
gates really do rely on tools installed beside vibey.

**It is bounded.** Each command gets `gates.timeout_seconds` (30 minutes by
default). One that overruns is killed and reported as a failing gate, exit 124
(coreutils `timeout`'s convention), so the repair loop sees it -- not raised,
and not waited on: an unbounded `communicate()` held the job's lease for as
long as the command hung, with the heartbeat renewing it the whole time.

**It dies with everything it started.** The command leads a session of its
own and the kill goes to the whole process group, so a test server or a
`sleep` behind `sh -c` dies with it; a survivor would hold the output pipes
open and hang the next read exactly where the timed-out one hung. stdin is
/dev/null, so a command that prompts reads end-of-file instead of waiting on
the worker's stdin."""

import asyncio
import contextlib
import math
import os
import shlex
import signal
import sys
from collections.abc import Mapping
from pathlib import Path

import structlog

from vibey.application.build_verify_handler import GateResult
from vibey.infrastructure.engines.loop_process_adapter import isolate_python_env

logger = structlog.get_logger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 1800.0
"""Per command. Generous on purpose: a project's whole test suite is one gate
command, and a cap it can hit on a slow day turns a passing suite into a
failing gate. What matters is that there is a bound at all."""

_DEFAULT_KILL_GRACE_SECONDS = 5.0
"""How long to wait for a killed command to be reaped before giving up on it.
SIGKILL cannot be caught, so the command itself is gone in milliseconds; the
grace only ever runs out when something outside its process group still holds
its output pipes (see `_kill`)."""

_EXIT_TIMED_OUT = 124
_EXIT_COULD_NOT_START = 127


class SubprocessGateRunner:
    def __init__(
        self,
        *,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        kill_grace_seconds: float = _DEFAULT_KILL_GRACE_SECONDS,
        isolate_python_env: bool = True,
    ) -> None:
        self._timeout_seconds = self._positive("timeout_seconds", timeout_seconds)
        self._kill_grace_seconds = self._positive("kill_grace_seconds", kill_grace_seconds)
        self._isolate_python_env = isolate_python_env

    @classmethod
    def from_config(cls, config: Mapping[str, object]) -> "SubprocessGateRunner":
        """Build a runner from the project's stored config record.

        Read off the record's `gates` object the same way `review`,
        `max_cycle_dollars` and `skills_context` are. `vibey.toml` is never
        loaded at runtime, so it is not a route for this. A malformed object
        raises when the worker is built rather than silently running gates
        with defaults nobody asked for.
        """
        raw = config.get("gates")
        if raw is None:
            return cls()
        if not isinstance(raw, Mapping):
            raise ValueError("gates project config must be an object")
        isolate = raw.get("isolate_python_env", True)
        if not isinstance(isolate, bool):
            raise ValueError("gates.isolate_python_env must be a boolean")
        return cls(
            timeout_seconds=cls._seconds(raw, "timeout_seconds", _DEFAULT_TIMEOUT_SECONDS),
            kill_grace_seconds=cls._seconds(raw, "kill_grace_seconds", _DEFAULT_KILL_GRACE_SECONDS),
            isolate_python_env=isolate,
        )

    @classmethod
    def _seconds(cls, raw: Mapping[str, object], key: str, default: float) -> float:
        value = raw.get(key, default)
        # bool is an int subclass: without this, `true` would read as a
        # one-second timeout.
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"gates.{key} must be a number of seconds")
        return cls._positive(f"gates.{key}", value)

    @staticmethod
    def _positive(name: str, value: float) -> float:
        # Zero, a negative, NaN or infinity is not a bound: each one either
        # kills every command at once or never kills anything.
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a finite number of seconds greater than zero")
        return float(value)

    async def run(self, argv: tuple[str, ...], *, cwd: Path) -> GateResult:
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(cwd),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._environment(),
                start_new_session=True,
            )
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            # The gate COMMAND is broken (engine wrote `python` on a box
            # that only has `python3`, greeter4 live finding #3) -- that is
            # a failing gate for the repair loop to fix, not a vibey
            # infrastructure failure to retry into a dead job. 127 is the
            # shell's command-not-found convention.
            return GateResult(_EXIT_COULD_NOT_START, "", f"gate command could not start: {exc}")
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self._timeout_seconds
            )
        except TimeoutError:
            await self._kill(process)
            return GateResult(
                _EXIT_TIMED_OUT,
                "",
                f"gate command timed out after {self._timeout_seconds:g}s and was killed: "
                f"{shlex.join(argv)}",
            )
        except BaseException:
            # Cancelled (Ctrl-C on the worker, event-loop shutdown, any caller
            # that cancels the handler) or anything else: a gate never outlives
            # the task that ran it.
            await self._kill(process)
            raise
        return GateResult(
            process.returncode or 0,
            stdout.decode(errors="replace"),
            stderr.decode(errors="replace"),
        )

    def _environment(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        if not self._isolate_python_env:
            return env
        return isolate_python_env(
            env, venv_prefixes=(os.environ.get("VIRTUAL_ENV"), self._interpreter_venv())
        )

    @staticmethod
    def _interpreter_venv() -> str | None:
        # sys.prefix names a venv only when it differs from sys.base_prefix. On
        # an interpreter installed into the system it is `/usr`, and stripping
        # every PATH entry under it would take /usr/bin -- git, sh, and most
        # of what a gate runs -- with it.
        return sys.prefix if sys.prefix != sys.base_prefix else None

    async def _kill(self, process: asyncio.subprocess.Process) -> None:
        # ProcessLookupError: nothing is left in the group -- the command
        # exited on its own, and whatever still holds its pipes left the group
        # first. PermissionError: macOS refuses killpg on a group whose only
        # member is a zombie, which the command is between exiting and being
        # reaped. Either way there is nothing left to kill.
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signal.SIGKILL)
        try:
            await asyncio.wait_for(process.wait(), timeout=self._kill_grace_seconds)
        except TimeoutError:
            # A wait() that starts before the process exits resolves only once
            # every pipe has closed too (CPython 3.12). A descendant that
            # escaped into a session of its own and kept the command's stdout
            # would block it forever, though the command itself is long dead
            # -- and a worker blocked here is the hang this runner exists to
            # prevent. The child watcher still reaps the command; the escaped
            # descendant is outside any group vibey started.
            logger.warning(
                "gate_process_not_reaped",
                pid=process.pid,
                returncode=process.returncode,
                kill_grace_seconds=self._kill_grace_seconds,
            )
