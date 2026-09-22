## Title
feat(install): install any catalogue dependency from its declared recipe, idempotently

## Why
Most of what `vibey install` provides is one kind of thing: a package, sometimes a daemon, and
sometimes a readiness probe. That covers Ollama, RabbitMQ, Valkey, Docker, git, uv, llama.cpp,
the cluster tools, VS Code and the paid engine CLIs. ADR-0018 and sub-doctrine 12.c ask that
this be declared data served by one implementation, not a bespoke class per tool. The data is
the catalogue (lane installer-catalogue); the steps are the host package runner and the host
service runner (lanes installer-host-runner and installer-service-runner). This lane adds the
one `DependencyInstaller` (lane installer-orchestrator) that combines them for every entry
whose `installer` is `InstallerKind.PACKAGE`.

## Required behaviour
1. `src/vibey/infrastructure/package_dependency.py` declares `class CataloguePackageInstaller`:
   ```python
   def __init__(self, spec: DependencySpec, host: HostOs | None,
                packages: HostPackageRunnerInterface, services: HostServiceRunnerInterface) -> None
   ```
   - `key` returns `spec.key`. In every non-ready report, `fix` is `f"vibey install --only {spec.key}"`.
   - `check() -> DependencyReport` changes nothing. It decides in this order:
     - `spec.recipe(host)` is None: UNSUPPORTED, f"{title} has no recipe for {packages.host_label()}",
       with no fix;
     - `not packages.is_installed(recipe.package)`: MISSING, f"{title} is not installed";
     - no probe: READY, f"{title} is installed";
     - `services.probe(recipe.probe)`: READY, f"{title} is running";
     - otherwise: STOPPED, f"{title} is installed but `{' '.join(probe.argv)}` does not answer".
   - `install() -> DependencyReport`:
     1. Call `check()`. READY returns that report with `"; nothing to do"` appended and
        `changed=False`. UNSUPPORTED returns unchanged.
     2. `packages.ensure(recipe.package)`. When not ok, return FAILED with its detail.
     3. `services.run_steps(recipe.post_install)`. When not ok, return FAILED.
     4. If there is a service, and the probe is absent or not answering, call
        `services.start(recipe.service)`. When not ok, return FAILED.
     5. If there is a probe, and `services.wait_ready(recipe.probe)` is False, return FAILED
        with f"{title} did not answer `{argv}` within {timeout:g} s". When `timeout_hint` is
        set, add `"; " + timeout_hint`.
     6. Return READY, with detail f"{title} is installed and running" when there is a probe,
        otherwise f"{title} is installed". `changed` is True when any step changed.
2. `src/vibey/infrastructure/interfaces/package_dependency_interface.py` declares
   `@runtime_checkable class CataloguePackageInstallerInterface(DependencyInstaller, Protocol)`.
   This follows the named-contract pattern in `src/vibey/infrastructure/interfaces/class_contracts.py:50-53`.
3. Running `install()` twice on a ready host must produce no install, start or post-install
   command the second time. Only queries and probes run.

## Where to change
- New files:
  - `src/vibey/infrastructure/package_dependency.py`
  - `src/vibey/infrastructure/interfaces/package_dependency_interface.py`
  - `tests/infrastructure/test_package_dependency.py`
- Provenance line 1 is copied from `src/vibey/infrastructure/postgres.py`.
- Tests build real `HostPackageRunner` and `HostServiceRunner` objects over
  `FakeCommandExecutor` and `FakeTime` (`tests/fakes/host.py`), with `DependencySpec`s built
  inline. Do not use catalogue entries, so later data lanes cannot break these tests.

## Acceptance criteria
- [ ] check covers UNSUPPORTED, MISSING, READY without a probe, READY with a probe, and
      STOPPED.
- [ ] Arch install of a daemon runs these install, step and start commands, in order:
      `sudo pacman -S --needed --noconfirm x`, the post-install steps, then
      `sudo systemctl enable --now x`. The probe is then polled until it answers. Queries
      and probes may sit between the commands. The result is READY with `changed=True`.
- [ ] macOS install of a formula daemon uses `brew install` and then `brew services start`.
- [ ] Each failing step (ensure, steps, start, readiness timeout) returns FAILED with that
      step's detail and the `vibey install --only <key>` fix. The timeout detail carries the
      `timeout_hint`.
- [ ] Replay: a second `install()` on the now-ready fake host adds no install, start or step
      command.
- [ ] 100% branch coverage of `package_dependency.py`.

## Tests to write first (TDD)
`tests/infrastructure/test_package_dependency.py`:
- `test_check_reports_each_state`, parametrized over the five states.
- `test_install_on_arch_installs_runs_steps_starts_and_waits`
- `test_install_on_macos_uses_brew_and_brew_services`
- `test_install_of_a_ready_dependency_changes_nothing`
- `test_install_replayed_after_success_runs_no_install_command`
- `test_install_reports_each_failing_step`, parametrized over ensure, steps, start and
  timeout.
- `test_install_leaves_an_unsupported_host_alone`
- `test_installer_satisfies_the_port`: `isinstance` against `DependencyInstaller` and the
  named contract.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_package_dependency.py tests/infrastructure/test_host_services.py tests/infrastructure/test_host_packages.py tests/application/test_interfaces_convention.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/infrastructure
    uv run coverage report --include='src/vibey/infrastructure/package_dependency.py' --fail-under=100

## Out of scope
- PostgreSQL: it keeps `PostgresLocalService` (lane installer-local-service-adapter).
- The model pull: lane installer-ollama.
- Wiring into bootstrap: lane installer-composition.
- New catalogue entries.
- Docs.

Commit as `feat(install): ...`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
