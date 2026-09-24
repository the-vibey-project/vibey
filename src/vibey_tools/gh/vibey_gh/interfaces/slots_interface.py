# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams of local slot calibration (`vibey_gh.slots`, ADR-0016, sub-doctrine 9.b).

How many runs of one local model fit on one device at once is a number read from that
device (8.j), never assumed. Calibration touches four things a test must be able to replace
exactly -- the machine's own reports, an Ollama runner, the server process being swept, and
the evidence written to disk -- and each is a declared seam here. The decisions that read the
numbers (the verdict and the gate) are declared too, so a caller holds them to a contract
rather than to an implementation. Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class OllamaClientInterface(Protocol):
    """One Ollama runner, spoken to over its HTTP API."""

    base_url: str

    def version(self) -> str:
        """The runner's version, or `""` when it does not answer."""
        ...

    def loaded(self) -> list[dict[str, Any]] | None:
        """What `/api/ps` says is resident; `None` when it could not be read -- never `[]`,
        which is a reading ("nothing is loaded")."""
        ...

    def digest(self, model: str) -> str:
        """The digest `/api/tags` states for `model`, or `""`."""
        ...

    def chat(self, body: Mapping[str, Any], timeout_s: float) -> tuple[int, dict[str, Any]]:
        """POST `/api/chat`: the HTTP status and the decoded answer (an `error` key when
        the runner refused; status 0 when nothing answered at all)."""
        ...


@runtime_checkable
class DeviceFingerprinterInterface(Protocol):
    """Names the device a calibration belongs to."""

    def fingerprint(self, model: str, context_window: int) -> Any:
        """The `DeviceFingerprint` of this machine, this runner and this model."""
        ...


@runtime_checkable
class DeviceProbeInterface(Protocol):
    """One platform's statement of its own hardware: what a fingerprint's machine half is."""

    def machine(self) -> dict[str, Any]:
        """`hardware`, `processor`, `memory_bytes`, `accelerator` and `os`; an unreadable
        field is empty or zero, never guessed."""
        ...


@runtime_checkable
class RunnerParallelismInterface(Protocol):
    """How a platform's production runner is told how many runs to serve at once, and
    restarted so it takes effect (macOS: the app; Linux: systemd, #1116)."""

    def current(self) -> int | None:
        """The parallelism the runner is set to, or `None` when it states none (its default)."""
        ...

    def apply(self, parallel: int) -> None:
        """Set the runner's parallelism and restart it, returning once it answers again."""
        ...


@runtime_checkable
class HostMemorySamplerInterface(Protocol):
    """What the hardware charges right now: wired memory, free share, swap counters."""

    def sample(self) -> Any:
        """One `HostSample`."""
        ...


@runtime_checkable
class SlotServerInterface(Protocol):
    """The runner a sweep restarts at each concurrency, and restores afterwards."""

    def start(self, parallel: int) -> OllamaClientInterface:
        """Start serving with `parallel` slots and return a client once it answers."""
        ...

    def stop(self) -> None:
        """Stop whatever `start` started; safe to call when nothing is running."""
        ...

    def log_facts(self) -> dict[str, Any]:
        """What the server's own log says about the current run: slots, context per slot,
        KV cache sizes, model loads, truncations and context shifts."""
        ...


@runtime_checkable
class TurnReplayerInterface(Protocol):
    """Replays corpus segments against a runner with a fixed number of workers."""

    def run(self, segments: Sequence[Any], workers: int) -> list[Any]:
        """One `TurnOutcome` per turn replayed."""
        ...


@runtime_checkable
class CorpusSamplerInterface(Protocol):
    """Draws a stratified corpus of turn segments from a turn pool."""

    def sample(self, runs: Sequence[Any]) -> dict[str, Any]:
        """The corpus document: its segments, strata, allocation and provenance."""
        ...


@runtime_checkable
class SlotVerdictInterface(Protocol):
    """Judges a sweep's steps against the declared bounds."""

    #: The `SlotBounds` it judges by.
    bounds: Any

    def judge(self, evidence: Mapping[str, Any]) -> dict[str, Any]:
        """Per-step breaches, the stop reason, and the ideal number of concurrent runs."""
        ...


@runtime_checkable
class SweepCheckpointInterface(Protocol):
    """Where each completed step of one sweep is kept the moment it finishes, so a sweep
    that is interrupted -- a reboot, a killed session -- resumes rather than repeats."""

    def load(self, label: str) -> dict[str, Any] | None:
        """The step saved under `label` for this very sweep, or `None`."""
        ...

    def save(self, label: str, step: Mapping[str, Any]) -> None:
        """Keep a completed step, durably, before the sweep moves on."""
        ...


@runtime_checkable
class SlotEvidenceStoreInterface(Protocol):
    """Where a device's calibration evidence, and requests for a new one, are kept."""

    def read(self, key: str) -> dict[str, Any] | None:
        """The evidence recorded for fingerprint `key`, or `None`."""
        ...

    def write(self, evidence: Mapping[str, Any]) -> Any:
        """Record `evidence` under its own fingerprint key; returns where it went."""
        ...

    def request(self, key: str, reason: str) -> Any:
        """Ask for a calibration of fingerprint `key` (idempotent); returns the request's path."""
        ...

    def requested(self, key: str) -> bool:
        """Whether a calibration of fingerprint `key` has been asked for and not yet made."""
        ...


@runtime_checkable
class SlotGateInterface(Protocol):
    """Decides how many runs of one local model may run at once on this device."""

    def decide(self, declared: int | str, fingerprint: Any, evidence: Any) -> Any:
        """A `SlotDecision`: the number, why, and whether a calibration must be asked for."""
        ...
