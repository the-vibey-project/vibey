# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every subprocess call site holds the one reaper, with its grace from its own seam.

ADR-0017: one kill-and-reap for the gate runner, the loop-process adapter and the
skills-context compiler (#283). ADR-0018: each grace comes from config where the
call site is built from config (`gates.kill_grace_seconds`,
`skills_context.kill_grace_seconds`). The adapter is not built from config, so its
grace is a constructor value. How each call site behaves with real processes is
tested beside it: `test_gate_runner.py`, `engines/test_loop_process_adapter.py`,
`test_skills_context.py`.
"""

from pathlib import Path

import pytest

from vibey.infrastructure.build.gate_runner import SubprocessGateRunner
from vibey.infrastructure.engines.descriptors import CLAUDELOOP
from vibey.infrastructure.engines.loop_process_adapter import LoopProcessAdapter
from vibey.infrastructure.process import ProcessReaper
from vibey.infrastructure.skills_context import compiler_from_config


def test_the_gate_runner_reaps_with_gates_kill_grace_seconds() -> None:
    default = SubprocessGateRunner.from_config({})
    configured = SubprocessGateRunner.from_config({"gates": {"kill_grace_seconds": 0.5}})

    assert isinstance(default._reaper, ProcessReaper)
    assert default._reaper.grace_seconds == 5.0
    assert default._reaper._event == "gate_process_not_reaped"
    assert configured._reaper.grace_seconds == 0.5


def test_the_adapter_reaps_with_its_kill_grace_and_names_its_engine() -> None:
    default = LoopProcessAdapter(descriptor=CLAUDELOOP)
    configured = LoopProcessAdapter(descriptor=CLAUDELOOP, kill_grace_seconds=0.5)

    assert isinstance(default._reaper, ProcessReaper)
    assert default._reaper.grace_seconds == 5.0
    assert default._reaper._event == "engine_process_not_reaped"
    assert default._reaper._context == {"engine": "claudeloop"}
    assert configured._reaper.grace_seconds == 0.5


def test_an_adapter_with_a_grace_that_is_not_a_bound_fails_when_built() -> None:
    with pytest.raises(ValueError, match="kill grace must be a finite number"):
        LoopProcessAdapter(descriptor=CLAUDELOOP, kill_grace_seconds=0)


def test_the_reaper_does_not_change_how_adapters_compare() -> None:
    assert LoopProcessAdapter(descriptor=CLAUDELOOP) == LoopProcessAdapter(descriptor=CLAUDELOOP)


def test_the_skills_compiler_reaps_with_skills_context_kill_grace_seconds(
    tmp_path: Path,
) -> None:
    default = compiler_from_config({"skills_context": {"mode": "shadow"}}, repo_path=tmp_path)
    configured = compiler_from_config(
        {"skills_context": {"mode": "shadow", "kill_grace_seconds": 0.5}}, repo_path=tmp_path
    )

    assert default is not None and configured is not None
    assert isinstance(default._reaper, ProcessReaper)
    assert default._reaper.grace_seconds == 5.0
    assert default._reaper._event == "skills_context_process_not_reaped"
    assert configured._reaper.grace_seconds == 0.5


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (True, "skills_context.kill_grace_seconds must be numeric"),
        ("5", "skills_context.kill_grace_seconds must be numeric"),
        (None, "skills_context.kill_grace_seconds must be numeric"),
        (0, "kill grace must be a finite number"),
        (-1, "kill grace must be a finite number"),
    ],
)
def test_a_malformed_skills_context_kill_grace_fails_when_the_worker_is_built(
    tmp_path: Path, value: object, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        compiler_from_config(
            {"skills_context": {"mode": "inject", "kill_grace_seconds": value}},
            repo_path=tmp_path,
        )
