# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Declared host tuning: what the machine vibey runs on should be set to, whether it is, and
the way back.

    python scripts/host_health.py tune check        # declared against actual; exit 1 on drift
    python scripts/host_health.py tune plan         # what apply would do, touching nothing
    python scripts/host_health.py tune apply        # apply what each item's gate allows
    python scripts/host_health.py tune undo ITEM    # restore what the journal says it replaced

Every item in `scripts/host_tuning.toml` has a class and a gate (ADR-0045, sub-doctrine
12.d): class A is applied whenever asked, because it cannot reach the model or a running
experiment and is reversible or regenerable; class B only once a merged pull request marks it
`adopted` after the review canary held; class C only once the operator approved it, and even
then a step that needs root or a desktop settings pane is printed for a person, never
performed. Every change goes to an append-only journal with the value it replaced, which is
what `undo` restores. Nothing here restarts a service: a change that needs one says so, and
`check` reports it as pending until the service's own start time is after the change.

Stdlib only: the weekly host-health unit runs this under `uv run --no-project`.
"""

from __future__ import annotations

import contextlib
import glob
import gzip
import json
import plistlib
import re
import shlex
import shutil
import time
import tomllib
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from scripts.interfaces.host_tuning_interface import (
        HostTunerInterface,
        TuningBackendInterface,
        TuningJournalInterface,
    )
    from scripts.interfaces.minimum_specs_interface import CommandRunnerInterface
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.host_tuning_interface import (  # type: ignore[import-not-found,no-redef]
        HostTunerInterface,
        TuningBackendInterface,
        TuningJournalInterface,
    )
    from interfaces.minimum_specs_interface import (  # type: ignore[import-not-found,no-redef]
        CommandRunnerInterface,
    )

MIB = 1024**2
#: The states an observation can be in. The first four want attention when the item's gate
#: is open: the host does not have what is declared and the tool was allowed to make it so.
ATTENTION = ("drift", "not-received", "pending-restart", "over-limit")
STATES = (
    *ATTENTION,
    "in-force",
    "proposed",
    "reclaimable",
    "listed",
    "absent",
    "not-applicable",
    "unknown",
)


# ------------------------------------------------------------------------ settings


@dataclass(frozen=True)
class TuningSettings:
    """Everything `scripts/host_tuning.toml` declares. A missing key is a KeyError."""

    table: Mapping[str, Any]

    @classmethod
    def load(cls, path: Path) -> TuningSettings:
        return cls(tomllib.loads(path.read_text(encoding="utf-8"))["host_tuning"])

    def __getitem__(self, key: str) -> Any:
        return self.table[key]

    def items(self) -> list[TuningItem]:
        return [TuningItem(key, spec) for key, spec in self.table["items"].items()]

    def service(self, name: str) -> Mapping[str, Any]:
        services: Mapping[str, Mapping[str, Any]] = self.table["services"]
        return services[name]


@dataclass(frozen=True)
class TuningItem:
    """One declared setting with its class, its evidence and the gate that lets it apply."""

    key: str
    spec: Mapping[str, Any]

    @property
    def klass(self) -> str:
        return str(self.spec["class"])

    @property
    def kind(self) -> str:
        return str(self.spec["kind"])

    @property
    def label(self) -> str:
        return str(self.spec["label"])

    def gate(self, gates: Mapping[str, str]) -> tuple[bool, str]:
        """Whether `tune apply` may touch this item, and why (sub-doctrine 12.d: a gate,
        never judgement)."""
        rule = gates[self.klass]
        if rule == "always":
            return True, "class A: safe now"
        if rule == "adopted":
            if self.spec["adopted"] is True:
                return True, "class B: adopted"
            return False, (
                "class B: waits until the experiments finish and the review canary holds"
                " against its baseline; adopt it with `adopted = true` in a merged pull request"
                " that cites the canary run"
            )
        if rule == "operator_approved":
            who = str(self.spec["operator_approved"])
            if who:
                return True, f"class C: approved by the operator ({who})"
            return False, (
                "class C: the operator's call; set `operator_approved` to the approving pull"
                " request or date"
            )
        raise KeyError(f"[host_tuning.gates] has no rule {rule!r} for class {self.klass}")


@dataclass(frozen=True)
class Observation:
    """One item, declared against actual, with the state that comparison is in."""

    key: str
    klass: str
    kind: str
    label: str
    declared: Any
    actual: Any
    state: str
    detail: str
    gate_open: bool

    def __post_init__(self) -> None:
        if self.state not in STATES:
            raise ValueError(f"{self.key}: unknown state {self.state!r}")

    @property
    def wants_attention(self) -> bool:
        return self.gate_open and self.state in ATTENTION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def line(self) -> str:
        return f"{self.state:<15} {self.klass} {self.key}: {self.detail}"


# ------------------------------------------------------------------------ the host


@dataclass(frozen=True)
class TuningContext:
    """How the tuner reaches the host: a command runner, a file tree, the platform and the
    clock. A test stands up any host from fixtures by replacing all of them."""

    runner: CommandRunnerInterface
    system: str
    now: Callable[[], str]
    timeout: float
    home: Path
    root: Path = Path("/")

    @property
    def mac(self) -> bool:
        return self.system == "Darwin"

    def path(self, text: str) -> Path:
        """A declared path on this host: `~` is the home, an absolute path is under root."""
        if text.startswith("~"):
            return self.home / text[1:].lstrip("/")
        return self.root / text.lstrip("/") if text.startswith("/") else Path(text)

    def argv(self, argv: Sequence[str]) -> list[str]:
        """A declared command with each `~` argument expanded to this host's home."""
        return [str(self.path(part)) if part.startswith("~") else str(part) for part in argv]

    def run(self, argv: Sequence[str], timeout: float | None = None) -> Any:
        return self.runner.run(
            self.argv(argv), timeout=self.timeout if timeout is None else timeout
        )

    def glob(self, pattern: str) -> list[Path]:
        return sorted(Path(p) for p in glob.glob(str(self.path(pattern))))

    def moment(self) -> datetime:
        return Clockwork.parse(self.now())


