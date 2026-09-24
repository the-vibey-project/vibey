## Title
feat(install): the local stack includes the bus and the cache — RabbitMQ and Valkey — on Arch Linux and macOS

## Why
Sub-doctrine 8.b (doctrines.md:152-153) defaults the bus to RabbitMQ and the cache to Redis.
ADR-0044 makes RabbitMQ the job queue's default dispatcher once R34 flips the defaults.
Without a broker, a laptop then fails with `QueueBackendNotConfigured`.

R33 (#380, specs/rmq-r33-install-and-doctor.md) plans `RabbitMqLocalService` for brew, apt and
dnf, with no pacman. On the two default OSes, RabbitMQ is exactly a package, a daemon and a
probe, which is catalogue data. The generic installer (lane installer-package-dependency)
already serves such entries, so this lane declares RabbitMQ there and does not add a second
Arch code path.

The versions read on 2026-09-22:
- Arch: `extra/rabbitmq` 4.3.1, with `rabbitmq.service`.
- Homebrew: `rabbitmq` 4.3.6, with a service.

The Redis protocol is served by **Valkey**:
- Arch's official repositories carry `extra/valkey` 9.1.2 (with `valkey.service` and
  `valkey-cli`). Redis moved to the AUR in 2025.
- Valkey is BSD-3-Clause, where Redis 8 is AGPL-3.0, RSAL or SSPL. 8.a prefers the freer
  licence.
- vibey's cache adapter speaks RESP over a plain socket
  (`src/vibey/infrastructure/cache/redis.py:1-8`), so it works with either.
- Homebrew carries `valkey` 9.1.2 with a service.

## Required behaviour
1. Add these two entries to `CATALOGUE_ENTRIES` in `src/vibey/domain/local_stack.py`,
   immediately after `postgres`, in this order. Both have group "services", default True and
   installer `PACKAGE`.
   - **rabbitmq**, title "RabbitMQ":
     - arch: `HostRecipe(PackageSpec(PACMAN, ("rabbitmq",), ()), ServiceSpec(SYSTEMD, "rabbitmq"), ProbeSpec(("rabbitmq-diagnostics", "-q", "ping"), privileged=True, timeout_seconds=120.0), hint=B)`.
       The probe is privileged because Arch's RabbitMQ scripts run only as root or the
       rabbitmq user.
     - macos: `HostRecipe(PackageSpec(BREW_FORMULA, ("rabbitmq",), ()), ServiceSpec(BREW_SERVICES, "rabbitmq"), ProbeSpec(("rabbitmq-diagnostics", "-q", "ping"), timeout_seconds=120.0), hint=B)`.
     - `B` is `"export VIBEY_BUS_AMQP_URL=amqp://guest:guest@localhost:5672/  # guest works on loopback only"`.
       The variable is the one R01 defines (specs/rmq-r01-queue-config.md:62).
   - **valkey**, title "Valkey (Redis protocol)":
     - arch: `HostRecipe(PackageSpec(PACMAN, ("valkey",), ("valkey-server",)), ServiceSpec(SYSTEMD, "valkey"), ProbeSpec(("valkey-cli", "ping"), timeout_seconds=60.0), hint=C)`.
     - macos: the same with `BREW_FORMULA` and `ServiceSpec(BREW_SERVICES, "valkey")`.
     - `C` is `"export VIBEY_CACHE_URL=redis://localhost:6379/0"`
       (`src/vibey/infrastructure/config_loader.py:47`).
     - note: "Valkey serves 8.b's Redis surface: BSD-3 (8.a), the only Redis-protocol server in
       Arch's official repositories; flip to `redis` here if the operator reads 8.b as the
       product".
2. RabbitMQ's `binaries` stay empty on purpose. Homebrew links its scripts into `sbin`, so the
   package query is the reliable test for "installed".

## Where to change
- `src/vibey/domain/local_stack.py`: insert the two entries. Use edit_file.
- `tests/domain/test_local_stack.py`: append tests.
- No other file.

## Acceptance criteria
- [ ] Both OSes' default resolutions contain rabbitmq and valkey, immediately after postgres.
- [ ] The Arch RabbitMQ probe is privileged, the macOS one is not, and both hints are exact.
- [ ] The Valkey probe is `valkey-cli ping` on both OSes.
- [ ] The guard tests pass, with 100% domain coverage.

## Tests to write first (TDD)
Append to `tests/domain/test_local_stack.py`:
- `test_bus_and_cache_are_default_services_after_postgres`
- `test_rabbitmq_probe_is_privileged_on_arch_only`
- `test_bus_and_cache_hints_name_the_vibey_variables`
- `test_valkey_serves_the_redis_protocol_on_both_oses`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- `RabbitMqLocalService` and doctor's broker and loop-service checks, which are R33's (#380).
- The `--rabbitmq` flag, which is lane installer-cli.
- Broker users other than `guest`.
- Docs.

Commit as `feat(install): ...`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
