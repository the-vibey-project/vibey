## Title
feat(cli)!: bare `vibey install` installs everything the host's default OS needs; flags narrow or extend it

## Why
The operator's standard (2026-09-22): the installer must always automatically install
everything needed to run vibey on the default OSes. Today, `vibey install` with no flag exits 2
("choose an install target", `src/vibey/cli/main.py:1169-1171`), and `--postgres` is its only
target.

#391 asks for `vibey install` with no target to install the sovereign local stack, with
`--yes`, `--no-model` and `--model NAME`, and with a confirmation, showing the download size,
before the model pull. R33 (#380) and R34 (specs/rmq-r34-defaults-flip.md:38) expect
`vibey install --rabbitmq`.

The stack is declared in the catalogue and built by `LocalStackComposition`
(`src/vibey/bootstrap.py`, lane installer-composition), behind the `LocalStackFactory` port.
This lane is the command. Substitution happens at the declared seam: the typer context's `obj`,
which Click's `CliRunner.invoke(..., obj=...)` sets. Nothing is patched (sub-doctrine 9.b).

## Required behaviour
1. `src/vibey/cli/local_install.py` declares two classes.
   - `class LocalStackPresenter`, with the method
     `lines(report: LocalStackReport, hints: Mapping[str, str] | None = None) -> list[str]`:
     - The first line is `f"host: {report.host_label}"`.
     - Each report gives `f"{r.key:<16} {r.state.value.upper():<14} {r.detail}"`.
     - A non-ok report with a fix adds `f"{'':<16} fix: {r.fix}"`.
     - An ok report with a hint adds `f"{'':<16} then: {hint}"`.
     - The last line is `"all ready"`, or f"{not_ok} of {total} not ready".
   - `class InstallCommand`:
     ```python
     def __init__(self, factory: LocalStackFactory, *, catalogue: LocalStackCatalogueInterface | None = None,
                  presenter: LocalStackPresenterInterface | None = None,
                  confirm: Callable[[str], bool] | None = None) -> None
     def run(self, *, only: tuple[str, ...] = (), extra: tuple[str, ...] = (), no_model: bool = False,
             model: str = DEFAULT_LOCAL_MODEL, yes: bool = False, check: bool = False) -> tuple[list[str], int]
     ```
     The default `confirm` calls `typer.confirm(prompt, default=False)` and returns False on
     `typer.Abort`. `run` does the following, in this order:
     1. Resolve `specs = catalogue.resolve(factory.host(), only=only, extra=extra, exclude=("model",) if no_model else ())`.
        `UnknownDependency` returns `([str(exc)], EXIT_USAGE)`.
     2. When `factory.host()` is None and `only` is empty, return:
        `[f"{factory.host_label()} is not a default OS for `vibey install` (Arch Linux, macOS); `vibey install --postgres` still installs PostgreSQL here"], 1`.
     3. When `specs` is empty, return `["nothing to install"], 0`.
     4. `installer = factory.build(specs, model=model)`.
     5. `check=True` returns `presenter.lines(installer.check()), 0 or 1`. The code is 0 only
        when every report is ok.
     6. When the host is not None and `factory.precondition()` returns a line, return
        `[line], 1`.
     7. When a spec has key `model`, `yes` is False, and the model's check report is not ok:
        - ask `confirm(f"Pull the local model {model} ({size})?")`, where `size` is
          `DEFAULT_LOCAL_MODEL_DOWNLOAD` for the default model and "download size unknown"
          otherwise;
        - on a decline, re-resolve with model excluded, rebuild the installer, and prepend the
          line `f"model: not pulling {model}; pull it later with `vibey install --only model`"`.
     8. `report = installer.install()`. Return the presenter lines (with a prepended note if
        any). Hints are `{s.key: r.hint for s in specs if (r := s.recipe(factory.host())) and r.hint}`.
        The code is 0 when `report.ok`, else 1.
   - A module constant `WITH_HELP` lists the opt-in keys and groups, read from the catalogue at
     import: "Add an opt-in dependency or group: " followed by the sorted names of the
     non-default entries and their groups.
2. `src/vibey/cli/interfaces/local_install_interface.py` declares two `@runtime_checkable`
   Protocols: `LocalStackPresenterInterface` and `InstallCommandInterface`.
3. `install` in `src/vibey/cli/main.py:1155-1182` becomes a thin wrapper. The body echoes each
   line and raises `typer.Exit(code)` when the code is non-zero.
   ```python
   @app.command("install")
   def install(
       ctx: typer.Context,
       only: Annotated[list[str] | None, typer.Option("--only", help="Install only this dependency or group (repeatable)")] = None,
       with_: Annotated[list[str] | None, typer.Option("--with", help=WITH_HELP)] = None,
       postgres: Annotated[bool, typer.Option("--postgres", help="Same as --only postgres")] = False,
       ollama: Annotated[bool, typer.Option("--ollama", help="Same as --only ollama --only model")] = False,
       rabbitmq: Annotated[bool, typer.Option("--rabbitmq", help="Same as --only rabbitmq")] = False,
       yes: Annotated[bool, typer.Option("--yes", "-y", help="Pull the model without asking")] = False,
       no_model: Annotated[bool, typer.Option("--no-model", help="Do not pull the local model")] = False,
       model: Annotated[str, typer.Option("--model", help="Model to pull (default: gpt-oss:20b)")] = DEFAULT_LOCAL_MODEL,
       check: Annotated[bool, typer.Option("--check", help="Report each dependency; install nothing")] = False,
   ) -> None:
       """Install everything vibey needs on this machine (Arch Linux or macOS)."""
       factory = ctx.obj if isinstance(ctx.obj, LocalStackFactory) else LocalStackComposition()
   ```
   The alias flags append their keys to `only`, in the order `postgres`, `ollama` (with
   `model`), `rabbitmq`. If R33 (#380) already added `--rabbitmq` to this command, keep a single
   `--rabbitmq` with this meaning. `_postgres_status_line` stays, because doctor uses it.
4. Existing tests in `tests/cli/test_operational_commands.py` change by edit, not rewrite:
   - `test_install_requires_an_explicit_postgres_target` (:863-867) becomes
     `test_install_rejects_an_unknown_dependency`. It invokes
     `["install", "--only", "no-such-dependency"]` without `obj`, asserts exit 2 and the
     `known:` list, and so covers the real-composition branch without running any command.
   - `test_install_postgres_reports_success` and `_failure` (:870-910) use `obj=FakeFactory(...)`
     from `tests/cli/test_local_install.py` instead of `patch(...)`, keeping their assertions:
     "READY" and "VIBEY_PG_URL"; "no package manager" with exit 1.

## Where to change
- New files:
  - `src/vibey/cli/local_install.py`
  - `src/vibey/cli/interfaces/local_install_interface.py`
  - `tests/cli/test_local_install.py`
- Edit `src/vibey/cli/main.py` `install`. Use edit_file; the file is 1761 lines.
- Edit the three tests named above.
- Copy the command-plus-presenter pattern from `src/vibey/cli/ledger_search.py:54-226`.
- The provenance line 1 is copied from `src/vibey/cli/ledger_search.py`.

## Acceptance criteria
- [ ] Bare `vibey install` on a fake macOS factory installs every default key in declaration
      order and exits 0 when all are READY. A FAILED dependency gives exit 1 and a `fix:` line.
- [ ] `--only docker` installs docker alone.
- [ ] `--with cluster` adds helm, kubectl and minikube, and minikube pulls in docker.
- [ ] `--postgres`, `--ollama` and `--rabbitmq` narrow as documented.
- [ ] `--no-model` never builds the model installer.
- [ ] `--model qwen3:8b` passes that name to `factory.build`.
- [ ] The model prompt shows "14 GB" for the default. `input="n\n"` skips the pull and prints
      the later-pull line, and `input="y\n"` pulls. `--yes` never prompts.
- [ ] `--check` never calls `install()`.
- [ ] On a non-default host, bare install exits 1 with the `--postgres` line, and
      `--postgres` still runs.
- [ ] A precondition line, such as the Homebrew one, exits 1 before any install.
- [ ] Every test injects a fake through `obj=`. No `patch(` appears in `tests/cli/test_local_install.py`.
- [ ] 100% branch coverage of `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/cli/test_local_install.py` defines these fakes:
- `FakeStackInstaller(reports)`, which records `install_calls` and `check_calls`;
- `FakeFactory(host, label, precondition, reports_by_key)`, whose `build()` records the specs
  and model and returns a `FakeStackInstaller` for them.

The tests:
- `test_bare_install_installs_the_default_stack_in_order`
- `test_failed_dependency_exits_one_with_its_fix`
- `test_only_and_with_narrow_and_extend_the_selection`
- `test_alias_flags_select_postgres_ollama_and_rabbitmq`
- `test_no_model_and_model_name_reach_the_factory`
- `test_model_pull_asks_first_and_honours_the_answer`: parametrized over y, n and EOF.
- `test_yes_skips_the_question`
- `test_check_reports_without_installing`
- `test_non_default_host_points_at_postgres`
- `test_precondition_stops_before_installing`
- `test_presenter_prints_fixes_hints_and_a_summary`
- `test_command_and_presenter_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Doctor, which is lane installer-doctor.
- New catalogue entries.
- Docs and CHANGELOG, which the docs wave owns. The commit footer carries the break.

Commit as `feat(cli)!: ...` with the footer
`BREAKING CHANGE: bare vibey install now installs the default local stack instead of exiting 2`.
Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