class Clockwork:
    """ISO-8601 stamps and `ps` start times, in one place."""

    @staticmethod
    def parse(text: str) -> datetime:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)

    @staticmethod
    def lstart(text: str) -> float | None:
        """`ps -o lstart` ("Wed Sep 30 19:54:12 2026", local time) as epoch seconds."""
        with contextlib.suppress(ValueError, OverflowError):
            return time.mktime(time.strptime(text.strip(), "%a %b %d %H:%M:%S %Y"))
        return None


class ServiceProcesses:
    """The host's processes with their start times, from `ps`, read once."""

    def __init__(self, ctx: TuningContext) -> None:
        result = ctx.run(["ps", "-axo", "lstart=,command="])
        self._rows = self.parse(str(result.stdout)) if result.returncode == 0 else []

    @staticmethod
    def parse(text: str) -> list[tuple[float | None, str]]:
        rows: list[tuple[float | None, str]] = []
        for line in text.splitlines():
            parts = line.split(None, 5)
            if len(parts) == 6:
                rows.append((Clockwork.lstart(" ".join(parts[:5])), parts[5]))
        return rows

    def find(self, pattern: str) -> tuple[float | None, str] | None:
        """The first process whose command line contains `pattern`."""
        return next((row for row in self._rows if pattern in row[1]), None)

    @staticmethod
    def flag(command: str, flag: str) -> str | None:
        """The value after `flag` on a command line; '' when the flag has none; None when
        the flag is absent."""
        words = command.split()
        if flag not in words:
            return None
        at = words.index(flag)
        return words[at + 1] if at + 1 < len(words) and not words[at + 1].startswith("-") else ""


# ------------------------------------------------------------------------ the journal


