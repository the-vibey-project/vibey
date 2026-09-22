# 0044 — The job queue is a port: RabbitMQ dispatches by default, PostgreSQL stays selectable and stays the record, and every loop engine runs as a long-lived service

**Status:** proposed · **Date:** 2026-09-22 · **Supersedes:** ADR-0002 (its queue-dispatch decision only; its record-store and ledger decisions are restated below and stand) · **Amends:** ADR-0025 (the autoscaling trigger), ADR-0009 (how an answer re-readies a parked job) · **Cites:** sub-doctrines 8.a, 8.b, 8.c, 9.b, 10.e, 10.f, 12.c · **Related:** ADR-0003, ADR-0004, ADR-0016, ADR-0017, ADR-0023, ADR-0024, ADR-0026, ADR-0029, ADR-0037, ADR-0038, ADR-0042, ADR-0043 · **Evidence:** `develop` at `d47c196d`, read 2026-09-22 in the checkout `/private/tmp/claude-501/storm/changelog-2.1.0`; every `file:line` below is at that commit; the canon is read at `472c5c6b`, the merge of #325 that ratified 8.c and amended 8.b

**Owes:** nothing new as conduct — this record is mechanism (ADR-0020), and the conduct
it implements is ratified: sub-doctrine 8.c (every loop runs once, fed by a queue) and
8.b's bus default (RabbitMQ), both by the merge of #325 on 2026-09-22. It owes the docs
wave: status notes on ADR-0002 and
ADR-0025, `docs/plans/data-model.md` §3.3–§4, `docs/plans/architecture-and-roadmap.md`
§4 and §7, the paper's *Queue semantics* and *Validation* sections, the CLAUDE.md
"Queue backend" fact, the four agent-surface trees, and the advertised ADR count
(`tests/meta/test_adr_counts.py`).

## Context

### The queue today

The queue is two application seams and one implementation of each.

- `JobRepository` (`src/vibey/application/interfaces/queue.py:89-186`): enqueue,
  batch enqueue, claim, heartbeat, ack, nack, defer, park, grant, reap, assign, and
  four reads. `JobReadyNotifier` (`queue.py:81-86`) is the wakeup.
- `PostgresJobRepository` (`src/vibey/infrastructure/db/job_repository.py:45-367`)
  implements every method as one SQL statement from data-model §3.4. The claim is a
  `FOR UPDATE SKIP LOCKED` scan scoped to one project, ordered by priority, then
  `run_after`, then id, excluding jobs with an unsucceeded dependency (`:178-208`).
  Every settling write is fenced on `lease_owner` (`:223-309`). The reaper returns
  every expired lease to `ready` (`:311-320`).
- `PostgresJobReadyNotifier` (`src/vibey/infrastructure/db/notifier.py:16-51`)
  listens on `vibey_job_ready`. `enqueue` sends that notification inside its own
  transaction (`job_repository.py:133`), and so does a gate answer
  (`human_gate_repository.py:85`).
- A gate answer re-readies its parked job in the same transaction as the answer
  (`src/vibey/infrastructure/db/human_gate_repository.py:61-86`).
- The worker loop (`src/vibey/application/worker.py:130-312`) claims, heartbeats at a
  third of the lease (`:387-423`), and settles. It raises a gate *before* it parks
  (`:296-311`), and it reports every lease-guarded write that did not land rather than
  raising (`:425-442`).
- The `vibey worker` drive loop (`src/vibey/cli/main.py:1728-1753`) calls `run_once`.
  Only when that finds nothing does it call `reap()` (`:1745`) and wait up to five
  seconds for a notification (`:1749`). It builds `PostgresJobReadyNotifier` itself
  (`:1715`). The composition root yields a concrete `PostgresJobRepository`
  (`src/vibey/bootstrap.py:918`).
- Leases depend on the job kind (`bootstrap.py:274-287`): two hours for
  `build.implement` and `build.verify`, fifteen minutes for decompose and integrate,
  two minutes for everything else.
- Schema: `migrations/0003_job.sql` (the enum, `job`, `job_dependency`, the claim and
  expiry indexes).

The semantics are pinned by `tests/infrastructure/db/test_job_repository.py`, by the
protected chaos test `tests/infrastructure/db/test_chaos.py` (8 workers, 500 jobs, 20%
simulated SIGKILL: no double commit, no lost job, every job terminal), by the
PostgreSQL 14–18 compatibility matrix (`.github/workflows/ci.yml:141-193`, bound to
runtime policy by `tests/meta/test_postgres_support_matrix.py`), and by the protected
system tests. The system tests run on `FakeJobRepository`
(`tests/application/fakes.py:16`), so they do not depend on the backend.

**A latent gap the move exposes.** Neither the claim nor the reaper bounds a job that
kills its worker. The claim increments `attempts` with no upper bound (`:182-187`), and
the reaper re-readies every expired lease (`:311-320`). A handler that takes its
process down on every attempt therefore never reaches `_settle_failure` (`worker.py:224-272`),
and it is re-claimed forever. That is an unbounded ladder, which ADR-0024 rules out.

### Autoscaling today

`deploy/helm/vibey/templates/keda-scaledobject.yaml:49-66` scales workers on a
PostgreSQL query that is the claim's SELECT arm scoped to the worker's project: ready,
due, with every dependency satisfied. `tests/infrastructure/db/test_keda_scaler_query.py`
binds the rendered SQL, taken from the committed goldens, to the real claim. ADR-0025
rejected scaling on raw queue depth by name.

### How vibey runs engines today

The worker spawns each runner as a child process. `LoopProcessAdapter`
(`src/vibey/infrastructure/engines/loop_process_adapter.py:114-735`) builds the argv
(`argv.py:10-30`), writes the plan to `<worktree>/.vibey/plans/<run_id>.md`, spawns
with the orchestrator's Python environment stripped (`:87-111`, `:335-416`), and tails
`events.jsonl` from the runner's run directory (`:418-589`). It stops a run by writing
`inbox/*-stop.json` and waiting up to 30 s for `stop-summary.md` (`:651-706`). The
exit code comes from the child (`:616-623`), and exit 75 is the wind-down signal
(`domain/engine.py:16`). Local engines receive an environment overlay: qwenloop's
`QWENLOOP_BASE_URL` comes from `VIBEY_OLLAMA_URL` (`local_engines.py:143-188`). The
DESIGN and DECOMPOSE providers also spawn through an injected `CommandExecutor`
(`claudeloop_process.py:34-104`, `opencodeloop_process.py:32-85`).

When qwenloop manages its own llama.cpp or vLLM server, each `qwenloop run` checks for
that server and starts it if it is not healthy (`qwenloop/cli/app.py:250-277`). An
attached OpenAI-compatible server such as Ollama is never started or stopped by
qwenloop (`qwenloop/infrastructure/inference.py:254-333`). Parallel callers therefore
contend for one model with no arbitration. The QwenStorm driver makes the point:
`storm-queue.sh` serializes lanes by hand.

