## Title
refactor(sovereignloop)!: the qwenloop runner becomes the sovereignloop package, and `qwenloop` stays as its legacy console script

ADR-0046 lane L18a (slug `loops-tenant-rename`).

## Why
Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-199`): "**`sovereignloop`** — what
`qwenloop` becomes". Draft ADR-0046's *Migration* table (`specs/ADR-two-loops.md`) renames the
package and tenant with "none: a clean import rename", and keeps the console script `qwenloop`
through all of 3.x with "a deprecation line on stderr". Its *Context* table lists the surfaces;
at integration `d3b4a388` they are:

| surface | where |
|---|---|
| tenant directory and package | `src/vibey_runners/qwen`, `src/vibey_runners/qwen/src/qwenloop` |
| tenant packaging | `src/vibey_runners/qwen/pyproject.toml:6` (name), `:38` (script), `:41`, `:62`, `:68`, `:72`, `:75`, `:81-98` (import-linter module names) |
| root console scripts | `pyproject.toml:75` |
| root wheel packages and sources | `pyproject.toml:206`, `:231` |
| container image | `deploy/docker/Dockerfile:132` and `:142` |
| CI tenant rows | `.github/workflows/ci.yml:531-546` (`package`, `dir`, `static` at `:535`) |
| console-script contracts | `ci.yml:827`; `.github/workflows/release.yml:148` |
| the shared code's forbidden list | `src/vibey_runners/common/pyproject.toml:80` |
| release content paths | `.vibey-gh.toml:52` (bound by `tests/meta/test_shipped_trees_are_reachable.py`) |
| the lock | `uv.lock:17`, `:4582-4584` |
| the CLI's own name | `src/vibey_runners/qwen/src/qwenloop/cli/app.py:81` (`typer.Typer(name="qwenloop")`), `:92` (`--version`) |

No module outside the tenant imports `qwenloop` (`git grep -n "import qwenloop\|from qwenloop" -- ':!src/vibey_runners/qwen'`
prints nothing). This lane renames **module paths only**. Environment names, the config and
cache directories, `.qwenloop/` run directories and the done marker keep their old spelling
here; lanes L18c and L18d rename each with its legacy read. The move is mechanical and wide,
so it is one checked script (8.h: plain Python, never `sed -i`, whose GNU and BSD forms differ).

## Required behaviour
1. The tenant lives at `src/vibey_runners/sovereign`, its package at
   `src/vibey_runners/sovereign/src/sovereignloop`, moved with `git mv` so history follows.
2. Inside the tenant (`.py`, `.toml`, `.json`, outside `docs/`), every `from qwenloop`,
   `import qwenloop`, quoted dotted module path `"qwenloop.` / `'qwenloop.` and
   `--cov=qwenloop` names `sovereignloop` instead. Nothing else inside the tenant changes in
   this lane (plain words, env names, paths, the marker, class names like `QwenConfig`).
3. The tenant's distribution is named `sovereignloop` and declares two console scripts:
   `sovereignloop = "sovereignloop.cli.app:main"` and
   `qwenloop = "sovereignloop.cli.app:legacy_main"`. The root `pyproject.toml` declares the
   same two, in place of today's single `qwenloop` line.
4. `sovereignloop/cli/app.py`:
   - `app = typer.Typer(name="sovereignloop", no_args_is_help=True, add_completion=False)`;
   - `--version` prints `sovereignloop <version>`;
   - after `main`, a constant and a function:
     ```python
     #: What the `qwenloop` console script prints first, on stderr (ADR-0046 Migration table).
     LEGACY_NAME_NOTICE = "qwenloop is a legacy name for sovereignloop (ADR-0046); it works through 3.x"


     def legacy_main(argv: list[str] | None = None) -> None:
         """The `qwenloop` console script: one deprecation line on stderr, then sovereignloop.

         Module-level for the same reason as `main`: a `[project.scripts]` entry point names a
         module attribute. It runs exactly what `main` runs; `argv` lets a test pass arguments
         without patching `sys.argv` (the console script passes none, so click reads
         `sys.argv`). Kept through 3.x; removed no earlier than 4.0.0, and only after
         `vibey doctor` reports no use (ADR-0046 Migration table).
         """
         typer.echo(LEGACY_NAME_NOTICE, err=True)
         app(args=argv)
     ```
