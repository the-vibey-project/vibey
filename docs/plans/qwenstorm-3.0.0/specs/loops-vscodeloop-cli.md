## Title
feat(vscodeloop): the vscodeloop command — run, resume, doctor, prompt, stop, wind-down

ADR-0046 lane L20g (slug `loops-vscodeloop-cli`).

## Why
ADR-0046 §8 (`specs/ADR-two-loops.md:267-270`) gives vscodeloop the family verbs `run`,
`resume`, `doctor`, `prompt` and `stop`, and the exit codes 0, 1, 75 and 78. vibey invokes it
through `build_argv` (`src/vibey/infrastructure/engines/argv.py:10-30`, integration
`d3b4a388`): `vscodeloop run <plan> --run-id <id> [--paid] --max-turns <n> --cwd <worktree>`
and `vscodeloop resume <session> --run-id <id> …` (the descriptors of lane
`loops-vscode-engine-ids`, `resume_run_id_flag="--run-id"`). Preflight runs `vscodeloop --version`
and `vscodeloop doctor [--paid]`; conformance reads `vscodeloop run --help`. The CLI shape is
carried from `src/vibey_runners/opencode/src/opencodeloop/cli/app.py` (the eager `--version`
callback at `:30-43`) and from `specs/opencodeloop-parity-p1.md` behaviours 5, 9 and 13
(bounds from flag, then environment, then default; invalid value → exit 2; `wind-down`).

