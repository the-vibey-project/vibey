## Title
feat(application): install the local stack in declared order, one idempotent report per dependency

## Why
`vibey install` must install everything on the default OS in one run. When one dependency
fails, the others must not be lost, and a dependent step must not run on a broken base. For
example, the model pull needs Ollama. The order and the `requires` edges are already declared
in the catalogue (lane installer-catalogue, `src/vibey/domain/local_stack.py`). This lane adds
the application-layer orchestrator and the ports the infrastructure installers implement.
Application code never imports infrastructure (import-linter contract
`application-independence`, `.importlinter:55`). Every class has its contract declared beside
it (ADR-0016, sub-doctrine 9.b). Every run is idempotent under replay (CLAUDE.md non-negotiable).

## Required behaviour
1. `src/vibey/application/interfaces/local_install.py` declares three `@runtime_checkable`
   Protocols.
   - `DependencyInstaller`:
     - `key` property (`str`);
     - `check() -> DependencyReport`, which changes nothing;
     - `install() -> DependencyReport`, which is idempotent: when already ready, it returns
       READY with `changed=False`.
   - `LocalStackInstallerInterface`: `check() -> LocalStackReport` and `install() -> LocalStackReport`.
   - `LocalStackFactory`:
     - `host() -> HostOs | None`;
     - `host_label() -> str`;
     - `precondition() -> str | None`;
     - `build(specs: tuple[DependencySpec, ...], *, model: str) -> LocalStackInstallerInterface`.

   Import `DependencyReport`, `DependencySpec`, `HostOs` and `LocalStackReport` from
   `vibey.domain.local_stack` at module level, not under `TYPE_CHECKING`, because
   `tests/application/test_interfaces_convention.py:121-132` resolves every annotation with
   `get_type_hints`.
2. `src/vibey/application/interfaces/__init__.py` imports the three Protocols and adds them to
   `__all__`, keeping it sorted. `test_interfaces_exports_every_protocol_it_declares` enforces
   this.
3. `src/vibey/application/local_install.py` declares `class LocalStackInstaller`:
   - `__init__(self, specs: tuple[DependencySpec, ...], installers: Mapping[str, DependencyInstaller], *, host_label: str)`
     raises `ValueError` naming any spec key with no installer.
   - `check()` returns `LocalStackReport(host_label, tuple(installers[s.key].check() for s in specs))`
     in spec order.
   - `install()` walks the specs in order.
     - When one of the spec's `requires` keys is also in this run and its report is not ok, it
       does not call the installer. It records
       `DependencyReport(key, DependencyState.SKIPPED, f"skipped: {k} is not ready", fix=f"vibey install --only {k}")`,
       where `k` is the first such key.
     - Otherwise it records `installers[key].install()`.
     - A failure never stops later, unrelated dependencies.
     - It returns a `LocalStackReport`.
4. Nothing in this lane performs I/O.

## Where to change
- New files:
  - `src/vibey/application/interfaces/local_install.py`
  - `src/vibey/application/local_install.py`
  - `tests/application/test_local_install.py`
- Edit `src/vibey/application/interfaces/__init__.py` (imports around :14-160, `__all__` at :162).
  Use edit_file, never write_file.
- The provenance line 1 is copied from `src/vibey/application/interfaces/system.py`.
- Copy the Protocol style from `src/vibey/application/interfaces/system.py`.

## Acceptance criteria
- [ ] Two fake installers run in order, and the stack report is ok when both are READY.
- [ ] When ollama fails, the model is SKIPPED with a fix naming ollama, and the model's
      installer is never called. An unrelated later dependency still runs.
- [ ] A requirement that is not part of this run does not cause a skip.
- [ ] `check()` calls only `check()` and never `install()`.
- [ ] A missing installer for a spec raises `ValueError`.
- [ ] `tests/application/test_interfaces_convention.py` passes.
- [ ] 100% branch coverage of `src/vibey/application/local_install.py`.

## Tests to write first (TDD)
`tests/application/test_local_install.py` uses an in-file `FakeInstaller(key, check_report, install_report)`
that records `calls`. The specs are built with `DependencySpec(...)` directly, not taken from
the catalogue, so later catalogue lanes cannot break these tests.
- `test_install_runs_every_installer_in_declared_order`
- `test_install_skips_a_dependent_whose_requirement_failed`
- `test_install_continues_past_a_failure_to_unrelated_dependencies`
- `test_a_requirement_outside_the_run_does_not_skip`
- `test_check_never_installs`
- `test_missing_installer_is_rejected`
- `test_fake_installer_and_orchestrator_satisfy_the_ports`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_local_install.py tests/application/test_interfaces_convention.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/local_install.py' --fail-under=100

## Out of scope
- The infrastructure installers: lanes installer-package-dependency,
  installer-local-service-adapter and installer-ollama.
- The composition: lane installer-composition.
- The CLI.
- Docs.

Commit as `feat(application): ...`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