### The bus surface today

`[bus]` (`src/vibey/domain/config.py:289-295`) is backed by an adapter:
`RabbitMqBusAdapter` (`src/vibey/infrastructure/bus/rabbitmq.py:25-114`). It is wired
in `bootstrap.py:866-882`. It speaks the management HTTP API through stdlib `urllib`
and consumes with `ackmode: ack_requeue_false` (`rabbitmq.py:103`). That is at-most-once,
with no prefetch, no redelivery and no consumer. Nothing in `src/vibey` reads
`resources.bus`. The chart runs RabbitMQ (`rabbitmq:4-management-alpine`, pinned by
digest at `values.yaml:434-450`) only inside the surfaces block
(`templates/surfaces.yaml:99-215`, gated by `surfaces.enabled`). The same broker is
Plane's Celery broker (`values.yaml:246`).

### What cannot move

Four non-negotiables are enforced by PostgreSQL itself:

- the `credits_never_have_a_deadline` CHECK (`migrations/0007_engine_health_rotation.sql:21`);
- the append-only rules on `event` and its gapless per-project `seq`, which rule R6 of
  the no-loss gate depends on (ADR-0003, ADR-0004);
- the fenced compare-and-set that is the chaos test's "exactly one commit per job";
- the unique index behind idempotent enqueue (`0003_job.sql:26`).

Advisory locks also serialize integrates (ADR-0029) and migrations (data-model §7.1).
None of this is queue dispatch. All of it must stay.

## Decision

### 1. Two seams, two backends, one record

For the queue, the application layer does not change. `JobRepository` and
`JobReadyNotifier` remain the whole queue contract. `WorkerLoop`'s queue use, every
handler's queue use and `FakeJobRepository` are untouched. The loop services need two
small application additions, listed in §14. The composition root chooses a backend from `[queue] backend`
(`VIBEY_QUEUE_BACKEND`).

| backend | `JobRepository` | `JobReadyNotifier` | status |
|---|---|---|---|
| `rabbitmq` | `RabbitMqJobRepository` | `RabbitMqJobWakeup` | the default |
| `postgres` | `PostgresJobRepository`, unchanged | `PostgresJobReadyNotifier`, unchanged | selectable, kept per 12.c |

**PostgreSQL remains the record store and the ledger in both backends. This is stated
explicitly, not left implied.** RabbitMQ carries *dispatch*: which job is claimable
now, who holds it, when it is due again, and which job keeps killing its consumers.
PostgreSQL carries *truth*: state, attempts, idempotency, dependencies, gates, lease
fencing, engine health and the ledger. A RabbitMQ message is a pointer to a `job` row,
never the job itself. State stays out of the broker for four reasons:

- idempotent enqueue needs a unique index, and the core broker has no durable
  deduplication (the deduplication plugin is third-party);
- dependencies form a DAG, which AMQP does not model;
- exactly one commit needs a fenced compare-and-set;
- `count_unsettled`, `queue_depth` and `list_for_cycle` are queries.

`vibey` therefore still refuses to start without `VIBEY_PG_URL` (ADR-0002's
`DatabaseNotConfigured`).

There is no silent fallback between backends. If `rabbitmq` is selected and no
`[bus] amqp_url` (`VIBEY_BUS_AMQP_URL`) is set, the start fails with
`QueueBackendNotConfigured`. The message gives the exact `export` line, or
`backend = "postgres"` as the alternative. This follows ADR-0002's rule for the DSN,
which exists because of the incident recorded there.

### 2. Topology

Every name starts with a configurable prefix (`[bus] prefix`, default `vibey`) and
lives in a configurable vhost (`[bus] vhost`, default `/`). The prefix is what keeps
vibey's objects apart from Plane's Celery queues on a shared broker.

| object | type | arguments / bindings | purpose |
|---|---|---|---|
| `vibey.jobs` | topic exchange, durable | — | dispatch |
| `vibey.jobs.<project_id>` | quorum queue | bound `job.<project_id>` and `*.job.<project_id>`; `x-delivery-limit`, `x-dead-letter-exchange=vibey.jobs.dlx`, `x-dead-letter-strategy=at-least-once`, `x-overflow=reject-publish`, `x-consumer-timeout` | one per project, because a worker serves one project (`cli/main.py:1549-1566`, `keda-scaledobject.yaml:4-12`) |
| `vibey.jobs.wait` | topic exchange | — | delays |
| `vibey.jobs.wait.<tier>` | queue, no consumers | `x-message-ttl=<tier ms>`, `x-dead-letter-exchange=vibey.jobs`; bound `<tier>.#` | fixed-delay tiers; the default tiers are `w1s w5s w30s w2m w10m w1h` |
| `vibey.jobs.dlx` | fanout exchange | — | poison |
| `vibey.jobs.dead` | quorum queue | bound to the DLX | poison pointers the reconciler parks |
| `vibey.runs` | direct exchange | — | loop-service run requests |
| `vibey.runs.<engine_id>` | quorum queue | routing key `<engine_id>`; `x-delivery-limit` (default 3), DLX `vibey.runs.dlx`, `x-consumer-timeout` | one per engine |
| `vibey.runs.<engine_id>.probe` | classic queue | routing key `<engine_id>.probe` | preflight probes, never queued behind a long run |
| `vibey.runs.dlx` / `vibey.runs.<engine_id>.dead` | direct exchange / queue | routing key `<engine_id>` | run requests that crashed their service |
| `vibey.runs.control` | topic exchange | each service instance binds an exclusive, auto-delete queue on `<engine_id>` | stop, wind-down and prompts |
| caller reply queue | exclusive, auto-delete, server-named | named in `reply_to` | accepted, progress and result messages for that caller |

Wait tiers are fixed per queue. A single wait queue with per-message TTLs would not
work: a classic queue expires only the message at its head, so one long delay would
hold back every shorter delay behind it. The delayed-message exchange is a community
plugin, is not in the official image, and does not replicate. Keys are
`<tier>.job.<project_id>`. A message that dead-letters out of a tier keeps its routing
key, so it lands in `*.job.<project_id>` and needs no per-message DLX key.

### 3. The dispatch envelope

The body is JSON (`content_type=application/json`, `delivery_mode=2`, published with
publisher confirms). A pure codec in `domain/job_dispatch.py` defines it:

```json
{"schema": "vibey.job.dispatch/1", "job_id": "<uuid>", "project_id": "<uuid>",
 "dispatch_seq": 3, "kind": "build.implement", "not_before": "2026-09-22T12:00:00+00:00"}
```

Properties: `message_id = "<job_id>:<dispatch_seq>"`, `type = "job.dispatch"`, and
`correlation_id` set to the project's delivery correlation id
(`DELIVERY_CORRELATION.for_project`). An unknown schema or a malformed body is
rejected without requeue, which dead-letters it. It is never guessed at, the same
forward-compatibility posture as vibey#287.

