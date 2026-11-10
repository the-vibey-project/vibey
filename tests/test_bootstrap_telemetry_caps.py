# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""build_app hands the declared `[telemetry]` buffer caps to the tracer and metrics it builds.

The caps are declared keys (sub-doctrine 12.c), not literals in `otel.py`: the bound on
the in-process span and sample buffers is the operator's to set."""

from uuid import uuid4

import pytest

from tests.test_bootstrap_surface_timeouts import _database
from vibey.bootstrap import build_app
from vibey.domain.config import ProjectConfig, TelemetryConfig, VibeyConfig
from vibey.domain.phase import Phase


@pytest.mark.asyncio
async def test_build_app_gives_the_tracer_and_metrics_the_declared_caps() -> None:
    cfg = VibeyConfig(
        project=ProjectConfig(name="demo"),
        telemetry=TelemetryConfig(max_spans=2, max_samples=3),
    )
    a, b, c, d = _database()
    with a, b, c, d:  # type: ignore[attr-defined]
        async with build_app(config=cfg) as resources:
            tracer = resources.telemetry_tracer
            for index in range(5):
                with tracer.start_span(f"s{index}"):
                    pass
            assert [s.name for s in tracer.get_finished_spans()] == ["s3", "s4"]

            project_id = uuid4()
            for value in (1.0, 2.0, 3.0, 4.0, 5.0):
                resources.telemetry_metrics.record_queue_latency(
                    project_id, Phase.BUILD, "build", value
                )
            exported = resources.telemetry_metrics.export_metrics(project_id)
            assert exported["queue_latencies"] == {"build": [3.0, 4.0, 5.0]}


@pytest.mark.asyncio
async def test_build_app_uses_the_default_caps_when_config_omits_them() -> None:
    cfg = VibeyConfig(project=ProjectConfig(name="demo"))
    a, b, c, d = _database()
    with a, b, c, d:  # type: ignore[attr-defined]
        async with build_app(config=cfg) as resources:
            tracer = resources.telemetry_tracer
            for index in range(10_001):
                with tracer.start_span(f"s{index}"):
                    pass
            assert len(tracer.get_finished_spans()) == 10_000


@pytest.mark.asyncio
async def test_build_app_uses_the_default_caps_when_no_configuration_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The resolver finds neither a vibey.toml nor environment settings: `resolved_config`
    is None, and the tracer and metrics get the documented defaults (10_000 and 1_000)."""
    from vibey.infrastructure.config_loader import StartupConfigResolver

    monkeypatch.setattr(StartupConfigResolver, "resolve", lambda self, directory: None)
    a, b, c, d = _database()
    with a, b, c, d:  # type: ignore[attr-defined]
        async with build_app() as resources:
            tracer = resources.telemetry_tracer
            for index in range(10_001):
                with tracer.start_span(f"s{index}"):
                    pass
            assert len(tracer.get_finished_spans()) == 10_000

            project_id = uuid4()
            for value in range(1_001):
                resources.telemetry_metrics.record_queue_latency(
                    project_id, Phase.BUILD, "build", float(value)
                )
            exported = resources.telemetry_metrics.export_metrics(project_id)
            assert len(exported["queue_latencies"]["build"]) == 1_000
