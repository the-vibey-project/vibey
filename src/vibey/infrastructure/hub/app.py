# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's HTTP surface: a FastAPI app over `HubServiceInterface` (ADR-0067).

Built on `vibey_bootstrap` (the dogfood rule): its request-timing middleware, its token
bucket as the rate limit, its metrics snapshot at `/api/metrics`, and its constant-time
compare inside the authenticator. What this module adds is the web hardening a surface a
browser can reach needs, applied to every request before any route runs:

- **Host allowlist** (the DNS-rebinding defence): a request whose `Host` is not one the hub
  expects is refused with 421, whatever else it carries.
- **No CORS at all.** No `Access-Control-Allow-*` header is ever sent, so a page on another
  origin cannot read a response; the web app is served from the hub's own origin.
- **A strict CSP and friends** on every response: `default-src 'none'`, no framing, no
  referrer, `nosniff`, and `no-store` so nothing a response says is cached.
- **Authentication before routing.** Every `/api/v1` route and `/api/metrics` names its
  principal first; a request that proves nothing gets 401 and learns nothing else.
  Authorisation is the service's: it checks scopes before it reads anything.

The health probes answer without a principal, and say only "live" and "ready".

Every route is versioned under `/api/v1`, and the OpenAPI 3.1 document is served at
`/api/v1/openapi.json` and committed at `docs/reference/hub-api.json`; a test fails when
the two differ.
"""

from collections.abc import Awaitable, Callable, Mapping
from typing import Annotated, Any, Final
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from vibey_bootstrap.fastapi_middleware import install_middleware
from vibey_bootstrap.metrics import build_metrics_snapshot
from vibey_bootstrap.ratelimit import TokenBucket, fastapi_rate_limit

from vibey.application.dto import HubPrincipal
from vibey.application.hub.interfaces.hub_service_interface import HubServiceInterface
from vibey.domain.errors import (
    GateAlreadyAnswered,
    InvalidActorLabel,
    InvalidAnswer,
    ReorderRefused,
    UnknownGate,
    UnknownProject,
    VibeyError,
)
from vibey.domain.hub_binding import HUB_BINDING
from vibey.domain.hub_scope import HUB_SCOPES, HubAction, HubForbidden
from vibey.domain.interfaces.hub_binding_interface import HubBindingPolicyInterface
from vibey.domain.ledger_query import DEFAULT_SEARCH_LIMIT, InvalidLedgerQuery
from vibey.infrastructure.hub.authenticator import HubRequest
from vibey.infrastructure.hub.interfaces.authenticator_interface import (
    HubAuthenticatorInterface,
)

HUB_API_VERSION: Final = "1"
"""The hub API's major version: the `v1` in every route, and the OpenAPI `info.version`."""

MAX_SEARCH_LIMIT: Final = 500
"""The most ledger events one search returns."""

SECURITY_HEADERS: Final[Mapping[str, str]] = {
    "content-security-policy": (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ),
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "cache-control": "no-store",
    "cross-origin-resource-policy": "same-origin",
    "cross-origin-opener-policy": "same-origin",
}
"""Sent on every response, refusals included."""

ERROR_STATUS: Final[tuple[tuple[type[VibeyError], int], ...]] = (
    (HubForbidden, 403),
    (UnknownProject, 404),
    (UnknownGate, 404),
    (GateAlreadyAnswered, 409),
    (ReorderRefused, 409),
    (InvalidAnswer, 422),
    (InvalidActorLabel, 422),
    (InvalidLedgerQuery, 422),
)
"""How each refusal the service raises reads over HTTP. Order matters only for
subclasses; none here shares a branch."""

REFUSED: Final[dict[int | str, dict[str, Any]]] = {
    401: {"description": "The request proves no principal."},
    403: {"description": "The principal's scopes do not permit this."},
    421: {"description": "The Host header is not one this hub answers."},
    429: {"description": "Too many requests."},
}