### 4. Dispatch lifecycle: a transactional outbox and a dispatch generation

Migration `0014_job_dispatch.sql` adds `job.dispatch_seq bigint NOT NULL DEFAULT 0`
and `job.dispatched_at timestamptz`, and creates `job_outbox`. That table has the
shape of the family's outbox (`vibey_bootstrap/db/outbox.py:31-42`) plus a
`claimed_at` column. `dispatch_seq` is a **dispatch generation**. A value of 0 means
never dispatched. Every transition that starts a new dispatch episode increments it
and writes one outbox row **in the same PostgreSQL transaction as the state change**.
A message whose generation is not the row's current one is stale and is dropped
unread.

| transition | PostgreSQL (one transaction) | outbox / broker |
|---|---|---|
| enqueue, deps met | `INSERT … ON CONFLICT DO NOTHING` (unchanged), then `dispatch_seq 0→1` only if still 0 and every dependency succeeded | outbox row; publish after commit |
| enqueue, deps unmet | insert only | nothing (released later) |
| ack | fenced ack (unchanged), then every dependent with `dispatch_seq = 0` whose dependencies have now all succeeded goes `0→1` | outbox rows for released dependents; `basic.ack` of the held delivery |
| nack (attempts remain) | unchanged backoff SQL, plus `dispatch_seq+1` | outbox row, `not_before = run_after`; `basic.ack` |
| nack (last attempt) | unchanged; `failed`, no bump | `basic.ack` |
| defer | unchanged, plus `dispatch_seq+1` | outbox row, `not_before = retry_at`; `basic.ack` |
| park | unchanged | `basic.ack`; nothing republished |
| gate answer | unchanged answer and re-ready, plus `dispatch_seq+1` | outbox row |
| reap (expired lease) | `ready` plus `dispatch_seq+1`; a row whose attempts reached `max_attempts` parks as `delivery_exhausted` instead (§8) | outbox row (none for a park) |
| lost-dispatch sweep | a claimable row not dispatched within `redispatch_after`, or claimable at seq 0 (the enqueue-versus-ack race) | outbox row, **same** generation (a duplicate, which is harmless), or `0→1` |

The relay drains `job_outbox` with the family's outbox. It routes each row to
`vibey.jobs` when it is due, or to the right wait tier when it is not, waits for the
publisher confirm, then marks the row sent and stamps `job.dispatched_at`. It runs in
two places: best-effort right after a commit in the process that committed, and
inside every worker's `reap()`. A crash between the commit and the publish leaves a
pending row that the next `reap()` publishes. A crash between the publish and the
mark publishes twice, and the generation check drops the duplicate. That is the
transactional-outbox guarantee: at-least-once publish, exactly-once effect.

### 5. Leases, mapped onto AMQP

**Two lease authorities with one arbiter.** The broker's lease is the *held delivery*,
an unacknowledged message on a live channel. PostgreSQL's lease is `lease_owner` and
`lease_expires_at`, extended by the same heartbeat as today (`worker.py:387-423`).
**Only the PostgreSQL lease decides a commit.** Every settling write stays fenced on
`lease_owner` exactly as it is today, so a stale holder's ack is refused whatever the
broker thinks.

| PostgreSQL backend (unchanged) | RabbitMQ backend |
|---|---|
| claim = `SKIP LOCKED` scan | take the next buffered delivery (`basic.qos prefetch = worker parallelism`), then a **fenced claim**: `UPDATE job … WHERE id = $job AND project_id = $p AND dispatch_seq = $seq AND (state = 'ready' OR (state = 'leased' AND lease_expires_at < now())) AND run_after <= now() AND <deps met> RETURNING *`. On a hit the delivery stays unacknowledged. On a miss a pure `DispatchMissPolicy` decides: drop (terminal, parked, stale generation, or unknown row), or re-delay to `max(lease_expires_at, run_after)` in a wait tier, then ack |
| lease expiry plus heartbeat | unchanged; the held delivery needs no heartbeat, because AMQP connection heartbeats keep the channel alive |
| worker death, then reap | channel death makes the broker redeliver at once. The fenced claim takes over an *expired* lease; an unexpired one is re-delayed to its expiry. `reap()` still reaps holders that are alive but stuck, because their channel never closes. Worst-case delay stays at most one lease, the same bound the paper gives today |
| ack / nack / defer / park | the PostgreSQL write (plus outbox), then `basic.ack` of the held delivery, **whether or not the write landed**. A refused write means the delivery is stale |
| (none) | **consumer timeout.** `x-consumer-timeout` on the work queue, default 6 h, at least the longest job. A breach closes the channel and every held delivery on it is redelivered. The PostgreSQL fence makes that safe, though noisy |
| (none) | **delivery limit.** `x-delivery-limit`, default 20, counts redeliveries after channel deaths. Past it the pointer dead-letters, and §8 parks the job |
| `LISTEN vibey_job_ready` plus a 5 s poll | `RabbitMqJobWakeup` resolves when a delivery for the project is buffered; the same 5 s idle tick remains |

A job's commit is therefore still "exactly one fenced ack", and its execution is still
at least once. Those are the two properties `test_chaos.py` counts. A RabbitMQ twin of
that test (not the protected file) asserts the same tally, with channels killed
instead of tasks abandoned.

### 6. Parked jobs

Parking is unchanged at the seam. A handler returns `Park`, and the worker raises the
`human_gate` row **before** releasing the lease (`worker.py:296-311`). In the RabbitMQ
backend, releasing the lease also acks the held delivery and publishes nothing. **A
parked job therefore holds no worker, no delivery, no prefetch slot and no KEDA
count.** The answer re-readies the job exactly as `human_gate_repository.py:77-84`
does today, and in the same transaction it increments `dispatch_seq` and writes an
outbox row. The notification stays; it is harmless in both backends.

### 7. Delays and scheduling

`run_after` stays the truth. The relay sends a dispatch that is not due to the
**largest tier no longer than the remaining delay**, or to the smallest tier if the
delay is shorter than that. It never sends one to a tier longer than the delay. A
message that arrives early is re-delayed by the miss policy. Lateness is bounded by
the smallest tier plus the queue's backlog. The longest backoff vibey writes today is
15 minutes for a nack; verify defers 10 minutes and capacity defers use a probe
interval, not a reset time (see non-negotiable 2). Lease waits of up to 2 h take a
few `w1h` hops. The tiers are a configurable list (`[queue.rabbitmq] wait_tiers_seconds`).

### 8. Dead letters are parks

A delivery that exceeds `x-delivery-limit` has killed that many consumers. It
dead-letters to `vibey.jobs.dead`. `reap()` drains that queue with `basic.get`. For
each pointer it raises a `delivery_exhausted` gate and moves the job to
`awaiting_human`, **in one PostgreSQL transaction**, and only if the row is still
`ready` or holds an expired lease at the same generation. Otherwise it acks and drops
the pointer, because the job has moved on. The gate prompt advertises the grant
(ADR-0024): "answer anything to retry with a fresh delivery budget". The answer is an
ordinary re-ready at a new generation, so the new message's delivery count starts
from zero.

