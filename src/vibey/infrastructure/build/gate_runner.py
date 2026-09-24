# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs build.verify's gate commands (and its `git diff`), build.integrate's
integration gates and REVIEW's automated checks as real subprocesses in a
work item's worktree. No shell=True: commands are already split into argv by
the caller, so there is no injection surface from a decomposer-produced
command string.

Three things hold for every command this runner executes (#212).

**It does not run in vibey's environment.** A gate command is decomposer-produced
argv running engine-written code, so it starts from an allow-list, never a copy of
the worker's environment: the system basics (`SYSTEM_ENVIRONMENT`) plus whatever the
project declares in `gates.env_allow` (a trailing `*` names a prefix). vibey's own
variables -- `VIBEY_PG_URL`, the queue and ledger DSN, among them -- libpq's `PG*`
and git's `GIT_*` can never be declared: GIT_DIR et al. leak in from a `git commit`
hook and override `-C`/`cwd` entirely (infrastructure/git/clean_env.py), and a gate
command can invoke git indirectly. A project's own test database is another matter:
a gate may be given one, by declaring it. By default the orchestrator's own Python
environment is stripped too, through the same `ChildEnvironment` the engine spawn
uses: left in place, a gate's bare `pip install -e .` lands inside vibey's venv and
its bare `python` or `pytest` resolves to vibey's interpreter -- the venv-isolation
leak from the greeter campaign. `gates.isolate_python_env = false` opts out, for a
project whose gates really do rely on tools installed beside vibey.

**It is bounded.** Each command gets `gates.timeout_seconds` (30 minutes by
default). One that overruns is killed and reported as a failing gate, exit 124
(coreutils `timeout`'s convention), so the repair loop sees it -- not raised,
and not waited on: an unbounded `communicate()` held the job's lease for as
long as the command hung, with the heartbeat renewing it the whole time.

**It dies with everything it started.** The command leads a session of its
own and the kill goes to the whole process group, so a test server or a
`sleep` behind `sh -c` dies with it; a survivor would hold the output pipes
open and hang the next read exactly where the timed-out one hung. The kill and
the bounded reap after it are `infrastructure/process/reaper.py`'s, the one
implementation every subprocess call site shares (#283). stdin is /dev/null, so
a command that prompts reads end-of-file instead of waiting on the worker's
stdin."""

import asyncio
import math
import shlex
from collections.abc import Iterable, Mapping
from pathlib import Path

from vibey.application.build_verify_handler import GateResult
from vibey.infrastructure.process import (
    DEFAULT_KILL_GRACE_SECONDS,
    GATE_FORBIDDEN,
    SYSTEM_ENVIRONMENT,
    ChildEnvironment,
    EnvironmentAllowList,
    ProcessReaper,
)

_DEFAULT_TIMEOUT_SECONDS = 1800.0
"""Per command. Generous on purpose: a project's whole test suite is one gate
command, and a cap it can hit on a slow day turns a passing suite into a
failing gate. What matters is that there is a bound at all."""

_EXIT_TIMED_OUT = 124
_EXIT_COULD_NOT_START = 127


class SubprocessGateRunner:
    def __init__(
        self,
        *,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        kill_grace_seconds: float = DEFAULT_KILL_GRACE_SECONDS,
        isolate_python_env: bool = True,
        env_allow: Iterable[str] = (),
    ) -> None:
        self._timeout_seconds = self._positive("timeout_seconds", timeout_seconds)
        self._kill_grace_seconds = self._positive("kill_grace_seconds", kill_grace_seconds)
        self._isolate_python_env = isolate_python_env
        self._reaper = ProcessReaper(
            grace_seconds=self._kill_grace_seconds, event="gate_process_not_reaped"
        )
        self._allow = SYSTEM_ENVIRONMENT.extended(
            env_allow, forbidden=GATE_FORBIDDEN, where="gates.env_allow"
        )
        self._environment = ChildEnvironment(self._allow, isolate_python_env=isolate_python_env)

    @classmethod
    def from_config(cls, config: Mapping[str, object]) -> "SubprocessGateRunner":
        """Build a runner from the project's stored config record.

        Read off the record's `gates` object the same way `review`,
        `max_cycle_dollars` and `skills_context` are. The object is declared in
        vibey.toml's `[gates]` table (copied into the record by `vibey new`) or the
        `VibeyProject` spec's `gates`. A malformed object raises when the worker is
        built rather than silently running gates with defaults nobody asked for.
        """
        raw = config.get("gates")
        if raw is None:
            return cls()
        if not isinstance(raw, Mapping):
            raise ValueError("gates project config must be an object")
        isolate = raw.get("isolate_python_env", True)
        if not isinstance(isolate, bool):
            raise ValueError("gates.isolate_python_env must be a boolean")
        env_allow = EnvironmentAllowList.parse(
            raw.get("env_allow", []), where="gates.env_allow", forbidden=GATE_FORBIDDEN
        )
        return cls(
            timeout_seconds=cls._seconds(raw, "timeout_seconds", _DEFAULT_TIMEOUT_SECONDS),
            kill_grace_seconds=cls._seconds(raw, "kill_grace_seconds", DEFAULT_KILL_GRACE_SECONDS),
            isolate_python_env=isolate,
            env_allow=env_allow.entries(),
        )

    @property
    def allow_list(self) -> EnvironmentAllowList:
        """Exactly what a gate command may receive of the worker's environment."""
        return self._allow

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
                env=self._environment.build(),
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
            await self._reaper.kill_and_reap(process)
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
            await self._reaper.kill_and_reap(process)
            raise
        return GateResult(
            process.returncode or 0,
            stdout.decode(errors="replace"),
            stderr.decode(errors="replace"),
        )
