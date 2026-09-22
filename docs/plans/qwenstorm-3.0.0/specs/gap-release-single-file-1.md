## Title
feat(cli): one executable can run every console script, chosen by the name it is run as or by --as

## Why
ADR-0019 (`docs/architecture/decisions/0019-installable-wherever-its-users-are.md:102-106`,
`:114-115`) makes a single-file executable the artifact that most channels point at.
ADR-0037 ships one distribution with twelve console scripts (`pyproject.toml:64-81`). One
single-file build per script would mean twelve copies of the same interpreter and libraries.
So the single file is one binary that dispatches on the name it was invoked as, the way
busybox does. Package managers install it once and link the other eleven names to it
(PKGBUILD `ln -s`, Homebrew `bin.install_symlink`). Windows shims cannot rely on symlinks,
so they pass the name explicitly (`vibey.exe --as claudeloop`, Scoop's `bin` alias).

This lane is only the dispatcher, a class with an interface (9.b, `src/vibey_tools/gh/docs/doctrines.md:349`),
under the `cli/` 100% floor. The build itself is `gap-release-single-file-2`.

## Required behaviour
1. New `src/vibey/cli/multicall.py` (provenance line 1), module docstring as in the Why.
   - `CONSOLE_SCRIPTS: Final[Mapping[str, str]] = MappingProxyType({...})` holds exactly
     `pyproject.toml:70-81`, in that order:
     - `vibey`: `vibey.cli.main:app`
     - `claudeloop`: `claudeloop.cli.app:main`
     - `codexloop`: `codexloop.cli.app:main`
     - `cursorloop`: `cursorloop.cli.app:main`
     - `agyloop`: `agyloop.cli.app:main`
     - `qwenloop`: `qwenloop.cli.app:main`
     - `opencodeloop`: `opencodeloop.cli.app:main`
     - `vibey-gh`: `vibey_gh.cli:main`
     - `vibey-skills`: `vibey_skills.cli:main`
     - `vibe-skills`: `vibey_skills.cli:deprecated_alias_main`
     - `vibey-bootstrap`: `vibey_bootstrap.contrib.scaffold:main`
     - `azbootstrap`: `vibey_bootstrap.contrib.scaffold:main_azbootstrap`
   - `DEFAULT_COMMAND: Final = "vibey"`.
   - `class UnknownCommand(ValueError)`.
   - `class EntryPointResolver` with `resolve(self, target: str) -> Callable[[], object]`. It
     splits `target` on `:`, imports the module with `importlib.import_module`, and returns
     the attribute. It resolves lazily, by string, so the CLI layer takes no static import of
     any tenant.
   - `class MultiCallDispatcher`, with
     `__init__(self, *, scripts: Mapping[str, str] = CONSOLE_SCRIPTS, resolver: EntryPointResolverInterface | None = None) -> None`
     (a `None` resolver becomes `EntryPointResolver()`), and:
     - `command_for(self, argv: Sequence[str]) -> tuple[str, list[str]]`:
       1. `invoked = PurePath(argv[0]).name if argv else DEFAULT_COMMAND`. If
          `invoked.lower().endswith(".exe")`, drop the last four characters.
       2. If `len(argv) >= 2 and argv[1] == "--as"`: with no `argv[2]`, raise
          `UnknownCommand("--as needs a command name")`. If `argv[2]` is not in `scripts`, raise
          `UnknownCommand(f"unknown command {argv[2]!r}")`. Otherwise return
          `(argv[2], list(argv[3:]))`.
       3. If `invoked in scripts`, return `(invoked, list(argv[1:]))`.
       4. Otherwise return `(DEFAULT_COMMAND, list(argv[1:]))`. A renamed download such as
          `vibey-2.1.0-linux-x86_64` runs `vibey`.
     - `main(self, argv: Sequence[str]) -> int`:
       - calls `command_for`. On `UnknownCommand`, it prints
         `f"vibey: {exc}; one of: {', '.join(self._scripts)}"` to stderr and returns 2;
       - resolves `scripts[name]`, saves `sys.argv`, sets `sys.argv = [name, *rest]`, and
         calls the target in `try` / `finally`, restoring `sys.argv`;
       - returns the target's result when it is an `int`, and 0 otherwise.
       - A `SystemExit` raised by the target (Typer's apps do this) propagates unchanged.
   - `MULTICALL: Final[MultiCallDispatcherInterface] = MultiCallDispatcher()`.
2. New `src/vibey/cli/interfaces/multicall_interface.py` (provenance line 1): `@runtime_checkable`
   `EntryPointResolverInterface` (`resolve`) and `MultiCallDispatcherInterface`
   (`command_for`, `main`), with docstrings. Standard library imports only.
3. `src/vibey/cli/interfaces/__init__.py`: import both, and add them to `__all__`, keeping
   both lists sorted (the file is 25 lines).

## Where to change
- New `src/vibey/cli/multicall.py`, new `src/vibey/cli/interfaces/multicall_interface.py`.
- `src/vibey/cli/interfaces/__init__.py` (edit_file).
- New `tests/cli/test_multicall.py` (provenance line 1). The resolver is substituted through
  the constructor: a small class in the test file, `_Recorder`, whose `resolve` returns a
  function that records `list(sys.argv)` and returns a scripted value. No patching.

## Acceptance criteria
- [ ] `dict(CONSOLE_SCRIPTS) == tomllib.load(pyproject)["project"]["scripts"]`, so a script
      renamed or added in `pyproject.toml` without updating this table fails the suite.
- [ ] `MULTICALL.main(["vibey", "--version"])` raises `SystemExit(0)` and prints
      `f"vibey {vibey.__version__}"` (a real call, no substitution).
- [ ] 100% branch coverage of `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/cli/test_multicall.py`:
- `test_the_table_is_the_manifests_console_scripts`
- `test_the_name_it_was_run_as_picks_the_script` (`["/usr/bin/claudeloop", "--version"]` gives `("claudeloop", ["--version"])`)
- `test_a_windows_exe_suffix_is_ignored` (`["C:/tools/codexloop.EXE", "run"]` gives `("codexloop", ["run"])`)
- `test_as_names_the_script_explicitly` (`["vibey.exe", "--as", "vibey-gh", "doctor"]` gives `("vibey-gh", ["doctor"])`)
- `test_as_without_a_name_or_with_an_unknown_one_exits_2_and_lists_the_choices` (capsys; both messages)
- `test_a_name_outside_the_table_runs_vibey` (`["vibey-2.1.0-linux-x86_64", "--help"]`)
- `test_an_empty_argv_runs_vibey`
- `test_the_target_sees_its_own_name_and_argv_is_restored`
- `test_an_int_result_is_the_exit_code_and_anything_else_is_zero`
- `test_system_exit_from_the_target_propagates`
- `test_the_real_vibey_prints_its_version`
- `test_the_real_resolver_imports_by_module_and_attribute` (`EntryPointResolver().resolve("vibey.cli.multicall:MultiCallDispatcher") is MultiCallDispatcher`)
- `test_the_defaults_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Building the single file (`gap-release-single-file-2`) and publishing it (`-3`).
- A later rename of a console script (for example `loops-rename`'s qwenloop to sovereignloop)
  updates this table in the same change; `test_the_table_is_the_manifests_console_scripts`
  makes it impossible to forget.
- Docs.

Commit as `feat(cli): a multi-call dispatcher for the single-file executable`. Do not push.

## Lane card
- **Depends on:** none.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