The same bound applies to the PostgreSQL backend, for parity and to close the latent
gap above. `reap()` parks an expired lease whose attempts have reached `max_attempts`,
instead of re-readying it. The gate is the same `delivery_exhausted` kind, and it
refunds one attempt, so each answer buys exactly one more delivery.

A malformed message on any queue is rejected without requeue. vibey_bootstrap's
dead-letter growth alarm watches the dead queues (`servicebus/dlq_alarm.py:38-86`,
fed through its `peek_dead_letter_messages` protocol by the existing management-API
client).

### 9. Idempotency keys

| what | key | enforced by |
|---|---|---|
| enqueue | `job.idempotency_key` = sha256(`project:cycle:kind:subject`) (`domain/job.py`) | `UNIQUE (project_id, idempotency_key)`, unchanged |
| dispatch | `message_id = <job_id>:<dispatch_seq>`; outbox key `dispatch:<job_id>:<seq>[:sweep:<epoch>]` | the fenced claim's `dispatch_seq = $seq`; the outbox's unique key |
| commit | `lease_owner` | every settling write, unchanged |
| run | `run_id` (a fresh `uuid4` per attempt, `build_implement_handler.py:222`) = AMQP `message_id` = `correlation_id` | the service's `ReplayGuard` (vibey_bootstrap `servicebus/async_ext.py:26-49`) plus a durable `<cwd>/.vibey/diagnostics/<run_id>.result.json` |
| run ownership | `supersedes = {key: <job_id>, attempt: <n>}`, plus `cwd` | the service stops a lower attempt for the same key before it starts a higher one; a different key on a busy `cwd` is rejected (§13) |
| ledger | `(project_id, seq)`, gapless | unchanged |

### 10. Ordering guarantees

- **PostgreSQL backend:** unchanged. Strict priority, then `run_after`, then id, per
  project, as the paper states.
- **RabbitMQ backend:** FIFO by dispatch time among due messages in one project's
  queue. Priority is best-effort: quorum queues in RabbitMQ 4 honour two levels, so
  `job.priority > 0` maps to the high level. **Strict cross-class priority is not
  guaranteed**, and the paper's queue-semantics paragraph must say which backend it
  describes. No caller sets a non-zero priority today (`EnqueueRequest.priority`
  defaults to 0 at `dto.py:28`, and no call site passes one). Dependency order is
  guaranteed by construction, because a job is never dispatched before every
  dependency has succeeded, and the fenced claim checks again. Correctness never
  depends on delivery order; fairness does, and it is weaker.
- **Per run:** a service publishes a run's replies on one channel to one reply queue.
  RabbitMQ keeps publish order for that path, and `RunProgress.seq` exposes any gap.
  The authoritative order of a run's events is `events.jsonl`, as today.

### 11. Wakeup, reconcile and drain

The drive loop does not change shape: `run_once`, then, when idle, `reap()` and a
wakeup wait (`cli/main.py:1728-1753`). In the RabbitMQ backend, `reap()` means
**reconcile**, at most once per `reconcile_interval` (default 30 s), in this order:
reap expired leases with a redispatch (§4, §8), sweep lost dispatches, drain the
outbox, drain the dead queue into parks. The first claim of a fresh consumer waits
briefly (`first_claim_wait`, default 2 s) so that `vibey work` and `--once` do not
report "no ready job" before the broker has pushed anything.

On SIGTERM the existing drain flag (ADR-0025, ADR-0026) stops claiming. The consumer
then sends `basic.cancel` and returns every buffered but unclaimed delivery with
`nack(requeue=true)`. Held deliveries settle normally as their jobs finish. Each drain
can add one to the delivery count of at most `prefetch` buffered messages, which is
why the delivery limit defaults to 20 and not 3.

### 12. Autoscaling

`keda-scaledobject.yaml` branches on `queue.backend`:

- `postgres` keeps today's trigger byte for byte. The `keda-latest` and `keda-project`
  golden profiles pin `--set queue.backend=postgres`, so
  `test_keda_scaler_query.py` keeps binding that SQL to the real claim, unchanged.
- `rabbitmq` uses KEDA's `rabbitmq` scaler with `protocol: http`, `mode: QueueLength`,
  `queueName: vibey.jobs.<worker.project>`, `value: <worker.parallelism>`,
  `excludeUnacknowledged: "false"`, and a `TriggerAuthentication` whose `host` is a
  chart-rendered Secret key using the fully-qualified service DNS. That qualification
  is ADR-0025's lesson: KEDA dials from its own namespace.

The count is claimable work plus in-flight work. Only due work with its dependencies
met is ever in the queue; parked, blocked and delayed jobs are not (§4, §6, §7). This
honours ADR-0025's rule against scaling on raw depth. Unlike the SQL trigger, it also
counts in-flight work, so a pod running a two-hour session is not scaled in under
it. The drain remains the guarantee.

**One consequence the backend cannot avoid.** A worker with no project bound resolves
"the newest project" at startup. A broker has no notion of project age, so the
RabbitMQ trigger cannot follow it. The chart therefore **fails the render** when
`keda.enabled`, `queue.backend=rabbitmq` and `worker.project=""` are all set, naming
both remedies. The PostgreSQL trigger keeps supporting the unbound mode, so no
configuration is lost (12.c). `values.yaml` already calls the unbound worker a
footgun.

### 13. Every loop engine runs as a long-lived service

**The engine seam does not change.** `EngineAdapter`
(`application/interfaces/engines.py:44-80`) is the contract. `[engines] invocation`
(`VIBEY_ENGINE_INVOCATION`) selects between two values:

- `service`, the default: `LoopServiceAdapter` publishes runs;
- `subprocess`: today's `LoopProcessAdapter`, kept and selectable per 12.c.

The DESIGN and DECOMPOSE `CommandExecutor` gets the same switch, through
`LoopServiceCommandExecutor`. Callers — workers, `vibey work` and `vibey design`, the
storms (through `vibey loop submit`) and the operator's kickoff path — publish run
requests. None of them spawns a runner.

**The service.** `vibey loop-service --engine <engine_id>` is one long-lived process
per engine, run as one Deployment per engine in a cluster. It consumes
`vibey.runs.<engine_id>` with `prefetch = [loop_services.<engine_id>] prefetch`. The
default is 1 for LOCAL-tier engines (`qwenloop`, `opencode`, `claudeloop-local`). The
default is also 1 for paid engines, and it can be raised to what their rate limits
allow; the bound is 1–64, and a value above 1 on a LOCAL engine logs a warning rather
than being refused (12.c). Each run is executed **as the runner's own CLI in a
subprocess**, with the same argv, run directory, inbox, exit codes and conformance
contract as today. The service reuses `LoopProcessAdapter`'s launch discipline,
extracted into a shared `EngineProcessLauncher`. The runner is not imported
in-process, for three reasons:

1. The protected live conformance suite (`tests/live/test_scripted_binary_conformance.py`)
   asserts that CLI contract against the installed binary, so it keeps pinning exactly
   what the service executes.
2. The six runner tenants, their pyprojects and their gates (ADR-0022) stay untouched.
3. `vibey-runners-common` stays at `dependencies = []`.

**"One model stays loaded; every caller shares it."** The qwenloop service's startup
hook applies the local-endpoint overlay (`LocalEndpointEnvironment`,
`local_engines.py:158-188`). With an attached endpoint (Ollama), the model is resident
in that server. With a managed backend, the hook runs `qwenloop server start` once at
service start (`qwenloop/cli/app.py:638`), and every run attaches to that healthy
server instead of starting its own (`app.py:269-271`). Prefetch 1 is what makes the
one model a shared resource rather than a contended one: the broker queues callers
that previously collided.

**Protocol** (`domain/run_protocol.py`: pure dataclasses and a strict codec;
`schema` is versioned):

| message | direction | body (JSON) | AMQP properties |
|---|---|---|---|
| `vibey.run.request/1` | caller → `vibey.runs` (key `<engine_id>` or `<engine_id>.probe`) | `run_id, engine_id, purpose (run\|probe), args (argv after the binary), cwd, run_dir, supersedes {key, attempt} \| null, deadline_seconds, start_by, capture_output, requested_at, caller` | `message_id = correlation_id = run_id`, `reply_to`, `delivery_mode=2`, **no `expiration`** |
| `vibey.run.accepted/1` | service → `reply_to` | `run_id, service_instance, pid, started_at` | `correlation_id = run_id` |
| `vibey.run.progress/1` | service → `reply_to` (optional, `publish_progress`) | `run_id, seq, line` (one raw `events.jsonl` line) | same |
| `vibey.run.result/1` | service → `reply_to` | `run_id, status, exit_code, meta_status, started_at, finished_at, detail, stdout?, stderr?` (capped) | same |
| `vibey.run.control/1` | caller → `vibey.runs.control` (key `<engine_id>`) | `run_id, command (stop\|wind_down\|prompt-now\|prompt-at-break), text?` | — |

`status` takes one of these values: `exited`, `superseded`, `abandoned`, `rejected`,
`dead_lettered`, `deadline_exceeded`. **`RunResult` has no completion field and no
capacity field.** Completion stays the caller's judgement from the verdict event,
checked *after* any capacity rejection (`build_engine_run.py:114-120`,
`build_implement_handler.py:241-263`). The service never classifies capacity.

- **Correlation.** `run_id` is the message id, the correlation id, the causation id
  on ledger rows (`build_engine_run.py:81-84`) and the run directory's name: one id
  joins broker, ledger and disk.
- **Evidence.** The authoritative evidence of a run is still its run directory on the
  shared worktree volume (`events.jsonl`, `meta.json`, `stop-summary.md`,
  `snapshots/latest.json`). `LoopServiceAdapter.tail` reads it through the extracted
  `RunDirTailer`, exactly as today. It ends on a terminal `meta.json` status, on
  `RunResult`, or at the deadline. The progress stream is advisory, for TUIs,
  followers and remote observers. It is never the ledger's source, so a lost progress
  message cannot drop evidence.
- **Result persistence.** Before it acks a request, the service writes
  `<cwd>/.vibey/diagnostics/<run_id>.result.json`, beside the stdout and stderr files
  `LoopProcessAdapter` already keeps (`:365-368`), and publishes `RunResult` with a
  publisher confirm. `run_exit_code` returns `RunResult.exit_code`, or reads the file
  when the reply was lost. Exit 75 keeps meaning wind-down.
- **Dedupe on redelivery.** If the request was redelivered after a service crash and
  the result file exists, the service republishes the result and acks. If the run
  directory is non-terminal and no process of this service owns it, the status is
  `abandoned` (the result file is written, then published, then acked). Otherwise the
  run starts.
- **Cancellation and supersede.** Control messages become the runner's own inbox files
  (`RunInbox`, extracted from `loop_process_adapter.py:591-614,651-658`). A request
  whose `supersedes.key` matches an active run with a lower `attempt` first stops that
  run: an inbox stop, then up to `supersede_grace_seconds` (default 30), then a group
  kill through `ProcessReaper`. The service publishes `superseded` for the old run and
  only then starts the new one. A request whose `cwd` already has an active run under
  a *different* supersede key, or under none, is answered `rejected` with the detail
  "worktree busy". The caller defers it; the service never queues it behind the run.
  **No two runs ever share one worktree.** The supersede key is the job id, and the
  attempt is `job.attempts`, both carried on `RunSpec` (two new fields with defaults).
- **Probes.** `preflight()` sends `--version` and `doctor` as `purpose=probe` to the
  probe queue, and `run --help` for `help_text`, which conformance reads synchronously
  (`conformance.py:119`). The adapter caches it from the last probe. Probes run where
  the runs run, which is the environment whose auth matters.
- **Queue wait.** Every request carries `start_by = requested_at + run_queue_wait_seconds`,
  and a service rejects a request it receives after that time. If the adapter has not
  seen `RunAccepted` by then, it raises `EngineQueueSaturated`, a new application
  exception beside `CapacityDeferred` (`worker.py:46-57`). `WorkerLoop` turns it into
  `Defer(capacity=False)`. A saturated service is not an engine capacity signal
  (`queue.py:40-57`), so it opens no circuit and burns no attempt. Both checks depend
  on host clocks, so skew between hosts only shortens or lengthens the wait window.
- **Drain.** On SIGTERM the service stops consuming and lets its runs finish within
  `terminationGracePeriodSeconds`, which mirrors the worker (ADR-0025). A run cut at
  the grace period ends `abandoned`, and its job nacks and retries.
- **Security.** The service executes only its own descriptor's binary. `args[0]` must
  be `run` or `resume` for `purpose=run`, and one of `--version`, `doctor` or
  `run --help` for `purpose=probe`. The environment comes only from the service's own
  configuration and never from a message.
- **Liveness.** The service feeds vibey_bootstrap's consumer watchdog
  (`heartbeat/__init__.py`: `record_consumer_iteration`, `record_message_settled`).

**Every worktree-mounting pod shares one filesystem.** A run edits `cwd`, and the
caller tails `run_dir`, so the service and its callers must see the same absolute
paths. In a cluster that means every loop service mounts the worker's worktrees PVC at
`/work`. `worker.worktrees.accessMode` becomes a value (default `ReadWriteOnce`). With
`ReadWriteOnce`, every pod that mounts the PVC carries the label
`vibey.dev/worktrees: <release>` and a *required* pod affinity on that label
(topology `kubernetes.io/hostname`). The first pod of the set may schedule because it
matches its own term. Multi-node clusters should use `ReadWriteMany`.

