# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""vibey's minimum system requirements, re-measured every week and never silently reused.

    python scripts/minimum_specs.py measure --out <record>   # probe the host, derive, merge
    python scripts/minimum_specs.py derive                   # recompute the derived figures
    python scripts/minimum_specs.py render                   # rewrite the GENERATED blocks
    python scripts/minimum_specs.py check                    # exit 1 if anything is out of step

The record (`docs/architecture/evidence/minimum-specs.json`, declared in
`scripts/minimum_specs.toml`) holds one entry per figure: its value and unit, how it was
obtained, when (UTC), on which host, under which conditions, and its status:

    measured   a command on the named host produced it
    declared   read from the repository (a constant, a manifest floor, a stated assumption)
    derived    arithmetic on other figures; the formula and every input are recorded
    stale      a weekly measurement could not run, so the last good value is kept, marked,
               with the date it was last good and the reason it was not re-measured
    skipped    it could not run and there was never a good value; no number is invented

Requirements are derived in code from the measured inputs (`Derivations`), so a change to a
measured figure, an assumption or one of vibey's own limits moves every table that depends
on it. `check` recomputes the derivations and the tables from the committed record and
fails when either disagrees with what is committed (sub-doctrine 12.e: the check that says
out loud when the step was missed). Status is evidence-bounded (sub-doctrine 10.f): every
table names the host and the dates of the figures in it.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import platform
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.interfaces.minimum_specs_interface import (
        ClockInterface,
        CommandRunnerInterface,
        DerivationsInterface,
        IdleGateInterface,
        ProbeInterface,
        RequirementsRendererInterface,
        StalenessPolicyInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.minimum_specs_interface import (  # type: ignore[import-not-found,no-redef]
        ClockInterface,
        CommandRunnerInterface,
        DerivationsInterface,
        IdleGateInterface,
        ProbeInterface,
        RequirementsRendererInterface,
        StalenessPolicyInterface,
    )

SCRIPT = "scripts/minimum_specs.py"
SCHEMA = "vibey-minimum-specs/1"
DEFAULT_CONFIG = "scripts/minimum_specs.toml"
STATUSES = ("measured", "declared", "derived", "stale", "skipped")
#: A figure the weekly run re-measures goes stale when it cannot; a `once` figure was
#: measured by a one-off pass the weekly probes do not repeat, and is shown with its date.
CADENCES = ("weekly", "once")
MIB = 1024**2
GIB = 1024**3
#: Every date in the record: a UTC instant, to the second or finer.
ISO_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")


# ------------------------------------------------------------------------ settings


@dataclass(frozen=True)
class SpecsSettings:
    """Everything `scripts/minimum_specs.toml` declares, typed. Nothing here has a default
    in code: a key missing from the file is an error, not a silent value."""

    record: str
    docs_page: str
    paper: str
    install: Mapping[str, Any]
    postgres: Mapping[str, Any]
    ollama: Mapping[str, Any]
    bench: Mapping[str, Any]
    idle: Mapping[str, Any]
    processes: Mapping[str, Any]
    declared: Mapping[str, Any]
    assumptions: Mapping[str, Any]

    @classmethod
    def load(cls, path: Path) -> SpecsSettings:
        table = tomllib.loads(path.read_text(encoding="utf-8"))["minimum_specs"]
        return cls(
            record=table["record"],
            docs_page=table["docs_page"],
            paper=table["paper"],
            install=table["install"],
            postgres=table["postgres"],
            ollama=table["ollama"],
            bench=table["bench"],
            idle=table["idle"],
            processes=table["processes"],
            declared=table["declared"],
            assumptions=table["assumptions"],
        )

    @property
    def sovereign_model(self) -> str:
        return str(self.ollama["sovereign_model"])


# ------------------------------------------------------------------------ the record


class VolatilePaths:
    """Rewrites a host's temporary directories to `$TMPDIR` in a figure's free text.

    A probe runs its scratch work under the temp directory, and the command it records can
    quote that path. It is throwaway and machine-specific, and the record is committed, so
    the tree's volatile-storage guard (tests/meta) refuses it -- and a weekly run would
    otherwise write it back each time. Scrubbed where every figure is built, not per probe.
    """

    # Assembled from parts, as tests/meta/test_no_volatile_work_paths.py assembles its own,
    # so these patterns -- which remove volatile paths -- are not mistaken for one.
    _PATTERNS = (
        re.compile(r"(?:/private)?/var/" + r"folders/[^/\s]+/[^/\s]+/T(?=/|\b)"),
        re.compile(r"(?:/private)?/" + r"tmp(?=/)"),
    )

    @classmethod
    def scrub(cls, text: str | None) -> str | None:
        if text is None:
            return None
        # The known shapes first, so the result does not depend on where it runs; then the
        # running host's own temp directory, whatever it is called.
        for pattern in cls._PATTERNS:
            text = pattern.sub("$TMPDIR", text)
        here = tempfile.gettempdir().rstrip("/")
        if len(here) > 1:
            text = text.replace(here, "$TMPDIR")
        return text


@dataclass(frozen=True)
class Figure:
    """One number (or verdict) with everything needed to trust it or not."""

    id: str
    label: str
    value: Any
    unit: str
    status: str
    method: str
    measured_at: str | None = None
    host: str | None = None
    conditions: Mapping[str, Any] = field(default_factory=dict)
    source: str | None = None
    cadence: str = "weekly"
    formula: str | None = None
    inputs: Mapping[str, Any] | None = None
    was: str | None = None
    stale_since: str | None = None
    reason: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        for name in ("method", "reason", "note"):
            object.__setattr__(self, name, VolatilePaths.scrub(getattr(self, name)))
        if self.status not in STATUSES:
            raise ValueError(f"{self.id}: unknown status {self.status!r}")
        if self.cadence not in CADENCES:
            raise ValueError(f"{self.id}: unknown cadence {self.cadence!r}")
        if self.status == "derived" and (not self.formula or self.inputs is None):
            raise ValueError(f"{self.id}: a derived figure records its formula and inputs")
        if self.status in ("stale", "skipped") and not self.reason:
            raise ValueError(f"{self.id}: a {self.status} figure says why")
        if self.status == "stale" and not self.stale_since:
            raise ValueError(f"{self.id}: a stale figure says since when")
        if self.status == "skipped" and self.value is not None:
            raise ValueError(f"{self.id}: a skipped figure carries no value")
        for name in ("measured_at", "stale_since"):
            stamp = getattr(self, name)
            if stamp is not None and not ISO_UTC.fullmatch(stamp):
                raise ValueError(f"{self.id}: {name} {stamp!r} is not an ISO-8601 UTC time")

    @property
    def has_value(self) -> bool:
        return self.status != "skipped" and self.value is not None

    @property
    def basis(self) -> str:
        """What the value is, stale or not: measured, declared or derived."""
        return self.was if self.status == "stale" and self.was else self.status

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        return {k: v for k, v in raw.items() if v not in (None, {}) or k == "value"}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> Figure:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def skipped(self, reason: str) -> Figure:
        """This figure, not measured this time, with no value to fall back on."""
        return replace(self, value=None, status="skipped", reason=reason, was=None)


@dataclass(frozen=True)
class SpecsRecord:
    """The committed evidence record: hosts, figures, sources and what was not verified."""

    generated_at: str
    hosts: Mapping[str, Mapping[str, Any]]
    figures: tuple[Figure, ...]
    sources: Mapping[str, str] = field(default_factory=dict)
    not_verified: tuple[str, ...] = ()
    schema: str = SCHEMA

    def by_id(self) -> dict[str, Figure]:
        return {f.id: f for f in self.figures}

    def to_json(self) -> str:
        body = {
            "schema": self.schema,
            "generated_at": self.generated_at,
            "generated_by": SCRIPT,
            "hosts": {k: dict(v) for k, v in sorted(self.hosts.items())},
            "sources": dict(sorted(self.sources.items())),
            "not_verified": list(self.not_verified),
            "figures": [f.to_dict() for f in sorted(self.figures, key=lambda f: f.id)],
        }
        return json.dumps(body, indent=2, ensure_ascii=False, sort_keys=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> SpecsRecord:
        raw = json.loads(text)
        if raw.get("schema") != SCHEMA:
            raise ValueError(f"record schema {raw.get('schema')!r} is not {SCHEMA}")
        return cls(
            generated_at=raw["generated_at"],
            hosts=raw["hosts"],
            figures=tuple(Figure.from_dict(f) for f in raw["figures"]),
            sources=raw.get("sources", {}),
            not_verified=tuple(raw.get("not_verified", ())),
        )

    @classmethod
    def load(cls, path: Path) -> SpecsRecord:
        return cls.from_json(path.read_text(encoding="utf-8"))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")


# ------------------------------------------------------------------------ the machinery


class SystemClock(ClockInterface):
    """UTC, to the millisecond, the one format every figure is stamped in."""

    def now(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    seconds: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def tail(self, lines: int = 3) -> str:
        text = (self.stderr or self.stdout).strip().splitlines()
        return " / ".join(line.strip() for line in text[-lines:])[:300]


class SubprocessRunner(CommandRunnerInterface):
    """subprocess.run with the outcome always returned: 127 for a missing tool, 124 for a
    timeout, so a probe records what happened instead of crashing the whole session."""

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> CommandResult:
        started = time.monotonic()
        merged = {**os.environ, **env} if env is not None else None
        try:
            done = subprocess.run(  # noqa: S603 - argv is built by this script, never a shell
                list(argv),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=merged,
                cwd=cwd,
                check=False,
            )
        except FileNotFoundError as exc:
            return CommandResult(127, "", str(exc), time.monotonic() - started)
        except OSError as exc:  # present but not runnable here (a sandbox, a permission)
            return CommandResult(126, "", str(exc), time.monotonic() - started)
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout if isinstance(exc.stdout, str) else ""
            return CommandResult(
                124, out, f"timed out after {timeout} s", time.monotonic() - started
            )
        return CommandResult(done.returncode, done.stdout, done.stderr, time.monotonic() - started)


class Units:
    """Conversions between the units the record uses. Bytes are the pivot."""

    FACTORS: Mapping[str, float] = {
        "bytes": 1,
        "KiB": 1024,
        "MiB": MIB,
        "GiB": GIB,
        "KB": 1e3,
        "MB": 1e6,
        "GB": 1e9,
    }

    @classmethod
    def convert(cls, value: float, unit: str, to: str) -> float:
        if unit not in cls.FACTORS or to not in cls.FACTORS:
            raise ValueError(f"cannot convert {unit} to {to}")
        return value * cls.FACTORS[unit] / cls.FACTORS[to]


# ------------------------------------------------------------------------ the host


class HostDescriber:
    """Who the measuring machine is: chip, cores, memory, operating system."""

    def __init__(self, runner: CommandRunnerInterface) -> None:
        self._runner = runner

    def _sysctl(self, key: str) -> str:
        return str(self._runner.run(["sysctl", "-n", key], timeout=10).stdout).strip()

    def describe(self) -> dict[str, Any]:
        system = platform.system()
        info: dict[str, Any] = {"system": system, "arch": platform.machine()}
        if system == "Darwin":
            info["chip"] = self._sysctl("machdep.cpu.brand_string")
            info["ram_bytes"] = int(self._sysctl("hw.memsize") or 0)
            info["cores_total"] = int(self._sysctl("hw.ncpu") or 0)
            perf, eff = (
                self._sysctl("hw.perflevel0.physicalcpu"),
                self._sysctl("hw.perflevel1.physicalcpu"),
            )
            info["cores_performance"] = int(perf) if perf.isdigit() else None
            info["cores_efficiency"] = int(eff) if eff.isdigit() else None
            hw = str(self._runner.run(["system_profiler", "SPHardwareDataType"], timeout=60).stdout)
            model = re.search(r"Model Identifier:\s*(\S+)", hw)
            info["model"] = model.group(1) if model else None
            gpu = str(
                self._runner.run(["system_profiler", "SPDisplaysDataType"], timeout=60).stdout
            )
            gpu_cores = re.search(r"Total Number of Cores:\s*(\d+)", gpu)
            info["gpu_cores"] = int(gpu_cores.group(1)) if gpu_cores else None
            version = str(
                self._runner.run(["sw_vers", "-productVersion"], timeout=10).stdout
            ).strip()
            build = str(self._runner.run(["sw_vers", "-buildVersion"], timeout=10).stdout).strip()
            info["os"] = f"macOS {version} ({build})" if version else None
        else:
            info["chip"] = self._linux_field("/proc/cpuinfo", r"model name\s*:\s*(.+)")
            mem = self._linux_field("/proc/meminfo", r"MemTotal:\s*(\d+)")
            info["ram_bytes"] = int(mem) * 1024 if mem else None
            info["cores_total"] = os.cpu_count()
            pretty = self._linux_field("/etc/os-release", r'PRETTY_NAME="?([^"\n]+)')
            info["os"] = pretty
            info["model"] = None
        return info

    @staticmethod
    def _linux_field(path: str, pattern: str) -> str | None:
        with contextlib.suppress(OSError):
            found = re.search(pattern, Path(path).read_text(encoding="utf-8", errors="replace"))
            if found:
                return found.group(1).strip()
        return None

    @staticmethod
    def host_id(info: Mapping[str, Any]) -> str:
        """A readable, stable key: model, chip, memory and OS, which is what a figure's
        meaning depends on. Two runs on the same machine share it."""
        ram = info.get("ram_bytes")
        parts = [
            info.get("model") or info.get("arch") or "unknown",
            info.get("chip") or "unknown chip",
            f"{round(ram / GIB)} GiB" if ram else "unknown memory",
            info.get("os") or info.get("system") or "unknown OS",
        ]
        return " · ".join(str(p) for p in parts)


# ------------------------------------------------------------------------ Ollama


class OllamaClient:
    """Loopback HTTP to Ollama, plus its registry for model sizes (no pull)."""

    def __init__(self, url: str, registry: str, timeout: float) -> None:
        self._url = url.rstrip("/")
        self._registry = registry.rstrip("/")
        self._timeout = timeout

    def call(self, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(  # noqa: S310 - the configured loopback endpoint
            self._url + path, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
            body = json.loads(response.read() or b"{}")
        return body if isinstance(body, dict) else {"value": body}

    def version(self) -> str | None:
        return self.call("/api/version").get("version")

    def loaded(self) -> list[dict[str, Any]]:
        models = self.call("/api/ps").get("models", [])
        return [m for m in models if isinstance(m, dict)]

    def unload(self, model: str) -> None:
        self.call("/api/generate", {"model": model, "keep_alive": 0})
        for _ in range(100):
            if not any(m.get("name") == model or m.get("model") == model for m in self.loaded()):
                return
            time.sleep(0.2)

    def manifest_bytes(self, model: str) -> int:
        """The sum of every layer and the config in the registry manifest: the download."""
        name, _, tag = model.partition(":")
        repo = name if "/" in name else f"library/{name}"
        request = urllib.request.Request(  # noqa: S310 - the configured registry
            f"{self._registry}/v2/{repo}/manifests/{tag or 'latest'}",
            headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            manifest = json.loads(response.read())
        layers = [*manifest.get("layers", []), manifest.get("config", {})]
        return sum(int(layer.get("size", 0)) for layer in layers)


class LlamaServerLog:
    """llama-server's own memory accounting, read from the Ollama server log.

    `ollama ps` understates a loaded model by 1.2-4.2 GiB (it omits most of the KV growth
    and the host buffers), so the device and host figures come from these lines instead.
    """

    _DEVICE = re.compile(
        r"\|\s+-\s+(?P<dev>\S+)\s+\([^)]*\)\s+\|\s+(?P<total>\d+)\s+=\s+(?P<free>\d+)\s+\+\s+"
        r"\((?P<self>\d+)\s+=\s+(?P<model>\d+)\s+\+\s+(?P<context>\d+)\s+\+\s+(?P<compute>\d+)\)"
    )
    # `CPU_Mapped` when the weights are memory-mapped, plain `CPU` when they were read in
    # (seen on the 2026-09-30 smoke run under memory pressure); the same host buffer.
    _HOST_MODEL = re.compile(r"CPU(?:_Mapped)? model buffer size =\s+([\d.]+) MiB")
    _HOST_COMPUTE = re.compile(r"CPU compute buffer size =\s+([\d.]+) MiB")
    _NCTX = re.compile(r"llama_context: n_ctx\s+=\s+(\d+)")
    _POST = re.compile(r'\| POST +"(/api/chat|/api/generate|/v1/chat/completions|/v1/completions)"')

    def __init__(self, path: Path) -> None:
        self.path = path

    def offset(self) -> int:
        try:
            return self.path.stat().st_size
        except OSError:
            return 0

    def since(self, offset: int) -> str:
        try:
            with self.path.open("rb") as handle:
                handle.seek(offset)
                return handle.read().decode("utf-8", "replace")
        except OSError:
            return ""

    @classmethod
    def accounting(cls, text: str) -> dict[str, float]:
        """The last load's device (weights + KV + compute) and host buffers, in MiB."""
        out: dict[str, float] = {}
        for match in cls._DEVICE.finditer(text):
            out.update(
                device_mib=float(match["self"]),
                weights_mib=float(match["model"]),
                kv_mib=float(match["context"]),
                compute_mib=float(match["compute"]),
                working_set_limit_mib=float(match["free"]),
            )
        for key, pattern in (
            ("host_model_mib", cls._HOST_MODEL),
            ("host_compute_mib", cls._HOST_COMPUTE),
        ):
            found = pattern.findall(text)
            if found:
                out[key] = float(found[-1])
        n_ctx = cls._NCTX.findall(text)
        if n_ctx:
            out["n_ctx"] = float(n_ctx[-1])
        return out

    @classmethod
    def inference_posts(cls, text: str) -> int:
        return sum(1 for line in text.splitlines() if cls._POST.search(line))

    _GIN_STAMP = re.compile(r"\[GIN\]\s+(\d{4}/\d{2}/\d{2} - \d{2}:\d{2}:\d{2})")

    @classmethod
    def last_post_epoch(cls, text: str) -> float | None:
        """When the last inference request in `text` was logged (GIN stamps local time)."""
        for line in reversed(text.splitlines()):
            if cls._POST.search(line):
                stamp = cls._GIN_STAMP.search(line)
                if stamp is None:
                    return None
                return time.mktime(time.strptime(stamp.group(1), "%Y/%m/%d - %H:%M:%S"))
        return None


# ------------------------------------------------------------------------ the idle gate


class IdleGate(IdleGateInterface):
    """The model measurements run only on a quiet host.

    Quiet means load1 at or below the declared ceiling, no inference request in the Ollama
    log for the declared window, and the declared busy command silent. The gate waits a
    bounded time and then says no, with the reason; it never unloads a model someone else
    is using, because the caller checks it before touching Ollama.
    """

    def __init__(
        self,
        settings: Mapping[str, Any],
        log: LlamaServerLog,
        runner: CommandRunnerInterface,
        loadavg: Callable[[], tuple[float, float, float]] = os.getloadavg,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
    ) -> None:
        self._settings = settings
        self._log = log
        self._runner = runner
        self._loadavg = loadavg
        self._sleep = sleep
        self._monotonic = monotonic
        self._wall = wall

    def _busy_output(self) -> str:
        command = str(self._settings.get("busy_command") or "").strip()
        if not command:
            return ""
        result = self._runner.run(["/bin/sh", "-c", command], timeout=60)
        return str(result.stdout).strip()[:200]

    def _recent_request(self) -> bool:
        """True when another client made an inference request within the quiet window.

        The request's own log stamp decides when it can be read; otherwise the log's mtime
        bounds when its last line was written, and a request near the end counts as recent.
        """
        try:
            modified = self._log.path.stat().st_mtime
        except OSError:
            return False
        window = float(self._settings["quiet_window_s"])
        if self._wall() - modified > window:
            return False
        tail = self._log.since(max(0, self._log.offset() - 65536))
        stamp = LlamaServerLog.last_post_epoch(tail)
        if stamp is not None:
            return self._wall() - stamp <= window
        return LlamaServerLog.inference_posts(tail) > 0

    def observe(self) -> tuple[str, dict[str, Any]]:
        load1, load5, _ = self._loadavg()
        busy = self._busy_output()
        recent = self._recent_request()
        conditions = {
            "load1": round(load1, 2),
            "load5": round(load5, 2),
            "busy_command_output": busy,
            "ollama_request_within_quiet_window": recent,
        }
        if busy:
            return f"busy command reported: {busy}", conditions
        if recent:
            return (
                f"another Ollama client made a request in the last {self._settings['quiet_window_s']} s",
                conditions,
            )
        if load1 > float(self._settings["max_load1"]):
            return f"load1 {load1:.2f} above {self._settings['max_load1']}", conditions
        return "", conditions

    def wait(self) -> tuple[bool, str, dict[str, Any]]:
        started = self._monotonic()
        while True:
            reason, conditions = self.observe()
            waited = round(self._monotonic() - started, 1)
            conditions["waited_s"] = waited
            if not reason:
                return True, "", conditions
            if waited >= float(self._settings["max_wait_s"]):
                return False, f"host not idle after {waited:.0f} s: {reason}", conditions
            self._sleep(float(self._settings["poll_s"]))

    def log_offset(self) -> int:
        return self._log.offset()

    def foreign_requests_since(self, offset: int) -> int:
        return LlamaServerLog.inference_posts(self._log.since(offset))


# ------------------------------------------------------------------------ probes


class FigureFactory:
    """Stamps figures with the host and the time, so every probe records them alike."""

    def __init__(self, clock: ClockInterface, host: str) -> None:
        self._clock = clock
        self.host = host

    def measured(
        self,
        fid: str,
        label: str,
        value: Any,
        unit: str,
        method: str,
        conditions: Mapping[str, Any] | None = None,
        note: str | None = None,
    ) -> Figure:
        return Figure(
            id=fid,
            label=label,
            value=value,
            unit=unit,
            status="measured",
            method=method,
            measured_at=self._clock.now(),
            host=self.host,
            conditions=dict(conditions or {}),
            note=note,
        )

    def declared(
        self, fid: str, label: str, value: Any, unit: str, method: str, source: str
    ) -> Figure:
        return Figure(
            id=fid,
            label=label,
            value=value,
            unit=unit,
            status="declared",
            method=method,
            measured_at=self._clock.now(),
            source=source,
        )

    def skipped(self, fid: str, label: str, unit: str, method: str, reason: str) -> Figure:
        return Figure(
            id=fid,
            label=label,
            value=None,
            unit=unit,
            status="skipped",
            method=method,
            measured_at=self._clock.now(),
            host=self.host,
            reason=reason,
        )


class DeclaredFloorsProbe(ProbeInterface):
    """The floors the repository itself declares, read from where they are declared."""

    name = "declared"

    def __init__(self, repo: Path, settings: SpecsSettings, figures: FigureFactory) -> None:
        self._repo = repo
        self._settings = settings
        self._figures = figures

    def _read(self, relative: str) -> str | None:
        with contextlib.suppress(OSError):
            return (self._repo / relative).read_text(encoding="utf-8")
        return None

    def _pattern(
        self,
        fid: str,
        label: str,
        unit: str,
        relative: str,
        pattern: str,
        cast: Callable[[str], Any] = str,
    ) -> Figure:
        method = f"read `{pattern}` from {relative}"
        text = self._read(relative)
        found = re.search(pattern, text, re.MULTILINE) if text is not None else None
        if not found:
            return self._figures.skipped(fid, label, unit, method, f"not found in {relative}")
        return self._figures.declared(fid, label, cast(found.group(1)), unit, method, relative)

    def run(self) -> list[Figure]:
        d = self._settings.declared
        pg = self._settings.postgres
        conductor, runner = d["conductor_source"], d["runner_config_source"]
        return [
            self._pattern(
                "declared.python_requires",
                "Python required by vibey-engine",
                "specifier",
                d["engine_pyproject"],
                r'^requires-python\s*=\s*"([^"]+)"',
            ),
            self._pattern(
                "declared.postgres_min_major",
                "PostgreSQL floor vibey checks on connect",
                "major",
                pg["floor_source"],
                rf"^{pg['floor_constant']}\b[^=]*=\s*(\d+)",
                int,
            ),
            self._pattern(
                "declared.ollama_timeout_s",
                "Per-request model timeout",
                "s",
                conductor,
                r"^DEFAULT_OLLAMA_TIMEOUT\s*=\s*(\d+)",
                int,
            ),
            self._pattern(
                "declared.conductor_context_max",
                "Conductor context ceiling (DESIGN, DECOMPOSE)",
                "tokens",
                conductor,
                r"^DEFAULT_OLLAMA_CONTEXT\s*=\s*(\d+)",
                int,
            ),
            self._pattern(
                "declared.conductor_output_tokens",
                "Conductor output budget (doubled on its one retry)",
                "tokens",
                conductor,
                r"^DEFAULT_OLLAMA_OUTPUT\s*=\s*(\d+)",
                int,
            ),
            self._pattern(
                "declared.runner_context_window",
                "gptossloop BUILD context window",
                "tokens",
                runner,
                r"^\s+context_window:\s*int\s*=\s*([\d_]+)",
                lambda v: int(v.replace("_", "")),
            ),
            self._pattern(
                "declared.vscode_engine",
                "VS Code the extension declares",
                "semver",
                d["vscode_manifest"],
                r'"vscode":\s*"([^"]+)"',
            ),
            self._pattern(
                "declared.vscode_node",
                "Node to build the VS Code extension",
                "semver",
                d["vscode_manifest"],
                r'"node":\s*"([^"]+)"',
            ),
            self._pattern(
                "declared.app_node",
                "Node for the React Native app",
                "semver",
                d["app_manifest"],
                r'"node":\s*"([^"]+)"',
            ),
            self._pattern(
                "declared.node_recommended",
                "Node the repository pins for development",
                "version",
                d["node_version_file"],
                r"^\s*(\S+)\s*$",
            ),
            self._pattern(
                "declared.desktop_meson",
                "meson for the desktop client",
                "semver",
                d["desktop_meson"],
                r"meson_version:\s*'([^']+)'",
            ),
            self._pattern(
                "declared.desktop_glib",
                "glib-2.0 for the desktop client",
                "semver",
                d["desktop_meson"],
                r"dependency\('glib-2\.0',\s*version:\s*'([^']+)'",
            ),
            self._pattern(
                "declared.desktop_json_glib",
                "json-glib-1.0 for the desktop client",
                "semver",
                d["desktop_meson"],
                r"'json-glib-1\.0',\s*\n\s*version:\s*'([^']+)'",
            ),
            self._pattern(
                "declared.desktop_gtk4",
                "GTK 4 for the desktop GUI",
                "semver",
                d["desktop_meson"],
                r"dependency\('gtk4',\s*version:\s*'([^']+)'",
            ),
            self._pattern(
                "declared.desktop_libadwaita",
                "libadwaita for the desktop GUI",
                "semver",
                d["desktop_meson"],
                r"dependency\('libadwaita-1',\s*version:\s*'([^']+)'",
            ),
        ]


class Workspace:
    """Scratch directories for one measurement session: wheels, venvs, caches, a project.

    Everything here is regenerable, so it may live under the system temporary directory
    (sub-doctrine 10.h keeps only durable work off volatile storage); it is removed at the
    end of the session.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(tempfile.mkdtemp(prefix="vibey-specs-"))
        self.wheels = self.root / "dist"
        self.venvs: dict[str, Path] = {}
        self.wheel_paths: dict[str, Path] = {}

    def path(self, *parts: str) -> Path:
        target = self.root.joinpath(*parts)
        target.mkdir(parents=True, exist_ok=True)
        return target

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


class DirectorySize:
    """`du -sk`, in bytes, or None when the path is absent."""

    def __init__(self, runner: CommandRunnerInterface) -> None:
        self._runner = runner

    def bytes(self, path: Path) -> int | None:
        if not path.exists():
            return None
        result = self._runner.run(["du", "-sk", str(path)], timeout=300)
        head = str(result.stdout).split()
        return (
            int(head[0]) * 1024 if result.returncode == 0 and head and head[0].isdigit() else None
        )


class PackageBuilder:
    """Builds the engine and launcher wheels from this checkout, once per session."""

    def __init__(
        self, repo: Path, settings: SpecsSettings, runner: CommandRunnerInterface, ws: Workspace
    ):
        self._repo = repo
        self._settings = settings
        self._runner = runner
        self._ws = ws

    def build(self) -> tuple[dict[str, Path], str]:
        if self._ws.wheel_paths:
            return self._ws.wheel_paths, ""
        timeout = float(self._settings.install["install_timeout_s"])
        for name, project in (
            ("vibey-engine", self._settings.install["engine_project"]),
            ("krypton-app", self._settings.install["krypton_project"]),
        ):
            result = self._runner.run(
                [
                    "uv",
                    "build",
                    "--wheel",
                    "--out-dir",
                    str(self._ws.wheels),
                    str(self._repo / project),
                ],
                timeout=timeout,
            )
            if not result.ok:
                return {}, f"`uv build` of {name} failed: {result.tail()}"
        for wheel in sorted(self._ws.wheels.glob("*.whl")):
            key = "vibey-engine" if wheel.name.startswith("vibey_engine-") else "krypton-app"
            self._ws.wheel_paths[key] = wheel
        missing = {"vibey-engine", "krypton-app"} - set(self._ws.wheel_paths)
        if missing:
            return {}, f"no wheel produced for {', '.join(sorted(missing))}"
        return self._ws.wheel_paths, ""


class PythonFloorProbe(ProbeInterface):
    """Installs the engine wheel on each candidate interpreter and runs `vibey --version`."""

    name = "python"

    def __init__(
        self,
        settings: SpecsSettings,
        runner: CommandRunnerInterface,
        builder: PackageBuilder,
        ws: Workspace,
        figures: FigureFactory,
    ) -> None:
        self._settings = settings
        self._runner = runner
        self._builder = builder
        self._ws = ws
        self._figures = figures

    def run(self) -> list[Figure]:
        candidates = [str(v) for v in self._settings.install["python_candidates"]]
        method = "uv venv -p {v}; uv pip install <engine wheel>; vibey --version"
        wheels, why = self._builder.build()
        if why:
            return [
                self._figures.skipped(
                    f"python.{v}.install", f"vibey-engine on Python {v}", "verdict", method, why
                )
                for v in candidates
            ]
        timeout = float(self._settings.install["install_timeout_s"])
        downloads = str(self._settings.install["python_downloads"])
        cache = self._ws.path("cache-python-floor")
        out: list[Figure] = []
        for version in candidates:
            venv = self._ws.root / f"venv-py{version}"
            env = {"UV_CACHE_DIR": str(cache), "UV_PYTHON_DOWNLOADS": downloads}
            created = self._runner.run(
                ["uv", "venv", "-q", "-p", version, str(venv)], timeout=300, env=env
            )
            label = f"vibey-engine on Python {version}"
            fid = f"python.{version}.install"
            if not created.ok:
                out.append(
                    self._figures.skipped(
                        fid, label, "verdict", method, f"no Python {version}: {created.tail()}"
                    )
                )
                continue
            python = venv / "bin" / "python"
            real = str(self._runner.run([str(python), "--version"], timeout=30).stdout).strip()
            installed = self._runner.run(
                ["uv", "pip", "install", "-q", "-p", str(python), str(wheels["vibey-engine"])],
                timeout=timeout,
                env=env,
            )
            if not installed.ok:
                verdict = (
                    "refused" if "does not satisfy" in installed.stderr else "fails to install"
                )
                out.append(
                    self._figures.measured(
                        fid,
                        label,
                        verdict,
                        "verdict",
                        method,
                        {"interpreter": real},
                        note=installed.tail(2),
                    )
                )
                continue
            smoke = self._runner.run([str(venv / "bin" / "vibey"), "--version"], timeout=60)
            verdict = "works" if smoke.ok else "installs, fails to run"
            note = None if smoke.ok else smoke.tail(2)
            out.append(
                self._figures.measured(
                    fid, label, verdict, "verdict", method, {"interpreter": real}, note=note
                )
            )
        return out


class InstallFootprintProbe(ProbeInterface):
    """Cold install time, venv and cache size, package count and download bytes per target."""

    name = "install"

    def __init__(
        self,
        settings: SpecsSettings,
        runner: CommandRunnerInterface,
        builder: PackageBuilder,
        ws: Workspace,
        sizes: DirectorySize,
        figures: FigureFactory,
    ) -> None:
        self._settings = settings
        self._runner = runner
        self._builder = builder
        self._ws = ws
        self._sizes = sizes
        self._figures = figures

    def targets(self, wheels: Mapping[str, Path]) -> dict[str, list[str]]:
        engine = str(wheels.get("vibey-engine", "vibey-engine"))
        out: dict[str, list[str]] = {"vibey-engine": [engine]}
        for extra in self._settings.install["engine_extras"]:
            out[f"vibey-engine[{extra}]"] = [f"{engine}[{extra}]"]
        # krypton-app resolves vibey-engine[hub] from its own metadata; the local engine
        # wheel is named beside it so the resolver takes this checkout's engine, not PyPI's.
        out["krypton-app"] = [str(wheels.get("krypton-app", "krypton-app")), f"{engine}[hub]"]
        return out

    @staticmethod
    def ids(target: str) -> dict[str, tuple[str, str]]:
        return {
            "cold_s": (f"install.{target}.cold_s", "s"),
            "venv": (f"install.{target}.venv_bytes", "bytes"),
            "cache": (f"install.{target}.uv_cache_bytes", "bytes"),
            "packages": (f"install.{target}.packages", "count"),
            "download": (f"install.{target}.download_bytes", "bytes"),
        }

    def run(self) -> list[Figure]:
        wheels, why = self._builder.build()
        python = str(self._settings.install["footprint_python"])
        timeout = float(self._settings.install["install_timeout_s"])
        out: list[Figure] = []
        for target, specs in self.targets(wheels).items():
            ids = self.ids(target)
            method = f"uv venv -p {python}; UV_CACHE_DIR=<empty> uv pip install {target} (this checkout's wheels)"
            if why:
                out += [
                    self._figures.skipped(i, f"{target} {k}", u, method, why)
                    for k, (i, u) in ids.items()
                ]
                continue
            venv = self._ws.root / f"venv-{re.sub(r'[^a-z0-9]+', '-', target)}"
            cache = self._ws.root / f"cache-{venv.name}"
            env = {
                "UV_CACHE_DIR": str(cache),
                "UV_PYTHON_DOWNLOADS": str(self._settings.install["python_downloads"]),
            }
            created = self._runner.run(
                ["uv", "venv", "-q", "-p", python, str(venv)], timeout=300, env=env
            )
            installed = (
                self._runner.run(
                    ["uv", "pip", "install", "-q", "-p", str(venv / "bin" / "python"), *specs],
                    timeout=timeout,
                    env=env,
                )
                if created.ok
                else created
            )
            if not installed.ok:
                reason = f"install failed: {installed.tail()}"
                out += [
                    self._figures.skipped(i, f"{target} {k}", u, method, reason)
                    for k, (i, u) in ids.items()
                ]
                continue
            self._ws.venvs[target] = venv
            conditions = {"python": python, "cache": "empty"}
            listed = self._runner.run(
                ["uv", "pip", "list", "-p", str(venv / "bin" / "python"), "--format", "json"],
                timeout=120,
            )
            with contextlib.suppress(ValueError):
                count = len(json.loads(listed.stdout or "[]"))
                out.append(
                    self._figures.measured(
                        ids["packages"][0], f"{target} packages", count, "count", method, conditions
                    )
                )
            out.append(
                self._figures.measured(
                    ids["cold_s"][0],
                    f"{target} cold install",
                    round(installed.seconds, 1),
                    "s",
                    method,
                    conditions,
                )
            )
            for key, path in (("venv", venv), ("cache", cache)):
                size = self._sizes.bytes(path)
                fid, unit = ids[key]
                label = f"{target} {'installed size' if key == 'venv' else 'uv cache'}"
                if size is None:
                    out.append(
                        self._figures.skipped(
                            fid, label, unit, "du -sk", f"{path.name} not measurable"
                        )
                    )
                else:
                    out.append(
                        self._figures.measured(
                            fid, label, size, unit, "du -sk after the install above", conditions
                        )
                    )
            out.append(self._download(target, specs, venv, ids["download"][0]))
        return out

    def _download(self, target: str, specs: Sequence[str], venv: Path, fid: str) -> Figure:
        """Bytes on the wire: every artifact pip downloads for the target, summed."""
        method = "pip download --only-binary=:all: into an empty directory; sum of file sizes"
        dest = self._ws.root / f"download-{venv.name}"
        seeded = self._runner.run(
            ["uv", "pip", "install", "-q", "-p", str(venv / "bin" / "python"), "pip"], timeout=300
        )
        if not seeded.ok:
            return self._figures.skipped(
                fid, f"{target} download", "bytes", method, f"no pip: {seeded.tail()}"
            )
        fetched = self._runner.run(
            [
                str(venv / "bin" / "python"),
                "-m",
                "pip",
                "download",
                "-q",
                "--only-binary=:all:",
                "-d",
                str(dest),
                *specs,
            ],
            timeout=float(self._settings.install["install_timeout_s"]),
        )
        if not fetched.ok:
            return self._figures.skipped(
                fid, f"{target} download", "bytes", method, f"pip download failed: {fetched.tail()}"
            )
        total = sum(p.stat().st_size for p in dest.iterdir() if p.is_file())
        return self._figures.measured(
            fid,
            f"{target} download",
            total,
            "bytes",
            method,
            {"files": len(list(dest.iterdir()))},
            note="includes this checkout's locally built wheel(s)",
        )


class ScratchDatabase:
    """A database this session creates, uses and drops, and never one it did not create."""

    def __init__(self, admin_url: str, name: str, runner: CommandRunnerInterface) -> None:
        self._admin = admin_url
        self.name = name
        self._runner = runner
        self.created = False

    def sql(self, statement: str, database: str | None = None) -> CommandResult:
        url = self.url(database) if database else self._admin
        return self._runner.run(
            ["psql", url, "-X", "-At", "-v", "ON_ERROR_STOP=1", "-c", statement], timeout=120
        )

    def url(self, database: str | None = None) -> str:
        """The admin DSN pointed at `database` (the path component replaced)."""
        base, _, query = self._admin.partition("?")
        head, _, _ = base.rpartition("/") if base.count("/") > 2 else (base, "", "")
        target = f"{head}/{database or self.name}"
        return f"{target}?{query}" if query else target

    def create(self) -> str:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", self.name):
            return f"refusing an unsafe scratch database name {self.name!r}"
        result = self.sql(f'CREATE DATABASE "{self.name}"')
        if not result.ok:
            return f"could not create {self.name} (it is never reused or dropped if it exists): {result.tail()}"
        self.created = True
        return ""

    def drop(self) -> None:
        if self.created:
            self.sql(f'DROP DATABASE IF EXISTS "{self.name}"')
            self.created = False


class PostgresProbe(ProbeInterface):
    """The server version against the declared floor, and a real migration on a scratch
    database: how many migrations apply and how large the empty schema is."""

    name = "postgres"

    def __init__(
        self,
        settings: SpecsSettings,
        runner: CommandRunnerInterface,
        ws: Workspace,
        figures: FigureFactory,
        environ: Mapping[str, str] = os.environ,
    ) -> None:
        self._settings = settings
        self._runner = runner
        self._ws = ws
        self._figures = figures
        self._environ = environ
        self.database: ScratchDatabase | None = None

    def run(self) -> list[Figure]:
        pg = self._settings.postgres
        ids = {
            "postgres.server_version": ("PostgreSQL server", "version"),
            "postgres.migrations_applied": ("Migrations applied to an empty database", "count"),
            "postgres.empty_db_bytes": ("Empty migrated database", "bytes"),
        }
        admin = self._environ.get(str(pg["admin_url_env"]), "")
        method = f"psql against ${pg['admin_url_env']}; scratch database {pg['scratch_database']}"

        def skip_all(reason: str) -> list[Figure]:
            return [self._figures.skipped(i, lab, u, method, reason) for i, (lab, u) in ids.items()]

        if not admin:
            return skip_all(f"${pg['admin_url_env']} is not set")
        database = ScratchDatabase(admin, str(pg["scratch_database"]), self._runner)
        version = database.sql("SHOW server_version")
        if not version.ok:
            return skip_all(f"server unreachable: {version.tail()}")
        out = [
            self._figures.measured(
                "postgres.server_version",
                "PostgreSQL server",
                version.stdout.strip().split()[0],
                "version",
                "SHOW server_version",
            )
        ]
        why = database.create()
        if why:
            return out + [
                self._figures.skipped(i, lab, u, method, why)
                for i, (lab, u) in list(ids.items())[1:]
            ]
        self.database = database
        venv = self._ws.venvs.get("vibey-engine")
        if venv is None:
            reason = "no engine venv (the install probe did not produce one)"
            return out + [
                self._figures.skipped(i, lab, u, method, reason)
                for i, (lab, u) in list(ids.items())[1:]
            ]
        migrated = self._runner.run(
            [str(venv / "bin" / "vibey"), "migrate"],
            timeout=300,
            env={"VIBEY_PG_MIGRATE_URL": database.url(), "VIBEY_PG_URL": ""},
            cwd=str(self._ws.path("project")),
        )
        applied = re.search(r"applied (\d+) migration", migrated.stdout + migrated.stderr)
        if applied is None:
            reason = f"`vibey migrate` applied nothing: {migrated.tail()}"
            return out + [
                self._figures.skipped(i, lab, u, method, reason)
                for i, (lab, u) in list(ids.items())[1:]
            ]
        out.append(
            self._figures.measured(
                "postgres.migrations_applied",
                "Migrations applied to an empty database",
                int(applied.group(1)),
                "count",
                "vibey migrate on the scratch database (this checkout's wheel)",
                {"exit": migrated.returncode},
                note="a non-zero exit here is the ledger-guard reconcile when no app role is given",
            )
        )
        size = database.sql(f"SELECT pg_database_size('{database.name}')")
        if size.ok and size.stdout.strip().isdigit():
            out.append(
                self._figures.measured(
                    "postgres.empty_db_bytes",
                    "Empty migrated database",
                    int(size.stdout.strip()),
                    "bytes",
                    "pg_database_size",
                )
            )
        else:
            out.append(
                self._figures.skipped(
                    "postgres.empty_db_bytes",
                    "Empty migrated database",
                    "bytes",
                    method,
                    size.tail(),
                )
            )
        return out


class OllamaSizesProbe(ProbeInterface):
    """The Ollama server version and each model's download size from the registry."""

    name = "ollama"

    def __init__(
        self, settings: SpecsSettings, client: OllamaClient, figures: FigureFactory
    ) -> None:
        self._settings = settings
        self._client = client
        self._figures = figures

    def run(self) -> list[Figure]:
        out: list[Figure] = []
        try:
            out.append(
                self._figures.measured(
                    "ollama.version",
                    "Ollama server",
                    self._client.version(),
                    "version",
                    "GET /api/version",
                )
            )
        except (OSError, ValueError) as exc:
            out.append(
                self._figures.skipped(
                    "ollama.version",
                    "Ollama server",
                    "version",
                    "GET /api/version",
                    f"unreachable: {exc}",
                )
            )
        models = [self._settings.sovereign_model, *self._settings.ollama["optional_models"]]
        for model in models:
            fid = f"model.{model}.download_bytes"
            method = "registry manifest: sum of layer and config sizes (nothing pulled)"
            try:
                size = self._client.manifest_bytes(model)
            except (OSError, ValueError, KeyError) as exc:
                out.append(
                    self._figures.skipped(
                        fid, f"{model} download", "bytes", method, f"registry unreachable: {exc}"
                    )
                )
                continue
            out.append(self._figures.measured(fid, f"{model} download", size, "bytes", method))
        return out


class ModelBench(ProbeInterface):
    """Memory against context and throughput, GPU and CPU only, for the sovereign model.

    Ported from the 2026-09-29 hardware pass (`model_bench.py`, `hwlib.py`). For each
    context the model is unloaded, loaded at that `num_ctx`, and llama-server's own memory
    accounting is read from the log; then a deterministic prompt (seeded, tagged per run so
    the prompt cache cannot reuse it) is run at temperature 0, and Ollama's own counters
    give the rates. A run that overlapped another client's request is discarded. Nothing
    runs unless the idle gate says the host is quiet, and then only the model this probe
    loaded is unloaded.
    """

    name = "model"

    SENTENCES = (
        "The conductor claims a job from the queue, runs one phase and writes the result to the ledger.",
        "A worker that dies leaves its lease to expire so that another worker can pick the job up again.",
        "Every event in the ledger is appended and never updated, and corrections supersede older events.",
        "The design phase asks the operator questions and parks the job until a human answers the gate.",
        "The build phase runs unattended and repairs its own failures until the gate command passes.",
        "Rotation picks an engine by smooth weighted round robin among the engines that are eligible.",
        "The local model runs on the same machine, so no request ever leaves the loopback interface.",
        "Postgres holds the queue, and FOR UPDATE SKIP LOCKED lets many workers claim jobs safely.",
    )

    def __init__(
        self,
        settings: SpecsSettings,
        client: OllamaClient,
        gate: IdleGateInterface,
        log: LlamaServerLog,
        figures: FigureFactory,
    ) -> None:
        self._settings = settings
        self._client = client
        self._gate = gate
        self._log = log
        self._figures = figures

    @classmethod
    def prompt(cls, target_tokens: int, seed: int, chars_per_token: float, tag: str) -> str:
        """About `target_tokens` tokens of seeded filler; the same arguments give the same text."""
        rng = random.Random(seed)
        want = int(target_tokens * chars_per_token)
        task = "\n\nTask: explain the system described above, section by section, at length."
        parts = [f"Run {tag}.\n"]
        size = len(parts[0]) + len(task)
        section = 0
        while size < want:
            section += 1
            sentences = list(cls.SENTENCES)
            rng.shuffle(sentences)
            block = f"\nSection {section}. " + " ".join(sentences[: rng.randint(3, 7)]) + "\n"
            parts.append(block)
            size += len(block)
        return "".join(parts) + task

    def expected(self) -> list[tuple[str, str, str]]:
        """Every figure this probe reports, so a skip can name each one."""
        m, b = self._settings.sovereign_model, self._settings.bench
        out = [("gpu.working_set_limit_mib", "GPU working-set limit", "MiB")]
        for ctx in b["contexts"]:
            for key, label in (
                ("device_mib", "on the device (weights + KV + compute)"),
                ("kv_mib", "KV cache"),
                ("host_model_mib", "host model buffer"),
                ("host_compute_mib", "host compute buffer"),
            ):
                out.append((f"bench.{m}.ctx{ctx}.{key}", f"{m} at {ctx}: {label}", "MiB"))
            for key, label in (("prompt_tok_s", "prompt"), ("gen_tok_s", "generation")):
                out.append(
                    (f"bench.{m}.gpu.ctx{ctx}.{key}", f"{m} GPU at {ctx}: {label}", "tokens/s")
                )
        for ctx in b["depth_contexts"]:
            for key, label in (("prompt_tok_s", "prompt"), ("gen_tok_s", "generation")):
                out.append(
                    (
                        f"bench.{m}.depth.ctx{ctx}.{key}",
                        f"{m} GPU, prompt at depth, {ctx}: {label}",
                        "tokens/s",
                    )
                )
        for ctx in b["cpu_contexts"]:
            for key, label in (("prompt_tok_s", "prompt"), ("gen_tok_s", "generation")):
                out.append(
                    (f"bench.{m}.cpu.ctx{ctx}.{key}", f"{m} CPU only at {ctx}: {label}", "tokens/s")
                )
        return out

    def _skip_all(self, reason: str) -> list[Figure]:
        method = "model_bench (idle-gated Ollama load and timed chat)"
        return [self._figures.skipped(i, lab, u, method, reason) for i, lab, u in self.expected()]

    def _load(self, ctx: int, options: Mapping[str, Any]) -> dict[str, float]:
        model = self._settings.sovereign_model
        self._client.unload(model)
        offset = self._log.offset()
        self._client.call(
            "/api/generate",
            {"model": model, "keep_alive": "10m", "options": {"num_ctx": ctx, **options}},
        )
        return LlamaServerLog.accounting(self._log.since(offset))

    def _rates(
        self, ctx: int, target: int, options: Mapping[str, Any], tag: str
    ) -> tuple[list[dict[str, float]], int]:
        b = self._settings.bench
        clean: list[dict[str, float]] = []
        discarded = 0
        for run in range(int(b["runs"])):
            offset = self._gate.log_offset()
            reply = self._client.call(
                "/api/chat",
                {
                    "model": self._settings.sovereign_model,
                    "stream": False,
                    "keep_alive": "10m",
                    "messages": [
                        {
                            "role": "user",
                            "content": self.prompt(
                                target, int(b["seed"]), float(b["chars_per_token"]), f"{tag}-{run}"
                            ),
                        }
                    ],
                    "options": {
                        "num_ctx": ctx,
                        "temperature": 0,
                        "seed": int(b["seed"]),
                        "num_predict": int(b["num_predict"]),
                        **options,
                    },
                },
            )
            if self._gate.foreign_requests_since(offset) > 1:
                discarded += 1
                continue
            pe_n, pe_d = reply.get("prompt_eval_count", 0), reply.get("prompt_eval_duration", 0)
            ev_n, ev_d = reply.get("eval_count", 0), reply.get("eval_duration", 0)
            if pe_d and ev_d:
                clean.append(
                    {
                        "prompt": pe_n / (pe_d / 1e9),
                        "gen": ev_n / (ev_d / 1e9),
                        "prompt_tokens": pe_n,
                    }
                )
        return clean, discarded

    @staticmethod
    def _median(values: Sequence[float]) -> float:
        ordered = sorted(values)
        mid = len(ordered) // 2
        return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2

    def _rate_figures(
        self,
        kind: str,
        ctx: int,
        target: int,
        options: Mapping[str, Any],
        conditions: dict[str, Any],
    ) -> list[Figure]:
        m = self._settings.sovereign_model
        method = "POST /api/chat stream=false temperature=0 seed fixed; Ollama prompt_eval and eval counters; median of clean runs"
        labels = {"gpu": "GPU", "depth": "GPU, prompt at depth,", "cpu": "CPU only at"}
        runs, discarded = self._rates(ctx, target, options, f"{kind}{ctx}")
        out: list[Figure] = []
        for key, name in (("prompt", "prompt_tok_s"), ("gen", "gen_tok_s")):
            fid = f"bench.{m}.{kind}.ctx{ctx}.{name}"
            label = f"{m} {labels[kind]} {ctx}: {'prompt' if key == 'prompt' else 'generation'}"
            if not runs:
                out.append(
                    self._figures.skipped(
                        fid,
                        label,
                        "tokens/s",
                        method,
                        f"every run overlapped another client ({discarded})",
                    )
                )
                continue
            values = [r[key] for r in runs]
            cond = {
                **conditions,
                "runs_clean": len(runs),
                "runs_discarded": discarded,
                "prompt_tokens": sorted({int(r["prompt_tokens"]) for r in runs}),
                "range": [round(min(values), 2), round(max(values), 2)],
                "options": dict(options),
            }
            out.append(
                self._figures.measured(
                    fid, label, round(self._median(values), 1), "tokens/s", method, cond
                )
            )
        return out

    def run(self) -> list[Figure]:
        idle, reason, conditions = self._gate.wait()
        if not idle:
            return self._skip_all(reason)
        m, b = self._settings.sovereign_model, self._settings.bench
        out: list[Figure] = []
        try:
            for ctx in b["contexts"]:
                accounting = self._load(int(ctx), {})
                method = (
                    "llama-server common_memory_breakdown_print and buffer lines in the Ollama log"
                )
                for key, label in (
                    ("device_mib", "on the device (weights + KV + compute)"),
                    ("kv_mib", "KV cache"),
                    ("host_model_mib", "host model buffer"),
                    ("host_compute_mib", "host compute buffer"),
                ):
                    fid = f"bench.{m}.ctx{ctx}.{key}"
                    if key in accounting:
                        out.append(
                            self._figures.measured(
                                fid,
                                f"{m} at {ctx}: {label}",
                                accounting[key],
                                "MiB",
                                method,
                                conditions,
                            )
                        )
                    else:
                        out.append(
                            self._figures.skipped(
                                fid,
                                f"{m} at {ctx}: {label}",
                                "MiB",
                                method,
                                "no accounting line in the log",
                            )
                        )
                if "working_set_limit_mib" in accounting and not any(
                    f.id == "gpu.working_set_limit_mib" for f in out
                ):
                    out.append(
                        self._figures.measured(
                            "gpu.working_set_limit_mib",
                            "GPU working-set limit",
                            accounting["working_set_limit_mib"],
                            "MiB",
                            "llama-server free device memory (Metal recommendedMaxWorkingSetSize)",
                        )
                    )
                target = min(int(b["prompt_tokens"]), int(ctx) - int(b["num_predict"]) - 256)
                out += self._rate_figures("gpu", int(ctx), target, {}, conditions)
            for ctx in b["depth_contexts"]:
                self._load(int(ctx), {})
                target = int(float(b["fill"]) * int(ctx)) - int(b["num_predict"]) - 256
                out += self._rate_figures("depth", int(ctx), target, {}, conditions)
            for ctx in b["cpu_contexts"]:
                self._load(int(ctx), {"num_gpu": 0})
                target = min(int(b["prompt_tokens"]), int(ctx) - int(b["num_predict"]) - 256)
                out += self._rate_figures("cpu", int(ctx), target, {"num_gpu": 0}, conditions)
        except (OSError, ValueError) as exc:
            done = {f.id for f in out}
            out += [f for f in self._skip_all(f"Ollama failed mid-run: {exc}") if f.id not in done]
        finally:
            with contextlib.suppress(OSError, ValueError):
                self._client.unload(m)
        if not any(f.id == "gpu.working_set_limit_mib" for f in out):
            out += [
                f
                for f in self._skip_all("no working-set line in the log")
                if f.id == "gpu.working_set_limit_mib"
            ]
        return out


class ProcessFootprintProbe(ProbeInterface):
    """Peak RSS and wall time of the everyday CLI commands, and idle RSS of the hub and the
    Krypton launcher, on the scratch database."""

    name = "processes"

    def __init__(
        self,
        settings: SpecsSettings,
        runner: CommandRunnerInterface,
        ws: Workspace,
        figures: FigureFactory,
        postgres: PostgresProbe,
    ) -> None:
        self._settings = settings
        self._runner = runner
        self._ws = ws
        self._figures = figures
        self._postgres = postgres

    @staticmethod
    def parse_time(text: str) -> dict[str, float]:
        """`/usr/bin/time -l` (macOS) or `-v` (GNU) output: wall seconds and peak RSS."""
        out: dict[str, float] = {}
        mac_real = re.search(r"([\d.]+) real", text)
        mac_rss = re.search(r"(\d+)\s+maximum resident set size", text)
        gnu_rss = re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)
        gnu_wall = re.search(r"Elapsed \(wall clock\) time.*: ([\d:.]+)", text)
        if mac_real:
            out["wall_s"] = float(mac_real.group(1))
        if mac_rss:
            out["max_rss_mib"] = round(int(mac_rss.group(1)) / MIB, 1)
        if gnu_rss:
            out["max_rss_mib"] = round(int(gnu_rss.group(1)) / 1024, 1)
        if gnu_wall:
            parts = [float(p) for p in gnu_wall.group(1).split(":")]
            out["wall_s"] = round(sum(p * 60**i for i, p in enumerate(reversed(parts))), 2)
        return out

    def commands(self) -> dict[str, list[str]]:
        repo = str(self._ws.path("project", "repo"))
        return {
            "version": ["--version"],
            "new": [
                "new",
                "specs-probe",
                "--repo",
                repo,
                "--intake",
                "Add a greet() function that returns hello",
            ],
            "status": ["status"],
            "worker_once": ["worker", "--once", "--provider", "scripted"],
        }

    def run(self) -> list[Figure]:
        out: list[Figure] = []
        venv = self._ws.venvs.get("vibey-engine")
        database = self._postgres.database
        flag = "-l" if platform.system() == "Darwin" else "-v"
        method = f"/usr/bin/time {flag} (peak RSS of the largest process in the tree)"
        timeout = float(self._settings.processes["command_timeout_s"])
        repo = self._ws.path("project", "repo")
        self._runner.run(["git", "init", "-q", str(repo)], timeout=30)
        self._runner.run(
            ["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "chore: init"],
            timeout=30,
        )
        for name, args in self.commands().items():
            ids = (f"process.cli.{name}.max_rss_mib", f"process.cli.{name}.wall_s")
            label = f"vibey {' '.join(args[:3])}"
            if venv is None or database is None:
                why = "no engine venv" if venv is None else "no scratch database"
                out += [self._figures.skipped(ids[0], f"{label} peak RSS", "MiB", method, why)]
                out += [self._figures.skipped(ids[1], f"{label} wall", "s", method, why)]
                continue
            result = self._runner.run(
                ["/usr/bin/time", flag, str(venv / "bin" / "vibey"), *args],
                timeout=timeout,
                env={"VIBEY_PG_URL": database.url()},
                cwd=str(self._ws.path("project")),
            )
            parsed = self.parse_time(result.stderr)
            if not result.ok or "max_rss_mib" not in parsed:
                why = f"exit {result.returncode}: {result.tail()}"
                out += [self._figures.skipped(ids[0], f"{label} peak RSS", "MiB", method, why)]
                out += [self._figures.skipped(ids[1], f"{label} wall", "s", method, why)]
                continue
            out.append(
                self._figures.measured(
                    ids[0], f"{label} peak RSS", parsed["max_rss_mib"], "MiB", method
                )
            )
            out.append(
                self._figures.measured(ids[1], f"{label} wall", parsed["wall_s"], "s", method)
            )
        out += self._server(
            "serve",
            self._ws.venvs.get("vibey-engine[hub]"),
            ["serve"],
            int(self._settings.processes["serve_port"]),
        )
        krypton = self._ws.venvs.get("krypton-app")
        port = int(self._settings.processes["krypton_port"])
        out += self._server(
            "krypton", krypton, ["--no-browser", "--port", str(port)], port, binary="krypton"
        )
        return out

    def _server(
        self, name: str, venv: Path | None, args: list[str], port: int, binary: str = "vibey"
    ) -> list[Figure]:
        ids = (f"process.{name}.idle_rss_mib", f"process.{name}.startup_s")
        label = "vibey serve (hub)" if name == "serve" else "krypton --no-browser (launcher + hub)"
        method = f"start, poll /health/live, then sum RSS over the process tree once a second for {self._settings.processes['idle_s']} s idle"
        database = self._postgres.database
        if venv is None or database is None:
            why = "no venv for it" if venv is None else "no scratch database"
            return [
                self._figures.skipped(ids[0], f"{label} idle RSS", "MiB", method, why),
                self._figures.skipped(ids[1], f"{label} start-up", "s", method, why),
            ]
        state = self._ws.path(f"hub-{name}")
        state.chmod(0o700)
        project = self._ws.path(f"project-{name}")
        (project / "vibey.toml").write_text(
            f'[hub]\nlan = false\nport = {port}\nstate_dir = "{state}"\n', encoding="utf-8"
        )
        env = {
            **os.environ,
            "VIBEY_PG_URL": database.url(),
            "PATH": f"{venv / 'bin'}:{os.environ.get('PATH', '')}",
        }
        started = time.monotonic()
        process = subprocess.Popen(  # noqa: S603 - argv built here
            [str(venv / "bin" / binary), *args],
            cwd=str(project),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            deadline = started + float(self._settings.processes["startup_timeout_s"])
            up = False
            while time.monotonic() < deadline and process.poll() is None:
                with (
                    contextlib.suppress(OSError),
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/health/live", timeout=1) as r,  # noqa: S310
                ):
                    up = r.status == 200
                if up:
                    break
                time.sleep(0.25)
            startup = round(time.monotonic() - started, 2)
            if not up:
                why = f"no /health/live within {self._settings.processes['startup_timeout_s']} s (exit {process.poll()})"
                return [
                    self._figures.skipped(ids[0], f"{label} idle RSS", "MiB", method, why),
                    self._figures.skipped(ids[1], f"{label} start-up", "s", method, why),
                ]
            samples: list[float] = []
            for _ in range(int(self._settings.processes["idle_s"])):
                reading = self.tree_rss_mib(process.pid)
                if reading is not None:
                    samples.append(reading)
                time.sleep(1)
            if not samples:
                why = "the process table could not be read (ps failed), so no RSS was sampled"
                return [
                    self._figures.skipped(ids[0], f"{label} idle RSS", "MiB", method, why),
                    self._figures.measured(ids[1], f"{label} start-up", startup, "s", method),
                ]
            peak = max(samples)
            return [
                self._figures.measured(ids[0], f"{label} idle RSS", round(peak, 1), "MiB", method),
                self._figures.measured(ids[1], f"{label} start-up", startup, "s", method),
            ]
        finally:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, signal.SIGTERM)
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=15)
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, signal.SIGKILL)

    def tree_rss_mib(self, root: int) -> float | None:
        """Summed RSS of `root` and every descendant, or None when `ps` cannot be read or
        `root` is not in it -- never a zero that would pass for a measurement."""
        listing = self._runner.run(["ps", "-Ao", "pid,ppid,rss"], timeout=10)
        if listing.returncode != 0:
            return None
        rows: dict[int, tuple[int, int]] = {}
        for line in str(listing.stdout).splitlines()[1:]:
            parts = line.split()
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                rows[int(parts[0])] = (int(parts[1]), int(parts[2]))
        keep, frontier = set(), [root]
        while frontier:
            pid = frontier.pop()
            if pid in rows and pid not in keep:
                keep.add(pid)
                frontier += [child for child, (parent, _) in rows.items() if parent == pid]
        return sum(rows[pid][1] for pid in keep) / 1024 if keep else None


class DiskProbe(ProbeInterface):
    """Sizes the disk estimate counts that the other probes do not already measure."""

    name = "disk"

    def __init__(
        self,
        repo: Path,
        settings: SpecsSettings,
        runner: CommandRunnerInterface,
        sizes: DirectorySize,
        figures: FigureFactory,
    ):
        self._repo = repo
        self._settings = settings
        self._runner = runner
        self._sizes = sizes
        self._figures = figures

    def run(self) -> list[Figure]:
        out: list[Figure] = []
        app = Path(str(self._settings.ollama["app_path"]))
        size = self._sizes.bytes(app)
        if size is None:
            out.append(
                self._figures.skipped(
                    "disk.ollama_app_bytes",
                    "Ollama application",
                    "bytes",
                    f"du -sk {app}",
                    f"{app} is absent on this host",
                )
            )
        else:
            out.append(
                self._figures.measured(
                    "disk.ollama_app_bytes", "Ollama application", size, "bytes", f"du -sk {app}"
                )
            )
        counted = self._runner.run(
            ["git", "-C", str(self._repo), "count-objects", "-v"], timeout=60
        )
        pack = re.search(r"size-pack:\s*(\d+)", str(counted.stdout))
        if pack:
            out.append(
                self._figures.measured(
                    "disk.git_pack_mib",
                    "git objects (shared by every worktree)",
                    round(int(pack.group(1)) / 1024, 2),
                    "MiB",
                    "git count-objects -v (size-pack)",
                )
            )
        else:
            out.append(
                self._figures.skipped(
                    "disk.git_pack_mib",
                    "git objects (shared by every worktree)",
                    "MiB",
                    "git count-objects -v",
                    counted.tail(),
                )
            )
        return out


# ------------------------------------------------------------------------ derivations


@dataclass(frozen=True)
class Derivation:
    """One derived figure: its id, what it means, the inputs it reads and the arithmetic."""

    id: str
    label: str
    unit: str
    formula: str
    inputs: tuple[str, ...]
    compute: Callable[[Mapping[str, float]], Any]
    note: str | None = None


class Derivations(DerivationsInterface):
    """The requirements, computed from the measured figures with the arithmetic recorded.

    Inputs are figure ids or `assumption.<key>` (a value from `[minimum_specs.assumptions]`).
    A derived figure whose inputs include a stale one is itself stale, since the date of its
    oldest stale input; one whose inputs are missing keeps its previous value, marked stale,
    or is skipped when it never had one. The outcome is deterministic, so `check` can
    recompute it from the committed record and compare.
    """

    def __init__(self, settings: SpecsSettings) -> None:
        self._settings = settings

    def specs(self) -> list[Derivation]:
        m = self._settings.sovereign_model
        a = self._settings.assumptions
        sizes = [float(s) for s in a["memory_sizes_gb"]]
        vram = [float(s) for s in a["vram_sizes_gb"]]
        optional = list(self._settings.ollama["optional_models"])

        def round_up(value: float, options: Sequence[float]) -> float | None:
            return next((s for s in sorted(options) if s >= value), None)

        def model_process(ctx: int) -> Derivation:
            return Derivation(
                f"ram.model_process.ctx{ctx}",
                f"{m} process memory at {ctx:,} tokens",
                "GiB",
                "(device + host model buffer + host compute buffer) / 1024",
                (
                    f"bench.{m}.ctx{ctx}.device_mib",
                    f"bench.{m}.ctx{ctx}.host_model_mib",
                    f"bench.{m}.ctx{ctx}.host_compute_mib",
                ),
                lambda v, c=ctx: round(
                    (
                        v[f"bench.{m}.ctx{c}.device_mib"]
                        + v[f"bench.{m}.ctx{c}.host_model_mib"]
                        + v[f"bench.{m}.ctx{c}.host_compute_mib"]
                    )
                    / 1024,
                    2,
                ),
            )

        contexts = sorted(int(c) for c in self._settings.bench["contexts"])
        lo, hi = contexts[0], contexts[-1]
        conductor, runner = "declared.conductor_context_max", "declared.runner_context_window"
        out_tokens, timeout = "declared.conductor_output_tokens", "declared.ollama_timeout_s"
        depth = f"bench.{m}.depth.ctx32768"
        cpu = f"bench.{m}.cpu.ctx8192"
        gpu_short = f"bench.{m}.gpu.ctx{lo}"

        def turn(prompt_tokens: float, prompt_rate: float, out: float, gen_rate: float) -> float:
            return round(prompt_tokens / prompt_rate + out / gen_rate, 1)

        specs = [
            model_process(8192),
            model_process(32768),
            model_process(hi),
            Derivation(
                "ram.kv_per_token_kib",
                "KV cache growth per token",
                "KiB/token",
                f"(KV@{hi} - KV@{lo}) x 1024 / ({hi} - {lo})",
                (f"bench.{m}.ctx{hi}.kv_mib", f"bench.{m}.ctx{lo}.kv_mib"),
                lambda v: round(
                    (v[f"bench.{m}.ctx{hi}.kv_mib"] - v[f"bench.{m}.ctx{lo}.kv_mib"])
                    * 1024
                    / (hi - lo),
                    1,
                ),
            ),
            Derivation(
                "ram.vibey_side_gib",
                "vibey, the hub and Postgres beside the model",
                "GiB",
                "ceil((worker peak RSS + hub idle RSS + Postgres RSS peak) / 1024 / step) x step",
                (
                    "process.cli.worker_once.max_rss_mib",
                    "process.serve.idle_rss_mib",
                    "postgres.rss_peak_mib",
                    "assumption.vibey_side_step_gib",
                ),
                lambda v: (
                    math.ceil(
                        (
                            v["process.cli.worker_once.max_rss_mib"]
                            + v["process.serve.idle_rss_mib"]
                            + v["postgres.rss_peak_mib"]
                        )
                        / 1024
                        / v["assumption.vibey_side_step_gib"]
                    )
                    * v["assumption.vibey_side_step_gib"]
                ),
            ),
            Derivation(
                "ram.minimum_need_gib",
                "Memory needed: model at the runner's window + vibey + OS",
                "GiB",
                "model@32768 + vibey side + OS headroom",
                ("ram.model_process.ctx32768", "ram.vibey_side_gib", "assumption.os_headroom_gib"),
                lambda v: round(
                    v["ram.model_process.ctx32768"]
                    + v["ram.vibey_side_gib"]
                    + v["assumption.os_headroom_gib"],
                    2,
                ),
            ),
            Derivation(
                "ram.minimum_gb",
                "Minimum memory (unified, as sold)",
                "GB",
                "the smallest declared memory size >= the need",
                ("ram.minimum_need_gib",),
                lambda v: round_up(v["ram.minimum_need_gib"], sizes),
            ),
            Derivation(
                "ram.design_only_need_gib",
                "Memory needed for DESIGN alone (conductor ceiling)",
                "GiB",
                "model@8192 + vibey side + OS headroom",
                ("ram.model_process.ctx8192", "ram.vibey_side_gib", "assumption.os_headroom_gib"),
                lambda v: round(
                    v["ram.model_process.ctx8192"]
                    + v["ram.vibey_side_gib"]
                    + v["assumption.os_headroom_gib"],
                    2,
                ),
            ),
            Derivation(
                "ram.recommended_need_gib",
                "Memory needed at the model's maximum window, with room for other apps",
                "GiB",
                f"model@{hi} + vibey side + OS headroom + apps headroom",
                (
                    f"ram.model_process.ctx{hi}",
                    "ram.vibey_side_gib",
                    "assumption.os_headroom_gib",
                    "assumption.apps_headroom_gib",
                ),
                lambda v: round(
                    v[f"ram.model_process.ctx{hi}"]
                    + v["ram.vibey_side_gib"]
                    + v["assumption.os_headroom_gib"]
                    + v["assumption.apps_headroom_gib"],
                    2,
                ),
            ),
            Derivation(
                "ram.recommended_gb",
                "Recommended memory (unified, as sold)",
                "GB",
                "the smallest declared memory size >= the recommended need",
                ("ram.recommended_need_gib",),
                lambda v: round_up(v["ram.recommended_need_gib"], sizes),
            ),
            Derivation(
                "gpu.metal_limit_16gb_mib",
                "GPU working-set limit a 16 GB Mac would have at this host's ratio",
                "MiB",
                "16384 x working-set limit / (RAM in MiB)",
                ("gpu.working_set_limit_mib", "host.ram_bytes"),
                lambda v: round(
                    16384 * v["gpu.working_set_limit_mib"] / (v["host.ram_bytes"] / MIB)
                ),
                note="assumes macOS keeps the same fraction on 16 GB (widely reported as about 2/3 there; not verified)",
            ),
            Derivation(
                "gpu.over_16gb.ctx8192_mib",
                "GPU need over a 16 GB Mac's limit at 8,192",
                "MiB",
                "device@8192 - 16 GB limit (positive: cannot run fully on the GPU)",
                (f"bench.{m}.ctx8192.device_mib", "gpu.metal_limit_16gb_mib"),
                lambda v: round(v[f"bench.{m}.ctx8192.device_mib"] - v["gpu.metal_limit_16gb_mib"]),
            ),
            Derivation(
                "gpu.over_16gb.ctx32768_mib",
                "GPU need over a 16 GB Mac's limit at 32,768",
                "MiB",
                "device@32768 - 16 GB limit",
                (f"bench.{m}.ctx32768.device_mib", "gpu.metal_limit_16gb_mib"),
                lambda v: round(
                    v[f"bench.{m}.ctx32768.device_mib"] - v["gpu.metal_limit_16gb_mib"]
                ),
            ),
            Derivation(
                "ram.16gb_verdict",
                "Can a 16 GB Mac run the sovereign model at vibey's contexts?",
                "verdict",
                "insufficient when the DESIGN-only need exceeds 16 GiB",
                ("ram.design_only_need_gib",),
                lambda v: "insufficient" if v["ram.design_only_need_gib"] > 16 else "sufficient",
            ),
            Derivation(
                "gpu.discrete_vram_gb",
                "Discrete GPU memory (derived only; not verified on CUDA)",
                "GB",
                "the smallest declared VRAM size >= device@32768 / 1024",
                (f"bench.{m}.ctx32768.device_mib",),
                lambda v: round_up(v[f"bench.{m}.ctx32768.device_mib"] / 1024, vram),
            ),
            Derivation(
                "time.runner_turn_worst.gpu_s",
                "Worst BUILD turn on the GPU",
                "s",
                "(window - reply) / prompt rate at depth + reply / generation rate at depth",
                (runner, out_tokens, f"{depth}.prompt_tok_s", f"{depth}.gen_tok_s"),
                lambda v: turn(
                    v[runner] - v[out_tokens],
                    v[f"{depth}.prompt_tok_s"],
                    v[out_tokens],
                    v[f"{depth}.gen_tok_s"],
                ),
            ),
            Derivation(
                "time.runner_turn_worst.cpu_s",
                "Worst BUILD turn, CPU only (rates at 2k depth: optimistic)",
                "s",
                "(window - reply) / CPU prompt rate + reply / CPU generation rate",
                (runner, out_tokens, f"{cpu}.prompt_tok_s", f"{cpu}.gen_tok_s"),
                lambda v: turn(
                    v[runner] - v[out_tokens],
                    v[f"{cpu}.prompt_tok_s"],
                    v[out_tokens],
                    v[f"{cpu}.gen_tok_s"],
                ),
            ),
            Derivation(
                "time.conductor_worst.cpu_s",
                "Conductor's worst call with its retry, CPU only",
                "s",
                "(ceiling - reply) / CPU prompt rate + 2 x reply / CPU generation rate",
                (conductor, out_tokens, f"{cpu}.prompt_tok_s", f"{cpu}.gen_tok_s"),
                lambda v: turn(
                    v[conductor] - v[out_tokens],
                    v[f"{cpu}.prompt_tok_s"],
                    2 * v[out_tokens],
                    v[f"{cpu}.gen_tok_s"],
                ),
            ),
            Derivation(
                "time.design_call.cpu_s",
                "One DESIGN call, CPU only",
                "s",
                "DESIGN prompt / CPU prompt rate + DESIGN output / CPU generation rate",
                (
                    "design_call.prompt_tokens",
                    "design_call.output_tokens_max",
                    f"{cpu}.prompt_tok_s",
                    f"{cpu}.gen_tok_s",
                ),
                lambda v: turn(
                    v["design_call.prompt_tokens"],
                    v[f"{cpu}.prompt_tok_s"],
                    v["design_call.output_tokens_max"],
                    v[f"{cpu}.gen_tok_s"],
                ),
            ),
            Derivation(
                "time.design_call.gpu_s",
                "One DESIGN call on the GPU",
                "s",
                "DESIGN prompt / GPU prompt rate + DESIGN output / GPU generation rate",
                (
                    "design_call.prompt_tokens",
                    "design_call.output_tokens_max",
                    f"{gpu_short}.prompt_tok_s",
                    f"{gpu_short}.gen_tok_s",
                ),
                lambda v: turn(
                    v["design_call.prompt_tokens"],
                    v[f"{gpu_short}.prompt_tok_s"],
                    v["design_call.output_tokens_max"],
                    v[f"{gpu_short}.gen_tok_s"],
                ),
            ),
            Derivation(
                "cpu_only.design_fits",
                "A DESIGN call fits the timeout CPU only",
                "verdict",
                "DESIGN call CPU only <= per-request timeout",
                ("time.design_call.cpu_s", timeout),
                lambda v: v["time.design_call.cpu_s"] <= v[timeout],
            ),
            Derivation(
                "cpu_only.build_fits",
                "A worst BUILD turn and the conductor's retry fit the timeout CPU only",
                "verdict",
                "max(worst BUILD turn, conductor retry) CPU only <= per-request timeout",
                ("time.runner_turn_worst.cpu_s", "time.conductor_worst.cpu_s", timeout),
                lambda v: (
                    max(v["time.runner_turn_worst.cpu_s"], v["time.conductor_worst.cpu_s"])
                    <= v[timeout]
                ),
            ),
            Derivation(
                "throughput.minimum.turn_s",
                "Worst BUILD turn at the minimum rates",
                "s",
                "(window - reply) / minimum prompt rate + reply / minimum generation rate (must be <= timeout)",
                (
                    runner,
                    out_tokens,
                    "assumption.minimum_prompt_tok_s",
                    "assumption.minimum_gen_tok_s",
                    timeout,
                ),
                lambda v: turn(
                    v[runner] - v[out_tokens],
                    v["assumption.minimum_prompt_tok_s"],
                    v[out_tokens],
                    v["assumption.minimum_gen_tok_s"],
                ),
            ),
            Derivation(
                "throughput.minimum.fits",
                "The minimum rates keep the worst BUILD turn within the timeout",
                "verdict",
                "worst turn at the minimum rates <= per-request timeout",
                ("throughput.minimum.turn_s", timeout),
                lambda v: v["throughput.minimum.turn_s"] <= v[timeout],
            ),
            Derivation(
                "throughput.recommended.turn_s",
                "Worst BUILD turn at the recommended rates",
                "s",
                "(window - reply) / recommended prompt rate + reply / recommended generation rate",
                (
                    runner,
                    out_tokens,
                    "assumption.recommended_prompt_tok_s",
                    "assumption.recommended_gen_tok_s",
                ),
                lambda v: turn(
                    v[runner] - v[out_tokens],
                    v["assumption.recommended_prompt_tok_s"],
                    v[out_tokens],
                    v["assumption.recommended_gen_tok_s"],
                ),
            ),
            Derivation(
                "throughput.host_meets_recommended",
                "The measured host meets the recommended rates at depth",
                "verdict",
                "measured prompt and generation rates at depth >= the recommended rates",
                (
                    f"{depth}.prompt_tok_s",
                    f"{depth}.gen_tok_s",
                    "assumption.recommended_prompt_tok_s",
                    "assumption.recommended_gen_tok_s",
                ),
                lambda v: (
                    v[f"{depth}.prompt_tok_s"] >= v["assumption.recommended_prompt_tok_s"]
                    and v[f"{depth}.gen_tok_s"] >= v["assumption.recommended_gen_tok_s"]
                ),
            ),
            Derivation(
                "disk.minimum_need_gb",
                "Free disk needed",
                "GB",
                "model + Ollama app + base venv + uv cache + Postgres install + Postgres data allowance + git objects + minimum worktrees x one worktree",
                (
                    f"model.{m}.download_bytes",
                    "disk.ollama_app_bytes",
                    "install.vibey-engine.venv_bytes",
                    "install.vibey-engine.uv_cache_bytes",
                    "disk.postgres_install_bytes",
                    "assumption.postgres_data_allowance_gb",
                    "disk.git_pack_mib",
                    "assumption.minimum_worktrees",
                    "disk.worktree_bytes",
                ),
                lambda v: round(
                    (
                        v[f"model.{m}.download_bytes"]
                        + v["disk.ollama_app_bytes"]
                        + v["install.vibey-engine.venv_bytes"]
                        + v["install.vibey-engine.uv_cache_bytes"]
                        + v["disk.postgres_install_bytes"]
                        + v["disk.git_pack_mib"] * MIB
                        + v["assumption.minimum_worktrees"] * v["disk.worktree_bytes"]
                    )
                    / 1e9
                    + v["assumption.postgres_data_allowance_gb"],
                    1,
                ),
            ),
            Derivation(
                "disk.minimum_gb",
                "Minimum free disk",
                "GB",
                "the need rounded up to the next 10 GB",
                ("disk.minimum_need_gb",),
                lambda v: math.ceil(v["disk.minimum_need_gb"] / 10) * 10,
            ),
            Derivation(
                "disk.recommended_need_gb",
                "Free disk recommended",
                "GB",
                "minimum need + optional models + dev venv + further worktrees + room to re-pull the sovereign model",
                (
                    "disk.minimum_need_gb",
                    *[f"model.{o}.download_bytes" for o in optional],
                    "disk.dev_venv_bytes",
                    "assumption.recommended_worktrees",
                    "assumption.minimum_worktrees",
                    "disk.worktree_bytes",
                    f"model.{m}.download_bytes",
                ),
                lambda v: round(
                    v["disk.minimum_need_gb"]
                    + (
                        sum(v[f"model.{o}.download_bytes"] for o in optional)
                        + v["disk.dev_venv_bytes"]
                        + (
                            v["assumption.recommended_worktrees"]
                            - v["assumption.minimum_worktrees"]
                        )
                        * v["disk.worktree_bytes"]
                        + v[f"model.{m}.download_bytes"]
                    )
                    / 1e9,
                    1,
                ),
            ),
            Derivation(
                "disk.recommended_gb",
                "Recommended free disk",
                "GB",
                "the recommended need rounded up to the next 10 GB",
                ("disk.recommended_need_gb",),
                lambda v: math.ceil(v["disk.recommended_need_gb"] / 10) * 10,
            ),
            Derivation(
                "download.first_install_bytes",
                "First install on the wire: Krypton + hub + the sovereign model",
                "bytes",
                "krypton-app download + sovereign model download",
                ("install.krypton-app.download_bytes", f"model.{m}.download_bytes"),
                lambda v: int(
                    v["install.krypton-app.download_bytes"] + v[f"model.{m}.download_bytes"]
                ),
            ),
            Derivation(
                "python.floor",
                "Oldest Python vibey-engine installs and runs on",
                "version",
                "the oldest candidate whose verdict is `works`",
                tuple(f"python.{c}.install" for c in self._settings.install["python_candidates"]),
                lambda v: next(
                    (
                        c
                        for c in self._settings.install["python_candidates"]
                        if v[f"python.{c}.install"] == "works"
                    ),
                    "none",
                ),
            ),
        ]
        return specs

    def _inputs(
        self, spec: Derivation, figures: Mapping[str, Figure]
    ) -> tuple[dict[str, Any], list[str], list[Figure]]:
        values: dict[str, Any] = {}
        missing: list[str] = []
        stale: list[Figure] = []
        for name in spec.inputs:
            if name.startswith("assumption."):
                key = name.split(".", 1)[1]
                if key in self._settings.assumptions:
                    values[name] = self._settings.assumptions[key]
                else:
                    missing.append(name)
                continue
            figure = figures.get(name)
            if figure is None or not figure.has_value:
                missing.append(name)
                continue
            values[name] = figure.value
            if figure.status == "stale":
                stale.append(figure)
        return values, missing, stale

    def derive(self, figures: Mapping[str, Figure]) -> list[Figure]:
        known: dict[str, Figure] = dict(figures)
        out: list[Figure] = []
        for spec in self.specs():
            values, missing, stale = self._inputs(spec, known)
            previous = figures.get(spec.id)
            computed: Any = None
            failure = ""
            if not missing:
                try:
                    computed = spec.compute(values)
                except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
                    # e.g. a configuration with one context has no KV slope to take
                    failure = f"cannot compute from these inputs: {exc!r}"
            if missing or failure:
                reason = failure or "missing input(s): " + ", ".join(missing)
                last_good = (
                    previous.stale_since or previous.measured_at if previous is not None else None
                )
                if previous is not None and previous.has_value and last_good:
                    figure = replace(
                        previous,
                        status="stale",
                        was="derived",
                        stale_since=last_good,
                        reason=reason,
                    )
                else:
                    figure = Figure(
                        spec.id,
                        spec.label,
                        None,
                        spec.unit,
                        "skipped",
                        "derived",
                        formula=spec.formula,
                        inputs={},
                        reason=reason,
                        note=spec.note,
                    )
            else:
                dated = [
                    known[i].measured_at for i in spec.inputs if i in known and known[i].measured_at
                ]
                figure = Figure(
                    id=spec.id,
                    label=spec.label,
                    value=computed,
                    unit=spec.unit,
                    status="derived",
                    method="derived",
                    measured_at=max(dated) if dated else None,
                    formula=spec.formula,
                    inputs=values,
                    note=spec.note,
                )
                if stale:
                    since = min(str(f.stale_since) for f in stale)  # a stale figure always has one
                    figure = replace(
                        figure,
                        status="stale",
                        was="derived",
                        stale_since=since,
                        reason="derived from stale input(s): " + ", ".join(f.id for f in stale),
                    )
            known[spec.id] = figure
            out.append(figure)
        return out

    def ids(self) -> set[str]:
        return {spec.id for spec in self.specs()}


# ------------------------------------------------------------------------ staleness


class StalenessPolicy(StalenessPolicyInterface):
    """A measurement that could not run keeps its last value, marked stale -- never reused
    silently. A `once` figure the weekly probes never re-measure keeps its own date."""

    def __init__(
        self, derived_ids: set[str], unreported: str = "not reported by this run's probes"
    ) -> None:
        self._derived = derived_ids
        self._unreported = unreported

    def merge(self, previous: Sequence[Figure], fresh: Sequence[Figure]) -> list[Figure]:
        now = {f.id: f for f in fresh}
        out: dict[str, Figure] = {}
        for old in previous:
            if old.id in self._derived:
                continue  # recomputed by the derivations from the merged inputs
            new = now.pop(old.id, None)
            if new is not None and new.status != "skipped":
                out[old.id] = new  # re-measured this week, so it is weekly from now on
                continue
            if new is None and old.cadence == "once":
                out[old.id] = old
                continue
            reason = new.reason if new is not None and new.reason else self._unreported
            last_good = old.stale_since or old.measured_at
            if old.has_value and last_good:
                out[old.id] = replace(
                    old,
                    status="stale",
                    was=old.basis,
                    stale_since=last_good,
                    reason=reason,
                    cadence="weekly",
                )
            else:
                out[old.id] = new if new is not None else old.skipped(reason)
        for fid, new in now.items():
            if fid not in self._derived:
                out[fid] = new
        return sorted(out.values(), key=lambda f: f.id)


# ------------------------------------------------------------------------ rendering


class Formatter:
    """How a figure reads in a table, with its status spelled out when it is not current."""

    @staticmethod
    def number(value: float, digits: int = 1) -> str:
        if float(value).is_integer() and digits == 0:
            return f"{int(value):,}"
        return f"{value:,.{digits}f}"

    @classmethod
    def value(cls, figure: Figure) -> str:
        v, unit = figure.value, figure.unit
        if isinstance(v, bool):
            return "yes" if v else "no"
        if unit == "bytes":
            return f"{v / 1e9:.2f} GB" if v >= 1e9 else f"{v / 1e6:.1f} MB"
        if unit == "GiB":
            return f"{v:.2f} GiB"
        if unit == "GB":
            return f"{v:g} GB"
        if unit == "MiB":
            return f"{cls.number(v, 0 if v >= 100 else 1)} MiB"
        if unit == "tokens/s":
            return f"{cls.number(v, 0 if v >= 100 else 1)} tok/s"
        if unit == "s":
            return f"{cls.number(v, 0 if v >= 100 else 1)} s"
        if unit in ("count", "tokens"):
            return f"{int(v):,}"
        return str(v)

    @staticmethod
    def day(stamp: str | None) -> str:
        return (stamp or "unknown")[:10]

    @classmethod
    def cell(cls, figure: Figure | None) -> str:
        if figure is None:
            return "not measured"
        if figure.status == "skipped":
            return f"not measured ({figure.reason})"
        text = cls.value(figure)
        if figure.status == "stale":
            return f"{text} (stale since {cls.day(figure.stale_since)}: {figure.reason})"
        return text


@dataclass(frozen=True)
class Row:
    """One table row: a requirement, its minimum and recommended cells, how they are known."""

    label: str
    minimum: str
    recommended: str
    basis: str
    figures: tuple[str, ...]


class RequirementTables:
    """The rows every rendering shares, composed from the record's figures."""

    def __init__(self, record: SpecsRecord, settings: SpecsSettings) -> None:
        self._f = record.by_id()
        self._settings = settings
        self._record = record

    def get(self, fid: str) -> Figure | None:
        return self._f.get(fid)

    def c(self, fid: str) -> str:
        return Formatter.cell(self._f.get(fid))

    def basis(self, *fids: str) -> str:
        kinds = []
        for fid in fids:
            figure = self._f.get(fid)
            kind = "not measured" if figure is None or figure.status == "skipped" else figure.basis
            if figure is not None and figure.status == "stale":
                kind = f"{figure.basis}, stale"
            if kind not in kinds:
                kinds.append(kind)
        return "; ".join(kinds)

    def row(self, label: str, minimum: str, recommended: str, fids: Sequence[str]) -> Row:
        return Row(label, minimum, recommended, self.basis(*fids), tuple(fids))

    def hardware(self) -> list[Row]:
        m = self._settings.sovereign_model
        depth = f"bench.{m}.depth.ctx32768"
        cpu = f"bench.{m}.cpu.ctx8192"
        return [
            self.row(
                "Memory, Apple Silicon (unified)",
                f"{self.c('ram.minimum_gb')} (needs {self.c('ram.minimum_need_gib')})",
                f"{self.c('ram.recommended_gb')} (needs {self.c('ram.recommended_need_gib')})",
                [
                    "ram.minimum_gb",
                    "ram.minimum_need_gib",
                    "ram.recommended_gb",
                    "ram.recommended_need_gib",
                ],
            ),
            self.row(
                "Memory, 16 GB Mac",
                f"{self.c('ram.16gb_verdict')}: DESIGN alone needs {self.c('ram.design_only_need_gib')}; "
                f"the GPU part is {self.c('gpu.over_16gb.ctx8192_mib')} over its limit at 8,192",
                "-",
                ["ram.16gb_verdict", "ram.design_only_need_gib", "gpu.over_16gb.ctx8192_mib"],
            ),
            self.row(
                f"GPU memory for {m}",
                f"{self.c(f'bench.{m}.ctx8192.device_mib')} at 8,192; {self.c(f'bench.{m}.ctx32768.device_mib')} at 32,768",
                f"discrete GPU: {self.c('gpu.discrete_vram_gb')} card (not verified on CUDA)",
                [
                    f"bench.{m}.ctx8192.device_mib",
                    f"bench.{m}.ctx32768.device_mib",
                    "gpu.discrete_vram_gb",
                ],
            ),
            self.row(
                "Model throughput at 24k depth",
                f"{self._assume('minimum_gen_tok_s')} tok/s generation, {self._assume('minimum_prompt_tok_s')} tok/s prompt "
                f"(worst BUILD turn {self.c('throughput.minimum.turn_s')} of {self.c('declared.ollama_timeout_s')})",
                f"{self._assume('recommended_gen_tok_s')} / {self._assume('recommended_prompt_tok_s')} tok/s "
                f"(worst turn {self.c('throughput.recommended.turn_s')}); measured here "
                f"{self.c(f'{depth}.gen_tok_s')} / {self.c(f'{depth}.prompt_tok_s')}",
                [
                    "throughput.minimum.turn_s",
                    "throughput.recommended.turn_s",
                    f"{depth}.gen_tok_s",
                ],
            ),
            self.row(
                "CPU only (no GPU)",
                f"DESIGN call {self.c('time.design_call.cpu_s')} (fits: {self.c('cpu_only.design_fits')}); "
                f"worst BUILD turn {self.c('time.runner_turn_worst.cpu_s')} (fits: {self.c('cpu_only.build_fits')})",
                f"use a GPU; CPU only measured {self.c(f'{cpu}.gen_tok_s')} generation, {self.c(f'{cpu}.prompt_tok_s')} prompt",
                ["time.design_call.cpu_s", "time.runner_turn_worst.cpu_s", f"{cpu}.gen_tok_s"],
            ),
            self.row(
                "Free disk",
                f"{self.c('disk.minimum_gb')} (needs {self.c('disk.minimum_need_gb')})",
                f"{self.c('disk.recommended_gb')} (needs {self.c('disk.recommended_need_gb')})",
                ["disk.minimum_gb", "disk.recommended_gb"],
            ),
            self.row(
                "PostgreSQL memory",
                f"summed RSS peak {self.c('postgres.rss_peak_mib')} (default shared_buffers suffices)",
                "-",
                ["postgres.rss_peak_mib"],
            ),
            self.row(
                "vibey processes",
                f"CLI {self.c('process.cli.status.max_rss_mib')}; worker {self.c('process.cli.worker_once.max_rss_mib')}; "
                f"hub idle {self.c('process.serve.idle_rss_mib')}",
                f"Krypton launcher + hub idle {self.c('process.krypton.idle_rss_mib')}",
                [
                    "process.cli.status.max_rss_mib",
                    "process.cli.worker_once.max_rss_mib",
                    "process.serve.idle_rss_mib",
                    "process.krypton.idle_rss_mib",
                ],
            ),
        ]

    def software(self) -> list[Row]:
        m = self._settings.sovereign_model
        working = [
            c
            for c in self._settings.install["python_candidates"]
            if (f := self._f.get(f"python.{c}.install")) is not None
            and f.has_value
            and f.value == "works"
        ]
        return [
            self.row(
                "Python",
                f"{self.c('python.floor')} (declared {self.c('declared.python_requires')})",
                f"works on {', '.join(working) or 'none measured'}",
                ["python.floor", "declared.python_requires"],
            ),
            self.row(
                "PostgreSQL",
                f"{self.c('declared.postgres_min_major')} (checked on connect)",
                f"measured on {self.c('postgres.server_version')}: {self.c('postgres.migrations_applied')} migrations applied",
                [
                    "declared.postgres_min_major",
                    "postgres.server_version",
                    "postgres.migrations_applied",
                ],
            ),
            self.row(
                f"Ollama with {m} (sovereign default)",
                f"required unless a paid engine is set up; measured on {self.c('ollama.version')}",
                "-",
                ["ollama.version"],
            ),
            self.row("git", f"{self.c('declared.git_floor')}", "-", ["declared.git_floor"]),
        ]

    def network(self) -> list[Row]:
        m = self._settings.sovereign_model
        optional = list(self._settings.ollama["optional_models"])
        extra = "; ".join(f"{o} {self.c(f'model.{o}.download_bytes')} (opt-in)" for o in optional)
        return [
            self.row(
                "Install download, vibey-engine",
                self.c("install.vibey-engine.download_bytes"),
                f"with [hub] {self.c('install.vibey-engine[hub].download_bytes')}; krypton-app {self.c('install.krypton-app.download_bytes')}",
                ["install.vibey-engine.download_bytes", "install.krypton-app.download_bytes"],
            ),
            self.row(
                "Installed size, vibey-engine",
                self.c("install.vibey-engine.venv_bytes"),
                f"krypton-app {self.c('install.krypton-app.venv_bytes')}",
                ["install.vibey-engine.venv_bytes", "install.krypton-app.venv_bytes"],
            ),
            self.row(
                f"Model download, {m}",
                self.c(f"model.{m}.download_bytes"),
                extra or "-",
                [f"model.{m}.download_bytes"],
            ),
            self.row(
                "First install on the wire",
                self.c("download.first_install_bytes"),
                "-",
                ["download.first_install_bytes"],
            ),
            self.row(
                "Internet at runtime (sovereign path)",
                self.c("network.runtime_internet"),
                "-",
                ["network.runtime_internet"],
            ),
        ]

    def clients(self) -> list[Row]:
        return [
            self.row(
                "krypton-app (launcher)",
                f"Python {self.c('python.floor')}; pulls vibey-engine[hub]",
                "-",
                ["python.floor"],
            ),
            self.row(
                "VS Code extension",
                f"VS Code {self.c('declared.vscode_engine')}; Node {self.c('declared.vscode_node')} to build",
                f"Node {self.c('declared.node_recommended')}",
                ["declared.vscode_engine", "declared.vscode_node", "declared.node_recommended"],
            ),
            self.row(
                "React Native app (mobile, web)",
                f"Node {self.c('declared.app_node')}",
                f"Node {self.c('declared.node_recommended')}",
                ["declared.app_node", "declared.node_recommended"],
            ),
            self.row(
                "Desktop (C, GTK 4)",
                f"meson {self.c('declared.desktop_meson')}; glib {self.c('declared.desktop_glib')}; "
                f"json-glib {self.c('declared.desktop_json_glib')}",
                f"GUI: gtk4 {self.c('declared.desktop_gtk4')}, libadwaita {self.c('declared.desktop_libadwaita')}",
                ["declared.desktop_meson", "declared.desktop_gtk4", "declared.desktop_libadwaita"],
            ),
        ]

    def paper(self) -> list[Row]:
        hw, sw, net = self.hardware(), self.software(), self.network()
        return [
            hw[0],
            hw[1],
            hw[2],
            hw[3],
            hw[4],
            hw[5],
            sw[0],
            sw[1],
            sw[2],
            net[2],
            net[0],
            net[4],
        ]

    def _assume(self, key: str) -> str:
        return f"{self._settings.assumptions[key]:g}"

    def provenance(self, rows: Sequence[Row]) -> tuple[str, str]:
        """The hosts and the date range of every dated figure behind `rows`, inputs included."""
        ids: set[str] = set()
        frontier = [fid for row in rows for fid in row.figures]
        while frontier:
            fid = frontier.pop()
            if fid in ids:
                continue
            ids.add(fid)
            figure = self._f.get(fid)
            if figure is not None and figure.inputs:
                frontier += [k for k in figure.inputs if not k.startswith("assumption.")]
        dates = sorted(
            Formatter.day(f.measured_at)
            for fid in ids
            if (f := self._f.get(fid)) and f.measured_at and f.basis == "measured"
        )
        hosts = sorted({f.host for fid in ids if (f := self._f.get(fid)) and f.host})
        span = (
            f"{dates[0]} to {dates[-1]}"
            if dates and dates[0] != dates[-1]
            else (dates[0] if dates else "no measured figure")
        )
        return ", ".join(hosts) or "no host recorded", span


class GeneratedBlocks:
    """The marker convention: `<!-- BEGIN GENERATED specs:NAME — regenerated by SCRIPT -->`."""

    PATTERN = re.compile(
        r"<!-- BEGIN GENERATED specs:(?P<name>[a-z0-9-]+) — regenerated by "
        + re.escape(SCRIPT)
        + r" -->\n(?P<body>.*?)<!-- END GENERATED specs:(?P=name) -->",
        re.DOTALL,
    )

    @classmethod
    def wrap(cls, name: str, body: str) -> str:
        return (
            f"<!-- BEGIN GENERATED specs:{name} — regenerated by {SCRIPT} -->\n"
            f"{body.rstrip()}\n<!-- END GENERATED specs:{name} -->"
        )

    @classmethod
    def names(cls, document: str) -> list[str]:
        return [m["name"] for m in cls.PATTERN.finditer(document)]

    @classmethod
    def replace_all(cls, document: str, blocks: Mapping[str, str]) -> str:
        return cls.PATTERN.sub(
            lambda m: cls.wrap(m["name"], blocks[m["name"]]) if m["name"] in blocks else m.group(0),
            document,
        )

    @classmethod
    def drift(cls, document: str, blocks: Mapping[str, str]) -> list[str]:
        present = {m["name"]: m["body"] for m in cls.PATTERN.finditer(document)}
        return sorted(
            name
            for name, body in blocks.items()
            if name not in present or present[name].rstrip() != body.rstrip()
        )


class DocsRenderer(RequirementsRendererInterface):
    """The reference page: one Markdown table per area, plus what was not verified."""

    def __init__(self, settings: SpecsSettings) -> None:
        self._settings = settings

    @staticmethod
    def _cell(text: str) -> str:
        return text.replace("|", "\\|")

    def _table(self, tables: RequirementTables, rows: Sequence[Row]) -> str:
        host, span = tables.provenance(rows)
        head = (
            f"*Measured on {host}; figures dated {span} (UTC). Source: "
            f"[`{self._settings.record}`](https://github.com/the-vibey-project/vibey/blob/develop/{self._settings.record}), "
            f"regenerated by `{SCRIPT}`; do not edit inside these markers.*\n\n"
            "| Requirement | Minimum | Recommended | Basis |\n|---|---|---|---|\n"
        )
        body = "".join(
            f"| {self._cell(r.label)} | {self._cell(r.minimum)} | {self._cell(r.recommended)} | {self._cell(r.basis)} |\n"
            for r in rows
        )
        return head + body

    def blocks(self, record: SpecsRecord) -> dict[str, str]:
        t = RequirementTables(record, self._settings)
        stale = [
            f
            for f in sorted(record.figures, key=lambda f: f.id)
            if f.status in ("stale", "skipped")
        ]
        status = (
            "*Every figure in the record is current: none is stale or skipped.*\n"
            if not stale
            else "| Figure | Status | Since | Reason |\n|---|---|---|---|\n"
            + "".join(
                f"| `{f.id}` | {f.status} | {Formatter.day(f.stale_since) if f.status == 'stale' else '-'} | {self._cell(f.reason or '')} |\n"
                for f in stale
            )
        )
        unverified = (
            "".join(f"- {item}\n" for item in record.not_verified) or "- nothing recorded\n"
        )
        return {
            "hardware": self._table(t, t.hardware()),
            "software": self._table(t, t.software()),
            "network": self._table(t, t.network()),
            "clients": self._table(t, t.clients()),
            "status": f"*Record generated {record.generated_at}.*\n\n{status}",
            "not-verified": unverified,
        }

    def apply(self, document: str, record: SpecsRecord) -> str:
        return GeneratedBlocks.replace_all(document, self.blocks(record))

    def drift(self, document: str, record: SpecsRecord) -> list[str]:
        return GeneratedBlocks.drift(document, self.blocks(record))


class PaperRenderer(RequirementsRendererInterface):
    """The paper's requirements table: a LaTeX `table*` in a ```latex fence, numbered by TeX
    like the paper's other table, its caption naming the host and the measurement dates."""

    LABEL = "tab:minimum-requirements"

    def __init__(self, settings: SpecsSettings) -> None:
        self._settings = settings

    #: Every character TeX treats specially, and the two a TeX text font may lack.
    _TEX: Mapping[str, str] = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "$": r"\$",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        # A bracket right after `\\` would be read as the row's optional argument.
        "[": "{[}",
        "]": "{]}",
        "·": r"$\cdot$",
        "`": "",
    }

    @classmethod
    def tex(cls, text: str) -> str:
        out = "".join(cls._TEX.get(ch, ch) for ch in text)
        return out.replace(">=", r"$\geq$").replace("<=", r"$\leq$")

    def blocks(self, record: SpecsRecord) -> dict[str, str]:
        t = RequirementTables(record, self._settings)
        rows = t.paper()
        host, span = t.provenance(rows)
        lines = [
            "```latex",
            r"\begin{table*}[t]",
            r"\centering\footnotesize",
            r"\begin{tabular}{@{}p{1.3in}p{2.3in}p{2.0in}p{0.9in}@{}}",
            r"\textbf{Requirement} & \textbf{Minimum} & \textbf{Recommended} & \textbf{Basis}\\",
            r"\hline",
        ]
        for row in rows:
            lines.append(
                " & ".join(
                    self.tex(c) for c in (row.label, row.minimum, row.recommended, row.basis)
                )
                + r"\\"
            )
        lines += [
            r"\end{tabular}",
            r"\caption{Minimum and recommended requirements for the sovereign default (vibey, "
            + self.tex(self._settings.sovereign_model)
            + r" on Ollama and PostgreSQL on one host), as the weekly measurement last recorded them. "
            + f"Measured on {self.tex(host)}, figures dated {self.tex(span)} (UTC); record "
            + r"\texttt{"
            + self.tex(self._settings.record)
            + r"}. A stale figure is the last good value, marked with the date it was last measured.}",
            rf"\label{{{self.LABEL}}}",
            r"\end{table*}",
            "```",
        ]
        return {"minimum-requirements": "\n".join(lines)}

    def apply(self, document: str, record: SpecsRecord) -> str:
        return GeneratedBlocks.replace_all(document, self.blocks(record))

    def drift(self, document: str, record: SpecsRecord) -> list[str]:
        return GeneratedBlocks.drift(document, self.blocks(record))


# ------------------------------------------------------------------------ the session


class MeasurementSession:
    """Runs every probe in order, merges with the previous record, derives, and returns the
    new record. The scratch database and the scratch directory are always cleaned up."""

    def __init__(
        self,
        repo: Path,
        settings: SpecsSettings,
        runner: CommandRunnerInterface | None = None,
        clock: ClockInterface | None = None,
        environ: Mapping[str, str] = os.environ,
        only: Sequence[str] = (),
    ) -> None:
        self._repo = repo
        self._settings = settings
        self._runner = runner or SubprocessRunner()
        self._clock = clock or SystemClock()
        self._environ = environ
        self._only = set(only)

    def _probes(
        self, figures: FigureFactory, ws: Workspace, postgres_holder: list[PostgresProbe]
    ) -> Iterator[ProbeInterface]:
        s = self._settings
        sizes = DirectorySize(self._runner)
        builder = PackageBuilder(self._repo, s, self._runner, ws)
        url = self._environ.get(str(s.ollama["url_env"])) or str(s.ollama["default_url"])
        client = OllamaClient(url, str(s.ollama["registry"]), float(s.bench["request_timeout_s"]))
        log = LlamaServerLog(Path(os.path.expanduser(str(s.ollama["server_log"]))))
        postgres = PostgresProbe(s, self._runner, ws, figures, self._environ)
        postgres_holder.append(postgres)
        yield DeclaredFloorsProbe(self._repo, s, figures)
        yield PythonFloorProbe(s, self._runner, builder, ws, figures)
        yield InstallFootprintProbe(s, self._runner, builder, ws, sizes, figures)
        yield postgres
        yield ProcessFootprintProbe(s, self._runner, ws, figures, postgres)
        yield OllamaSizesProbe(s, client, figures)
        yield ModelBench(s, client, IdleGate(s.idle, log, self._runner), log, figures)
        yield DiskProbe(self._repo, s, self._runner, sizes, figures)

    def run(self, previous: SpecsRecord | None) -> SpecsRecord:
        info = HostDescriber(self._runner).describe()
        host = HostDescriber.host_id(info)
        figures = FigureFactory(self._clock, host)
        ws = Workspace()
        holder: list[PostgresProbe] = []
        fresh: list[Figure] = []
        crashed: list[str] = []
        try:
            for probe in self._probes(figures, ws, holder):
                if self._only and probe.name not in self._only:
                    continue
                print(f"{SCRIPT}: probe {probe.name} ...", file=sys.stderr)
                try:
                    fresh += probe.run()
                except Exception as exc:  # noqa: BLE001 - one probe's crash must not lose the rest
                    # Its figures are then not reported, so the merge keeps their last
                    # values marked stale; the crash itself is said out loud here.
                    print(f"{SCRIPT}: probe {probe.name} crashed: {exc!r}", file=sys.stderr)
                    crashed.append(f"{probe.name}: {exc!r}")
        finally:
            for postgres in holder:
                if postgres.database is not None:
                    postgres.database.drop()
            ws.cleanup()
        if info.get("ram_bytes"):
            fresh.append(
                figures.measured(
                    "host.ram_bytes",
                    "Host memory",
                    info["ram_bytes"],
                    "bytes",
                    "sysctl hw.memsize / MemTotal",
                )
            )
        unreported = "not reported by this run's probes" + (
            f" (crashed: {'; '.join(crashed)})" if crashed else ""
        )
        return RecordBuilder(self._settings, self._clock).build(
            previous, fresh, {host: info}, unreported=unreported
        )


class RecordBuilder:
    """Merge, derive, stamp: the one path every record takes, seeded or measured."""

    def __init__(self, settings: SpecsSettings, clock: ClockInterface) -> None:
        self._settings = settings
        self._clock = clock

    def build(
        self,
        previous: SpecsRecord | None,
        fresh: Sequence[Figure],
        hosts: Mapping[str, Mapping[str, Any]],
        unreported: str = "not reported by this run's probes",
    ) -> SpecsRecord:
        derivations = Derivations(self._settings)
        merged = StalenessPolicy(derivations.ids(), unreported).merge(
            previous.figures if previous else (), fresh
        )
        base = {f.id: f for f in merged}
        if previous is not None:
            for fid in derivations.ids():
                old = previous.by_id().get(fid)
                if old is not None:
                    base.setdefault(fid, old)
        derived = derivations.derive(base)
        figures = tuple(sorted([*merged, *derived], key=lambda f: f.id))
        return SpecsRecord(
            generated_at=self._clock.now(),
            hosts={**(previous.hosts if previous else {}), **hosts},
            figures=figures,
            sources=previous.sources if previous else {},
            not_verified=previous.not_verified if previous else (),
        )

    def rederive(self, record: SpecsRecord) -> SpecsRecord:
        """The same record with its derived figures recomputed from its other figures."""
        derivations = Derivations(self._settings)
        derived = derivations.derive(record.by_id())
        kept = [f for f in record.figures if f.id not in derivations.ids()]
        return replace(record, figures=tuple(sorted([*kept, *derived], key=lambda f: f.id)))


# ------------------------------------------------------------------------ the command line


class MinimumSpecsCli:
    """`measure`, `derive`, `render` and `check`, over the declared configuration."""

    def __init__(self, repo: Path = Path("."), clock: ClockInterface | None = None) -> None:
        self._repo = repo
        self._clock = clock or SystemClock()

    def parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
        parser.add_argument("--repo", type=Path, default=None)
        parser.add_argument("--config", default=DEFAULT_CONFIG, help="relative to --repo")
        sub = parser.add_subparsers(dest="command", required=True)
        measure = sub.add_parser("measure", help="probe this host and write a new record")
        measure.add_argument("--out", type=Path, default=None, help="default: the declared record")
        measure.add_argument(
            "--only", action="append", default=[], help="run only this probe (repeatable)"
        )
        sub.add_parser("derive", help="recompute the derived figures in the record")
        sub.add_parser("render", help="rewrite the GENERATED blocks from the record")
        sub.add_parser(
            "check", help="exit 1 if the record's derivations or the blocks are out of step"
        )
        return parser

    def run(self, argv: Sequence[str]) -> int:
        args = self.parser().parse_args(list(argv))
        repo = args.repo or self._repo
        settings = SpecsSettings.load(repo / args.config)
        record_path = repo / settings.record
        if args.command == "measure":
            previous = SpecsRecord.load(record_path) if record_path.exists() else None
            record = MeasurementSession(repo, settings, clock=self._clock, only=args.only).run(
                previous
            )
            out = args.out if args.out is not None else record_path
            record.save(out if out.is_absolute() else repo / out)
            counts = {s: sum(1 for f in record.figures if f.status == s) for s in STATUSES}
            print(f"{SCRIPT}: wrote {out}: " + ", ".join(f"{n} {s}" for s, n in counts.items()))
            return 0
        record = SpecsRecord.load(record_path)
        builder = RecordBuilder(settings, self._clock)
        renderers: list[tuple[Path, RequirementsRendererInterface]] = [
            (repo / settings.docs_page, DocsRenderer(settings)),
            (repo / settings.paper, PaperRenderer(settings)),
        ]
        if args.command == "derive":
            builder.rederive(record).save(record_path)
            print(f"{SCRIPT}: re-derived {record_path}")
            return 0
        if args.command == "render":
            for path, renderer in renderers:
                path.write_text(
                    renderer.apply(path.read_text(encoding="utf-8"), record), encoding="utf-8"
                )
                print(f"{SCRIPT}: rendered {path}")
            return 0
        problems: list[str] = []
        rederived = builder.rederive(record)
        if rederived.to_json() != record.to_json():
            before, after = record.by_id(), rederived.by_id()
            changed = sorted(k for k in after if before.get(k) != after[k])
            problems.append(
                f"{settings.record}: derived figures out of step with their inputs: {', '.join(changed)}"
            )
        for path, renderer in renderers:
            drift = renderer.drift(path.read_text(encoding="utf-8"), record)
            if drift:
                problems.append(
                    f"{path.relative_to(repo)}: generated blocks out of date: {', '.join(drift)}"
                )
        for problem in problems:
            print(f"{SCRIPT}: {problem}", file=sys.stderr)
        if problems:
            print(f"{SCRIPT}: run `python {SCRIPT} derive` and/or `render`", file=sys.stderr)
            return 1
        print(f"{SCRIPT}: the record's derivations and every generated block are in step")
        return 0


if __name__ == "__main__":
    sys.exit(MinimumSpecsCli(Path.cwd()).run(sys.argv[1:]))