class TuningJournal(TuningJournalInterface):
    """Every apply, undo, reclaim and rotation, with the value it replaced. Append-only:
    a correction is a new entry (the `undo` that supersedes an `apply`), never an edit."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, entry: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(entry), sort_keys=True) + "\n")

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{self.path}:{number}: not a journal entry: {exc}") from exc
        return out

    def last(self, key: str, actions: Sequence[str]) -> dict[str, Any] | None:
        return next(
            (e for e in reversed(self.entries()) if e["key"] == key and e["action"] in actions),
            None,
        )

    def applied_env(self, service: str) -> dict[str, str]:
        """The environment the tool has applied to `service` and not undone: what the login
        agent (macOS) or the drop-in (Linux) must keep asserting."""
        env: dict[str, str] = {}
        for entry in self.entries():
            if entry.get("kind") != "env" or entry.get("service") != service:
                continue
            if entry["action"] == "apply":
                env[str(entry["name"])] = str(entry["value"])
            elif entry["action"] == "undo":
                env.pop(str(entry["name"]), None)
        return env


# ------------------------------------------------------------------------ backends


class Backend(TuningBackendInterface):
    """What every backend shares: the host, the settings, the journal and the gates."""

    def __init__(
        self, ctx: TuningContext, settings: TuningSettings, journal: TuningJournal
    ) -> None:
        self._ctx = ctx
        self._settings = settings
        self._journal = journal

    def _gate(self, item: TuningItem) -> tuple[bool, str]:
        return item.gate(self._settings["gates"])

    def _seen(
        self, item: TuningItem, declared: Any, actual: Any, state: str, detail: str
    ) -> Observation:
        return Observation(
            item.key,
            item.klass,
            item.kind,
            item.label,
            declared,
            actual,
            state,
            detail,
            self._gate(item)[0],
        )

    def _differs(self, item: TuningItem) -> str:
        """The state of an item whose actual value is not the declared one."""
        return "drift" if self._gate(item)[0] else "proposed"

    def _entry(self, item: TuningItem, action: str, **fields: Any) -> dict[str, Any]:
        return {
            "at": self._ctx.now(),
            "key": item.key,
            "kind": item.kind,
            "action": action,
            **fields,
        }

    def observe(self, item: TuningItem) -> Observation:  # pragma: no cover - abstract
        raise NotImplementedError

    def apply(self, item: TuningItem) -> list[str]:  # pragma: no cover - abstract
        raise NotImplementedError

    def undo(self, item: TuningItem, entry: Mapping[str, Any]) -> list[str]:
        """A kind that never changes the host has nothing to put back."""
        return [f"{item.key}: nothing to undo: this tool changed nothing for it"]


class EnvironmentBackend(Backend):
    """A service's environment variable. The platform subclasses say how it is read and
    written; this class judges it, including whether the running service has it yet."""

    def actual(self, item: TuningItem) -> str | None:  # pragma: no cover - abstract
        raise NotImplementedError

    def _service(self, item: TuningItem) -> Mapping[str, Any]:
        return self._settings.service(str(item.spec["service"]))

    def _restart(self, item: TuningItem) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def observe(self, item: TuningItem) -> Observation:
        name, declared = str(item.spec["name"]), str(item.spec["value"])
        actual = self.actual(item)
        if actual != declared:
            return self._seen(
                item,
                declared,
                actual,
                self._differs(item),
                f"{name} is {actual or 'unset'}; declared {declared}",
            )
        svc = self._service(item)
        processes = ServiceProcesses(self._ctx)
        runner = processes.find(str(svc["runner_pattern"]))
        flag = item.spec.get("runner_flag")
        seen = ""
        if flag and runner is not None:
            value = ServiceProcesses.flag(runner[1], str(flag))
            seen = f"; the running {svc['runner_pattern']} has " + (
                f"{flag} {value}".rstrip() if value is not None else f"no {flag}"
            )
        applied = self._journal.last(item.key, ("apply",))
        server = processes.find(str(svc["server_pattern"]))
        if (
            applied
            and server is not None
            and server[0] is not None
            and server[0] < Clockwork.parse(str(applied["at"])).timestamp()
        ):
            return self._seen(
                item,
                declared,
                actual,
                "pending-restart",
                f"{name}={actual} set {applied['at']}, but the server started before it:"
                f" {self._restart(item)}{seen}",
            )
        if flag and runner is not None and ServiceProcesses.flag(runner[1], str(flag)) is None:
            return self._seen(
                item,
                declared,
                actual,
                "not-received",
                f"{name}={actual} is set, but the server did not pass it on{seen}",
            )
        return self._seen(item, declared, actual, "in-force", f"{name}={actual}{seen}")


class LaunchctlEnvironment(EnvironmentBackend):
    """macOS: the launchd session environment the Ollama app hands its server at launch.

    Not `vibey_gh.slots.MacOSAppParallelism`, though it is the same mechanism (10.e: the
    reason is a capability gap, written here): the weekly host-health unit runs this module
    under `uv run --no-project`, stdlib only, where vibey_gh cannot be imported; and that
    class owns one variable and restarts the app, where this one must journal each prior
    value and must never restart a service while an experiment runs on it.
    """

    def actual(self, item: TuningItem) -> str | None:
        result = self._ctx.run(["launchctl", "getenv", str(item.spec["name"])])
        value = str(result.stdout).strip()
        return value if result.returncode == 0 and value else None

    def _restart(self, item: TuningItem) -> str:
        return str(self._service(item)["restart_macos"])

    def agent(self, service: str) -> tuple[Path, str | None]:
        """The login agent that re-asserts the applied environment after a log-out (a
        `launchctl setenv` does not survive one), and its content; None when nothing is
        applied and the agent should not exist."""
        svc = self._settings.service(service)
        label = str(svc["agent_label"])
        path = self._ctx.path(str(svc["agent_dir"])) / f"{label}.plist"
        env = self._journal.applied_env(service)
        if not env:
            return path, None
        script = "; ".join(
            f"/bin/launchctl setenv {shlex.quote(k)} {shlex.quote(v)}"
            for k, v in sorted(env.items())
        )
        body = {"Label": label, "ProgramArguments": ["/bin/sh", "-c", script], "RunAtLoad": True}
        return path, plistlib.dumps(body).decode("utf-8")

    def _write_agent(self, service: str) -> str:
        path, content = self.agent(service)
        if content is None:
            path.unlink(missing_ok=True)
            return f"login agent {path} removed: nothing applied remains"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"login agent {path} re-asserts it at every log-in"

    def apply(self, item: TuningItem) -> list[str]:
        name, value = str(item.spec["name"]), str(item.spec["value"])
        prior = self.actual(item)
        result = self._ctx.run(["launchctl", "setenv", name, value])
        if result.returncode != 0:
            return [f"{item.key}: launchctl setenv {name} failed: {result.tail()}"]
        service = str(item.spec["service"])
        self._journal.append(
            self._entry(item, "apply", service=service, name=name, value=value, prior=prior)
        )
        return [
            f"{item.key}: {name}={value} set (was {prior or 'unset'})",
            f"{item.key}: {self._write_agent(service)}",
            f"{item.key}: takes effect after a restart, which this tool never does:"
            f" {self._restart(item)}",
        ]

    def undo(self, item: TuningItem, entry: Mapping[str, Any]) -> list[str]:
        name, prior = str(entry["name"]), entry.get("prior")
        argv = (
            ["launchctl", "unsetenv", name]
            if prior is None
            else ["launchctl", "setenv", name, str(prior)]
        )
        result = self._ctx.run(argv)
        if result.returncode != 0:
            return [f"{item.key}: {' '.join(argv)} failed: {result.tail()}"]
        service = str(entry["service"])
        self._journal.append(self._entry(item, "undo", service=service, name=name, restored=prior))
        return [
            f"{item.key}: {name} restored to {prior or 'unset'}",
            f"{item.key}: {self._write_agent(service)}",
            f"{item.key}: takes effect after a restart: {self._restart(item)}",
        ]


class SystemdEnvironment(EnvironmentBackend):
    """Linux: a systemd drop-in with `Environment=` lines. The drop-in lives under /etc and
    needs root, so the tool stages it in a durable directory and prints the commands that
    install it; it never runs sudo (the convention `vibey_gh.slots.SystemdParallelism` and
    `scripts/host_health.py tools` keep too)."""

    def _environment(self, item: TuningItem) -> dict[str, str]:
        unit = str(self._service(item)["systemd_unit"])
        result = self._ctx.run(["systemctl", "show", unit, "-p", "Environment", "--value"])
        if result.returncode != 0:
            return {}
        pairs = (word.partition("=") for word in shlex.split(str(result.stdout)))
        return {k: v for k, _, v in pairs if k}

    def actual(self, item: TuningItem) -> str | None:
        return self._environment(item).get(str(item.spec["name"]))

    def _restart(self, item: TuningItem) -> str:
        return str(self._service(item)["restart_linux"])

    def drop_in(self, service: str) -> tuple[Path, str]:
        """The staged drop-in for `service` and its content (an empty [Service] section
        when nothing is applied, which an operator installs to clear it, or removes)."""
        svc = self._settings.service(service)
        target = Path(str(svc["drop_in"]))
        staged = self._ctx.path(str(self._settings["stage_dir"])) / target.name
        lines = [
            f'Environment="{k}={v}"' for k, v in sorted(self._journal.applied_env(service).items())
        ]
        return staged, "\n".join(["[Service]", *lines]) + "\n"

    def _stage(self, item: TuningItem, service: str) -> list[str]:
        staged, content = self.drop_in(service)
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text(content, encoding="utf-8")
        target = self._settings.service(service)["drop_in"]
        return [
            f"{item.key}: staged {staged}; install it as root (this tool never runs sudo):",
            f"  sudo install -D -m 0644 {staged} {target}",
            f"  {self._restart(item)}",
        ]

    def apply(self, item: TuningItem) -> list[str]:
        name, value = str(item.spec["name"]), str(item.spec["value"])
        service = str(item.spec["service"])
        prior = self.actual(item)
        self._journal.append(
            self._entry(item, "apply", service=service, name=name, value=value, prior=prior)
        )
        return self._stage(item, service)

    def undo(self, item: TuningItem, entry: Mapping[str, Any]) -> list[str]:
        service, name = str(entry["service"]), str(entry["name"])
        self._journal.append(
            self._entry(item, "undo", service=service, name=name, restored=entry.get("prior"))
        )
        return self._stage(item, service)


class DockerDesktopBackend(Backend):
    """Docker Desktop's settings (its VM's memory, its built-in Kubernetes). Observed from
    its settings file; never written: the application rewrites that file while it runs, and
    the change is a desktop settings pane the operator uses (class C)."""

    def _file(self) -> Path:
        return self._ctx.path(str(self._settings.service("docker_desktop")["settings"]))

    def observe(self, item: TuningItem) -> Observation:
        key, declared = str(item.spec["key"]), item.spec["value"]
        if not self._ctx.mac:
            return self._seen(
                item, declared, None, "not-applicable", "Docker Desktop's VM is macOS's here"
            )
        path = self._file()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return self._seen(item, declared, None, "absent", f"no {path}")
        except (OSError, ValueError) as exc:
            return self._seen(item, declared, None, "unknown", f"{path} unreadable: {exc}")
        actual = data.get(key)
        if actual == declared:
            return self._seen(item, declared, actual, "in-force", f"{key} = {actual}")
        return self._seen(
            item, declared, actual, self._differs(item), f"{key} is {actual}; declared {declared}"
        )

    def apply(self, item: TuningItem) -> list[str]:
        return [
            f"{item.key}: for the operator (vibey never edits a running application's settings):"
            f" {item.spec['where']}"
        ]


class PostgresBackend(Backend):
    """A server setting of the queue's Postgres: read with SHOW, changed with ALTER SYSTEM
    and a reload. The prior value and its source are journalled, so undo can RESET a
    setting that was at its default rather than pin the default's value."""

    _NAME = re.compile(r"^[a-z_]+$")

    def _psql(self, sql: str) -> Any:
        argv = [*self._settings.service("postgres")["psql"], "-c", sql]
        return self._ctx.run(argv)

    def _name(self, item: TuningItem) -> str:
        name = str(item.spec["name"])
        if not self._NAME.fullmatch(name):
            raise ValueError(f"{item.key}: {name!r} is not a Postgres setting name")
        return name

    @staticmethod
    def _literal(value: Any) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    def observe(self, item: TuningItem) -> Observation:
        name, declared = self._name(item), str(item.spec["value"])
        result = self._psql(f"SHOW {name}")
        if result.returncode != 0:
            return self._seen(item, declared, None, "unknown", f"psql: {result.tail()}")
        actual = str(result.stdout).strip()
        if actual.lower() == declared.lower():
            return self._seen(item, declared, actual, "in-force", f"{name} = {actual}")
        return self._seen(
            item, declared, actual, self._differs(item), f"{name} is {actual}; declared {declared}"
        )

    def _set(self, item: TuningItem, sql: str, name: str) -> tuple[bool, str]:
        result = self._psql(sql)
        if result.returncode != 0:
            return False, f"{item.key}: {sql} failed: {result.tail()}"
        self._psql("SELECT pg_reload_conf()")
        context = str(
            self._psql(f"SELECT context FROM pg_settings WHERE name = {self._literal(name)}").stdout
        ).strip()
        note = (
            "takes effect at the server's next restart, which is the operator's"
            if context == "postmaster"
            else "reloaded"
        )
        return True, note

    def apply(self, item: TuningItem) -> list[str]:
        name, value = self._name(item), str(item.spec["value"])
        prior = str(self._psql(f"SHOW {name}").stdout).strip()
        source = str(
            self._psql(f"SELECT source FROM pg_settings WHERE name = {self._literal(name)}").stdout
        ).strip()
        done, note = self._set(item, f"ALTER SYSTEM SET {name} = {self._literal(value)}", name)
        if not done:
            return [note]
        self._journal.append(
            self._entry(item, "apply", name=name, value=value, prior=prior, prior_source=source)
        )
        return [f"{item.key}: {name} = {value} (was {prior}, from {source}); {note}"]

    def undo(self, item: TuningItem, entry: Mapping[str, Any]) -> list[str]:
        name = self._name(item)
        if entry.get("prior_source") == "default":
            sql = f"ALTER SYSTEM RESET {name}"
        else:
            sql = f"ALTER SYSTEM SET {name} = {self._literal(entry['prior'])}"
        done, note = self._set(item, sql, name)
        if not done:
            return [note]
        self._journal.append(self._entry(item, "undo", name=name, restored=entry["prior"]))
        return [f"{item.key}: {name} restored to {entry['prior']}; {note}"]


