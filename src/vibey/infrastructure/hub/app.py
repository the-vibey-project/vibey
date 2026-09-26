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
- **Bounded bodies.** A body over `MAX_BODY_BYTES`, or one sent without a length, is
  refused (413/411) before it is read, so an unauthenticated caller cannot make the hub
  buffer an unbounded request.
- **Authentication, then the rate limit.** Every `/api/v1` route except the OpenAPI
  document, and `/api/metrics`, names its principal first; a request that proves nothing
  gets 401 and learns nothing else. Each principal has its own token bucket, so a flood
  from one caller never starves another; failed attempts draw from a small bucket per
  client address. Authorisation is the service's: it checks scopes before it reads
  anything.

The health probes and the OpenAPI document answer without a principal (the document is
public: it is committed at `docs/reference/hub-api.json`); the probes say only "live" and
"ready".

Every route is versioned under `/api/v1`, and the OpenAPI 3.1 document is served at
`/api/v1/openapi.json` and committed at `docs/reference/hub-api.json`; a test fails when
the two differ.
"""

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Annotated, Any, Final
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Security,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from vibey_bootstrap.fastapi_middleware import install_middleware
from vibey_bootstrap.metrics import build_metrics_snapshot
from vibey_bootstrap.ratelimit import TokenBucket

from vibey.application.dto import HubPrincipal
from vibey.application.hub.interfaces.hub_service_interface import HubServiceInterface
from vibey.domain.errors import (
    GateAlreadyAnswered,
    InvalidActorLabel,
    InvalidAnswer,
    PriorityRefused,
    ReorderRefused,
    UnknownGate,
    UnknownLane,
    UnknownProject,
    VibeyError,
)
from vibey.domain.hub_binding import HUB_BINDING
from vibey.domain.hub_pairing import CODE_DIGITS, PairingRefused
from vibey.domain.hub_scope import HUB_SCOPES, HubAction, HubForbidden, HubScope
from vibey.domain.interfaces.hub_binding_interface import HubBindingPolicyInterface
from vibey.domain.ledger_query import DEFAULT_SEARCH_LIMIT, InvalidLedgerQuery
from vibey.infrastructure.hub.authenticator import HOST_PRINCIPAL, HubRequest
from vibey.infrastructure.hub.interfaces.authenticator_interface import (
    HubAuthenticatorInterface,
)
from vibey.infrastructure.hub.interfaces.live_interface import LedgerAnnouncementsInterface
from vibey.infrastructure.hub.interfaces.pairing_interface import HubPairingInterface

MAX_BODY_BYTES: Final = 64 * 1024
"""The largest request body the hub reads. A gate answer is a few hundred bytes."""

FAILED_BURST: Final = 10.0
FAILED_PER_SECOND: Final = 0.5
"""The budget for requests that prove no principal, per client address."""

HUB_API_VERSION: Final = "1"
"""The hub API's major version: the `v1` in every route, and the OpenAPI `info.version`."""

MAX_SEARCH_LIMIT: Final = 500
"""The most ledger events one search returns."""

LIVE_PAGE: Final = 200
"""The most events one live-feed message carries; a feed behind by more sends pages."""

HEARTBEAT_SECONDS: Final = 25.0
"""How long a quiet feed waits before it says it is still there (and notices a client
that went away)."""

LANE_POLL_SECONDS: Final = 1.0
"""How often a lane feed looks for new bytes."""

POLICY_VIOLATION: Final = 1008
"""The WebSocket close code for a refused connection: it proves nothing, names a Host
or Origin this hub does not answer, or may not read what it asked for."""

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
    (PairingRefused, 403),
    (UnknownProject, 404),
    (UnknownGate, 404),
    (UnknownLane, 404),
    (GateAlreadyAnswered, 409),
    (PriorityRefused, 403),
    (ReorderRefused, 409),
    (InvalidAnswer, 422),
    (InvalidActorLabel, 422),
    (InvalidLedgerQuery, 422),
)
"""How each refusal the service raises reads over HTTP. The first match wins, so a
subclass comes before its base: `PriorityRefused` (the host's queue grant does not admit
the hub) is a 403, every other `ReorderRefused` a 409."""