## Required behaviour
0. **Gate (ADR-0046 §8, CDD bounded divergence).** Before any edit run
   `grep -n "V-VS VERDICT: FEASIBLE" /private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
   If nothing matches, change nothing and report `gated: V-VS verdict is not FEASIBLE`.
1. **Seams** — `vscodeloop/cli/seams.py`: `@dataclass(frozen=True) class CliSeams` with
   `driver: Callable[[], EditorDriverInterface]`, `which: Callable[[str], str | None]` (default
   `shutil.which`), `environ: Mapping[str, str]` (default `os.environ`), `store: Callable[[], RunStoreInterface]`
   (default `FileRunStore`). `DEFAULT_SEAMS` uses `driver=UnconfiguredDriver`, a class in the same
   module implementing `EditorDriverInterface` whose `start` raises
   `DriverMisconfigured("no editor driver is configured; lane loops-vscodeloop-oss-driver provides it")`
   (its other methods are unreachable after that and raise the same). Commands read seams from
   `ctx.obj` when it is a `CliSeams`, else `DEFAULT_SEAMS` (so tests pass
   `CliRunner().invoke(app, [...], obj=CliSeams(...))`; no patching). Interface
   `vscodeloop/cli/interfaces/seams_interface.py` (`CliSeamsInterface`).
2. **Settings resolution** (a class `SettingsResolver` in `cli/app.py`'s sibling
   `cli/settings.py`, interface beside it): `resolve(*, paid: bool, environ, which) -> DriverSettings`:
   - editor: `VSCODELOOP_EDITOR` when set and non-empty, else the first of `codium`, `code` for
     which `which(name)` is not None (Arch's Code - OSS ships `code`, macOS VSCodium ships
     `codium`; the doctor's OSS check, lane `loops-vscodeloop-doctor`, refuses Microsoft's
     build), else raise `DriverMisconfigured("no Code - OSS editor on PATH (codium or code); set VSCODELOOP_EDITOR")`;
   - sovereign (`paid=False`): `base_url = VSCODELOOP_BASE_URL`, `model = VSCODELOOP_MODEL`,
     `provider = None`; either missing → `DriverMisconfigured("<NAME> is not set")`;
   - paid (`paid=True`): `provider = VSCODELOOP_PROVIDER`, `model = VSCODELOOP_MODEL`,
     `base_url = VSCODELOOP_BASE_URL or None`; provider or model missing → `DriverMisconfigured`.
3. **Commands** — `vscodeloop/cli/app.py`, `app = typer.Typer(name="vscodeloop", no_args_is_help=True, add_completion=False)`:
   - root callback with eager `--version` printing `vscodeloop <__version__>`.
   - `run PLAN [--run-id ID] [--cwd DIR=.] [--paid] [--max-turns N] [--max-seconds S] [--stall-timeout S]`:
     bounds from flag, then `VSCODELOOP_MAX_TURNS` / `VSCODELOOP_MAX_SECONDS` /
     `VSCODELOOP_STALL_TIMEOUT_SECONDS` (`typer.Option(..., envvar=...)`), then `RunBounds()`
     defaults; building `RunBounds` or parsing the run id inside `try` → `ValueError` exits 2 with
     the message on stderr. The run id defaults to `str(uuid.uuid4())`. A `DriverMisconfigured`
     raised by `SettingsResolver.resolve` is not printed and exited on directly: the command
     builds `RaisingDriver(exc)` (seams.py: a port implementation whose `start` raises the given
     exception) and `DriverSettings(editor="", model="", base_url=None, provider=None)`, and runs
     `SessionRunner(driver, store).run(...)` as usual, so the run is recorded (`meta.json`,
     `stop-summary.md`, terminal `failed` event) and exits 78 through the runner's misconfigured
     path (lane `loops-vscodeloop-runner`, behaviour 3 step 2). `UnconfiguredDriver` is
     `RaisingDriver` with the default message above. Always `raise typer.Exit(code=result.exit_code)`.
   - `resume SESSION_ID --run-id ID [--cwd] [--paid] [bounds…]`: the same with
     `session_id=SESSION_ID` and the family resume prompt
     `"Continue the assigned work from this session and complete any remaining work."`
     (opencodeloop's `RESUME_PROMPT`, `cli/app.py:18`).
   - `doctor [--paid]`: prints one line per check and exits 0 when every check passes, 1
     otherwise. In this lane the checks are: settings resolve (else print the
     `DriverMisconfigured` text, exit 78) and the editor answers `<editor> --version` (through
     an injected `run_version: Callable[[str], str | None]` seam in `CliSeams`, default runs
     `subprocess.run([editor, "--version"], capture_output=True, text=True, timeout=30)` and
     returns the first line or None). Lane `loops-vscodeloop-doctor` adds the OSS and
     loopback checks.
   - `prompt RUN_ID TEXT [--now] [--cwd]` → `store.write_prompt`; prints the path; exit 0.
   - `stop RUN_ID [--cwd]` → `store.request_stop`; `wind-down RUN_ID [--cwd]` → `store.request_wind_down`.
     An invalid run id exits 2.
   - `def main() -> None: app()`.
4. **Packaging**: tenant `pyproject.toml` gains `[project.scripts] vscodeloop = "vscodeloop.cli.app:main"`;
   root `pyproject.toml` `[project.scripts]` (`:69-81` at `d3b4a388`) gains
   `vscodeloop = "vscodeloop.cli.app:main"` and the comment's script count goes up by one;
   `.github/workflows/ci.yml` "Image contract - every console script is on PATH" (`:827`) adds
   `vscodeloop` to the `for tool in …` list. `uv lock` if the lock changes.

## Where to change
- New: `vscodeloop/cli/__init__.py`, `cli/app.py`, `cli/seams.py`, `cli/settings.py`,
  `cli/interfaces/__init__.py`, `cli/interfaces/seams_interface.py`,
  `cli/interfaces/settings_interface.py`; `tests/test_cli.py`.
- Edit: tenant `pyproject.toml`; root `pyproject.toml`; `.github/workflows/ci.yml`.

## Acceptance criteria
- [ ] `vscodeloop --version` prints `vscodeloop 0.1.0`.
- [ ] `run` with a `FakeEditorDriver` that finishes exits 0; wind-down exits 75; misconfigured exits 78; a failure exits 1.
- [ ] `run --max-turns 0` and `VSCODELOOP_MAX_SECONDS=0 run …` exit 2 naming the field; `--run-id ../x` exits 2.
- [ ] The argv vibey builds (`run <plan> --run-id <uuid> --paid --max-turns 40 --cwd <dir>`) parses.
- [ ] Editor resolution prefers `VSCODELOOP_EDITOR`, then `codium`, then `code`; none → 78 with the message.
- [ ] `prompt`, `stop`, `wind-down` write the family inbox bodies.
- [ ] Tenant suite at 100% branch coverage; mypy strict, lint-imports, bandit pass; `uv run pytest -q -p no:cacheprovider tests/meta` passes.

## Tests to write first (TDD)
`src/vibey_runners/vscode/tests/test_cli.py` (typer `CliRunner`, `obj=CliSeams(...)` with
`FakeEditorDriver`, a dict `environ`, a `which` that answers from a dict, `tmp_path`):
- `test_version_is_eager`
- `test_run_exit_codes_follow_the_family` (parametrized: finished 0, wind-down 75, misconfigured 78, failed 1)
- `test_bounds_come_from_flag_then_env_then_default`
- `test_invalid_bounds_and_run_ids_exit_2`
- `test_vibey_built_argv_parses` (sovereign and `--paid`)
- `test_resume_passes_the_session_and_the_resume_prompt`
- `test_editor_resolution_order_and_missing_editor_exits_78`
- `test_sovereign_and_paid_settings_require_their_variables`
- `test_doctor_reports_settings_and_editor_version`
- `test_prompt_stop_and_wind_down_write_inbox_files`
- `test_default_seams_driver_is_unconfigured`
- `test_seams_and_resolver_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/vscode && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q
    cd src/vibey_runners/vscode && mypy --strict src/vscodeloop && lint-imports && bandit -q -r src/vscodeloop
    uv lock --check
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta
    uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"

## Out of scope
- The Code - OSS driver (`loops-vscodeloop-oss-driver`) and the OSS/loopback doctor checks
  (`loops-vscodeloop-doctor`).
- Any vibey-side change beyond the root console script and the image contract.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-vscodeloop-runner`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
