# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sovereign heartbeat's timer, stood up from the tree (sub-doctrine 12.c, ADR-0059).

The heartbeat used to be published by `vibey-local-authority`, a LaunchAgent that lived in one
operator's home directory, written by hand and recorded nowhere: nothing in the repository
could say it existed, restore it, or notice it had stopped. It is retired. This is the timer
declared: rendered from `[runners]` and `[pr_automation.fallback]` and the templates beside
the runner's, installed, checked and removed by the same command family.

- **launchd on macOS, a systemd user timer on Linux** (Ubuntu LTS is first-class, #1116).
  `[runners] heartbeat_scheduler` picks one explicitly; empty picks by platform.
- **The interval is at most half the gate's trust window** (`heartbeat_max_age_minutes`), so
  one missed beat never stales the lane. `heartbeat_interval_minutes` = 0 takes exactly half.
- **Nothing it runs lives somewhere that disappears.** The interpreter, the `vibey_gh` it
  imports, and the log must not sit under a temporary directory -- a reboot wipes those -- or
  inside a git work tree -- a lane's worktree is deleted when the lane ends, and a checkout's
  virtualenv changes under every `uv sync`. The checkout it pushes from must be a main clone,
  not a linked worktree. Each is refused at render time, with the reason.
- **Nothing is loaded or unloaded unasked**, as with the runner: `install` writes files and
  touches the service manager only with `load=True`; `uninstall` only says what it would do
  until `apply=True`, and moves a unit aside into `<install_dir>/retired-units/` rather than
  deleting it.
- **Status reads the last beat's own record**: `sovereign --beat --record` writes what it did
  -- published or withheld, and why -- and `status` reports its age and result.
"""

from __future__ import annotations

import json
import os
import plistlib
import shlex
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from vibey_gh.config import GhConfig
from vibey_gh.interfaces.heartbeat_timer_interface import (
    HeartbeatPlanInterface,
    HeartbeatTimerInterface,
)
from vibey_gh.sovereign_runner import RETIRED_DIR, TEMPLATES, RunnerFile, SovereignRunner

__all__ = ["BeatRecord", "HeartbeatPlan", "HeartbeatTimer"]

ServiceManager = Callable[[tuple[str, ...]], tuple[int, str]]
ModuleOrigin = Callable[[str, Path], str | None]

LAUNCHD, SYSTEMD = "launchd", "systemd"
# The Linux default for the log and the beat record, when `heartbeat_log_dir` is empty. On
# macOS it is `[runners] log_dir`, which is `~/Library/Logs` by default.
_LINUX_STATE_DIR = "~/.local/state/vibey-gh"


@dataclass(frozen=True)
class BeatRecord:
    """What one `sovereign --beat` did: when, whether it published, and why."""

    at: float
    published: bool
    reason: str

    def write(self, path: Path) -> None:
        """Atomically: a status read never sees half a record."""
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(f".{path.name}.partial")
        body = {"at": self.at, "published": self.published, "reason": self.reason}
        partial.write_text(json.dumps(body) + "\n", encoding="utf-8")
        os.replace(partial, path)

    @classmethod
    def read(cls, path: Path) -> BeatRecord | None:
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
            return cls(float(body["at"]), bool(body["published"]), str(body["reason"]))
        except (OSError, ValueError, KeyError, TypeError):
            return None


@dataclass(frozen=True)
class HeartbeatPlan:
    """Everything one heartbeat install writes, and what it runs."""

    label: str
    scheduler: str
    repository: str
    python: str
    checkout: Path
    log: Path
    record: Path
    interval_minutes: int
    files: tuple[RunnerFile, ...]


class HeartbeatTimer(HeartbeatTimerInterface):
    """Renders, installs, reports on and removes the heartbeat timer the tree declares."""

    def __init__(
        self,
        cfg: GhConfig,
        *,
        home: Path,
        uid: int,
        platform: str | None = None,
        python: str | None = None,
        templates: Path | None = None,
        service: ServiceManager | None = None,
        origin: ModuleOrigin | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._cfg = cfg
        self._runners = cfg.runners
        self._fallback = cfg.pr_automation.fallback
        self._home = home
        self._uid = uid
        self._platform = platform if platform is not None else sys.platform
        self._python = python if python is not None else sys.executable
        self._templates = templates or TEMPLATES
        self._service = service or self._run
        self._origin = origin or self._module_origin
        self._clock = clock or time.time

    # --- paths and names ------------------------------------------------------------------

    def _expand(self, declared: str) -> Path:
        return self._home / declared[2:] if declared.startswith("~/") else Path(declared)

    def _scheduler(self) -> tuple[str, str]:
        declared = self._runners.heartbeat_scheduler
        if declared:
            return declared, ""
        if self._platform == "darwin":
            return LAUNCHD, ""
        if self._platform.startswith("linux"):
            return SYSTEMD, ""
        return "", (
            "the heartbeat timer is a launchd agent (macOS) or a systemd user timer (Linux);"
            f" this platform is {self._platform}: set [runners] heartbeat_scheduler"
        )

    def _log_dir(self, scheduler: str) -> Path:
        declared = self._runners.heartbeat_log_dir
        if not declared:
            declared = self._runners.log_dir if scheduler == LAUNCHD else _LINUX_STATE_DIR
        return self._expand(declared)

    def _units(self, label: str, scheduler: str) -> tuple[Path, ...]:
        if scheduler == LAUNCHD:
            return (self._expand(self._runners.launch_agents_dir) / f"{label}.plist",)
        units = self._expand(self._runners.systemd_user_dir)
        return (units / f"{label}.service", units / f"{label}.timer")

    def _names(self) -> tuple[str, str, str, str]:
        """(label, scheduler, owner/name, problem): what `uninstall` and `status` need, which
        is everything but the interpreter."""
        if not self._fallback.enabled:
            return (
                "",
                "",
                "",
                (
                    "[pr_automation.fallback] is disabled, so no workflow schedules the sovereign"
                    " lane and nothing reads a heartbeat; enable it before installing a timer"
                ),
            )
        slug, _url, problem = self._runners.registration(self._cfg.platform)
        if problem:
            return "", "", "", problem
        scheduler, problem = self._scheduler()
        if problem:
            return "", "", "", problem
        return SovereignRunner.heartbeat_label(self._runners.unit_prefix, slug), scheduler, slug, ""

    def interval_minutes(self) -> tuple[int, str]:
        """(minutes between beats, problem). At most half the trust window, at least one."""
        window = self._fallback.heartbeat_max_age_minutes
        interval = self._runners.heartbeat_interval_minutes or window // 2
        if interval < 1 or interval * 2 > window:
            return 0, (
                f"a heartbeat every {interval}m cannot keep a {window}m trust window"
                " ([pr_automation.fallback] heartbeat_max_age_minutes) fresh through one missed"
                " beat: the interval must be at least 1 and at most half the window"
            )
        return interval, ""

    # --- where things may live ------------------------------------------------------------

    @staticmethod
    def temp_roots() -> tuple[Path, ...]:
        """Directories a reboot or the system empties. A method so a test on a machine whose
        own temporary directory holds the test tree can say so."""
        roots = [
            tempfile.gettempdir(),
            "/tmp",
            "/var/tmp",
            "/private/tmp",
            "/private/var/tmp",
            "/var/folders",
            "/private/var/folders",
            "/dev/shm",
            "/run/user",
        ]
        return tuple(Path(os.path.realpath(root)) for root in roots)

    def _placement(self, what: str, path: Path) -> str:
        """Why `path` is no place for something a timer runs every few minutes, or ""."""
        for candidate in {path, Path(os.path.realpath(path))}:
            for root in self.temp_roots():
                if candidate == root or root in candidate.parents:
                    return (
                        f"{what} {path} is under the temporary directory {root}, which a"
                        " reboot empties"
                    )
            for parent in (candidate, *candidate.parents):
                if (parent / ".git").exists():
                    return (
                        f"{what} {path} is inside the git work tree {parent}, which a lane"
                        " deletes or a sync rewrites; install vibey-gh outside any checkout"
                        " (for example `uv tool install vibey`) or set [runners]"
                        " heartbeat_python"
                    )
        return ""

    # --- rendering ------------------------------------------------------------------------

    def render(self, python: str | None = None) -> tuple[HeartbeatPlan | None, str]:
        label, scheduler, slug, problem = self._names()
        if problem:
            return None, problem
        interval, problem = self.interval_minutes()
        if problem:
            return None, problem
        checkout = self._cfg.root
        if not (checkout / ".git").is_dir():
            return None, (
                f"{checkout} is not a main clone ({checkout / '.git'} is not a directory): a"
                " linked worktree is deleted when its lane ends, so install the timer from the"
                " repository's main checkout"
            )
        declared = self._runners.heartbeat_python
        interpreter = python or (str(self._expand(declared)) if declared else self._python)
        if not os.path.isabs(interpreter):
            return None, f"the heartbeat interpreter must be an absolute path: {interpreter!r}"
        problem = self._placement("the heartbeat interpreter", Path(interpreter))
        if problem:
            return None, problem
        origin = self._origin(interpreter, checkout)
        if not origin:
            return None, f"{interpreter} cannot import vibey_gh; install vibey into it first"
        problem = self._placement("the vibey_gh it runs", Path(origin))
        if problem:
            return None, problem
        log_dir = self._log_dir(scheduler)
        problem = self._placement("the heartbeat log directory", log_dir)
        if problem:
            return None, problem
        log, record = log_dir / f"{label}.log", log_dir / f"{label}.last.json"
        argv = (interpreter, "-m", "vibey_gh.cli", "sovereign", "--beat", "--record", str(record))
        files: tuple[RunnerFile, ...]
        if scheduler == LAUNCHD:
            files = (self._launchd(label, argv, checkout, log, interval),)
        else:
            files = self._systemd(label, slug, argv, checkout, log, interval)
        return (
            HeartbeatPlan(
                label, scheduler, slug, interpreter, checkout, log, record, interval, files
            ),
            "",
        )

    def _read(self, name: str) -> str:
        return (self._templates / name).read_text(encoding="utf-8")

    def _launchd(
        self, label: str, argv: Sequence[str], checkout: Path, log: Path, interval: int
    ) -> RunnerFile:
        values = {
            "__LABEL__": label,
            "__PYTHON__": argv[0],
            "__RECORD__": argv[-1],
            "__CHECKOUT__": str(checkout),
            "__PATH__": self._runners.path,
            "__INTERVAL_SECONDS__": str(interval * 60),
            "__LOG__": str(log),
        }
        text = self._read("heartbeat-agent.plist")
        for placeholder, value in values.items():
            text = text.replace(placeholder, escape(value))
        return RunnerFile(self._units(label, LAUNCHD)[0], text)

    def _systemd(
        self,
        label: str,
        slug: str,
        argv: Sequence[str],
        checkout: Path,
        log: Path,
        interval: int,
    ) -> tuple[RunnerFile, ...]:
        service_path, timer_path = self._units(label, SYSTEMD)
        service = self._read("heartbeat.service")
        for placeholder, value in {
            "__REPOSITORY__": self._unit_text(slug),
            "__CHECKOUT__": self._unit_text(str(checkout)),
            "__PATH_ASSIGNMENT__": self._unit_word(f"PATH={self._runners.path}"),
            "__EXEC_START__": " ".join(self._unit_word(arg) for arg in argv),
            "__LOG__": self._unit_text(str(log)),
        }.items():
            service = service.replace(placeholder, value)
        timer = self._read("heartbeat.timer")
        for placeholder, value in {
            "__REPOSITORY__": self._unit_text(slug),
            "__INTERVAL_MINUTES__": str(interval),
            "__LABEL__": label,
        }.items():
            timer = timer.replace(placeholder, value)
        return RunnerFile(service_path, service), RunnerFile(timer_path, timer)

    @staticmethod
    def _unit_text(value: str) -> str:
        """A value systemd reads verbatim but expands specifiers in: `%` is doubled."""
        return value.replace("%", "%%")

    @classmethod
    def _unit_word(cls, value: str) -> str:
        """One argument of an `ExecStart=` or `Environment=` line, quoted so a space, a
        quote, a backslash, a `$` or a `%` in a path stays part of that one argument."""
        quoted = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "$$")
        return f'"{cls._unit_text(quoted)}"'

    # --- install, status, uninstall -------------------------------------------------------

    def install(self, plan: HeartbeatPlanInterface, *, load: bool) -> tuple[list[str], bool]:
        lines = []
        plan.log.parent.mkdir(parents=True, exist_ok=True)
        for rendered in plan.files:
            rendered.path.parent.mkdir(parents=True, exist_ok=True)
            rendered.path.write_text(rendered.text, encoding="utf-8")
            rendered.path.chmod(0o644)
            lines.append(f"wrote {rendered.path}")
        if not load:
            return lines, True
        for argv in self._load_commands(plan):
            code, output = self._service(argv)
            if code != 0 and argv[1] != "bootout":
                lines.append(f"{' '.join(argv[:2])} failed (exit {code}): {output}")
                return lines, False
        lines.append(f"loaded {plan.label}: a beat every {plan.interval_minutes}m")
        return lines, True

    def _load_commands(self, plan: HeartbeatPlanInterface) -> list[tuple[str, ...]]:
        if plan.scheduler == LAUNCHD:
            target = f"gui/{self._uid}"
            # Unloading first makes a re-install pick up the new plist; "not loaded" is the
            # expected answer on a first install, so its status is not a failure.
            return [
                ("launchctl", "bootout", f"{target}/{plan.label}"),
                ("launchctl", "bootstrap", target, str(plan.files[0].path)),
            ]
        return [
            ("systemctl", "--user", "daemon-reload"),
            ("systemctl", "--user", "enable", "--now", f"{plan.label}.timer"),
        ]

    def next_steps(self, plan: HeartbeatPlanInterface) -> list[str]:
        """The commands that load what `install` wrote, every path quoted for the shell."""
        q = shlex.quote
        if plan.scheduler == LAUNCHD:
            target = f"gui/{self._uid}"
            unit = q(str(plan.files[0].path))
            return [
                (
                    f"launchctl bootout {q(f'{target}/{plan.label}')} 2>/dev/null;"
                    f" launchctl bootstrap {target} {unit}"
                ),
                "vibey-gh heartbeat status",
            ]
        return [
            "systemctl --user daemon-reload",
            f"systemctl --user enable --now {q(plan.label + '.timer')}",
            'loginctl enable-linger "$USER"   # keep user timers running without a session',
            "vibey-gh heartbeat status",
        ]

    def status(self) -> tuple[list[str], bool]:
        label, scheduler, _slug, problem = self._names()
        if problem:
            return [problem], False
        lines: list[str] = []
        healthy = True
        units = self._units(label, scheduler)
        missing = [unit for unit in units if not unit.is_file()]
        for unit in missing:
            lines.append(f"missing: {unit}")
            healthy = False
        if not missing:
            python = self._installed_python(units[0], scheduler)
            plan, problem = self.render(python=python)
            if plan is None:
                lines.append(f"cannot render what should be installed: {problem}")
                healthy = False
            else:
                for rendered in plan.files:
                    if rendered.path.read_text(encoding="utf-8") != rendered.text:
                        lines.append(f"drift: {rendered.path}")
                        healthy = False
            loaded = self._loaded(label, scheduler)
            lines.append(f"{label}: {'loaded' if loaded else 'not loaded'} ({scheduler})")
            healthy = healthy and loaded
        record = BeatRecord.read(self._log_dir(scheduler) / f"{label}.last.json")
        if record is None:
            lines.append("last beat: none recorded")
            return lines, False
        age = int(self._clock() - record.at)
        outcome = "published" if record.published else "withheld"
        lines.append(f"last beat: {age // 60}m{age % 60:02d}s ago, {outcome}: {record.reason}")
        window = self._fallback.heartbeat_max_age_minutes
        if age > window * 60:
            lines.append(f"the last beat is older than the {window}m window the gate trusts")
            healthy = False
        return lines, healthy and record.published

    def _installed_python(self, unit: Path, scheduler: str) -> str | None:
        """The interpreter the installed unit runs, so drift is judged against what is on the
        host rather than against whichever interpreter happens to run `status`."""
        try:
            if scheduler == LAUNCHD:
                body = plistlib.loads(unit.read_bytes())
                return str(body["ProgramArguments"][0])
            for line in unit.read_text(encoding="utf-8").splitlines():
                if line.startswith("ExecStart="):
                    first = shlex.split(line.removeprefix("ExecStart="))[0]
                    return first.replace("$$", "$").replace("%%", "%")
        except (
            OSError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            plistlib.InvalidFileException,
        ):
            return None
        return None

    def _loaded(self, label: str, scheduler: str) -> bool:
        if scheduler == LAUNCHD:
            argv: tuple[str, ...] = ("launchctl", "print", f"gui/{self._uid}/{label}")
        else:
            argv = ("systemctl", "--user", "is-active", "--quiet", f"{label}.timer")
        return self._service(argv)[0] == 0

    def uninstall(self, *, apply: bool) -> list[str]:
        label, scheduler, _slug, problem = self._names()
        if problem:
            return [problem]
        units = [unit for unit in self._units(label, scheduler) if unit.is_file()]
        if not units:
            return ["no heartbeat timer is installed"]
        if scheduler == LAUNCHD:
            unload: list[tuple[str, ...]] = [("launchctl", "bootout", f"gui/{self._uid}/{label}")]
        else:
            unload = [("systemctl", "--user", "disable", "--now", f"{label}.timer")]
        retired = self._expand(self._runners.install_dir) / RETIRED_DIR
        lines = []
        for argv in unload:
            if not apply:
                lines.append(f"would run: {' '.join(argv)}")
                continue
            code, output = self._service(argv)
            lines.append(f"unloaded {label}" if code == 0 else f"{label} was not loaded ({output})")
        for unit in units:
            target = SovereignRunner.free_name(retired, unit)
            if not apply:
                lines.append(f"would move {unit} to {target}")
                continue
            retired.mkdir(parents=True, exist_ok=True)
            os.rename(unit, target)
            lines.append(f"moved {unit} to {target}")
        if apply and scheduler == SYSTEMD:
            self._service(("systemctl", "--user", "daemon-reload"))
        return lines

    # --- the default seams ----------------------------------------------------------------

    @staticmethod
    def _run(argv: tuple[str, ...]) -> tuple[int, str]:
        try:
            done = subprocess.run(  # nosec B603 - a fixed argv, never a shell
                argv, capture_output=True, text=True, check=False, timeout=60
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 127, str(exc)
        return done.returncode, (done.stdout + done.stderr).strip()

    @staticmethod
    def _module_origin(python: str, checkout: Path) -> str | None:
        """Where `python` imports vibey_gh from, asked of that interpreter exactly as the
        timer will run it: from the checkout, with the checkout kept off sys.path."""
        probe = "import os, vibey_gh; print(os.path.dirname(os.path.abspath(vibey_gh.__file__)))"
        env = {**os.environ, "PYTHONSAFEPATH": "1"}
        env.pop("PYTHONPATH", None)
        try:
            done = subprocess.run(  # nosec B603 - a fixed argv, never a shell
                [python, "-c", probe],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
                cwd=checkout,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        origin = done.stdout.strip()
        return origin if done.returncode == 0 and origin else None
