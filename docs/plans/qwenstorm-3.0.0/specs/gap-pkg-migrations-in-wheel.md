## Title
fix(packaging): the wheel carries the migrations, so an installed vibey can bring its schema up to date

## Why
`build_app()` applies migrations on every start (`src/vibey/bootstrap.py:709`), and finds them
with `migrations_dir()`:

```python
def migrations_dir() -> Path:
    ...
    return Path(__file__).resolve().parents[2] / "migrations"
```
(`src/vibey/bootstrap.py:685-690`). That resolves in a source checkout (`<root>/migrations`) and
in the image (`/app/migrations`, `deploy/docker/Dockerfile:153`). The published wheel ships no
migrations: `[tool.hatch.build.targets.wheel.force-include]` (`pyproject.toml:238-243`) does not
list them. So `pip install vibey` resolves `site-packages/../../migrations`, which does not
exist. The single-file build (`gap-release-single-file-2`) and every package-manager channel
built on it inherit the same hole.

Sub-doctrine 2.b (`src/vibey_tools/gh/docs/doctrines.md:30`) asks the packaging to be honest
about what the install does not include. The schema is not something to leave out. This lane
ships the migrations inside the `vibey` package, and resolves them there first.

## Required behaviour
1. `pyproject.toml`, `[tool.hatch.build.targets.wheel.force-include]`: add
   `"migrations" = "vibey/migrations"` after `:243`
   (`"src/vibey_tools/gh/docs/javascripts/math.js" = "vibey_gh/templates/release/math.js"`).
2. `.vibey-gh.toml`, `[version] content_paths` (`:46-62`): add `  "migrations/",` immediately
   after `  "src/vibey/",` (`:47`). A change to a migration now ships, so it derives a
   release. `tests/meta/test_shipped_trees_are_reachable.py::test_every_shipped_tree_can_derive_a_release`
   requires it for the new force-include source, and
   `test_every_shipped_tree_is_in_the_container_build_context` is already satisfied by
   `COPY migrations/ ./migrations/` (`Dockerfile:153`).
3. `src/vibey/bootstrap.py`, `migrations_dir` (`:685-690`) becomes:
   ```python
   def migrations_dir(anchor: Path | None = None) -> Path:
       """Where the schema migrations are, resolved from this file (or `anchor`, for tests).

       An installed wheel and the single-file build carry them inside the package, at
       vibey/migrations, and that copy is used when it exists. A source checkout and the image
       keep them at the repository root (/app/src/vibey/bootstrap.py -> /app/migrations),
       which is the fallback. Derived in one place because two copies of this arithmetic
       would drift silently -- the image's layout depends on it."""
       here = (anchor if anchor is not None else Path(__file__)).resolve()
       packaged = here.parent / "migrations"
       if packaged.is_dir():
           return packaged
       return here.parents[2] / "migrations"
   ```
   Callers (`bootstrap.py:709`, `src/vibey/cli/main.py:1351-1374`) are unchanged.
4. No `src/vibey/migrations` directory is created in the tree. It exists only inside the
   built wheel.

## Where to change
- `pyproject.toml` (edit_file, one line).
- `.vibey-gh.toml` (edit_file, one line).
- `src/vibey/bootstrap.py` (edit_file only: `migrations_dir` alone).
- Append tests to `tests/test_bootstrap.py`. Do not rewrite it.

## Acceptance criteria
- [ ] `migrations_dir()` in the checkout equals `REPO / "migrations"`, and lists every `migrations/*.sql`.
- [ ] With `anchor = tmp_path/"site"/"vibey"/"bootstrap.py"`, `migrations_dir(anchor)` returns
      `tmp_path/"site"/"vibey"/"migrations"` when that directory exists. Without it, the
      function returns `anchor.resolve().parents[2] / "migrations"`.
- [ ] `uv build --wheel --out-dir "$TMPDIR/w" && python -c "import zipfile,glob;n=[x for x in zipfile.ZipFile(glob.glob('$TMPDIR/w/*.whl')[0]).namelist() if x.startswith('vibey/migrations/') and x.endswith('.sql')];print(len(n));assert n"`
      prints the same count as `ls migrations/*.sql | wc -l`.
- [ ] Every existing test in `tests/test_bootstrap.py`, `tests/meta/test_shipped_trees_are_reachable.py`
      and `tests/cli` passes unchanged.

## Tests to write first (TDD)
Append to `tests/test_bootstrap.py`:
- `test_migrations_resolve_to_the_checkout_in_a_source_tree`
- `test_migrations_packaged_beside_the_module_win_when_present`
- `test_migrations_fall_back_to_the_repository_root_when_not_packaged`
- `test_the_wheel_force_includes_the_migrations_into_the_package`: read `pyproject.toml`
  with `tomllib` and assert `force-include["migrations"] == "vibey/migrations"`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/meta tests/cli
    uv lock --check

## Out of scope
- The data-model page's description of the resolution (`docs/plans/data-model.md:959`; the docs wave).
- The cluster preflight's migration check (`src/vibey/infrastructure/cluster_preflight.py:271-277`)
  and the ORM migrator (`orm-migrator`). Both take the directory as an argument, and they
  receive the new resolution unchanged.
- The Dockerfile. It already copies `migrations/`.

Commit as `fix(packaging): ship the migrations in the wheel and resolve them there first`. Do not push.

## Lane card
- **Depends on:** none.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
