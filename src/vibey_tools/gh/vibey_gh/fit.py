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
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from vibey_gh.estimation import GradedEstimator, Sample
from vibey_gh.interfaces.context_sizer_interface import ContextSizerInterface
from vibey_gh.interfaces.graded_estimator_interface import GradedEstimatorInterface
from vibey_gh.interfaces.memory_sampler_interface import MemorySamplerInterface
from vibey_gh.interfaces.model_sampler_interface import ModelSamplerInterface
from vibey_gh.interfaces.text_file_reader_interface import TextFileReaderInterface

__all__ = [
    "ADMIT",
    "DEFAULT_OLLAMA_URL",
    "DEFER",
    "FLOOR",
    "OLLAMA_URL_ENV",
    "ContextSizer",
    "DarwinMemorySampler",
    "Estimate",
    "Fit",
    "LinuxMemorySampler",
    "Machine",
    "Model",
    "Observation",
    "OllamaModelSampler",
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
# This process's own cgroup, which is where its limit actually lives. The files above name
# the ROOT of each hierarchy, and a container on a host-mounted hierarchy is not at the
# root: its `memory.max` sits under the path this file reports, while the root's reads
# `max`. Reading only the root therefore falls through to `/proc/meminfo` and reports the
# HOST's memory -- the exact mistake the cgroup preference exists to avoid.
LINUX_PROC_SELF_CGROUP = "/proc/self/cgroup"
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

# Where the model side is read from. `VIBEY_OLLAMA_URL` is the name the fallback workflows
# already export on the sovereign runner (`--base-url "${VIBEY_OLLAMA_URL:-...}"`), so the
# fit is read from the same runner the local review it gates would call -- not from a
# second guess at where that runner lives. The URL below is the default when nothing says
# otherwise, and the same one `[pr_automation.fallback] base_url` ships with.
OLLAMA_URL_ENV = "VIBEY_OLLAMA_URL"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
# Per request. A runner that cannot answer a metadata query in this long is not one a
# projection should be built on, and the sampler reports it as unreadable instead.
DEFAULT_OLLAMA_TIMEOUT_S = 10

# The context window a local call asks for, sized to its prompt (see `ContextSizer`). Each
# is a default rather than a constant (ADR-0018).
DEFAULT_CONTEXT_FLOOR_TOKENS = 4096
DEFAULT_CONTEXT_CEILING_TOKENS = 32768
DEFAULT_CHARS_PER_TOKEN = 3
DEFAULT_CONTEXT_RESERVE_TOKENS = 2048


def _with_nested(paths: tuple[str, ...], relative: str) -> tuple[str, ...]:
    """Each path preceded by its equivalent inside `relative`, the caller's own cgroup.

    `/sys/fs/cgroup/memory.max` with `/docker/abc` becomes
    `/sys/fs/cgroup/docker/abc/memory.max`, which is where a container's real limit sits;
    the original follows it, so a host that is at the hierarchy root is unaffected and a
    derived path that does not exist simply falls through.

    Derived from the CONFIGURED paths rather than from constants, so a caller that mounts
    its hierarchy elsewhere keeps that choice and gains this one (ADR-0018).
    """
    if not relative:
        return paths
    nested: list[str] = []
    for path in paths:
        directory, _, name = path.rpartition("/")
        nested.extend((f"{directory}/{relative.strip('/')}/{name}", path))
    return tuple(nested)


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
    # Whether the runner had this model LOADED when it was read. Resident, `size_gb` is the
    # runner's own reading of what the model occupies and `context_length` is the window in
    # use (`/api/ps`). Not resident, `size_gb` is its weights on disk (`/api/tags`) and
    # `context_length` the maximum its metadata states (`/api/show`) -- a lower bound on
    # what loading it will occupy, because the context's KV cache and the compute buffers
    # come on top. The two must not pass for each other, so `decide()` says which it had.
    resident: bool = True


@dataclass(frozen=True)
class Observation:
    """One completed operation, contributing its own timing to the estimate."""

    payload_bytes: int
    elapsed_s: float
    concurrent: int

    @property
    def sample(self) -> Sample:
        """This observation as the shared estimator reads it: payload in KB against the
        seconds it took. The one conversion `estimate_from` and `vibey-gh estimate` both
        use, so the two can never disagree about what an observation says."""
        return Sample(x=self.payload_bytes / 1024, y=self.elapsed_s)


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
        proc_self_cgroup_path: str = LINUX_PROC_SELF_CGROUP,
    ) -> None:
        self._reader: TextFileReaderInterface = TextFileReader() if reader is None else reader
        self._meminfo_path = meminfo_path
        # Each tuple gains this process's OWN cgroup ahead of the hierarchy root, so a
        # container that is not at the root is read where its limit actually is. Ahead,
        # not instead: `_first_int` walks the tuple in order, so a derived path that does
        # not exist or holds `max` falls through to the root exactly as before. The
        # addition can therefore only replace a missing answer with a real one -- never
        # a real answer with a wrong one, which is the trade this module refuses.
        #
        # Both tuples are expanded the same way, which is what keeps `_paired_int`'s
        # index pairing honest: index n of limit and usage stay the same cgroup.
        relative = self._relative_cgroup(proc_self_cgroup_path)
        self._cgroup_limit_paths = _with_nested(cgroup_limit_paths, relative)
        self._cgroup_usage_paths = _with_nested(cgroup_usage_paths, relative)
        self._cgroup_swap_limit_paths = _with_nested(cgroup_swap_limit_paths, relative)
        self._cgroup_swap_usage_paths = _with_nested(cgroup_swap_usage_paths, relative)

    def _relative_cgroup(self, path: str) -> str:
        """This process's cgroup path relative to its hierarchy root, or `""`.

        `/proc/self/cgroup` lists one line per hierarchy: cgroup v2 writes a single
        `0::/some/path`, v1 writes `N:controller,controller:/some/path`. The memory
        controller's line is preferred and the v2 line is the fallback, because a v1
        memory path is the one that belongs under a v1 memory mount.

        `""` for the root, for an unreadable file, and for anything unparsed -- all of
        which mean "add nothing", leaving the configured paths exactly as they were.
        """
        raw = self._reader.read(path)
        if raw is None:
            return ""
        unified = ""
        for line in raw.splitlines():
            parts = line.split(":", 2)
            if len(parts) != 3:
                continue
            controllers, relative = parts[1], parts[2].strip()
            if relative in ("", "/"):
                continue
            if "memory" in controllers.split(","):
                return relative
            if controllers == "" and not unified:
                unified = relative
        return unified

    def sample(self) -> Machine:
        fields = self._meminfo()
        total = fields.get("MemTotal", 0)
        # MemAvailable is the kernel's own answer to "what could a new process get?" and
        # is the right number here; MemFree, which ignores reclaimable cache, is only the
        # fallback for a kernel too old to publish it.
        free = fields.get("MemAvailable", fields.get("MemFree", 0))
        swap_total = fields.get("SwapTotal", 0)
        swap_used = max(swap_total - fields.get("SwapFree", 0), 0)

        limit, version = self._first_int(self._cgroup_limit_paths)
        if limit is not None and (total <= 0 or limit < total):
            # Limit and usage are read as a matched pair: index n of each tuple is the
            # same cgroup version, so a v2 limit is only ever reduced by a v2 usage. Read
            # independently, a hybrid host with both hierarchies mounted could subtract a
            # v1 cgroup's usage from a v2 cgroup's limit -- two different accounting
            # scopes, and the error runs towards a larger free figure.
            usage = self._paired_int(self._cgroup_usage_paths, version)
            if usage is None:
                # No usage reading means free memory inside this cgroup was never
                # measured, and an unmeasured figure is zero rather than the whole limit.
                # The host's MemAvailable is not a smaller ceiling to fall back on: it
                # describes the host's accounting scope, not this cgroup's, so capping it
                # at the limit would report a full container as entirely free -- which
                # inflates the ceiling, the one direction doctrine 10 forbids, and which
                # `test_a_cgroup_limit_is_read_even_when_proc_meminfo_is_not` already
                # answers with zero for the same reason.
                free = 0
            else:
                free = max(limit - usage, 0)
            total = limit
            # The host's paging space is not this container's to claim.
            swap_total = self._first_int(self._cgroup_swap_limit_paths)[0] or 0
            swap_used = min(self._first_int(self._cgroup_swap_usage_paths)[0] or 0, swap_total)

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

    def _first_int(self, paths: tuple[str, ...]) -> tuple[int | None, int]:
        """The first of these files that holds a plain integer, with its index in `paths`,
        or `(None, -1)`.

        cgroup v2 writes `max` for "no limit", which is not an integer and so falls
        through to the next path and finally to `None` -- which is the honest answer:
        this hierarchy states no number here. The index comes back with the value so a
        caller can read the file that pairs with it (`_paired_int`) rather than searching
        the companion tuple from the top and landing on a different cgroup version.
        """
        for index, path in enumerate(paths):
            raw = self._reader.read(path)
            if raw is not None and raw.strip().isdigit():
                return int(raw.strip()), index
        return None, -1

    def _paired_int(self, paths: tuple[str, ...], index: int) -> int | None:
        """The integer at `index` of `paths` -- the file belonging to the same cgroup
        version as the one a limit was just read from -- or `None`.

        A caller that overrides one path tuple and not the other can leave `index` past
        the end of this one; that hierarchy simply publishes no such file here.
        """
        if index >= len(paths):
            return None
        raw = self._reader.read(paths[index])
        if raw is None or not raw.strip().isdigit():
            return None
        return int(raw.strip())


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


