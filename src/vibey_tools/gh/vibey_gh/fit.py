# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The fit calculus (#263): both sides of the fit, measured continuously.

Doctrine 10's hardware-decomposition clarification says to read the specs of the
hardware the code actually runs on AND the specs of the model actually wanted on
it — fully, honestly, in detail — then decompose work until each piece fits, down
to the floor of the lowest hardware that can run that model, and beyond the floor
to fail loudly to a human rather than silently.

This module is that clarification as a running control loop rather than a one-time
preflight. It samples both sides, keeps a rolling estimate of the two constants
that govern everything, projects whether a piece of work fits a deadline, and says
`admit`, `defer`, or `floor` with the arithmetic that justifies the answer.

The constants, measured on a live machine (24 GB, qwen2.5-coder:14b at 9.7 GB):

- **s** — effective parallelism, total generation-seconds ÷ wall seconds. Measured
  at 3.1 across a six-way rung, not the 2 a naive throughput reading suggested;
  payload size, not queue depth, governed wall time.
- **τ** — service time, a *distribution* (58s–206s observed) that scales with
  payload size, so it is estimated as `base + rate × bytes` from what actually ran.

Everything else follows: `wall(N) ≈ W(N)/s`, and a job fails when its projected
wait plus service exceeds the caller's deadline.

**This module never resizes swap by itself.** It computes what headroom the
projection needs and reports it; growing paging space is an irreversible act on
someone's machine, and Article III's bounded delegation puts that in a human's
hands. `recommendation()` is the output; acting on it is the operator's call.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

from vibey_gh.interfaces.memory_sampler_interface import MemorySamplerInterface
from vibey_gh.interfaces.text_file_reader_interface import TextFileReaderInterface

__all__ = [
    "ADMIT",
    "DEFER",
    "FLOOR",
    "DarwinMemorySampler",
    "Estimate",
    "Fit",
    "LinuxMemorySampler",
    "Machine",
    "Model",
    "Observation",
    "TextFileReader",
    "decide",
    "estimate_from",
    "headroom_gb",
    "machine_sampler",
    "sample_machine",
    "sample_model",
    "saturating_wait",
]

ADMIT = "admit"
DEFER = "defer"
FLOOR = "floor"

_PAGE_KEYS = (
    "Pages free",
    "Pages active",
    "Pages inactive",
    "Pages wired down",
    "Pages occupied by compressor",
)

# Linux states its memory in files rather than in `sysctl`, and inside a container the
# host's file is the wrong answer: `/proc/meminfo` is the *host's* memory even when the
# cgroup will kill this process long before it reaches that much. So the cgroup limit is
# preferred when one exists, v2 first and v1 after it, and `/proc/meminfo` is the fallback
# for a machine that is not in a container at all. Every path is a default, not a
# constant: a caller on a machine that mounts its cgroup hierarchy elsewhere passes its
# own (ADR-0018 -- a hard-coded value that could have been a key is a decision taken away
# from the next adopter).
LINUX_MEMINFO_PATH = "/proc/meminfo"
LINUX_CGROUP_MEMORY_LIMIT_PATHS = (
    "/sys/fs/cgroup/memory.max",  # cgroup v2
    "/sys/fs/cgroup/memory/memory.limit_in_bytes",  # cgroup v1
)
LINUX_CGROUP_MEMORY_USAGE_PATHS = (
    "/sys/fs/cgroup/memory.current",
    "/sys/fs/cgroup/memory/memory.usage_in_bytes",
)
# v2 only, deliberately. v1's `memory.memsw.*` counts memory *plus* swap in one number, so
# reading it as swap would overstate the ceiling -- the one direction doctrine 10 forbids.
# A v1 container therefore reports no paging space of its own, which understates the
# ceiling and fails towards the floor rather than towards a confident wrong admission.
LINUX_CGROUP_SWAP_LIMIT_PATHS = ("/sys/fs/cgroup/memory.swap.max",)
LINUX_CGROUP_SWAP_USAGE_PATHS = ("/sys/fs/cgroup/memory.swap.current",)
_MEMINFO_KEYS = ("MemTotal", "MemAvailable", "MemFree", "SwapTotal", "SwapFree")


