# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Can the sovereign lane serve right now? Read, never assumed (ADR-0058).

The heartbeat tells the PR-review gate it may schedule the sovereign review. That is a claim
about two things this machine can check before it makes it:

- **the runner** -- a self-hosted runner carrying `[pr_automation.fallback] runner_label` is
  registered with the repository `[runners]` declares, and GitHub reports it `online`. Read
  from GitHub's runners API with the runner's OWN credential (`[runners] gh_config_dir`, every
  ambient token stripped), the one login on this machine that holds the Administration
  permission the API needs. A busy runner counts: it takes the next job when it finishes, and
  withholding its heartbeat would stale the lane out during every long review.
- **the model** -- the endpoint `[pr_automation.fallback] base_url` names answers, and holds
  `[pr_automation.fallback] model`. Read through `vibey_gh.fit.OllamaModelSampler`, the same
  reader the fit calculus uses, so there is one way in the tree to ask a runner what it holds.

Both are always checked and every failure is named, so a refusal says everything that is
wrong at once. A check that could not be read is a failure: the lane is serving only when
every answer came back positive.
"""

from __future__ import annotations

from dataclasses import dataclass

from vibey_gh.config import PrAutomationFallbackConfig
from vibey_gh.interfaces.model_sampler_interface import ModelSamplerInterface
from vibey_gh.interfaces.sovereign_interface import LaneReadinessInterface
from vibey_gh.interfaces.sovereign_runner_interface import SovereignRunnerInterface

__all__ = ["LaneState", "SovereignLaneReadiness"]


@dataclass(frozen=True)
class LaneState:
    """Whether the lane can serve, and why. Satisfies `LaneStateInterface` by shape: a frozen
    dataclass cannot inherit the protocol's read-only properties."""

    serving: bool
    reason: str


class SovereignLaneReadiness(LaneReadinessInterface):
    """The runner and the model, each read from the thing that knows."""

    def __init__(
        self,
        fallback: PrAutomationFallbackConfig,
        *,
        runner: SovereignRunnerInterface,
        model: ModelSamplerInterface,
    ) -> None:
        self._fallback = fallback
        self._runner = runner
        self._model = model

    def assess(self) -> LaneState:
        problems: list[str] = []
        observed: list[str] = []
        self._assess_runner(problems, observed)
        name, url = self._fallback.model, self._fallback.base_url
        if self._model.sample(name) is None:
            problems.append(
                f"the model endpoint at {url} did not answer with {name}"
                " (unreachable, or the model is not held)"
            )
        else:
            observed.append(f"{name} answers at {url}")
        if problems:
            return LaneState(False, "; ".join(problems))
        return LaneState(True, "; ".join(observed))

    def _assess_runner(self, problems: list[str], observed: list[str]) -> None:
        plan, problem = self._runner.render()
        if plan is None:
            problems.append(problem)
            return
        runners, problem = self._runner.registered_runners(plan)
        if problem:
            problems.append(problem)
            return
        label, repository = self._fallback.runner_label, plan.repository
        labelled = [runner for runner in runners if label in runner.labels]
        online = [runner for runner in labelled if runner.online]
        if not online:
            held = f"{len(labelled)} registered, none online" if labelled else "none registered"
            problems.append(f"no runner labelled {label} is online for {repository} ({held})")
            return
        busy = sum(1 for runner in online if runner.busy)
        observed.append(
            f"runners online with label {label} for {repository}: {len(online)} ({busy} busy)"
        )