5. Every packaging and CI reference in the *Why* table names the new directory and package:
   the Dockerfile's two `COPY` lines, the three CI rows (`package: sovereignloop`,
   `dir: src/vibey_runners/sovereign`, and the 3.12 row's `static` paths `src/sovereignloop`),
   the common tenant's forbidden list (`"sovereignloop"` in place of `"qwenloop"`), and
   `.vibey-gh.toml`'s content path. Both console-script contracts list `sovereignloop` **and**
   still list `qwenloop` (the legacy script ships through 3.x).
6. `uv.lock` is regenerated and `uv lock --check` passes.

## Where to change
Run everything from the repository root, in this order.

1. Move the tree:
   ```
   git mv src/vibey_runners/qwen src/vibey_runners/sovereign
   git mv src/vibey_runners/sovereign/src/qwenloop src/vibey_runners/sovereign/src/sovereignloop
   ```
2. Save the script in *The rename script* below with `write_file` as `loops_tenant_rename.py`
   at the repository root, run `python3 loops_tenant_rename.py`, then delete it
   (`rm loops_tenant_rename.py`). It must not be committed. Every assert names what it
   expected; if one fails, the tree differs from what this spec read: stop and report the
   assert's message.
3. `uv lock` (if it cannot reach an index, `uv lock --offline`; if both fail, stop and report),
   then `uv sync --extra dev`, which re-installs the workspace member under its new name.
4. Write the new test file (below). Its line 1 is the provenance line copied byte for byte from
   line 1 of `src/vibey_runners/sovereign/tests/test_cli.py`.
5. If `uv run ruff check .` reports only I001 (import order) in tenant files, run
   `uv run ruff check --fix --select I src/vibey_runners/sovereign`; if `ruff format --check`
   fails only on files this lane touched, run `uv run ruff format` on those files.

### The rename script
Copy it exactly as it stands (it starts at column 0).