class ReclaimBackend(Backend):
    """A regenerable cache: sized, then trimmed by the tool that owns it (never by deleting
    its files from outside). Not reversible by design; regenerable, and each item says why."""

    _UNITS: Mapping[str, float] = {"B": 1, "kB": 1e3, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12}

    @classmethod
    def parse(cls, argv: Sequence[str], text: str) -> int | None:
        """Bytes from `du -sk` (KiB, first field) or `docker builder du` (Reclaimable)."""
        if argv and argv[0] == "du":
            first = text.split()[:1]
            return int(first[0]) * 1024 if first and first[0].isdigit() else None
        found = re.search(r"Reclaimable:\s*([\d.]+)\s*([kKMGT]?B)", text)
        return round(float(found.group(1)) * cls._UNITS[found.group(2)]) if found else None

    def size(self, item: TuningItem) -> int | None:
        argv = [str(part) for part in item.spec["measure"]]
        result = self._ctx.run(argv, timeout=float(item.spec["timeout_s"]))
        # du still prints the total when it could not read some entry (and exits 1); a
        # timeout or a missing tool prints none.
        return (
            None if result.returncode in (124, 126, 127) else self.parse(argv, str(result.stdout))
        )

    @staticmethod
    def gb(size: int | None) -> str:
        return "unknown" if size is None else f"{size / 1e9:.2f} GB"

    def _local(self, item: TuningItem) -> Path | None:
        text = str(item.spec["path"])
        return self._ctx.path(text) if text.startswith(("~", "/")) else None

    def observe(self, item: TuningItem) -> Observation:
        local = self._local(item)
        if local is not None and not local.exists():
            return self._seen(item, None, None, "absent", f"no {item.spec['path']}")
        size = self.size(item)
        if size is None:
            return self._seen(item, None, None, "unknown", f"could not size {item.spec['path']}")
        return self._seen(
            item,
            None,
            size,
            "reclaimable",
            f"{self.gb(size)} at {item.spec['path']}; regenerable: {item.spec['why_regenerable']}",
        )

    def apply(self, item: TuningItem) -> list[str]:
        before = self.size(item)
        lines = [
            f"{item.key}: target {item.spec['path']}, {self.gb(before)};"
            f" regenerable: {item.spec['why_regenerable']}"
        ]
        command = [str(part) for part in item.spec["command"]]
        result = self._ctx.run(command, timeout=float(item.spec["timeout_s"]))
        after = self.size(item)
        self._journal.append(
            self._entry(
                item,
                "reclaim",
                command=command,
                before=before,
                after=after,
                returncode=result.returncode,
            )
        )
        if result.returncode == 124:
            lines.append(
                f"{item.key}: {' '.join(command)} timed out after {item.spec['timeout_s']} s"
                f" (a process holding the cache?); now {self.gb(after)}"
            )
        elif result.returncode != 0:
            lines.append(
                f"{item.key}: {' '.join(command)} exited {result.returncode}: {result.tail()}"
            )
        else:
            freed = None if before is None or after is None else before - after
            lines.append(
                f"{item.key}: {self.gb(before)} -> {self.gb(after)} (freed {self.gb(freed)})"
            )
        return lines

    def undo(self, item: TuningItem, entry: Mapping[str, Any]) -> list[str]:
        return [
            f"{item.key}: not reversible, by design; regenerable: {item.spec['why_regenerable']}"
        ]


