# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh estimate`: before a run, what can be known about it -- and what cannot (#134).

Issue #134 asks for five answers before any run: whether the job can complete through
the whole pipeline, how long it will take, what it will cost, how close each coordinate
of the state is to peak, and what to adjust first. This is the first slice, and it is
deliberately honest about how little of that is measurable yet:

- **Two coordinates are measured**, both by the fit calculus that already exists:
  hardware availability (can this machine's memory and paging host the local model?) and
  software availability (does the local runner hold that model?). The paper calls the fit
  "the two-coordinate projection of this space", and that is exactly what is used.
- **The other sixteen are `unknown`**, each naming what would measure it, and the
  reported confidence falls accordingly. None is defaulted: an unmeasured coordinate that
  quietly read as healthy would turn "we do not know" into "yes" (doctrine 10).
- **Feasibility is judged along the whole path** from `--from` to `--operation`, with
  agency shortfalls reported first (`vibey_gh.feasibility`).
- **Duration** is projected through the family's one graded estimator
  (`vibey_gh.estimation`) from the fit journal's own observations, and it is labelled for
  what it is: the local model's service time for one payload. No stage timings are
  recorded in vibey-gh, so the stages' duration is `unknown`.
- **Cost is `unknown`.** Neither paid-lane spend nor local generation-seconds reach this
  command yet, and a made-up number is worse than none.

**Offline by default.** The command reads this machine's memory, and the model runner
only when the runner is on this machine (a loopback address). A runner elsewhere is not
read unless `--online` or `[estimate] offline = false` allows it; its coordinates stay
`unknown` and say why. The other sixteen coordinates have no probe yet, online or off --
when they get one, a probe that leaves the machine will sit behind the same switch.

Nothing is written: the fit journal is read, never appended to. An estimate is not an
admission, and recording it as one would put a projection where the loop keeps its
decisions.
"""

from __future__ import annotations

import ipaddress
import math
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import urlsplit

from vibey_gh import fit
from vibey_gh.estimate_report import DEFAULT_PAYLOAD_BYTES, OperationEstimate
from vibey_gh.estimation import GradedEstimator
from vibey_gh.feasibility import Coordinate, FeasibilityEvaluator, Pipeline, StateVector
from vibey_gh.fitloop import recorded_observations
from vibey_gh.interfaces.feasibility_evaluator_interface import FeasibilityEvaluatorInterface
from vibey_gh.interfaces.graded_estimator_interface import GradedEstimatorInterface
from vibey_gh.interfaces.memory_sampler_interface import MemorySamplerInterface
from vibey_gh.interfaces.model_sampler_interface import ModelSamplerInterface
from vibey_gh.interfaces.operation_estimator_interface import OperationEstimatorInterface
from vibey_gh.interfaces.pipeline_interface import PipelineInterface

__all__ = ["DEFAULT_PAYLOAD_BYTES", "OperationEstimate", "OperationEstimator"]


class OperationEstimator(OperationEstimatorInterface):
    """Measures the fit's two coordinates, judges the path, and projects the local lane.

    Every collaborator is a declared seam with the shipped behaviour as its default
    (ADR-0016, ADR-0018): the machine and model samplers are the fit calculus's own, the
    pipeline is the nine default stages, the evaluator reports agency first, the estimator
    is the family's one graded estimator, and `journal` is where the fit loop already
    keeps its observations (`None` reads none).
    """

    def __init__(
        self,
        model_name: str,
        *,
        base_url: str | None = None,
        offline: bool = True,
        journal: Path | None = None,
        pipeline: PipelineInterface | None = None,
        evaluator: FeasibilityEvaluatorInterface | None = None,
        estimator: GradedEstimatorInterface | None = None,
        machine_sampler: MemorySamplerInterface | None = None,
        model_sampler: ModelSamplerInterface | None = None,
        clock: Callable[[], float] | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.model_name = model_name
        self.base_url = fit.OllamaModelSampler.resolve_base_url(base_url, environ=environ)
        self.offline = offline
        self.journal = journal
        self._pipeline: PipelineInterface = Pipeline() if pipeline is None else pipeline
        self._evaluator: FeasibilityEvaluatorInterface = (
            FeasibilityEvaluator() if evaluator is None else evaluator
        )
        self._estimator: GradedEstimatorInterface = (
            GradedEstimator() if estimator is None else estimator
        )
        # Looked up through the module at construction, so the CLI's defaults are exactly
        # the samplers `vibey-gh fit` uses.
        self._machine_sampler: MemorySamplerInterface = (
            fit.machine_sampler() if machine_sampler is None else machine_sampler
        )
        self._model_sampler: ModelSamplerInterface = (
            fit.OllamaModelSampler(self.base_url) if model_sampler is None else model_sampler
        )
        self._clock = clock or time.time

    @staticmethod
    def is_local(url: str) -> bool:
        """Whether `url` names this machine: `localhost`, a `.localhost` name, or a
        loopback address. Decided from the text alone -- resolving a name to find out
        would itself leave the machine."""
        host = urlsplit(url).hostname or ""
        if host == "localhost" or host.endswith(".localhost"):
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def estimate(
        self,
        operation: str,
        *,
        start: str | None = None,
        payload_bytes: int = DEFAULT_PAYLOAD_BYTES,
    ) -> OperationEstimate:
        stages = self._pipeline.path(operation, start)
        machine = self._machine_sampler.sample()
        runner_read = not self.offline or self.is_local(self.base_url)
        model = self._model_sampler.sample(self.model_name) if runner_read else None
        at = round(self._clock(), 3)
        state = StateVector.unknown().with_measurements(
            self._fit_coordinates(machine, model, runner_read=runner_read, at=at)
        )
        verdict = self._evaluator.evaluate(state, stages)
        observations = (
            [] if self.journal is None else recorded_observations(self.journal, self.model_name)
        )
        duration = self._estimator.predict([o.sample for o in observations], x=payload_bytes / 1024)
        return OperationEstimate(
            operation=operation,
            start=stages[0].name,
            stages=stages,
            verdict=verdict,
            state=state,
            duration=duration,
            payload_bytes=payload_bytes,
            model=self.model_name,
            runner=self.base_url,
            runner_read=runner_read,
            offline=self.offline,
            journal=self.journal,
        )

    def _fit_coordinates(
        self, machine: fit.Machine, model: fit.Model | None, *, runner_read: bool, at: float
    ) -> tuple[Coordinate, Coordinate]:
        """Hardware and software availability, read from the fit's two sides.

        Hardware is the machine's ceiling -- memory plus paging, the same ceiling
        `fit.decide` floors against -- over what the model needs, capped at 1. It is 1
        exactly when the fit would not declare the hardware floor, so `estimate` and `fit`
        can never disagree about whether this machine can host the model at all.
        Software is 1 when the runner holds the model, loaded or on disk.
        """
        runner = f"runner at {self.base_url}"
        if not runner_read:
            why = (
                f"{runner} not read: it is not on this machine and the estimate is offline"
                " (pass --online, or set [estimate] offline = false)"
            )
        else:
            why = (
                f"{runner} did not report {self.model_name}: it does not hold it, or could"
                " not be read, and its answer does not say which — so unknown, not zero"
                " (`vibey-gh fit` treats this as the floor)"
            )
        if model is None:
            software = Coordinate("software", "availability", None, why, at)
        else:
            held = "loaded" if model.resident else "on disk, not loaded"
            software = Coordinate(
                "software", "availability", 1.0, f"{runner} holds {model.name} ({held})", at
            )

        if not machine.readable:
            hardware = Coordinate(
                "hardware",
                "availability",
                None,
                "the fit could not read this machine's memory — no reading, not an empty machine",
                at,
            )
        elif model is None:
            hardware = Coordinate(
                "hardware",
                "availability",
                None,
                f"the model's size is unknown, so whether this machine can host it is too: {why}",
                at,
            )
        else:
            ceiling = machine.total_gb + machine.swap_total_gb
            # Rounded DOWN when short, so a model a hair over the ceiling can never display
            # as 1 -- the one reading that would contradict the fit's floor.
            value = (
                1.0
                if model.size_gb <= ceiling
                else math.floor(ceiling / model.size_gb * 10_000) / 10_000
            )
            bound = "" if model.resident else " (weights on disk: a lower bound)"
            hardware = Coordinate(
                "hardware",
                "availability",
                value,
                f"fit: {model.name} needs {model.size_gb} GB{bound} against a {ceiling:.2f} GB"
                f" ceiling ({machine.total_gb} GB memory + {machine.swap_total_gb} GB paging);"
                f" {machine.available_gb} GB available now",
                at,
            )
        return hardware, software
