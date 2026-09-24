# 0056 — Everything a queue guards is reaped by measurement: five conditions, each a declared threshold, both backends judged alike, and no dead letter ever deleted

**Status:** proposed · **Date:** 2026-09-24 · **Cites:** the CLAUDE.md non-negotiables "Never block a worker on a human", "Every job is idempotent under replay" and "The ledger is append-only"; sub-doctrines 12.c, 12.d, 12.e, 10.f, 10.g, 9.b, 8.c; SD-01 §4 · **Related:** ADR-0002, ADR-0016, ADR-0017, ADR-0024, ADR-0025, ADR-0042, ADR-0044, ADR-0054, ADR-0055 · **Evidence:** `develop` at `b6444000`, read 2026-09-24; the Helm chart at the same commit; the storm's lane ledger (`docs/plans/qwenstorm-3.0.0/rmq-lanes.json`, `integrated.txt`) at the same commit

**Owes:**

- the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md` and
  `docs/index.md` (`tests/meta/test_adr_counts.py`), and a nav entry in `properdocs.yml`;
- `docs/reference/configuration.md` (`[queue.reap]`, `[bus] vhost`, the overlay),
  `docs/reference/cli.md` (`vibey queue reap`), `docs/plans/data-model.md` §3.4 (REAP),
  `docs/plans/handoff-protocol.md` (the `QueueReaped` kind), `docs/plans/domain-model.md`
  (the enum), and the paper's *Queue semantics* sentence on the reaper;
- **a sub-doctrine.** The operator's requirement -- *"all items that are guarded by a
  rabbitmq need reapers for when they are stuck"* -- binds future decisions, survives a
  rewrite, and is conduct, so under ADR-0020 it belongs in the canon, not only here. This
  record applies it; it does not ratify it. Proposed text, for the operator to file:
  *"Everything a queue holds has a reaper. Held or waiting work that stops moving is found
  by a measured condition against a declared threshold, bounded, recorded, and never
  silently dropped; a dead letter becomes a person's decision, never a deletion."*
- lane **R09** (`rmq-r09-reap-bound`, #356) is delivered here for the PostgreSQL half of
  ADR-0044 §8; the lane's spec should be closed or narrowed rather than run again.

## Context

The operator, verbatim: *"all items that are guarded by a rabbitmq need reapers for when
they are stuck."* The job queue on RabbitMQ is the 3.0.0 decision (ADR-0044, sub-doctrine
8.c), so the first question is what RabbitMQ actually guards at this commit, and what is
only declared.

### The inventory

| # | Item | Queues and dead-letter queue | Publishes | Consumes | Ack mode | What "stuck" can mean | In 3.0.0 |
|---|---|---|---|---|---|---|---|
| 1 | The bus port, `BusPort` / `RabbitMqBusAdapter` (ADR-0042) | any `<q>` a caller declares; fanout `<q>.dlx` → durable `<q>.dlq` | **nobody** in `src/vibey` (`grep` for `resources.bus`: no reader). This record adds one: a replayed dead letter | **nobody** in `src/vibey` | at-most-once: the management API's `basic.get` with `ack_requeue_false` (`infrastructure/bus/rabbitmq.py`), acknowledged on take | (a), (b) and (c) cannot arise: no delivery is ever held. (d) ready work ageing with no consumer; (e) dead-letter growth. And the opposite of stuck: a consumer that dies after `consume` returns has **lost** the message | **wired and idle.** Composed in `bootstrap.py` when `[bus]` is set -- which, in a cluster, it never was (finding 2) |
| 2 | Plane's Celery broker, on the same in-cluster RabbitMQ, vhost `/` (`templates/plane.yaml`) | Plane's Celery queues -- the default is `celery`; the names are Plane's and were **not** read from Plane's source here. Celery declares no dead-letter queue by default | `plane-api`, `plane-beat` | `plane-worker` | Celery's: acknowledged on receipt unless a task opts into `acks_late` -- Plane's choice, **unverified** | (a) a hung task holding unacknowledged messages; (b) a worker gone with messages unacknowledged; (d) ready work with no worker | **live** whenever `surfaces.plane` and `surfaces.rabbitmq` are enabled (both default `true`) |
| 3 | Job-queue dispatch (ADR-0044 §2–§8) | quorum `vibey.jobs.<project_id>`; `vibey.jobs.wait.<tier>`; DLX `vibey.jobs.dlx` → `vibey.jobs.dead` | the outbox relay (lane R13) | the worker (R14, R16) | held delivery, acknowledged after the PostgreSQL write | all five | **declared, not wired.** Lanes R01–R34 (#348–#381). Of them only R03's `aio-pika` dependency is on `develop`; no topology, relay or consumer exists |
| 4 | Loop-service runs (ADR-0044 §13) | quorum `vibey.runs.<engine_id>`; `vibey.runs.<engine_id>.probe`; `vibey.runs.dlx` → `vibey.runs.<engine_id>.dead`; `vibey.runs.control`; server-named reply queues | callers (R24–R26) | the loop service (R22) | held delivery, acknowledged after the result is persisted | all five | **declared, not wired** |
| 5 | The job queue on PostgreSQL -- not RabbitMQ, but the parity target the operator's rule reaches through ADR-0044 | the `job` table; a lease is the "delivery" | `JobRepository.enqueue` | `WorkerLoop` | lease with heartbeat at a third of it; every settle fenced on `lease_owner` | (a)/(b) the lease runs out; (c) **re-claimed forever** -- ADR-0044 §8's latent gap: `reap()` re-readied every expired lease and the claim's `attempts + 1` had no bound; (d) ready work no worker takes | **live**: the 3.0.0 job queue |

### Findings

1. **The bus port can lose a message, but it can never leave one held.** Its consume
   acknowledges on take, so there is nothing for a hung-handler or orphan reaper to find.
   It also means a crash between `consume` and the caller's work loses that message. No
   reaper can recover a message the broker has already been told was handled. The
   transport that fixes this is ADR-0044's AMQP client (R04/R14), not a reaper. It is
   recorded here, not fixed.
2. **In a cluster, the RabbitMQ adapter was never composed.** The chart renders
   `VIBEY_BUS_*` into the worker (`templates/worker.yaml`). But `build_app` applies the
   environment overlay only through `load_config_from_path`, and only when a
   `./vibey.toml` exists. The worker's working directory is `/work`, the worktrees volume,
   and it has none. So `resources.bus` was the in-memory bus in every cluster. This record
   composes the bus, and the reaper's thresholds, from the environment alone when there is
   no `vibey.toml` (`EnvironmentConfigLoader`). **Every other surface keeps today's
   behaviour.** They have the same gap, and it is left for the surfaces lanes to decide.
3. **The PostgreSQL reaper was unbounded** (row 5). That is a ladder ADR-0024 rules out.
4. **Nothing measured "ready and waiting with nobody to take it"** on either backend, and
   nothing looked at a dead-letter queue at all.

## Decision

### 1. Five conditions, each a measurement against a declared threshold (12.d, 12.c)

The judgement is one pure class, `domain/queue_reap.py::QueueReapPolicy`. It does no I/O,
and the clock is an argument. It takes a measurement and the thresholds, and returns a
`ReapVerdict`: the object, the condition, the measured value, the threshold, the unit and
the action. Every key lives in `[queue.reap]`, which the chart renders from
`worker.queueReap`.

| Condition | Measured | Threshold (key, default) | Action |
|---|---|---|---|
| **(a) hung handler**: a live holder past its deadline | *Broker:* how long a consumer has held an unacknowledged delivery. *PostgreSQL:* seconds past `lease_expires_at`. The heartbeat at a third of the lease is what pushes that deadline on | *Broker-wide:* `surfaces.rabbitmq.consumerTimeoutMs`, **1 800 000 ms**. That is the image's own default, declared explicitly so Plane keeps what it was built against. *vibey's own queues:* the policy key `consumer-timeout` = `consumer_timeout_seconds`, **21 600 s**, at least the two-hour BUILD lease with room (ADR-0044's default). *PostgreSQL:* `lease_grace_seconds`, **0** | *Broker:* it closes the channel and requeues every delivery on it; the redelivery counts toward (c). *PostgreSQL:* **requeue**. The claim already counted the attempt, so the ladder is (c)'s. `HUNG_HANDLER`, or `LEASE_EXPIRED` where liveness cannot be told apart from a hang |
| **(b) holder gone**: work held with nobody holding it | *Broker:* `messages_unacknowledged` on a queue with `consumers = 0`. *PostgreSQL:* indistinguishable from (a) (`LEASE_EXPIRED`) | 0 messages | *Broker:* **surface**. Closing a dead consumer's channel and requeueing is the broker's own job; vibey reports when it has not happened, and does not guess. *PostgreSQL:* as (a) |
| **(c) poison**: handed out as often as its limit allows and never settled | *PostgreSQL:* `attempts` at an expired lease. *Broker:* the quorum queue's delivery count | *PostgreSQL:* the row's `max_attempts`, default 7. *Broker:* the policy key `delivery-limit` = `delivery_limit`, **20** (ADR-0044) | *PostgreSQL:* **park.** The job goes to `awaiting_human` with a `delivery_exhausted` gate, and one attempt is refunded, so each answer buys exactly one more delivery (ADR-0044 §8). *Broker:* the broker dead-letters it, and (e) parks it |
| **(d) stale ready**: ready, older than a declared age, nobody taking it | Age of the oldest ready message (its `timestamp` property; vibey's publishes now set one), with `consumers = 0`. *PostgreSQL:* how long the oldest claimable job has been claimable: the latest of `run_after`, its last state change, and its last dependency's success | `stale_ready_seconds`, **900** | **surface**, loudly, as a `QueueReaped` event, a `queue.stuck` warning and a line in `vibey queue reap`. Nothing is moved, because there is nowhere better to put it. An unmeasurable age (a message with no timestamp) is not old (10.f) |
| **(e) dead letters** | Depth of a queue matching `dead_letter_queue_pattern`, **`(\.dlq\|\.dead)$`** | `dead_letter_min_depth`, **1**. Ownership: `owned_queue_pattern`, **`^vibey\.`** | *Owned:* each message becomes a **parked `bus.dead_letter` job and a `bus_dead_lettered` gate**, in one transaction and idempotent by identity. **Never deleted.** *Not owned* (Plane's): **surface**, never touched |

Everything is bounded. A reap reads at most `dead_letter_peek_limit` messages
(**100**) off a dead-letter queue. It runs at most once per `interval_seconds` (**60**) in
each worker. `enabled` (**true**) switches the automatic pass off, and never the
on-demand one.

**Both backends reap identically** because both are judged by `judge_held`. The PostgreSQL
lease reaper, `PostgresJobRepository.reap()`, is now `PostgresQueueReapStore.reap_leases()`.
Nothing is reimplemented. The existing reaper grew the bound and the record, and kept
its call sites and its `int` result.

### 2. Every reap is on the ledger, and a reap reports only what it observed (12.e)

`EventKind.QUEUE_REAPED` (`QueueReaped`). Its payload is `object`, `queue`, `condition`,
`measured`, `threshold`, `unit`, `action`, and `detail` where there is some.

- A lease reap appends its event **in the same transaction** as the job row it moves. The
  expired rows are locked `FOR UPDATE SKIP LOCKED`, so two reapers split the work and a
  replayed reap never moves a row twice. A test pins that: two stores reap twelve leases
  at once and record twelve events.
- A dead-letter park writes the job, the gate and the event in one transaction. A second
  read of the same identity finds `ON CONFLICT DO NOTHING` and writes nothing.
- A surfaced condition moves nothing. It is recorded when first seen, and again only after
  it has cleared. A queue stuck for an hour is one event, not sixty. A source the pass
  could not read says nothing about whether the condition cleared, so it clears nothing.
- A dead letter's event is `untrusted`. Its queue and reason come from the message's own
  headers (`x-first-death-queue`, `x-death`), and a publisher can write those (SD-01 §4).
  The gate shows those values quoted and cut to 200 characters. Lease and ready-work
  events are vibey's own measurements, and are `trusted`.
- The broker policy is **reconciled, then read back**. It is read first, written only when
  it differs, and read again. `PolicyOutcome.verified` comes from the read-back and never
  from a status code. A refused write -- a management user without the `policymaker` tag
  -- is reported, not raised.
- A source that cannot be read (the broker is down, a query fails) is named in the
  report's `unreadable`. Nothing is concluded from it, and the pass is not `ok`.
  `vibey queue reap` then exits 1.

### 3. A dead letter is never deleted

A reaper that deletes a dead letter has decided what happens to work nobody finished.
That is a person's decision (non-negotiable 1: a parked job and a `human_gate` row, never a
waiting worker). The reaper reads a dead-letter queue with the management API's
`ackmode: ack_requeue_true`, which returns each message to its place, and parks what it
read. The gate offers:

- `vibey answer <gate> --choice replay`: publish the body back to the queue it died on. This
  is offered only for a whole JSON object, never a body the broker cut short. Delivery is
  at least once, so the consumer must be idempotent.
- `--choice dismiss`: settle it with nothing sent.

The broker's copy stays on the dead-letter queue as evidence either way. Clearing it is a
person's act (the management UI, `rabbitmqctl purge_queue`), never a reaper's.

**What that costs, measured rather than hidden (10.g).** A read returns messages to their
place and the reaper removes none, so the messages past `dead_letter_peek_limit` stay past
it until a person clears the head. Every pass measures that remainder and surfaces it
(`dead letters past the read limit, not yet parked`). It is never assumed parked.

### 4. Where it runs

The architecture already reaps in the worker's idle loop (`cli/main.py`): after a
`run_once` that found nothing, `jobs.reap()` runs, then the wait for a notification. That
place is kept, and nothing new is scheduled. After the lease reap, the loop calls
`queue_reaper.run_if_due(project)`. That covers stale ready work and the broker, at most
once per interval across all of a worker's drive loops. On demand, `vibey queue reap
[--project] [--dry-run] [--json]` runs one whole pass. `--dry-run` judges everything and
writes nothing: no requeue, no park, no event, no policy.

As code (12.c):

- `templates/surfaces.yaml` mounts `20-vibey-reap.conf` into the broker's `conf.d`, setting
  `consumer_timeout`, and restarts the broker when the value changes.
- `templates/worker.yaml` renders every `[queue.reap]` key.
- The reaper reconciles the owned-queue policy (`vibey-reap`: `consumer-timeout`,
  `delivery-limit`) from configuration on every pass.
- A cluster-smoke contract reads `consumer_timeout` back from the running node. It then runs
  `vibey queue reap --json` in the worker pod, using only the chart's environment, and
  asserts the policy verified and present on the broker.

### 5. Code

| Layer | New |
|---|---|
| `domain/` | `queue_reap.py`: `QueueReapPolicy`, `ReapThresholds`, `HeldWork`, `QueueDepth`, `DeadLetter`, `DeadLetterPeek`, `BrokerPolicy`, `ReapVerdict`, `PolicyOutcome`. `config.py`: `QueueReapConfig`, `BusConfig.vhost`. `ledger.py`: `QUEUE_REAPED` |
| `application/` | `queue_reaper.py`: `QueueReaper`, `DeliveryExhaustedGate`. `bus_dead_letter_handler.py`: `BusDeadLetterHandler`, `BusDeadLetterGate`. Ports `BusInspectorPort` and `QueueReapStore`. `QueueReapReport` |
| `infrastructure/` | `bus/management.py` (the management client, extracted from the adapter); `bus/rabbitmq_inspector.py`; `InMemoryBus` given the same inspection semantics; `db/queue_reap_store.py`; `config_loader.py`'s nested overlay and `EnvironmentConfigLoader` |
| `cli/` | `vibey queue reap`; the drive loop's call |

Every class has its interface beside it (9.b, ADR-0016). The names are `Reap*` and
`QueueReap*`, not `BusReap*`. The storm's push-lock reaper, on `feat/push-gate-reaper`, is
another reaper over another lock. If the two converge, `ReapCondition` is the vocabulary
to converge on.

## How each non-negotiable still holds

- **Never block a worker on a human.** A poison job and a dead letter are parked jobs with
  a `human_gate` row. Neither holds a lease, a delivery or a worker.
- **Every job is idempotent under replay.** A requeued lease runs again, as it always did.
  A replayed dead letter is published at least once. Two reapers never move one row twice
  (`SKIP LOCKED`, pinned by a test). A park is idempotent by identity.
- **The ledger is append-only.** The reaper only appends. It changes queue state (`job`),
  never history (ADR-0055).
- **Credits ≠ rate limit, and a capacity rejection outranks a completion claim.** Both are
  untouched. The reaper reads no engine output and defers nothing on capacity.
- **`domain/` stays pure.** `queue_reap.py` imports `hashlib`, `json` and `re`, and has no
  clock. `tests/domain/test_domain_purity.py` walks it.

## Verification owed (upstream facts; CI has no RabbitMQ)

`.github/workflows/ci.yml` runs PostgreSQL services and no broker, and the Docker socket
was outside this lane's sandbox. So the broker's side is pinned by what vibey sends and
reads, over a faked management API (`tests/infrastructure/bus/test_rabbitmq_inspector.py`),
and by the in-memory bus with the adapter's semantics
(`tests/infrastructure/bus/test_in_memory_reap.py`). The following are upstream behaviours
of the pinned image (`rabbitmq:4-management-alpine@sha256:b839b492…`), recalled rather than
observed:

- **`consumer_timeout` in a `conf.d` snippet takes effect.** Checked by the new
  cluster-smoke contract, which reads it back with `rabbitmqctl eval`.
- **`consumer-timeout` and `delivery-limit` are accepted policy keys.** Checked by the same
  contract: the reaper's policy write, read back from `rabbitmqctl list_policies`.
- **A closed channel's unacknowledged deliveries are requeued**, which is condition (b).
  Not observed here. Owed to lane R18's chaos twin, which kills channels. Meanwhile the
  reaper surfaces any unacknowledged message left on a queue with no consumer.
- **`delivery-limit` dead-letters on a quorum queue and is ignored on a classic one.** The
  bus port's queues are classic, so on them (c) is bounded by at-most-once, not by the
  limit. Owed to R12.
- **`head_message_timestamp` reports the head message's `timestamp` property.** Without
  it, (d) on the broker stays unmeasured and is never guessed.

## Consequences

**Good.**

- Every item RabbitMQ guards, live or declared, has a named condition, threshold and
  action. The declared items' broker-side bounds (the timeout, the delivery limit) are
  already in force by policy on the day their queues appear.
- The PostgreSQL job queue's poison ladder is closed. It was the one live unbounded reap.
- A person hears about a stuck queue from the ledger, the log and one command, rather than
  from a job that never finished.

**Bad.**

- Every idle worker makes a few management-API calls per interval: a policy read, a queue
  list, and a peek per non-empty owned dead-letter queue. That is bounded but not free.
- Dead letters accumulate on the broker until a person clears them, and past
  `dead_letter_peek_limit` they are only counted, not parked. That is the price of never
  deleting.
- A dead letter with no `message_id` is known by a digest of its origin, its first death
  and its body. Two identical bodies that died in the same instant are one identity, and
  are parked once.

## Alternatives rejected

- **Move a dead letter into PostgreSQL and acknowledge the broker's copy.** It would solve
  the read-limit remainder. But a crash between the acknowledgement and the park's commit
  loses the message, and a management-API `get` cannot target a message by identity, so
  the window cannot be closed. "Never deleted" wins.
- **Reject poison messages from the bus port's queues.** Nothing is ever held there, so
  there is nothing to reject. The fix for at-most-once is the AMQP transport, not a reaper.
- **Set `x-consumer-timeout` and `x-delivery-limit` as queue arguments on
  `declare_queue`.** Changing an existing queue's arguments is a `406
  PRECONDITION_FAILED`, which would break every broker that already has the queue. A
  policy applies to existing queues and can be reconciled.
- **A CronJob.** The reap already lives in the worker's idle loop (ADR-0044 §11 keeps it
  there). The default chart always runs a worker. A second scheduler would be a second
  owner of the same reap.
- **Change the broker-wide `consumer_timeout`.** Plane's Celery workers share the broker.
  The broker-wide value stays the image default, declared, and vibey's own queues get
  theirs by policy.