class LogBackend(Backend):
    """A log that grows without a bound of its own: rotated past `max_mib` by copying it to
    a compressed archive and truncating it in place, so the writer keeps its file open."""

    def _path(self, item: TuningItem) -> Path:
        return self._ctx.path(str(item.spec["path"]))

    def observe(self, item: TuningItem) -> Observation:
        path, limit = self._path(item), int(item.spec["max_mib"]) * MIB
        if not path.exists():
            return self._seen(item, limit, None, "absent", f"no {item.spec['path']}")
        size = path.stat().st_size
        state = "in-force" if size <= limit else "over-limit"
        return self._seen(
            item, limit, size, state, f"{size / MIB:.1f} MiB of {item.spec['max_mib']} MiB"
        )

    @staticmethod
    def archive(path: Path, n: int) -> Path:
        return path.with_name(f"{path.name}.{n}.gz")

    def apply(self, item: TuningItem) -> list[str]:
        path, keep = self._path(item), int(item.spec["keep"])
        size = path.stat().st_size
        self.archive(path, keep).unlink(missing_ok=True)
        for n in range(keep - 1, 0, -1):
            if self.archive(path, n).exists():
                self.archive(path, n).replace(self.archive(path, n + 1))
        with path.open("rb") as source, gzip.open(self.archive(path, 1), "wb") as target:
            shutil.copyfileobj(source, target)
        with path.open("r+b") as handle:
            handle.truncate(0)
        self._journal.append(
            self._entry(item, "rotate", before=size, archive=str(self.archive(path, 1)))
        )
        return [f"{item.key}: {size / MIB:.1f} MiB rotated to {self.archive(path, 1)}"]

    def undo(self, item: TuningItem, entry: Mapping[str, Any]) -> list[str]:
        return [
            f"{item.key}: nothing to restore: the rotated content is kept in {entry['archive']}"
        ]


