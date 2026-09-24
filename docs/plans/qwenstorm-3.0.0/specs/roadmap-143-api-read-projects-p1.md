## Title
build(deps): the conductor declares FastAPI and uvicorn, the HTTP API's stack, at the versions uv.lock already holds

## Why
Issue #143 (rewrite: `issue-audit/updates/143.md`, Scope 1 "`vibey server`: an HTTP API over the
application layer", "Proposed child issues" 1). Runbook 12 names the stack: "FastAPI app in
`infrastructure/api/` (new `vibey server` CLI entry)" (`docs/runbooks/expansion/12-integration-surfaces.md:25-31`).
FastAPI is not a dependency of the conductor: it appears only in the `bootstrap-all` extra
(`pyproject.toml:140-141`), and the lanes' environment (`uv sync --extra dev`) does not install it
(checked 2026-09-22 in a lane venv: `import fastapi` raises `ModuleNotFoundError`). uvicorn, starlette,
sse-starlette and httpx are installed, but only transitively (`claude-agent-sdk` -> `mcp`, read from
`uv.lock`), and a package the code imports must be declared, not borrowed from another package's
dependency list. Both are already locked: `fastapi 0.141.1` (`uv.lock:1559-1560`) and
`uvicorn 0.52.4` (`uv.lock:5405-5406`). Sub-doctrine 12.c (`src/vibey_tools/gh/docs/doctrines.md:455`):
what the code needs is declared in the repository.

Declaring them changes `uv.lock`'s record of vibey's requirements, so this lane runs `uv lock`,
which **needs network** (with an empty cache `uv lock --offline` fails on `hatchling`; verified
2026-09-22). Every other #143 lane is offline and lands after this one.

## Required behaviour
1. `pyproject.toml` `[project] dependencies` (`:19-51`): after `"platformdirs>=4.0",` (`:50`) and before
   the closing `]` (`:51`), add exactly these three lines:
   ```
       # the conductor's HTTP API (`vibey server`, #143): FastAPI, served by uvicorn
       "fastapi>=0.110",
       "uvicorn>=0.30",
   ```
   The `bootstrap-all` extra (`:123-156`) is unchanged.
2. Run `uv lock`. The resolution must not move any version: `uv.lock` gains exactly four lines and
   loses none (measured 2026-09-22 in a copy of this tree: "Resolved 279 packages"):
   - in vibey's `[[package]]` `dependencies = [` list: `    { name = "fastapi" },` and `    { name = "uvicorn" },`;
   - in vibey's `[package.metadata] requires-dist = [` list:
     `    { name = "fastapi", specifier = ">=0.110" },` and `    { name = "uvicorn", specifier = ">=0.30" },`.
   If `uv lock` changes any other line (a version, a hash, a new package), stop: do not commit, and
   report the diff in your verdict.
3. New `tests/meta/test_api_dependencies.py` (the provenance header on line 1, copied byte-for-byte from
   `tests/meta/test_shipped_trees_are_reachable.py:1`). Module docstring: the conductor's API stack is
   declared, not borrowed from another package's requirements; module-level test functions follow
   `tests/meta/test_shipped_trees_are_reachable.py`'s written reason (pytest collects `test_*`
   functions, and the class rule is about production code). `REPO = Path(__file__).resolve().parents[2]`.

## Where to change
- `pyproject.toml` (three lines, with `edit_file`), `uv.lock` (by `uv lock` only, never by hand).
- New `tests/meta/test_api_dependencies.py`.
- No file under `src/`.

## Acceptance criteria
- [ ] `git diff --numstat -- uv.lock` prints `4	0	uv.lock`.
- [ ] `uv lock --check` exits 0.
- [ ] `uv run python -c "import fastapi, uvicorn; print(fastapi.__version__, uvicorn.__version__)"` prints `0.141.1 0.52.4`.
- [ ] The two new tests pass, and `tests/meta/test_shipped_trees_are_reachable.py` still passes.

## Tests to write first (TDD)
`tests/meta/test_api_dependencies.py`:
- `test_the_api_stack_is_a_runtime_dependency` — `tomllib` reads `pyproject.toml`; `"fastapi>=0.110"`
  and `"uvicorn>=0.30"` are both in `data["project"]["dependencies"]`, and neither is only in an extra.
- `test_the_api_stack_is_importable` — `importlib.import_module` of `fastapi`, `uvicorn` and
  `fastapi.testclient` succeeds.

## Checks the lane must run (all must pass)
    # needs network (pypi.org, files.pythonhosted.org): re-resolves the workspace
    uv lock
    uv lock --check
    git diff --numstat -- uv.lock
    uv sync --extra dev
    uv run python -c "import fastapi, uvicorn; print(fastapi.__version__, uvicorn.__version__)"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/meta/test_api_dependencies.py tests/meta/test_shipped_trees_are_reachable.py
    # needs network: the advisory database
    uv run pip-audit

## Out of scope
- Any code that imports FastAPI or uvicorn (`roadmap-143-api-read-projects-p4`, `-p6`).
- `sse-starlette` (the event stream uses Starlette's own `StreamingResponse`); the `bootstrap-all` extra.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the agent-surface trees. Do not
  push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
