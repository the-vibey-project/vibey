## Title
feat(cli): vibey install --rabbitmq, and doctor checks the broker and every loop service

## Why
ADR-0044's *Migration* section. Once R34 flips the defaults, a laptop with no broker
fails with `QueueBackendNotConfigured`. The fix must be one command, as
`vibey install --postgres` is for PostgreSQL (`cli/main.py:1156-1180`, backed by
`PostgresLocalService` at `infrastructure/postgres.py:134-390`).

`vibey doctor` must also say whether the broker answers and whether each engine's loop
service is consuming. Otherwise a worker whose runs sit in a queue nobody consumes
looks healthy.

## Required behaviour
1. `class RabbitMqLocalService` mirrors `PostgresLocalService`:
   - `status()` reports whether `rabbitmq-server` or `rabbitmqctl` is on `PATH`, and
     whether `rabbitmq-diagnostics -q ping` exits 0.
   - `install()` uses Homebrew (`brew install rabbitmq`, `brew services start rabbitmq`),
     apt (`rabbitmq-server` plus a service start) or dnf (`rabbitmq-server` plus a
     service start).
   - It uses the same `_privileged` and step-recording approach, and the same result
     dataclasses (new `RabbitMqStatus` and `RabbitMqInstallResult`).
2. `vibey install --rabbitmq`:
   - It is independent of `--postgres`, and both flags may be given.
   - On success it prints `export VIBEY_BUS_AMQP_URL=amqp://guest:guest@localhost:5672/`.
     The `guest` account works on loopback only, and the output says so.
   - With neither flag, the usage line names both flags.
3. `vibey doctor`, when the resolved backend is `rabbitmq` or the invocation is `service`:
   - It connects with `AmqpClient` and reports `broker: ok <redacted url>`, or
     `broker: unreachable (<error>)`. An unreachable broker makes the exit non-zero.
   - In `service` mode, for each engine in the pool, it probes `--version` through
     `LoopServiceClient.probe` with a 10 s timeout, and reports
     `loop-service <engine>: answering (<version>)` or
     `loop-service <engine>: no service answered; start one with vibey loop-service --engine <engine>`.
   - With the defaults (`postgres` and `subprocess`), doctor's output is unchanged.

## Where to change
- The new module, its interface, and `cli/main.py`.

## Acceptance criteria
- [ ] Each package-manager path is tested with a fake runner, as `test_postgres_local.py` does.
- [ ] `install --rabbitmq` prints the export line.
- [ ] Doctor reports an unreachable broker and exits non-zero.
- [ ] Doctor reports a silent loop service.
- [ ] Doctor's default output is unchanged.
- [ ] 100% coverage on `cli/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/infrastructure/test_rabbitmq_local.py`: mirror each `test_postgres_local.py`
  case for brew, apt, dnf, an unsupported platform, and a failed start.
- `tests/cli/test_operational_commands.py`:
  - `test_install_rabbitmq_prints_the_export_line`
  - `test_doctor_reports_an_unreachable_broker`
  - `test_doctor_reports_a_silent_loop_service`
  - `test_doctor_default_output_is_unchanged`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_rabbitmq_local.py tests/infrastructure/test_postgres_local.py tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Flipping the defaults (R34).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R28.
- **Wave:** 9.
- **Files touched:**
  - `src/vibey/infrastructure/rabbitmq_local.py` (new)
  - `src/vibey/infrastructure/interfaces/rabbitmq_local_interface.py` (new)
  - `src/vibey/cli/main.py` (`install` at `:1156`; doctor's checks)
  - `tests/infrastructure/test_rabbitmq_local.py` (new)
  - `tests/cli/test_operational_commands.py` (new tests)
- **Parallel-safe with:** R30 and R31.
- **Must keep passing unchanged:**
  - `tests/infrastructure/test_postgres_local.py`
  - every existing `install` and `doctor` test in `tests/cli/*`
  - all protected tests
- **Standing constraints:** see the header list.

## Standing constraints for every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
  `tests/system/test_delivery_stage_set.py`, `tests/live/**` (`.vibey-gh.toml:78-85`,
  `.github/CODEOWNERS`). They must keep passing.
- **The first line of every new source file** is the provenance comment, copied
  byte-for-byte from line 1 of a sibling file (`vibey-gh check` compares it exactly).
- **No lane needs a running RabbitMQ.** Unit tests use
  `vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (lane R04). Tests against a real
  broker are marked `integration` and skip unless `VIBEY_TEST_AMQP_URL` is set.
- **SQL runs on PostgreSQL 14:** no `MERGE`, no PostgreSQL 15+ syntax. The 14–18 matrix
  runs `tests/infrastructure/db`.
- **Defaults stay today's until R34:** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.

---