REFUSED: Final[dict[int | str, dict[str, Any]]] = {
    401: {"description": "The request proves no principal."},
    411: {"description": "A body was sent without a Content-Length."},
    413: {"description": "The body is larger than the hub reads."},
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


class OfferBody(BaseModel):
    """The body of `POST /api/v1/pairing/offers` (the host only)."""

    model_config = ConfigDict(extra="forbid")

    scopes: list[HubScope] = Field(
        min_length=1, description="What a device claiming the code may do; never empty."
    )


class ClaimBody(BaseModel):
    """The body of `POST /api/v1/pairing/claim` (a device, before it holds a key)."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        min_length=CODE_DIGITS, max_length=CODE_DIGITS, description="The code the host shows."
    )
    name: str = Field(min_length=1, max_length=64, description="What the device calls itself.")


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
        live: LedgerAnnouncementsInterface,
        pairing: HubPairingInterface | None = None,
    ) -> FastAPI:
        buckets: dict[str, TokenBucket] = {}

        def spend(key: str, burst: float, rate: float) -> bool:
            bucket = buckets.get(key)
            if bucket is None:
                bucket = buckets[key] = TokenBucket(
                    budget=burst, refill_per_second=rate, name=f"hub.{key}"
                )
            return bucket.consume(1.0)

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
                address = request.client.host if request.client else "unknown"
                if not spend(f"failed:{address}", FAILED_BURST, FAILED_PER_SECOND):
                    raise HTTPException(status_code=429)
                raise HTTPException(status_code=401)
            # vibey_bootstrap's token bucket, one per principal (the dogfood rule).
            if not spend(f"principal:{found.name}", self._burst, self._rate):
                raise HTTPException(status_code=429)
            return found

        who = Annotated[HubPrincipal, Depends(principal)]
        v1 = f"/api/v{HUB_API_VERSION}"

        @app.get("/health/live", tags=["health"], summary="The process is up.")
        async def live_probe() -> dict[str, str]:
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
            responses=REFUSED,
        )
        async def projects(caller: who) -> JSONResponse:
            return JSONResponse(await service.projects(caller))

        @app.get(
            f"{v1}/projects/{{project_id}}/status",
            tags=["projects"],
            summary="One project's phase, queue depth and engine circuits.",
            responses=REFUSED,
        )
        async def status(caller: who, project_id: UUID) -> JSONResponse:
            return JSONResponse(await service.status(caller, project_id))

        @app.get(
            f"{v1}/gates",
            tags=["gates"],
            summary="Open gates, oldest first; one project's with project_id.",
            responses=REFUSED,
        )
        async def gates(caller: who, project_id: UUID | None = None) -> JSONResponse:
            return JSONResponse(await service.gates(caller, project_id))

        @app.post(
            f"{v1}/gates/{{gate_id}}/answer",
            tags=["gates"],
            summary="Answer a gate once.",
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
            responses=REFUSED,
        )
        async def budget(caller: who, project_id: UUID) -> JSONResponse:
            return JSONResponse(await service.budget(caller, project_id))

        @app.get(
            f"{v1}/projects/{{project_id}}/queue",
            tags=["queue"],
            summary="A project's queue, in claim order.",
            responses=REFUSED,
        )
        async def queue(caller: who, project_id: UUID) -> JSONResponse:
            return JSONResponse(await service.queue(caller, project_id))

        @app.post(
            f"{v1}/projects/{{project_id}}/queue/{{job_id}}/bump",
            tags=["queue"],
            summary="Move a queued job to the front, as the declared source vibey-hub.",
            responses=REFUSED,
        )
        async def bump(caller: who, project_id: UUID, job_id: UUID) -> JSONResponse:
            return JSONResponse(await service.bump(caller, project_id, job_id))

        @app.get(
            f"{v1}/projects/{{project_id}}/ledger",
            tags=["ledger"],
            summary="Search a project's ledger.",
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
            responses=REFUSED,
        )
        async def loops(caller: who) -> JSONResponse:
            return JSONResponse(service.loops(caller))

        @app.get(
            f"{v1}/lanes",
            tags=["lanes"],
            summary="The lanes running on this computer.",
            responses=REFUSED,
        )
        async def lanes(caller: who) -> JSONResponse:
            return JSONResponse(service.lanes(caller))

        @app.get(
            f"{v1}/doctor",
            tags=["doctor"],
            summary="The checks the hub runs itself.",
            responses=REFUSED,
        )
        async def doctor(caller: who) -> JSONResponse:
            return JSONResponse(await service.doctor(caller))

        @app.get(
            f"{v1}/projects/{{project_id}}/ledger/after",
            tags=["live"],
            summary="Events after a seq, oldest first: the live feed, for a client that polls.",
            responses=REFUSED,
        )
        async def ledger_after(
            caller: who,
            project_id: UUID,
            seq: Annotated[int, Query(ge=0)] = 0,
            limit: Annotated[int, Query(ge=1, le=LIVE_PAGE)] = LIVE_PAGE,
        ) -> JSONResponse:
            return JSONResponse(
                await service.ledger_after(caller, project_id, after=seq, limit=limit)
            )

        @app.get(
            f"{v1}/lanes/tail",
            tags=["live"],
            summary="A listed lane's complete lines after a byte offset.",
            responses=REFUSED,
        )
        async def lane_tail(
            caller: who, path: str, after: Annotated[int, Query(ge=0)] = 0
        ) -> JSONResponse:
            return JSONResponse(service.lane_tail(caller, path, after))

        def paired() -> HubPairingInterface:
            if pairing is None:
                raise HTTPException(status_code=503, detail="pairing is not enabled on this hub")
            return pairing

        def host_only(caller: HubPrincipal) -> None:
            # Only the host pairs, lists and revokes: a device can never widen its own
            # grant, pair another device, or revoke one (SD-01, 12.j).
            if caller.name != HOST_PRINCIPAL.name:
                raise HubForbidden(f"{caller.name} may not manage pairings; only the host may")

        @app.post(
            f"{v1}/pairing/offers",
            tags=["pairing"],
            summary="Offer a 6-digit pairing code for two minutes (the host only).",
            responses={**REFUSED, 503: {"description": "Pairing is not enabled."}},
        )
        async def offer(caller: who, body: OfferBody) -> JSONResponse:
            host_only(caller)
            return JSONResponse(paired().offer(frozenset(body.scopes)))

        @app.post(
            f"{v1}/pairing/claim",
            tags=["pairing"],
            summary="Claim a pairing code: a device's key, shown once.",
            responses={**REFUSED, 503: {"description": "Pairing is not enabled."}},
        )
        async def claim(request: Request, body: ClaimBody) -> JSONResponse:
            # No principal yet: this is how a device gets one. Every claim draws from the
            # small per-address bucket, right or wrong, so guessing is slow as well as
            # capped (`MAX_WRONG_CLAIMS`).
            address = request.client.host if request.client else "unknown"
            if not spend(f"claim:{address}", FAILED_BURST, FAILED_PER_SECOND):
                raise HTTPException(status_code=429)
            return JSONResponse(await paired().claim(body.code, body.name))

        @app.get(
            f"{v1}/devices",
            tags=["pairing"],
            summary="The paired devices, without their keys (the host only).",
            responses={**REFUSED, 503: {"description": "Pairing is not enabled."}},
        )
        async def devices(caller: who) -> JSONResponse:
            host_only(caller)
            return JSONResponse(paired().devices())

        @app.delete(
            f"{v1}/devices/{{device_id}}",
            tags=["pairing"],
            summary="Revoke a device: refused from its next request (the host only).",
            responses={
                **REFUSED,
                404: {"description": "No such paired device."},
                503: {"description": "Pairing is not enabled."},
            },
        )
        async def revoke(caller: who, device_id: str) -> JSONResponse:
            host_only(caller)
            if not await paired().revoke(device_id):
                raise HTTPException(status_code=404, detail=f"no paired device {device_id}")
            return JSONResponse({"revoked": device_id})

        async def admitted(socket: WebSocket) -> HubRequest | None:
            """The socket's request, when its Host and Origin are ones this hub answers.
            A browser always sends Origin on a WebSocket, and a page on another origin must
            never ride the user's credentials in (cross-site WebSocket hijacking)."""
            origin = socket.headers.get("origin")
            if not self._binding.admits(socket.headers.get("host"), allowed_hosts) or (
                origin is not None and urlsplit(origin).netloc.lower() not in allowed_hosts
            ):
                return None
            return HubRequest(
                method="GET",
                path=socket.url.path,
                query=socket.url.query,
                headers={name.lower(): value for name, value in socket.headers.items()},
                body=b"",
            )

        @app.websocket(f"{v1}/projects/{{project_id}}/live")
        async def project_live(socket: WebSocket, project_id: UUID, after: int = 0) -> None:
            request = await admitted(socket)
            if request is None or (await authenticator.authenticate(request)) is None:
                await socket.close(code=POLICY_VIOLATION)
                return
            with live.subscribe(project_id) as wake:
                last = max(after, 0)
                try:
                    while True:
                        # Authenticated again for every page: a principal revoked while
                        # the socket is open is refused at the next event, not the next
                        # connection.
                        caller = await authenticator.authenticate(request)
                        if caller is None:
                            raise HubForbidden("the principal no longer proves itself")
                        page = await service.ledger_after(
                            caller, project_id, after=last, limit=LIVE_PAGE
                        )
                        if socket.client_state.name == "CONNECTING":
                            await socket.accept()
                        body = page if isinstance(page, dict) else {}
                        events = body.get("events") or []
                        if events:
                            await socket.send_json(body)
                            last = int(body["last_seq"])
                            if len(events) == LIVE_PAGE:
                                continue
                        try:
                            await asyncio.wait_for(wake.get(), timeout=HEARTBEAT_SECONDS)
                        except TimeoutError:
                            await socket.send_json({"heartbeat": last})
                except (HubForbidden, UnknownProject):
                    await socket.close(code=POLICY_VIOLATION)
                except WebSocketDisconnect:
                    return

        @app.websocket(f"{v1}/lanes/live")
        async def lane_live(socket: WebSocket, path: str, after: int = 0) -> None:
            request = await admitted(socket)
            if request is None or (await authenticator.authenticate(request)) is None:
                await socket.close(code=POLICY_VIOLATION)
                return
            offset = max(after, 0)
            try:
                while True:
                    caller = await authenticator.authenticate(request)
                    if caller is None:
                        raise HubForbidden("the principal no longer proves itself")
                    chunk = service.lane_tail(caller, path, offset)
                    if socket.client_state.name == "CONNECTING":
                        await socket.accept()
                    if isinstance(chunk, dict) and chunk.get("lines"):
                        await socket.send_json(chunk)
                    offset = int(chunk["offset"]) if isinstance(chunk, dict) else offset
                    await asyncio.sleep(LANE_POLL_SECONDS)
            except (HubForbidden, UnknownLane):
                await socket.close(code=POLICY_VIOLATION)
            except WebSocketDisconnect:
                return

        return app

    def _harden(self, app: FastAPI, allowed_hosts: frozenset[str]) -> None:
        binding = self._binding

        @app.middleware("http")
        async def harden(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ) -> Response:
            length = request.headers.get("content-length")
            if not binding.admits(request.headers.get("host"), allowed_hosts):
                response: Response = JSONResponse(
                    {"detail": "this hub does not answer that Host"}, status_code=421
                )
            elif request.headers.get("transfer-encoding"):
                response = JSONResponse({"detail": "send a Content-Length"}, status_code=411)
            elif length is not None and (not length.isdigit() or int(length) > MAX_BODY_BYTES):
                response = JSONResponse({"detail": "the body is too large"}, status_code=413)
            else:
                response = await call_next(request)
            for name, value in SECURITY_HEADERS.items():
                response.headers[name] = value
            return response

    @staticmethod
    def _errors(app: FastAPI) -> None:
        async def refused(_request: Request, exc: Exception) -> JSONResponse:
            status = next((code for kind, code in ERROR_STATUS if isinstance(exc, kind)), 500)
            return JSONResponse({"detail": str(exc)}, status_code=status)

        for kind, _code in ERROR_STATUS:
            app.add_exception_handler(kind, refused)


HUB_APP: Final = HubAppFactory()
"""The factory `vibey serve` builds its app with."""
