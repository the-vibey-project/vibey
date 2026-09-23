## Title
feat(cli): `vibey server` serves the conductor's HTTP API on loopback, for the one operator holding its token

## Why
Issue #143 (rewrite: `issue-audit/updates/143.md`, Scope 1 "`vibey server`", "Proposed child
issues" 1). Runbook 12: "Not started: `vibey server` (FastAPI)" (`docs/runbooks/expansion/12-integration-surfaces.md:8-9`),
"new `vibey server` CLI entry" (`:27-28`). The pieces exist after the earlier lanes: the query
(`-p3`), the app (`-p4`), the `[api]` table (`-p5`) and the serving seam (`-p6`). This lane is the
command that composes them. It reads `[api]` from `./vibey.toml` the way `vibey doctor` reads its
local-engine settings from the working directory (`src/vibey/cli/main.py:256-265`), refuses to start
without a token (fail closed: an API without its token is never served), and hands the app to the
serving seam taken from `CliComposition`, so tests never open a socket (sub-doctrine 9.b,
`src/vibey_tools/gh/docs/doctrines.md:349`). Loopback only is the coordinator's single-operator
ruling; #143's open question 1 stays open.
Lands after `roadmap-143-api-read-projects-p3`, `-p4`, `-p5`, `-p6`, `fakes-cli-composition` and
`fakes-cli-operational-1`.

## Required behaviour
1. `src/vibey/cli/composition.py` and `src/vibey/cli/interfaces/composition_interface.py`
   (lanes `fakes-job-wakeup`, `fakes-cli-composition`): `CliComposition` gains a keyword-only field
   `api_server: Callable[[], ApiServerInterface]` whose production default is the class
   `UvicornServer` (`vibey.infrastructure.api.server`), in the same shape as the `postgres_local`
   field (a class used as a zero-argument factory); `CliCompositionInterface` mirrors it.
2. `src/vibey/cli/main.py`:
   - import `ApiConfig`, `parse_api` and `parse_toml_string` from `vibey.domain.config` with the other
     `vibey.domain` imports (`:39-57`);
   - after `_local_engines_from_toml` (`:256-265`), add
     ```python
     def _api_settings_from_toml(root: Path | None = None) -> ApiConfig:
         """The `[api]` table `vibey server` reads: `./vibey.toml`, or every default without one.

         Module-level, like `_local_engines_from_toml` above: it is the CLI's own reading of the
         working directory. Only `[api]` is parsed, because the server serves every project and a
         `vibey.toml` beside it need not describe one (`parse_config` requires `[project]`).
         """
         path = (root or Path.cwd()) / "vibey.toml"
         data = parse_toml_string(path.read_text()) if path.is_file() else {}
         return parse_api(data)
     ```
   - a new command, placed after `status` (`:709-790`):
     ```python
     @app.command("server")
     def server() -> None:
         """Serve the conductor's HTTP API on loopback, for the one operator who holds its token.

         `[api]` in ./vibey.toml sets bind (127.0.0.1 or ::1), port, token_env and page_size.
         The token is read from the environment variable token_env names, never from a file.
         """
         with guard():
             settings = _api_settings_from_toml()
         token = os.environ.get(settings.token_env, "").strip()
         if not token:
             typer.echo(
                 f"the API token is unset: export {settings.token_env} (the variable "
                 "[api] token_env names), then run `vibey server` again",
                 err=True,
             )
             raise typer.Exit(EXIT_USAGE)

         async def serve() -> None:
             from vibey.application.project_status import ProjectStatusQuery
             from vibey.infrastructure.api.app import ConductorApi

             composition = CliComposition.current()
             async with composition.open_app() as resources:
                 status = ProjectStatusQuery(
                     projects=resources.projects,
                     jobs=resources.jobs,
                     health=resources.engine_health_repo,
                     ledger=resources.ledger,
                 )
                 api = ConductorApi(status=status, token=token, page_size=settings.page_size)
                 shown = f"[{settings.bind}]" if ":" in settings.bind else settings.bind
                 typer.echo(f"serving the vibey API on http://{shown}:{settings.port}")
                 await composition.api_server().serve(
                     api.build(), host=settings.bind, port=settings.port
                 )

         with guard():
             asyncio.run(serve())
     ```
   The token is never echoed or logged. A bad `[api]` table is a `ConfigError`, which `guard`
   renders and exits 3 (`src/vibey/cli/errors.py:84-95`); a missing token exits 2 (`EXIT_USAGE`, `:34`).