@dataclass(frozen=True)
class ModelLoad:
    """One model load the Ollama server logged: when, which blob, at which context size."""

    at: datetime
    digest: str
    num_ctx: int


class OllamaLoadLog:
    """Every `starting llama-server` line in the Ollama server log: each one is a model
    (re)load, with the blob it loaded and the context size (`-c`) the request asked for."""

    _LOAD = re.compile(
        r'^time=(\S+) .*msg="starting llama-server" cmd=".*?--model \S*?sha256-([0-9a-f]+)'
        r".*? -c (\d+)"
    )

    @classmethod
    def loads(cls, lines: Iterable[str]) -> list[ModelLoad]:
        out: list[ModelLoad] = []
        for line in lines:
            found = cls._LOAD.match(line)
            if found:
                with contextlib.suppress(ValueError):
                    at = datetime.fromisoformat(found.group(1)).astimezone(UTC)
                    out.append(ModelLoad(at, found.group(2), int(found.group(3))))
        return out

    @classmethod
    def read(cls, files: Sequence[Path]) -> list[ModelLoad]:
        out: list[ModelLoad] = []
        for path in files:
            with (
                contextlib.suppress(OSError),
                path.open(encoding="utf-8", errors="replace") as handle,
            ):
                out.extend(cls.loads(handle))
        return sorted(out, key=lambda load: load.at)


