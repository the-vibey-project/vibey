## Title
build(explorer): `vibey_explorer` ships inside the one `vibey` distribution, with its release paths and image context declared

## Why
Issue #87 (rewrite: `issue-audit/updates/87.md`, "Proposed child issues" 2). ADR-0037: the whole
tree ships as one `vibey` distribution — every tenant package is a package of the root wheel
(`pyproject.toml:196-243`: `[tool.hatch.build.targets.wheel] packages` and the explicit
`[tool.hatch.build.targets.wheel.sources]` mapping, whose comment explains why each root must be
named). `.vibey-gh.toml:47-65` lists every shipped prefix in `[version] content_paths` so a change to
it derives a release, and `tests/meta/test_shipped_trees_are_reachable.py:86-103` binds both the
content paths and the Dockerfile's COPY lines (`deploy/docker/Dockerfile:127-150`) to the wheel's
package list. `roadmap-87-explorer-skeleton-p1` created the tenant; this lane makes it ship.

## Required behaviour
1. `pyproject.toml`:
   - `[tool.hatch.build.targets.wheel] packages` (`:200-212`): append
     `"src/vibey_tools/explorer/vibey_explorer",` after `"src/vibey_tools/skills/src/vibey_skills",`.
   - `[tool.hatch.build.targets.wheel.sources]` (`:226-237`): append
     `"src/vibey_tools/explorer/vibey_explorer" = "vibey_explorer"`.
   - The comment at `:215-225` says "eleven prefixes"/"the eleven no longer overlap": make it
     "twelve".
2. `.vibey-gh.toml` `[version] content_paths` (`:47-65`): add `"src/vibey_tools/explorer/vibey_explorer/",`
   after `"src/vibey_tools/bootstrap/vibey_bootstrap/",`.
3. `deploy/docker/Dockerfile`: after `COPY src/vibey_tools/skills/src/vibey_skills/ ./src/vibey_tools/skills/src/vibey_skills/`
   (`Dockerfile:147`) add `COPY src/vibey_tools/explorer/vibey_explorer/ ./src/vibey_tools/explorer/vibey_explorer/`,
   and change the comment's "eleven package roots" (`Dockerfile:119`) to "twelve package roots".
4. `uv lock --check` still passes (no dependency changes; run `uv lock` only if it fails, and report).

## Where to change
- `pyproject.toml`, `.vibey-gh.toml`, `deploy/docker/Dockerfile`. Use `edit_file` for each insertion.
- No new test: the existing meta tests are the check.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_shipped_trees_are_reachable.py tests/meta/test_tools_matrix_covers_every_package.py` passes.
- [ ] `uv build --wheel -o "$TMPDIR/explorer-wheel"` produces a wheel containing `vibey_explorer/__init__.py`
      (`python -m zipfile -l "$TMPDIR"/explorer-wheel/*.whl | grep vibey_explorer/__init__.py`).
- [ ] `uv run python -c "import vibey_explorer; print(vibey_explorer.__version__)"` prints `0.1.0`.
- [ ] Root gates stay green (ruff, mypy on `src/vibey`, lint-imports).

## Tests to write first (TDD)
None new: `tests/meta/test_shipped_trees_are_reachable.py` fails before this lane only if the wheel
already names the package; run it after each edit.

## Checks the lane must run (all must pass)
    uv lock --check
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/meta
    uv build --wheel -o "$TMPDIR/explorer-wheel" && python -m zipfile -l "$TMPDIR"/explorer-wheel/*.whl | grep -q "vibey_explorer/__init__.py"

## Out of scope
- The tenant itself (`-p1`); any explorer logic; a console script (none is declared yet).
- The `image` CI job (it runs in CI, not in the lane). Docs, CHANGELOG. Do not push; commit locally
  with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