## Where to change
- `src/vibey/cli/composition.py`, `src/vibey/cli/interfaces/composition_interface.py`, `src/vibey/cli/main.py`
  (all with `edit_file`).
- New `tests/cli/test_server_command.py`; append to `tests/cli/test_composition.py`.

## Acceptance criteria
- [ ] With no token, `vibey server` exits 2, names the variable, and the serving seam is never called.
- [ ] With the token, the seam is asked to serve on `("127.0.0.1", 8765)`, and the app it was handed
      refuses `GET /projects` without the token (401) and lists the seeded project with it.
- [ ] `[api]` in `./vibey.toml` moves the bind, port, token variable and page size; a non-loopback bind exits 3.
- [ ] 100% branch coverage of `src/vibey/cli/`.

## Tests to write first (TDD)
`tests/cli/test_server_command.py` (default tier: the `memory_app` fixture and `ops.invoke` from
`tests/cli/ops_support.py`, imported as `tests/cli/test_ops_status_ledger.py` imports them;
`RecordingApiServer` from `tests/fakes/api.py`; `TestClient` from `fastapi.testclient`;
`monkeypatch.chdir(tmp_path)` in every test; `TOKEN = "test-token-0123456789"`; the composition is
`ops.invoke(memory_app, "server", api_server=lambda: recorder)`):
- `test_server_refuses_to_start_without_its_token` — `monkeypatch.delenv("VIBEY_API_TOKEN", raising=False)`;
  exit 2; `"export VIBEY_API_TOKEN"` in `result.output`; `recorder.calls == []`.
- `test_server_serves_the_read_api_on_loopback_with_the_operators_token` — `setenv("VIBEY_API_TOKEN", TOKEN)`;
  a project `served` created through `async with memory_app.open_app() as r:`; exit 0;
  `"serving the vibey API on http://127.0.0.1:8765"` in the output; `recorder.calls == [("127.0.0.1", 8765)]`;
  `TestClient(recorder.apps[0]).get("/projects").status_code == 401`; with
  `{"Authorization": f"Bearer {TOKEN}"}` the names are `["served"]`.
- `test_server_reads_its_table_from_vibey_toml` — `tmp_path / "vibey.toml"` holds
  `[api]\nbind = "::1"\nport = 9001\ntoken_env = "MY_VIBEY_TOKEN"\npage_size = 1\n`; `setenv("MY_VIBEY_TOKEN", TOKEN)`;
  `recorder.calls == [("::1", 9001)]`; `"http://[::1]:9001"` in the output; `GET /projects?limit=2`
  with the token is 422.
- `test_server_refuses_a_bind_beyond_loopback` — `[api]\nbind = "0.0.0.0"\n`; token set; exit 3;
  `"api.bind: must be a loopback address"` in the output; `recorder.calls == []`.
Append to `tests/cli/test_composition.py`:
- `test_the_api_server_defaults_to_uvicorn` — `CliComposition().api_server is UvicornServer`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_server_command.py tests/cli/test_composition.py tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Command-line flags for the bind or port (the `[api]` table is the declared source, 12.c).
- Gates and the event stream on the server (`roadmap-143-api-gates-p2`, `roadmap-143-api-event-stream-p3`
  add one constructor argument each to this command's `ConductorApi(...)`).
- A chart or systemd unit for the server; TLS; non-loopback serving (#143 open question 1).
- `docs/reference/cli.md` (the docs wave), CHANGELOG.md, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and
  the agent-surface trees. Do not push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
