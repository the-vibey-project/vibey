## Title
feat(api): a declared seam serves the conductor's API with uvicorn, and a recording twin stands in for it in tests

## Why
Issue #143 (rewrite: `issue-audit/updates/143.md`, Scope 1 "`vibey server`"). Serving binds a socket
on the host, so it is a driver seam: sub-doctrine 9.b (`src/vibey_tools/gh/docs/doctrines.md:349`)
wants a class with its interface beside it and substitution at that seam, and the operator's
standard wants a registered in-memory fake for it, so no default-tier test ever opens a port.
uvicorn is the ASGI server: declared by `roadmap-143-api-read-projects-p1` and locked at 0.52.4
(`uv.lock:5405-5406`). `log_config=None` keeps vibey's own logging (`src/vibey/cli/main.py:125`
configures it) instead of uvicorn's dictConfig, and uvicorn's `Server.serve` installs and restores
its own SIGINT/SIGTERM handlers, so Ctrl-C and a SIGTERM stop the server cleanly. Sub-doctrine 8.h
(`doctrines.md:326-333`): uvicorn runs the same on Arch Linux and macOS, and these tests touch no OS
facility. Lands after `roadmap-143-api-read-projects-p1` and `-p4` (the package).

## Required behaviour
1. New `src/vibey/infrastructure/api/interfaces/server_interface.py` (provenance header copied from
   `src/vibey/infrastructure/api/interfaces/app_interface.py:1`):
   - `@runtime_checkable class ServeableInterface(Protocol)` with
     `async def serve(self, sockets: list[socket.socket] | None = None) -> None: ...`
     (docstring: "What `uvicorn.Server` offers: serve until stopped.");
   - `@runtime_checkable class ApiServerInterface(Protocol)` with
     `async def serve(self, app: ASGIApp, *, host: str, port: int) -> None: ...`
     (`ASGIApp` from `starlette.types`; docstring: "Serves one ASGI app on one host and port until
     it is stopped.").
   Re-export both from `src/vibey/infrastructure/api/interfaces/__init__.py` and add them to `__all__`.
2. New `src/vibey/infrastructure/api/server.py` (header on line 1):
   ```python
   class UvicornServer:
       """Serves the conductor's API with uvicorn until Ctrl-C or SIGTERM stops it."""

       def __init__(
           self, *, server_factory: Callable[[uvicorn.Config], ServeableInterface] = uvicorn.Server
       ) -> None:
           self._server_factory = server_factory

       async def serve(self, app: ASGIApp, *, host: str, port: int) -> None:
           config = uvicorn.Config(app, host=host, port=port, log_config=None, lifespan="off")
           await self._server_factory(config).serve()
   ```
   plus the module-level conformance line `_CONFORMS: ApiServerInterface = UvicornServer()`
   (the pattern `src/vibey/domain/correlation.py:66-77` explains: the annotation is what makes mypy check the seam). This passes `mypy --strict`
   with `uvicorn.Server` as the default factory (checked 2026-09-22 against uvicorn 0.52.4).
3. New `tests/fakes/api.py` (header copied from `tests/fakes/__init__.py:1`):
   `class RecordingApiServer` implementing `ApiServerInterface`: `__init__` sets
   `self.calls: list[tuple[str, int]] = []` and `self.apps: list[ASGIApp] = []`;
   `async def serve(self, app, *, host, port)` appends `app` to `apps` and `(host, port)` to
   `calls`, then returns at once. Docstring: "Stands in for `UvicornServer`: records what it was
   asked to serve and never opens a socket."
4. `tests/fakes/registry.py` (lane `fakes-registry`): append `ApiServerInterface` to `DRIVER_SEAMS`
   and add `FakeRegistration(port=ApiServerInterface, build=RecordingApiServer)` to `REGISTRY`.

## Where to change
- New `src/vibey/infrastructure/api/server.py`, `src/vibey/infrastructure/api/interfaces/server_interface.py`;
  `src/vibey/infrastructure/api/interfaces/__init__.py` (re-export).
- New `tests/fakes/api.py`, `tests/fakes/test_fake_api.py`, `tests/infrastructure/api/test_server.py`;
  `tests/fakes/registry.py`.

## Acceptance criteria
- [ ] `UvicornServer().serve(app, host="127.0.0.1", port=8765)` hands uvicorn a `Config` whose
      `app is app`, `host == "127.0.0.1"`, `port == 8765`, `log_config is None`, `lifespan == "off"`,
      proven with a recording factory and no socket.
- [ ] `tests/fakes/test_port_parity.py` passes: the seam is registered, the fake matches its
      signature and is not a stub.
- [ ] 100% branch coverage of `src/vibey/infrastructure/api/`.

## Tests to write first (TDD)
`tests/infrastructure/api/test_server.py`:
- `test_uvicorn_is_handed_the_app_host_and_port_and_keeps_vibeys_logging` — a local class
  `_RecordingUvicorn` whose `__init__(self, config: uvicorn.Config)` stores the config in a class-level
  list and whose `async def serve(self, sockets=None)` records that it ran; `await
  UvicornServer(server_factory=_RecordingUvicorn).serve(FastAPI(), host="127.0.0.1", port=8765)`;
  assert the five `Config` attributes above and that `serve` ran once.
- `test_the_default_factory_is_uvicorns_server` — `UvicornServer()._server_factory is uvicorn.Server`.
- `test_the_server_satisfies_its_interface` — `isinstance(UvicornServer(), ApiServerInterface)`.
`tests/fakes/test_fake_api.py`:
- `test_the_recording_server_records_and_returns_at_once` — two `serve` calls record two apps and
  `[("127.0.0.1", 8765), ("::1", 9001)]`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/api tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/api/*' --fail-under=100
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The `vibey server` command (`roadmap-143-api-read-projects-p7`); TLS; binding anything but what
  the caller passes (the `[api]` table decides, `-p5`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the agent-surface trees. Do not
  push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