### 14. Where the code lives, and the new dependency

Family first (10.e). `src/vibey_tools/bootstrap` has **no AMQP client**. It does have
five things this design uses:

- the Service Bus settle vocabulary: complete, abandon, dead-letter, classified by
  `is_unrecoverable` (`servicebus/consumer_wrapper.py:26-225`);
- a bounded `ReplayGuard` (`servicebus/async_ext.py:26-49`);
- a dead-letter growth alarm (`servicebus/dlq_alarm.py:38-86`);
- a consumer watchdog (`heartbeat/__init__.py`);
- a transactional outbox (`db/outbox.py:31-183`). It is sync SQLAlchemy only, and
  a row claimed as `sending` by a relay that then dies is never reclaimed.

Its tenacity retry (`retry/__init__.py`) needs an extra that vibey does not install,
and AMQP's own reconnection is the client library's job.

The management-HTTP `RabbitMqBusAdapter` cannot be the queue transport. `basic.get`
over HTTP is destructive and meant for diagnostics. It has no prefetch, no held
delivery and no redelivery on consumer death, and it runs at most once
(`rabbitmq.py:103`).

The gaps are therefore closed by teaching the family (10.e) before vibey uses it:

- **`vibey_bootstrap.amqp`** (new) is the family's RabbitMQ client: robust connection,
  confirming publisher, prefetching consumer, an `AmqpDelivery` whose settle methods
  mirror the Service Bus vocabulary (`complete` = `basic.ack`, `abandon` =
  `nack(requeue)`, `dead_letter` = `reject(requeue=false)`), topology declaration, and
  an in-memory double for tests.
- **`vibey_bootstrap.db.outbox.AsyncOutbox`** (new) adds the same outbox semantics
  over any asyncpg-shaped executor, with `claimed_at` tracking and reclaim of stale
  `sending` rows. The sync API is unchanged.

**The one new third-party dependency is `aio-pika`** (Apache-2.0, asyncio AMQP 0-9-1),
at `>=9.5`. Transitively it brings `aiormq` and `pamqp`. `yarl`, `multidict`,
`propcache` and `idna` are already in `uv.lock` through `aiohttp` (via kopf); they
become base-runtime rather than extra-only.

- It goes in the root `[project] dependencies`, because RabbitMQ is the default and
  `pip install vibey` must run it (ADR-0037).
- It goes in vibey-bootstrap's new `amqp` extra, and in its `all` extra.
- It does **not** go in `vibey-runners-common`, whose `dependencies = []` is what lets
  `domain/` import it, nor in any runner tenant.
- `.importlinter`'s `domain-independence` contract adds `aio_pika`, `aiormq` and
  `pamqp` to its forbidden list. `vibey_bootstrap` is already forbidden there by name.
- `uv lock --check` and `pip-audit` (CI Gate 7) see the new packages in the same
  change.

| layer | new modules |
|---|---|
| `domain/` (pure) | `job_dispatch.py` (envelope, `QueueNames`, `WaitTierPlan`), `dispatch_policy.py` (`DispatchMissPolicy`), `run_protocol.py`; each with a `domain/interfaces/*_interface.py` |
| `application/` | no new port. `RunSpec` gains `supersede_key` and `attempt`, both defaulted; `worker.py` gains `EngineQueueSaturated`, turned into `Defer(capacity=False)` |
| `infrastructure/db/` | `dispatch_records.py` (outbox-writing transitions, fenced claim, sweep, dead-letter park) |
| `infrastructure/queue/` | `rabbitmq_topology.py`, `dispatch_relay.py`, `project_deliveries.py`, `rabbitmq_wakeup.py`, `rabbitmq_job_repository.py` |
| `infrastructure/engines/` | `run_dir.py` (`RunDirTailer`, `RunInbox`), `process_launcher.py` (`EngineProcessLauncher`), extracted from `LoopProcessAdapter` with no behaviour change |
| `infrastructure/loop_service/` | `local_run_executor.py`, `result_store.py`, `host.py`, `control.py`, `client.py`, `adapter.py`, `command_executor.py` |
| `cli/` | `vibey loop-service`, `vibey loop submit` |
| `bootstrap.py` | backend and invocation selection; `build_loop_service` |

Every new class has its mirrored interface (9.b, ADR-0016). Each new `interfaces/`
package joins `.importlinter`'s `infrastructure-interfaces-declare-only` contract.

### 15. Chart

- **The broker is core.** A new `templates/broker.yaml` renders the RabbitMQ Secret,
  PVC, Service and Deployment when `broker.enabled` (default `true`), whatever
  `surfaces.enabled` says. The resource names are unchanged (`<fullName>-rabbitmq`),
  so Plane's broker default, `VIBEY_BUS_URL` and the cluster-smoke availability list
  keep working. Its settings are still read from `surfaces.rabbitmq.*`, so no values
  key moves (12.c). The bus `VibeySurface` CR stays under the surfaces gate.
  `broker.existingSecret` / `broker.existingSecretUrlKey` point at an external broker.
  The in-cluster broker's Secret gains `amqp-url` and `keda-host` keys, and a
  `rabbitmq.conf` ConfigMap sets `consumer_timeout` for the case where a broker
  refuses the queue argument.
- The **worker** gains `VIBEY_QUEUE_BACKEND`, `VIBEY_ENGINE_INVOCATION` and
  `VIBEY_BUS_AMQP_URL`.
- **One Deployment per loop service** (`templates/loop-services.yaml`,
  `loopServices.<engine_id>.{enabled, prefetch, replicas, resources, extraEnv,
  engineAuth}`). qwenloop and opencode are enabled by default (8.b). The paid engines
  and claudeloop-local are declared-only. Each service mounts the worktrees PVC at
  `/work`, and the qwenloop service takes the Ollama wiring the worker has today.
  `terminationGracePeriodSeconds` defaults to 7200.
- **KEDA** follows §12.

### 16. Tests and CI

- One contract suite, `tests/contracts/test_job_queue_contract.py`, runs the
  `JobRepository` contract against both backends. RabbitMQ is used when
  `VIBEY_TEST_AMQP_URL` is set, and CI sets it: the `gates` job gains a
  `rabbitmq:4-management-alpine` service.
- A RabbitMQ chaos twin lives at `tests/infrastructure/queue/test_rabbitmq_chaos.py`.
- The protected files are never edited, and they keep passing:
  `tests/infrastructure/db/test_chaos.py`, `tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/system/test_delivery_stage_set.py`,
  `tests/live/**` (`.vibey-gh.toml:78-85`).
- The PostgreSQL 14–18 matrix is unchanged and also covers the new SQL, so no
  PostgreSQL 15+ feature is used (no `MERGE`).