```python
"""ADR-0046 lane L18a: rename the qwenloop tenant's package to sovereignloop.

Run from the repository root after the two `git mv` commands. Plain Python, so it runs the
same on Arch Linux and macOS. Every edit is asserted.
"""

import re
from pathlib import Path

ROOT = Path.cwd()
TENANT = ROOT / "src/vibey_runners/sovereign"
assert (TENANT / "src/sovereignloop/cli/app.py").is_file(), "run the two git mv commands first"
assert not (ROOT / "src/vibey_runners/qwen").exists(), "src/vibey_runners/qwen still exists"


def edit(path: Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    found = text.count(old)
    assert found == count, f"{path}: expected {count} of {old!r}, found {found}"
    path.write_text(text.replace(old, new), encoding="utf-8")


# 1. Module paths inside the tenant: imports, quoted dotted paths, and --cov.
IMPORT_FROM = re.compile(r"^(\s*)from qwenloop(?=[.\s])", re.MULTILINE)
IMPORT = re.compile(r"^(\s*)import qwenloop(?=[.\s]|$)", re.MULTILINE)
QUOTED = re.compile(r"""(["'])qwenloop\.""")
changed = []
for path in sorted(TENANT.rglob("*")):
    if not path.is_file() or path.suffix not in {".py", ".toml", ".json"}:
        continue
    if "docs" in path.relative_to(TENANT).parts:
        continue
    text = path.read_text(encoding="utf-8")
    new = IMPORT_FROM.sub(r"\1from sovereignloop", text)
    new = IMPORT.sub(r"\1import sovereignloop", new)
    new = QUOTED.sub(r"\1sovereignloop.", new)
    new = new.replace("--cov=qwenloop", "--cov=sovereignloop")
    if new != text:
        path.write_text(new, encoding="utf-8")
        changed.append(path.relative_to(ROOT).as_posix())
print("module paths rewritten in:", *changed, sep="\n  ")

# 2. The tenant's own pyproject (the quoted module paths were rewritten in step 1).
pyproject = TENANT / "pyproject.toml"
edit(pyproject, 'name = "qwenloop"', 'name = "sovereignloop"')
edit(
    pyproject,
    'qwenloop = "sovereignloop.cli.app:main"\n',
    'sovereignloop = "sovereignloop.cli.app:main"\n'
    'qwenloop = "sovereignloop.cli.app:legacy_main"\n',
)
edit(pyproject, 'packages = ["src/qwenloop"]', 'packages = ["src/sovereignloop"]')
edit(pyproject, 'packages = ["qwenloop"]', 'packages = ["sovereignloop"]')
edit(pyproject, 'source = ["src/qwenloop"]', 'source = ["src/sovereignloop"]')
edit(pyproject, 'root_package = "qwenloop"', 'root_package = "sovereignloop"')
for line in pyproject.read_text(encoding="utf-8").splitlines():
    if "qwenloop" in line:
        assert (
            "github.com/the-vibey-project/qwenloop" in line
            or line == 'qwenloop = "sovereignloop.cli.app:legacy_main"'
        ), f"unexpected qwenloop left in the tenant pyproject: {line}"

# 3. The CLI: its own name, its version line, and the legacy console script.
app = TENANT / "src/sovereignloop/cli/app.py"
edit(app, 'typer.Typer(name="qwenloop", ', 'typer.Typer(name="sovereignloop", ')
edit(app, 'typer.echo(f"qwenloop {__version__}")', 'typer.echo(f"sovereignloop {__version__}")')
LEGACY = '''def main() -> None:
    app()


#: What the `qwenloop` console script prints first, on stderr (ADR-0046 Migration table).
LEGACY_NAME_NOTICE = "qwenloop is a legacy name for sovereignloop (ADR-0046); it works through 3.x"


def legacy_main(argv: list[str] | None = None) -> None:
    """The `qwenloop` console script: one deprecation line on stderr, then sovereignloop.

    Module-level for the same reason as `main`: a `[project.scripts]` entry point names a
    module attribute. It runs exactly what `main` runs; `argv` lets a test pass arguments
    without patching `sys.argv` (the console script passes none, so click reads
    `sys.argv`). Kept through 3.x; removed no earlier than 4.0.0, and only after
    `vibey doctor` reports no use (ADR-0046 Migration table).
    """
    typer.echo(LEGACY_NAME_NOTICE, err=True)
    app(args=argv)
'''
edit(app, "def main() -> None:\n    app()\n", LEGACY)

# 4. Root packaging.
root = ROOT / "pyproject.toml"
edit(
    root,
    'qwenloop = "qwenloop.cli.app:main"\n',
    'sovereignloop = "sovereignloop.cli.app:main"\n'
    'qwenloop = "sovereignloop.cli.app:legacy_main"\n',
)
edit(
    root,
    '    "src/vibey_runners/qwen/src/qwenloop",\n',
    '    "src/vibey_runners/sovereign/src/sovereignloop",\n',
)
edit(
    root,
    '"src/vibey_runners/qwen/src/qwenloop" = "qwenloop"\n',
    '"src/vibey_runners/sovereign/src/sovereignloop" = "sovereignloop"\n',
)
edit(root, '    # qwenloop\n    "platformdirs>=4.0",', '    # sovereignloop\n    "platformdirs>=4.0",')

# 5. The container image.
docker = ROOT / "deploy/docker/Dockerfile"
edit(
    docker,
    "COPY src/vibey_runners/qwen/pyproject.toml ./src/vibey_runners/qwen/\n",
    "COPY src/vibey_runners/sovereign/pyproject.toml ./src/vibey_runners/sovereign/\n",
)
edit(
    docker,
    "COPY src/vibey_runners/qwen/src/qwenloop/ ./src/vibey_runners/qwen/src/qwenloop/\n",
    "COPY src/vibey_runners/sovereign/src/sovereignloop/"
    " ./src/vibey_runners/sovereign/src/sovereignloop/\n",
)

# 6. CI and release: the tenant rows and both console-script contracts.
ci = ROOT / ".github/workflows/ci.yml"
edit(
    ci,
    "          - package: qwenloop\n            dir: src/vibey_runners/qwen\n",
    "          - package: sovereignloop\n            dir: src/vibey_runners/sovereign\n",
    count=3,
)
edit(
    ci,
    "static: 'mypy --strict src/qwenloop && lint-imports && bandit -q -r src/qwenloop'",
    "static: 'mypy --strict src/sovereignloop && lint-imports && bandit -q -r src/sovereignloop'",
)
edit(ci, "agyloop qwenloop opencodeloop; do", "agyloop sovereignloop qwenloop opencodeloop; do")
release = ROOT / ".github/workflows/release.yml"
edit(release, "agyloop qwenloop; do", "agyloop sovereignloop qwenloop; do")

# 7. The shared runner code may import no concrete runner, under its new name.
common = ROOT / "src/vibey_runners/common/pyproject.toml"
edit(common, '    "opencodeloop",\n    "qwenloop",\n]', '    "opencodeloop",\n    "sovereignloop",\n]')

# 8. The release derivation's content paths.
vibey_gh = ROOT / ".vibey-gh.toml"
edit(vibey_gh, '  "src/vibey_runners/qwen/src/",\n', '  "src/vibey_runners/sovereign/src/",\n')
print("L18a edits applied")
```

