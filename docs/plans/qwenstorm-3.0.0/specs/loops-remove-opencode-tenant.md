## Title
chore(runners)!: remove the opencodeloop tenant; opencodeloop stays as a stub that names vscodeloop

ADR-0046 lane L39 (slug `loops-remove-opencode-tenant`).

## Why
ADR-0046 §9 (`specs/ADR-two-loops.md:294`): "**L39 then removes the tenant** and its packaging.
The console script `opencodeloop` remains through 3.x as a stub that exits 64, naming
`vscodeloop`." The Migration table (`:415`): "`opencodeloop` stays as an exit-64 stub … the stub
through 3.x". Sub-doctrine 8.b (#392): "the runner that drove OpenCode is retired once the VS Code
adapter carries its work"; the gate below is that evidence. After lane `loops-retire-opencode-id`
nothing in vibey runs the binary.

The tenant is `src/vibey_runners/opencode` (27 files at integration `d3b4a388`), packaged in the
root `pyproject.toml` (script `:76`, package `:207`, source `:232`), the image
(`deploy/docker/Dockerfile:133`, `:143`), the CI tools matrix (`.github/workflows/ci.yml:547-561`)
and the console-script contract (`:827`), and forbidden to shared code
(`src/vibey_runners/common/pyproject.toml`, "Shared code depends on no concrete runner").

## Required behaviour
0. **Gate (ADR-0046 §9: live conformance first).** Unless
   `grep "V-VS CONFORMANCE: PASS" STORM/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`
   prints a line naming Arch Linux and a line naming macOS, change nothing and report
   `gated: vscode has not passed live conformance on both OSes`.
1. `git rm -r src/vibey_runners/opencode`.
2. **The stub** — new `src/vibey/cli/retired.py` (+ `src/vibey/cli/interfaces/retired_interface.py`,
   `RetiredCommandInterface`):
   ```python
   class RetiredCommand:
       """A console script kept after its tool was retired, so a stale script or muscle memory
       gets an answer instead of a missing command (ADR-0046 §9: through 3.x)."""
       def __init__(self, *, name: str, replacement: str, reason: str,
                    stderr: TextIO | None = None) -> None
       def run(self) -> int  # writes one line to stderr, returns 64 (EX_USAGE)

   OPENCODELOOP = RetiredCommand(
       name="opencodeloop", replacement="vscodeloop",
       reason="sub-doctrine 8.b, ADR-0046 §9",
   )

   def opencodeloop_main() -> None:
       """Console-script entry point. A module function because a `[project.scripts]` target
       must be a callable attribute of a module; it only delegates to the class."""
       raise SystemExit(OPENCODELOOP.run())
   ```
   The line is `opencodeloop was retired (sub-doctrine 8.b, ADR-0046 §9); use vscodeloop`.
3. **Packaging**: root `pyproject.toml`: `opencodeloop = "vibey.cli.retired:opencodeloop_main"`
   (replacing `opencodeloop.cli.app:main`); drop `"src/vibey_runners/opencode/src/opencodeloop"`
   from `packages` and its `sources` line; update the comments' package counts; the script count
   is unchanged (the name stays). `deploy/docker/Dockerfile`: delete both opencode `COPY` lines.
   `.github/workflows/ci.yml`: delete the three `opencodeloop` rows; the console-script contract
   keeps `opencodeloop` (the stub is on PATH). `src/vibey_runners/common/pyproject.toml`: drop
   `"opencodeloop"` from `forbidden_modules`. `uv lock`.
4. `grep -rn "opencodeloop" --include=*.py --include=*.toml --include=*.yml --include=*.yaml src tests deploy .github pyproject.toml`
   then prints only the stub, its test, the script line, and the CI contract list.

## Where to change
- Delete: `src/vibey_runners/opencode/**`.
- New: `src/vibey/cli/retired.py`, `src/vibey/cli/interfaces/retired_interface.py`,
  `tests/cli/test_retired_opencodeloop.py`.
- Edit: `pyproject.toml`, `deploy/docker/Dockerfile`, `.github/workflows/ci.yml`,
  `src/vibey_runners/common/pyproject.toml`, `uv.lock`.

## Acceptance criteria
- [ ] `uv run opencodeloop run x` exits 64 and prints the line naming `vscodeloop` on stderr.
- [ ] `uv lock --check` passes; `uv run pytest -q -p no:cacheprovider tests/meta` passes (tools matrix, shipped trees reachable).
- [ ] The grep in behaviour 4 shows only the allowed hits.
- [ ] 100% branch coverage of `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/cli/test_retired_opencodeloop.py`:
- `test_the_stub_names_the_replacement_and_exits_64` (a `RetiredCommand` with an `io.StringIO` stderr)
- `test_the_entry_point_raises_system_exit_64` (`pytest.raises(SystemExit)` on `opencodeloop_main`)
- `test_the_console_script_points_at_the_stub` (reads root `pyproject.toml` with `tomllib`)
- `test_the_tenant_is_gone` (`not (REPO / "src/vibey_runners/opencode").exists()`)
- `test_retired_command_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv lock --check
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_retired_opencodeloop.py tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
    (cd src/vibey_runners/common && pip install -e ".[dev]" && lint-imports)

## Out of scope
- vibey-gh's failover default seat (`loops-gh-failover-seats`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally as `chore(runners)!: …` with a `BREAKING CHANGE:`
  footer: "the opencodeloop runner is removed; the opencodeloop command is a stub that exits 64
  and names vscodeloop (through 3.x)".

**Depends on:** `loops-retire-opencode-id`, `loops-vscodeloop-scaffold`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
