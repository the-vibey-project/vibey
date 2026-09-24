# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How many runs of one local model fit on this device at once -- measured, never assumed.

Sub-doctrine 8.c runs each loop as one instance fed by a queue, and says of a model on the
operator's own hardware "one run at a time". Sub-doctrine 8.j says every part of the family
fits itself to the machine it runs on, by measurement, and that correctness is never traded
for speed. The number of concurrent runs is exactly such a fit, so this module measures it:

1. **A corpus of turns.** `CorpusSampler` draws contiguous segments of turns from a turn pool
   -- chat payloads an agent loop sends, rebuilt with the loop's own code -- stratified by
   prompt depth so the deep tail (the turns a halved context would refuse) is always there.
2. **A sweep.** `SlotSweep` starts a runner at N = 1, 2, 3, ... slots (`SpawnedOllamaServer`),
   replays the corpus with N closed-loop workers (`TurnReplayer`), and samples what the
   hardware charges while it runs (`MemoryWatch`): wired memory, the free share, swap-ins and
   swap-outs, and which models are resident. Every request says `truncate: false` and
   `shift: false`, so a prompt the slot cannot hold is a refusal with a status, never a
   silent loss of its front half. Each completed step is kept at once (`SweepCheckpoint`),
   so an interrupted sweep resumes instead of repeating hours of measurement.
3. **A verdict.** `SlotVerdict` holds each step to declared bounds -- the wired ceiling, no
   rising swap, no new failure or truncation, no model reload, fidelity at temperature 0
   against the one-slot answers -- and names the ideal N: the smallest that reaches the best
   throughput inside every bound. It stops the sweep when a bound breaks or throughput has
   stopped improving.
4. **A gate.** The evidence is keyed to a `DeviceFingerprint` (hardware, memory,
   accelerator, OS, runner version, model digest, context window). `SlotGate` answers "how
   many here?" from the evidence for the *current* fingerprint only, re-judged against the
   bounds declared today: no evidence, or evidence for a device this no longer is, means
   one -- said out loud, with a calibration requested so nobody has to remember to ask.

Everything that touches the machine is behind a seam in
`vibey_gh.interfaces.slots_interface`, so the logic is tested exactly and the measurement is
evidence rather than a test.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import queue
import random
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

from vibey_gh.fit import TextFileReader
from vibey_gh.interfaces.slots_interface import (
    CorpusSamplerInterface,
    DeviceFingerprinterInterface,
    HostMemorySamplerInterface,
    OllamaClientInterface,
    SlotEvidenceStoreInterface,
    SlotGateInterface,
    SlotServerInterface,
    SlotVerdictInterface,
    SweepCheckpointInterface,
    TurnReplayerInterface,
)
from vibey_gh.interfaces.text_file_reader_interface import TextFileReaderInterface

EVIDENCE_SCHEMA = "vibey-gh/slot-evidence/1"
CORPUS_SCHEMA = "vibey-gh/slot-corpus/1"
POOL_SCHEMA = "vibey-gh/turn-pool/1"
#: `[local_models] concurrent_runs = "measured"`: whatever this device's evidence supports.
MEASURED = "measured"
SLOTS_DIR_ENV = "VIBEY_GH_SLOTS_DIR"
DEFAULT_SLOTS_DIR = "~/.local/state/vibey-gh/slots"
#: A port beside the default 11434, so a calibration never takes the production runner's.
DEFAULT_CALIBRATION_PORT = 11435
GB = 1e9

Runner = Callable[[Sequence[str]], str]


