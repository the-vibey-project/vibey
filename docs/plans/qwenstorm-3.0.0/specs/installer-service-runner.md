## Title
feat(install): start declared services with systemd, brew services or the macOS app, and wait until they answer

## Why
Some dependencies are daemons: Ollama, RabbitMQ, Valkey and Docker. For those, being
installed is not enough; they must be started and must answer. Starting differs by OS:
- Arch Linux uses `systemctl enable --now <unit>` as root;
- a macOS Homebrew formula uses `brew services start <formula>`;
- Docker Desktop on macOS is an app that `open -g -a Docker` launches.

Today only `PostgresLocalService._service_start` exists (src/vibey/infrastructure/postgres.py:367-372),
and it does not know brew services or apps. The catalogue (lane installer-catalogue) declares
each daemon's `ServiceSpec`, `ProbeSpec` and privileged `post_install` steps as data
(sub-doctrine 12.c). This lane executes them.

The operator requires that the installer wait for Docker to answer `docker info`
(2026-09-22). So waiting is a bounded poll with an injected clock, never an unbounded loop.

## Required behaviour
1. `src/vibey/infrastructure/host_services.py` declares `class HostServiceRunner`:
   ```python
   def __init__(self, packages: HostPackageRunnerInterface, executor: CommandExecutorInterface, *,
                sleep: Callable[[float], None] = time.sleep,
                monotonic: Callable[[], float] = time.monotonic,
                poll_seconds: float = 2.0) -> None
   ```
   - `probe(spec: ProbeSpec) -> bool`:
     - builds the argv as `packages.privileged(spec.argv)` when `spec.privileged` is set,
       otherwise `spec.argv`;
     - returns False when that is None;
     - otherwise returns whether `executor.run(argv, timeout=10.0).returncode == 0`.
   - `start(spec: ServiceSpec) -> StepOutcome` builds the argv from the manager:
     - SYSTEMD: `packages.privileged(("systemctl", "enable", "--now", name))`. When that is
       None it returns `StepOutcome(False, False, f"starting {name} needs root or sudo")`.
     - BREW_SERVICES: `("brew", "services", "start", name)`.
     - MACOS_APP: `("open", "-g", "-a", name)`.

     Exit 0 returns `StepOutcome(True, True, f"started {name}", (argv,))`. Any other exit returns
     `StepOutcome(False, True, f"could not start {name}: <last non-empty stderr line or 'exit N'>", (argv,))`.
     Use `timeout=120.0`.
   - `wait_ready(spec: ProbeSpec) -> bool` probes first. If the probe fails, it sleeps
     `poll_seconds` and probes again. It returns True on the first success, and False once
     `monotonic()` has passed `start + spec.timeout_seconds`. It probes at least once, even
     with a zero timeout.
   - `run_steps(steps: tuple[tuple[str, ...], ...]) -> StepOutcome`:
     - for each step, it replaces every `{user}` inside each argument with `packages.user`,
       then runs `packages.privileged(step)`;
     - with no privilege it fails with f"`{' '.join(step)}` needs root or sudo";
     - on a non-zero exit it fails with f"`{' '.join(step)}` failed: <last stderr line>", with
       `changed=True` and the commands run so far;
     - with no steps it returns `StepOutcome(True, False, "no post-install steps")`;
     - on success it returns `StepOutcome(True, True, "ran <n> post-install step(s)", commands)`.
2. `src/vibey/infrastructure/interfaces/host_services_interface.py` declares the
   `@runtime_checkable` Protocol `HostServiceRunnerInterface`, with the four methods. Its
   types are imported under `TYPE_CHECKING`.

## Where to change
- New files:
  - `src/vibey/infrastructure/host_services.py`
  - `src/vibey/infrastructure/interfaces/host_services_interface.py`
  - `tests/infrastructure/test_host_services.py`
- The provenance line 1 is copied from `src/vibey/infrastructure/postgres.py`.
- Use `HostPackageRunner`, `StepOutcome`, `FakeCommandExecutor` and `FakeTime` from lane
  installer-host-runner: `src/vibey/infrastructure/host_packages.py` and `tests/fakes/host.py`.
- In tests, build a real `HostPackageRunner` over a `FakeCommandExecutor`. Do not fake the
  runner and do not patch anything.

## Acceptance criteria
- [ ] Each manager produces its exact argv. SYSTEMD goes through sudo when not root and runs
      directly as root.
- [ ] A privileged probe runs as `("sudo", *argv)`, and an unprivileged probe runs as-is.
- [ ] `wait_ready`, using `FakeTime` and a probe that fails twice and then succeeds, returns
      True after exactly two sleeps of `poll_seconds`.
- [ ] `wait_ready` returns False once the timeout passes. `FakeTime.now` must not exceed the
      timeout by more than one poll.
- [ ] `{user}` is substituted in post-install steps, which always run privileged. A failing
      step stops the rest.
- [ ] 100% branch coverage of `host_services.py`.

## Tests to write first (TDD)
`tests/infrastructure/test_host_services.py`:
- `test_start_systemd_unit_through_sudo`
- `test_start_systemd_unit_as_root_and_without_privilege`
- `test_start_brew_service_and_macos_app`
- `test_start_reports_a_failed_start`
- `test_probe_runs_privileged_probes_through_sudo`
- `test_wait_ready_polls_until_the_probe_answers`
- `test_wait_ready_gives_up_after_the_timeout`
- `test_run_steps_substitutes_the_user_and_runs_privileged`
- `test_run_steps_stops_at_the_first_failure_and_without_privilege`
- `test_run_steps_with_no_steps_changes_nothing`
- `test_runner_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_host_services.py tests/infrastructure/test_host_packages.py tests/application/test_interfaces_convention.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/infrastructure
    uv run coverage report --include='src/vibey/infrastructure/host_services.py' --fail-under=100

## Out of scope
- Deciding which dependency to start: that is lane installer-package-dependency.
- Catalogue entries.
- The CLI.
- Docs.

Commit as `feat(install): ...`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
