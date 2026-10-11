# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A health check that never answers must not keep a worker from starting."""

import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from vibey.application.bounded_preflight import bounded_preflight
from vibey.application.dto import PreflightResult
from vibey.application.preflight import ConductorPreflight
from vibey.domain.engine import EngineId


class _Hangs:
    async def preflight(self) -> PreflightResult:
        await asyncio.sleep(30)
        raise AssertionError("unreachable")


class _Answers:
    async def preflight(self) -> PreflightResult:
        return PreflightResult(installed=True, version="1", auth_ok=True)


async def test_an_answer_in_time_is_passed_through() -> None:
    assert (await bounded_preflight(_Answers(), timeout=5)).auth_ok is True  # type: ignore[arg-type]


async def test_a_check_that_hangs_is_reported_as_not_checked_and_says_how_to_go_on() -> None:
    result = await bounded_preflight(_Hangs(), timeout=0.05)  # type: ignore[arg-type]

    assert (result.installed, result.auth_ok, result.version) == (False, False, None)
    assert "did not answer in 0.05s" in result.detail
    assert "--engines" in result.detail


async def test_one_hung_engine_does_not_stop_the_others_being_recorded() -> None:
    health = Mock()
    health.record_preflight = AsyncMock()
    health.list_for_project = AsyncMock(return_value=[])
    feasibility = Mock()
    feasibility.evaluate = Mock(return_value=Mock())
    preflight = ConductorPreflight(health=health, feasibility=feasibility, timeout=0.05)
    project = uuid4()

    await preflight.run(
        project_id=project,
        adapters={EngineId.CLAUDELOOP: _Hangs(), EngineId.GPTOSSLOOP: _Answers()},  # type: ignore[dict-item]
    )

    recorded = {call.args[1]: call.args[2] for call in health.record_preflight.await_args_list}
    assert recorded[EngineId.GPTOSSLOOP].auth_ok is True
    assert recorded[EngineId.CLAUDELOOP].auth_ok is False
