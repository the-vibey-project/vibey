## Title
feat(bootstrap): vibey_bootstrap.amqp can say whether anyone consumes a queue

## Why
Draft ADR-0045 §3 and §12. harness-T21a taught the real `AmqpClient` to count a queue's consumers
with a passive declare. This lane completes the capability in the family (10.e,
`src/vibey_tools/gh/docs/doctrines.md:417`): the interface declares it, and the in-memory client,
which amendment A4 names **the registered in-memory bus fake** for the harness's AMQP lanes
(`specs/ADR-test-harness-fakes-amendment.md:134-135`), answers it with real behaviour.

The harness's AMQP lanes also rely on two AMQP 0-9-1 behaviours of that fake that rmq-r04's spec
does not name: the **default exchange** (`""`), which routes a message to the queue named by its
routing key (the harness service replies to `reply_to` that way, harness-T23), and a
**server-named queue** (`declare_queue("")` returns a fresh unique name; the requester's reply
queue, harness-T24). This lane verifies both in memory, and adds them if they are missing, so the
fake stays as strict as the broker (amendment A2: a fake kinder than the real adapter is not
comprehensive).

## Required behaviour
1. **`AmqpClientInterface`** (`src/vibey_tools/bootstrap/vibey_bootstrap/amqp/interfaces/client_interface.py`)
   gains `async def consumer_count(self, queue: str) -> int | None`, with a docstring: the number of
   active consumers of a declared queue, or `None` when the queue does not exist.
2. **`InMemoryAmqpClient.consumer_count(queue)`** (`src/vibey_tools/bootstrap/vibey_bootstrap/amqp/memory.py`)
   returns the number of active consumers on a declared queue, or `None` for an undeclared one. A
   cancelled consumer no longer counts.
3. **The default exchange.** If `InMemoryAmqpClient.publish("", "<queue name>", body, properties, mandatory=...)`
   does not deliver to the declared queue of that name, add that routing: the exchange `""` routes
   to the queue whose name equals the routing key, and a mandatory publish to an undeclared name
   raises `AmqpPublishError`, like any unroutable mandatory publish (rmq-r04 behaviour 6).
4. **Server-named queues.** If `await client.declare_queue("", exclusive=True, auto_delete=True)` does
   not return a fresh, unique, non-empty name, make it return one (for example
   `f"amq.gen-{uuid.uuid4().hex}"`, the broker's prefix).

## Where to change
- `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/memory.py` and
  `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/interfaces/client_interface.py` (with `edit_file`).
- `src/vibey_tools/bootstrap/test/amqp/test_memory_client.py` (append).

## Acceptance criteria
- [ ] In memory: an undeclared queue gives `None`, a declared one `0`, one after `consume` `1`, and after `cancel` `0` again.
- [ ] A publish to exchange `""` with a queue's name as the routing key lands in that queue; a mandatory one to an undeclared name raises `AmqpPublishError`.
- [ ] Two `declare_queue("")` calls return two different non-empty names.
- [ ] Both `AmqpClient` (harness-T21a) and `InMemoryAmqpClient` satisfy `isinstance(..., AmqpClientInterface)`.
- [ ] If the tenant's registry and parity test exist (lanes fakes-tenant-bootstrap-*), they pass with the new method.
- [ ] The tenant's suite (`-m "not integration"`) and static gates pass.

## Tests to write first (TDD)
Appended to `src/vibey_tools/bootstrap/test/amqp/test_memory_client.py`:
- `test_consumer_count_follows_consume_and_cancel`
- `test_default_exchange_routes_to_the_named_queue`
- `test_server_named_queues_are_unique`
- `test_both_clients_satisfy_the_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/ -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)
    uv run lint-imports

## Out of scope
- Anything under `src/vibey/` (the harness's AMQP lanes are harness-T22–T25).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T21a-amqp-consumer-count-client.
- **Files touched:** `vibey_bootstrap/amqp/memory.py`, `vibey_bootstrap/amqp/interfaces/client_interface.py`, `test/amqp/test_memory_client.py` (all under `src/vibey_tools/bootstrap/`).
- **Shares a file with:** rmq-r04's module; fakes-tenant-bootstrap-3 (it registers the in-memory client in the tenant's registry).
- **Must keep passing unchanged:** every rmq-r04 test, the whole vibey-bootstrap suite, and the protected root tests.
- **Registry (amendment A4):** `InMemoryAmqpClient` is the registered bus fake; this lane keeps it complete for its interface. The root registry entry is added by harness-T22.
- **Standing constraints (every vibey-bootstrap harness lane):**
  - This lane changes the vibey-bootstrap tenant and runs its own gates (ADR-0022).
  - No lane needs a running RabbitMQ; a real-broker test is `integration` and skips without `VIBEY_TEST_AMQP_URL`.
  - Substitute only at a declared seam. Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - Protected root tests are never edited. Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