@dataclass(frozen=True)
class Machine:
    """The hardware side of the fit, as honestly as the machine states it."""

    total_gb: float
    free_gb: float
    swap_used_gb: float
    swap_total_gb: float
    # Whether this machine stated its own size at all. A machine that could not be read
    # reports zeros -- and zero is not a measurement, it is the absence of one. Without
    # this flag the two are indistinguishable, and an unreadable machine looks like a
    # machine with room for nothing, which is exactly the silent failure doctrine 10
    # forbids. `decide()` turns a false here into a loud FLOOR.
    readable: bool = True

    @property
    def available_gb(self) -> float:
        """What a model could actually occupy right now: free memory plus the
        paging space not already spoken for."""
        return round(self.free_gb + max(self.swap_total_gb - self.swap_used_gb, 0.0), 2)


@dataclass(frozen=True)
class Model:
    """The model side of the fit — read, never assumed."""

    name: str
    size_gb: float
    context_length: int


@dataclass(frozen=True)
class Observation:
    """One completed operation, contributing its own timing to the estimate."""

    payload_bytes: int
    elapsed_s: float
    concurrent: int


@dataclass(frozen=True)
class Estimate:
    """The two constants, plus how much evidence stands behind them."""

    slots: float
    base_s: float
    rate_s_per_kb: float
    samples: int

    def service_s(self, payload_bytes: int) -> float:
        """τ for a payload of this size."""
        return round(self.base_s + self.rate_s_per_kb * (payload_bytes / 1024), 1)


@dataclass(frozen=True)
class Fit:
    verdict: str
    reason: str
    projected_wait_s: float
    projected_service_s: float
    headroom_gb: float
    estimate: Estimate | None = None
    notes: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        return self.verdict == ADMIT


def _run(*cmd: str) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout if proc.returncode == 0 else ""


class TextFileReader(TextFileReaderInterface):
    """Reads a file the kernel writes, or says it could not be read.

    Nothing here interprets the contents; that belongs to whichever sampler asked. An
    unreadable file is `None` rather than an empty string, because "this machine has no
    such file" and "this file is empty" lead to different verdicts.
    """

    def read(self, path: str) -> str | None:
        try:
            with open(path, encoding="utf-8") as handle:
                return handle.read()
        except OSError:
            return None


class DarwinMemorySampler(MemorySamplerInterface):
    """The hardware side on macOS, read from `sysctl` and `vm_stat`.

    Unreadable fields report zero rather than a guess -- a projection built on invented
    numbers is worse than no projection -- and a machine that would not state its own
    size reports `readable=False` so the caller can fail loudly instead.
    """

    def sample(self) -> Machine:
        total_bytes = 0
        raw = _run("sysctl", "-n", "hw.memsize").strip()
        if raw.isdigit():
            total_bytes = int(raw)

        free_gb = 0.0
        stat = _run("vm_stat")
        if stat:
            page_size = 4096
            first = stat.splitlines()[0] if stat.splitlines() else ""
            for token in first.replace(")", " ").split():
                if token.isdigit():
                    page_size = int(token)
                    break
            pages: dict[str, int] = {}
            for line in stat.splitlines():
                key, _, value = line.partition(":")
                digits = value.strip().rstrip(".")
                if key.strip() in _PAGE_KEYS and digits.isdigit():
                    pages[key.strip()] = int(digits)
            free_pages = pages.get("Pages free", 0) + pages.get("Pages inactive", 0)
            free_gb = round(free_pages * page_size / 1e9, 2)

        swap_used = swap_total = 0.0
        swap = _run("sysctl", "-n", "vm.swapusage")
        for token in swap.replace("=", " ").split():
            if token.endswith("M") and token[:-1].replace(".", "", 1).isdigit():
                gb = float(token[:-1]) / 1024
                if swap_total == 0.0:
                    swap_total = round(gb, 2)
                elif swap_used == 0.0:
                    swap_used = round(gb, 2)
        return Machine(
            total_gb=round(total_bytes / 1e9, 2),
            free_gb=free_gb,
            swap_used_gb=swap_used,
            swap_total_gb=swap_total,
            readable=total_bytes > 0,
        )


