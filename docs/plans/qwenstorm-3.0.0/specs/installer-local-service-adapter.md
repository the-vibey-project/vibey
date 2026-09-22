## Title
feat(install): the local-service classes (PostgreSQL today) join the stack through one adapter

## Why
`PostgresLocalService` (src/vibey/infrastructure/postgres.py:134-397) stays the installer for
PostgreSQL. Its initdb, role and version rules are behaviour that catalogue data cannot
express. `vibey install` needs it to speak the stack's port, `DependencyInstaller` (lane
installer-orchestrator, `src/vibey/application/interfaces/local_install.py`).

Its `status()` and `install()` results already carry the fields a report needs:
- `PostgresStatus`: `ready`, `installed`, `detail` (postgres.py:57-68);
- `PostgresInstallResult`: `ok`, `changed`, `detail`, `status` (:81-89).

R33 (#380) plans a `RabbitMqLocalService` of the same shape. So one structural adapter serves
every such class (sub-doctrine 10.e: the family's own capability, used once), and there is no
per-service copy.

## Required behaviour
1. `src/vibey/infrastructure/interfaces/local_service_installer_interface.py` declares these
   `@runtime_checkable` structural Protocols:
   - `LocalServiceStatusLike`: properties `ready: bool`, `installed: bool`, `detail: str`;
   - `LocalServiceInstallResultLike`: properties `ok: bool`, `changed: bool`, `detail: str`,
     `status: LocalServiceStatusLike`;
   - `LocalServiceLike`: `status() -> LocalServiceStatusLike`, `install() -> LocalServiceInstallResultLike`;
   - `LocalServiceInstallerInterface(DependencyInstaller, Protocol)`.
2. `src/vibey/infrastructure/local_service_installer.py` declares:
   ```python
   class LocalServiceInstaller:
       def __init__(self, key: str, title: str, service: LocalServiceLike) -> None
   ```
   - `key` returns the key. The fix for every non-ready report is `f"vibey install --only {key}"`.
   - `check()` calls `service.status()` only:
     - `ready`: READY with `status.detail`;
     - not `installed`: MISSING with `status.detail`;
     - otherwise: STOPPED with `status.detail`.
   - `install()` calls `service.install()` only:
     - `ok`: READY with `result.detail` and `changed=result.changed`;
     - otherwise: FAILED with `result.detail` and `changed=result.changed`.
3. A real `PostgresLocalService` satisfies `LocalServiceLike` structurally. A test proves it
   with `isinstance`, without running any command. `PostgresLocalService(which=lambda _n: None)`
   constructed with a fake runner is enough.

## Where to change
- New files:
  - `src/vibey/infrastructure/local_service_installer.py`
  - `src/vibey/infrastructure/interfaces/local_service_installer_interface.py`
  - `tests/infrastructure/test_local_service_installer.py`
- Provenance line 1 is copied from postgres.py.
- Do not edit postgres.py.

## Acceptance criteria
- [ ] check maps ready to READY, not installed to MISSING, and installed-but-not-ready to
      STOPPED. Each non-ready report carries the fix.
- [ ] install maps ok to READY and not ok to FAILED, keeping `changed` and the detail.
- [ ] check never calls `install()`, and install never calls `status()` directly.
- [ ] Adapting a `PostgresLocalService` built with a fake `command_runner` and `which` reports
      MISSING when no client tools are found (postgres.py:163-174). No real subprocess runs.
- [ ] 100% branch coverage of `local_service_installer.py`.

## Tests to write first (TDD)
`tests/infrastructure/test_local_service_installer.py`, using in-file `FakeStatus`,
`FakeResult` and `FakeService` dataclasses:
- `test_check_maps_ready_missing_and_stopped`
- `test_install_maps_success_and_failure_and_keeps_changed`
- `test_check_does_not_install`
- `test_adapts_a_real_postgres_local_service_without_running_commands`
- `test_adapter_and_postgres_satisfy_the_protocols`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_local_service_installer.py tests/infrastructure/test_postgres_local.py tests/application/test_interfaces_convention.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/infrastructure/test_local_service_installer.py
    uv run coverage report --include='src/vibey/infrastructure/local_service_installer.py' --fail-under=100

## Out of scope
- Changing `PostgresLocalService`.
- RabbitMQ (see lane installer-broker-cache).
- The composition and the CLI.
- Docs.

Commit as `feat(install): ...`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
