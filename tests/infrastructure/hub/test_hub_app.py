# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's HTTP surface: every route, and the hardening in front of all of them.

The service behind the app is a fake that returns which use case ran, so these tests
are about the surface alone: who may reach a route (Host allowlist, principal), what
every response carries (security headers, never a CORS header), and how each refusal
the service raises reads over HTTP. The use cases themselves are tested in
tests/application/test_hub_service.py, and end to end in tests/cli/test_serve_cli.py.
"""

from typing import Any
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI

from vibey.application.dto import HubPrincipal
from vibey.domain.errors import (
    GateAlreadyAnswered,
    InvalidActorLabel,
    InvalidAnswer,
    PriorityRefused,
    ReorderRefused,
    UnknownGate,
    UnknownProject,
)
from vibey.domain.hub_binding import HUB_BINDING
from vibey.domain.hub_scope import HUB_SCOPES, NEVER_FROM_THE_HUB, HubForbidden
from vibey.domain.ledger_query import InvalidLedgerQuery
from vibey.infrastructure.hub.app import (
    HUB_API_VERSION,
    SECURITY_HEADERS,
    HubAppFactory,
)
from vibey.infrastructure.hub.authenticator import (
    FirstOf,
    HubRequest,
    LocalTokenAuthenticator,
)
from vibey.infrastructure.hub.interfaces.app_interface import HubAppFactoryInterface

TOKEN = "t0ken"
HOST = "127.0.0.1:8765"
AUTH = {"authorization": f"Bearer {TOKEN}", "host": HOST}
PID = UUID("11111111-1111-4111-8111-111111111111")
JOB = UUID("22222222-2222-4222-8222-222222222222")
GATE = UUID("33333333-3333-4333-8333-333333333333")


class Service:
    """Returns the name of the use case that ran, and what it was given."""

    def __init__(self) -> None:
        self.raises: Exception | None = None

    def _done(self, name: str, *args: Any) -> Any:
        if self.raises is not None:
            raise self.raises
        return {"ran": name, "args": [str(arg) for arg in args]}

    async def projects(self, principal: HubPrincipal) -> Any:
        return self._done("projects", principal.name)

    async def status(self, principal: HubPrincipal, project_id: UUID) -> Any:
        return self._done("status", project_id)

    async def gates(self, principal: HubPrincipal, project_id: UUID | None) -> Any:
        return self._done("gates", project_id)

    async def answer_gate(
        self, principal: HubPrincipal, gate_id: UUID, answer: Any, *, request_id: str | None
    ) -> Any:
        return self._done("answer_gate", gate_id, answer, request_id)

    async def budget(self, principal: HubPrincipal, project_id: UUID) -> Any:
        return self._done("budget", project_id)

    async def queue(self, principal: HubPrincipal, project_id: UUID) -> Any:
        return self._done("queue", project_id)

    async def bump(self, principal: HubPrincipal, project_id: UUID, job_id: UUID) -> Any:
        return self._done("bump", project_id, job_id)

    async def ledger(
        self,
        principal: HubPrincipal,
        project_id: UUID,
        *,
        text: str | None,
        kinds: Any,
        actor: str | None,
        limit: int,
    ) -> Any:
        return self._done("ledger", project_id, text, list(kinds), actor, limit)

    def loops(self, principal: HubPrincipal) -> Any:
        return self._done("loops")

    def lanes(self, principal: HubPrincipal) -> Any:
        return self._done("lanes")

    async def doctor(self, principal: HubPrincipal) -> Any:
        return self._done("doctor")


class Nobody:
    """Names a principal with no scopes for any request."""

    async def authenticate(self, request: HubRequest) -> HubPrincipal | None:
        return HubPrincipal(name="nobody")


def _app(
    service: Service | None = None,
    *,
    ready: bool = True,
    authenticator: Any = None,
    factory: HubAppFactory | None = None,
) -> FastAPI:
    async def readiness() -> bool:
        return ready

    return (factory or HubAppFactory()).build(
        service or Service(),  # type: ignore[arg-type]
        authenticator=authenticator or LocalTokenAuthenticator(TOKEN),
        allowed_hosts=HUB_BINDING.allowed_hosts(8765, frozenset()),
        ready=readiness,
    )


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=f"http://{HOST}")


def test_the_factory_meets_its_declared_seam() -> None:
    assert isinstance(HubAppFactory(), HubAppFactoryInterface)


@pytest.mark.parametrize(
    ("method", "path", "ran", "body"),
    [
        ("GET", "/api/v1/projects", "projects", None),
        ("GET", f"/api/v1/projects/{PID}/status", "status", None),
        ("GET", "/api/v1/gates", "gates", None),
        ("GET", f"/api/v1/gates?project_id={PID}", "gates", None),
        ("POST", f"/api/v1/gates/{GATE}/answer", "answer_gate", {"answer": {"verdict": "ok"}}),
        ("GET", f"/api/v1/projects/{PID}/budget", "budget", None),
        ("GET", f"/api/v1/projects/{PID}/queue", "queue", None),
        ("POST", f"/api/v1/projects/{PID}/queue/{JOB}/bump", "bump", None),
        ("GET", f"/api/v1/projects/{PID}/ledger?text=x&kind=GateAnswered&limit=3", "ledger", None),
        ("GET", "/api/v1/loops", "loops", None),
        ("GET", "/api/v1/lanes", "lanes", None),
        ("GET", "/api/v1/doctor", "doctor", None),
    ],
)
async def test_every_route_runs_its_use_case_for_the_host(
    method: str, path: str, ran: str, body: Any
) -> None:
    async with _client(_app()) as client:
        response = await client.request(method, path, headers=AUTH, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["ran"] == ran
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value


async def test_the_ledger_route_passes_every_filter_through() -> None:
    async with _client(_app()) as client:
        response = await client.get(
            f"/api/v1/projects/{PID}/ledger?text=x&kind=A&kind=B&actor=me&limit=3", headers=AUTH
        )
    assert response.json()["args"] == [str(PID), "x", "['A', 'B']", "me", "3"]


async def test_a_request_that_proves_nothing_is_refused_before_any_route() -> None:
    service = Service()
    service.raises = AssertionError("no route may run")
    async with _client(_app(service)) as client:
        missing = await client.get("/api/v1/projects", headers={"host": HOST})
        wrong = await client.get(
            "/api/v1/projects", headers={"host": HOST, "authorization": "Bearer nope"}
        )
        basic = await client.get(
            "/api/v1/projects", headers={"host": HOST, "authorization": f"Basic {TOKEN}"}
        )
    assert [missing.status_code, wrong.status_code, basic.status_code] == [401, 401, 401]


@pytest.mark.parametrize(
    "host", ["attacker.example:8765", "attacker.example", "192.168.1.20:8765", ""]
)
async def test_dns_rebinding_a_host_it_does_not_expect_is_refused(host: str) -> None:
    service = Service()
    service.raises = AssertionError("no route may run")
    async with _client(_app(service)) as client:
        response = await client.get("/api/v1/projects", headers={**AUTH, "host": host})
        probe = await client.get("/health/live", headers={"host": host})
    assert response.status_code == 421 and probe.status_code == 421
    assert response.headers["content-security-policy"].startswith("default-src 'none'")


async def test_no_cross_origin_reader_is_ever_admitted() -> None:
    async with _client(_app()) as client:
        simple = await client.get(
            "/api/v1/projects", headers={**AUTH, "origin": "https://attacker.example"}
        )
        preflight = await client.options(
            "/api/v1/projects",
            headers={
                "host": HOST,
                "origin": "https://attacker.example",
                "access-control-request-method": "GET",
            },
        )
    for response in (simple, preflight):
        assert not [name for name in response.headers if name.startswith("access-control-")]
    assert preflight.status_code == 405


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (HubForbidden("no"), 403),
        (UnknownProject("no"), 404),
        (UnknownGate("no"), 404),
        (GateAlreadyAnswered("g", answered_by="x", answered_at="t"), 409),
        (PriorityRefused("hub", "no grant"), 403),
        (ReorderRefused("no"), 409),
        (InvalidAnswer("no"), 422),
        (InvalidActorLabel("no"), 422),
        (InvalidLedgerQuery("no"), 422),
    ],
)
async def test_each_refusal_reads_as_its_status(error: Exception, status: int) -> None:
    service = Service()
    service.raises = error
    async with _client(_app(service)) as client:
        response = await client.get("/api/v1/projects", headers=AUTH)
    assert response.status_code == status
    assert response.json() == {"detail": str(error)}


async def test_an_answer_body_with_unknown_keys_is_refused() -> None:
    async with _client(_app()) as client:
        response = await client.post(
            f"/api/v1/gates/{GATE}/answer",
            headers=AUTH,
            json={"answer": {}, "scopes": ["spend"]},
        )
    assert response.status_code == 422


async def test_the_probes_need_no_principal_and_say_only_live_or_ready() -> None:
    async with _client(_app(ready=True)) as client:
        live = await client.get("/health/live", headers={"host": HOST})
        ready = await client.get("/health/ready", headers={"host": HOST})
    async with _client(_app(ready=False)) as client:
        not_ready = await client.get("/health/ready", headers={"host": HOST})
    assert live.json() == {"status": "live"}
    assert ready.json() == {"status": "ready"}
    assert not_ready.status_code == 503 and not_ready.json() == {"status": "not ready"}


async def test_metrics_need_view() -> None:
    async with _client(_app()) as client:
        host = await client.get("/api/metrics", headers=AUTH)
    async with _client(_app(authenticator=Nobody())) as client:
        nobody = await client.get("/api/metrics", headers={"host": HOST})
    assert host.status_code == 200 and "alert_counters" in host.json()
    assert nobody.status_code == 403


async def test_the_rate_limit_answers_429_with_an_empty_body() -> None:
    factory = HubAppFactory(requests_per_second=0.0, burst=1.0)
    async with _client(_app(factory=factory)) as client:
        first = await client.get("/api/v1/projects", headers=AUTH)
        second = await client.get("/api/v1/projects", headers=AUTH)
    assert first.status_code == 200 and second.status_code == 429


async def test_the_openapi_document_is_version_one_and_3_1() -> None:
    async with _client(_app()) as client:
        document = (
            await client.get(f"/api/v{HUB_API_VERSION}/openapi.json", headers={"host": HOST})
        ).json()
    assert document["openapi"] == "3.1.0"
    assert document["info"]["version"] == "1"
    assert all(
        path.startswith(("/api/v1/", "/health/", "/api/metrics")) for path in document["paths"]
    )


async def test_first_of_asks_each_authenticator_in_turn() -> None:
    request = HubRequest(method="GET", path="/", query="", headers={}, body=b"")
    assert await FirstOf([LocalTokenAuthenticator(TOKEN), Nobody()]).authenticate(request) == (
        HubPrincipal(name="nobody")
    )
    assert await FirstOf([LocalTokenAuthenticator(TOKEN)]).authenticate(request) is None


async def test_an_oversized_or_unmeasured_body_is_refused_before_it_is_read() -> None:
    service = Service()
    service.raises = AssertionError("no route may run")
    async with _client(_app(service)) as client:
        big = await client.post(
            f"/api/v1/gates/{GATE}/answer", headers=AUTH, content=b"x" * (64 * 1024 + 1)
        )
        bogus = await client.post(
            f"/api/v1/gates/{GATE}/answer", headers={**AUTH, "content-length": "lots"}, content=b""
        )

        async def stream() -> Any:
            yield b"{}"

        chunked = await client.post(f"/api/v1/gates/{GATE}/answer", headers=AUTH, content=stream())
    assert [big.status_code, bogus.status_code, chunked.status_code] == [413, 413, 411]


async def test_a_flood_of_failed_attempts_never_starves_the_host() -> None:
    factory = HubAppFactory(requests_per_second=0.0, burst=5.0)
    async with _client(_app(factory=factory)) as client:
        failed = [
            (await client.get("/api/v1/projects", headers={"host": HOST})).status_code
            for _ in range(12)
        ]
        host = await client.get("/api/v1/projects", headers=AUTH)
    assert failed[:10] == [401] * 10 and failed[10:] == [429, 429]
    assert host.status_code == 200


def test_no_route_offers_what_the_hub_never_offers() -> None:
    """NEVER_FROM_THE_HUB is enforced by the routes that exist: none touches a reserved
    capability, and the only route under a budget is a read (security review of #1155)."""
    words = {
        "declare_paid_use": ("paid", "declare"),
        "no_cap": ("nocap", "no-cap", "no_cap"),
        "change_caps": ("caps", "cap"),
        "database_dsn": ("dsn", "database"),
        "migrations": ("migrat",),
        "canon": ("canon", "doctrine"),
    }
    assert set(words) == NEVER_FROM_THE_HUB
    app = _app()
    for route in app.routes:
        path = getattr(route, "path", "")
        segments = [part for part in path.lower().split("/") if part]
        for capability, fragments in words.items():
            assert HUB_SCOPES.reserved(capability)
            assert not any(f in segment for f in fragments for segment in segments), (
                path,
                capability,
            )
        if "budget" in path:
            assert getattr(route, "methods", set()) == {"GET"}