class LinuxMemorySampler(MemorySamplerInterface):
    """The hardware side on Linux, read from the kernel's own files.

    `/proc/meminfo` describes the machine; inside a container it describes the *host*,
    which is the wrong machine -- the process is killed at the cgroup limit long before
    it reaches the host's total. So a cgroup limit, when one exists, wins over
    `/proc/meminfo`: v2 (`memory.max`) first, then v1 (`memory.limit_in_bytes`). A value
    of `max`, or a limit at or above what the host itself has, is not a limit at all --
    that is how both cgroup versions spell "unlimited" -- and the host's own numbers
    stand.

    When neither answers, every field is zero and `readable` is false: doctrine 10's
    floor, stated loudly, rather than a machine that silently appears to have no memory.

    Every path is injected and every read goes through `TextFileReaderInterface`, so a
    test on any platform hands this sampler exact file contents instead of patching
    module attributes (sub-doctrine 9.b).
    """

    def __init__(
        self,
        reader: TextFileReaderInterface | None = None,
        *,
        meminfo_path: str = LINUX_MEMINFO_PATH,
        cgroup_limit_paths: tuple[str, ...] = LINUX_CGROUP_MEMORY_LIMIT_PATHS,
        cgroup_usage_paths: tuple[str, ...] = LINUX_CGROUP_MEMORY_USAGE_PATHS,
        cgroup_swap_limit_paths: tuple[str, ...] = LINUX_CGROUP_SWAP_LIMIT_PATHS,
        cgroup_swap_usage_paths: tuple[str, ...] = LINUX_CGROUP_SWAP_USAGE_PATHS,
    ) -> None:
        self._reader: TextFileReaderInterface = TextFileReader() if reader is None else reader
        self._meminfo_path = meminfo_path
        self._cgroup_limit_paths = cgroup_limit_paths
        self._cgroup_usage_paths = cgroup_usage_paths
        self._cgroup_swap_limit_paths = cgroup_swap_limit_paths
        self._cgroup_swap_usage_paths = cgroup_swap_usage_paths

    def sample(self) -> Machine:
        fields = self._meminfo()
        total = fields.get("MemTotal", 0)
        # MemAvailable is the kernel's own answer to "what could a new process get?" and
        # is the right number here; MemFree, which ignores reclaimable cache, is only the
        # fallback for a kernel too old to publish it.
        free = fields.get("MemAvailable", fields.get("MemFree", 0))
        swap_total = fields.get("SwapTotal", 0)
        swap_used = max(swap_total - fields.get("SwapFree", 0), 0)

        limit = self._first_int(self._cgroup_limit_paths)
        if limit is not None and (total <= 0 or limit < total):
            usage = self._first_int(self._cgroup_usage_paths)
            if usage is None:
                # Without a usage reading the host's free memory is still a ceiling on
                # what this cgroup can be holding free, so take the smaller of the two.
                free = min(free, limit)
            else:
                free = max(limit - usage, 0)
            total = limit
            # The host's paging space is not this container's to claim.
            swap_total = self._first_int(self._cgroup_swap_limit_paths) or 0
            swap_used = min(self._first_int(self._cgroup_swap_usage_paths) or 0, swap_total)

        return Machine(
            total_gb=round(total / 1e9, 2),
            free_gb=round(free / 1e9, 2),
            swap_used_gb=round(swap_used / 1e9, 2),
            swap_total_gb=round(swap_total / 1e9, 2),
            readable=total > 0,
        )

    def _meminfo(self) -> dict[str, int]:
        """The `/proc/meminfo` keys this calculus needs, in bytes."""
        text = self._reader.read(self._meminfo_path)
        if text is None:
            return {}
        fields: dict[str, int] = {}
        for line in text.splitlines():
            key, _, rest = line.partition(":")
            name = key.strip()
            parts = rest.split()
            if name not in _MEMINFO_KEYS or not parts or not parts[0].isdigit():
                continue
            value = int(parts[0])
            if len(parts) > 1 and parts[1].lower() == "kb":
                value *= 1024
            fields[name] = value
        return fields

    def _first_int(self, paths: tuple[str, ...]) -> int | None:
        """The first of these files that holds a plain integer, or `None`.

        cgroup v2 writes `max` for "no limit", which is not an integer and so falls
        through to the next path and finally to `None` -- which is the honest answer:
        this hierarchy states no number here.
        """
        for path in paths:
            raw = self._reader.read(path)
            if raw is not None and raw.strip().isdigit():
                return int(raw.strip())
        return None