- The historical suite runs on the backend it was written for: `tests/conftest.py`
  pins `VIBEY_QUEUE_BACKEND=postgres` and `VIBEY_ENGINE_INVOCATION=subprocess` in
  `pytest_configure`.
- New cluster-smoke contracts:
  - each enabled loop service's queue has a consumer;
  - the RabbitMQ `ScaledObject` becomes Ready;
  - the existing contract that a worker drains within 60 s still holds.
- Unit tests reach the 100% floors (ADR-0023) through the in-memory AMQP double, so
  no lane needs a broker on the developer's machine.

## How each non-negotiable still holds

1. **Never block a worker on a human.** Parking is unchanged at the seam (§6). A
   parked job holds no worker, delivery, prefetch slot or KEDA count. A human never
   holds a queue slot in either backend. The new waits are on machines, never people:
   a worker waiting for its run in a saturated engine queue is bounded by
   `run_queue_wait_seconds` and then defers (§13).
2. **Credits ≠ rate limit.** All three layers are unchanged and still apply:
   - the type: `CreditsExhausted` has no `resets_at` (`domain/capacity.py:21-24`;
     `tests/domain/test_capacity.py:28-31`);
   - the property test: `tests/domain/test_circuit.py:86-97`, plus
     `tests/infrastructure/engines/test_classify.py:48-51`;
   - **the CHECK, which still lives in PostgreSQL**: `engine_health.credits_never_have_a_deadline`
     (`migrations/0007_engine_health_rotation.sql:21`;
     `tests/infrastructure/db/test_engine_health_repository.py:111-125`).
     `engine_health` never moves to the broker, and every capacity state is still
     persisted through `EngineHealthService` into that table.

   The broker adds no clock to credits. A capacity defer's wait tier is the probe
   interval the circuit already chooses, never a reset time. The run protocol has no
   capacity field, and a property test on the codec proves no `resets_at` key survives
   encoding. The loop service never interprets capacity, so it can never schedule a
   resume from a credits event.
3. **A capacity rejection outranks a completion claim.** The service reports an exit
   code and a status, never completion (§13). The caller still reads every event from
   `events.jsonl` in order. It still checks `capacity_rejected` before wind-down and
   before `complete` (`build_implement_handler.py:241-263`).
4. **`domain/` stays pure.** The new domain modules are dataclasses, codecs and pure
   policies. No clock is involved: `now` is always an argument. `aio_pika`, `aiormq`
   and `pamqp` join the `domain-independence` forbidden list. `vibey_bootstrap` stays
   forbidden there by name, and `tests/domain/test_domain_purity.py` walks the new
   files.
5. **Dogfood the family.** vibey_bootstrap was checked first (§14). Where it had the
   capability (outbox, replay guard, dead-letter alarm, watchdog, settle vocabulary),
   it is used. Where it lacked one (AMQP transport, async outbox), it is taught before
   vibey uses it. `aio-pika` is the one third-party addition, justified by that
   capability gap, which is written down at `vibey_bootstrap/amqp/__init__.py`.
6. **Everything-as-code, never less configurable (12.c).** Both backends and both
   invocation modes stay selectable. Every tunable is a key: delivery limit, consumer
   timeout, wait tiers, reconcile interval, redispatch window, prefetch per engine,
   supersede grace, queue wait, prefix, vhost, access mode. The broker topology is
   declared by code at start, not clicked. The one mode the RabbitMQ backend cannot
   offer (unbound KEDA) fails the render loudly and stays available on the PostgreSQL
   backend (§12).
7. **A governing rule is a ratified sub-doctrine.** This record states no new rule.
   The rules it leans on are ratified: 8.b names RabbitMQ as the bus surface's sovereign
   default, and 8.c requires every loop to run as one instance fed by a queue (#325).
8. **CDD.** Every lane lands behind the old defaults. The flip is the final lane, after
   the contract suite, the chaos twin and the cluster contracts are green, so any
   divergence is bounded and reversible by one key.
9. **Status is evidence-bounded (10.f).** Every claim here names its file and the
   cutoff (`d47c196d`). Upstream broker behaviours this design relies on are listed
   under *Verification owed*, each with the lane test that will fail if the pinned
   image disagrees.
10. **Code lives in classes with interfaces beside them (9.b).** Every new class has a
    mirrored interface. Each new `interfaces/` package is added to `.importlinter`.
    No lane adds a module-level function.
11. **The handoff no-loss gate.** It is untouched: `domain/noloss.py`,
    `handoff_orchestration.py` and `wind_down.py`. Exit 75 still reaches
    `build_implement_handler.py:249` through `run_exit_code`, and `stop()` still yields
    `StopSummary` from `stop-summary.md` and the snapshot on the shared volume. A lost
    `RunResult` reads the persisted result file. If that is missing too, the exit code
    is `None`, which is a failure and a retry, **never** a wind-down built on missing
    evidence and never a silent partial.
12. **Every job is idempotent under replay.** Handlers still run at least once and
    commit exactly once (§5, §9). What changed is that a run can now outlive its
    caller's lease. The loop service is not killed with the worker, unlike the
    `tini -g` process group today (ADR-0026). The replacement attempt carries the same
    `supersedes.key` with a higher `attempt`, and the service stops the orphan before
    it starts the successor (§13). This is the **riskiest invariant** in the design;
    see *Consequences*.
13. **The ledger is append-only.** The ledger stays in PostgreSQL and its rules are
    unchanged. `job`, `job_outbox` and `dispatch_seq` are mutable queue state, as `job`
    always was; they are not the ledger.
14. **Conventional Commits** and **never implement on `main`**: every lane is a
    Conventional Commit on a storm branch, merged into `develop` by the merge train.

## Evidence flags on the operator's decisions (10.f)

These are stated plainly, without resolving them silently:

- **Decision 3's ratification came after the code cutoff, and is now recorded.** At
  `d47c196d`, 8.b's ratified text named no bus surface and ADR-0042's table had no bus
  row; RabbitMQ as the bus appeared only in ADR-0043 (proposed) and the `BusPort`
  docstring (`application/interfaces/bus.py:11`). The merge of #325 (`472c5c6b`,
  2026-09-22) amended 8.b to name RabbitMQ as the bus default and ratified 8.c, so the
  default this record builds on is now law rather than a choice of this record.
- **Decision 3 says `[bus]` "has no adapter". At the cutoff it has one**
  (`infrastructure/bus/rabbitmq.py`, wired at `bootstrap.py:866-882`). It speaks the
  management HTTP API, runs at most once, and no code reads it. That is why this
  design adds an AMQP client rather than extending that adapter.
- **Decision 1 "moves the queue from PostgreSQL" cannot mean removing PostgreSQL.**
  Three non-negotiables are enforced *by PostgreSQL*: the credits CHECK (layer 3), the
  append-only rules and gapless `seq`, and the fenced exactly-once commit. So is the
  integrate lock (ADR-0029). This design supersedes ADR-0002 only for dispatch and
  keeps PostgreSQL mandatory in both backends. If the operator intended PostgreSQL to
  become optional, that conflicts with non-negotiables 2, 12 and 13 as they are
  enforced today.