class OllamaLoadsBackend(Backend):
    """Not a setting but its outcome: how often the model reloads, and at how many context
    sizes, in the trailing window. The lever is in the callers (one num_ctx per lane)."""

    def observe(self, item: TuningItem) -> Observation:
        svc = self._settings.service(str(item.spec["service"]))
        declared = {
            "max_loads_per_day": item.spec["max_loads_per_day"],
            "max_distinct_num_ctx": item.spec["max_distinct_num_ctx"],
        }
        files = self._ctx.glob(str(svc["log_glob"]))
        if not files:
            return self._seen(item, declared, None, "absent", f"no log matches {svc['log_glob']}")
        hours = float(item.spec["window_hours"])
        since = self._ctx.moment() - timedelta(hours=hours)
        recent = [load for load in OllamaLoadLog.read(files) if load.at >= since]
        actual = {
            "loads": len(recent),
            "loads_per_day": round(len(recent) * 24 / hours, 1),
            "distinct_num_ctx": len({load.num_ctx for load in recent}),
            "window_hours": hours,
        }
        within = (
            actual["loads_per_day"] <= declared["max_loads_per_day"]
            and actual["distinct_num_ctx"] <= declared["max_distinct_num_ctx"]
        )
        detail = (
            f"{actual['loads']} loads in {hours:g} h at {actual['distinct_num_ctx']} context"
            f" sizes; declared at most {declared['max_loads_per_day']}/day at"
            f" {declared['max_distinct_num_ctx']}"
        )
        return self._seen(
            item, declared, actual, "in-force" if within else self._differs(item), detail
        )

    def apply(self, item: TuningItem) -> list[str]:
        return [
            f"{item.key}: not an environment setting: every lane must send one fixed num_ctx"
            " (docs/runbooks/host-optimization.md, the class-B procedure)"
        ]