class GateAnswerBody(BaseModel):
    """The body of `POST /api/v1/gates/{gate_id}/answer`."""

    model_config = ConfigDict(extra="forbid")

    answer: dict[str, Any] = Field(
        description='The answer, as `vibey answer --raw` takes it, e.g. {"choice": "yes"}.'
    )
    request_id: str | None = Field(
        default=None,
        description="Names this request so a retry of the same answer is a no-op.",
    )


class HubAppFactory:
    """Builds the hub's FastAPI app.

    Declared by `interfaces/app_interface.py::HubAppFactoryInterface`."""

    def __init__(
        self,
        *,
        binding: HubBindingPolicyInterface = HUB_BINDING,
        requests_per_second: float = 20.0,
        burst: float = 120.0,
    ) -> None:
        self._binding = binding
        self._rate = requests_per_second
        self._burst = burst

    def build(
        self,
        service: HubServiceInterface,
        *,
        authenticator: HubAuthenticatorInterface,
        allowed_hosts: frozenset[str],
        ready: Callable[[], Awaitable[bool]],
    ) -> FastAPI:
        bucket = TokenBucket(budget=self._burst, refill_per_second=self._rate, name="hub")
        app = FastAPI(
            title="vibey hub",
            version=HUB_API_VERSION,
            summary="The one HTTP surface every Krypton client reaches (ADR-0067).",
            openapi_url=f"/api/v{HUB_API_VERSION}/openapi.json",
            docs_url=None,
            redoc_url=None,
        )
        install_middleware(app, fire_alerts=False)
        self._harden(app, allowed_hosts)
        self._errors(app)
        bearer = HTTPBearer(auto_error=False, description="The host's token, or a device's key.")

        async def principal(
            request: Request,
            _documented: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)],
        ) -> HubPrincipal:
            found = await authenticator.authenticate(
                HubRequest(
                    method=request.method,
                    path=request.url.path,
                    query=request.url.query,
                    headers={name.lower(): value for name, value in request.headers.items()},
                    body=await request.body(),
                )
            )
            if found is None:
                raise HTTPException(status_code=401)
            return found

        who = Annotated[HubPrincipal, Depends(principal)]
        limited = [Depends(fastapi_rate_limit(bucket))]
        v1 = f"/api/v{HUB_API_VERSION}"

        @app.get("/health/live", tags=["health"], summary="The process is up.")
        async def live() -> dict[str, str]:
            return {"status": "live"}

        @app.get(
            "/health/ready",
            tags=["health"],
            summary="The database answers.",
            responses={503: {"description": "Not ready."}},
        )
        async def ready_probe() -> JSONResponse:
            if await ready():
                return JSONResponse({"status": "ready"})
            return JSONResponse({"status": "not ready"}, status_code=503)

        @app.get(
            "/api/metrics",
            tags=["health"],
            summary="vibey_bootstrap's metrics snapshot.",
            dependencies=limited,
            responses=REFUSED,
        )
        async def metrics(caller: who) -> JSONResponse:
            if not HUB_SCOPES.permits(caller.scopes, HubAction.READ):
                raise HubForbidden(f"{caller.name} may not read")
            return JSONResponse(build_metrics_snapshot())

        @app.get(
            f"{v1}/projects",
            tags=["projects"],
            summary="Every project, newest first.",
            dependencies=limited,
            responses=REFUSED,
        )
        async def projects(caller: who) -> JSONResponse:
            return JSONResponse(await service.projects(caller))

        @app.get(
            f"{v1}/projects/{{project_id}}/status",
            tags=["projects"],
            summary="One project's phase, queue depth and engine circuits.",
            dependencies=limited,
            responses=REFUSED,
        )
        async def status(caller: who, project_id: UUID) -> JSONResponse:
            return JSONResponse(await service.status(caller, project_id))

        @app.get(
            f"{v1}/gates",
            tags=["gates"],
            summary="Open gates, oldest first; one project's with project_id.",
            dependencies=limited,
            responses=REFUSED,
        )
        async def gates(caller: who, project_id: UUID | None = None) -> JSONResponse:
            return JSONResponse(await service.gates(caller, project_id))

        @app.post(
            f"{v1}/gates/{{gate_id}}/answer",
            tags=["gates"],
            summary="Answer a gate once.",
            dependencies=limited,
            responses=REFUSED,
        )
        async def answer(caller: who, gate_id: UUID, body: GateAnswerBody) -> JSONResponse:
            return JSONResponse(
                await service.answer_gate(caller, gate_id, body.answer, request_id=body.request_id)
            )

        @app.get(
            f"{v1}/projects/{{project_id}}/budget",
            tags=["budget"],
            summary="A project's caps and spend (read only).",
            dependencies=limited,
            responses=REFUSED,
        )
        async def budget(caller: who, project_id: UUID) -> JSONResponse:
            return JSONResponse(await service.budget(caller, project_id))

        @app.get(
            f"{v1}/projects/{{project_id}}/queue",
            tags=["queue"],
            summary="A project's queue, in claim order.",
            dependencies=limited,
            responses=REFUSED,
        )
        async def queue(caller: who, project_id: UUID) -> JSONResponse:
            return JSONResponse(await service.queue(caller, project_id))

        @app.post(
            f"{v1}/projects/{{project_id}}/queue/{{job_id}}/bump",
            tags=["queue"],
            summary="Move a queued job to the front, as the declared source vibey-hub.",
            dependencies=limited,
            responses=REFUSED,
        )
        async def bump(caller: who, project_id: UUID, job_id: UUID) -> JSONResponse:
            return JSONResponse(await service.bump(caller, project_id, job_id))

        @app.get(
            f"{v1}/projects/{{project_id}}/ledger",
            tags=["ledger"],
            summary="Search a project's ledger.",
            dependencies=limited,
            responses=REFUSED,
        )
        async def ledger(
            caller: who,
            project_id: UUID,
            text: str | None = None,
            kind: Annotated[list[str] | None, Query()] = None,
            actor: str | None = None,
            limit: Annotated[int, Query(ge=1, le=MAX_SEARCH_LIMIT)] = DEFAULT_SEARCH_LIMIT,
        ) -> JSONResponse:
            return JSONResponse(
                await service.ledger(
                    caller, project_id, text=text, kinds=kind or [], actor=actor, limit=limit
                )
            )

        @app.get(
            f"{v1}/loops",
            tags=["loops"],
            summary="The loops, their engines and efforts.",
            dependencies=limited,
            responses=REFUSED,
        )
        async def loops(caller: who) -> JSONResponse:
            return JSONResponse(service.loops(caller))

        @app.get(
            f"{v1}/lanes",
            tags=["lanes"],
            summary="The lanes running on this computer.",
            dependencies=limited,
            responses=REFUSED,
        )
        async def lanes(caller: who) -> JSONResponse:
            return JSONResponse(service.lanes(caller))

        @app.get(
            f"{v1}/doctor",
            tags=["doctor"],
            summary="The checks the hub runs itself.",
            dependencies=limited,
            responses=REFUSED,
        )
        async def doctor(caller: who) -> JSONResponse:
            return JSONResponse(await service.doctor(caller))

        return app

    def _harden(self, app: FastAPI, allowed_hosts: frozenset[str]) -> None:
        binding = self._binding

        @app.middleware("http")
        async def harden(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ) -> Response:
            if not binding.admits(request.headers.get("host"), allowed_hosts):
                response: Response = JSONResponse(
                    {"detail": "this hub does not answer that Host"}, status_code=421
                )
            else:
                response = await call_next(request)
            for name, value in SECURITY_HEADERS.items():
                response.headers[name] = value
            return response

    @staticmethod
    def _errors(app: FastAPI) -> None:
        async def refused(_request: Request, exc: Exception) -> JSONResponse:
            status = next(code for kind, code in ERROR_STATUS if isinstance(exc, kind))
            return JSONResponse({"detail": str(exc)}, status_code=status)

        for kind, _code in ERROR_STATUS:
            app.add_exception_handler(kind, refused)


HUB_APP: Final = HubAppFactory()
"""The factory `vibey serve` builds its app with."""