class OllamaModelSampler(ModelSamplerInterface):
    """The model side of the fit, read from an Ollama runner — loaded or not.

    `/api/ps` lists only what is RESIDENT. Asked alone, it makes a model the runner holds
    on disk but has not loaded yet read exactly like a model the runner does not have, so
    every cold call — the first review after the runner idled its model out — would be
    refused at the floor for the wrong reason. A model that is not loaded is therefore
    looked for in `/api/tags`, which lists everything the runner holds, and its context
    length is read from `/api/show`'s model metadata. It comes back with `resident=False`,
    because its size is then the weights on disk: a lower bound, not a measurement.

    `None` is kept for exactly what it names — the runner does not hold this model, or
    could not be read at all — and never stands in for "not loaded right now".

    Where the runner is: `base_url`, else `VIBEY_OLLAMA_URL`, else `fallback_url` (see
    `resolve_base_url`). The transport is `curl`, as it always was here, so the sampler
    adds no dependency (#135: the sampler reads what the machine already publishes); `run`
    and `curl` are injectable so a test hands it exact responses without a socket.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        environ: Mapping[str, str] | None = None,
        fallback_url: str = DEFAULT_OLLAMA_URL,
        timeout_s: int = DEFAULT_OLLAMA_TIMEOUT_S,
        run: Callable[..., str] | None = None,
        curl: str | None = None,
    ) -> None:
        self.base_url = self.resolve_base_url(base_url, environ=environ, fallback=fallback_url)
        self._timeout_s = timeout_s
        self._run = run
        self._curl = curl

    @staticmethod
    def resolve_base_url(
        explicit: str | None = None,
        *,
        environ: Mapping[str, str] | None = None,
        fallback: str = DEFAULT_OLLAMA_URL,
    ) -> str:
        """The runner to read: `explicit`, else `VIBEY_OLLAMA_URL`, else `fallback`.

        An empty value at any step counts as unset, which is how a shell spells it. The
        trailing slash is dropped so `http://host:11434/` and `http://host:11434` read the
        same endpoints.
        """
        env = os.environ if environ is None else environ
        return (explicit or env.get(OLLAMA_URL_ENV) or fallback).rstrip("/")

    def sample(self, name: str) -> Model | None:
        loaded = self._entry(self._request("/api/ps"), name)
        if loaded is not None:
            return Model(
                name=name,
                size_gb=round(float(loaded.get("size", 0)) / 1e9, 2),
                context_length=int(loaded.get("context_length", 0) or 0),
            )
        held = self._entry(self._request("/api/tags"), name)
        if held is None:
            return None
        # `model` is the current field and `name` the deprecated one older runners read; a
        # runner ignores whichever it does not know, so both are sent.
        show = self._request("/api/show", {"model": name, "name": name})
        return Model(
            name=name,
            size_gb=round(float(held.get("size", 0)) / 1e9, 2),
            context_length=self._stated_context(show),
            resident=False,
        )

    def _request(self, path: str, body: dict[str, str] | None = None) -> object:
        """The runner's JSON answer at `path` — a POST when there is a `body` — or `None`
        when there is no `curl`, no answer, or no JSON in it."""
        curl = self._curl or shutil.which("curl")
        if not curl:
            return None
        command = [curl, "-s", "-m", str(self._timeout_s)]
        if body is not None:
            command += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
        # `_run` is looked up here rather than bound at construction, so the module's own
        # runner stays the one default.
        raw = (self._run or _run)(*command, f"{self.base_url}{path}")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _entry(data: object, name: str) -> dict | None:
        """The `models` entry naming this model, or `None`.

        A name without a tag also matches its `:latest`, because that is the model the
        runner itself resolves the bare name to. The tag is whatever follows the last `:`
        in the final path segment, so a registry port (`host:5000/model`) is not one.
        """
        if not isinstance(data, dict):
            return None
        names = {name}
        if ":" not in name.rsplit("/", 1)[-1]:
            names.add(f"{name}:latest")
        for entry in data.get("models", []) or []:
            if isinstance(entry, dict) and (
                entry.get("name") in names or entry.get("model") in names
            ):
                return entry
        return None

    @staticmethod
    def _stated_context(show: object) -> int:
        """The context length the model's own metadata states, or 0 when it states none.

        `model_info` keys it by architecture — `qwen2.context_length`,
        `llama.context_length` — so the architecture it names picks the key first, and any
        other `*.context_length` is the fallback for a runner that omits the name. Zero is
        the absence of a reading, exactly as a loaded model with no stated window reports.
        """
        info = show.get("model_info") if isinstance(show, dict) else None
        if not isinstance(info, dict):
            return 0
        preferred = info.get(f"{info.get('general.architecture')}.context_length")
        others = (value for key, value in info.items() if str(key).endswith(".context_length"))
        for value in (preferred, *others):
            if type(value) is int and value > 0:
                return value
        return 0


class ContextSizer(ContextSizerInterface):
    """A context window that actually fits the prompt — the one rule every local call uses.

    Ollama loads models with a small default context (4096 tokens here). Sending a
    60,000-character diff into that does not error: llama.cpp repeatedly shifts the
    window instead, and generation degrades from seconds to never-finishes — observed in
    production as the fallback timing out at 600s and then 1800s on a 717-line diff a
    10,000-character slice of which reviewed in 17 seconds. Code tokenizes at roughly
    3 characters per token; 2048 covers the system prompt, schema and response. Capped
    because an enormous request should fail visibly rather than exhaust the host.

    Each of those numbers is a keyword with that value as its default (ADR-0018); the
    defaults reproduce the rule `local_review` shipped with exactly.
    """

    def __init__(
        self,
        *,
        floor_tokens: int = DEFAULT_CONTEXT_FLOOR_TOKENS,
        ceiling_tokens: int = DEFAULT_CONTEXT_CEILING_TOKENS,
        chars_per_token: int = DEFAULT_CHARS_PER_TOKEN,
        reserve_tokens: int = DEFAULT_CONTEXT_RESERVE_TOKENS,
    ) -> None:
        if chars_per_token < 1:
            raise ValueError("chars_per_token must be at least 1")
        if floor_tokens > ceiling_tokens:
            raise ValueError("floor_tokens must not exceed ceiling_tokens")
        self._floor = floor_tokens
        self._ceiling = ceiling_tokens
        self._chars_per_token = chars_per_token
        self._reserve = reserve_tokens

    def num_ctx(self, prompt_chars: int) -> int:
        wanted = prompt_chars // self._chars_per_token + self._reserve
        return min(self._ceiling, max(self._floor, wanted))


def sample_model(name: str, base_url: str | None = None) -> Model | None:
    """Read the model side from the runner itself. None when the runner does not hold the
    model or cannot be read — the caller must not proceed on an assumed model (doctrine 10).

    Module-level for the same reason as `sample_machine`: it is the published entry point
    `cli.py` and adopters already call by name, so it stays a function and does nothing
    but ask `OllamaModelSampler`. `base_url` defaults to `VIBEY_OLLAMA_URL`, then to
    `DEFAULT_OLLAMA_URL`.
    """
    return OllamaModelSampler(base_url).sample(name)


def estimate_from(
    observations: list[Observation],
    floor_slots: float = 1.0,
    *,
    estimator: GradedEstimatorInterface | None = None,
) -> Estimate:
    """Fit s and τ to what actually ran.

    τ is `base + rate × KB` by least squares when the payload sizes differ; a
    single size cannot separate the two terms, so it all goes to `base` and the
    rate stays zero rather than being invented. s is total generation-seconds over
    wall-equivalent seconds, which is what the rung data actually measures.

    τ is fitted by the family's one graded estimator (`vibey_gh.estimation`, #88/#134)
    rather than by arithmetic of its own; this function keeps only what is the fit's --
    the slots, and the rounding its callers have always seen. `estimator` replaces it
    for a caller that needs another (a test, or a quantity that may go negative).
    """
    if not observations:
        return Estimate(slots=floor_slots, base_s=0.0, rate_s_per_kb=0.0, samples=0)

    samples = [o.sample for o in observations]
    line = (GradedEstimator() if estimator is None else estimator).fit(samples)
    n = line.n
    concurrent = max((o.concurrent for o in observations), default=1)
    slots = max(float(min(concurrent, n)), floor_slots)
    return Estimate(
        slots=round(slots, 2),
        base_s=round(line.intercept, 1),
        rate_s_per_kb=round(line.slope, 3),
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
    if not model.resident:
        notes.append(
            f"{model.name} is not loaded: {model.size_gb} GB is its weights on disk, a lower"
            " bound on what loading it will occupy — the context's KV cache comes on top"
        )
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