def _run(argv: Sequence[str]) -> str:
    """Standard output of `argv`, or `""` when it could not run or failed.

    Module-level for the reason `vibey_gh.fit._run` is: it is the one default every probe
    class takes through its `run` parameter, and a class wrapping a single call would add a
    seam nothing needs.
    """
    try:
        proc = subprocess.run(list(argv), capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout if proc.returncode == 0 else ""


# ---------------------------------------------------------------------------------------
# The declared bounds
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SlotBounds:
    """What a step must stay inside to count, as `[local_models]` declares it (12.c)."""

    #: Peak wired memory as a share of physical memory. Wired, not resident: a model served
    #: on unified memory is wired through Metal, and swap cannot touch it (8.j).
    wired_ceiling_fraction: float = 0.80
    #: Swap-outs may grow to this multiple of the one-slot rate ...
    swap_growth_factor: float = 2.0
    #: ... and are never judged below this rate, in MB per minute, so a quiet baseline does
    #: not turn background noise into a breach.
    swap_floor_mb_per_minute: float = 64.0
    #: Structural agreement with the one-slot answers may fall this far below the one-slot
    #: run's agreement with itself, and no further.
    fidelity_tolerance: float = 0.05
    #: A step "improves" only when it beats the best so far by this share.
    min_throughput_gain: float = 0.10
    #: Evidence older than this many days is stale.
    max_evidence_age_days: float = 30.0

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


# ---------------------------------------------------------------------------------------
# The device
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class DeviceFingerprint:
    """The device a calibration belongs to. Any field changing makes the evidence stale."""

    hardware: str
    processor: str
    memory_bytes: int
    accelerator: str
    os: str
    runtime: str
    model: str
    model_digest: str
    context_window: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def missing(self) -> list[str]:
        """The fields this device would not state. Evidence cannot be keyed to a guess."""
        return [name for name, value in self.as_dict().items() if value in ("", 0)]

    def key(self) -> str:
        canonical = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def differences(self, recorded: Mapping[str, Any]) -> list[str]:
        """Each field on which `recorded` is not this device, in plain words."""
        return [
            f"{name} was {recorded.get(name)!r}, is {value!r}"
            for name, value in self.as_dict().items()
            if recorded.get(name) != value
        ]


class OllamaClient(OllamaClientInterface):
    """An Ollama runner over its HTTP API, with the transport injectable for tests."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_s: float = 10.0,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._open = opener or urllib.request.urlopen

    def _request(
        self, path: str, body: Mapping[str, Any] | None = None, timeout_s: float | None = None
    ) -> tuple[int, Any]:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="GET" if data is None else "POST",
        )
        try:
            with self._open(request, timeout=timeout_s or self._timeout_s) as response:
                status, raw = int(getattr(response, "status", 200)), response.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
        except (OSError, ValueError):
            return 0, None
        try:
            return status, json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return status, None

    def version(self) -> str:
        _, data = self._request("/api/version")
        return str(data.get("version", "")) if isinstance(data, dict) else ""

    def loaded(self) -> list[dict[str, Any]] | None:
        _, data = self._request("/api/ps")
        if not isinstance(data, dict) or not isinstance(data.get("models"), list):
            return None
        return [entry for entry in data["models"] if isinstance(entry, dict)]

    def digest(self, model: str) -> str:
        _, data = self._request("/api/tags")
        if not isinstance(data, dict):
            return ""
        names = {model} if ":" in model.rsplit("/", 1)[-1] else {model, f"{model}:latest"}
        for entry in data.get("models", []) or []:
            if isinstance(entry, dict) and (
                entry.get("name") in names or entry.get("model") in names
            ):
                return str(entry.get("digest", ""))
        return ""

    def chat(self, body: Mapping[str, Any], timeout_s: float) -> tuple[int, dict[str, Any]]:
        status, data = self._request("/api/chat", body, timeout_s)
        if isinstance(data, dict):
            return status, data
        return status, {"error": "no answer" if status == 0 else "an answer that was not JSON"}


class DeviceFingerprinter(DeviceFingerprinterInterface):
    """Reads the device's own statement of itself, on macOS or Linux.

    macOS answers through `sysctl`, `system_profiler` and `sw_vers`; Linux through the
    kernel's files, `nvidia-smi` where there is an NVIDIA accelerator, and `/etc/os-release`.
    A field that cannot be read stays empty, and `DeviceFingerprint.missing` names it: an
    unreadable device is never keyed to a guess.
    """

    def __init__(
        self,
        client: OllamaClientInterface,
        *,
        platform_name: str = "",
        run: Runner | None = None,
        reader: TextFileReaderInterface | None = None,
    ) -> None:
        self._client = client
        self._platform = platform_name or sys.platform
        self._run = run or _run
        self._reader: TextFileReaderInterface = reader or TextFileReader()

    def fingerprint(self, model: str, context_window: int) -> DeviceFingerprint:
        machine = self._linux() if self._platform.startswith("linux") else self._darwin()
        version = self._client.version()
        return DeviceFingerprint(
            **machine,
            runtime=f"ollama {version}" if version else "",
            model=model,
            model_digest=self._client.digest(model),
            context_window=context_window,
        )

    @staticmethod
    def _field(text: str, label: str) -> str:
        match = re.search(rf"^\s*{re.escape(label)}:\s*(.+?)\s*$", text, re.MULTILINE)
        return match.group(1) if match else ""

    def _darwin(self) -> dict[str, Any]:
        hardware = self._run(["sysctl", "-n", "hw.model"]).strip()
        processor = self._run(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()
        raw_memory = self._run(["sysctl", "-n", "hw.memsize"]).strip()
        memory = int(raw_memory) if raw_memory.isdigit() else 0
        if not (hardware and processor and memory):
            # A sandboxed caller may be refused `sysctl` but not `system_profiler`.
            profile = self._run(["system_profiler", "SPHardwareDataType"])
            hardware = hardware or self._field(profile, "Model Identifier")
            processor = processor or self._field(profile, "Chip")
            stated = re.match(r"(\d+)\s*GB", self._field(profile, "Memory"))
            memory = memory or (int(stated.group(1)) * 2**30 if stated else 0)
        displays = self._run(["system_profiler", "SPDisplaysDataType"])
        chipset = self._field(displays, "Chipset Model")
        cores = self._field(displays, "Total Number of Cores")
        accelerator = f"{chipset} GPU, {cores} cores" if chipset and cores else chipset or "none"
        name = self._run(["sw_vers", "-productName"]).strip()
        release = self._run(["sw_vers", "-productVersion"]).strip()
        return {
            "hardware": hardware,
            "processor": processor,
            "memory_bytes": memory,
            "accelerator": accelerator,
            "os": f"{name} {release}".strip(),
        }

    def _linux(self) -> dict[str, Any]:
        hardware = (self._reader.read("/sys/devices/virtual/dmi/id/product_name") or "").strip()
        cpuinfo = self._reader.read("/proc/cpuinfo") or ""
        processor = self._field(cpuinfo, "model name") or self._field(cpuinfo, "Model")
        meminfo = self._reader.read("/proc/meminfo") or ""
        total = re.search(r"^MemTotal:\s*(\d+)\s*kB", meminfo, re.MULTILINE)
        gpus = self._run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"]
        ).strip()
        release = self._reader.read("/etc/os-release") or ""
        pretty = re.search(r'^PRETTY_NAME="?([^"\n]*)"?', release, re.MULTILINE)
        return {
            "hardware": hardware,
            "processor": processor,
            "memory_bytes": int(total.group(1)) * 1024 if total else 0,
            "accelerator": "; ".join(line.strip() for line in gpus.splitlines()) or "none",
            "os": pretty.group(1) if pretty else "",
        }


# ---------------------------------------------------------------------------------------
# What the hardware charges
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HostSample:
    """One reading: wired memory, the free share, and the cumulative swap counters."""

    at: float
    wired_bytes: int
    free_percent: float | None
    swapins: int
    swapouts: int
    page_bytes: int
    readable: bool = True


class DarwinHostSampler(HostMemorySamplerInterface):
    """`vm_stat` for wired pages and swap counters; `memory_pressure -Q` for the free share."""

    def __init__(self, run: Runner | None = None, clock: Callable[[], float] = time.monotonic):
        self._run = run or _run
        self._clock = clock

    def sample(self) -> HostSample:
        stat = self._run(["vm_stat"])
        page = re.search(r"page size of (\d+) bytes", stat)
        counters = {
            key.strip().strip('"'): int(value.strip().rstrip("."))
            for key, _, value in (line.partition(":") for line in stat.splitlines())
            if value.strip().rstrip(".").isdigit()
        }
        pressure = re.search(r"free percentage:\s*(\d+)%", self._run(["memory_pressure", "-Q"]))
        page_bytes = int(page.group(1)) if page else 4096
        return HostSample(
            at=self._clock(),
            wired_bytes=counters.get("Pages wired down", 0) * page_bytes,
            free_percent=float(pressure.group(1)) if pressure else None,
            swapins=counters.get("Swapins", 0),
            swapouts=counters.get("Swapouts", 0),
            page_bytes=page_bytes,
            readable="Pages wired down" in counters,
        )


class LinuxHostSampler(HostMemorySamplerInterface):
    """The kernel's own accounts. Linux has no "wired" figure; the nearest honest one is
    what cannot be reclaimed (`Unevictable`) plus what an NVIDIA accelerator holds, which is
    where a GPU-served model's weights and KV cache live on such a host."""

    def __init__(
        self,
        run: Runner | None = None,
        reader: TextFileReaderInterface | None = None,
        clock: Callable[[], float] = time.monotonic,
        page_bytes: int = 4096,
    ) -> None:
        self._run = run or _run
        self._reader: TextFileReaderInterface = reader or TextFileReader()
        self._clock = clock
        self._page_bytes = page_bytes

    def sample(self) -> HostSample:
        meminfo = self._reader.read("/proc/meminfo") or ""
        fields = {
            key: int(value.split()[0])
            for key, _, value in (line.partition(":") for line in meminfo.splitlines())
            if value.split() and value.split()[0].isdigit()
        }
        vmstat_text = self._reader.read("/proc/vmstat") or ""
        vmstat = {
            parts[0]: int(parts[1])
            for parts in (line.split() for line in vmstat_text.splitlines())
            if len(parts) == 2 and parts[1].isdigit()
        }
        used = self._run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"])
        gpu_mib = sum(int(line.strip()) for line in used.splitlines() if line.strip().isdigit())
        total = fields.get("MemTotal", 0)
        return HostSample(
            at=self._clock(),
            wired_bytes=fields.get("Unevictable", 0) * 1024 + gpu_mib * 2**20,
            free_percent=round(100 * fields.get("MemAvailable", 0) / total, 1) if total else None,
            swapins=vmstat.get("pswpin", 0),
            swapouts=vmstat.get("pswpout", 0),
            page_bytes=self._page_bytes,
            readable=total > 0,
        )


class PlatformProbes:
    """The probes that can read the machine this actually is."""

    @staticmethod
    def host_sampler(platform_name: str = "") -> HostMemorySamplerInterface:
        if (platform_name or sys.platform).startswith("linux"):
            return LinuxHostSampler()
        return DarwinHostSampler()


class MemoryWatch:
    """Samples the host, and the residency of every named runner, while a step runs.

    A background thread takes one sample every `interval_s`; `sample_once` is the same
    reading taken on demand, so a test drives it without a thread or a clock.
    """

    def __init__(
        self,
        sampler: HostMemorySamplerInterface,
        clients: Mapping[str, OllamaClientInterface],
        *,
        interval_s: float = 1.0,
    ) -> None:
        self._sampler = sampler
        self._clients = dict(clients)
        self._interval_s = interval_s
        self.samples: list[HostSample] = []
        self.residency: dict[str, list[list[tuple[str, int, int]] | None]] = {
            label: [] for label in self._clients
        }
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def sample_once(self) -> None:
        self.samples.append(self._sampler.sample())
        for label, client in self._clients.items():
            loaded = client.loaded()
            self.residency[label].append(
                None
                if loaded is None
                else sorted(
                    (
                        str(entry.get("name", "")),
                        int(entry.get("size", 0) or 0),
                        int(entry.get("context_length", 0) or 0),
                    )
                    for entry in loaded
                )
            )

    def _loop(self) -> None:
        while not self._stop.wait(self._interval_s):
            self.sample_once()

    def __enter__(self) -> Self:
        self.sample_once()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        self.sample_once()

    def summary(self) -> dict[str, Any]:
        readable = [sample for sample in self.samples if sample.readable]
        if not readable:
            return {"samples": len(self.samples), "readable": False, "residency": self._residency()}
        first, last = readable[0], readable[-1]
        minutes = max((last.at - first.at) / 60, 1e-9)
        frees = [sample.free_percent for sample in readable if sample.free_percent is not None]
        return {
            "samples": len(self.samples),
            "readable": True,
            "duration_s": round(last.at - first.at, 1),
            "wired_start_bytes": first.wired_bytes,
            "wired_peak_bytes": max(sample.wired_bytes for sample in readable),
            "free_percent_min": min(frees) if frees else None,
            "swapins": last.swapins - first.swapins,
            "swapouts": last.swapouts - first.swapouts,
            "swapout_mb_per_minute": round(
                (last.swapouts - first.swapouts) * last.page_bytes / 1e6 / minutes, 2
            ),
            "swapin_mb_per_minute": round(
                (last.swapins - first.swapins) * last.page_bytes / 1e6 / minutes, 2
            ),
            "residency": self._residency(),
            # Seconds, wired GB, free %, swap-ins and swap-outs since the first reading: a
            # burst on load and a sustained thrash read alike in a rate, never in this.
            "timeline": [
                [
                    round(sample.at - first.at, 1),
                    round(sample.wired_bytes / GB, 3),
                    sample.free_percent,
                    sample.swapins - first.swapins,
                    sample.swapouts - first.swapouts,
                ]
                for sample in readable
            ],
        }

    def _residency(self) -> dict[str, dict[str, Any]]:
        """Per runner: every model seen resident, how often it could not be read, and how
        many times what was resident changed between two readings."""
        out: dict[str, dict[str, Any]] = {}
        for label, readings in self.residency.items():
            seen = [reading for reading in readings if reading is not None]
            changes = sum(1 for before, after in itertools.pairwise(seen) if before != after)
            out[label] = {
                "models": sorted({name for reading in seen for name, _, _ in reading}),
                "unreadable": len(readings) - len(seen),
                "changes": changes,
                "last": [list(item) for item in seen[-1]] if seen else None,
            }
        return out


# ---------------------------------------------------------------------------------------
# The runner being swept
# ---------------------------------------------------------------------------------------


class SpawnedOllamaServer(SlotServerInterface):
    """An `ollama serve` of its own, on its own port, restarted at each concurrency.

    Calibrating beside the production runner rather than restarting it keeps the production
    runner's process, settings and version exactly as they were: restoring is stopping this
    one. It is refused while the production runner has a model resident (`SlotSweep`
    checks), because two resident models bidding for one accelerator is the contention 8.c
    forbids and a measurement of it would be a measurement of the wrong thing. It starts
    with `OLLAMA_NOPRUNE` set, so it never prunes the shared model store, and with only the
    `OLLAMA_*` settings it is given plus the handful of variables a process needs to run --
    never the caller's whole environment.
    """

    _KEPT_ENV = ("HOME", "PATH", "TMPDIR", "USER", "LANG", "LC_ALL", "OLLAMA_MODELS")

    def __init__(
        self,
        binary: str,
        log_dir: Path,
        *,
        host: str = "127.0.0.1",
        port: int = DEFAULT_CALIBRATION_PORT,
        settings: Mapping[str, str] | None = None,
        environ: Mapping[str, str] | None = None,
        ready_timeout_s: float = 120.0,
        popen: Callable[..., Any] = subprocess.Popen,
        client_factory: Callable[[str], OllamaClientInterface] = OllamaClient,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        reader: TextFileReaderInterface | None = None,
    ) -> None:
        self._binary = binary
        self._log_dir = log_dir
        self.base_url = f"http://{host}:{port}"
        self._host_port = f"{host}:{port}"
        self._settings = dict(settings or {})
        self._environ = os.environ if environ is None else environ
        self._ready_timeout_s = ready_timeout_s
        self._popen = popen
        self._client_factory = client_factory
        self._sleep = sleep
        self._clock = clock
        self._reader: TextFileReaderInterface = reader or TextFileReader()
        self._process: Any = None
        self._log_path: Path | None = None

    def settings(self, parallel: int) -> dict[str, str]:
        """The `OLLAMA_*` settings a start at `parallel` slots uses -- recorded as evidence."""
        return {
            "OLLAMA_MAX_LOADED_MODELS": "1",
            "OLLAMA_KEEP_ALIVE": "30m",
            **self._settings,
            "OLLAMA_HOST": self._host_port,
            "OLLAMA_NUM_PARALLEL": str(parallel),
            "OLLAMA_NOPRUNE": "true",
        }

    def start(self, parallel: int) -> OllamaClientInterface:
        self.stop()
        client = self._client_factory(self.base_url)
        if client.version():
            raise RuntimeError(
                f"something already answers at {self.base_url}; a calibration will not share a"
                " port with another runner"
            )
        env = {key: self._environ[key] for key in self._KEPT_ENV if key in self._environ}
        env.update(self.settings(parallel))
        self._log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        self._log_path = self._log_dir / f"serve-{stamp}-p{parallel}.log"
        with self._log_path.open("ab") as log:
            self._process = self._popen(
                [self._binary, "serve"],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        deadline = self._clock() + self._ready_timeout_s
        while self._clock() < deadline:
            if client.version():
                return client
            if self._process.poll() is not None:
                break
            self._sleep(0.5)
        tail = (self._reader.read(str(self._log_path)) or "")[-2000:]
        self.stop()
        raise RuntimeError(f"the calibration runner did not answer at {self.base_url}:\n{tail}")

    def stop(self) -> None:
        process, self._process = self._process, None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=30)

    #: What the runner's own log says. llama-server names its slots and each slot's context;
    #: the rest are counted so a step can subtract what was true before it began.
    _SLOTS = re.compile(r"n_slots = (\d+), n_ctx_slot = (\d+)")
    _KV = re.compile(r"creating\s+(non-SWA|SWA) KV cache, size = (\d+) cells")
    _MIB = re.compile(r"^.*\b(?:KV|kv|compute buffer|model buffer)\b.*\bMiB\b.*$", re.MULTILINE)
    _LOAD = re.compile(r"loading model via|msg=\"starting runner\"")
    #: llama-server prints `truncated = 0` on every release; only a non-zero count, or a
    #: message saying the input was cut, is a truncation.
    _TRUNCATE = re.compile(
        r"truncated = [1-9]|truncating input|input (?:was )?truncated", re.IGNORECASE
    )
    _SHIFT = re.compile(r"context shift|n_discard|shifting context", re.IGNORECASE)
    _OVERFLOW = re.compile(r"exceeds the available context size")
    _DEVICE_FAILURE = re.compile(r"command buffer \d+ failed|failed to decode|decode\(\) failed")

    def log_facts(self) -> dict[str, Any]:
        text = self._reader.read(str(self._log_path)) if self._log_path else None
        if text is None:
            return {"readable": False}
        slots = self._SLOTS.findall(text)
        return {
            "readable": True,
            "log": str(self._log_path),
            "n_slots": int(slots[-1][0]) if slots else None,
            "n_ctx_slot": int(slots[-1][1]) if slots else None,
            "kv_cells": {kind: int(cells) for kind, cells in self._KV.findall(text)},
            "buffers": [line.strip()[-160:] for line in self._MIB.findall(text)][-8:],
            "loads": len(self._LOAD.findall(text)),
            "truncations": len(self._TRUNCATE.findall(text)),
            "shifts": len(self._SHIFT.findall(text)),
            "overflows": len(self._OVERFLOW.findall(text)),
            "device_failures": len(self._DEVICE_FAILURE.findall(text)),
        }


# ---------------------------------------------------------------------------------------
# The replay
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TurnOutcome:
    """What one replayed turn did."""

    segment: int
    turn_id: str
    worker: int
    started_s: float
    ended_s: float
    status: int
    error: str
    done_reason: str
    prompt_tokens: int
    output_tokens: int
    prompt_ms: float
    output_ms: float
    recorded_input_tokens: int
    first_in_segment: bool
    signature: str
    exact: str

    @property
    def ok(self) -> bool:
        return self.status == 200 and not self.error

    @property
    def wall_s(self) -> float:
        return self.ended_s - self.started_s

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "wall_s": round(self.wall_s, 3)}


