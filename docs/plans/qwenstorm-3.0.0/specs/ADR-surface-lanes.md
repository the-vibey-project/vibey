# 0047 — Every sovereign surface runs in one lane fed by RabbitMQ: each operation is a message, answers come back on reply queues, and a send whose outcome is unknown is parked, never repeated

**Status:** proposed · **Date:** 2026-09-22 · **Cites:** sub-doctrines 8.b, 8.c, 8.e, 12.c, 10.e (and 8.f, the operator's decision of 2026-09-22, drafted for ratification; 10.f for the evidence rules) · **Related:** ADR-0042 (the surfaces and their ports), ADR-0043 (their Helm install), ADR-0044 (the queue port, the AMQP client, dead letters as parks, idempotency keys), ADR-0045 (the test harness queue), ADR-0046 (the two loops, drafted in parallel), ADR-0016, ADR-0002, ADR-0024 · **Evidence:** the storm integration branch (`develop` plus verified storm lanes) at `391673c2`, read 2026-09-22. Every `file:line` below is at that commit unless it names a storm file (`STORM/…`). ADR-0044's lanes R01–R34 and ADR-0045's lanes T01–T28 are specifications, not code: where this record builds on one, it names the lane. The Redis timings in §10 were measured on 2026-09-22; the AMQP timings are estimates, labelled as such.

**Owes:** the ratification of 8.f, with the amendments asked for under *Where the operator's rule conflicts or falls short*. The measurement named in §10, recorded here before lane S33 flips the default. The docs wave (lane S34): `docs/reference/cli.md` (`vibey surface serve|ping|dead-letters|requeue`), `docs/reference/configuration.md` (`[surfaces]`, `[surfaces.cache]`), `docs/plans/data-model.md` (`surface_operation`, `surface_dead_letter`), `docs/plans/architecture-and-roadmap.md`, the paper's queue section, the four agent-surface trees, CHANGELOG, and the ADR count (`tests/meta/test_adr_counts.py`).

## Context

### The rule

The operator's decision of 2026-09-22, final, to be ratified as sub-doctrine 8.f:

> Every sovereign surface runs in a single lane, driven by RabbitMQ.

It names the surfaces of 8.b's list (`src/vibey_tools/gh/docs/doctrines.md:125-151`) and explicitly includes the Redis cache: tracker (Plane), docs (BookStack), secrets (OpenBao), files (Nextcloud), email (SMTP/Postfix), SMS (Kannel), messaging (Matrix/Synapse), configuration (Infisical), cache (Redis), blob storage (Garage) and security events (Wazuh). "Single lane" means one consumer instance per surface per deployment, as 8.c holds for loops (`doctrines.md:173-198`). "Driven by RabbitMQ" means every operation on the surface is a message on its queue, with dead-letter queues and idempotency, as 8.e holds for the test harness (`doctrines.md:222-242`).

### The surfaces today

Each surface is an application port with a sovereign adapter and an in-memory adapter (ADR-0042). `build_app` picks one per surface and puts it in `AppResources` (`src/vibey/bootstrap.py:159-170`, yielded at `:939-950`).

| surface | port (`src/vibey/application/interfaces/`) | operations | sovereign adapter (`src/vibey/infrastructure/`) | wired at `bootstrap.py` |
|---|---|---|---|---|
| tracker | `tracker.py:8-17` `IssueTrackerPort` | `create_ticket`, `get_ticket_status` | `tracker/plane.py:17-86` (urllib) | `:751-765` |
| docs | `docs.py:8-17` `DocsPort` | `create_page`, `update_page` | `docs/bookstack.py:17-76` (urllib) | `:767-780` |
| secrets | `secrets.py:8-17` `SecretsPort` | `get_secret`, `set_secret` | `secrets/openbao.py:26-73` (urllib, KV v2) | `:782-788` |
| files | `files.py:8-17` `FilesPort` | `upload_file`, `download_file` | `files/nextcloud.py:18-67` (WebDAV) | `:790-802` |
| email | `email.py:8-13` `EmailPort` | `send_email` | `email/forward_email.py:16-56` (smtplib) | `:804-813` |
| sms | `sms.py:8-13` `SmsPort` | `send_sms` | `sms/kannel.py:22-60` (sendsms CGI) | `:815-828` |
| messaging | `messaging.py:8-13` `MessagingPort` | `send_message` | `messaging/matrix.py:18-47` (client-server API) | `:830-836` |
| configuration | `config_store.py:9-13` `ConfigStorePort` | `create_config`, `get_config` | `config_store/infisical.py:16-91` (urllib) | `:838-855` |
| cache | `cache.py:8-21` `CachePort` | `get`, `set`, `delete` | `cache/redis.py:53-91` (stdlib RESP) | `:857-864` |
| bus | `bus.py:8-26` `BusPort` | `declare_queue`, `publish`, `consume` | `bus/rabbitmq.py:25-114` (management HTTP) | `:866-882` |
| blob | `blob.py:8-19` `BlobPort` | `put_blob`, `get_blob` | `blob/garage.py:54-159` (S3 SigV4) | `:884-901` |
| security events | `siem.py:8-18` `SiemPort` | `send_event` | `siem/wazuh.py:23-54` (indexer API) | `:903-914` |

Every sovereign adapter does its I/O in a thread (`asyncio.to_thread`), opens a new connection per call, and passes no timeout to `urlopen` (for example `plane.py:31` and `:61`). `RedisCacheAdapter` opens, authenticates, selects and closes a TCP connection for every command (`redis.py:64-78`).

### Who calls them: nobody yet

No production code reads any surface port. Searching `src/` for `resources.<surface>`, the port method names and the port types, at `391673c2`, finds only the wiring in `bootstrap.py` and the port declarations. The only exercise is the adapter test file `tests/infrastructure/test_sovereign_surfaces.py`. Notifications go to desktop alerts and signed webhooks (`src/vibey/infrastructure/notify/service.py:14-26`), not to the email, SMS or Matrix ports. The cache in particular has no reader: `CachePort` appears at `bootstrap.py:49`, `:167`, `:860`, `:864` and `:947`, and nowhere else.

This is the most important fact in the record. Every cost below is prospective. Nothing that runs today gets slower when this lands, and the first consumer of each surface will be written against the lane, not migrated to it.

The only memo on a per-call path in `src/vibey` is `LoopProcessAdapter`'s process-local `_help_text_cache` (`src/vibey/infrastructure/engines/loop_process_adapter.py:68`, `:231-264`). It memoizes a binary's `--help` text in a dictionary. It is not the cache surface, and moving it behind a broker would turn a dictionary hit into a network round trip for nothing (§10).

### What each operation needs back

Classified by the port contract, since there is no caller to classify by:

- **Needs an answer:** `create_ticket` (the id), `get_ticket_status`, `create_page` (the id), `get_secret`, `upload_file` (the URL), `download_file`, `get_config`, cache `get`, `put_blob` (the locator), `get_blob`.
- **Needs to know it was applied** (the port returns `None`, but `await` means "done" today): `update_page`, `set_secret`, `create_config`, cache `set` and `delete`.
- **Fire-and-forget:** `send_email`, `send_sms`, `send_message`, `send_event`. `SiemPort` already says so: "a sink that is down must not fail the work that produced the event" (`siem.py:12-13`).

### What exists to build on

- **ADR-0044's AMQP client** (lane R04): `vibey_bootstrap.amqp` with a confirming publisher, prefetching consumers, `AmqpDelivery.complete/abandon/dead_letter`, `get`, and `InMemoryAmqpClient` for tests.
- **ADR-0044's conventions:** quorum queues with a delivery limit and at-least-once dead-lettering (§2), `start_by` in the body instead of an AMQP expiration (§13), "persist the result, then publish, then acknowledge" (§13), dead letters as parks (§8), and the idempotency-key table (§9).
- **R17's `QueueBackendSettings`:** the AMQP URL, vhost and prefix, with their precedence.
- **R22's host shape:** decode, dedupe a redelivery that is still active, reply, then settle.
- **ADR-0045:** `x-single-active-consumer` on a service queue (§12), and dead letters recorded with their evidence where a human can see them (§9).
- **The family:** the consumer watchdog (`vibey_bootstrap.heartbeat`), `ReplayGuard` (`servicebus/async_ext.py:26-49`), and the retry conventions (`retry/__init__.py:41-130`).

### What does not fit

- **One lane has two queues** (§4), and `x-single-active-consumer` is per queue. Two processes could each become active on a different queue. The family has no primitive for "one owner across several queues".
- **The family's retry is sync only.** `build_retry` wraps a sync function (`retry/__init__.py:85-86`), and tenacity reaches vibey only transitively, through `google-genai` (`uv.lock:1744`).
- **The family has no general bounded memo with expiry.** `identity.TokenCache` (`identity/__init__.py:245`) is token-specific module state.
- **`human_gate.project_id` is `NOT NULL`** (`migrations/0008_human_gate_artifact_budget.sql:3`), and a surface operation belongs to no project. So a parked surface operation cannot be a gate row, the same finding as ADR-0045 §3.
- **Two backends cannot deduplicate.** SMTP and Kannel's sendsms have no idempotency key, so a repeated send is a second message. BookStack's page create has none either.
- **Some arguments are secrets or bytes.** `set_secret` and `create_config` carry values, and `upload_file` and `put_blob` carry bytes. ADR-0044's messages carry only ids.
- **The Redis adapter's test pins its exact commands** (`tests/infrastructure/test_sovereign_surfaces.py:1026-1034`), so the adapter cannot grow a key prefix or a persistent connection without changing those tests.

## Decision

**The cache server is Valkey** (the operator's ruling of 2026-09-22): the installer and the chart run Valkey, the BSD-licensed server of the Redis protocol, which is Arch Linux's official package. 8.b's "Redis" names the protocol vibey speaks; the adapter, its commands and everything below are unchanged, and the §10 measurements, taken against Redis 8.8.0, are re-taken against Valkey before S33 flips the default.

### 1. The lane, the instance, the deployment

- A **surface lane** is the one consumer instance that performs every operation vibey makes on one surface. It owns the surface's credentials and its sovereign adapter, and nothing else in vibey talks to that surface.
- A **deployment** is one machine or one cluster, as in 8.c.
- **One instance.** Three things enforce it:
  1. **A broker lease.** A lane first declares an exclusive, auto-delete queue named `<prefix>.surface.<name>.lock`. RabbitMQ lets only one connection own an exclusive queue; any other connection is refused with `RESOURCE_LOCKED`. The holder is the instance. A second process that is started stays a **standby**: it polls for the lease and consumes nothing. The lease covers both of the lane's queues, which `x-single-active-consumer` cannot do.
  2. **`x-single-active-consumer`** on both queues, as defence in depth.
  3. **In a cluster, one Deployment per lane** with `replicas: 1` and `strategy: Recreate`.
- **When the connection is lost, the lane exits.** It does not try to reclaim its lease. The supervisor restarts it, and the restarted process takes the lease again. This is 8.c: "a restart, never a second copy".
- **Capacity inside the instance is a key; the instance count is not.** Reads run concurrently up to `read_prefetch` (default 64), which is the "as much work at once as its capacity allows" of 8.c. The write queue is consumed with prefetch 1, because FIFO order of writes is what makes replaying an overwrite safe (§8).
- **The replica count is not a key.** A key that could only be set to a value the law forbids is not configurability; ADR-0045 §1 argues the same for the harness.

### 2. The transport is an adapter; the ports stay

For the application layer nothing changes. The transport is one more adapter per port, as ADR-0044 §1 left `JobRepository` alone.

`[surfaces] transport` (`VIBEY_SURFACES_TRANSPORT`) chooses one of two values in `build_app`:

| transport | what `AppResources.<surface>` holds | status |
|---|---|---|
| `queue` | `Queued<Surface>` adapters that publish to the lane (§6, §7) | the default after lane S33 |
| `direct` | today's adapters, chosen exactly as today | the default until S33; kept per 12.c for unit tests and for deployments without a bus |

- **No silent fallback.** `queue` without an AMQP URL fails at start with `SurfaceTransportNotConfigured`, which names both remedies. This follows ADR-0002 and ADR-0044 §1.
- **`direct` is loud after the flip.** From S33 on, `build_app` logs a warning that 8.f is not held when `direct` is chosen and any surface resolved to a real adapter.
- **The lane uses the same adapters `direct` does.** `DirectSurfaceFactory` (lane S14) is today's selection code (`bootstrap.py:751-914`) moved into one class. `direct` calls it inside every process; the lane calls it once, inside itself. Nothing is implemented twice.
- **The in-memory adapters keep working** in two places. Unit tests run with `direct` and in-memory adapters, exactly as today. A lane whose surface has no credentials serves the in-memory adapter, and says so at start (`backend=InMemoryTracker`). That is a behaviour change for the better: one shared fake per deployment, where each process had its own before.

**The one port change is additive.** The six operations that create something or send something gain an optional keyword, `idempotency_key: str | None = None`:

- `create_ticket` and `create_page`;
- `send_email`, `send_sms`, `send_message` and `send_event`.

A caller that replays, such as a job handler after a worker died, can then pass a stable key and be answered once. Every implementation gains the parameter (lanes S04–S06). Where the backend supports a key, the sovereign adapter uses it natively (§8). Without a key, behaviour is exactly today's.

### 3. The operation catalogue

One pure table in `domain/surface_catalogue.py` (lane S02) declares, for every operation, what goes on the wire and how it may be retried. The client, the lane, the codec and the redaction all read it.

- The **reply mode** is `answer` (a result comes back), `ack` (the lane confirms the operation was applied) or `accept` (the broker's publisher confirm is the answer).
- The **idempotency class** is one of four:
  - `read`: the operation changes nothing.
  - `overwrite`: repeating it leaves the same state.
  - `native`: the backend deduplicates by a key vibey supplies.
  - `guarded`: the backend cannot deduplicate, so the lane guards it (§8).

| surface | operation | reply | class | not found raises | notes |
|---|---|---|---|---|---|
| tracker | `create_ticket` | answer | native | — | Plane `external_source="vibey"`, `external_id=<op_id>`; a 409 carries the first ticket's id (verification owed) |
| tracker | `get_ticket_status` | answer | read | `KeyError` | |
| docs | `create_page` | answer | guarded | — | BookStack has no key |
| docs | `update_page` | ack | overwrite | `KeyError` | a full-content PUT |
| secrets | `get_secret` | answer | read | `KeyError` | the result is sensitive |
| secrets | `set_secret` | ack | overwrite | — | `value` is sensitive. A replay writes one more KV version with the same value |
| files | `upload_file` | answer | overwrite | — | `content` is bytes; WebDAV PUT to a fixed path |
| files | `download_file` | answer | read | `FileNotFoundError` | |
| email | `send_email` | accept | guarded | — | `Message-ID` derived from the key (a courtesy to receivers, not a guarantee) |
| sms | `send_sms` | accept | guarded | — | |
| messaging | `send_message` | accept | native | — | Matrix `txnId = vibey-<op_id>`; the server deduplicates per access token (verification owed) |
| configuration | `create_config` | ack | overwrite | — | `value` is sensitive. On failure, the lane reads `get_config(key)`; the stored value equal to the requested one means a replayed create, which succeeded |
| configuration | `get_config` | answer | read | `KeyError` | |
| cache | `get` | answer | read | — | on the read queue, served from the lane's memo (§10) |
| cache | `set` | ack | overwrite | — | |
| cache | `delete` | ack | overwrite | — | |
| blob | `put_blob` | answer | overwrite | — | `content` is bytes; S3 PUT |
| blob | `get_blob` | answer | read | `FileNotFoundError` | |
| security events | `send_event` | accept | native | — | Wazuh indexer `PUT /<index>/_doc/<op_id>`: a repeat overwrites the same document |
| every lane | `_ping` | answer | read | — | answered by the lane itself: instance, backend, start time |

### 4. Topology

Every name uses `[bus] prefix` (default `vibey`) and `[bus] vhost` (lane R01), resolved by R17's `QueueBackendSettings`. `<name>` is the surface's catalogue name. The bus has no lane (§11).

| object | type | arguments / bindings | purpose |
|---|---|---|---|
| `<prefix>.surface` | **topic** exchange, durable | — | requests. It is a topic exchange, with exact keys only, so that RabbitMQ topic permissions can grant a caller some surfaces and not others (see *Security impact*) |
| `<prefix>.surface.<name>` | quorum queue | key `<name>`; `x-single-active-consumer: true`, `x-delivery-limit` (`delivery_limit`, default 5), `x-dead-letter-exchange=<prefix>.surface.dlx`, `x-dead-letter-strategy=at-least-once`, `x-overflow=reject-publish`, `x-max-length` (`write_max_length`, default 100 000), `x-consumer-timeout=consumer_timeout_seconds × 1000` (default 900 s) | every operation except reads: persistent, publisher-confirmed, consumed with prefetch 1 |
| `<prefix>.surface.<name>.read` | classic queue, durable | key `<name>.read`; `x-single-active-consumer: true`, `x-dead-letter-exchange=<prefix>.surface.dlx`, `x-overflow=reject-publish`, `x-max-length` (`read_max_length`, default 10 000) | reads: transient messages with no confirm wait, consumed with prefetch `read_prefetch` |
| `<prefix>.surface.dlx` | direct exchange, durable | — | poison and evidence |
| `<prefix>.surface.<name>.dead` | quorum queue | keys `<name>` and `<name>.read` on the DLX | dead letters in transit to their record (§9) |
| `<prefix>.surface.<name>.lock` | classic queue, exclusive, auto-delete | none | the lane's lease (§1) |
| caller reply queue | classic, exclusive, auto-delete, server-named | named in `reply_to` | answers for one caller process |

Why reads get their own queue:

- A quorum queue commits every message to its Raft log before it delivers it. That is a write to disk on the read path, and §10 shows what that costs.
- A classic queue holding transient messages does not. A read lost when the broker restarts is simply asked again, because reads are idempotent.
- Writes keep the quorum queue's durability, its delivery limit and its at-least-once dead-lettering.

The client and the lane both declare the topology (lane S15) with the same arguments. Declaring twice is harmless, and a request published before its lane ever started still routes, and waits.

### 5. The wire protocol

`domain/surface_protocol.py` (lane S03) is pure and versioned, and its codec is strict, like R19's. Decoding rejects an unknown schema, a missing key, any extra key, a wrong type, a naive datetime, an unknown surface or operation, and an `op_id` outside `^[A-Za-z0-9._:-]{1,200}$`. An extra key is always rejected, so a `resets_at` can never ride along (non-negotiable 2).

| message | body (JSON) | AMQP properties |
|---|---|---|
| `vibey.surface.request/1` | `request_id, op_id, surface, operation, args, requested_at, start_by, caller, grant` | `message_id = correlation_id = request_id`, `type = surface.request`, `reply_to` (omitted for a send when `sends_await_outcome` is false); `delivery_mode` 2 on the write queue, 1 on the read queue; **no `expiration`** |
| `vibey.surface.reply/1` | `request_id, op_id, status, result, detail, replayed, instance, finished_at` | `correlation_id = request_id`, `type = surface.reply`, `delivery_mode` 1 |
| `vibey.surface.dead/1` | `surface, operation, op_id, request_id, reason, detail, attempts, delivery_count, instance, dead_lettered_at, request (redacted), retained` | `message_id = <request_id>:<reason>`, `type = surface.dead`, persistent, confirmed |

- **Arguments are typed by the catalogue.** Bytes travel as `{"b64": …}`. A request whose encoded body exceeds `inline_max_bytes` (default 8 MiB, which stays under the broker's own message-size limit after base64) is refused **before** it is published, with `SurfacePayloadTooLarge`. The error names the key.
- `status` is one of `ok`, `not_found`, `error`, `rejected`, `expired` or `parked`.
- **No reply claims more than the operation.** A reply reports an operation on a surface. It carries nothing about engines, capacity or completion.

### 6. Operations that need an answer: request and reply

The caller side is one `SurfaceLaneClient` per process (lane S16). The `Queued<Surface>` adapters (lanes S20–S22) are thin classes over it.

1. On first use the client declares one reply queue (server-named, exclusive, auto-delete) and consumes it. Each reply is routed to its waiting call by `correlation_id`. A reply nobody is waiting for is acknowledged and dropped.
2. It builds the request:
   - `request_id` is a fresh UUID for this publish.
   - `op_id` is the caller's `idempotency_key`, or a fresh UUID when there is none.
   - `start_by` is `requested_at` plus a window: `read_timeout_seconds` (default 5) for a read, or `write_timeout_seconds` (default 30) for any other operation that answers.
3. It publishes:
   - a read to `<name>.read`, without waiting for a confirm (§10);
   - anything else to `<name>`, waiting for the publisher confirm.
4. It waits for the reply for at most `(start_by − now) + operation_timeout_seconds + 1 s`.

**The lane refuses to start an operation after its `start_by`.** It answers `expired` instead. Once it has started an operation, `operation_timeout_seconds` (default 60) bounds it. A caller that waited out its whole window can therefore say something exact: no lane started the operation in time, so it was not applied. The one exception is stated in *Consequences*: an adapter call that runs past its bound in its thread.

**What the caller sees:**

| situation | read | answer / ack |
|---|---|---|
| the lane answers | the result, or the port's own not-found error (`KeyError` or `FileNotFoundError`) | the same |
| the backend failed | `RuntimeError`, as the direct adapter raises today | the same, after the lane's bounded retries (§8) |
| the broker is unreachable | `SurfaceLaneUnavailable` at once | the same |
| the lane is down or restarting | `SurfaceLaneUnavailable` after 5 s. The request expires unread | `SurfaceLaneUnavailable` after the window. The request waits in the quorum queue until the lane returns, which then answers `expired` to nobody and applies nothing |
| the queue is full (`reject-publish`) | the publish is dropped, so it times out | the confirm is a nack: `SurfaceLaneUnavailable` at once |
| the operation is parked (§9) | — | `SurfaceOperationParked` |

- `SurfaceLaneUnavailable` and `SurfaceOperationParked` subclass `RuntimeError`, so any code that handles today's adapter errors handles these too. Their messages name the lane to start (`vibey surface serve <name>`) or the command to inspect (`vibey surface dead-letters`).
- **The caller never falls back to calling the backend directly.** That would be a second path to the surface, which is what 8.f forbids.

### 7. Operations that are one-way: sends

`send_email`, `send_sms`, `send_message` and `send_event` use the `accept` mode.

- The caller's `await` returns once the broker has confirmed a persistent publish to the lane's quorum queue. The send is then durable. If the lane is down it waits, and it goes out when the lane returns.
- **A send can go stale.** Its `start_by` is `requested_at + send_start_by_seconds` (default 86 400). A send still unsent after that is not sent. It becomes a dead letter with reason `expired`, so a message that never went out is visible, never silently dropped.
- **Failure no longer reaches the caller.** The lane's outcome is a dead letter with evidence (§9), not an exception in the caller. For the SIEM that is already the port's contract (`siem.py:12-13`). For email, SMS and messaging it is a real change from today, where `await send_email()` raises on an SMTP error.
- `[surfaces] sends_await_outcome = true` restores an `ack` round trip for operators who want the error in the caller (12.c).

### 8. Idempotency keys

| what | key | enforced by |
|---|---|---|
| one publish | `request_id` = `message_id` = `correlation_id` | reply routing. The lane keeps a map of the requests it is executing, so a redelivery of one that is still running (a channel blip) starts nothing (as R22 rule b) |
| one logical operation | `op_id`: the caller's `idempotency_key`, or a fresh UUID per call | per class, below |
| `read` | none needed | a read is naturally idempotent. A redelivered read is simply read again |
| `overwrite` | none needed | the write queue is FIFO with prefetch 1 and a single active consumer. A delivery is redelivered only if it was never settled, and then nothing after it has run yet, so a replay cannot reorder writes. `create_config` also verifies by reading back (§3) |
| `native` | `op_id` given to the backend | Matrix `txnId`, the Wazuh document id, Plane `external_id`. A redelivery re-executes, and the backend answers the duplicate |
| `guarded` | `(surface, op_id)` in `surface_operation`, plus `request_digest` | see below |

**Guarded operations** are `create_page`, `send_email` and `send_sms`. The lane writes an intent row **before** the effect and a result row **after** it (lanes S10, S11, S24). What it does depends on the row it finds:

- **None:** insert `started` and execute.
- **`done`:** reply with the recorded result and `replayed=true`. Nothing is sent again.
- **`started`:** an earlier delivery began and never finished, so the outcome is unknown. The lane **parks** it (reason `outcome_unknown`) and sends nothing. This is how "a send must not be delivered twice on redelivery" holds for a backend that cannot deduplicate. The price is that a crash in the middle of a send asks a human, rather than guessing.
- **`failed`:** the previous attempt failed before any effect, so executing again is safe.
- **`parked`:** answer `parked` at once, unless the request carries a grant (§9).
- **A different `request_digest` under the same `op_id`:** reject with "idempotency key reused with different arguments". A caller's bug is never executed.

**Which failures are retried** (lane S17) depends on the class:

- A **read** is never retried inside the lane. It fails fast, and the caller decides.
- An **`overwrite` or `native`** operation is retried on transport errors: `OSError`, a timeout, and HTTP 5xx or 429. The waits are `retry_backoff_seconds` (default 1, 5 and 30 s), and the retry is the family's (lane S08).
- A **`guarded`** operation is retried only on errors raised **before** anything was sent: connection refused, name resolution, `SMTPConnectError`. Any other transport error, or a timeout, is `outcome_unknown` and parks.
- Everything else is permanent.

Retries block the write queue (FIFO), and they are bounded.

### 9. Dead letters are parks

This is ADR-0044 §8's pattern and ADR-0024's grant, recorded as ADR-0045 §9 records test runs.

| what is dead-lettered | how it gets to `<prefix>.surface.<name>.dead` |
|---|---|
| a malformed message, or one for the wrong surface | the lane calls `dead_letter()`; the broker adds `x-death` |
| a message that killed the lane `delivery_limit` times | the quorum queue's delivery limit |
| retries exhausted on a send; a permanent failure of a send; a send past its `start_by`; an unknown outcome; a reused key on a send | the lane publishes a `vibey.surface.dead/1` evidence message to the DLX (confirmed), **then** completes the original delivery |

- **Where a caller is waiting** (answer or ack), a failure is **replied**, not dead-lettered. The caller has the error in hand, exactly as with a direct call today. Only outcomes that nobody would otherwise see become dead letters.
- **The park.** Every `reconcile_interval_seconds` (default 30), the lane drains its dead queue into `surface_dead_letter` rows (lane S25). A row is written once, keyed by `(surface, dedupe_key)`. For a guarded operation, the drain also moves `surface_operation` to `parked`, so any later request with that `op_id` is answered `parked` at once. **Nothing waits for a human**, and nothing is retried forever.
- **Evidence.** Each row holds the surface, the operation, `op_id` and `request_id`, the reason, a detail capped at 2 000 characters (the exception type and message), attempts, the delivery count, the lane instance, the time, and the request with its arguments **redacted**. A sensitive argument becomes `sha256:<digest>`. A bytes argument becomes its length and digest. `retained` says whether the request can be rebuilt from the row.
- **Seeing them.** `vibey surface dead-letters [--surface NAME] [--json]` (lane S28) reads PostgreSQL, so it works while a lane is down.
- **The grant.** `vibey surface requeue <id>` republishes a retained request with `grant: true` and a new `request_id`. It then marks the row answered, once. The dead letter itself is never rewritten. A request that is not retained (it carried a secret or bytes) cannot be requeued from its row, and the command says so and names the caller as the only place the value exists.
- **Why PostgreSQL.** It is already required (ADR-0002's `DatabaseNotConfigured`), and ADR-0044 §1 puts truth there. The rows are readable with every lane down, and a `human_gate` row is impossible (*Context*). `surface_operation` and `surface_dead_letter` are mutable operational state, like `job` and `job_outbox` (ADR-0044, non-negotiable 13). They are not the ledger.

### 10. The cache, honestly

A cache read now crosses the broker twice. That cost is real and it is not hidden here.

**What a read costs.** The Redis rows were measured on 2026-09-22 on the operator's laptop: macOS 26.6.2 on arm64 with 10 cores, Python 3.14.7, Redis 8.8.0, over loopback. Each mode ran 5 000 GETs of a 64-byte value, twice. That run was ad hoc from the design session; lane S32 makes it a tracked, repeatable measurement. The queue rows are **estimates**: no broker was reachable from the design session.

| path | p50 | p99 | source |
|---|---|---|---|
| today's `RedisCacheAdapter.get` shape: a new TCP connection, GET, close, through `asyncio.to_thread` (`redis.py:64-81`) | 0.18 ms | 0.42–0.51 ms | measured |
| one persistent asyncio connection, one GET per round trip | 0.08 ms | 0.17–0.21 ms | measured |
| pipelined, 16 GETs per round trip, cost per GET | 0.006 ms | 0.011–0.033 ms | measured |
| queue transport, a hit in the lane's memo | ≈ 0.4–1.0 ms | ≈ 2–5 ms | estimated: four aio-pika publish and deliver steps at ≈ 50–100 µs each, two broker hops at ≈ 30–100 µs each, the JSON codec, and event-loop jitter |
| queue transport, a memo miss | ≈ 0.5–1.1 ms | ≈ 2–5 ms | estimated: the above, plus one Redis round trip that may be shared with other reads |
| reads on the quorum queue with confirms (rejected) | ≈ 1.5–5 ms | ≈ 5–20 ms | estimated: a Raft commit, which is a disk sync, on every read |

A cache read through the lane is therefore, by estimate:

- 2 to 6 times today's adapter at p50, and 4 to 10 times at p99;
- 5 to 12 times a persistent Redis connection;
- about 100 times a pipelined GET.

The throughput ceiling is also one process: an estimated 5 000 to 15 000 reads per second for aio-pika in one Python process, against Redis's own hundred thousand and more. That is the ceiling on cache reads for a whole deployment.

**Hot paths today: none.** The cache has no reader (*Context*). The only per-call memo is process-local (`loop_process_adapter.py:68`) and is not the cache surface.

**How the design keeps the rule without making the cache pointless.**

1. **Reads avoid the disk.** They go to a classic queue as transient messages, with no publisher-confirm wait (§4). The confirm alone would add a broker round trip, and the quorum queue a disk sync.
2. **The lane has its own connection.** `PipelinedRedisCache` (lane S13) keeps one persistent asyncio connection. It authenticates and selects once, and pipelines. That takes the Redis half from 0.18 ms to 0.08 ms, or 0.006 ms per GET when batched.
3. **Concurrent reads are batched.** Every read the lane has buffered (up to `read_prefetch`) that is waiting in the same event-loop turn goes to Redis in one pipeline of `GET` and `PTTL`. There is no timer, so batching adds no latency when there is only one reader.
4. **The lane owns a read-through memo.**
   - It is a bounded memo with expiry, from the family (lane S09), 10 000 entries by default. A hit touches no Redis at all.
   - It is coherent because the lane is the **only writer** of vibey's cache keys. Every `set` and `delete` passes through it and updates the memo when the write is applied.
   - A memo entry never outlives Redis's own expiry, which is read with `PTTL` on every fill.
   - A read that raced a write is never memoized: every write bumps a generation counter, and a fill is discarded if the counter moved while the read was in flight.
   - **The precondition is stated, not assumed.** Nothing else writes vibey's Redis database. In the chart vibey's cache is database 0 (`deploy/helm/vibey/templates/worker.yaml:235`) and Plane's is database 1 (`templates/plane.yaml:21`). An operator who points another writer at database 0 breaks the memo's coherence.
   - The memo is one cache inside the one instance, so it is not a second cache beside the lane.

**What the mitigations cannot remove** is the two broker hops. That is the price of 8.f for the cache, and this record does not exempt reads to avoid paying it.

**What that leaves the cache good for.** The cache remains worth using when the value costs well over the lane's p99 (≈ 5 ms) to produce, or when it must be **shared** between processes. Examples: HTTP answers from Plane, BookStack or Infisical, which take tens of milliseconds; model-catalogue probes; rendered artefacts; any result another process should reuse.

**What it is pointless for.** Sub-millisecond memoization inside one process. That is not a use of the cache surface: a process-local dictionary is not a sovereign surface, and it stays local. The line is drawn at **shared** state. Anything another process must see goes through the lane. The operator may want that line ratified with 8.f, so that it cannot be stretched into a way around the rule.

**The measurement owed** (lane S32, `scripts/bench_surface_lanes.py`), before lane S33 flips the default:

- **Modes:** p50, p95 and p99 latency and throughput for four modes: the direct adapter, `PipelinedRedisCache`, the queue with a memo hit, and the queue with a memo miss.
- **Load:** concurrency 1 and 16, 10 000 operations each after a warm-up.
- **Images:** the pinned `redis:8-alpine` and `rabbitmq:4-management-alpine`.
- **Machines:** once on the operator's laptop and once on a Linux node.

The JSON is recorded in this record's evidence. **The operator then decides**, in writing, whether the measured p99 is acceptable. If it is not, the choices are the operator's, not this record's:

- keep the cache for costly and shared values only, which is this design's posture;
- amend 8.f to exempt cache reads;
- drop the cache surface.

Two optimizations are held back until that measurement exists: RabbitMQ's direct reply-to, which saves the reply queue, and a `CachePort.get_many`, which spends one round trip on many keys.

### 11. The bus is exempt, and how

RabbitMQ is the medium the lanes run on. A bus lane would put a request for the bus on the bus: the thing being driven would have to be up for anything to reach it, and every publish would need a publish first. So:

- **The broker is already one instance per deployment.** Its Deployment has `replicas: 1` and `strategy: Recreate` (`deploy/helm/vibey/templates/surfaces.yaml:151-160`, moved unchanged to `broker.yaml` by R29). Every lane, worker, loop service and harness connects to that one broker, which is where their waiting is ordered. The broker satisfies "one instance" by being the thing that orders everyone else.
- **The AMQP connection each lane uses is transport, not an operation on a surface.** It is `vibey_bootstrap.amqp` (R04).
- **`BusPort` stays direct in both transports.** It is the management-HTTP adapter (`bus/rabbitmq.py:25-114`). ADR-0044 §14 already ruled it out as a transport: it runs at most once and uses a diagnostics endpoint. Nothing reads `resources.bus` (*Context*). It remains a diagnostics seam and is not a lane. `vibey surface serve bus` exits 2 with this paragraph's first sentence.
- **The ratified 8.f should name the exemption,** so that it is law rather than this record's reading. See *Where the operator's rule conflicts*.

### 12. Where the code lives, and family first

| layer | modules (new unless noted) | lanes |
|---|---|---|
| `domain/` (pure) | `surface_catalogue.py`: `SurfaceName`, `ReplyMode`, `IdempotencyClass`, `ParamSpec`, `VerifySpec`, `OperationSpec`, `SurfaceCatalogue`, `SurfaceQueueNames`. `surface_protocol.py`: `SurfaceRequest`, `SurfaceReply`, `SurfaceDeadLetter`, `SurfaceArgsCodec`, `SurfaceProtocolCodec`, `SurfaceDeadLetterFactory`. `config.py` (edited): `SurfacesConfig`, `SurfaceCacheLaneConfig`. `errors.py` (edited): `MalformedSurfaceMessage`, `SurfaceLaneUnavailable`, `SurfaceOperationParked`, `SurfacePayloadTooLarge`, `SurfaceTransportNotConfigured` | S01–S03, S16, S26 |
| `application/interfaces/` (edited) | the `idempotency_key` keyword on six operations | S04–S06 |
| `infrastructure/<surface>/` (edited) | native keys in the Plane, Matrix and Wazuh adapters; `Message-ID` in SMTP; `cache/pipelined_redis.py` (new) | S04–S06, S13 |
| `infrastructure/db/` | `surface_operation_repository.py`, `surface_dead_letter_repository.py`; `migrations/0015_surface_lanes.sql` and two ORM models | S10–S12 |
| `infrastructure/surface_lanes/` | `direct_factory.py`, `topology.py`, `client.py`, `failure_policy.py`, `handler.py`, `cache_handler.py`, `queued_records.py`, `queued_reads.py`, `queued_sends.py`, `host.py`, `reconcile.py`, `selection.py`, each with its interface in `interfaces/`, which joins `.importlinter`'s `infrastructure-interfaces-declare-only` contract | S14–S27 |
| `cli/` | `surface.py`: `vibey surface serve|ping|dead-letters|requeue` | S27, S28 |
| `bootstrap.py` (edited) | the transport choice in `build_app`; `build_surface_lanes` | S14, S26, S27 |
| `vibey_bootstrap` (edited) | `amqp`: `acquire_exclusive` → `AmqpLease`, and `publish(…, confirm=False)`. `retry`: `AsyncRetry`. `memo` (new): `BoundedTtlMemo` | S07–S09 |
| `scripts/` | `bench_surface_lanes.py` | S32 |
| chart | `templates/surface-lanes.yaml`, a `vibey.surfaceEnv` helper, `surfaceLanes.*` values, lane components on each `VibeySurface` | S29, S30 |

**Why here.** ADR-0044 §14 put its loop services inside vibey rather than in the runner tenants, and ADR-0045 §13 did the same for the harness. The lanes need vibey's configuration, its composition root and its adapters, so they live in vibey too. They are not a tenant.

**Family first (10.e).** Every capability comes from the family, and each gap is closed by teaching the family, with the reason written at the definition:

- the AMQP transport, the settle vocabulary and the in-memory double: `vibey_bootstrap.amqp` (R04);
- the lease and the unconfirmed publish: taught to `vibey_bootstrap.amqp` (S07), because the family had no one-owner primitive and every publish waited for a confirm;
- the retry: `vibey_bootstrap.retry`, taught an async form (S08). `tenacity>=8.0` becomes a declared root dependency. It is **already in `uv.lock`** through `google-genai`, so no new package enters the environment and `pip-audit` sees nothing new;
- the memo: `vibey_bootstrap.memo` (S09), stdlib only;
- the consumer watchdog: `vibey_bootstrap.heartbeat`, fed by the AMQP client;
- the AMQP URL precedence: R17's `QueueBackendSettings`;
- the surface adapters themselves: `DirectSurfaceFactory` (S14), shared by `direct` and the lanes.

**No new third-party dependency.** RESP over asyncio streams is stdlib, and `aio-pika` is already added by R03.

### 13. Configuration (12.c)

`[surfaces]` and `[surfaces.cache]` in `vibey.toml` (lane S01). Environment beats file, and file beats default.

| key | default | env | constraint |
|---|---|---|---|
| `transport` | `direct` (S33 makes it `queue`) | `VIBEY_SURFACES_TRANSPORT` | `direct` or `queue` |
| `read_timeout_seconds` | 5 | `VIBEY_SURFACES_READ_TIMEOUT_SECONDS` | 1–300 |
| `write_timeout_seconds` | 30 | `VIBEY_SURFACES_WRITE_TIMEOUT_SECONDS` | 1–3600 |
| `operation_timeout_seconds` | 60 | `VIBEY_SURFACES_OPERATION_TIMEOUT_SECONDS` | 1–3600 |
| `send_start_by_seconds` | 86 400 | — | 60–2 592 000 |
| `sends_await_outcome` | `false` | — | bool |
| `delivery_limit` | 5 | `VIBEY_SURFACES_DELIVERY_LIMIT` | 1–100 |
| `consumer_timeout_seconds` | 900 | — | ≥ 60, and at least `operation_timeout × (retries + 1) + Σ backoff + 60` |
| `retry_backoff_seconds` | `[1, 5, 30]` | — | 0–10 entries, each 0–3600; the entry count is the retry count |
| `read_prefetch` | 64 | `VIBEY_SURFACES_READ_PREFETCH` | 1–1024 |
| `read_max_length` | 10 000 | — | ≥ 1 |
| `write_max_length` | 100 000 | — | ≥ 1 |
| `inline_max_bytes` | 8 388 608 | `VIBEY_SURFACES_INLINE_MAX_BYTES` | 1 024–15 728 640 |
| `reconcile_interval_seconds` | 30 | — | ≥ 1 |
| `standby_poll_seconds` | 5 | — | ≥ 1 |
| `drain_grace_seconds` | 30 | — | ≥ 0 |
| `cache.memo` | `true` | — | bool |
| `cache.memo_max_entries` | 10 000 | `VIBEY_SURFACES_CACHE_MEMO_MAX_ENTRIES` | 0–1 000 000; 0 disables |
| `cache.memo_max_value_bytes` | 65 536 | — | ≥ 0 |

Two numbers are deliberately **not** keys:

- the lane count per surface, which 8.f fixes at one;
- the write prefetch, which is 1 because FIFO replay safety depends on it (§8).

### 14. The chart

- **One Deployment per lane** (`templates/surface-lanes.yaml`, lane S30), named `<fullName>-surface-<name>`:
  - rendered when `surfaceLanes.transport` is `queue` and `surfaceLanes.lanes.<name>.enabled`, which is true for all eleven;
  - `replicas: 1`, `strategy: Recreate`, `args: ["surface", "serve", "<name>"]`;
  - the `wait-for-postgres` and `wait-for-rabbitmq` init containers, copied from the worker;
  - **no Service**: a lane listens on no port. Workers reach it only through the broker.
- **The surface's credentials move to its lane.** A helper, `vibey.surfaceEnv` (lane S29), renders the surface environment block that `worker.yaml:118-273` renders today, either for all surfaces or for one. S29 changes no golden byte. In `queue` mode:
  - each lane receives only its own surface's variables;
  - the worker receives only the bus's;
  - the worker keeps `VIBEY_BUS_AMQP_URL` (R29), which is all it needs to reach every lane.
- **Health.** Each surface's `VibeySurface` resource (ADR-0043 §4) lists the lane's Deployment as a component in `queue` mode, so `Ready` means the surface is usable through vibey, not only that its server is up.
- **cluster-smoke** gains two contracts (lane S31): every lane Deployment becomes Available, and `vibey surface ping --all` answers from inside the worker pod.

### 15. Order: land behind `direct`, then flip

Every lane lands with `transport = direct`, so the suite and every deployment behave as today. The chart renders no lanes until `surfaceLanes.transport=queue` is set, and cluster-smoke sets it explicitly (S31).

The last lane, S33, flips the default, but only once all of these hold:

- the lanes are merged and cluster-smoke is green in `queue` mode;
- the §10 measurement is recorded;
- the operator has accepted the cache cost in writing;
- 8.f is ratified.

`tests/conftest.py` then pins `VIBEY_SURFACES_TRANSPORT=direct` for the historical suite, as R34 does for the queue backend. Every step can be reversed with one key (CDD, 9.c).

### 16. Relation to ADR-0044, ADR-0045 and ADR-0046

**The lanes are independent of the two-loop design (ADR-0046).** They:

- consume no `<prefix>.runs.*` or `<prefix>.jobs.*` object;
- change no engine seam;
- touch no loop-service module.

ADR-0046 can merge, split or rename loop services without touching a lane, and a lane can change without touching a loop. The one reservation: the `<prefix>.surface.*` names belong to this record, and ADR-0046 should take its own segment (for example `<prefix>.loops.*`).

The four records share these conventions:

| convention | ADR-0044 (jobs, runs) | ADR-0045 (tests) | this record (surfaces) |
|---|---|---|---|
| names | `[bus] prefix` and `vhost` | same | same |
| one consumer | prefetch per engine service | `x-single-active-consumer` | SAC plus the exclusive lease (S07). The lease is offered to ADR-0046 if it needs one owner across several queues |
| work queue | quorum, delivery limit, DLX `at-least-once`, `reject-publish`, consumer timeout | same | same, plus `x-max-length` |
| message ids | `message_id = correlation_id = run_id` | `= request_id` | `= request_id`; `op_id` in the body |
| deadline | `start_by` in the body, no `expiration` | same | same |
| settle order | persist, publish, acknowledge | same | same |
| dead letters | parks as `delivery_exhausted` gates | records in the harness store | records in `surface_dead_letter`, and guarded operations parked |
| codecs | strict, versioned, unknown keys rejected | same | same |
| cluster shape | one Deployment per service | `replicas: 1`, `Recreate` | same |

**A follow-up, not part of this record.** R22's loop-service host, T23's harness service and this record's lane host have the same skeleton: decode, dedupe the active request, execute, persist, reply, settle. Once all three exist, that skeleton belongs in the family as one `AmqpServiceHost` (10.e).

## How each non-negotiable still holds

1. **Never block a worker on a human.**
   - A parked operation is answered `parked` at once, and no caller waits for its grant.
   - Every wait is on a machine, and every wait is bounded: the read window, the write window, the operation bound, and a send's `start_by`.
   - A lane that is down makes callers fail fast (§6), never wait for a person.
2. **Credits ≠ rate limit.** Untouched.
   - The lanes carry no capacity model, read no engine event, and have no field for credits.
   - The strict codecs reject every unknown key, so a `resets_at` cannot be smuggled in.
   - A lane's retry backoff is for a surface's transport errors, never for an engine's credits.
3. **A capacity rejection outranks a completion claim.** Untouched. A reply reports an operation on a surface, never an engine's completion.
4. **`domain/` stays pure.** The catalogue, the protocol and the configuration are dataclasses, enums and codecs. `now` is always an argument. `tests/domain/test_domain_purity.py` walks the new files.
5. **Dogfood the family.** See §12. Three gaps are taught to the family (the lease and unconfirmed publish, the async retry, the memo), each with its reason at the definition. No new third-party package enters the lock.
6. **Everything-as-code, and never less of it (12.c).**
   - Every tunable is a key (§13), and both transports stay selectable.
   - The topology is declared by code at start, and the chart declares every lane.
   - Two numbers are not keys, because 8.f fixes one and replay safety fixes the other (§13).
   - Nothing that was configurable becomes less so.
7. **A governing rule is a ratified sub-doctrine.** This record is mechanism, and it states no rule of its own. 8.f must be ratified, with the amendments below, before S33 makes `queue` the default. Until then every lane lands behind `direct`.
8. **CDD.** Each lane lands behind the old default. Its tests use the in-memory broker, and its integration tests use a real one. The flip is last and is reversible with one key (§15).
9. **Status is evidence-bounded (10.f).**
   - Every claim here names its file and the cutoff (`391673c2`).
   - The Redis timings are measured and say where. The AMQP timings are estimates and say so.
   - A reply of `replayed=true` says it was answered from a record.
   - A timed-out operation reports an unknown outcome, never a failure it cannot prove.
10. **Code lives in classes, with an interface beside each (9.b).** Every new class has its mirrored interface. The unavoidable module-level functions are the typer command bodies in `cli/surface.py`, which hold no logic (as `cli/ledger_search.py` does), and the benchmark script's entry guard. Each carries its reason.
11. **The handoff no-loss gate.** Untouched.
12. **Every job is idempotent under replay.**
    - A redelivered request is answered as §8 describes, by class.
    - A guarded send is never repeated by a redelivery. An unknown outcome parks.
    - A job handler that passes an `idempotency_key` derived from its job is answered once across a worker's death.
    - A handler that passes no key is no worse off than today.
13. **The ledger is append-only.** The ledger is untouched. `surface_operation` and `surface_dead_letter` are operational state, not the ledger. A dead-letter row is written once, and its `answered_at` is set once.
14. **Conventional Commits; never implement on `main`.** Every lane is a Conventional Commit on a storm branch.

## Where the operator's rule conflicts or falls short (stated plainly)

1. **The bus cannot be driven by itself.** It is exempt by construction (§11). The ratified text should say so: "…driven by RabbitMQ, except the bus itself, which is the lanes' medium."
2. **`direct` does not hold 8.f.** It is kept for unit tests and for deployments with no bus (12.c). ADR-0045 asks 8.e for the same allowance. The ratified text should name it: "…or, where a deployment has no bus, in-process, and saying so at start."
3. **A surface's own servers use Redis and RabbitMQ directly.**
   - Plane's Celery broker is the same RabbitMQ (`values.yaml:248`), and Plane's cache is Redis database 1 (`plane.yaml:21`).
   - That is the surfaces' own internals, not vibey's operations on them. It cannot be laned without forking Plane.
   - This record reads 8.f as binding every operation **vibey** makes on a surface. If the operator meant every client of Redis and RabbitMQ, that cannot be met.
4. **Exactly-once is not available for SMTP and Kannel.**
   - The design guarantees what the operator asked: a send is never delivered twice because of a redelivery. The mechanism is an intent record, with a park when the outcome is unknown (§8).
   - The cost is at-most-once plus a human's grant when a lane dies in the middle of a send.
   - A caller that replays with no idempotency key can still send twice, as it can today.
5. **8.b names more surfaces than 8.f.** 8.b also covers engines, cloud (OpenStack) and forge (Forgejo). Engines are 8.c's. Cloud and forge are not in the operator's list, and this record does not lane them. The ratified text should say whether they are covered.
6. **The cache pays a broker round trip on every read.** By estimate that is 2 to 6 times today's p50 and 4 to 10 times its p99, and one process is the ceiling for cache reads per deployment (§10). This is a performance consequence of the rule, flagged for the operator's decision after the measurement. It is not resolved here by exempting reads.
7. **One lane is one point of unavailability per surface.**
   - While a lane restarts (`Recreate`), reads to that surface fail and writes wait.
   - Throughput per surface is one process's.
   - 8.c accepts this for loops; 8.f extends it to every surface.
8. **Secrets pass through the broker** (see *Security impact*).
9. **Payloads are bounded in `queue` mode.** A file or blob larger than `inline_max_bytes` cannot go through a lane, and `direct` had no limit. Staging large payloads on a shared volume and passing a reference is a follow-up. Until it lands, this is a regression for large objects, stated rather than hidden.

## Security impact

- **Credentials leave the worker.** In `queue` mode, every surface credential moves from the worker (`worker.yaml:118-273`) to its own lane.
  - A compromised worker holds broker rights, not a Plane token, an OpenBao token or an SMTP password.
  - A compromised worker can invoke only the catalogue's operations. It can make no arbitrary Plane API call.
  - Each lane holds exactly one surface's credentials.
- **The broker becomes a surface capability.**
  - Anyone who can publish to `<prefix>.surface` can run any catalogue operation, including `get_secret`.
  - The request exchange is a topic exchange (§4) so that RabbitMQ topic permissions can confine a caller's user to named surfaces. Wiring separate broker users per caller is a follow-up.
  - Broker credentials are secrets on a par with the surface tokens they replace.
- **Secret values cross the broker.**
  - A `get_secret` reply travels transient on an exclusive reply queue that only its caller's connection can consume.
  - A `set_secret` or `create_config` request is persistent on a quorum queue, so the value sits in the broker's log until the lane consumes it and the log is truncated.
  - The broker's data volume is therefore inside the secrets' trust boundary. It should be encrypted at rest, and connections should use `amqps://` outside minikube.
  - Values are never written to `surface_operation` (reads and overwrites keep no row) and never to a dead letter, which holds digests only.
  - A dead letter drained from the broker is acknowledged, which removes the value from the broker too.
- **Email bodies and SMS text are retained** in `surface_dead_letter.request`, so that a human can decide and requeue. That is personal data kept in PostgreSQL until answered and pruned. Pruning answered rows is a follow-up.
- **The lane validates every request against the catalogue** before calling anything. The operation names a method from a fixed table, never an attribute taken from a message.

## Migration

- Until S33, nothing changes. `transport = direct` is the default, and the chart renders no lanes.
- **Enabling queue mode** before S33:
  - set `VIBEY_SURFACES_TRANSPORT=queue` and `VIBEY_BUS_AMQP_URL`;
  - run `vibey surface serve --all` on a laptop, or set `surfaceLanes.transport=queue` in the chart;
  - a laptop can install its broker with R33's `vibey install --rabbitmq`.
- **From S33 on:**
  - a deployment that sets nothing runs its surfaces through lanes;
  - a process with surfaces configured and no lanes running fails its first surface call with `SurfaceLaneUnavailable`, naming `vibey surface serve <name>`;
  - `VIBEY_SURFACES_TRANSPORT=direct` restores today's behaviour, with a warning that 8.f is not held.
- **No existing caller changes,** because there are none (*Context*).
- **Schema.** `0015_surface_lanes.sql` adds two tables; nothing is migrated. The number is the next free one at landing time; ADR-0046 may claim 0015 first.
- **Switching transports needs no data migration.** A cache written in `direct` mode is read by the lane from the same Redis database. The lane's memo starts empty.

## Consequences

**Good.**

- Every vibey operation on a sovereign surface is ordered, bounded, visible in a queue, and recorded when it fails. None is silently dropped.
- A send is never duplicated by a redelivery. Plane, Matrix and Wazuh are deduplicated natively; SMTP, Kannel and BookStack are guarded.
- Credentials move from every worker to one lane per surface.
- Notifications no longer fail the work that produced them, and they survive a backend outage in the queue.
- One shared in-memory fake per deployment replaces one per process, when a surface is unconfigured.
- The family gains an exclusive lease, an unconfirmed publish, an async retry and a bounded memo, which any adopter can use.

**Bad.**

- **The cache costs more per read.**
  - A cache read is a broker round trip: by estimate 0.4–1.1 ms at p50 and 2–5 ms at p99, against 0.18 ms and 0.5 ms today (§10). That is 2 to 6 times the p50 and 4 to 10 times the p99.
  - One lane process caps cache reads per deployment, at an estimated 5 000–15 000 per second.
  - The memo, the lane's own connection and the batching remove the Redis half of the cost, but not the broker hops.
  - Fine-grained memoization is ruled out of the cache surface.
  - The measurement and the operator's acceptance are owed before the flip.
- **A lane restart is a surface outage** for reads, and a queue for writes.
- **More moving parts:** eleven more Deployments, two tables, a lease, a reconciler and a benchmark.
- **A laptop needs lanes running** (`vibey surface serve --all`) once `queue` is the default and surfaces are called.
- **A send no longer raises in its caller.** Its failure is a dead letter, unless `sends_await_outcome` is set.
- **An unknown send outcome asks a human** rather than retrying.
- **A timeout is still ambiguous.** An adapter call that outlives `operation_timeout_seconds` keeps running in its thread, because the adapters pass no timeout to `urlopen` (for example `plane.py:61`). The effect may land after the lane replied `error`. The reply says "timed out; it may still apply", and a guarded operation parks. Giving the adapters socket timeouts is a follow-up defect fix.
- **Adapters flatten HTTP 4xx and 5xx into `RuntimeError`** (for example `plane.py:63-64`), so a 5xx from those adapters is not retried. Teaching them a transient error type is a follow-up.
- **Large files and blobs** above `inline_max_bytes` cannot use the lanes yet.
- **A broker outage is now an outage of every surface.** It already stops every job and loop under ADR-0044.

## Alternatives rejected

- **Exempt cache reads, or give callers their own memo.** That is a second path to the surface, and the rule explicitly includes the cache. §10 flags the cost instead, and leaves any amendment to the operator.
- **Reads on the quorum queue with confirms.** A Raft commit per read (§10), with no durability a read needs.
- **One queue per lane for everything.** Either reads pay the quorum commit, or writes lose their durability and delivery limit.
- **`x-single-active-consumer` alone.** It is per queue, so two processes could each own one of a lane's two queues and break the memo's single-writer coherence (§1).
- **An exclusive lease that reconnects silently.** A reconnect after another process took the lease would be two instances, however briefly. The lane exits instead, and the supervisor restarts it.
- **Retry by requeue** (`abandon()`). It hot-loops against a backend that is down, and it reorders writes. A bounded in-process retry keeps FIFO order.
- **Per-surface delay queues**, as in ADR-0044's wait tiers. Surface retries are seconds, not hours, and in-process waits keep FIFO order with less topology.
- **Keep the records in the harness's file store, or in the broker only.** Dead letters must be readable while a lane is down, and ADR-0044 puts truth in PostgreSQL. `human_gate` is impossible (`project_id NOT NULL`).
- **A per-surface transport override.** It would be the quiet exemption the operator forbade, especially for the cache. The only escape is the global, loud `direct` (§2).
- **Put the lanes in the worker process.** Every worker would hold every credential, and the lease would move a lane between workers as they scale. Hosting lanes inside `vibey worker` on a laptop, where the lease makes it safe, is a possible convenience later. It is not in this record.
- **A lane over the bus.** Circular (§11).
- **HTTP services per surface instead of a queue.** 8.f says "driven by RabbitMQ". HTTP has no durable waiting, no dead letters and no ordering, and each lane would need a Service and its own authentication.
- **Staging every payload through blob storage.** It would make the files lane depend on the blob lane, and it adds a hop to small payloads. Inline up to a bound, with a later shared-volume reference for large ones, is simpler.

## Verification owed at implementation

Each of these facts is recalled from upstream documentation at design time. Each is asserted by a test in the lane that relies on it, so a disagreement fails a lane rather than a deployment. The images are the pinned `rabbitmq:4-management-alpine@sha256:b839b492…` and `redis:8-alpine@sha256:ba6e394f…`.

- A second connection that declares an exclusive queue another connection owns is refused with `RESOURCE_LOCKED` (405), and the queue is deleted when its owner's connection closes (S07, integration).
- aio-pika reports a lost robust connection through a close callback before it reconnects, so the lease is marked lost in time (S07).
- Quorum queues accept `x-single-active-consumer`, `x-consumer-timeout` and `x-max-length` with `x-overflow=reject-publish`; classic queues accept `x-single-active-consumer` (S15, integration).
- A publish to a queue that is full and set to `reject-publish` is nacked when confirms are on (S16, integration).
- Transient messages on a classic queue do not survive a broker restart. The broker may still page them to disk under memory pressure, which is why §*Security impact* treats the volume as inside the trust boundary (S15, integration: restart and read).
- RabbitMQ 4's default maximum message size is at least 16 MiB, so `inline_max_bytes` at 8 MiB (about 10.7 MiB after base64) fits (S16, integration).
- A message dead-lettered by the delivery limit carries an `x-death` reason of `delivery_limit` (S25, integration).
- Plane's work-item create honours `external_source` and `external_id`, and answers a duplicate with 409 and the existing id (S04; a live check against the chart's Plane image is owed to cluster-smoke, because no Plane runs in unit CI).
- Matrix deduplicates `PUT …/send/m.room.message/{txnId}` per access token (S06; the same live-check caveat).
- The Wazuh indexer accepts `PUT /<index>/_doc/<id>` and overwrites the document (S06; the same caveat).
- Redis `PTTL` returns −2 for a missing key and −1 for a key with no expiry (S13, integration).
- The §10 AMQP estimates: p50, p95 and p99 for a memo hit and a miss, at concurrency 1 and 16, on the operator's laptop and on a Linux node (S32). This one is not a pass/fail test. It is evidence for the operator's decision.
