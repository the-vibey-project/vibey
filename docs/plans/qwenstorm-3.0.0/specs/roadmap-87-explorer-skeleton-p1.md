## Title
feat(explorer): the `vibey-explorer` workspace tenant exists, stdlib-only, with its own suite, 100% floor and CI rows

## Why
Issue #87 (rewrite: `issue-audit/updates/87.md`, "Proposed child issues" 2: "the workspace tenant
skeleton (`src/vibey_tools/explorer`, pyproject, own gates per ADR-0022)"). Runbook 21
(`docs/runbooks/expansion/21-vibey-explorer.md:1-12`) designs discovery as "a new workspace package,
`vibey-explorer` (`src/vibey_tools/explorer`)", and nothing exists: `src/vibey_tools/` holds
`bootstrap`, `gh`, `skills` only. The workspace already admits it by glob
(`pyproject.toml:249-251`, `members = ["src/vibey_runners/*", "src/vibey_tools/*"]`), and
`tests/meta/test_tools_matrix_covers_every_package.py:59-78` demands a `tools` CI row for every
tenant with a pyproject and a `test`/`tests` directory (ADR-0022: every tenant keeps its own suite
and gates). Sub-doctrine 10.e (`src/vibey_tools/gh/docs/doctrines.md:417`): the explorer is family
code, stdlib-only like vibey-gh (`src/vibey_tools/gh/pyproject.toml:28-30`), so it adds no
dependency. This lane creates the empty, gated tenant; shipping it inside the one `vibey`
distribution (ADR-0037) is `roadmap-87-explorer-skeleton-p2`.

## Required behaviour
1. `src/vibey_tools/explorer/pyproject.toml`, exactly:
   ```toml
   [build-system]
   requires = ["hatchling>=1.27"]
   build-backend = "hatchling.build"

   [project]
   name = "vibey-explorer"
   version = "0.1.0"
   description = "Finds open-source work this system can finish, with provenance, and proposes it for a human to accept."
   requires-python = ">=3.12"
   license = "MIT"
   authors = [{ name = "Adam Matthew Steinberger", email = "adam@matthewsteinberger.com" }]
   # Stdlib only, like vibey-gh: every dependency is a party who can be pressured (10.a).
   dependencies = []

   [project.optional-dependencies]
   dev = ["pytest>=7.4", "pytest-cov>=4.1", "mypy>=1.8"]

   [tool.hatch.build.targets.wheel]
   packages = ["vibey_explorer"]

   [tool.pytest.ini_options]
   testpaths = ["test"]
   addopts = ["--cov=vibey_explorer", "--cov-branch", "--cov-report=term-missing", "--cov-fail-under=100"]

   [tool.mypy]
   python_version = "3.12"
   strict = true
   packages = ["vibey_explorer"]
   ```
   (`license = "MIT"` with no `license-files`, as `src/vibey_runners/qwen/pyproject.toml:11` does.)
2. `src/vibey_tools/explorer/vibey_explorer/__init__.py`: the provenance header line (copied from
   `src/vibey_tools/gh/vibey_gh/__init__.py:1`), then a docstring of 3–6 lines naming runbook 21's
   two constraints (capability-first selection; an unsolicited PR spends someone else's time), then
   `__version__ = "0.1.0"`.
3. `src/vibey_tools/explorer/vibey_explorer/py.typed` (empty).
4. `src/vibey_tools/explorer/test/test_package.py` (provenance header):
   - `test_the_version_is_declared_once` — `vibey_explorer.__version__` equals the `[project]
     version` read from the tenant's `pyproject.toml` with `tomllib`.
   - `test_the_package_imports_nothing_outside_the_standard_library` — walk every `.py` under
     `vibey_explorer/` with `ast`, collect top-level import names, and assert each is in
     `sys.stdlib_module_names` or is `vibey_explorer`.
5. `.github/workflows/ci.yml`, `tools` matrix: three rows after the last `vibey-skills` row
   (`ci.yml:266-270`), in the inline form vibey-gh uses (`ci.yml:236-243`):
   ```yaml
             - {package: vibey-explorer, dir: src/vibey_tools/explorer, python: "3.12",
                install: 'pip install -e ".[dev]"',
                static: 'python -m mypy', test: 'python -m pytest -q'}
             - {package: vibey-explorer, dir: src/vibey_tools/explorer, python: "3.13",
                install: 'pip install -e ".[dev]"', test: 'python -m pytest -q'}
             - {package: vibey-explorer, dir: src/vibey_tools/explorer, python: "3.14",
                install: 'pip install -e ".[dev]"', test: 'python -m pytest -q'}
   ```
   Match the surrounding indentation exactly.
6. `deploy/docker/Dockerfile`: after `COPY src/vibey_tools/skills/pyproject.toml ./src/vibey_tools/skills/`
   (`Dockerfile:137`) add `COPY src/vibey_tools/explorer/pyproject.toml ./src/vibey_tools/explorer/`,
   and in the comment at `Dockerfile:118-120` change "the ten tenant manifests" to "the eleven tenant
   manifests" — uv's workspace glob requires the manifest of every member directory
   (`Dockerfile:120-122`).
7. `uv lock` so the workspace lock names the new member; then `uv lock --check` passes.

## Where to change
- New: `src/vibey_tools/explorer/pyproject.toml`, `vibey_explorer/__init__.py`,
  `vibey_explorer/py.typed`, `test/test_package.py`.
- Edit: `.github/workflows/ci.yml` (three rows), `deploy/docker/Dockerfile` (one COPY line and one
  comment word), `uv.lock` (by `uv lock` only, never by hand).

## Acceptance criteria
- [ ] `cd src/vibey_tools/explorer && pip install -e ".[dev]" && python -m pytest -q` passes at 100% branch.
- [ ] `cd src/vibey_tools/explorer && python -m mypy` is clean.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_tools_matrix_covers_every_package.py` passes.
- [ ] `uv lock --check` passes.
- [ ] Root `uv run ruff check . && uv run ruff format --check .` pass (the new `.py` files are under `src/`).

## Tests to write first (TDD)
`src/vibey_tools/explorer/test/test_package.py`: `test_the_version_is_declared_once`,
`test_the_package_imports_nothing_outside_the_standard_library`.

## Checks the lane must run (all must pass)
    uv lock && uv lock --check      # needs the package index or a warm uv cache; if it cannot resolve offline, stop and report
    cd src/vibey_tools/explorer && python -m pip install -e ".[dev]" && python -m pytest -q && python -m mypy
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta/test_tools_matrix_covers_every_package.py tests/meta/test_shipped_trees_are_reachable.py

## Out of scope
- Shipping the tenant's package in the `vibey` wheel, its Dockerfile package COPY and `.vibey-gh.toml` content paths
  (`roadmap-87-explorer-skeleton-p2`); any discovery logic (`roadmap-87-explorer-candidate`,
  `roadmap-87-polite-fetcher`, `roadmap-87-scoring-skiplist`).
- CLAUDE.md's tenant list and other agent-surface docs (docs wave). CHANGELOG. Do not push;
  commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
