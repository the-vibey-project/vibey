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
        CellRunnerInterface,
        ClockInterface,
        CommandRunnerInterface,
        DerivationsInterface,
        DerivationSourceInterface,
        IdleGateInterface,
        PackageManagerInterface,
        ProbeInterface,
        RequirementsRendererInterface,
        StalenessPolicyInterface,
    )
    from scripts.requirements_math import AmdahlFit, LinearFit, RequirementsMath
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.minimum_specs_interface import (  # type: ignore[import-not-found,no-redef]
        CellRunnerInterface,
        ClockInterface,
        CommandRunnerInterface,
        DerivationsInterface,
        DerivationSourceInterface,
        IdleGateInterface,
        PackageManagerInterface,
        ProbeInterface,
        RequirementsRendererInterface,
        StalenessPolicyInterface,
    )
    from requirements_math import (  # type: ignore[import-not-found,no-redef]
        AmdahlFit,
        LinearFit,
        RequirementsMath,
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
    host: Mapping[str, Any]
    install: Mapping[str, Any]
    postgres: Mapping[str, Any]
    ollama: Mapping[str, Any]
    bench: Mapping[str, Any]
    idle: Mapping[str, Any]
    processes: Mapping[str, Any]
    declared: Mapping[str, Any]
    assumptions: Mapping[str, Any]
    growth: Mapping[str, Any]
    linux: Mapping[str, Any]

    @classmethod
    def load(cls, path: Path) -> SpecsSettings:
        table = tomllib.loads(path.read_text(encoding="utf-8"))["minimum_specs"]
        return cls(
            record=table["record"],
            docs_page=table["docs_page"],
            paper=table["paper"],
            host=table["host"],
            install=table["install"],
            postgres=table["postgres"],
            ollama=table["ollama"],
            bench=table["bench"],
            idle=table["idle"],
            processes=table["processes"],
            declared=table["declared"],
            assumptions=table["assumptions"],
            growth=table["growth"],
            linux=table["linux"],
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


class Arch:
    """One spelling per architecture: the kernel's (`uname -m` on Linux)."""

    _ALIASES: Mapping[str, str] = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
    }

    @classmethod
    def normalize(cls, machine: str) -> str:
        return cls._ALIASES.get(machine.lower(), machine.lower())


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
            info["chip"] = self._linux_chip()
            mem = self._linux_field("/proc/meminfo", r"MemTotal:\s*(\d+)")
            info["ram_bytes"] = int(mem) * 1024 if mem else None
            # In a container these are the runner's: its idle memory and its kernel.
            available = self._linux_field("/proc/meminfo", r"MemAvailable:\s*(\d+)")
            info["mem_available_bytes"] = int(available) * 1024 if available else None
            info["kernel"] = platform.release()
            info["cores_total"] = os.cpu_count()
            pretty = self._linux_field("/etc/os-release", r'PRETTY_NAME="?([^"\n]+)')
            info["os"] = pretty
            info["model"] = None
        return info

    def _linux_chip(self) -> str | None:
        """x86 names its CPU in /proc/cpuinfo; arm64 lists only implementer and part numbers
        there, so `lscpu`'s model name (a core name such as Neoverse-N2) names it."""
        chip = self._linux_field("/proc/cpuinfo", r"model name\s*:\s*(.+)")
        if chip:
            return chip
        listed = self._runner.run(["lscpu"], timeout=10)
        found = re.search(r"^Model name:\s*(.+)$", str(listed.stdout), re.MULTILINE)
        name = found.group(1).strip() if listed.ok and found else ""
        return name if name and name != "-" else None

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
    """Builds the engine and launcher wheels from this checkout, once per session.

    A Linux cell's container is handed wheels built once on its host (`$VIBEY_SPECS_WHEELS`),
    so every cell installs the same artifacts and the checkout is mounted read-only.
    """

    WHEELS_ENV = "VIBEY_SPECS_WHEELS"

    def __init__(
        self,
        repo: Path,
        settings: SpecsSettings,
        runner: CommandRunnerInterface,
        ws: Workspace,
        environ: Mapping[str, str] = os.environ,
    ):
        self._repo = repo
        self._settings = settings
        self._runner = runner
        self._ws = ws
        self._environ = environ

    def _key(self, wheel: Path) -> str:
        return "vibey-engine" if wheel.name.startswith("vibey_engine-") else "krypton-app"

    def build(self) -> tuple[dict[str, Path], str]:
        if self._ws.wheel_paths:
            return self._ws.wheel_paths, ""
        prebuilt = self._environ.get(self.WHEELS_ENV, "")
        if prebuilt:
            for wheel in sorted(Path(prebuilt).glob("*.whl")):
                self._ws.wheel_paths[self._key(wheel)] = wheel
            missing = {"vibey-engine", "krypton-app"} - set(self._ws.wheel_paths)
            if missing:
                return {}, f"no prebuilt wheel for {', '.join(sorted(missing))} in {prebuilt}"
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
            self._ws.wheel_paths[self._key(wheel)] = wheel
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
    """Cold install time, venv and cache size, package count and download bytes per target.

    `prefix` namespaces the figures (a Linux cell measures under `linux.<distro>.<arch>.install`),
    `only` narrows the targets, and an `emulated` run refuses its timings: under QEMU a cold
    install measures the emulator, not the architecture. On Linux the newest glibc any
    installed wheel's manylinux tag requires is read from the engine's venv as well.
    """

    name = "install"

    def __init__(
        self,
        settings: SpecsSettings,
        runner: CommandRunnerInterface,
        builder: PackageBuilder,
        ws: Workspace,
        sizes: DirectorySize,
        figures: FigureFactory,
        prefix: str = "install",
        only: Sequence[str] = (),
        emulated: str = "",
    ) -> None:
        self._settings = settings
        self._runner = runner
        self._builder = builder
        self._ws = ws
        self._sizes = sizes
        self._figures = figures
        self._prefix = prefix
        self._only = tuple(only)
        self._emulated = emulated

    def targets(self, wheels: Mapping[str, Path]) -> dict[str, list[str]]:
        engine = str(wheels.get("vibey-engine", "vibey-engine"))
        out: dict[str, list[str]] = {"vibey-engine": [engine]}
        for extra in self._settings.install["engine_extras"]:
            out[f"vibey-engine[{extra}]"] = [f"{engine}[{extra}]"]
        # krypton-app resolves vibey-engine[hub] from its own metadata; the local engine
        # wheel is named beside it so the resolver takes this checkout's engine, not PyPI's.
        out["krypton-app"] = [str(wheels.get("krypton-app", "krypton-app")), f"{engine}[hub]"]
        if self._only:
            out = {k: v for k, v in out.items() if k in self._only}
        return out

    def ids(self, target: str) -> dict[str, tuple[str, str]]:
        p = f"{self._prefix}.{target}"
        return {
            "cold_s": (f"{p}.cold_s", "s"),
            "venv": (f"{p}.venv_bytes", "bytes"),
            "cache": (f"{p}.uv_cache_bytes", "bytes"),
            "packages": (f"{p}.packages", "count"),
            "download": (f"{p}.download_bytes", "bytes"),
        }

    _MANYLINUX = re.compile(r"manylinux_(\d+)_(\d+)_|manylinux(2014|2010|1)_")
    _LEGACY = {"2014": (2, 17), "2010": (2, 12), "1": (2, 5)}

    @classmethod
    def glibc_floor(cls, venv: Path) -> tuple[str, int] | None:
        """The newest glibc any installed wheel requires, from its WHEEL `Tag:` lines, and
        how many wheels carried a manylinux tag. None when none did (all pure Python)."""
        newest: tuple[int, int] | None = None
        tagged = 0
        for wheel in venv.glob("lib/python*/site-packages/*.dist-info/WHEEL"):
            with contextlib.suppress(OSError):
                found = [
                    (int(m[0]), int(m[1])) if m[0] else cls._LEGACY[m[2]]
                    for m in cls._MANYLINUX.findall(wheel.read_text(encoding="utf-8"))
                ]
                if found:
                    tagged += 1
                    # A wheel tagged for several policies runs on the oldest of them.
                    floor = min(found)
                    newest = floor if newest is None else max(newest, floor)
        return (f"{newest[0]}.{newest[1]}", tagged) if newest else None

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
                out += self._glibc_skipped(target, why)
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
                out += self._glibc_skipped(target, reason)
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
            if self._emulated:
                out.append(
                    self._figures.skipped(
                        ids["cold_s"][0],
                        f"{target} cold install",
                        "s",
                        method,
                        f"emulated ({self._emulated}): a timing here measures the emulator, not the architecture",
                    )
                )
            else:
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
            if target == "vibey-engine" and platform.system() == "Linux":
                out.append(self._glibc(venv, conditions))
        return out

    def _glibc_skipped(self, target: str, reason: str) -> list[Figure]:
        if target != "vibey-engine" or platform.system() != "Linux":
            return []
        return [
            self._figures.skipped(
                f"{self._prefix}.glibc_floor",
                "Newest glibc the installed wheels require",
                "version",
                "the engine venv's WHEEL tags",
                f"no engine venv to read: {reason}",
            )
        ]

    def _glibc(self, venv: Path, conditions: Mapping[str, Any]) -> Figure:
        fid, label = f"{self._prefix}.glibc_floor", "Newest glibc the installed wheels require"
        method = "max over the venv's *.dist-info/WHEEL of each wheel's oldest manylinux_X_Y tag"
        found = self.glibc_floor(venv)
        if found is None:
            return self._figures.skipped(
                fid, label, "version", method, "no installed wheel carries a manylinux tag"
            )
        floor, tagged = found
        return self._figures.measured(
            fid, label, floor, "version", method, {**conditions, "manylinux_wheels": tagged}
        )

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
        return out + self.scaling_expected()

    def scaling_expected(self) -> list[tuple[str, str, str]]:
        """The CPU scaling sweep's figures on this host's architecture."""
        m, arch = self._settings.sovereign_model, Arch.normalize(platform.machine())
        return [
            (
                f"bench.{m}.cpu.{arch}.threads{n}.{key}",
                f"{m} CPU only ({arch}) on {n} thread(s): {label}",
                "tokens/s",
            )
            for n in self._settings.bench["cpu_scaling"]["threads"]
            for key, label in (("prompt_tok_s", "prompt"), ("gen_tok_s", "generation"))
        ]

    def _scaling(self, conditions: dict[str, Any]) -> list[Figure]:
        """Generation and prompt rates on the CPU alone at each declared thread count."""
        m, cs = self._settings.sovereign_model, self._settings.bench["cpu_scaling"]
        arch, cores = Arch.normalize(platform.machine()), os.cpu_count() or 0
        method = "POST /api/chat num_gpu=0 num_thread=n temperature=0 seed fixed; Ollama counters; median of clean runs"
        out: list[Figure] = []
        ctx = int(cs["context"])
        target = min(int(cs["prompt_tokens"]), ctx - int(cs["num_predict"]) - 256)
        self._load(ctx, {"num_gpu": 0})
        for n in cs["threads"]:
            ids = [
                (f"bench.{m}.cpu.{arch}.threads{n}.{name}", key)
                for key, name in (("prompt", "prompt_tok_s"), ("gen", "gen_tok_s"))
            ]
            label = f"{m} CPU only ({arch}) on {n} thread(s)"
            if int(n) > cores:
                out += [
                    self._figures.skipped(
                        fid, f"{label}: {key}", "tokens/s", method, f"the host has {cores} cores"
                    )
                    for fid, key in ids
                ]
                continue
            options = {"num_gpu": 0, "num_thread": int(n)}
            runs, discarded = self._rates(
                ctx, target, options, f"threads{n}", int(cs["runs"]), int(cs["num_predict"])
            )
            for fid, key in ids:
                if not runs:
                    out.append(
                        self._figures.skipped(
                            fid,
                            f"{label}: {key}",
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
                    "range": [round(min(values), 2), round(max(values), 2)],
                    "options": options,
                    "host_cores": cores,
                }
                out.append(
                    self._figures.measured(
                        fid,
                        f"{label}: {key}",
                        round(self._median(values), 2),
                        "tokens/s",
                        method,
                        cond,
                    )
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
        self,
        ctx: int,
        target: int,
        options: Mapping[str, Any],
        tag: str,
        runs: int | None = None,
        num_predict: int | None = None,
    ) -> tuple[list[dict[str, float]], int]:
        b = self._settings.bench
        clean: list[dict[str, float]] = []
        discarded = 0
        for run in range(int(b["runs"]) if runs is None else runs):
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
                        "num_predict": int(
                            b["num_predict"] if num_predict is None else num_predict
                        ),
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

    def _sweep(self, out: list[Figure], ctx: int, conditions: dict[str, Any]) -> None:
        """Load at `ctx`, read llama-server's memory accounting, then time the default
        offload there. Appends to `out` as it goes, so a failure keeps what was read."""
        m, b = self._settings.sovereign_model, self._settings.bench
        accounting = self._load(ctx, {})
        method = "llama-server common_memory_breakdown_print and buffer lines in the Ollama log"
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
                        fid, f"{m} at {ctx}: {label}", accounting[key], "MiB", method, conditions
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
        target = min(int(b["prompt_tokens"]), ctx - int(b["num_predict"]) - 256)
        out += self._rate_figures("gpu", ctx, target, {}, conditions)

    def _stages(
        self, conditions: dict[str, Any]
    ) -> list[tuple[str, tuple[str, ...], Callable[[list[Figure]], None]]]:
        """Each stage of the bench, the figure ids it owns, and how to run it into a list.

        A stage that fails (a context that does not fit the host's memory, say: 131072 on a
        16 GB runner) skips only its own figures with the reason; the next stage still runs.
        """
        m, b = self._settings.sovereign_model, self._settings.bench
        stages: list[tuple[str, tuple[str, ...], Callable[[list[Figure]], None]]] = []

        def sweep(ctx: int) -> Callable[[list[Figure]], None]:
            def stage(out: list[Figure]) -> None:
                self._sweep(out, ctx, conditions)

            return stage

        for ctx in b["contexts"]:
            stages.append(
                (
                    f"at num_ctx {ctx}",
                    (f"bench.{m}.ctx{ctx}.", f"bench.{m}.gpu.ctx{ctx}."),
                    sweep(int(ctx)),
                )
            )

        def rates(
            kind: str, ctx: int, fill: bool, options: Mapping[str, Any]
        ) -> Callable[[list[Figure]], None]:
            def stage(out: list[Figure]) -> None:
                self._load(ctx, options)
                if fill:
                    target = int(float(b["fill"]) * ctx) - int(b["num_predict"]) - 256
                else:
                    target = min(int(b["prompt_tokens"]), ctx - int(b["num_predict"]) - 256)
                out += self._rate_figures(kind, ctx, target, options, conditions)

            return stage

        for ctx in b["depth_contexts"]:
            stages.append(
                (
                    f"at depth, num_ctx {ctx}",
                    (f"bench.{m}.depth.ctx{ctx}.",),
                    rates("depth", int(ctx), True, {}),
                )
            )
        for ctx in b["cpu_contexts"]:
            stages.append(
                (
                    f"on the CPU alone at num_ctx {ctx}",
                    (f"bench.{m}.cpu.ctx{ctx}.",),
                    rates("cpu", int(ctx), False, {"num_gpu": 0}),
                )
            )
        stages.append(
            (
                "in the CPU scaling sweep",
                tuple(fid for fid, _, _ in self.scaling_expected()),
                lambda out: out.extend(self._scaling(conditions)),
            )
        )
        return stages

    def run(self) -> list[Figure]:
        idle, reason, conditions = self._gate.wait()
        if not idle:
            return self._skip_all(reason)
        out: list[Figure] = []
        try:
            for what, owned, stage in self._stages(conditions):
                try:
                    stage(out)
                except (OSError, ValueError) as exc:
                    done = {f.id for f in out}
                    out += [
                        f
                        for f in self._skip_all(f"Ollama failed {what}: {exc}")
                        if f.id.startswith(owned) and f.id not in done
                    ]
        finally:
            with contextlib.suppress(OSError, ValueError):
                self._client.unload(self._settings.sovereign_model)
        if not any(f.id == "gpu.working_set_limit_mib" for f in out):
            out += [
                f
                for f in self._skip_all("no working-set line in the log")
                if f.id == "gpu.working_set_limit_mib"
            ]
        return out


class ProcessFootprintProbe(ProbeInterface):
    """Peak RSS and wall time of the everyday CLI commands, and idle RSS of the hub and the
    krypton launcher, on the scratch database."""

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
        worker = "process.cli.worker_once.max_rss_mib"
        out.append(self._after_one_job(any(f.id == worker and f.has_value for f in out)))
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

    def _after_one_job(self, ran: bool) -> Figure:
        """The scratch database after `vibey new` and one `worker --once`: the ledger's
        growth for one project and one job, against the empty migrated database."""
        fid, label = "postgres.after_one_job_bytes", "Database after one project and one job"
        method = "pg_database_size after the commands above (new, worker --once)"
        database = self._postgres.database
        if not ran or database is None:
            return self._figures.skipped(
                fid, label, "bytes", method, "`worker --once` did not run on a scratch database"
            )
        size = database.sql(f"SELECT pg_database_size('{database.name}')")
        if size.ok and size.stdout.strip().isdigit():
            return self._figures.measured(
                fid,
                label,
                int(size.stdout.strip()),
                "bytes",
                method,
                note="page-granular: one job's rows can fill new 8 KiB pages, so an upper bound",
            )
        return self._figures.skipped(fid, label, "bytes", method, size.tail())

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


# ------------------------------------------------------------------------ Linux


class Versions:
    """Distribution version strings, compared by their leading numeric part.

    `1:4.22.5-1` (an epoch), `16+257build1.1`, `6.8.0-146.146` and a floor like `>= 2.74`
    all reduce to a tuple of integers; anything after the dotted number is packaging.
    """

    _NUMBER = re.compile(r"\d+(?:\.\d+)*")

    @classmethod
    def key(cls, text: str) -> tuple[int, ...]:
        body = str(text).split(":", 1)[1] if re.match(r"^\d+:", str(text)) else str(text)
        found = cls._NUMBER.search(body)
        if not found:
            raise ValueError(f"no version number in {text!r}")
        return tuple(int(part) for part in found.group(0).split("."))

    @classmethod
    def at_least(cls, have: str, floor: str) -> bool:
        a, b = cls.key(have), cls.key(floor)
        width = max(len(a), len(b))
        return a + (0,) * (width - len(a)) >= b + (0,) * (width - len(b))

    @classmethod
    def major(cls, text: str) -> int:
        return cls.key(text)[0]


class PackageManager(PackageManagerInterface):
    """apt, pacman or dnf, as `[minimum_specs.linux.package_managers.*]` declares them."""

    _PACMAN_UNITS: Mapping[str, int] = {"B": 1, "KiB": 1024, "MiB": MIB, "GiB": GIB}

    def __init__(
        self, config: Mapping[str, Any], runner: CommandRunnerInterface, timeout: float
    ) -> None:
        self._config = config
        self._runner = runner
        self._timeout = timeout

    def _env(self) -> dict[str, str]:
        return {str(k): str(v) for k, v in dict(self._config.get("env", {})).items()}

    def installed(self) -> set[str]:
        result = self._runner.run(list(self._config["installed"]), timeout=120)
        if not result.ok:
            raise OSError(f"listing installed packages failed: {result.tail()}")
        return {line.strip() for line in str(result.stdout).splitlines() if line.strip()}

    def sizes(self) -> dict[str, int]:
        result = self._runner.run(list(self._config["sizes"]), timeout=300)
        if not result.ok:
            raise OSError(f"reading installed sizes failed: {result.tail()}")
        return self.parse_sizes(str(result.stdout), str(self._config["size_format"]))

    @classmethod
    def parse_sizes(cls, text: str, size_format: str) -> dict[str, int]:
        out: dict[str, int] = {}
        if size_format in ("name-tab-kib", "name-tab-bytes"):
            scale = 1024 if size_format == "name-tab-kib" else 1
            for line in text.splitlines():
                name, _, size = line.partition("\t")
                if name.strip() and size.strip().isdigit():
                    out[name.strip()] = out.get(name.strip(), 0) + int(size) * scale
            return out
        if size_format == "pacman-qi":
            current: str | None = None
            for line in text.splitlines():
                key, _, value = line.partition(":")
                if key.strip() == "Name":
                    current = value.strip()
                elif key.strip() == "Installed Size" and current:
                    number, _, unit = value.strip().partition(" ")
                    out[current] = round(float(number) * cls._PACMAN_UNITS[unit.strip()])
            return out
        raise ValueError(f"unknown size_format {size_format!r}")

    def install(self, packages: Sequence[str]) -> CommandResult:
        command = str(self._config["install"]).replace(
            "{packages}", " ".join(re.sub(r"[^A-Za-z0-9.+_:-]", "", p) for p in packages)
        )
        result: CommandResult = self._runner.run(
            ["/bin/sh", "-c", command], timeout=self._timeout, env=self._env()
        )
        return result

    def version(self, package: str) -> str | None:
        argv = [str(a).replace("{package}", package) for a in self._config["version"]]
        result = self._runner.run(argv, timeout=120, env=self._env())
        found = [
            v
            for v in re.findall(str(self._config["version_pattern"]), str(result.stdout))
            if v != "(none)"
        ]
        candidates = []
        for value in found:
            with contextlib.suppress(ValueError):
                candidates.append((Versions.key(value), value))
        return max(candidates)[1] if candidates else None


@dataclass(frozen=True)
class LinuxCell:
    """One (distribution x architecture) cell of the matrix, as the configuration declares it."""

    distro: str
    arch: str
    name: str
    image: str
    reason: str
    goarch: str
    runner: str

    @property
    def prefix(self) -> str:
        return f"linux.{self.distro}.{self.arch}"

    @property
    def platform(self) -> str:
        return f"linux/{self.goarch}"


class LinuxMatrix:
    """The declared matrix: every distribution on every architecture, in declared order."""

    CELL_ENV = "VIBEY_SPECS_CELL"
    EMULATED_ENV = "VIBEY_SPECS_EMULATED"
    HOST_ENV = "VIBEY_SPECS_HOST_LABEL"
    BEFORE_ENV = "VIBEY_SPECS_PACKAGES_BEFORE"

    def __init__(self, settings: SpecsSettings) -> None:
        self._settings = settings
        self._linux = settings.linux

    def arches(self) -> list[str]:
        return list(self._linux["arches"])

    def distros(self) -> list[str]:
        return list(self._linux["distros"])

    def distro(self, key: str) -> Mapping[str, Any]:
        return self._linux["distros"][key]  # type: ignore[no-any-return]

    def package_manager(self, distro: str) -> Mapping[str, Any]:
        return self._linux["package_managers"][self.distro(distro)["package_manager"]]  # type: ignore[no-any-return]

    def cell(self, distro: str, arch: str) -> LinuxCell:
        if distro not in self._linux["distros"] or arch not in self._linux["arches"]:
            raise KeyError(f"no cell {distro}/{arch} in the declared matrix")
        d, a = self.distro(distro), self._linux["arches"][arch]
        image = str(d["images"].get(arch, ""))
        reason = str(dict(d.get("unavailable", {})).get(arch, ""))
        if not image and not reason:
            reason = f"no image declared for {arch}"
        return LinuxCell(
            distro, arch, str(d["name"]), image, reason, str(a["goarch"]), str(a["runner"])
        )

    def cells(self) -> list[LinuxCell]:
        return [self.cell(d, a) for d in self.distros() for a in self.arches()]

    def bundle_prefix(self, arch: str) -> str:
        return f"linux.ollama.{arch}"

    def prefixes(self, cell: LinuxCell) -> tuple[str, ...]:
        """The figure prefixes a cell's run is responsible for."""
        own: tuple[str, ...] = (f"{cell.prefix}.",)
        if cell.distro == self._linux["ollama_bundle_distro"]:
            own += (f"{self.bundle_prefix(cell.arch)}.",)
        return own

    def expected(self, cell: LinuxCell) -> list[tuple[str, str, str]]:
        """Every figure a cell's run reports, so a cell that cannot run can name each one."""
        p, d = cell.prefix, self.distro(cell.distro)
        out = [
            (f"{p}.os_release", f"{cell.name} ({cell.arch}): OS release", "text"),
            (f"{p}.glibc", f"{cell.name} ({cell.arch}): glibc", "version"),
        ]
        out += [
            (f"{p}.packaged.{role}", f"{cell.name} ({cell.arch}): packaged {role}", "version")
            for role in d["versions"]
        ]
        for name in ("base", *d["sets"]):
            out += [
                (f"{p}.pkg.{name}.bytes", f"{cell.name} ({cell.arch}): {name} closure", "bytes"),
                (f"{p}.pkg.{name}.count", f"{cell.name} ({cell.arch}): {name} packages", "count"),
            ]
        for target in self._linux["install_targets"]:
            for key, unit in (
                ("cold_s", "s"),
                ("venv_bytes", "bytes"),
                ("uv_cache_bytes", "bytes"),
                ("packages", "count"),
                ("download_bytes", "bytes"),
            ):
                out.append((f"{p}.install.{target}.{key}", f"{target} {key}", unit))
        out.append(
            (f"{p}.install.glibc_floor", "Newest glibc the installed wheels require", "version")
        )
        if cell.distro == self._linux["ollama_bundle_distro"]:
            b = self.bundle_prefix(cell.arch)
            out += [
                (f"{b}.download_bytes", f"Ollama Linux bundle ({cell.arch}) download", "bytes"),
                (f"{b}.unpacked_bytes", f"Ollama Linux bundle ({cell.arch}) unpacked", "bytes"),
            ]
        return out


class LinuxCellProbe(ProbeInterface):
    """Inside one distribution's container: what that distribution offers and what vibey
    costs on it. The OS release and glibc; the repository version of each floor's package
    (kernel, Python, PostgreSQL, the desktop libraries), read from metadata, not installed;
    the closure each package set adds (the bootstrap's base, PostgreSQL, the desktop
    libraries), as the package manager's own installed sizes; and a cold install of the
    declared targets with uv. The container's kernel, cores and memory are its runner's, so
    they describe the host, not the distribution, and are recorded with the host instead.
    """

    name = "linux"

    def __init__(
        self,
        settings: SpecsSettings,
        cell: LinuxCell,
        manager: PackageManagerInterface,
        install: ProbeInterface,
        figures: FigureFactory,
        before: set[str] | None,
        emulated: str = "",
        os_release: Path = Path("/etc/os-release"),
    ) -> None:
        self._settings = settings
        self._cell = cell
        self._matrix = LinuxMatrix(settings)
        self._pm = manager
        self._install = install
        self._figures = figures
        self._before = before
        self._emulated = emulated
        self._os_release = os_release

    def _conditions(self) -> dict[str, Any]:
        return {"image": self._cell.image, "emulated": bool(self._emulated), "container": True}

    def _closure(self, name: str, before: set[str], method: str) -> list[Figure]:
        p, label = f"{self._cell.prefix}.pkg.{name}", f"{self._cell.name} ({self._cell.arch})"
        after = self._pm.installed()
        added = sorted(after - before)
        sizes = self._pm.sizes()
        unsized = [n for n in added if n not in sizes]
        cond = {**self._conditions(), "packages": added[:200]}
        if unsized:
            reason = f"no installed size for {', '.join(unsized[:5])}"
            return [
                self._figures.skipped(
                    f"{p}.bytes", f"{label}: {name} closure", "bytes", method, reason
                ),
                self._figures.measured(
                    f"{p}.count", f"{label}: {name} packages", len(added), "count", method, cond
                ),
            ]
        return [
            self._figures.measured(
                f"{p}.bytes",
                f"{label}: {name} closure",
                sum(sizes[n] for n in added),
                "bytes",
                method,
                cond,
            ),
            self._figures.measured(
                f"{p}.count", f"{label}: {name} packages", len(added), "count", method, cond
            ),
        ]

    def run(self) -> list[Figure]:
        cell, d = self._cell, self._matrix.distro(self._cell.distro)
        p, label = cell.prefix, f"{cell.name} ({cell.arch})"
        pm_name = str(d["package_manager"])
        out: list[Figure] = []
        release = HostDescriber._linux_field(str(self._os_release), r'PRETTY_NAME="?([^"\n]+)')
        if release:
            out.append(
                self._figures.measured(
                    f"{p}.os_release",
                    f"{label}: OS release",
                    release,
                    "text",
                    f"PRETTY_NAME in {self._os_release}",
                    self._conditions(),
                )
            )
        else:
            out.append(
                self._figures.skipped(
                    f"{p}.os_release",
                    f"{label}: OS release",
                    "text",
                    "os-release",
                    "no PRETTY_NAME",
                )
            )
        glibc = ""
        with contextlib.suppress(ValueError, OSError, AttributeError):
            glibc = (os.confstr("CS_GNU_LIBC_VERSION") or "").replace("glibc", "").strip()
        if glibc:
            out.append(
                self._figures.measured(
                    f"{p}.glibc",
                    f"{label}: glibc",
                    glibc,
                    "version",
                    "os.confstr('CS_GNU_LIBC_VERSION')",
                    self._conditions(),
                )
            )
        else:
            out.append(
                self._figures.skipped(
                    f"{p}.glibc", f"{label}: glibc", "version", "os.confstr", "not a glibc system"
                )
            )
        for role, package in d["versions"].items():
            method = f"{pm_name}: the repositories' version of {package} (metadata, not installed)"
            version = self._pm.version(str(package))
            fid = f"{p}.packaged.{role}"
            if version is None:
                out.append(
                    self._figures.skipped(
                        fid,
                        f"{label}: packaged {role}",
                        "version",
                        method,
                        f"{package} not in the repositories",
                    )
                )
            else:
                out.append(
                    self._figures.measured(
                        fid,
                        f"{label}: packaged {role}",
                        version,
                        "version",
                        method,
                        {**self._conditions(), "package": package},
                    )
                )
        base_method = f"{pm_name}: packages the bootstrap added ({', '.join(d['base'])} and their dependencies), installed sizes summed"
        if self._before is None:
            out += [
                self._figures.skipped(
                    f"{p}.pkg.base.{k}",
                    f"{label}: base {k}",
                    u,
                    base_method,
                    "no package list from before the bootstrap",
                )
                for k, u in (("bytes", "bytes"), ("count", "count"))
            ]
        else:
            out += self._closure("base", self._before, base_method)
        for name, packages in d["sets"].items():
            method = f"{pm_name}: install {' '.join(packages)} (no recommends / weak deps); packages it added, installed sizes summed"
            before = self._pm.installed()
            result = self._pm.install([str(x) for x in packages])
            if not result.ok:
                out += [
                    self._figures.skipped(
                        f"{p}.pkg.{name}.{k}",
                        f"{label}: {name} {k}",
                        u,
                        method,
                        f"install failed: {result.tail()}",
                    )
                    for k, u in (("bytes", "bytes"), ("count", "count"))
                ]
                continue
            out += self._closure(name, before, method)
        out += self._install.run()
        return out


class CellRunner(CellRunnerInterface):
    """Runs one cell from its host: builds the wheels once, runs the distribution's image
    (`docker run --platform`), bootstraps it from the declared package manager, and runs this
    script's `measure` inside it with the checkout mounted read-only. A run on the other
    architecture is emulated and says so. A cell with no image, or whose container fails, is
    returned with every figure skipped and the reason -- never left out. The Ollama bundle
    for the architecture is measured here, on the host, by the declared distribution's cell.
    """

    def __init__(
        self,
        repo: Path,
        settings: SpecsSettings,
        runner: CommandRunnerInterface,
        clock: ClockInterface,
        runner_label: str,
        host_arch: str | None = None,
        head: Callable[[str], int] | None = None,
    ) -> None:
        self._repo = repo
        self._settings = settings
        self._runner = runner
        self._clock = clock
        self._label = runner_label
        self._host_arch = Arch.normalize(host_arch or platform.machine())
        self._matrix = LinuxMatrix(settings)
        self._head = head or self.content_length

    @staticmethod
    def content_length(url: str) -> int:
        request = urllib.request.Request(url, method="HEAD")  # noqa: S310 - the declared URL
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            return int(response.headers["Content-Length"])

    def host_label(self, cell: LinuxCell) -> str:
        mode = "not run" if not cell.image else ("emulated" if self.emulated(cell) else "native")
        return f"{cell.image or cell.name} ({cell.platform}, {mode}) on {self._label}"

    def emulated(self, cell: LinuxCell) -> str:
        return "" if cell.arch == self._host_arch else f"{cell.platform} on {self._host_arch}"

    def bootstrap(self, cell: LinuxCell) -> str:
        """The container's shell: snapshot the packages, refresh, install the base, fetch uv,
        then run this script's measurement on the distribution's own python3."""
        pm = self._matrix.package_manager(cell.distro)
        base = " ".join(self._matrix.distro(cell.distro)["base"])
        env = " ".join(f"{k}={v}" for k, v in dict(pm.get("env", {})).items())
        listing = " ".join(f"'{a}'" for a in pm["installed"])
        steps = [
            "set -eu",
            f"export {env}" if env else ":",
            f"{listing} > /out/packages-before.txt",
            str(pm["refresh"]),
            str(pm["install"]).replace("{packages}", base),
            str(self._settings.linux["uv_install"]),
            "python3 /src/scripts/minimum_specs.py --repo /src measure --out /out/partial.json",
        ]
        return "\n".join(steps)

    def _skipped(self, cell: LinuxCell, reason: str, factory: FigureFactory) -> list[Figure]:
        return [
            factory.skipped(
                fid, label, unit, f"minimum_specs.py cell {cell.distro} {cell.arch}", reason
            )
            for fid, label, unit in self._matrix.expected(cell)
        ]

    def _bundle(self, cell: LinuxCell, factory: FigureFactory) -> list[Figure]:
        if cell.distro != self._settings.linux["ollama_bundle_distro"]:
            return []
        b = self._matrix.bundle_prefix(cell.arch)
        url = str(self._settings.linux["ollama_bundle_url"]).replace("{goarch}", cell.goarch)
        out: list[Figure] = []
        try:
            out.append(
                factory.measured(
                    f"{b}.download_bytes",
                    f"Ollama Linux bundle ({cell.arch}) download",
                    self._head(url),
                    "bytes",
                    f"HTTP HEAD {url}: Content-Length",
                )
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            out.append(
                factory.skipped(
                    f"{b}.download_bytes",
                    f"Ollama Linux bundle ({cell.arch}) download",
                    "bytes",
                    f"HTTP HEAD {url}",
                    f"unreachable: {exc}",
                )
            )
        command = str(self._settings.linux["ollama_bundle_unpacked"]).replace("{url}", url)
        result = self._runner.run(["/bin/sh", "-c", command], timeout=3600)
        size = str(result.stdout).strip()
        if result.ok and size.isdigit():
            out.append(
                factory.measured(
                    f"{b}.unpacked_bytes",
                    f"Ollama Linux bundle ({cell.arch}) unpacked",
                    int(size),
                    "bytes",
                    command,
                    note="the tar stream's bytes: file contents plus tar headers and padding",
                )
            )
        else:
            out.append(
                factory.skipped(
                    f"{b}.unpacked_bytes",
                    f"Ollama Linux bundle ({cell.arch}) unpacked",
                    "bytes",
                    command,
                    f"exit {result.returncode}: {result.tail()}",
                )
            )
        return out

    def run(self, distro: str, arch: str) -> SpecsRecord:
        cell = self._matrix.cell(distro, arch)
        label = self.host_label(cell)
        factory = FigureFactory(self._clock, label)
        host = {
            "image": cell.image,
            "platform": cell.platform,
            "runner": self._label,
            "emulated": bool(self.emulated(cell)) if cell.image else None,
        }
        if not cell.image:
            figures = self._skipped(cell, cell.reason, factory)
            return SpecsRecord(self._clock.now(), {label: host}, tuple(figures))
        bundle = self._bundle(cell, factory)
        ws = Workspace()
        try:
            wheels, why = PackageBuilder(self._repo, self._settings, self._runner, ws).build()
            if why:
                figures = self._skipped(cell, f"the wheels could not be built: {why}", factory)
                return SpecsRecord(
                    self._clock.now(), {label: host}, tuple(self._keep(figures, bundle))
                )
            out = ws.path("out")
            argv = [
                str(self._settings.linux["docker"]),
                "run",
                "--rm",
                "--platform",
                cell.platform,
                "-v",
                f"{self._repo.resolve()}:/src:ro",
                "-v",
                f"{ws.wheels}:/wheels:ro",
                "-v",
                f"{out}:/out",
                "-e",
                f"{LinuxMatrix.CELL_ENV}={cell.distro}/{cell.arch}",
                "-e",
                f"{LinuxMatrix.EMULATED_ENV}={self.emulated(cell)}",
                "-e",
                f"{LinuxMatrix.HOST_ENV}={label}",
                "-e",
                f"{LinuxMatrix.BEFORE_ENV}=/out/packages-before.txt",
                "-e",
                f"{PackageBuilder.WHEELS_ENV}=/wheels",
                cell.image,
                "/bin/sh",
                "-c",
                self.bootstrap(cell),
            ]
            result = self._runner.run(
                argv, timeout=float(self._settings.linux["container_timeout_s"])
            )
            partial = out / "partial.json"
            if not partial.exists():
                reason = f"the container run failed (exit {result.returncode}): {result.tail()}"
                figures = self._skipped(cell, reason, factory)
                return SpecsRecord(
                    self._clock.now(), {label: host}, tuple(self._keep(figures, bundle))
                )
            measured = SpecsRecord.load(partial)
        finally:
            ws.cleanup()
        own = [f for f in measured.figures if f.id.startswith(f"{cell.prefix}.")]
        hosts = {k: {**dict(v), **host} for k, v in measured.hosts.items() if k == label} or {
            label: host
        }
        return SpecsRecord(self._clock.now(), hosts, tuple(self._keep(own, bundle)))

    @staticmethod
    def _keep(figures: Sequence[Figure], bundle: Sequence[Figure]) -> list[Figure]:
        ids = {f.id for f in bundle}
        return [f for f in figures if f.id not in ids] + list(bundle)


class CellMerger:
    """Folds cell records into the main record, each under its own prefixes, so one cell's
    run never marks another's figures stale. With `complete` (the workflow's merge, after
    every cell's job), a cell that handed nothing over has its figures marked stale with
    that reason. Every declared cell's figures are present afterwards: one never measured
    is skipped, naming why."""

    def __init__(self, settings: SpecsSettings, clock: ClockInterface) -> None:
        self._settings = settings
        self._clock = clock
        self._matrix = LinuxMatrix(settings)

    def _cell_of(self, record: SpecsRecord) -> list[LinuxCell]:
        ids = [f.id for f in record.figures]
        return [c for c in self._matrix.cells() if any(i.startswith(f"{c.prefix}.") for i in ids)]

    def merge(
        self, record: SpecsRecord, partials: Sequence[SpecsRecord], complete: bool = False
    ) -> SpecsRecord:
        derived = Derivations(self._settings).ids()
        figures = list(record.figures)
        hosts = dict(record.hosts)
        covered: set[str] = set()
        for partial in partials:
            for cell in self._cell_of(partial):
                prefixes = self._matrix.prefixes(cell)
                covered.add(cell.prefix)
                policy = StalenessPolicy(
                    derived,
                    f"the {cell.distro}/{cell.arch} cell's run did not report it",
                    lambda fid, p=prefixes: fid.startswith(p),
                )
                figures = [
                    *policy.merge(figures, partial.figures),
                    *[f for f in figures if f.id in derived],
                ]
            hosts.update(partial.hosts)
        present = {f.id for f in figures}
        for cell in self._matrix.cells():
            if complete and cell.prefix not in covered and cell.image:
                prefixes = self._matrix.prefixes(cell)
                policy = StalenessPolicy(
                    derived,
                    f"the {cell.distro}/{cell.arch} cell handed over no record this run",
                    lambda fid, p=prefixes: fid.startswith(p),
                )
                figures = [*policy.merge(figures, []), *[f for f in figures if f.id in derived]]
            reason = (
                cell.reason or "not measured yet: awaiting this cell's run (minimum_specs.py cell)"
            )
            for fid, label, unit in self._matrix.expected(cell):
                if fid not in present:
                    figures.append(
                        Figure(
                            fid,
                            label,
                            None,
                            unit,
                            "skipped",
                            f"minimum_specs.py cell {cell.distro} {cell.arch}",
                            reason=reason,
                        )
                    )
                    present.add(fid)
        merged = replace(
            record,
            generated_at=self._clock.now(),
            hosts=hosts,
            figures=tuple(sorted({f.id: f for f in figures}.values(), key=lambda f: f.id)),
        )
        return RecordBuilder(self._settings, self._clock).rederive(merged)


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
    #: A fit over a sweep may run on part of it: when set, missing inputs are tolerated as
    #: long as at least this many figure inputs are present (the formula names the rest).
    at_least: int = 0


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
                "First install on the wire: krypton + hub + the sovereign model",
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
        return specs + ModelFits(self._settings).specs() + LinuxDerivations(self._settings).specs()

    def _config(self, name: str) -> Any:
        """`config.<table>.<key>`: a value from `[minimum_specs.<table>]`, or KeyError."""
        _, table, key = name.split(".", 2)
        tables: Mapping[str, Mapping[str, Any]] = {
            "growth": self._settings.growth,
            "linux": self._settings.linux,
        }
        return tables[table][key]

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
            if name.startswith("config."):
                try:
                    values[name] = self._config(name)
                except (KeyError, ValueError):
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
            present = sum(1 for k in values if not k.startswith(("assumption.", "config.")))
            if spec.at_least and present >= spec.at_least:
                missing = [m for m in missing if m.startswith(("assumption.", "config."))]
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
                reason = failure or self._missing(spec, missing, present)
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

    @staticmethod
    def _missing(spec: Derivation, missing: Sequence[str], present: int) -> str:
        """Why a derivation could not run: its missing inputs, or, for a fit over a sweep,
        how many points it has against how many it needs and the first one missing."""
        figures = [m for m in missing if not m.startswith(("assumption.", "config."))]
        if spec.at_least and figures and len(figures) == len(missing):
            return (
                f"a fit needing {spec.at_least} of its {present + len(figures)} measured "
                f"points has {present}; missing {figures[0]} and {len(figures) - 1} more"
            )
        return "missing input(s): " + ", ".join(missing)


class ModelFits(DerivationSourceInterface):
    """The fitted models (scripts/requirements_math.py) as derived figures.

    Each parameter is its own figure, so the record keeps the formula and every point the
    fit used, and `check` refits from the committed record: the memory line over the
    measured context sweep, Amdahl's law over each architecture's CPU thread sweep, the
    database's bytes per job, and the ledger's growth integrated over the declared horizon.
    """

    def __init__(self, settings: SpecsSettings, math_: RequirementsMath | None = None) -> None:
        self._settings = settings
        self._math = math_ or RequirementsMath()

    def memory_points(self) -> list[tuple[int, tuple[str, str, str]]]:
        m = self._settings.sovereign_model
        return [
            (
                int(c),
                (
                    f"bench.{m}.ctx{c}.device_mib",
                    f"bench.{m}.ctx{c}.host_model_mib",
                    f"bench.{m}.ctx{c}.host_compute_mib",
                ),
            )
            for c in sorted(int(c) for c in self._settings.bench["contexts"])
        ]

    def memory_fit(self, v: Mapping[str, Any]) -> LinearFit:
        xs, ys = [], []
        for ctx, ids in self.memory_points():
            if all(i in v for i in ids):
                xs.append(float(ctx))
                ys.append(sum(float(v[i]) for i in ids))
        return self._math.least_squares(xs, ys)

    def thread_ids(self, arch: str) -> list[tuple[int, str]]:
        m = self._settings.sovereign_model
        return [
            (int(n), f"bench.{m}.cpu.{arch}.threads{n}.gen_tok_s")
            for n in self._settings.bench["cpu_scaling"]["threads"]
        ]

    def cpu_fit(self, arch: str, v: Mapping[str, Any]) -> AmdahlFit:
        points = [(n, float(v[i])) for n, i in self.thread_ids(arch) if i in v]
        return self._math.amdahl([n for n, _ in points], [t for _, t in points])

    def specs(self) -> list[Derivation]:
        contexts = [c for c, _ in self.memory_points()]
        memory_inputs = tuple(i for _, ids in self.memory_points() for i in ids)
        line = (
            "least squares over (c, device + host model buffer + host compute buffer) at "
            f"c = {', '.join(f'{c:,}' for c in contexts)}: M(c) = M0 + k*c"
        )
        specs = [
            Derivation(
                "fit.memory.m0_mib",
                "Model memory at zero context, M0 (the weights)",
                "MiB",
                f"{line}; M0 = mean(M) - k*mean(c)",
                memory_inputs,
                lambda v: round(self.memory_fit(v).intercept, 1),
            ),
            Derivation(
                "fit.memory.k_kib_per_token",
                "Model memory per context token, k (KV cache and compute buffers)",
                "KiB/token",
                f"{line}; k = sum((c - mean c)(M - mean M)) / sum((c - mean c)^2), x 1024",
                memory_inputs,
                lambda v: round(self.memory_fit(v).slope * 1024, 3),
            ),
            Derivation(
                "fit.memory.r2",
                "Memory line's coefficient of determination, R^2",
                "ratio",
                f"{line}; R^2 = 1 - SS_res / SS_tot",
                memory_inputs,
                lambda v: round(self.memory_fit(v).r2, 6),
            ),
            Derivation(
                "fit.memory.max_residual_mib",
                "Memory line's largest residual, |M - M(c)|",
                "MiB",
                f"{line}; max over the points of |M - (M0 + k*c)|",
                memory_inputs,
                lambda v: round(self.memory_fit(v).max_abs_residual, 1),
            ),
            Derivation(
                "postgres.bytes_per_job",
                "Database growth for one project and one job",
                "bytes",
                "database after `new` + one `worker --once` - the empty migrated database",
                ("postgres.after_one_job_bytes", "postgres.empty_db_bytes"),
                lambda v: int(v["postgres.after_one_job_bytes"] - v["postgres.empty_db_bytes"]),
                note="page-granular, so an upper bound for one job",
            ),
            Derivation(
                "disk.ledger_growth_gb",
                "Ledger growth over the declared horizon",
                "GB",
                "integral from 0 to H of b*(r0 + r1*t) dt = b*(r0*H + r1*H^2/2), / 1e9",
                (
                    "postgres.bytes_per_job",
                    "config.growth.jobs_per_day",
                    "config.growth.jobs_per_day_growth",
                    "config.growth.horizon_days",
                ),
                lambda v: round(
                    self._math.integral_of_linear_rate(
                        v["postgres.bytes_per_job"],
                        v["config.growth.jobs_per_day"],
                        v["config.growth.jobs_per_day_growth"],
                        v["config.growth.horizon_days"],
                    )
                    / 1e9,
                    2,
                ),
            ),
        ]
        threads = [int(n) for n in self._settings.bench["cpu_scaling"]["threads"]]
        sweep = f"over generation rates at n = {', '.join(map(str, threads))} threads"
        amdahl = (
            "1/T = (1-p)/T1 + (p/T1)(1/n) by least squares on (1/n, 1/T); T1 = 1/(a+b), p = b/(a+b)"
        )
        knee = "config.linux.cpu_knee_tok_s_per_core"
        for arch in LinuxMatrix(self._settings).arches():
            ids = tuple(i for _, i in self.thread_ids(arch))
            f = f"fit.cpu.{arch}"

            def fit(v: Mapping[str, Any], a: str = arch) -> AmdahlFit:
                return self.cpu_fit(a, v)

            specs += [
                Derivation(
                    f"{f}.t1_tok_s",
                    f"CPU generation on one core, T1 ({arch})",
                    "tokens/s",
                    f"Amdahl T(n) = T1 / ((1-p) + p/n) {sweep}: {amdahl}",
                    ids,
                    lambda v, g=fit: round(g(v).t1, 3),
                    at_least=3,
                ),
                Derivation(
                    f"{f}.p",
                    f"Parallel fraction of CPU generation, p ({arch})",
                    "ratio",
                    f"Amdahl {sweep}: p = b/(a+b)",
                    ids,
                    lambda v, g=fit: round(g(v).p, 4),
                    at_least=3,
                ),
                Derivation(
                    f"{f}.r2",
                    f"Amdahl fit's R^2 on the measured rates ({arch})",
                    "ratio",
                    f"Amdahl {sweep}; R^2 of T(n) against the measured T",
                    ids,
                    lambda v, g=fit: round(g(v).r2, 4),
                    at_least=3,
                ),
                Derivation(
                    f"{f}.asymptote_tok_s",
                    f"CPU generation with unlimited cores, T1/(1-p) ({arch})",
                    "tokens/s",
                    "lim n->inf T(n) = T1 / (1-p)",
                    ids,
                    lambda v, g=fit: round(g(v).asymptote, 2) if g(v).p < 1 else "unbounded",
                    at_least=3,
                ),
                Derivation(
                    f"{f}.knee_cores",
                    f"Recommended cores: the knee where dT/dn falls to the threshold ({arch})",
                    "cores",
                    "dT/dn = T1*p / ((1-p)n + p)^2 = theta  =>  n* = (sqrt(T1*p/theta) - p)/(1-p); ceil",
                    (*ids, knee),
                    lambda v, g=fit: (
                        math.ceil(self._math.knee(g(v), v[knee]))
                        if math.isfinite(self._math.knee(g(v), v[knee]))
                        else "unbounded"
                    ),
                    at_least=3,
                ),
                Derivation(
                    f"{f}.minimum_cores",
                    f"Minimum cores: the fewest that reach the minimum generation rate ({arch})",
                    "cores",
                    "T(n) >= F  <=>  n >= p / (T1/F - (1-p)), solvable only when F < T1/(1-p); ceil",
                    (*ids, "assumption.minimum_gen_tok_s"),
                    lambda v, g=fit: (
                        self._math.cores_for_rate(g(v), v["assumption.minimum_gen_tok_s"])
                        or "unreachable"
                    ),
                    at_least=3,
                ),
            ]
        return specs


class LinuxDerivations(DerivationSourceInterface):
    """The Linux matrix's requirements, per (distribution x architecture) cell.

    Memory is the same for every cell: the model dominates, and its weights and KV cache are
    the same bytes on any Linux (the fit's compute buffers come from the measured host's
    backend). Cores come from the architecture's Amdahl fit. Disk and the floors are each
    cell's own: its package closures, its install, its packaged versions against the floors
    vibey declares.
    """

    def __init__(self, settings: SpecsSettings, math_: RequirementsMath | None = None) -> None:
        self._settings = settings
        self._math = math_ or RequirementsMath()
        self._matrix = LinuxMatrix(settings)

    def _round_up(self, value: float) -> float | None:
        sizes = sorted(float(s) for s in self._settings.assumptions["memory_sizes_gb"])
        return next((s for s in sizes if s >= value), None)

    def specs(self) -> list[Derivation]:
        m = self._settings.sovereign_model
        hi = max(int(c) for c in self._settings.bench["contexts"])
        h, probe = "config.linux.memory_headroom_factor", "config.linux.probe_memory_gb"
        m0, k = "fit.memory.m0_mib", "fit.memory.k_kib_per_token"
        window = "declared.runner_context_window"
        side, osh, apps = (
            "ram.vibey_side_gib",
            "assumption.os_headroom_gib",
            "assumption.apps_headroom_gib",
        )

        def model_mib(v: Mapping[str, Any], ctx: float) -> float:
            return float(v[m0]) + float(v[k]) / 1024 * ctx

        specs = [
            Derivation(
                "linux.ram.minimum_need_gib",
                "Linux memory needed: the model at the runner's window, with headroom, + vibey + OS",
                "GiB",
                "h * (M0 + k*c_runner) / 1024 + vibey side + OS headroom",
                (m0, k, window, h, side, osh),
                lambda v: round(v[h] * model_mib(v, v[window]) / 1024 + v[side] + v[osh], 2),
            ),
            Derivation(
                "linux.ram.minimum_gb",
                "Linux minimum memory (system RAM, as sold)",
                "GB",
                "the smallest declared memory size >= the need",
                ("linux.ram.minimum_need_gib",),
                lambda v: self._round_up(v["linux.ram.minimum_need_gib"]),
            ),
            Derivation(
                "linux.ram.recommended_need_gib",
                "Linux memory recommended: the model at its maximum window, + apps",
                "GiB",
                f"h * (M0 + k*{hi:,}) / 1024 + vibey side + OS headroom + apps headroom",
                (m0, k, h, side, osh, apps),
                lambda v: round(v[h] * model_mib(v, hi) / 1024 + v[side] + v[osh] + v[apps], 2),
            ),
            Derivation(
                "linux.ram.recommended_gb",
                "Linux recommended memory (system RAM, as sold)",
                "GB",
                "the smallest declared memory size >= the recommended need",
                ("linux.ram.recommended_need_gib",),
                lambda v: self._round_up(v["linux.ram.recommended_need_gib"]),
            ),
            Derivation(
                "linux.ram.max_context_at_probe",
                "The largest context whose model fits the probed memory size",
                "tokens",
                "c_max = ((S*1e9/2^20 - (vibey side + OS headroom)*1024) / h - M0) / (k/1024), floored at 0",
                (m0, k, h, probe, side, osh),
                lambda v: max(
                    0,
                    math.floor(
                        ((v[probe] * 1e9 / MIB - (v[side] + v[osh]) * 1024) / v[h] - v[m0])
                        / (v[k] / 1024)
                    ),
                ),
            ),
            Derivation(
                "linux.ram.probe_fits_runner",
                "The probed memory size holds the runner's window",
                "verdict",
                "c_max >= the runner's context window",
                ("linux.ram.max_context_at_probe", window),
                lambda v: v["linux.ram.max_context_at_probe"] >= v[window],
            ),
        ]
        optional = list(self._settings.ollama["optional_models"])
        for cell in self._matrix.cells():
            p = cell.prefix
            b = self._matrix.bundle_prefix(cell.arch)
            engine, krypton = f"{p}.install.vibey-engine", f"{p}.install.krypton-app"
            specs += [
                Derivation(
                    f"{p}.disk.minimum_need_gb",
                    f"{cell.name} ({cell.arch}): free disk needed",
                    "GB",
                    "(base + PostgreSQL closures + engine venv + uv cache + Ollama bundle unpacked + model + git objects + minimum worktrees x one worktree) / 1e9 + Postgres data allowance",
                    (
                        f"{p}.pkg.base.bytes",
                        f"{p}.pkg.postgres.bytes",
                        f"{engine}.venv_bytes",
                        f"{engine}.uv_cache_bytes",
                        f"{b}.unpacked_bytes",
                        f"model.{m}.download_bytes",
                        "disk.git_pack_mib",
                        "assumption.minimum_worktrees",
                        "disk.worktree_bytes",
                        "assumption.postgres_data_allowance_gb",
                    ),
                    lambda v, p=p, b=b, e=engine: round(
                        (
                            v[f"{p}.pkg.base.bytes"]
                            + v[f"{p}.pkg.postgres.bytes"]
                            + v[f"{e}.venv_bytes"]
                            + v[f"{e}.uv_cache_bytes"]
                            + v[f"{b}.unpacked_bytes"]
                            + v[f"model.{m}.download_bytes"]
                            + v["disk.git_pack_mib"] * MIB
                            + v["assumption.minimum_worktrees"] * v["disk.worktree_bytes"]
                        )
                        / 1e9
                        + v["assumption.postgres_data_allowance_gb"],
                        1,
                    ),
                ),
                Derivation(
                    f"{p}.disk.minimum_gb",
                    f"{cell.name} ({cell.arch}): minimum free disk",
                    "GB",
                    "the need rounded up to the next 10 GB",
                    (f"{p}.disk.minimum_need_gb",),
                    lambda v, p=p: math.ceil(v[f"{p}.disk.minimum_need_gb"] / 10) * 10,
                ),
                Derivation(
                    f"{p}.disk.with_ledger_gb",
                    f"{cell.name} ({cell.arch}): free disk with the ledger's growth",
                    "GB",
                    "minimum need + ledger growth over the horizon",
                    (f"{p}.disk.minimum_need_gb", "disk.ledger_growth_gb"),
                    lambda v, p=p: round(
                        v[f"{p}.disk.minimum_need_gb"] + v["disk.ledger_growth_gb"], 1
                    ),
                ),
                Derivation(
                    f"{p}.disk.recommended_need_gb",
                    f"{cell.name} ({cell.arch}): free disk recommended",
                    "GB",
                    "minimum need + desktop closure + krypton-app venv + optional models + dev venv + further worktrees + room to re-pull the model",
                    (
                        f"{p}.disk.minimum_need_gb",
                        f"{p}.pkg.desktop.bytes",
                        f"{krypton}.venv_bytes",
                        *[f"model.{o}.download_bytes" for o in optional],
                        "disk.dev_venv_bytes",
                        "assumption.recommended_worktrees",
                        "assumption.minimum_worktrees",
                        "disk.worktree_bytes",
                        f"model.{m}.download_bytes",
                    ),
                    lambda v, p=p, kr=krypton: round(
                        v[f"{p}.disk.minimum_need_gb"]
                        + (
                            v[f"{p}.pkg.desktop.bytes"]
                            + v[f"{kr}.venv_bytes"]
                            + sum(v[f"model.{o}.download_bytes"] for o in optional)
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
                    f"{p}.disk.recommended_gb",
                    f"{cell.name} ({cell.arch}): recommended free disk",
                    "GB",
                    "the recommended need rounded up to the next 10 GB",
                    (f"{p}.disk.recommended_need_gb",),
                    lambda v, p=p: math.ceil(v[f"{p}.disk.recommended_need_gb"] / 10) * 10,
                ),
                Derivation(
                    f"{p}.floor.postgres",
                    f"{cell.name} ({cell.arch}): packaged PostgreSQL meets vibey's floor",
                    "verdict",
                    "major(packaged PostgreSQL) >= the floor vibey checks on connect",
                    (f"{p}.packaged.postgres", "declared.postgres_min_major"),
                    lambda v, p=p: (
                        Versions.major(v[f"{p}.packaged.postgres"])
                        >= int(v["declared.postgres_min_major"])
                    ),
                ),
                Derivation(
                    f"{p}.floor.python",
                    f"{cell.name} ({cell.arch}): packaged Python meets the floor (else uv fetches one)",
                    "verdict",
                    "packaged python3 >= the oldest Python vibey-engine runs on",
                    (f"{p}.packaged.python", "python.floor"),
                    lambda v, p=p: Versions.at_least(v[f"{p}.packaged.python"], v["python.floor"]),
                ),
                Derivation(
                    f"{p}.floor.glibc",
                    f"{cell.name} ({cell.arch}): glibc meets the installed wheels' manylinux floor",
                    "verdict",
                    "glibc >= the newest glibc any installed wheel requires",
                    (f"{p}.glibc", f"{p}.install.glibc_floor"),
                    lambda v, p=p: Versions.at_least(
                        v[f"{p}.glibc"], v[f"{p}.install.glibc_floor"]
                    ),
                ),
                Derivation(
                    f"{p}.floor.desktop",
                    f"{cell.name} ({cell.arch}): packaged desktop libraries meet the client's floors",
                    "verdict",
                    "glib, json-glib, gtk4 and libadwaita each >= the meson.build floor",
                    (
                        f"{p}.packaged.glib",
                        "declared.desktop_glib",
                        f"{p}.packaged.json_glib",
                        "declared.desktop_json_glib",
                        f"{p}.packaged.gtk4",
                        "declared.desktop_gtk4",
                        f"{p}.packaged.libadwaita",
                        "declared.desktop_libadwaita",
                    ),
                    lambda v, p=p: all(
                        Versions.at_least(v[f"{p}.packaged.{role}"], v[f"declared.desktop_{role}"])
                        for role in ("glib", "json_glib", "gtk4", "libadwaita")
                    ),
                ),
            ]
        return specs


# ------------------------------------------------------------------------ staleness


class StalenessPolicy(StalenessPolicyInterface):
    """A measurement that could not run keeps its last value, marked stale -- never reused
    silently. A `once` figure the weekly probes never re-measure keeps its own date.

    `scope` says which figures this run was responsible for. One outside it (a Linux cell's
    figure during the macOS run, or a probe left out by `--only`) is kept exactly as it was:
    not re-measured, but not this run's to mark stale either. A fresh figure outside the
    scope is dropped. With no scope, every figure is in it.
    """

    def __init__(
        self,
        derived_ids: set[str],
        unreported: str = "not reported by this run's probes",
        scope: Callable[[str], bool] | None = None,
    ) -> None:
        self._derived = derived_ids
        self._unreported = unreported
        self._scope = scope

    def in_scope(self, fid: str) -> bool:
        return self._scope is None or self._scope(fid)

    def merge(self, previous: Sequence[Figure], fresh: Sequence[Figure]) -> list[Figure]:
        now = {f.id: f for f in fresh if self.in_scope(f.id)}
        out: dict[str, Figure] = {}
        for old in previous:
            if old.id in self._derived:
                continue  # recomputed by the derivations from the merged inputs
            if not self.in_scope(old.id):
                out[old.id] = old
                continue
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
                f"krypton launcher + hub idle {self.c('process.krypton.idle_rss_mib')}",
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
        return self.provenance_of([fid for row in rows for fid in row.figures])

    def provenance_of(self, roots: Sequence[str]) -> tuple[str, str]:
        """The hosts and the date range of every dated figure behind `roots`, inputs included."""
        ids: set[str] = set()
        frontier = list(roots)
        while frontier:
            fid = frontier.pop()
            if fid in ids:
                continue
            ids.add(fid)
            figure = self._f.get(fid)
            if figure is not None and figure.inputs:
                frontier += [
                    k for k in figure.inputs if not k.startswith(("assumption.", "config."))
                ]
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


class LinuxTables:
    """The Linux matrix's tables and the fitted models, composed from the record.

    A cell's run mode (native, emulated, not run) comes from its OS-release figure. Cells in
    these tables are short -- the value, `not measured`, or the value marked stale -- and the
    reasons are listed once, in the status block, rather than repeated across the matrix.
    """

    def __init__(self, record: SpecsRecord, settings: SpecsSettings) -> None:
        self._f = record.by_id()
        self._settings = settings
        self._matrix = LinuxMatrix(settings)
        self.tables = RequirementTables(record, settings)

    def short(self, fid: str) -> str:
        figure = self._f.get(fid)
        if figure is None or not figure.has_value:
            return "not measured"
        text = Formatter.value(figure)
        return f"{text} (stale)" if figure.status == "stale" else text

    def version(self, fid: str) -> str:
        figure = self._f.get(fid)
        if figure is None or not figure.has_value:
            return "not measured"
        try:
            text = ".".join(str(part) for part in Versions.key(str(figure.value)))
        except ValueError:
            text = str(figure.value)
        return f"{text} (stale)" if figure.status == "stale" else text

    def glibc(self, p: str) -> str:
        """The image's glibc, against the newest glibc its installed wheels require."""
        have, need = self.version(f"{p}.glibc"), self._f.get(f"{p}.install.glibc_floor")
        if need is None or not need.has_value:
            return f"{have} (the wheels' floor not measured)"
        return f"{have} (wheels need {self.version(need.id)}: {self.short(f'{p}.floor.glibc')})"

    def mode(self, cell: LinuxCell) -> str:
        figure = self._f.get(f"{cell.prefix}.os_release")
        if figure is None or not figure.has_value:
            return "not run" if not cell.image else "not measured"
        emulated = bool(dict(figure.conditions).get("emulated"))
        return "emulated" if emulated else "native"

    def floors(self) -> tuple[list[list[str]], list[str]]:
        rows, ids = [], []
        for cell in self._matrix.cells():
            p, mode = cell.prefix, self.mode(cell)
            if mode == "not run":
                rows.append([cell.name, cell.arch, f"not run: {cell.reason}", *["-"] * 6])
                continue
            fids = [
                f"{p}.os_release",
                f"{p}.glibc",
                f"{p}.install.glibc_floor",
                f"{p}.floor.glibc",
                f"{p}.packaged.kernel",
                f"{p}.packaged.python",
                f"{p}.floor.python",
                f"{p}.packaged.postgres",
                f"{p}.floor.postgres",
                f"{p}.packaged.gtk4",
                f"{p}.packaged.libadwaita",
                f"{p}.floor.desktop",
            ]
            ids += fids
            rows.append(
                [
                    cell.name,
                    cell.arch,
                    mode,
                    self.short(f"{p}.os_release"),
                    self.glibc(p),
                    self.version(f"{p}.packaged.kernel"),
                    f"{self.version(f'{p}.packaged.python')} (>= {self.short('python.floor')}: {self.short(f'{p}.floor.python')})",
                    f"{self.version(f'{p}.packaged.postgres')} (>= {self.short('declared.postgres_min_major')}: {self.short(f'{p}.floor.postgres')})",
                    f"gtk4 {self.version(f'{p}.packaged.gtk4')}, libadwaita {self.version(f'{p}.packaged.libadwaita')} (meet floors: {self.short(f'{p}.floor.desktop')})",
                ]
            )
        return rows, ids

    def requirements(self) -> tuple[list[list[str]], list[str]]:
        rows, ids = [], []
        memory = f"{self.short('linux.ram.minimum_gb')} / {self.short('linux.ram.recommended_gb')}"
        for cell in self._matrix.cells():
            p, f = cell.prefix, f"fit.cpu.{cell.arch}"
            fids = [
                "linux.ram.minimum_gb",
                "linux.ram.recommended_gb",
                f"{f}.minimum_cores",
                f"{f}.knee_cores",
                f"{p}.disk.minimum_gb",
                f"{p}.disk.recommended_gb",
            ]
            ids += fids
            disk = (
                "-"
                if self.mode(cell) == "not run"
                else f"{self.short(f'{p}.disk.minimum_gb')} / {self.short(f'{p}.disk.recommended_gb')}"
            )
            rows.append(
                [
                    cell.name,
                    cell.arch,
                    memory,
                    f"{self.short(f'{f}.minimum_cores')} / {self.short(f'{f}.knee_cores')}",
                    disk,
                    self.tables.basis(*fids),
                ]
            )
        return rows, ids

    def models(self) -> tuple[str, list[str]]:
        """The fitted models in math notation, with their parameters and fit quality."""
        s, lin = self._settings, self._settings.linux
        window = self.short("declared.runner_context_window")
        hi = max(int(c) for c in s.bench["contexts"])
        a = s.assumptions
        m0, k = self.short("fit.memory.m0_mib"), self.short("fit.memory.k_kib_per_token")
        lines = [
            "Memory against context: least squares over the measured sweep",
            "",
            "    M(c) = M₀ + k·c",
            f"    M₀ = {m0}   k = {k} KiB/token   R² = {self.short('fit.memory.r2')}   max |residual| = {self.short('fit.memory.max_residual_mib')}",
            "",
            f"Linux memory: h = {lin['memory_headroom_factor']:g} (declared headroom), the model held in system RAM",
            "",
            "    RAM(c) = h·M(c)/1024 + vibey side + OS headroom",
            f"    minimum     = RAM({window}) = {self.short('linux.ram.minimum_need_gib')} → {self.short('linux.ram.minimum_gb')}",
            f"    recommended = RAM({hi:,}) + apps headroom ({a['apps_headroom_gib']:g} GiB) = {self.short('linux.ram.recommended_need_gib')} → {self.short('linux.ram.recommended_gb')}",
            f"    c_max({lin['probe_memory_gb']:g} GB) = ((S·10⁹/2²⁰ − (side + OS)·1024)/h − M₀)/(k/1024) = {self.short('linux.ram.max_context_at_probe')} tokens; holds {window}: {self.short('linux.ram.probe_fits_runner')}",
            "",
            "CPU throughput against cores: Amdahl's law, per architecture",
            "",
            "    T(n) = T₁ / ((1 − p) + p/n)       fitted as 1/T = (1 − p)/T₁ + (p/T₁)·(1/n)",
            "    dT/dn = T₁·p / ((1 − p)·n + p)²",
            f"    knee:  dT/dn = θ  ⇒  n* = (√(T₁·p/θ) − p)/(1 − p),  θ = {lin['cpu_knee_tok_s_per_core']:g} tok/s per core",
            f"    floor: T(n) ≥ F  ⇔  n ≥ p/(T₁/F − (1 − p)),  F = {a['minimum_gen_tok_s']:g} tok/s; none if F ≥ T₁/(1 − p)",
        ]
        ids = [
            "fit.memory.m0_mib",
            "fit.memory.k_kib_per_token",
            "fit.memory.r2",
            "fit.memory.max_residual_mib",
            "linux.ram.minimum_gb",
            "linux.ram.recommended_gb",
            "linux.ram.max_context_at_probe",
        ]
        for arch in self._matrix.arches():
            f = f"fit.cpu.{arch}"
            ids += [f"{f}.t1_tok_s", f"{f}.p", f"{f}.knee_cores", f"{f}.minimum_cores"]
            lines.append(
                f"    {arch}: T₁ = {self.short(f'{f}.t1_tok_s')}, p = {self.short(f'{f}.p')}, R² = {self.short(f'{f}.r2')}, "
                f"T∞ = {self.short(f'{f}.asymptote_tok_s')}; knee {self.short(f'{f}.knee_cores')}, minimum {self.short(f'{f}.minimum_cores')}"
            )
        g = s.growth
        ids += ["postgres.bytes_per_job", "disk.ledger_growth_gb"]
        lines += [
            "",
            "Ledger growth: append-only, so the disk it needs is the integral of its rate",
            "",
            "    D(H) = ∫₀ᴴ b·(r₀ + r₁·t) dt = b·(r₀·H + r₁·H²/2)",
            f"    b = {self.short('postgres.bytes_per_job')} per job, r₀ = {g['jobs_per_day']:g} jobs/day, "
            f"r₁ = {g['jobs_per_day_growth']:g} jobs/day², H = {g['horizon_days']:g} days  ⇒  D = {self.short('disk.ledger_growth_gb')}",
        ]
        return "```text\n" + "\n".join(lines) + "\n```\n", ids


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

    def _provenance(self, tables: RequirementTables, ids: Sequence[str]) -> str:
        host, span = tables.provenance_of(ids)
        return (
            f"*Measured on {host}; figures dated {span} (UTC). Source: "
            f"[`{self._settings.record}`](https://github.com/the-vibey-project/vibey/blob/develop/{self._settings.record}), "
            f"regenerated by `{SCRIPT}`; do not edit inside these markers.*\n\n"
        )

    def _matrix(
        self,
        tables: RequirementTables,
        rows: Sequence[Sequence[str]],
        ids: Sequence[str],
        header: Sequence[str],
    ) -> str:
        head = "| " + " | ".join(header) + " |\n|" + "---|" * len(header) + "\n"
        body = "".join("| " + " | ".join(self._cell(c) for c in row) + " |\n" for row in rows)
        return self._provenance(tables, ids) + head + body

    def _models(self, tables: RequirementTables, text: str, ids: Sequence[str]) -> str:
        return self._provenance(tables, ids) + text

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
        linux = LinuxTables(record, self._settings)
        return {
            "hardware": self._table(t, t.hardware()),
            "software": self._table(t, t.software()),
            "network": self._table(t, t.network()),
            "clients": self._table(t, t.clients()),
            "linux-floors": self._matrix(
                t,
                *linux.floors(),
                [
                    "Distribution",
                    "Arch",
                    "Run",
                    "OS release",
                    "glibc",
                    "Kernel (packaged)",
                    "Python (packaged)",
                    "PostgreSQL (packaged)",
                    "Desktop libraries (packaged)",
                ],
            ),
            "linux-requirements": self._matrix(
                t,
                *linux.requirements(),
                [
                    "Distribution",
                    "Arch",
                    "Memory min / rec",
                    "Cores min / rec",
                    "Disk min / rec",
                    "Basis",
                ],
            ),
            "linux-models": self._models(t, *linux.models()),
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
        # Not `\$`: the paper's render check reads an escaped dollar as math that failed.
        "$": r"\textdollar{}",
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
        return {"minimum-requirements": "\n".join(lines), "linux-requirements": self.linux(record)}

    LINUX_LABEL = "tab:linux-requirements"

    def linux(self, record: SpecsRecord) -> str:
        """The Linux matrix, one row per cell, and the fitted models in its caption."""
        linux = LinuxTables(record, self._settings)
        rows, ids = linux.requirements()
        floors, floor_ids = linux.floors()
        host, span = linux.tables.provenance_of([*ids, *floor_ids])
        lines = [
            "```latex",
            r"\begin{table*}[t]",
            r"\centering\footnotesize",
            r"\begin{tabular}{@{}p{1.2in}p{0.55in}p{0.65in}p{0.8in}p{0.8in}p{0.9in}p{1.2in}@{}}",
            r"\textbf{Distribution} & \textbf{Arch} & \textbf{Run} & \textbf{Cores min / rec} & "
            r"\textbf{Disk min / rec} & \textbf{PostgreSQL} & \textbf{glibc}\\",
            r"\hline",
        ]
        for row, floor in zip(rows, floors, strict=True):
            run = "not run" if floor[2].startswith("not run") else floor[2]
            cells = (row[0], row[1], run, row[3], row[4], floor[7], floor[4])
            lines.append(" & ".join(self.tex(c) for c in cells) + r"\\")
        lines += [
            r"\end{tabular}",
            r"\caption{The Linux matrix: each supported distribution on each architecture, measured "
            r"in the distribution's own container image. Memory is the same for every cell, "
            + self.tex(linux.short("linux.ram.minimum_gb"))
            + " minimum and "
            + self.tex(linux.short("linux.ram.recommended_gb"))
            + r" recommended, from the least-squares line $M(c) = M_0 + kc$ fitted to the measured "
            + "model memory ($M_0$ = "
            + self.tex(linux.short("fit.memory.m0_mib"))
            + ", $k$ = "
            + self.tex(linux.short("fit.memory.k_kib_per_token"))
            + " KiB/token, $R^2$ = "
            + self.tex(linux.short("fit.memory.r2"))
            + r") with a declared headroom factor. Cores come from Amdahl's law fitted per "
            r"architecture: the minimum reaches the minimum generation rate, the recommended is "
            r"the knee where $dT/dn$ falls to a declared threshold. An emulated cell's sizes "
            r"and versions stand; its timings are refused. "
            + f"Measured on {self.tex(host)}, figures dated {self.tex(span)} (UTC).}}",
            rf"\label{{{self.LINUX_LABEL}}}",
            r"\end{table*}",
            "```",
        ]
        return "\n".join(lines)

    def apply(self, document: str, record: SpecsRecord) -> str:
        return GeneratedBlocks.replace_all(document, self.blocks(record))

    def drift(self, document: str, record: SpecsRecord) -> list[str]:
        return GeneratedBlocks.drift(document, self.blocks(record))


# ------------------------------------------------------------------------ the session


class MeasurementSession:
    """Runs every probe in order, merges with the previous record, derives, and returns the
    new record. The scratch database and the scratch directory are always cleaned up.

    On a host it measures everything but the Linux matrix, whose figures are each cell's
    own and are left as they were. Inside a cell's container (`$VIBEY_SPECS_CELL` set by
    `cell`) it runs the Linux probe alone and is responsible for that cell's figures only.
    """

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

    def cell(self) -> LinuxCell | None:
        """The matrix cell this run measures, when it runs inside one's container."""
        named = self._environ.get(LinuxMatrix.CELL_ENV, "")
        if not named:
            return None
        distro, _, arch = named.partition("/")
        return LinuxMatrix(self._settings).cell(distro, arch)

    def _cell_probes(
        self, cell: LinuxCell, figures: FigureFactory, ws: Workspace
    ) -> Iterator[ProbeInterface]:
        s = self._settings
        emulated = self._environ.get(LinuxMatrix.EMULATED_ENV, "")
        builder = PackageBuilder(self._repo, s, self._runner, ws, self._environ)
        install = InstallFootprintProbe(
            s,
            self._runner,
            builder,
            ws,
            DirectorySize(self._runner),
            figures,
            prefix=f"{cell.prefix}.install",
            only=list(s.linux["install_targets"]),
            emulated=emulated,
        )
        listing = self._environ.get(LinuxMatrix.BEFORE_ENV, "")
        before: set[str] | None = None
        with contextlib.suppress(OSError):
            if listing:
                text = Path(listing).read_text(encoding="utf-8")
                before = {line.strip() for line in text.splitlines() if line.strip()}
        manager = PackageManager(
            LinuxMatrix(s).package_manager(cell.distro),
            self._runner,
            float(s.linux["package_timeout_s"]),
        )
        yield LinuxCellProbe(s, cell, manager, install, figures, before, emulated)

    def _probes(
        self, figures: FigureFactory, ws: Workspace, postgres_holder: list[PostgresProbe]
    ) -> Iterator[ProbeInterface]:
        cell = self.cell()
        if cell is not None:
            yield from self._cell_probes(cell, figures, ws)
            return
        s = self._settings
        sizes = DirectorySize(self._runner)
        builder = PackageBuilder(self._repo, s, self._runner, ws, self._environ)
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
        cell = self.cell()
        host = self._environ.get(LinuxMatrix.HOST_ENV) or HostDescriber.host_id(info)
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
        if info.get("ram_bytes") and cell is None:
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
        if cell is not None:
            mine = f"{cell.prefix}."
            scope: Callable[[str], bool] = lambda fid: fid.startswith(mine)  # noqa: E731
        else:
            scope = lambda fid: not fid.startswith("linux.")  # noqa: E731
        return RecordBuilder(self._settings, self._clock).build(
            previous, fresh, {host: info}, unreported=unreported, scope=scope
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
        scope: Callable[[str], bool] | None = None,
    ) -> SpecsRecord:
        derivations = Derivations(self._settings)
        merged = StalenessPolicy(derivations.ids(), unreported, scope).merge(
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
        host = sub.add_parser(
            "host", help="what the measure job needs: runner, model, PostgreSQL floor, Ollama log"
        )
        host.add_argument(
            "--github-output", action="store_true", help="as `key=value` lines for $GITHUB_OUTPUT"
        )
        cells = sub.add_parser("cells", help="list the Linux matrix's cells")
        cells.add_argument("--json", action="store_true", help="as a GitHub Actions matrix")
        cell = sub.add_parser("cell", help="measure one Linux cell in its container")
        cell.add_argument("--distro", required=True)
        cell.add_argument("--arch", required=True)
        cell.add_argument("--out", type=Path, required=True, help="the cell's partial record")
        cell.add_argument(
            "--runner-label",
            default="",
            help="what ran it (default: this host's description)",
        )
        merge = sub.add_parser("merge", help="fold Linux cell records into the record")
        merge.add_argument("partials", type=Path, nargs="*")
        merge.add_argument(
            "--complete",
            action="store_true",
            help="every cell was expected: one with no record goes stale, with that reason",
        )
        sub.add_parser("derive", help="recompute the derived figures in the record")
        sub.add_parser("render", help="rewrite the GENERATED blocks from the record")
        sub.add_parser(
            "check", help="exit 1 if the record's derivations or the blocks are out of step"
        )
        return parser

    def _host(self, repo: Path, settings: SpecsSettings, github_output: bool) -> int:
        """The measure job's runner, the model it pulls, the PostgreSQL major it runs and the
        file Ollama's server must log to (on this host), all from the declared sources, so
        the workflow restates none of them."""
        figures = FigureFactory(self._clock, "repository")
        floor = next(
            f
            for f in DeclaredFloorsProbe(repo, settings, figures).run()
            if f.id == "declared.postgres_min_major"
        )
        if not floor.has_value:
            print(f"{SCRIPT}: the PostgreSQL floor: {floor.reason}", file=sys.stderr)
            return 1
        values = {
            "runner": str(settings.host["runner"]),
            "model": settings.sovereign_model,
            "postgres_floor": str(floor.value),
            "server_log": os.path.expanduser(str(settings.ollama["server_log"])),
        }
        separator = "=" if github_output else "\t"
        for key, value in values.items():
            print(f"{key}{separator}{value}")
        return 0

    @staticmethod
    def _cells(settings: SpecsSettings, as_json: bool) -> int:
        cells = LinuxMatrix(settings).cells()
        if as_json:
            include = [
                {
                    "distro": c.distro,
                    "arch": c.arch,
                    "runner": c.runner,
                    "image": c.image,
                }
                for c in cells
            ]
            print(json.dumps({"include": include}, separators=(",", ":")))
            return 0
        for c in cells:
            print(f"{c.distro}\t{c.arch}\t{c.runner}\t{c.image or '-'}\t{c.reason or ''}")
        return 0

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
        if args.command == "host":
            return self._host(repo, settings, args.github_output)
        if args.command == "cells":
            return self._cells(settings, args.json)
        if args.command == "cell":
            label = args.runner_label or HostDescriber.host_id(
                HostDescriber(SubprocessRunner()).describe()
            )
            partial = CellRunner(repo, settings, SubprocessRunner(), self._clock, label).run(
                args.distro, args.arch
            )
            out = args.out if args.out.is_absolute() else repo / args.out
            partial.save(out)
            counts = {s: sum(1 for f in partial.figures if f.status == s) for s in STATUSES}
            print(f"{SCRIPT}: wrote {out}: " + ", ".join(f"{n} {s}" for s, n in counts.items()))
            return 0
        record = SpecsRecord.load(record_path)
        if args.command == "merge":
            partials = [SpecsRecord.load(path) for path in args.partials]
            CellMerger(settings, self._clock).merge(record, partials, args.complete).save(
                record_path
            )
            print(f"{SCRIPT}: merged {len(partials)} cell record(s) into {record_path}")
            return 0
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
