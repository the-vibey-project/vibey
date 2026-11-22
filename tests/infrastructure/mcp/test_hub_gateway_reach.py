# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`HubGateway.reach`: asking whether the hub is up never starts or restarts it (ADR-0101, M1).

`call` runs the starter when no hub answers; `reach` never does, so a liveness probe cannot
restart a hub unit the keep-alive has just restarted. Module-level test functions (ADR-0016)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from vibey.domain.host_tools import HubCall
from vibey.infrastructure.mcp.hub_gateway import HubGateway, HubGatewayError

LIVE = HubCall(tool="vibey_health", method="GET", route="/health/live")


class _Refused:
    def __init__(self, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> _Refused:
        return self

    def __exit__(self, *exc: object) -> None:
        pass

    def request(self, *args: Any, **kwargs: Any) -> Any:
        raise httpx.ConnectError("connection refused")


def _gateway(tmp_path: Path, starts: list[str], *, serving: bool) -> HubGateway:
    state = tmp_path / "hub"
    state.mkdir(mode=0o700)
    config = tmp_path / "vibey.toml"
    config.write_text(f'[hub]\nstate_dir = "{state}"\n')
    if serving:
        (state / "serving.json").write_text(json.dumps({"host": "127.0.0.1", "port": 9, "pid": 1}))

    def starter() -> bool:
        starts.append("start")
        return True

    return HubGateway(config_path=lambda: config, starter=starter, client=_Refused)


def test_reach_with_no_hub_running_is_an_error_and_starts_nothing(tmp_path: Path) -> None:
    starts: list[str] = []
    with pytest.raises(HubGatewayError, match="no hub is running"):
        _gateway(tmp_path, starts, serving=False).reach(LIVE)
    assert starts == []


def test_reach_to_a_silent_hub_is_an_error_and_restarts_nothing(tmp_path: Path) -> None:
    starts: list[str] = []
    with pytest.raises(HubGatewayError, match="did not answer"):
        _gateway(tmp_path, starts, serving=True).reach(LIVE)
    assert starts == []


def test_call_still_starts_the_hub_once(tmp_path: Path) -> None:
    starts: list[str] = []
    with pytest.raises(HubGatewayError):
        _gateway(tmp_path, starts, serving=True).call(LIVE)
    assert starts == ["start"]
