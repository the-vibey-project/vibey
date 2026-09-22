## Title
feat(api): the conductor's HTTP API reads projects and their queues, behind one operator's bearer token

## Why
Issue #143 (rewrite: `issue-audit/updates/143.md`, Scope 1 and "Proposed child issues" 1:
"`GET /projects`, `GET /projects/{id}` and `GET /projects/{id}/jobs` are built from the same
application queries `vibey status --json` uses. Token auth, bound to 127.0.0.1"). Runbook 12 puts
the app in `infrastructure/api/` and says the API "is the root artifact"
(`docs/runbooks/expansion/12-integration-surfaces.md:25-36`); today it is "Not started"
(`:3-9`). The coordinator's ruling for this wave: the API serves **one operator** (loopback, one
token). Multi-user access is #143's open question 1 and #89's identity work, and this lane does not
answer it.

Family first (sub-doctrine 10.e, `src/vibey_tools/gh/docs/doctrines.md:417`): the token comparison
is `vibey_bootstrap.security.compare_secrets` (`src/vibey_tools/bootstrap/vibey_bootstrap/security/__init__.py:20-29`)
and request timing is `vibey_bootstrap.fastapi_middleware.install_middleware` (`fastapi_middleware/__init__.py:19-142`).
The family's `verify_api_key_header` (`security/__init__.py:32-63`) is **not** used, and the call
site says why: FastAPI reads every parameter of a dependency function as a query parameter, so
`Depends(verify_api_key_header)`, the pattern `auth/api_key.py:5-11` documents, lets an
unauthenticated caller pass `?env_var=<any variable>&x_api_key=<its value>` or
`?env_var=<unset>&fail_open_when_unset=true` and be let in (verified 2026-09-22 against fastapi
0.141.1: both return 200, and the `X-API-Key` header itself is never read). That is a capability
gap, closed in the family, not here. Importing `vibey_bootstrap` from `infrastructure/` is allowed
(`.importlinter:20-25`, `:35-53`).

Lands after `roadmap-143-api-read-projects-p1` (FastAPI installed) and `-p3` (the query).

