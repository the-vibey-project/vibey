# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Can the sovereign lane serve? The runner and the model, each read, never assumed."""

from __future__ import annotations

from pathlib import Path

import pytest

from vibey_gh.config import PrAutomationFallbackConfig
from vibey_gh.fit import Model
from vibey_gh.interfaces.sovereign_lane_interface import (
    LaneReadinessInterface,
    LaneStateInterface,
)
from vibey_gh.sovereign_lane import LaneState, SovereignLaneReadiness
from vibey_gh.sovereign_runner import RegisteredRunner, RunnerPlan

FALLBACK = PrAutomationFallbackConfig(runner_label="vibey-local-r", model="m:1")
PLAN = RunnerPlan("org.vibey.runner-r", "o/r", "https://github.com/o/r", Path("p"), ())


class _Runner:
    """A runner whose plan and registered runners are exactly what the test says."""

    def __init__(self, runners=(), problem: str = "", render_problem: str = "") -> None:
        self._runners = tuple(runners)
        self._problem = problem
        self._render_problem = render_problem
        self.listed = 0

    def render(self):
        return (None, self._render_problem) if self._render_problem else (PLAN, "")

    def registered_runners(self, plan):
        self.listed += 1
        return self._runners, self._problem


class _Model:
    def __init__(self, held: bool = True) -> None:
        self.held = held
        self.asked: list[str] = []

    def sample(self, name: str) -> Model | None:
        self.asked.append(name)
        return Model(name=name, size_gb=13.0, context_length=65536) if self.held else None


def _online(*labels: str, busy: bool = False, online: bool = True) -> RegisteredRunner:
    return RegisteredRunner("runner-1", online, busy, labels or ("self-hosted", "vibey-local-r"))


def _assess(runner: _Runner, model: _Model | None = None) -> LaneState:
    readiness = SovereignLaneReadiness(FALLBACK, runner=runner, model=model or _Model())
    return readiness.assess()


def test_the_readiness_and_its_state_honour_their_interfaces():
    readiness = SovereignLaneReadiness(FALLBACK, runner=_Runner([_online()]), model=_Model())
    assert isinstance(readiness, LaneReadinessInterface)
    assert isinstance(readiness.assess(), LaneStateInterface)


def test_an_online_runner_and_an_answering_model_serve():
    model = _Model()
    state = _assess(_Runner([_online()]), model)
    assert state.serving
    assert state.reason == (
        "runners online with label vibey-local-r for o/r: 1 (0 busy); m:1 answers at"
        " http://127.0.0.1:11434"
    )
    assert model.asked == ["m:1"]


def test_a_busy_runner_still_serves():
    """It takes the next job when it finishes; withholding its heartbeat would stale the
    lane out during every long review."""
    state = _assess(_Runner([_online(busy=True)]))
    assert state.serving and "1 (1 busy)" in state.reason


@pytest.mark.parametrize(
    "runners, expected",
    [
        ((), "no runner labelled vibey-local-r is online for o/r (none registered)"),
        (
            (_online(online=False),),
            "no runner labelled vibey-local-r is online for o/r (1 registered, none online)",
        ),
        (
            (_online("self-hosted", "vibey-local-other"),),
            "no runner labelled vibey-local-r is online for o/r (none registered)",
        ),
    ],
)
def test_no_online_runner_with_the_label_means_not_serving(runners, expected):
    state = _assess(_Runner(runners))
    assert not state.serving and state.reason == expected


def test_a_runner_listing_that_could_not_be_read_is_a_refusal_not_a_pass():
    state = _assess(_Runner(problem="could not list the runners registered with o/r"))
    assert not state.serving and "could not list the runners" in state.reason


def test_an_unrenderable_runner_is_a_refusal_and_lists_nothing():
    runner = _Runner(render_problem="[pr_automation.fallback] is disabled")
    state = _assess(runner)
    assert not state.serving and "is disabled" in state.reason and runner.listed == 0


def test_a_model_endpoint_that_does_not_answer_is_a_refusal():
    state = _assess(_Runner([_online()]), _Model(held=False))
    assert not state.serving
    assert state.reason == (
        "the model endpoint at http://127.0.0.1:11434 did not answer with m:1"
        " (unreachable, or the model is not held)"
    )


def test_every_failure_is_named_at_once():
    state = _assess(_Runner(), _Model(held=False))
    assert not state.serving
    assert "no runner labelled" in state.reason and "did not answer with m:1" in state.reason