def machine_sampler(platform_name: str = "") -> MemorySamplerInterface:
    """The sampler that can actually read this machine.

    Module-level for the reason given on `sample_machine`; it is the selection itself,
    kept nameable so the choice can be asserted directly instead of inferred from a
    reading that differs on every machine the suite runs on.

    `platform_name` defaults to this interpreter's own `sys.platform`, and is a parameter
    so either sampler can be asked for from either kind of machine.
    """
    system = platform_name or sys.platform
    if system.startswith("linux"):
        return LinuxMemorySampler()
    return DarwinMemorySampler()


def sample_machine(platform_name: str = "") -> Machine:
    """Read the hardware side on whichever machine this actually is.

    Module-level, and deliberately so under ADR-0016: this name is `vibey_gh`'s published
    entry point into the fit calculus -- `cli.py` and `fitloop.py` already import it by
    name, and adopters call it -- so it stays a function and does nothing but ask the
    right sampler. Every measurement lives in a class with a declared seam.
    """
    return machine_sampler(platform_name).sample()


def sample_model(name: str, base_url: str = "http://127.0.0.1:11434") -> Model | None:
    """Read the model side from the runner itself. None when it cannot be read —
    the caller must not proceed on an assumed model (doctrine 10)."""
    curl = shutil.which("curl")
    if not curl:
        return None
    body = _run(curl, "-s", "-m", "10", f"{base_url}/api/ps")
    if not body:
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None
    for entry in data.get("models", []) or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("name") == name or entry.get("model") == name:
            return Model(
                name=name,
                size_gb=round(float(entry.get("size", 0)) / 1e9, 2),
                context_length=int(entry.get("context_length", 0) or 0),
            )
    return None


def estimate_from(observations: list[Observation], floor_slots: float = 1.0) -> Estimate:
    """Fit s and τ to what actually ran.

    τ is `base + rate × KB` by least squares when the payload sizes differ; a
    single size cannot separate the two terms, so it all goes to `base` and the
    rate stays zero rather than being invented. s is total generation-seconds over
    wall-equivalent seconds, which is what the rung data actually measures.
    """
    if not observations:
        return Estimate(slots=floor_slots, base_s=0.0, rate_s_per_kb=0.0, samples=0)

    xs = [o.payload_bytes / 1024 for o in observations]
    ys = [o.elapsed_s for o in observations]
    n = len(observations)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x > 0:
        rate = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / var_x
        base = mean_y - rate * mean_x
    else:
        rate, base = 0.0, mean_y
    # Negative fits are physically meaningless; fall back to the flat mean.
    if base < 0 or rate < 0:
        rate, base = 0.0, mean_y

    concurrent = max((o.concurrent for o in observations), default=1)
    slots = max(float(min(concurrent, n)), floor_slots)
    return Estimate(
        slots=round(slots, 2),
        base_s=round(base, 1),
        rate_s_per_kb=round(rate, 3),
        samples=n,
    )