**Stop rule.** If a tenant test fails for any reason other than a module path this script
should have rewritten, stop and report it; do not edit test logic.

## Acceptance criteria
- [ ] `test ! -e src/vibey_runners/qwen && test -d src/vibey_runners/sovereign/src/sovereignloop`.
- [ ] `git grep -nE "^\s*(from|import) qwenloop\b" -- src tests scripts` prints nothing.
- [ ] `git grep -n "[\"']qwenloop\." -- src/vibey_runners/sovereign` prints nothing.
- [ ] `git grep -n "vibey_runners/qwen" -- . ':!docs' ':!*.md' ':!*.mdc'` prints nothing.
- [ ] `git grep -n "src/qwenloop" -- .github deploy pyproject.toml src/vibey_runners/sovereign/pyproject.toml` prints nothing.
- [ ] `sovereignloop --version` prints `sovereignloop 0.2.0`; `qwenloop --version` prints the same on stdout and the notice on stderr (run both with `uv run`).
- [ ] The tenant suite passes at its 100% floor; its mypy, import-linter and bandit gates pass; `uv lock --check` passes; `tests/meta` passes.

## Tests to write first (TDD)
`src/vibey_runners/sovereign/tests/test_legacy_entry_point.py`:
- `test_the_notice_names_both_names_and_the_window`: `LEGACY_NAME_NOTICE == "qwenloop is a legacy name for sovereignloop (ADR-0046); it works through 3.x"`.
- `test_legacy_main_warns_on_stderr_then_runs_sovereignloop` (`capsys`): `with pytest.raises(SystemExit) as exited: legacy_main(["--version"])`; `exited.value.code == 0`; `capsys.readouterr().err.strip() == LEGACY_NAME_NOTICE`; `.out.strip() == f"sovereignloop {__version__}"`.
- `test_the_app_is_named_sovereignloop`: `app.info.name == "sovereignloop"`.
- `test_the_tenant_declares_both_console_scripts`: `tomllib` reads `Path(__file__).resolve().parents[1] / "pyproject.toml"`; `project.scripts == {"sovereignloop": "sovereignloop.cli.app:main", "qwenloop": "sovereignloop.cli.app:legacy_main"}` and `project.name == "sovereignloop"`.

No test patches anything; `capsys` is pytest's own capture.

## Checks the lane must run (all must pass)
    uv lock --check
    uv sync --extra dev
    (cd src/vibey_runners/sovereign && uv run --extra dev python -m pytest -q -p no:cacheprovider)
    (cd src/vibey_runners/sovereign && uv run --extra dev python -m mypy --strict src/sovereignloop && uv run --extra dev lint-imports && uv run --extra dev bandit -q -r src/sovereignloop)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta
    uv run sovereignloop --version
    uv run qwenloop --version
    git grep -nE "^\s*(from|import) qwenloop\b" -- src tests scripts
    git grep -n "vibey_runners/qwen" -- . ':!docs' ':!*.md' ':!*.mdc'
    git status --short

The two `git grep` lines must print nothing, and `git status --short` must not list
`loops_tenant_rename.py`. The tenant's `pytest` carries its own 100% floor (`addopts
--cov=sovereignloop --cov-fail-under=100`). The `image` CI job proves the Dockerfile; locally
`tests/meta/test_shipped_trees_are_reachable.py` binds the root packages to its `COPY` lines.

## Out of scope
- Environment names, the config path, the model cache, run directories and the done marker
  (lanes `loops-tenant-legacy-env` L18c and `loops-tenant-legacy-paths` L18d).
- Class names (`QwenConfig`, `QwenloopComposition`), the `qwenloop-verdict` fence name, the
  tenant's description and URLs, and user-facing messages other than `--version`.
- vibey's descriptor binary (L18d) and the engine id (L06).
- The tenant's `README.md`, `AGENTS.md` and `docs/`, the root CLAUDE.md, AGENTS.md, GEMINI.md,
  CHANGELOG.md, docs/, ADRs, `.cursor/` and the other skill trees (the docs wave).
- Do not push or change remotes. Commit locally with the Title as the subject and this footer:
  `BREAKING CHANGE: the runner's Python package is sovereignloop (import sovereignloop); the qwenloop console script remains through 3.x and prints a deprecation line.`

**Depends on:** `loops-engine-id-sovereignloop`, `fakes-tenant-qwen-2`, `default-model-p3`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
