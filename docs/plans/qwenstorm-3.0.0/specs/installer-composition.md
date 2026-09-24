## Title
feat(bootstrap): compose the local-stack installer for this host in the composition root

## Why
The installer's parts exist:
- the catalogue (`vibey.domain.local_stack`);
- the host package and service runners;
- `CataloguePackageInstaller`, `LocalServiceInstaller` over `PostgresLocalService`, and
  `OllamaModelInstaller`;
- the orchestrator `LocalStackInstaller` and its `LocalStackFactory` port
  (`vibey.application.interfaces.local_install`).

Someone must choose, per catalogue entry, which installer serves it. CLAUDE.md names
`bootstrap.py` "the sole composition root" (layer map). ADR-0016 wants the class's contract
declared beside it, and `src/vibey/bootstrap_interface.py` is where composition-root contracts
live (:23). The CLI (lanes installer-cli and installer-doctor) then depends only on the
`LocalStackFactory` port. Its tests substitute a fake factory at that seam, not by patching
(sub-doctrine 9.b).

## Required behaviour
1. Append `class LocalStackComposition` to `src/vibey/bootstrap.py`:
   ```python
   def __init__(self, *, executor: CommandExecutorInterface | None = None,
                os_release_path: Path = Path("/etc/os-release"),
                environ: Mapping[str, str] | None = None,
                postgres: LocalServiceLike | None = None) -> None
   ```
   - It builds `self._executor = executor or SubprocessCommandExecutor()`, then
     `HostPackageRunner.for_this_host(self._executor, os_release_path=..., environ=...)`, then
     `HostServiceRunner(packages, self._executor)`, and sets
     `self._postgres = postgres or PostgresLocalService()`.
   - Construction runs no command.
   - `host()`, `host_label()` and `precondition()` delegate to the package runner.
   - `build(specs, *, model: str) -> LocalStackInstallerInterface` maps each spec by
     `spec.installer`:
     - `POSTGRES`: `LocalServiceInstaller(spec.key, spec.title, self._postgres)`;
     - `MODEL`: `OllamaModelInstaller(self._executor, model=model, key=spec.key)`;
     - `PACKAGE`: `CataloguePackageInstaller(spec, self.host(), packages, services)`.

     It returns `LocalStackInstaller(specs, installers, host_label=self.host_label())`.
2. `src/vibey/bootstrap_interface.py` gains
   `@runtime_checkable class LocalStackCompositionInterface(LocalStackFactory, Protocol)`,
   with a one-line docstring.
3. Nothing is executed at import time. `bootstrap.py`'s existing imports stay as they are, and
   the new imports go at module level beside them.

## Where to change
- `src/vibey/bootstrap.py`: append the class, and add imports near :1-60. The file is 962
  lines, so use edit_file only, never write_file.
- `src/vibey/bootstrap_interface.py`: add the Protocol.
- `tests/test_bootstrap.py`: append tests, and never rewrite it. The tests use:
  - `FakeCommandExecutor` from `tests/fakes/host.py`;
  - a `tmp_path` os-release file;
  - an in-file `FakePostgres` with `status()` and `install()` returning simple dataclasses with
    the fields named in `local_service_installer_interface.py`.

## Acceptance criteria
- [ ] With an Arch os-release, `build(LocalStackCatalogue().resolve(HostOs.ARCH), model="gpt-oss:20b")`:
  - maps postgres to `LocalServiceInstaller`, model to `OllamaModelInstaller` and ollama to
    `CataloguePackageInstaller`;
  - its `check()` runs only queries and probes against the fake executor, never
    `pacman -S` or `brew install`.
- [ ] Constructing `LocalStackComposition` runs no command: the fake executor's `calls` is
      empty.
- [ ] `host()`, `host_label()` and `precondition()` equal what
      `HostPackageRunner.for_this_host(...)` returns for the same os-release path and environ.
      Lane installer-host-runner already tests detection per OS. Here, assert only that the
      values are delegated, so the test passes on macOS and Linux alike. Do not patch
      `sys.platform`.
- [ ] `isinstance(LocalStackComposition(...), LocalStackCompositionInterface)` and
      `isinstance(..., LocalStackFactory)` hold.
- [ ] `uv run lint-imports` passes. bootstrap is outside the onion's layer containers
      (`.importlinter:28`).

## Tests to write first (TDD)
Append to `tests/test_bootstrap.py`:
- `test_local_stack_composition_runs_nothing_when_built`
- `test_local_stack_composition_maps_each_installer_kind`
- `test_local_stack_composition_check_runs_only_queries`
- `test_local_stack_composition_satisfies_the_factory_port`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/application/test_interfaces_convention.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- The CLI.
- Doctor.
- New catalogue entries.
- Docs.

Commit as `feat(bootstrap): ...`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
