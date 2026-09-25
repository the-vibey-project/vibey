# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sovereign heartbeat's timer, stood up from the tree (sub-doctrine 12.c, ADR-0060).

The heartbeat used to be published by `vibey-local-authority`, a LaunchAgent that lived in one
operator's home directory, written by hand and recorded nowhere: nothing in the repository
could say it existed, restore it, or notice it had stopped. It is retired. This is the timer
declared: rendered from `[runners]` and `[pr_automation.fallback]` and the templates beside
the runner's, installed, checked and removed by the same command family.

- **It pushes from a repository of its own** (`vibey_gh.heartbeat_clone`): a clone with no
  working tree, the repository's remote, the runner's own credential, and a pre-push gate
  rendered here that asks the timer's own interpreter for its scope decision. Never the
  operator's checkout, whose hook is whatever the branch checked out there happens to carry.
  `install` creates or repairs it, and hands its gate a synthetic heartbeat before anything
  is scheduled; `status` does the same every time it is asked.
- **launchd on macOS, a systemd user timer on Linux** (Ubuntu LTS is first-class, #1116).
  `[runners] heartbeat_scheduler` picks one explicitly; empty picks by platform.
- **The interval is at most half the gate's trust window** (`heartbeat_max_age_minutes`), so
  one missed beat never stales the lane. `heartbeat_interval_minutes` = 0 takes exactly half.
- **Nothing it runs lives somewhere that disappears** (10.h). The interpreter, the
  `vibey_gh` it imports, the log and the clone must not sit under a temporary directory -- a
  reboot empties those -- or inside a git work tree -- a lane's worktree is deleted when the
  lane ends, and a checkout's virtualenv changes under every `uv sync`. Each is refused at
  render time, naming the key that moves it.
- **Nothing is loaded or unloaded unasked**, as with the runner: `install` writes files and
  touches the service manager only with `load=True`; `uninstall` only says what it would do
  until `apply=True`, and moves units and the clone aside into
  `<install_dir>/retired-units/` rather than deleting them.
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

from vibey_gh.config import CONFIG_NAME, GhConfig
from vibey_gh.heartbeat_clone import HOOK_TEMPLATE, GitCommand, HeartbeatClone, HookRunner
from vibey_gh.interfaces.heartbeat_timer_interface import (
    HeartbeatPlanInterface,
    HeartbeatTimerInterface,
)
from vibey_gh.interfaces.sovereign_runner_interface import RunnerFileInterface
from vibey_gh.push_scope import NO_CODE
from vibey_gh.sovereign_runner import RETIRED_DIR, TEMPLATES, RunnerFile, SovereignRunner

__all__ = ["BeatRecord", "HeartbeatPlan", "HeartbeatTimer"]

ServiceManager = Callable[[tuple[str, ...]], tuple[int, str]]
ModuleOrigin = Callable[[str, Path], str | None]

LAUNCHD, SYSTEMD = "launchd", "systemd"
# The Linux default for the log and the beat record, when `heartbeat_log_dir` is empty. On
# macOS it is `[runners] log_dir`, which is `~/Library/Logs` by default.
_LINUX_STATE_DIR = "~/.local/state/vibey-gh"
# What each placement refusal tells the operator to change, by the key that moves it (10.h).
_MOVE_IT = {
    "heartbeat_python": (
        "install vibey-gh outside any checkout (`uv tool install vibey` puts it where the"
        " default [runners] heartbeat_python looks) or set [runners] heartbeat_python"
    ),
    "heartbeat_log_dir": "set [runners] heartbeat_log_dir somewhere durable",
    "heartbeat_clone_dir": "set [runners] heartbeat_clone_dir somewhere durable",
}
_ENABLE_LINGER = 'loginctl enable-linger "$USER"'


@dataclass(frozen=True)
class BeatRecord:
    """What one `sovereign --beat` did: when, whether it published, and why. Satisfies
    `BeatRecordInterface` by shape: a frozen dataclass cannot inherit the protocol's
    read-only properties."""

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
    remote_url: str
    python: str
    clone: Path
    log: Path
    record: Path
    interval_minutes: int
    files: tuple[RunnerFile, ...]


class HeartbeatTimer(HeartbeatTimerInterface):
    """Renders, installs, reports on and removes the heartbeat timer the tree declares.

    `service` runs launchctl, systemctl and loginctl; `origin` asks an interpreter where it
    imports vibey_gh from; `git` and `hook` are the clone's seams (`HeartbeatClone`).
    """

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
        git: GitCommand | None = None,
        hook: HookRunner | None = None,
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
        self._git = git
        self._hook = hook

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

    def _clone_path(self, repository: str) -> Path:
        declared = self._runners.heartbeat_clone_dir
        if declared:
            return self._expand(declared)
        name = repository.split("/")[1]
        return self._expand(self._runners.install_dir) / f"heartbeat-{name}"

    def _names(self) -> tuple[str, str, str, str, str]:
        """(label, scheduler, owner/name, remote URL, problem): what every action needs."""
        if not self._fallback.enabled:
            return (
                "",
                "",
                "",
                "",
                (
                    "[pr_automation.fallback] is disabled, so no workflow schedules the sovereign"
                    " lane and nothing reads a heartbeat; enable it before installing a timer"
                ),
            )
        slug, url, problem = self._runners.registration(self._cfg.platform)
        if problem:
            return "", "", "", "", problem
        scheduler, problem = self._scheduler()
        if problem:
            return "", "", "", "", problem
        label = SovereignRunner.heartbeat_label(self._runners.unit_prefix, slug)
        return label, scheduler, slug, url, ""

    def clone_dir(self) -> tuple[Path | None, str]:
        """(the heartbeat's own repository, problem): where `sovereign --beat` pushes from."""
        slug, _url, problem = self._runners.registration(self._cfg.platform)
        if problem:
            return None, problem
        return self._clone_path(slug), ""

    def _clone(self, path: Path, remote_url: str) -> HeartbeatClone:
        return HeartbeatClone(
            path,
            remote_url=remote_url,
            gh_config_dir=self._expand(self._runners.gh_config_dir),
            heartbeat_ref=self._fallback.heartbeat_ref,
            path_env=self._runners.path,
            git=self._git,
            hook=self._hook,
        )

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
        """Directories a reboot or the system empties, resolved and sorted, so a refusal
        names the same root on every run. A method so a test on a machine whose own
        temporary directory holds the test tree can say so."""
        roots = (
            tempfile.gettempdir(),
            "/tmp",
            "/var/tmp",
            "/private/tmp",
            "/private/var/tmp",
            "/var/folders",
            "/private/var/folders",
            "/dev/shm",
            "/run/user",
        )
        return tuple(sorted({Path(os.path.realpath(root)) for root in roots}))

    def _placement(self, what: str, path: Path, key: str, *, own_repository: bool = False) -> str:
        """Why `path` is no place for something a timer runs every few minutes, or "".

        `own_repository` is for the clone, which IS a git repository: only the directories
        above it must not be a work tree."""
        for candidate in dict.fromkeys((path, Path(os.path.realpath(path)))):
            for root in self.temp_roots():
                if candidate == root or root in candidate.parents:
                    return (
                        f"{what} {path} is under the temporary directory {root}, which a"
                        f" reboot empties: {_MOVE_IT[key]}"
                    )
            above = tuple(candidate.parents) if own_repository else (candidate, *candidate.parents)
            for parent in above:
                if (parent / ".git").exists():
                    return (
                        f"{what} {path} is inside the git work tree {parent}, which a lane"
                        f" deletes or a sync rewrites: {_MOVE_IT[key]}"
                    )
        return ""

    # --- rendering ------------------------------------------------------------------------

    def render(self, python: str | None = None) -> tuple[HeartbeatPlan | None, str]:
        label, scheduler, slug, url, problem = self._names()
        if problem:
            return None, problem
        interval, problem = self.interval_minutes()
        if problem:
            return None, problem
        clone = self._clone(self._clone_path(slug), url)
        problem = self._placement(
            "the heartbeat's clone", clone.path, "heartbeat_clone_dir", own_repository=True
        )
        if problem:
            return None, problem
        source = self._cfg.root / CONFIG_NAME
        if not source.is_file():
            return None, f"{source} does not exist, so there is no declared lane to give the clone"
        declared = self._runners.heartbeat_python
        interpreter = python or (str(self._expand(declared)) if declared else self._python)
        if not os.path.isabs(interpreter):
            return None, f"the heartbeat interpreter must be an absolute path: {interpreter!r}"
        problem = self._placement(
            "the heartbeat interpreter", Path(interpreter), "heartbeat_python"
        )
        if problem:
            return None, problem
        origin = self._origin(interpreter, self._home)
        if not origin:
            return None, (
                f"{interpreter} cannot import vibey_gh; install vibey into it first (for"
                " example `uv tool install --force --from . vibey`)"
            )
        problem = self._placement("the vibey_gh it runs", Path(origin), "heartbeat_python")
        if problem:
            return None, problem
        log_dir = self._log_dir(scheduler)
        problem = self._placement("the heartbeat log directory", log_dir, "heartbeat_log_dir")
        if problem:
            return None, problem
        log, record = log_dir / f"{label}.log", log_dir / f"{label}.last.json"
        argv = (interpreter, "-m", "vibey_gh.cli", "sovereign", "--beat", "--record", str(record))
        hook = self._read(HOOK_TEMPLATE).replace("__PYTHON__", shlex.quote(interpreter))
        files: tuple[RunnerFile, ...] = (
            RunnerFile(clone.hook_path, hook, True),
            RunnerFile(clone.config_path, source.read_text(encoding="utf-8")),
        )
        if scheduler == LAUNCHD:
            files += (self._launchd(label, argv, clone.path, log, interval),)
        else:
            files += self._systemd(label, slug, argv, clone.path, log, interval)
        return (
            HeartbeatPlan(
                label, scheduler, slug, url, interpreter, clone.path, log, record, interval, files
            ),
            "",
        )

    def _read(self, name: str) -> str:
        return (self._templates / name).read_text(encoding="utf-8")

    def _launchd(
        self, label: str, argv: Sequence[str], clone: Path, log: Path, interval: int
    ) -> RunnerFile:
        values = {
            "__LABEL__": label,
            "__PYTHON__": argv[0],
            "__RECORD__": argv[-1],
            "__CLONE__": str(clone),
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
        clone: Path,
        log: Path,
        interval: int,
    ) -> tuple[RunnerFile, ...]:
        service_path, timer_path = self._units(label, SYSTEMD)
        service = self._read("heartbeat.service")
        for placeholder, value in {
            "__REPOSITORY__": self._unit_text(slug),
            "__CLONE__": self._unit_text(str(clone)),
            "__PATH_ASSIGNMENT__": self._env_word(f"PATH={self._runners.path}"),
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
    def _env_word(cls, value: str) -> str:
        """One `Environment=` assignment, quoted so a space, a quote or a backslash stays part
        of it. `$` is left alone: systemd expands variables in a command line, never in an
        assignment, so doubling it here would write a literal `$$`."""
        quoted = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{cls._unit_text(quoted)}"'

    @classmethod
    def _unit_word(cls, value: str) -> str:
        """One argument of an `ExecStart=` line, quoted so a space, a quote, a backslash, a
        `$` or a `%` in a path stays part of that one argument."""
        quoted = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "$$")
        return f'"{cls._unit_text(quoted)}"'

    # --- install, status, uninstall -------------------------------------------------------

    @staticmethod
    def _write(rendered: RunnerFileInterface) -> str:
        rendered.path.parent.mkdir(parents=True, exist_ok=True)
        rendered.path.write_text(rendered.text, encoding="utf-8")
        rendered.path.chmod(0o755 if rendered.executable else 0o644)
        return f"wrote {rendered.path}"

    def install(self, plan: HeartbeatPlanInterface, *, load: bool) -> tuple[list[str], bool]:
        """The clone first, then its gate is asked about a synthetic heartbeat, and only a
        clone whose gate lets it through gets a timer: a unit that could never publish is not
        written, let alone loaded."""
        lines = []
        plan.log.parent.mkdir(parents=True, exist_ok=True)
        clone = self._clone(plan.clone, plan.remote_url)
        made, problem = clone.ensure()
        lines += made
        if problem:
            lines.append(problem)
            return lines, False
        own = [rendered for rendered in plan.files if plan.clone in rendered.path.parents]
        units = [rendered for rendered in plan.files if rendered not in own]
        lines += [self._write(rendered) for rendered in own]
        problem = clone.gate_check()
        if problem:
            lines.append(f"refused: {problem}. The timer was not written.")
            return lines, False
        lines.append(f"the clone's own pre-push gate lets a heartbeat through: {NO_CODE}")
        lines += [self._write(rendered) for rendered in units]
        if not load:
            return lines, True
        for argv in self._load_commands(plan):
            code, output = self._service(argv)
            if code != 0 and argv[1] != "bootout":
                lines.append(f"{' '.join(argv[:2])} failed (exit {code}): {output}")
                return lines, False
        lines.append(f"loaded {plan.label}: a beat every {plan.interval_minutes}m")
        if plan.scheduler == SYSTEMD:
            lingering, said = self._linger()
            if not lingering:
                lines.append(f"{said}; next: {_ENABLE_LINGER}")
        return lines, True

    def _load_commands(self, plan: HeartbeatPlanInterface) -> list[tuple[str, ...]]:
        if plan.scheduler == LAUNCHD:
            target = f"gui/{self._uid}"
            # Unloading first makes a re-install pick up the new plist; "not loaded" is the
            # expected answer on a first install, so its status is not a failure.
            return [
                ("launchctl", "bootout", f"{target}/{plan.label}"),
                ("launchctl", "bootstrap", target, str(self._units(plan.label, LAUNCHD)[0])),
            ]
        # `restart` makes a re-install take effect: `enable --now` leaves a running timer
        # on the schedule it was started with.
        return [
            ("systemctl", "--user", "daemon-reload"),
            ("systemctl", "--user", "enable", "--now", f"{plan.label}.timer"),
            ("systemctl", "--user", "restart", f"{plan.label}.timer"),
        ]

    def next_steps(self, plan: HeartbeatPlanInterface) -> list[str]:
        """The commands that load what `install` wrote, every path quoted for the shell."""
        q = shlex.quote
        if plan.scheduler == LAUNCHD:
            target = f"gui/{self._uid}"
            unit = q(str(self._units(plan.label, LAUNCHD)[0]))
            return [
                (
                    f"launchctl bootout {q(f'{target}/{plan.label}')} 2>/dev/null;"
                    f" launchctl bootstrap {target} {unit}"
                ),
                "vibey-gh heartbeat status",
            ]
        timer = q(plan.label + ".timer")
        return [
            "systemctl --user daemon-reload",
            f"systemctl --user enable --now {timer} && systemctl --user restart {timer}",
            f"{_ENABLE_LINGER}   # keep user timers running without a login session",
            "vibey-gh heartbeat status",
        ]

    def _linger(self) -> tuple[bool, str]:
        """Whether systemd keeps this user's timers running without a login session."""
        code, said = self._service(("loginctl", "show-user", str(self._uid), "-p", "Linger"))
        if code != 0:
            return False, (
                f"could not read whether lingering is on for uid {self._uid} (loginctl exited"
                f" {code}), so the timer may stop when you log out"
            )
        if said.strip() == "Linger=yes":
            return True, f"lingering is on for uid {self._uid}: the timer runs without a session"
        return False, (f"lingering is off for uid {self._uid}, so the timer stops when you log out")

    @staticmethod
    def _file_problem(rendered: RunnerFileInterface) -> str:
        if not rendered.path.is_file():
            return f"missing: {rendered.path}"
        if rendered.path.read_text(encoding="utf-8") != rendered.text:
            return f"drift: {rendered.path}"
        if rendered.executable and not os.access(rendered.path, os.X_OK):
            return f"not executable: {rendered.path}"
        return ""

    def status(self) -> tuple[list[str], bool]:
        label, scheduler, _slug, _url, problem = self._names()
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
                clone_lines, clone_healthy = self._clone_status(plan)
                lines += clone_lines
                healthy = healthy and clone_healthy
            loaded = self._loaded(label, scheduler)
            lines.append(f"{label}: {'loaded' if loaded else 'not loaded'} ({scheduler})")
            healthy = healthy and loaded
            if scheduler == SYSTEMD:
                lingering, said = self._linger()
                lines.append(said if lingering else f"{said}: {_ENABLE_LINGER}")
                healthy = healthy and lingering
        record_lines, record_healthy = self._record_status(label, scheduler)
        return lines + record_lines, healthy and record_healthy

    def _clone_status(self, plan: HeartbeatPlan) -> tuple[list[str], bool]:
        """Every file the plan wrote, the clone's settings, and then its gate's own answer."""
        clone = self._clone(plan.clone, plan.remote_url)
        problems = [found for found in map(self._file_problem, plan.files) if found]
        problems += clone.problems()
        if not clone.hook_path.is_file():
            return problems, False
        refused = clone.gate_check()
        if refused:
            return [*problems, f"the clone's gate: {refused}"], False
        passed = f"the clone's own pre-push gate lets a heartbeat through: {NO_CODE}"
        return [*problems, passed], not problems

    def _record_status(self, label: str, scheduler: str) -> tuple[list[str], bool]:
        record = BeatRecord.read(self._log_dir(scheduler) / f"{label}.last.json")
        if record is None:
            return ["last beat: none recorded"], False
        age = int(self._clock() - record.at)
        if age < 0:
            impossible = (
                f"last beat: recorded {-age}s in the future, which no clock should allow:"
                f" {record.reason}"
            )
            return [impossible], False
        outcome = "published" if record.published else "withheld"
        lines = [f"last beat: {age // 60}m{age % 60:02d}s ago, {outcome}: {record.reason}"]
        window = self._fallback.heartbeat_max_age_minutes
        if age > window * 60:
            lines.append(f"the last beat is older than the {window}m window the gate trusts")
            return lines, False
        return lines, record.published

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
        label, scheduler, slug, _url, problem = self._names()
        if problem:
            return [problem]
        clone = self._clone_path(slug)
        units = [unit for unit in self._units(label, scheduler) if unit.is_file()]
        aside = [*units, clone] if (clone / ".git").is_dir() else units
        if not aside:
            return ["no heartbeat timer is installed"]
        if scheduler == LAUNCHD:
            unload: list[tuple[str, ...]] = [("launchctl", "bootout", f"gui/{self._uid}/{label}")]
        else:
            unload = [("systemctl", "--user", "disable", "--now", f"{label}.timer")]
        retired = self._expand(self._runners.install_dir) / RETIRED_DIR
        lines = []
        for argv in unload if units else []:
            if not apply:
                lines.append(f"would run: {' '.join(argv)}")
                continue
            code, output = self._service(argv)
            lines.append(f"unloaded {label}" if code == 0 else f"{label} was not loaded ({output})")
        for path in aside:
            target = SovereignRunner.free_name(retired, path)
            if not apply:
                lines.append(f"would move {path} to {target}")
                continue
            retired.mkdir(parents=True, exist_ok=True)
            os.rename(path, target)
            lines.append(f"moved {path} to {target}")
        if apply and units and scheduler == SYSTEMD:
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
    def _module_origin(python: str, cwd: Path) -> str | None:
        """Where `python` imports vibey_gh from, asked of that interpreter exactly as the
        timer will run it: with the working directory kept off sys.path and no PYTHONPATH."""
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
                cwd=cwd,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        origin = done.stdout.strip()
        return origin if done.returncode == 0 and origin else None
