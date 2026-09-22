## Title
ci: a RabbitMQ service in the gates and three cluster contracts for the broker

## Why
ADR-0044 §16. The contract suite (R18), the topology and relay integration tests
(R12, R13), and the chaos twin need a real broker in CI, or the "verification owed"
list in the ADR is never discharged.

The cluster must also prove three things against the pinned broker image
(`values.yaml:434-440`):

- the core broker exists;
- each enabled loop service consumes its queue;
- the RabbitMQ `ScaledObject` becomes Ready.

## Required behaviour
1. **`gates` job** (`ci.yml:30-96`). Add a service `rabbitmq` using the same image
   *and digest* as `values.yaml:436-439`:
   - `RABBITMQ_DEFAULT_USER=vibey` and `RABBITMQ_DEFAULT_PASS=vibey` (the default
     `guest` account refuses non-loopback connections);
   - ports `5672:5672` and `15672:15672`;
   - health check `rabbitmq-diagnostics -q ping`, interval 10 s, 12 retries.

   Add `VIBEY_TEST_AMQP_URL: amqp://vibey:vibey@localhost:5672/` to the job env.
2. **`cluster-smoke`.** After "the worker picks up a project created in-cluster"
   (`:956-966`), add:
   - `Contract - every enabled loop service consumes its queue`:
     - `kubectl wait --for=condition=available deployment/vibey-vibey-loop-qwenloop deployment/vibey-vibey-loop-opencode -n vibey --timeout=5m`
     - then `kubectl exec -n vibey deploy/vibey-vibey-rabbitmq -- rabbitmqctl list_queues name consumers`
     - assert that `vibey.runs.qwenloop` and `vibey.runs.opencode` each show at least 1
       consumer, retrying for up to 2 minutes.
   - `Contract - the RabbitMQ ScaledObject reconciles`:
     - read the demo project's id from the worker log line or from `vibey status` (read
       `cli/main.py` for the exact output and parse it);
     - `helm upgrade vibey deploy/helm/vibey -n vibey --set keda.enabled=true --set queue.backend=rabbitmq --set worker.project=$ID --wait --timeout 5m`;
     - wait for the `ScaledObject` `Ready=True`, the same loop as `:980-988`.

   This step runs after the existing PostgreSQL `ScaledObject` contract and before the
   drain contract. The drain contract then upgrades with `--set keda.enabled=false`
   exactly as today.
3. `vibey-vibey-rabbitmq` stays in the availability list. Nothing else changes.

## Where to change
- `.github/workflows/ci.yml` only.

## Acceptance criteria
- [ ] `ci.yml` parses (`python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"`).
- [ ] The meta tests pass.
- [ ] Locally, with a broker at `VIBEY_TEST_AMQP_URL`, `uv run pytest -m integration tests/infrastructure/queue tests/contracts` passes.
- [ ] The cluster steps are syntax-checked (`bash -n` on each extracted `run` block).

## Tests to write first (TDD)
- No new test file. The contracts are the tests. Run `tests/meta` to prove the matrix
  bindings still hold.

## Checks the lane must run (all must pass)
    uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
    uv run pytest -q -p no:cacheprovider tests/meta
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Flipping the defaults (R34), which updates the existing PostgreSQL `ScaledObject`
  step to pin `queue.backend=postgres`.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R18, R30, R31.
- **Wave:** 10.
- **Files touched:** `.github/workflows/ci.yml`.
- **Parallel-safe with:** nothing that edits `ci.yml`.
- **Must keep passing unchanged:**
  - `tests/meta/test_postgres_support_matrix.py`; the 14–18 matrix is untouched
  - `tests/meta/test_tools_matrix_covers_every_package.py`
  - every existing job name. `noloss` is a required check (`ci.yml:98-104`), so no job
    is renamed.
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