class AnswerShape:
    """How two answers to the same turn are compared (8.j: fidelity in the same breath).

    `structure` is what an agent loop acts on -- which tools were called, in order, with
    which argument names -- or, for a plain-text answer, that it was text. `exact` is the
    whole answer, content and arguments, hashed. How often one slot agrees with itself, run
    twice, is the baseline every other concurrency is held to.
    """

    @staticmethod
    def of(message: Mapping[str, Any]) -> tuple[str, str]:
        calls = []
        for call in message.get("tool_calls") or []:
            function = call.get("function", {}) if isinstance(call, dict) else {}
            arguments = function.get("arguments", {})
            name = str(function.get("name", ""))
            calls.append((name, arguments if isinstance(arguments, dict) else {}))
        content = str(message.get("content", "") or "")
        if calls:
            structure = "tools:" + ";".join(
                f"{name}({','.join(sorted(args))})" for name, args in calls
            )
        else:
            structure = "text:fenced" if "```" in content else "text"
        exact = hashlib.sha256(
            json.dumps({"content": content, "calls": calls}, sort_keys=True).encode()
        ).hexdigest()[:16]
        return structure, exact


class TurnReplayer(TurnReplayerInterface):
    """Replays segments with `workers` closed-loop workers: each takes the next segment and
    sends its turns in order, so a worker keeps its own prefix warm exactly as one lane
    does, and N workers are N lanes contending for the runner."""

    def __init__(
        self,
        client: OllamaClientInterface,
        model: str,
        *,
        num_ctx: int,
        num_predict: int = 768,
        seed: int = 42,
        temperature: float = 0.0,
        keep_alive: str = "30m",
        timeout_s: float = 900.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._model = model
        self._num_ctx = num_ctx
        self._num_predict = num_predict
        self._seed = seed
        self._temperature = temperature
        self._keep_alive = keep_alive
        self._timeout_s = timeout_s
        self._clock = clock

    def body(
        self, messages: Sequence[Any], tools: Sequence[Any], num_predict: int
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self._model,
            "messages": list(messages),
            "stream": False,
            # Refuse, never silently cut: Ollama otherwise drops the FRONT of an oversized
            # prompt to about half the window and answers as if nothing happened.
            "truncate": False,
            "shift": False,
            "keep_alive": self._keep_alive,
            "options": {
                "temperature": self._temperature,
                "seed": self._seed,
                "num_ctx": self._num_ctx,
                "num_predict": num_predict,
            },
        }
        if tools:
            body["tools"] = list(tools)
        return body

    def warm(self) -> TurnOutcome:
        """Load the model at this context before anything is timed."""
        turn = {"id": "warm", "messages": [{"role": "user", "content": "Reply: ready"}]}
        return self._turn(-1, {"turns": [turn]}, turn, 0, 0.0, first=True, num_predict=8)

    def run(self, segments: Sequence[Any], workers: int) -> list[TurnOutcome]:
        work: queue.SimpleQueue[tuple[int, Any]] = queue.SimpleQueue()
        for index, segment in enumerate(segments):
            work.put((index, segment))
        results: list[TurnOutcome] = []
        lock = threading.Lock()
        origin = self._clock()

        def worker(number: int) -> None:
            while True:
                try:
                    index, segment = work.get_nowait()
                except queue.Empty:
                    return
                for position, turn in enumerate(segment["turns"]):
                    outcome = self._turn(index, segment, turn, number, origin, first=position == 0)
                    with lock:
                        results.append(outcome)

        threads = [threading.Thread(target=worker, args=(n,), daemon=True) for n in range(workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return sorted(results, key=lambda outcome: (outcome.started_s, outcome.turn_id))

    def _turn(
        self,
        index: int,
        segment: Mapping[str, Any],
        turn: Mapping[str, Any],
        worker: int,
        origin: float,
        *,
        first: bool,
        num_predict: int | None = None,
    ) -> TurnOutcome:
        body = self.body(
            turn["messages"], segment.get("tools") or [], num_predict or self._num_predict
        )
        started = self._clock() - origin
        status, data = self._client.chat(body, self._timeout_s)
        ended = self._clock() - origin
        error = "" if status == 200 else str(data.get("error", "") or f"status {status}")
        if not error and not data.get("done_reason"):
            # Measured, not supposed: Ollama answers HTTP 200 with no done_reason and no
            # output when llama-server's decode fails underneath it (a Metal command buffer
            # out of memory, say). A status is not an answer; this is a failed turn.
            error = "the runner answered 200 without finishing (no done_reason): a silent failure"
        structure, exact = AnswerShape.of(data.get("message") or {}) if not error else ("", "")
        return TurnOutcome(
            segment=index,
            turn_id=str(turn.get("id", "")),
            worker=worker,
            started_s=round(started, 3),
            ended_s=round(ended, 3),
            status=status,
            error=error[:300],
            done_reason=str(data.get("done_reason", "")),
            prompt_tokens=int(data.get("prompt_eval_count", 0) or 0),
            output_tokens=int(data.get("eval_count", 0) or 0),
            prompt_ms=round(int(data.get("prompt_eval_duration", 0) or 0) / 1e6, 1),
            output_ms=round(int(data.get("eval_duration", 0) or 0) / 1e6, 1),
            recorded_input_tokens=int(turn.get("recorded_input_tokens", 0) or 0),
            first_in_segment=first,
            signature=structure,
            exact=exact,
        )


# ---------------------------------------------------------------------------------------
# The corpus
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolRun:
    """One agent run in a turn pool, rebuilt the way the loop built its transcript.

    Each turn may carry `before` (messages the loop appended during that turn, ahead of the
    call that answered -- a retry prompt, say) and `after` (what it appended once the answer
    came: the assistant message, tool results, a continue prompt). Turn k's payload is the
    preamble, then `before` and `after` of every earlier turn, then its own `before`. A turn
    whose loop trimmed its history carries its whole payload as `messages` instead, because
    no sum of appendices reproduces a deletion.
    """

    run: str
    source: str
    tools: list[Any]
    preamble: list[Any]
    turns: list[dict[str, Any]]
    notes: tuple[str, ...] = ()

    def payload(self, index: int) -> list[Any]:
        if "messages" in self.turns[index]:
            return list(self.turns[index]["messages"])
        messages = list(self.preamble)
        for turn in self.turns[:index]:
            messages.extend(turn.get("before", []))
            messages.extend(turn.get("after", []))
        messages.extend(self.turns[index].get("before", []))
        return messages


class TurnPool:
    """Reads a turn pool: JSON lines, one `PoolRun` each (schema `vibey-gh/turn-pool/1`)."""

    @staticmethod
    def load(path: Path) -> tuple[list[PoolRun], str]:
        raw = path.read_bytes()
        runs = []
        for number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            data = json.loads(line)
            if data.get("schema") != POOL_SCHEMA:
                raise ValueError(f"{path}:{number} is not a {POOL_SCHEMA} line")
            runs.append(
                PoolRun(
                    run=str(data["run"]),
                    source=str(data.get("source", "")),
                    tools=list(data.get("tools", [])),
                    preamble=list(data["preamble"]),
                    turns=list(data["turns"]),
                    notes=tuple(str(note) for note in data.get("notes", [])),
                )
            )
        return runs, hashlib.sha256(raw).hexdigest()


class CorpusSampler(CorpusSamplerInterface):
    """Stratified, seeded, contiguous: the corpus a sweep replays.

    Strata are prompt depth at a segment's first turn (the recorded input tokens). Segments
    are allocated to strata in proportion to how many turns of the pool fall in each, by
    largest remainder, with at least `min_per_stratum` in every stratum that has any -- so
    the deep tail is always present, and how far the sample over-represents it is stated
    beside the population it was drawn from. Distinct runs are preferred within a stratum.
    """

    def __init__(
        self,
        *,
        segments: int,
        segment_length: int,
        strata: Sequence[int],
        min_per_stratum: int = 1,
        seed: int = 0,
    ) -> None:
        if segments < 1 or segment_length < 1:
            raise ValueError("segments and segment_length must be at least 1")
        self._segments = segments
        self._length = segment_length
        self._edges = sorted(strata)
        self._minimum = min_per_stratum
        self._seed = seed

    def label(self, tokens: int) -> str:
        lower = 0
        for edge in self._edges:
            if tokens < edge:
                return f"{lower}-{edge - 1}"
            lower = edge
        return f">={lower}"

    def labels(self) -> list[str]:
        bounds = [0, *self._edges]
        return [f"{a}-{b - 1}" for a, b in itertools.pairwise(bounds)] + [f">={bounds[-1]}"]

    def allocate(
        self, population: Mapping[str, int], available: Mapping[str, int]
    ) -> dict[str, int]:
        total = sum(population.values())
        labels = [label for label in self.labels() if available.get(label, 0)]
        if not labels or not total:
            return {}
        quotas = {label: self._segments * population.get(label, 0) / total for label in labels}
        counts = {label: int(quotas[label]) for label in labels}
        by_remainder = sorted(labels, key=lambda label: quotas[label] - counts[label], reverse=True)
        for label in by_remainder[: self._segments - sum(counts.values())]:
            counts[label] += 1
        for label in labels:
            counts[label] = max(counts[label], min(self._minimum, available[label]))
        while sum(counts.values()) > self._segments:
            over = [label for label in labels if counts[label] > self._minimum]
            if not over:
                break
            counts[max(over, key=lambda label: counts[label])] -= 1
        return {label: min(count, available[label]) for label, count in counts.items()}

    @staticmethod
    def _distinct_first(pool: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Candidates from runs not yet drawn first, then the rest, each in pool order."""
        used: set[int] = set()
        first: list[tuple[int, int]] = []
        rest: list[tuple[int, int]] = []
        for item in pool:
            (rest if item[0] in used else first).append(item)
            used.add(item[0])
        return first + rest

    def sample(self, runs: Sequence[PoolRun]) -> dict[str, Any]:
        population: Counter[str] = Counter()
        candidates: dict[str, list[tuple[int, int]]] = {}
        depths: list[int] = []
        for number, run in enumerate(runs):
            for index, turn in enumerate(run.turns):
                depth = int(turn.get("recorded_input_tokens", 0))
                depths.append(depth)
                label = self.label(depth)
                population[label] += 1
                if index + self._length <= len(run.turns):
                    candidates.setdefault(label, []).append((number, index))
        allocation = self.allocate(population, {k: len(v) for k, v in candidates.items()})
        rng = random.Random(self._seed)
        chosen: list[tuple[str, int, int]] = []
        for label in self.labels():
            pool = list(candidates.get(label, []))
            rng.shuffle(pool)
            picks = self._distinct_first(pool)[: allocation.get(label, 0)]
            chosen.extend((label, number, index) for number, index in picks)
        tools: dict[str, list[Any]] = {}
        segments = []
        for label, number, index in chosen:
            run = runs[number]
            ref = hashlib.sha256(json.dumps(run.tools, sort_keys=True).encode()).hexdigest()[:12]
            tools.setdefault(ref, run.tools)
            segments.append(
                {
                    "run": run.run,
                    "source": run.source,
                    "stratum": label,
                    "start_turn": int(run.turns[index].get("turn", index + 1)),
                    "tools_ref": ref,
                    "turns": [self._turn(run, k) for k in range(index, index + self._length)],
                }
            )
        total = len(depths)
        body = json.dumps(segments, sort_keys=True).encode()
        return {
            "schema": CORPUS_SCHEMA,
            "seed": self._seed,
            "segment_length": self._length,
            "strata": self._edges,
            "population": {"runs": len(runs), "turns": total, "by_stratum": dict(population)},
            "share_at_or_over": {
                str(edge): round(sum(d >= edge for d in depths) / total, 4) if total else 0.0
                for edge in self._edges
            },
            "allocation": allocation,
            "notes": sorted({note for run in runs for note in run.notes}),
            "tools": tools,
            "segments": segments,
            "sha256": hashlib.sha256(body).hexdigest(),
        }

    @staticmethod
    def _turn(run: PoolRun, k: int) -> dict[str, Any]:
        turn = run.turns[k]
        number = int(turn.get("turn", k + 1))
        return {
            "id": f"{run.run}#{number}",
            "turn": number,
            "recorded_input_tokens": int(turn.get("recorded_input_tokens", 0)),
            "recorded_output_tokens": int(turn.get("recorded_output_tokens", 0)),
            "messages": run.payload(k),
        }

    @staticmethod
    def resolve(corpus: Mapping[str, Any]) -> list[dict[str, Any]]:
        """The corpus's segments with each one's tool list inlined, as a replayer takes them."""
        tools = corpus.get("tools", {})
        return [
            {**segment, "tools": tools.get(segment.get("tools_ref"), [])}
            for segment in corpus["segments"]
        ]


# ---------------------------------------------------------------------------------------
# The sweep
# ---------------------------------------------------------------------------------------


class StepSummary:
    """Turns one step's outcomes and readings into the numbers the verdict reads."""

    @staticmethod
    def percentile(values: Sequence[float], share: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        rank = share * (len(ordered) - 1)
        low = int(rank)
        high = min(low + 1, len(ordered) - 1)
        return round(ordered[low] + (ordered[high] - ordered[low]) * (rank - low), 2)

    @staticmethod
    def error_kind(status: int) -> str:
        """A failed turn, named by what the runner did: refused it, never answered, or other."""
        if status == 400:
            return "refused (400)"
        if status == 0:
            return "no answer"
        return f"status {status}"

    @classmethod
    def build(
        cls,
        parallel: int,
        num_ctx: int,
        outcomes: Sequence[TurnOutcome],
        memory: Mapping[str, Any],
        facts_before: Mapping[str, Any],
        facts_after: Mapping[str, Any],
        settings: Mapping[str, str],
    ) -> dict[str, Any]:
        ok = [outcome for outcome in outcomes if outcome.ok]
        wall = max((o.ended_s for o in outcomes), default=0.0) - min(
            (o.started_s for o in outcomes), default=0.0
        )
        per_worker_end: dict[int, float] = {}
        for outcome in outcomes:
            per_worker_end[outcome.worker] = max(
                per_worker_end.get(outcome.worker, 0.0), outcome.ended_s
            )
        busy_end = min(per_worker_end.values()) if len(per_worker_end) == parallel else wall
        busy_ok = [o for o in ok if o.ended_s <= busy_end]
        errors = Counter(cls.error_kind(o.status) for o in outcomes if not o.ok)

        def delta(key: str) -> int:
            return int(facts_after.get(key, 0) or 0) - int(facts_before.get(key, 0) or 0)

        def rate(count: float, seconds: float, scale: float = 1.0) -> float:
            return round(count / seconds * scale, 2) if seconds > 0 else 0.0

        return {
            "parallel": parallel,
            "num_ctx": num_ctx,
            "settings": dict(settings),
            "turns": len(outcomes),
            "ok": len(ok),
            "errors": dict(errors),
            "done_reasons": dict(Counter(o.done_reason for o in ok)),
            "wall_s": round(wall, 1),
            "throughput_turns_per_hour": rate(len(ok), wall, 3600),
            "busy_window_s": round(busy_end, 1),
            "busy_throughput_turns_per_hour": rate(len(busy_ok), busy_end, 3600),
            "output_tokens_per_s": rate(sum(o.output_tokens for o in ok), wall),
            "prompt_tokens_per_s": rate(sum(o.prompt_tokens for o in ok), wall),
            "latency_p50_s": cls.percentile([o.wall_s for o in ok], 0.50),
            "latency_p95_s": cls.percentile([o.wall_s for o in ok], 0.95),
            "cold_latency_p50_s": cls.percentile(
                [o.wall_s for o in ok if o.first_in_segment], 0.50
            ),
            # How much of each recorded prompt the replay carried: the corpus's own
            # fidelity, measured by the runner's token count rather than estimated.
            "prompt_vs_recorded_p50": cls.percentile(
                [o.prompt_tokens / o.recorded_input_tokens for o in ok if o.recorded_input_tokens],
                0.50,
            ),
            "memory": dict(memory),
            "server": {
                "n_slots": facts_after.get("n_slots"),
                "n_ctx_slot": facts_after.get("n_ctx_slot"),
                "kv_cells": facts_after.get("kv_cells"),
                "buffers": facts_after.get("buffers"),
                "log_readable": bool(facts_after.get("readable")),
                "loads_during": delta("loads"),
                "truncations_during": delta("truncations"),
                "shifts_during": delta("shifts"),
                "overflows_during": delta("overflows"),
                "device_failures_during": delta("device_failures"),
            },
            "outcomes": [outcome.as_dict() for outcome in outcomes],
        }

    @staticmethod
    def agreement(step: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
        """How often this step's answers match the baseline's, turn by turn."""
        base = {o["turn_id"]: o for o in baseline.get("outcomes", []) if not o["error"]}
        both = [
            (o, base[o["turn_id"]])
            for o in step.get("outcomes", [])
            if not o["error"] and o["turn_id"] in base
        ]
        if not both:
            return {"compared": 0, "structural": None, "exact": None}
        return {
            "compared": len(both),
            "structural": round(
                sum(a["signature"] == b["signature"] for a, b in both) / len(both), 4
            ),
            "exact": round(sum(a["exact"] == b["exact"] for a, b in both) / len(both), 4),
        }


class SlotVerdict(SlotVerdictInterface):
    """The bounds, applied. Pure: the same evidence and bounds always give the same answer,
    which is what lets the gate re-judge old evidence against today's declaration."""

    def __init__(self, bounds: SlotBounds) -> None:
        self.bounds = bounds

    def pressure(
        self, step: Mapping[str, Any], first: Mapping[str, Any], memory_bytes: int
    ) -> list[str]:
        """The memory bounds: wired over the ceiling, and swap-outs rising.

        At one slot these are reported, never refusing: one run at a time is 8.c's floor and
        the reference every other step is measured against, so a machine that already
        strains at one learns that loudly, and still runs one.
        """
        b = self.bounds
        memory = step.get("memory", {})
        found: list[str] = []
        ceiling = b.wired_ceiling_fraction * memory_bytes
        peak = int(memory.get("wired_peak_bytes", 0) or 0)
        if memory_bytes and peak > ceiling:
            found.append(
                f"wired memory peaked at {peak / GB:.2f} GB, over the {ceiling / GB:.2f} GB ceiling"
            )
        base_rate = float(first.get("memory", {}).get("swapout_mb_per_minute", 0.0) or 0.0)
        allowance = (
            b.swap_floor_mb_per_minute
            if step is first
            else max(base_rate * b.swap_growth_factor, b.swap_floor_mb_per_minute)
        )
        rate = float(memory.get("swapout_mb_per_minute", 0.0) or 0.0)
        if rate > allowance:
            found.append(
                f"swap-outs ran at {rate} MB/min, over the {round(allowance, 2)} MB/min allowance"
            )
        return found

    def breaches(
        self,
        step: Mapping[str, Any],
        first: Mapping[str, Any],
        memory_bytes: int,
        baseline_fidelity: float,
    ) -> list[str]:
        b = self.bounds
        memory = step.get("memory", {})
        server = step.get("server", {})
        found: list[str] = []
        if not memory.get("readable"):
            found.append("the host's memory could not be read, so the wired bound is unmeasured")
        if step is not first:
            found.extend(self.pressure(step, first, memory_bytes))
            fit_first = {o["turn_id"] for o in first.get("outcomes", []) if not o["error"]}
            lost = [
                o["turn_id"]
                for o in step.get("outcomes", [])
                if o["error"] and o["turn_id"] in fit_first
            ]
            if lost:
                found.append(
                    f"{len(lost)} turn(s) that ran at one slot failed here: {', '.join(lost[:5])}"
                )
            fidelity = step.get("fidelity", {}).get("structural")
            floor = baseline_fidelity - b.fidelity_tolerance
            if fidelity is None or fidelity < floor:
                found.append(f"structural fidelity {fidelity} is below {round(floor, 4)}")
        odd = {
            reason: n
            for reason, n in step.get("done_reasons", {}).items()
            if reason not in ("stop", "length")
        }
        if odd:
            found.append(f"answers ended for reasons other than stop or length: {odd}")
        for key, words in (
            ("truncations_during", "truncation"),
            ("shifts_during", "context shift"),
            ("device_failures_during", "device failure"),
        ):
            if server.get(key):
                found.append(f"the runner logged {server[key]} {words} line(s) during the step")
        calibration = memory.get("residency", {}).get("calibration", {})
        if server.get("loads_during") or calibration.get("changes"):
            found.append(
                f"the model was loaded or evicted during the step ({server.get('loads_during', 0)}"
                f" load(s), {calibration.get('changes', 0)} residency change(s))"
            )
        foreign = memory.get("residency", {}).get("production", {}).get("models")
        if foreign:
            found.append(
                f"another runner held {foreign} resident during the step; the reading is contaminated"
            )
        return found

    def judge(self, evidence: Mapping[str, Any]) -> dict[str, Any]:
        steps = sorted(evidence.get("steps", []), key=lambda step: step["parallel"])
        memory_bytes = int(evidence.get("fingerprint", {}).get("memory_bytes", 0) or 0)
        baseline_fidelity = float(evidence.get("self_consistency", {}).get("structural") or 1.0)
        judged: list[dict[str, Any]] = []
        best = 0.0
        flat = 0
        stop = ""
        for step in steps:
            found = self.breaches(step, steps[0], memory_bytes, baseline_fidelity)
            warnings = self.pressure(step, steps[0], memory_bytes) if step is steps[0] else []
            throughput = float(step.get("throughput_turns_per_hour", 0.0))
            improves = not found and throughput >= best * (1 + self.bounds.min_throughput_gain)
            judged.append(
                {
                    "parallel": step["parallel"],
                    "within_bounds": not found,
                    "breaches": found,
                    "floor_warnings": warnings,
                    "throughput_turns_per_hour": throughput,
                    "improves": improves,
                }
            )
            if found:
                stop = f"a bound broke at {step['parallel']}: {found[0]}"
                break
            flat = 0 if improves else flat + 1
            best = max(best, throughput)
            if flat >= 2:
                stop = (
                    f"throughput stopped improving: {flat} steps without a"
                    f" {self.bounds.min_throughput_gain:.0%} gain"
                )
                break
        inside = [j for j in judged if j["within_bounds"]]
        top = max((j["throughput_turns_per_hour"] for j in inside), default=0.0)
        gain = 1 + self.bounds.min_throughput_gain
        ideal = min(
            (j["parallel"] for j in inside if j["throughput_turns_per_hour"] * gain >= top),
            default=1,
        )
        return {"bounds": self.bounds.as_dict(), "steps": judged, "stop": stop, "ideal": ideal}


class SweepCheckpoint(SweepCheckpointInterface):
    """Each completed step of one sweep, on disk the moment it finishes.

    A sweep is keyed by everything that makes two sweeps the same measurement -- the device
    fingerprint, the corpus hash and the replay method -- so a restart after a reboot takes
    the steps already measured for exactly this sweep, and a changed device, corpus or
    method starts clean rather than mixing readings that describe different things.
    """

    def __init__(self, directory: Path, identity: Mapping[str, Any]) -> None:
        canonical = json.dumps(dict(identity), sort_keys=True, separators=(",", ":"))
        self.key = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        self.directory = directory / self.key
        self._identity = dict(identity)

    def _path(self, label: str) -> Path:
        return self.directory / f"step-{re.sub(r'[^A-Za-z0-9@_.-]', '_', label)}.json"

    def load(self, label: str) -> dict[str, Any] | None:
        try:
            data = json.loads(self._path(label).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict) or data.get("identity") != self._identity:
            return None
        return dict(data["step"])

    def save(self, label: str, step: Mapping[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path(label)
        partial = target.with_suffix(".partial")
        document = {"identity": self._identity, "label": label, "step": dict(step)}
        partial.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
        partial.replace(target)


class SlotSweep:
    """Measures N = 1, 2, 3, ... and stops where the verdict says to.

    One slot is measured twice when `repeat_baseline` is set, so fidelity is judged against
    what the model does when nothing about the run changes -- a batched floating-point
    answer need not be bit-identical, and a bound that assumed it would be refuses N=2 for a
    difference N=1 has too. The runner is stopped after every step and, whatever happens,
    once more at the end. With a `checkpoint`, every completed step is kept at once and a
    step already kept for this very sweep is taken rather than measured again; `on_step`
    hears the record after each one, so a caller can publish partial evidence as it goes.
    """

    def __init__(
        self,
        server: SlotServerInterface,
        sampler: HostMemorySamplerInterface,
        verdict: SlotVerdictInterface,
        replayer: Callable[[OllamaClientInterface, int], Any],
        *,
        production: OllamaClientInterface | None = None,
        max_runs: int = 8,
        repeat_baseline: bool = True,
        extras: Sequence[tuple[int, int]] = (),
        interval_s: float = 1.0,
        log: Callable[[str], None] = lambda line: None,
        settings: Callable[[int], Mapping[str, str]] = lambda parallel: {},
        watch: Callable[..., MemoryWatch] = MemoryWatch,
        idle: Callable[[], bool] | None = None,
        retries: int = 2,
        checkpoint: SweepCheckpointInterface | None = None,
        on_step: Callable[[Mapping[str, Any]], None] = lambda record: None,
    ) -> None:
        self._server = server
        self._sampler = sampler
        self._verdict = verdict
        self._replayer = replayer
        self._production = production
        self._max_runs = max_runs
        self._repeat = repeat_baseline
        self._extras = list(extras)
        self._interval_s = interval_s
        self._log = log
        self._settings = settings
        self._watch = watch
        self._idle = idle
        self._retries = retries
        self._checkpoint = checkpoint
        self._on_step = on_step

    @staticmethod
    def _reading(sample: HostSample) -> dict[str, Any]:
        return {"wired_bytes": sample.wired_bytes, "free_percent": sample.free_percent}

    def measure(self, parallel: int, num_ctx: int, segments: Sequence[Any]) -> dict[str, Any]:
        rest = self._sampler.sample()
        client = self._server.start(parallel)
        try:
            runtime = client.version()
            replayer = self._replayer(client, num_ctx)
            warm = replayer.warm()
            if not warm.ok:
                raise RuntimeError(
                    f"the model did not load at {parallel} slot(s), context {num_ctx}: {warm.error}"
                )
            loaded = self._sampler.sample()
            before = self._server.log_facts()
            clients = {"calibration": client}
            if self._production is not None:
                clients["production"] = self._production
            watch = self._watch(self._sampler, clients, interval_s=self._interval_s)
            with watch:
                outcomes = replayer.run(segments, parallel)
            after = self._server.log_facts()
        finally:
            self._server.stop()
        step = StepSummary.build(
            parallel, num_ctx, outcomes, watch.summary(), before, after, self._settings(parallel)
        )
        step["runtime"] = f"ollama {runtime}" if runtime else ""
        step["memory_at_rest"] = self._reading(rest)
        step["memory_loaded"] = self._reading(loaded)
        self._log(
            f"N={parallel} ctx={num_ctx}: {step['ok']}/{step['turns']} ok,"
            f" {step['throughput_turns_per_hour']} turns/h, p50 {step['latency_p50_s']}s,"
            f" p95 {step['latency_p95_s']}s, peak wired"
            f" {round((step['memory'].get('wired_peak_bytes') or 0) / GB, 2)} GB,"
            f" errors {step['errors']}"
        )
        return step

    def clean(
        self, label: str, parallel: int, num_ctx: int, segments: Sequence[Any]
    ) -> dict[str, Any]:
        """A step measured while the production runner held nothing resident, or the step
        this very sweep already kept under `label`.

        A model loaded on the production runner mid-step is a second model bidding for the
        same memory and accelerator -- measured on 2026-09-24 as Metal command-buffer
        failures in the calibration runner seconds after another client loaded one. That
        reading describes the contention, not the device, so it is discarded: the sweep waits
        for production to idle and measures the step again, up to `retries` times, and marks
        the step `contaminated` when it never gets a clean reading.
        """
        kept = self._checkpoint.load(label) if self._checkpoint is not None else None
        if kept is not None:
            self._log(f"{label}: taken from the checkpoint, not measured again")
            return kept
        discarded = 0
        while True:
            step = self.measure(parallel, num_ctx, segments)
            foreign = step["memory"].get("residency", {}).get("production", {}).get("models")
            if not foreign:
                break
            discarded += 1
            self._log(f"{label}: the production runner held {foreign} resident; reading discarded")
            if discarded > self._retries or self._idle is None or not self._idle():
                step["contaminated"] = True
                break
        step["discarded_attempts"] = discarded
        if self._checkpoint is not None and not step.get("contaminated"):
            self._checkpoint.save(label, step)
        return step

    def run(
        self, segments: Sequence[Any], context_window: int, fingerprint: Mapping[str, Any]
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "fingerprint": dict(fingerprint),
            "steps": [],
            "extras": [],
            "contaminated": False,
        }
        try:
            for parallel in range(1, self._max_runs + 1):
                step = self.clean(str(parallel), parallel, context_window, segments)
                if parallel == 1 and self._repeat and not step.get("contaminated"):
                    repeat = self.clean("1-repeat", 1, context_window, segments)
                    record["baseline_repeat"] = repeat
                    record["self_consistency"] = StepSummary.agreement(repeat, step)
                    record["contaminated"] = bool(repeat.get("contaminated"))
                if parallel > 1:
                    step["fidelity"] = StepSummary.agreement(step, record["steps"][0])
                record["steps"].append(step)
                record["contaminated"] = bool(record["contaminated"] or step.get("contaminated"))
                self._on_step(record)
                if record["contaminated"]:
                    self._log(
                        "stopping: no clean reading could be taken beside the production runner"
                    )
                    break
                judgement = self._verdict.judge(record)
                if judgement["stop"]:
                    self._log(f"stopping: {judgement['stop']}")
                    break
            for parallel, num_ctx in () if record["contaminated"] else self._extras:
                extra = self.clean(f"extra-{parallel}@{num_ctx}", parallel, num_ctx, segments)
                extra["fidelity"] = StepSummary.agreement(extra, record["steps"][0])
                record["extras"].append(extra)
                record["contaminated"] = bool(record["contaminated"] or extra.get("contaminated"))
                self._on_step(record)
        finally:
            self._server.stop()
        record["judgement"] = self._verdict.judge(record)
        return record


# ---------------------------------------------------------------------------------------
# The evidence and the gate
# ---------------------------------------------------------------------------------------


class SlotEvidenceStore(SlotEvidenceStoreInterface):
    """One JSON file per device fingerprint, and a request file beside it when a
    calibration has been asked for and not yet made."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    @staticmethod
    def resolve(declared: str = "", environ: Mapping[str, str] | None = None) -> Path:
        env = os.environ if environ is None else environ
        return Path(declared or env.get(SLOTS_DIR_ENV) or DEFAULT_SLOTS_DIR).expanduser()

    def path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def read(self, key: str) -> dict[str, Any] | None:
        try:
            data = json.loads(self.path(key).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def write(self, evidence: Mapping[str, Any]) -> Path:
        key = str(evidence["fingerprint_key"])
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.path(key)
        partial = target.with_suffix(".json.partial")
        partial.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        partial.replace(target)
        (self.directory / f"{key}.request.json").unlink(missing_ok=True)
        return target

    def request(self, key: str, reason: str) -> Path:
        target = self.directory / f"{key}.request.json"
        if not target.exists():
            self.directory.mkdir(parents=True, exist_ok=True)
            document = {"key": key, "reason": reason, "requested_at": datetime.now(UTC).isoformat()}
            target.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        return target

    def requested(self, key: str) -> bool:
        return (self.directory / f"{key}.request.json").exists()


@dataclass(frozen=True)
class SlotDecision:
    """How many runs of the model may run at once here, and why."""

    runs: int
    reason: str
    recalibrate: bool = False
    refused: bool = False
    notes: tuple[str, ...] = field(default=())

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "notes": list(self.notes)}


class SlotGate(SlotGateInterface):
    """The declared value, checked against this device's evidence (8.j, 12.c).

    - `1` is always allowed: it is 8.c's floor and needs no evidence.
    - `"measured"` takes the ideal N the evidence supports, re-judged against the bounds
      declared now; no evidence, or evidence for another device, means one.
    - A number above one is refused -- one runs instead, and the refusal names what is
      missing -- unless the evidence for this device measured that number inside every
      bound and faster than one. "By measurement" is a gate, not a judgement.
    """

    def __init__(
        self,
        verdict: SlotVerdictInterface,
        *,
        max_age_days: float,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._verdict = verdict
        self._max_age_days = max_age_days
        self._now = now

    def problem(self, fingerprint: DeviceFingerprint, evidence: Mapping[str, Any] | None) -> str:
        if evidence is None:
            return f"no calibration evidence for this device (fingerprint {fingerprint.key()})"
        if (
            evidence.get("schema") != EVIDENCE_SCHEMA
            or not evidence.get("steps")
            or evidence.get("contaminated")
        ):
            return "the evidence for this device is not a complete, clean calibration"
        changed = fingerprint.differences(evidence.get("fingerprint", {}))
        if changed:
            return "the evidence is stale: " + "; ".join(changed)
        try:
            ended = datetime.fromisoformat(str(evidence.get("cutoff", {}).get("ended")))
        except ValueError:
            return "the evidence does not say when it was measured"
        age = (self._now() - ended).total_seconds() / 86400
        if age > self._max_age_days:
            return (
                f"the evidence is stale: measured {age:.0f} days ago, beyond {self._max_age_days:g}"
            )
        return ""

    def decide(self, declared: int | str, fingerprint: Any, evidence: Any) -> SlotDecision:
        if declared == 1:
            return SlotDecision(1, "[local_models] concurrent_runs = 1: one run at a time (8.c)")
        if fingerprint is None or fingerprint.missing:
            unread = ", ".join(fingerprint.missing) if fingerprint is not None else "everything"
            return SlotDecision(
                1,
                f"this device could not be fingerprinted ({unread} unread), so no evidence can be"
                " matched to it; one run at a time",
                refused=declared != MEASURED,
            )
        problem = self.problem(fingerprint, evidence)
        if problem:
            if declared == MEASURED:
                return SlotDecision(
                    1, f"{problem}; unmeasured or stale means one", recalibrate=True
                )
            return SlotDecision(
                1,
                f"concurrent_runs = {declared} refused: {problem}. Run `vibey-gh slots calibrate`"
                " on this device",
                recalibrate=True,
                refused=True,
            )
        judgement = self._verdict.judge(evidence)
        when = evidence["cutoff"]["ended"][:10]
        if declared == MEASURED:
            return SlotDecision(
                judgement["ideal"],
                f"measured on this device on {when}: {judgement['ideal']} concurrent run(s)"
                " reach the best throughput inside every bound",
            )
        steps = {step["parallel"]: step for step in judgement["steps"]}
        step = steps.get(declared) if isinstance(declared, int) else None
        one = steps.get(1, {}).get("throughput_turns_per_hour", 0.0)
        if step is None:
            reason = f"{declared} was never measured on this device (measured: {sorted(steps)})"
        elif not step["within_bounds"]:
            reason = f"{declared} broke a bound on this device: {step['breaches'][0]}"
        elif step["throughput_turns_per_hour"] < one * (
            1 + self._verdict.bounds.min_throughput_gain
        ):
            reason = f"{declared} measured no significant gain over one on this device"
        else:
            return SlotDecision(
                step["parallel"], f"{declared}: measured inside every bound on {when}"
            )
        return SlotDecision(1, f"concurrent_runs = {declared} refused: {reason}", refused=True)


class SlotReport:
    """The human summary of one calibration."""

    @staticmethod
    def bounds_cell(verdict: Mapping[str, Any] | None) -> str:
        if verdict is None:
            return "not judged"
        if not verdict["within_bounds"]:
            return "no: " + "; ".join(verdict["breaches"])
        warnings = verdict.get("floor_warnings") or []
        return "yes (floor: " + "; ".join(warnings) + ")" if warnings else "yes"

    @staticmethod
    def row(step: Mapping[str, Any], verdict: Mapping[str, Any] | None) -> str:
        fidelity = step.get("fidelity") or {}
        memory = step.get("memory", {})
        return (
            f"| {step['parallel']} | {step['num_ctx']} | {step['ok']}/{step['turns']}"
            f" | {step['throughput_turns_per_hour']} | {step['output_tokens_per_s']}"
            f" | {step['latency_p50_s']} | {step['latency_p95_s']}"
            f" | {round((memory.get('wired_peak_bytes') or 0) / GB, 2)}"
            f" | {memory.get('swapout_mb_per_minute')}"
            f" | {fidelity.get('structural', '-')}/{fidelity.get('exact', '-')}"
            f" | {SlotReport.bounds_cell(verdict)} |"
        )

    @staticmethod
    def markdown(evidence: Mapping[str, Any]) -> str:
        judgement = evidence.get("judgement", {})
        fp = evidence.get("fingerprint", {})
        cutoff = evidence.get("cutoff", {})
        corpus = evidence.get("corpus", {})
        lines = [
            f"# Slot calibration: {fp.get('model')} on {fp.get('hardware')}",
            "",
            f"- Object: {evidence.get('object')}",
            (
                f"- Fingerprint: `{evidence.get('fingerprint_key')}` -- {fp.get('processor')},"
                f" {round((fp.get('memory_bytes') or 0) / 2**30)} GiB, {fp.get('accelerator')},"
                f" {fp.get('os')}, {fp.get('runtime')}, digest {str(fp.get('model_digest'))[:12]},"
                f" context {fp.get('context_window')}"
            ),
            f"- Cutoff: {cutoff.get('started')} to {cutoff.get('ended')}",
            (
                f"- Corpus: `{str(evidence.get('source', {}).get('corpus_sha256', ''))[:16]}`,"
                f" {corpus.get('segments')} segments / {corpus.get('turns')} turns per step"
            ),
            (
                f"- Ideal concurrent runs: **{judgement.get('ideal')}** --"
                f" {judgement.get('stop') or 'the sweep reached its limit'}"
            ),
            *(
                [
                    (
                        "- **Contaminated:** another runner held a model resident and no clean"
                        " reading could be taken; this is not evidence for the device."
                    )
                ]
                if evidence.get("contaminated")
                else []
            ),
            "",
            (
                "| N | ctx/slot | ok/turns | turns/h | out tok/s | p50 s | p95 s | peak wired GB"
                " | swap-out MB/min | fidelity (struct/exact) | within bounds |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        verdicts = {j["parallel"]: j for j in judgement.get("steps", [])}
        rows: list[tuple[Mapping[str, Any], Mapping[str, Any] | None]] = [
            (s, verdicts.get(s["parallel"])) for s in evidence.get("steps", [])
        ]
        if evidence.get("baseline_repeat"):
            rows.insert(1, (evidence["baseline_repeat"], None))
        rows += [(s, None) for s in evidence.get("extras", [])]
        lines += [SlotReport.row(step, verdict) for step, verdict in rows]
        consistency = evidence.get("self_consistency")
        if consistency:
            lines += [
                "",
                (
                    f"One slot run twice agreed with itself: structural {consistency.get('structural')},"
                    f" exact {consistency.get('exact')} over {consistency.get('compared')} turns."
                ),
            ]
        for heading, key in (("Not measured", "not_measured"), ("Confidence", "confidence")):
            value = evidence.get(key)
            if value:
                lines += ["", f"## {heading}", ""]
                lines += (
                    [f"- {item}" for item in value] if isinstance(value, list) else [str(value)]
                )
        return "\n".join(lines) + "\n"


class DirectoryLock:
    """A `mkdir` lock shared with shell tooling: held while the directory exists."""

    def __init__(
        self,
        path: Path,
        *,
        poll_s: float = 20.0,
        sleep: Callable[[float], None] = time.sleep,
        log: Callable[[str], None] = lambda line: None,
    ) -> None:
        self.path = path
        self._poll_s = poll_s
        self._sleep = sleep
        self._log = log

    def __enter__(self) -> Self:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        said = False
        while True:
            try:
                self.path.mkdir()
                return self
            except FileExistsError:
                if not said:
                    self._log(f"waiting for {self.path}, held by another measurement or storm")
                    said = True
                self._sleep(self._poll_s)

    def __exit__(self, *exc: object) -> None:
        try:
            self.path.rmdir()
        except OSError:
            pass