- **Decision 2 changes a premise of non-negotiable 12.** "Workers die, the lease
  expires and another worker picks it up" assumed a worker's death ended its work. A
  run in a long-lived service outlives its worker. The non-negotiable still holds only
  because of supersede fencing (§13). That is a new mechanism, and it must hold
  under redelivery, restart and partition.
- **Decision 2's "up to their rate limits"** must be read as a concurrency ceiling the
  operator configures. It is not a schedule the service derives from capacity events,
  which would risk a timed resume after `CreditsExhausted` (non-negotiable 2). The
  service therefore interprets no capacity at all.

## Security impact

The broker becomes an execution capability. Anyone who can publish to
`vibey.runs.<engine_id>` can make that engine's service run its own binary, with
arguments of their choosing, in any `cwd` the service can reach. It cannot run another
binary, choose an environment, or escape `args[0]` validation (§13).

- Broker credentials are therefore secrets on a par with engine API keys: chart
  Secrets, never values in plain text for anything but minikube defaults.
- vibey's objects live under their own prefix and vhost.
- The service validates `cwd` to lie under a configured `[loop_services] root`
  (`/work` in a cluster).

Dispatch messages carry ids, never payloads, prompts or secrets. Run requests carry a
plan *path*, and the plan text stays on the volume. Replies carry at most capped
stdout and stderr, which already go to the diagnostics files today. Credentials in
`amqp-url` and `keda-host` are rendered into Secrets, never into ConfigMaps or args.

## Migration

- Until the final lane, every default is today's behaviour (`postgres`, `subprocess`).
- After the flip:
  - An existing laptop install with no broker fails at start with
    `QueueBackendNotConfigured`, naming two fixes: install a broker
    (`vibey install --rabbitmq`), or set `VIBEY_QUEUE_BACKEND=postgres` and
    `VIBEY_ENGINE_INVOCATION=subprocess`.
  - An existing cluster gets the broker even with `surfaces.enabled=false`.
  - `keda.enabled` with the default backend now requires `worker.project`.
- **Switching a live project between backends needs no data migration.** Moving from
  PostgreSQL to RabbitMQ, the first `reap()` sweeps every claimable row at generation 0
  into the outbox. Moving back, the PostgreSQL claim ignores `dispatch_seq`, and stale
  broker messages are simply never consumed.

## Consequences

**Good.**

- Wakeups are pushed, not polled.
- Concurrency per engine is declared, not accidental, and one local model is shared
  in an orderly way.
- Worker-killing jobs are bounded on both backends, which closes a latent ADR-0024 gap.
- KEDA counts in-flight work, and parked, delayed and blocked jobs stay invisible to it.
- Workers no longer need engine binaries or engine credentials in service mode.
- The queue contract is proven against two implementations by one suite.
- The family gains an AMQP client and an async outbox that any adopter can use.

**Bad.**

- **Riskiest invariant: idempotency under replay across the worker→service boundary.**
  Two lease authorities exist, and PostgreSQL arbitrates every commit. A run can
  outlive its job's lease, and the successor must stop it first. A defect in supersede
  would let two attempts edit one worktree. The chaos twin and the supersede tests in
  the loop-service lanes are the evidence this record owes before the flip.
- A laptop now needs two daemons by default (PostgreSQL and RabbitMQ). That doubles
  ADR-0002's "main cost". The PostgreSQL and subprocess modes remain the one-daemon
  path.
- More moving parts: an outbox relay, a reconciler, wait tiers, dead queues, per-engine
  services, and a shared volume that must be `ReadWriteMany` or pinned to one node.
- The RabbitMQ backend's ordering is FIFO with best-effort priority, weaker than the
  PostgreSQL backend's strict priority.
- A delay can arrive early and hop again, and duplicate dispatches circulate until
  their episode ends. Both are harmless, but they are extra traffic.
- Importing `vibey_bootstrap` loads its whole package `__init__`, which soft-fails
  without Azure. That is start-up cost in the worker and the service.
- `job_outbox` grows. `sent` rows are not ledger and may be pruned; pruning is a
  follow-up, not part of this record.
- `vibey doctor --conformance` in service mode needs a worktree on the shared volume
  (`/work/.vibey-conformance` in a cluster).

## Alternatives rejected

- **Move all queue state into RabbitMQ.** The broker has no durable deduplication, no
  DAG and no fenced compare-and-set. The gate-answer atomicity and three
  non-negotiable enforcement layers need PostgreSQL anyway (§1).
- **Reuse the management-HTTP `RabbitMqBusAdapter`.** It runs at most once, has no
  prefetch and no redelivery, and uses a diagnostics endpoint (§14).
- **Acknowledge on claim, with only PostgreSQL holding the lease.** It is simpler, but
  it loses crash redelivery, the consumer timeout, the delivery-limit poison bound,
  and the in-flight KEDA count, which are the reasons for the move.
- **The delayed-message exchange plugin.** It is community-maintained, absent from the
  official image, and does not replicate (§2).
- **Per-message TTL on one wait queue.** Head-of-line expiry would block short delays
  behind long ones (§2).
- **Run each runner in-process inside the service.** That would duplicate six runners'
  internals into vibey, bypass the protected CLI conformance suite, and pull runner
  SDKs into the service's import graph (§13).
- **Put the AMQP client in `vibey-runners-common`.** It would break that package's
  `dependencies = []`, which is what lets `domain/` import it.
- **A new runner-side `serve` subcommand in each of the six tenants.** It would mean
  six copies of a consumer, six new dependency declarations and six sets of tenant
  gates, all for the same host logic.
- **Silently fall back to the PostgreSQL backend when no broker is configured.**
  ADR-0002 forbids silent defaults in exactly this place.

## Verification owed at implementation (upstream facts, pinned image `rabbitmq:4-management-alpine@sha256:b839b492…`)

Each fact below comes from upstream documentation as recalled at design time. Each is
asserted by an integration test in the lane that relies on it, so a disagreement fails
a lane rather than a cluster:

- the per-queue `x-consumer-timeout` argument is accepted on quorum queues (lane R12);
  the chart's `consumer_timeout` is the fallback;
- quorum-queue `x-delivery-limit` counts channel-close redeliveries (R18's chaos twin),
  and a `nack(requeue=true)` on drain also counts (R14);
- `x-dead-letter-strategy=at-least-once` requires `x-overflow=reject-publish` (R12);
- quorum queues honour two priority levels (R12);
- a TTL-expired message keeps its routing key when dead-lettered without an explicit
  DLX routing key (R13);
- KEDA's `rabbitmq` scaler with `protocol: http` counts unacknowledged messages unless
  `excludeUnacknowledged` is true (R31, cluster contract in R32).