def saturating_wait(service_s: float, queue_depth: int, slots: float) -> float:
    """Projected wait, superlinear in queue depth.

    A linear model — `service × queue/slots` — is what this module shipped with, and
    a stress escalation falsified it within one rung: measured latency grew 22 s per
    added job through twelve concurrent, then 59 s per job by sixteen. Linear
    projection under-predicts exactly where accuracy matters, so an admission rule
    built on it admits work that then times out — the failure this module exists to
    prevent.

    The correction keeps the shape a queue actually has. With load factor
    ρ = queue/slots, wait grows as ρ(1 + ρ): linear while the runner has slack,
    quadratic once it does not. That reproduces the observed slope growth far better
    than a line, and it is labelled for what it is — an empirical fit, refitted from
    observations, never trusted as a law.
    """
    if slots <= 0:
        return 0.0
    rho = queue_depth / slots
    return service_s * rho * (1 + rho)


def headroom_gb(machine: Machine, model: Model, slots: float) -> float:
    """Paging headroom the projection wants: one resident model plus a per-slot
    context share, less what is already available. Zero means the fit is
    comfortable and nothing needs to grow."""
    per_slot = model.size_gb * 0.1 * max(slots - 1, 0)
    wanted = model.size_gb + per_slot
    return round(max(wanted - machine.available_gb, 0.0), 2)


def decide(
    machine: Machine,
    model: Model | None,
    est: Estimate,
    *,
    queue_depth: int,
    payload_bytes: int,
    deadline_s: float,
) -> Fit:
    """Admit, defer, or declare the floor — with the arithmetic in the reason."""
    notes: list[str] = []
    if model is None:
        return Fit(
            verdict=FLOOR,
            reason=(
                "the model's own specs could not be read — doctrine 10 forbids"
                " proceeding on an assumed model; start the runner or name a model"
                " it holds"
            ),
            projected_wait_s=0.0,
            projected_service_s=0.0,
            headroom_gb=0.0,
            estimate=est,
        )

    if not machine.readable:
        return Fit(
            verdict=FLOOR,
            reason=(
                "this machine would not state its own memory — doctrine 10 forbids"
                " projecting onto a machine whose specs could not be read, and a zero"
                " here is the absence of a measurement rather than an empty machine"
                " (Linux: neither /proc/meminfo nor a cgroup limit was readable;"
                " macOS: sysctl and vm_stat answered nothing)"
            ),
            projected_wait_s=0.0,
            projected_service_s=0.0,
            headroom_gb=0.0,
            estimate=est,
        )

    ceiling = machine.total_gb + machine.swap_total_gb
    if ceiling > 0 and model.size_gb > ceiling:
        return Fit(
            verdict=FLOOR,
            reason=(
                f"{model.name} needs {model.size_gb} GB and this machine cannot reach"
                f" it: {machine.total_gb} GB of memory plus {machine.swap_total_gb} GB"
                " of paging space is the absolute ceiling. This is the floor doctrine"
                " 10 names — failing loudly rather than thrashing"
            ),
            projected_wait_s=0.0,
            projected_service_s=0.0,
            headroom_gb=round(model.size_gb - ceiling, 2),
            estimate=est,
        )

    service = est.service_s(payload_bytes)
    ahead = max(queue_depth, 0)
    wait = round(saturating_wait(service, ahead, est.slots), 1)
    need = headroom_gb(machine, model, est.slots)
    if need > 0:
        notes.append(
            f"projection wants {need} GB more headroom than the {machine.available_gb}"
            " GB available — grow paging space before it is needed, not after a stall"
        )
    if est.samples == 0:
        notes.append(
            "no observations yet: τ is unmeasured, so this projection is a floor, not a forecast"
        )

    if wait + service > deadline_s:
        return Fit(
            verdict=DEFER,
            reason=(
                f"projected {wait}s wait + {service}s service exceeds the {deadline_s}s"
                f" deadline at s={est.slots}, queue {ahead} — decompose the work or"
                " wait for a slot"
            ),
            projected_wait_s=wait,
            projected_service_s=service,
            headroom_gb=need,
            estimate=est,
            notes=tuple(notes),
        )
    return Fit(
        verdict=ADMIT,
        reason=(
            f"projected {wait}s wait + {service}s service fits the {deadline_s}s"
            f" deadline at s={est.slots}, queue {ahead}"
        ),
        projected_wait_s=wait,
        projected_service_s=service,
        headroom_gb=need,
        estimate=est,
        notes=tuple(notes),
    )
