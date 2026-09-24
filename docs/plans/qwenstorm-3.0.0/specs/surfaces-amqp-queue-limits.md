## Title
feat(bootstrap): the in-memory broker honours x-max-length, x-overflow and x-single-active-consumer

## Why
Draft ADR-0047 §4 (`specs/ADR-surface-lanes.md`) declares every surface queue with
`x-overflow=reject-publish` and `x-max-length`, and with `x-single-active-consumer: true` as
defence in depth behind the lane's lease (§1). §6 says what a caller sees when a lane's queue
is full: a confirmed publish is nacked (`SurfaceLaneUnavailable` at once), and an unconfirmed
read is dropped (the caller times out).

`InMemoryAmqpClient` (lane `split-351-1-amqp-contract`, `issue-audit/updates/351.md` behaviour 5)
models delivery limits, dead-lettering and TTL, but not queue length or single-active
consumers. Without them the surface lanes' unit tests could not prove the "queue full" row of
§6, and a fake that is kinder than the broker fails its contract (draft amendment A2,
`specs/ADR-test-harness-fakes-amendment.md`). ADR-0047 lane S07, part of the family teaching
(10.e).

## Required behaviour
Only `vibey_bootstrap/amqp/memory.py` changes. "Ready" below means messages in the queue that
are not currently delivered and unsettled; RabbitMQ counts only those against `x-max-length`.

1. **`x-max-length`** (an `int` ≥ 0 in the queue's `arguments`) with **`x-overflow`**:
   - `"reject-publish"`: a publish that would make the queue hold more than `x-max-length`
     ready messages is **not** enqueued in that queue. Other queues it routes to still
     receive it.
     - With `confirm=True` the publish then raises
       `AmqpPublishError(f"queue {name!r} is full (x-max-length={n}, x-overflow=reject-publish)")`
       after the other queues were served.
     - With `confirm=False` (lane `surfaces-amqp-publish-modes`) the refused copy is appended to
       `dropped` and nothing is raised.
   - `"drop-head"` or no `x-overflow`: the message is enqueued, and then the oldest ready
     message is removed and dead-lettered to the queue's `x-dead-letter-exchange` with its
     routing key kept, or discarded when the queue has none.
   - Any other `x-overflow` value raises `AmqpError(f"unsupported x-overflow {value!r}")` at
     `declare_queue`.
2. **`x-single-active-consumer: True`**: of the consumers registered on the queue, only the
   earliest one that is still active receives pushes; the others receive nothing. When the
   active consumer is cancelled (`cancel(tag)`) or its channel closes
   (`simulate_channel_close(tag)`), the next registered consumer becomes active, and every
   message returned by the closed one is pushed to it, count incremented as today.
3. A queue declared without these arguments behaves exactly as today.

## Where to change
- `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/memory.py` only. Keep per-queue state as the
  plain lists R04 left (351.md behaviour 5, last paragraph).
- New test module `src/vibey_tools/bootstrap/test/amqp/test_memory_queue_limits.py`.

## Acceptance criteria
- [ ] A `reject-publish` queue with `x-max-length=2` accepts two messages; the third confirmed publish raises naming the queue and the limit, and an unconfirmed third lands in `dropped`.
- [ ] Settling a delivered message does not change the ready count; `x-max-length` counts ready messages only.
- [ ] `drop-head` dead-letters the oldest message with its routing key to the DLX.
- [ ] With single-active-consumer, a second consumer receives nothing until the first is cancelled, then receives the queue in order.
- [ ] Every existing memory-client test passes unchanged; the tenant keeps its 100% line floor.

## Tests to write first (TDD)
`test/amqp/test_memory_queue_limits.py` (no service):
- `test_reject_publish_refuses_a_confirmed_publish_when_full`
- `test_reject_publish_drops_an_unconfirmed_publish_when_full`
- `test_reject_publish_still_serves_the_other_queues`
- `test_max_length_counts_ready_messages_only`
- `test_drop_head_dead_letters_the_oldest_with_its_key`
- `test_unsupported_overflow_is_refused_at_declare`
- `test_single_active_consumer_pushes_to_the_first_only`
- `test_single_active_consumer_fails_over_on_cancel_and_on_channel_close`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider --no-cov test/amqp)
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/ -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)

## Out of scope
- The real broker needs no change: RabbitMQ implements these arguments. The integration
  evidence is `surfaces-topology`'s.
- `client.py`, the interfaces, the lease. Anything under `src/vibey/`. CHANGELOG.md, docs/,
  ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not
  push, open PRs or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-amqp-publish-modes` (the `confirm` keyword and `dropped`).
- **Shares a file with:** `memory.py` (T21, L21, `surfaces-amqp-publish-modes`); keep their additions.
- **Must keep passing unchanged:** every existing test under `src/vibey_tools/bootstrap/test/amqp/`; the whole vibey-bootstrap suite; all protected root tests.
- **Standing constraints (every vibey-bootstrap surfaces lane):**
  - Read `STORM/EDITING-RULES.md` first. `memory.py`
    is long: change it with `edit_file` only.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from a sibling.
  - No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no broker.
  - If `src/vibey_tools/bootstrap/test/fakes/registry.py` exists, keep `InMemoryAmqpClient`
    registered; add nothing else.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
