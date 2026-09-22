# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Surface health handlers with a fake apps client (no cluster, no database).

Unlike the project handlers, surface health observes Deployments, not
Postgres, so every path here runs without integration.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import kopf
import pytest

from vibey.infrastructure.operator import handlers


def _api(*, available: int | None, desired: int | None, error: BaseException | None = None) -> Any:
    class _FakeApi:
        def read_namespaced_deployment_status(self, name: str, namespace: str) -> Any:
            assert (name, namespace) == ("plane-api", "vibey")
            if error is not None:
                raise error
            return SimpleNamespace(
                status=SimpleNamespace(available_replicas=available),
                spec=SimpleNamespace(replicas=desired),
            )

    return _FakeApi()


async def test_deployment_health_reports_observed_replicas() -> None:
    component = await handlers.deployment_health(
        "vibey", "plane-api", client_factory=lambda: _api(available=2, desired=2)
    )
    assert (component.deployment, component.available, component.desired) == (
        "plane-api",
        2,
        2,
    )


async def test_deployment_health_treats_missing_counts_as_zero() -> None:
    component = await handlers.deployment_health(
        "vibey", "plane-api", client_factory=lambda: _api(available=None, desired=None)
    )
    assert (component.available, component.desired) == (0, None)


async def test_deployment_health_treats_read_failure_as_down() -> None:
    component = await handlers.deployment_health(
        "vibey",
        "plane-api",
        client_factory=lambda: _api(available=0, desired=0, error=RuntimeError("gone")),
    )
    assert (component.available, component.desired) == (0, None)


def test_surface_deployments_rejects_malformed_specs() -> None:
    assert handlers._surface_deployments({"components": [{"deployment": "a"}]}) == ["a"]
    assert handlers._surface_deployments({}) == []
    with pytest.raises(ValueError, match="must be a list"):
        handlers._surface_deployments({"components": "nope"})
    with pytest.raises(ValueError, match="must name a deployment"):
        handlers._surface_deployments({"components": [{"name": "a"}]})
    with pytest.raises(ValueError, match="must name a deployment"):
        handlers._surface_deployments({"components": ["a"]})


async def test_reconcile_surface_reports_ready_and_degraded() -> None:
    class _MixedApi:
        def read_namespaced_deployment_status(self, name: str, namespace: str) -> Any:
            assert namespace == "vibey"
            return SimpleNamespace(
                status=SimpleNamespace(available_replicas=1 if name == "plane-api" else 0),
                spec=SimpleNamespace(replicas=1),
            )

    status = await handlers.reconcile_surface(
        name="tracker",
        namespace="vibey",
        spec={"components": [{"deployment": "plane-api"}, {"deployment": "plane-web"}]},
        client_factory=_MixedApi,
    )
    assert status["surface"] == "tracker"
    assert status["conditions"] == [
        {
            "type": "Ready",
            "status": "False",
            "reason": "Degraded",
            "message": "no serving pods for: plane-web",
        }
    ]


def test_apps_client_loads_incluster_and_returns_client() -> None:
    with (
        patch("kubernetes.config.load_incluster_config") as load_cfg,
        patch("kubernetes.client.AppsV1Api") as apps_api,
    ):
        ret = handlers._apps_client()
        load_cfg.assert_called_once()
        apps_api.assert_called_once()
        assert ret == apps_api.return_value


async def test_on_surface_create_updates_patch() -> None:
    patch_obj = kopf.Patch()
    with patch(
        "vibey.infrastructure.operator.handlers.reconcile_surface",
        return_value={"surface": "tracker", "conditions": []},
    ):
        await handlers.on_surface_create(
            spec={"components": []},
            name="tracker",
            namespace="vibey",
            patch=patch_obj,
        )
    assert patch_obj.status["surface"] == "tracker"


async def test_reconcile_surface_cron_updates_patch() -> None:
    patch_obj = kopf.Patch()
    with patch(
        "vibey.infrastructure.operator.handlers.reconcile_surface",
        return_value={"surface": "tracker", "conditions": []},
    ):
        await handlers.reconcile_surface_cron(
            spec={"components": []},
            name="tracker",
            namespace="vibey",
            patch=patch_obj,
        )
    assert patch_obj.status["surface"] == "tracker"