## Required behaviour
1. New package `src/vibey/infrastructure/api/`:
   - `__init__.py`: the provenance header (copied from `src/vibey/infrastructure/tracker/__init__.py:1`)
     and the docstring `"""The conductor's HTTP API (#143, runbook 12)."""`.
   - `interfaces/__init__.py`: header, docstring
     `"""Seams the conductor's HTTP API declares. Interfaces declare; they never consume."""`, and a
     re-export of `ConductorApiInterface` with `__all__`, in the shape of
     `src/vibey/infrastructure/tracker/interfaces/__init__.py`.
   - `interfaces/app_interface.py`: header; `@runtime_checkable class ConductorApiInterface(Protocol)`
     with `def build(self) -> FastAPI: ...` (docstring: "A fresh ASGI app serving the conductor's
     routes; every route requires the bearer token.").
2. New `src/vibey/infrastructure/api/app.py` (header on line 1):
   - `_BEARER: Final = HTTPBearer(auto_error=False)` (from `fastapi.security`).
   - `class ConductorApi` with class constants `TITLE: ClassVar[str] = "vibey conductor API"`,
     `VERSION: ClassVar[str] = "1.0.0"` and `DESCRIPTION: ClassVar[str]` = line 1 of this file with
     its leading `# ` removed, byte-for-byte (the committed OpenAPI schema carries it, lane
     `roadmap-143-api-openapi-drift`).
   - `__init__(self, *, status: ProjectStatusQueryInterface, token: str, page_size: int) -> None`:
     `not token.strip()` raises `ValueError("the API token is empty; the conductor API never serves without one")`;
     `page_size < 1` raises `ValueError(f"page_size must be at least 1, got {page_size}")`.
     Later lanes add optional keyword collaborators (`gates=`, `events=`) whose routes `build`
     registers only when they are given; keep `build` a flat sequence of `add_api_route` calls so
     they can.
   - `def build(self) -> FastAPI`:
     - `app = FastAPI(title=self.TITLE, version=self.VERSION, description=self.DESCRIPTION, dependencies=[Depends(self._authorize)])`;
     - `install_middleware(app, probe_paths=(), fire_alerts=False)` with the comment
       `# 10.e: the family's request timing. Alerts stay off: they page a hosted alert channel.`;
     - `app.add_exception_handler(UnknownProject, self._not_found)`;
     - `app.add_api_route("/projects", self._list_projects, methods=["GET"], operation_id="listProjects", summary="The newest projects, newest first")`;
     - `app.add_api_route("/projects/{project_id}", self._project, methods=["GET"], operation_id="getProject", summary="One project's status, the object `vibey status --json` prints")`;
     - `app.add_api_route("/projects/{project_id}/jobs", self._project_jobs, methods=["GET"], operation_id="getProjectJobs", summary="A project's queue depth by job state")`;
     - `return app`.
   - `async def _authorize(self, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_BEARER)]) -> None`:
     when `credentials is None` or `not compare_secrets(credentials.credentials, self._token)`, raise
     `HTTPException(status_code=401, detail="missing or wrong bearer token", headers={"WWW-Authenticate": "Bearer"})`.
     Above it, the written reason for not using `verify_api_key_header` (the Why's paragraph, in
     three comment lines, ending "capability gap: the family has no bearer-token dependency").
   - `async def _not_found(self, request: Request, exc: Exception) -> JSONResponse`: returns
     `JSONResponse(status_code=404, content={"detail": str(exc)})`.
   - `async def _list_projects(self, limit: int | None = None) -> dict[str, object]`:
     `wanted = self._page_size if limit is None else limit`; outside `1..page_size` raise
     `HTTPException(status_code=422, detail=f"limit must be between 1 and {self._page_size}")`;
     return `{"projects": [self._status.summary_json(r) for r in await self._status.recent(limit=wanted)]}`.
   - `async def _project(self, project_id: UUID) -> dict[str, object]`: returns
     `self._status.status_json(await self._status.status(project_id))`.
   - `async def _project_jobs(self, project_id: UUID) -> dict[str, object]`: returns
     `self._status.queue_json(project_id, await self._status.queue_depth(project_id))`.
   Unauthenticated requests get 401 before any parameter is validated (FastAPI solves the app-level
   dependency first; checked against 0.141.1).
3. `.importlinter`: add `    vibey.infrastructure.api.interfaces` to the `source_modules` of
   `[importlinter:contract:infrastructure-interfaces-declare-only]`, after
   `vibey.infrastructure.tracker.interfaces` (`:129`).

## Where to change
- New `src/vibey/infrastructure/api/__init__.py`, `app.py`, `interfaces/__init__.py`, `interfaces/app_interface.py`.
- `.importlinter` (one line).
- New `tests/infrastructure/api/__init__.py` (the provenance header only, like
  `tests/infrastructure/db/__init__.py`) and `tests/infrastructure/api/test_read_routes.py`.

## Acceptance criteria
- [ ] Every route answers 401 with `WWW-Authenticate: Bearer` without the token, with a wrong one,
      and with the right one under the `Basic` scheme.
- [ ] `GET /projects/{id}` returns exactly `ProjectStatusQuery.status_json(...)` for that project.
- [ ] `grep -n "verify_api_key_header" src/vibey/infrastructure/api/app.py` finds only the comment.
- [ ] `uv run lint-imports` passes with the new contract line.
- [ ] 100% branch coverage of `src/vibey/infrastructure/api/` and of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/api/test_read_routes.py`. `TOKEN = "test-token-0123456789"`. A module helper
`_api(tmp_path, page_size=2)` builds `ProjectStatusQuery(projects=InMemoryProjectRepository(clock=clock), jobs=FakeJobRepository(), health=FakeEngineHealthRepository(), ledger=InMemoryLedger())`
(fakes from `tests/fakes/projects.py`, `queue.py`, `engines.py`, `ledger.py`; `FakeClock` from
`tests/fakes/system.py`), seeds projects with `asyncio.run(...)`, and returns the query, the
`ConductorApi(status=query, token=TOKEN, page_size=page_size)` and `TestClient(api.build())`
(`from fastapi.testclient import TestClient`). Tests are plain (sync) functions.
- `test_every_route_refuses_a_request_without_the_bearer_token` — parametrized over the three paths
  (a random project id) and the headers `{}`, `{"Authorization": "Bearer wrong"}`,
  `{"Authorization": f"Basic {TOKEN}"}`: status 401, `headers["www-authenticate"] == "Bearer"`,
  body `{"detail": "missing or wrong bearer token"}`.
- `test_projects_lists_the_newest_first_within_the_page_size` — projects `a`, `b`, `c` one second
  apart; `GET /projects` names `["c", "b"]`; `?limit=1` names `["c"]`; `?limit=0` and `?limit=3`
  are 422 with detail `"limit must be between 1 and 2"`; each item has exactly the eight
  `summary_json` keys.
- `test_a_project_route_answers_with_the_status_json` — body equals
  `query.status_json(asyncio.run(query.status(pid)))`.
- `test_the_jobs_route_answers_with_the_queue_depth` — one enqueued job: body is
  `{"project_id": str(pid), "queue_depth": {...}}` with `"ready": 1`.
- `test_an_unknown_project_is_404_and_named` — both project routes for `UUID(int=5)`: 404,
  `{"detail": "unknown project 00000000-0000-0000-0000-000000000005"}`.
- `test_a_malformed_project_id_is_422`.
- `test_the_api_refuses_an_empty_token_or_page_size` — `ConductorApi(..., token="  ", ...)` and
  `page_size=0` raise `ValueError` with the two messages.
- `test_the_schema_names_the_bearer_scheme_and_the_operations` — `client.app.openapi()` has
  `components.securitySchemes == {"HTTPBearer": {"type": "http", "scheme": "bearer"}}`, the three
  operation ids, and `info.description == ConductorApi.DESCRIPTION`, which starts with `"Made with ❤️ by [Vibey]"`.
- `test_the_api_satisfies_its_interface` — `isinstance(api, ConductorApiInterface)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/api
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/infrastructure/api
    uv run coverage report --include='src/vibey/infrastructure/api/*' --fail-under=100
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/infrastructure
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- `vibey server` and the uvicorn seam (`-p5`, `-p6`, `-p7`); gates (`roadmap-143-api-gates-p2`);
  the event stream (`roadmap-143-api-event-stream-p3`); the committed schema (`roadmap-143-api-openapi-drift`).
- Scoped or multiple tokens, hashed tokens at rest, CORS, non-loopback serving (#143 open question 1).
- Fixing `vibey_bootstrap.security.verify_api_key_header` (a vibey-bootstrap lane; reported to the coordinator).
- Recording request latency into the ledger (gaps.md §D1's surfaces lane).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the agent-surface trees. Do not
  push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
