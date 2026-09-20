# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The fit calculus as a running control loop, with its reasoning kept (#263).

`fit` measures both sides and decides once. This closes the loop around it: every
completed operation feeds its own timing back, the constants are re-fitted from a
rolling window rather than assumed, and **every decision is written down with the
inputs that produced it** — so an admission can be explained months later instead of
being re-derived from a shrug.

Three properties are the point.

**Self-adjusting.** The window is bounded, so the estimate tracks what the machine is
doing *now*. A model that was swapped out, a machine that gained free memory, a run of
unusually large payloads — each moves τ and s within a few operations rather than
being averaged into irrelevance by history.

**Reconstructible.** The journal records the whole basis of each decision: the
projection, the constants, the queue, the payload, the deadline. Recording only the
verdict would leave "why was this deferred?" unanswerable, which is the state doctrine
7 exists to prevent.

**Bounded.** This loop does not resize swap, and that is deliberate rather than
unfinished. #263 asks for headroom to be scaled autonomously; growing paging space is
an irreversible act on somebody's machine, and the floor rule puts irreversible acts
in a human's hands. So the loop computes exactly what to change, says so loudly, and
stops there. `recommendation()` is the output; acting on it is the operator's.

At the floor — a model the machine cannot host at all — it stops adjusting and says
so in plain words, in under one service time, which is what doctrine 10's
clarification requires of it.
"""

from __future__ import annotations

import json
import os
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path

from vibey_gh.fit import (
    FLOOR,
    Estimate,
    Fit,
    Machine,
    Model,
    Observation,
    OllamaModelSampler,
    decide,
    estimate_from,
    sample_machine,
)
from vibey_gh.interfaces.model_sampler_interface import ModelSamplerInterface

__all__ = ["DEFAULT_JOURNAL", "JOURNAL_ENV", "Decision", "FitLoop", "recorded_observations"]

# Where the journal lives when nobody says otherwise: beside the failover seat's state
# (`~/.local/state/vibey-gh/failover.json`), because it describes this MACHINE's runner
# rather than any one repository, and every invocation on the machine -- the CLI now, the
# live local calls next -- has to read the same one for the estimate to be a loop at all.
# `VIBEY_GH_FIT_JOURNAL` moves it, following the tool's `VIBEY_GH_*` naming.
JOURNAL_ENV = "VIBEY_GH_FIT_JOURNAL"
DEFAULT_JOURNAL = Path("~/.local/state/vibey-gh/fit.jsonl")

# `None` is a real answer for a model — "the runner does not hold it", which is the
# FLOOR case — so it cannot double as "the caller did not say". A caller that has
# already determined there is no model must be able to state that without the loop
# helpfully going and finding one.
_UNSET: object = object()


def recorded_observations(journal: Path, model: str | None = None) -> list[Observation]:
    """Measurements a previous run wrote, so constants carry across invocations.

    Only entries a caller recorded through `observe()` are returned — never a decision's
    *projection*. Feeding a projection back as a measurement would let the estimate
    confirm its own guesses and drift from the machine while growing more confident.

    With `model`, only that model's measurements. One machine-wide journal holds every
    model the runner serves, and τ for a 14B model says nothing about a 70B one — mixing
    them would fit a service time that belongs to neither.

    A missing, unreadable, or partly corrupt journal yields what it can rather than
    raising: an admission controller that will not run because its own logbook is
    damaged has made observability a single point of failure.
    """
    try:
        lines = journal.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    samples: list[Observation] = []
    for line in lines:
        try:
            entry = json.loads(line)
            if entry.get("kind") != "observation":
                continue
            if model is not None and entry.get("model") != model:
                continue
            samples.append(
                Observation(
                    payload_bytes=int(entry["payload_bytes"]),
                    elapsed_s=float(entry["elapsed_s"]),
                    concurrent=int(entry["concurrent"]),
                )
            )
        except (json.JSONDecodeError, AttributeError, KeyError, TypeError, ValueError):
            continue
    return samples


# Enough to span several rungs of concurrency without letting an hour-old machine
# state govern the next admission.
DEFAULT_WINDOW = 64


@dataclass(frozen=True)
class Decision:
    """One admission, with everything needed to re-derive it."""

    at: float
    verdict: str
    reason: str
    payload_bytes: int
    deadline_s: float
    queue_depth: int
    slots: float
    base_s: float
    rate_s_per_kb: float
    samples: int
    projected_wait_s: float
    projected_service_s: float
    headroom_gb: float
    free_gb: float
    model: str
    notes: tuple[str, ...] = field(default=())


class FitLoop:
    """A continuously re-fitted admission controller for one model on one machine.

    The model is read from the runner at `base_url` -- else `VIBEY_OLLAMA_URL`, else the
    local default -- which is the runner the work would actually go to. `model_sampler`
    replaces that reader outright (a test, or a runner that is not Ollama); `base_url`
    then only names the runner for whoever reads `loop.base_url`.

    `journal=None` keeps the decisions in memory only. `default_journal()` is where the
    CLI and any other caller that wants the machine-wide loop point it.
    """

    def __init__(
        self,
        model_name: str,
        *,
        journal: Path | None = None,
        window: int = DEFAULT_WINDOW,
        clock: Callable[[], float] | None = None,
        base_url: str | None = None,
        model_sampler: ModelSamplerInterface | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.model_name = model_name
        self.journal = journal
        self.base_url = OllamaModelSampler.resolve_base_url(base_url, environ=environ)
        self._model_sampler: ModelSamplerInterface = (
            OllamaModelSampler(self.base_url) if model_sampler is None else model_sampler
        )
        self._observations: deque[Observation] = deque(maxlen=max(window, 1))
        self._clock = clock or time.time
        self._decisions: list[Decision] = []

    @staticmethod
    def default_journal(environ: Mapping[str, str] | None = None) -> Path:
        """`VIBEY_GH_FIT_JOURNAL` when it is set and not empty, else `DEFAULT_JOURNAL`,
        with `~` expanded."""
        env = os.environ if environ is None else environ
        return Path(env.get(JOURNAL_ENV) or DEFAULT_JOURNAL).expanduser()

    def replay(self) -> int:
        """Load the measurements this loop's journal already holds into its window, and
        say how many there were.

        This is what makes separate processes one loop: each invocation starts from what
        the previous ones measured instead of from nothing. Only this loop's model's
        observations come back, never projections and never another model's timings (see
        `recorded_observations`), and the window still bounds how many of them govern the
        estimate.
        """
        if self.journal is None:
            return 0
        samples = recorded_observations(self.journal, self.model_name)
        self._observations.extend(samples)
        return len(samples)

    # -- measurement ------------------------------------------------------------

    def observe(self, payload_bytes: int, elapsed_s: float, concurrent: int) -> None:
        """Feed one completed operation back into the estimate.

        The calculus is computed for all operations, always — which only means anything
        if every operation reports what it actually cost.

        Journalled under its own `kind`, and read back only from there. A projection must
        never re-enter the loop as if it were a measurement: doing so would let the model
        confirm its own guesses, and the estimate would drift away from the machine while
        looking more confident with every cycle.
        """
        self._observations.append(
            Observation(payload_bytes=payload_bytes, elapsed_s=elapsed_s, concurrent=concurrent)
        )
        self._write(
            {
                "kind": "observation",
                "at": round(self._clock(), 3),
                "payload_bytes": payload_bytes,
                "elapsed_s": elapsed_s,
                "concurrent": concurrent,
                "model": self.model_name,
            }
        )

    @property
    def estimate(self) -> Estimate:
        return estimate_from(list(self._observations))

    @property
    def decisions(self) -> tuple[Decision, ...]:
        return tuple(self._decisions)

    # -- decision ---------------------------------------------------------------

    def admit(
        self,
        *,
        payload_bytes: int,
        deadline_s: float,
        queue_depth: int = 0,
        machine: Machine | None = None,
        model: Model | None | object = _UNSET,
    ) -> Fit:
        """Sample both sides, decide, and record the decision with its basis.

        The machine is re-sampled per call rather than cached: free memory moved by three
        points *within* a single stress rung, and an admission made against a stale
        reading is exactly the kind of confident wrong answer this module exists to avoid.
        """
        machine = sample_machine() if machine is None else machine
        if model is _UNSET:
            model = self._model_sampler.sample(self.model_name)
        resolved = model if isinstance(model, Model) else None
        est = self.estimate
        verdict = decide(
            machine,
            resolved,
            est,
            queue_depth=queue_depth,
            payload_bytes=payload_bytes,
            deadline_s=deadline_s,
        )
        self._record(verdict, est, machine, payload_bytes, deadline_s, queue_depth)
        return verdict

    def _record(
        self,
        verdict: Fit,
        est: Estimate,
        machine: Machine,
        payload_bytes: int,
        deadline_s: float,
        queue_depth: int,
    ) -> None:
        entry = Decision(
            at=round(self._clock(), 3),
            verdict=verdict.verdict,
            reason=verdict.reason,
            payload_bytes=payload_bytes,
            deadline_s=deadline_s,
            queue_depth=queue_depth,
            slots=est.slots,
            base_s=est.base_s,
            rate_s_per_kb=est.rate_s_per_kb,
            samples=est.samples,
            projected_wait_s=verdict.projected_wait_s,
            projected_service_s=verdict.projected_service_s,
            headroom_gb=verdict.headroom_gb,
            free_gb=machine.free_gb,
            model=self.model_name,
            notes=verdict.notes,
        )
        self._decisions.append(entry)
        self._write({"kind": "decision", **asdict(entry)})

    def _write(self, payload: dict) -> None:
        if self.journal is None:
            return
        try:
            self.journal.parent.mkdir(parents=True, exist_ok=True)
            with self.journal.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
        except OSError:
            # A journal that cannot be written must never take the admission down with
            # it. Losing the record is bad; refusing the work because of it is worse.
            pass

    # -- what the human is asked to do ------------------------------------------

    def recommendation(self) -> str | None:
        """The loudest thing the loop currently wants a human to know, or None.

        The floor outranks headroom: a machine that cannot host the model at all is not
        helped by being told to grow its paging space.
        """
        if not self._decisions:
            return None
        last = self._decisions[-1]
        if last.verdict == FLOOR:
            return f"FLOOR — {last.reason}"
        if last.headroom_gb > 0:
            return (
                f"grow paging space by at least {last.headroom_gb} GB before it is needed:"
                f" the projection for {self.model_name} wants more headroom than the"
                f" {last.free_gb} GB free at the last sample. This loop will not resize"
                " swap by itself — an irreversible change to your machine is yours to make"
            )
        return None