class ModelsBackend(Backend):
    """The models on disk, with the last time each was loaded. Listed for the operator;
    deleting one is theirs to decide and do (`ollama rm`)."""

    def inventory(self, item: TuningItem) -> list[dict[str, Any]]:
        svc = self._settings.service(str(item.spec["service"]))
        root = self._ctx.path(str(svc["manifest_dir"]))
        last: dict[str, datetime] = {}
        for load in OllamaLoadLog.read(self._ctx.glob(str(svc["log_glob"]))):
            last[load.digest] = load.at
        models: list[dict[str, Any]] = []
        for manifest in sorted(p for p in root.rglob("*") if p.is_file()) if root.is_dir() else []:
            parts = manifest.relative_to(root).parts
            if len(parts) != 4:
                continue
            with contextlib.suppress(OSError, ValueError):
                layers = json.loads(manifest.read_text(encoding="utf-8"))["layers"]
                model = next(x for x in layers if str(x["mediaType"]).endswith(".model"))
                digest = str(model["digest"]).removeprefix("sha256:")
                name = parts[2] if parts[1] == "library" else f"{parts[1]}/{parts[2]}"
                loaded = last.get(digest)
                models.append(
                    {
                        "model": f"{name}:{parts[3]}",
                        "gb": round(int(model["size"]) / 1e9, 1),
                        "last_loaded": loaded.strftime("%Y-%m-%dT%H:%M:%SZ") if loaded else None,
                    }
                )
        return models

    def stale(
        self, item: TuningItem, models: Sequence[Mapping[str, Any]]
    ) -> list[Mapping[str, Any]]:
        since = self._ctx.moment() - timedelta(days=int(item.spec["stale_after_days"]))
        return [
            m
            for m in models
            if m["last_loaded"] is None or Clockwork.parse(str(m["last_loaded"])) < since
        ]

    def observe(self, item: TuningItem) -> Observation:
        models = self.inventory(item)
        if not models:
            return self._seen(item, None, [], "absent", "no Ollama model manifests")
        stale = self.stale(item, models)
        names = ", ".join(f"{m['model']} ({m['gb']} GB)" for m in stale) or "none"
        return self._seen(
            item,
            None,
            models,
            "listed",
            f"{len(models)} models, {sum(m['gb'] for m in models):.1f} GB;"
            f" not loaded in {item.spec['stale_after_days']} days: {names}",
        )

    def apply(self, item: TuningItem) -> list[str]:
        stale = self.stale(item, self.inventory(item))
        if not stale:
            return [f"{item.key}: every model was loaded recently"]
        return [f"{item.key}: for the operator to decide (never run here):"] + [
            f"  ollama rm {m['model']}   # {m['gb']} GB, last loaded {m['last_loaded'] or 'never in the retained logs'}"
            for m in stale
        ]


# ------------------------------------------------------------------------ the tuner


class HostTuner(HostTunerInterface):
    """The declared items through their backends, under each item's gate."""

    def __init__(
        self, settings: TuningSettings, ctx: TuningContext, journal: TuningJournal | None = None
    ) -> None:
        self._settings = settings
        self._ctx = ctx
        self.journal = journal or TuningJournal(ctx.path(str(settings["journal"])))
        env: Backend = (
            LaunchctlEnvironment(ctx, settings, self.journal)
            if ctx.mac
            else SystemdEnvironment(ctx, settings, self.journal)
        )
        self._backends: dict[str, Backend] = {
            "env": env,
            "docker_desktop": DockerDesktopBackend(ctx, settings, self.journal),
            "postgres": PostgresBackend(ctx, settings, self.journal),
            "reclaim": ReclaimBackend(ctx, settings, self.journal),
            "log": LogBackend(ctx, settings, self.journal),
            "ollama_loads": OllamaLoadsBackend(ctx, settings, self.journal),
            "models": ModelsBackend(ctx, settings, self.journal),
        }

    def items(self, only: Sequence[str] = ()) -> list[TuningItem]:
        items = self._settings.items()
        known = {item.key for item in items}
        unknown = [key for key in only if key not in known]
        if unknown:
            raise KeyError(f"not declared in [host_tuning.items]: {', '.join(unknown)}")
        return [item for item in items if not only or item.key in only]

    def observe(self, item: TuningItem) -> Observation:
        try:
            return self._backends[item.kind].observe(item)
        except Exception as exc:  # noqa: BLE001 -- one item's failure is reported, not fatal
            return Observation(
                item.key,
                item.klass,
                item.kind,
                item.label,
                None,
                None,
                "unknown",
                f"could not observe: {type(exc).__name__}: {exc}",
                item.gate(self._settings["gates"])[0],
            )

    def check(self, kinds: Sequence[str] | None = None) -> list[Observation]:
        return [self.observe(item) for item in self.items() if kinds is None or item.kind in kinds]

    def apply(self, only: Sequence[str] = (), dry_run: bool = False) -> list[str]:
        lines: list[str] = []
        for item in self.items(only):
            open_, why = item.gate(self._settings["gates"])
            if not open_:
                lines.append(f"{item.key}: not applied: {why}")
                continue
            seen = self.observe(item)
            if seen.state in ("in-force", "absent", "not-applicable", "unknown"):
                lines.append(f"{item.key}: nothing to do ({seen.state}: {seen.detail})")
                continue
            if dry_run:
                lines.append(f"{item.key}: would apply ({seen.state}: {seen.detail})")
                continue
            lines.extend(self._backends[item.kind].apply(item))
        return lines

    def undo(self, key: str) -> list[str]:
        item = self.items([key])[0]
        entry = self.journal.last(key, ("apply", "undo", "reclaim", "rotate"))
        if entry is None or entry["action"] == "undo":
            return [f"{key}: nothing to undo: the journal holds no standing change by this tool"]
        return self._backends[item.kind].undo(item, entry)
