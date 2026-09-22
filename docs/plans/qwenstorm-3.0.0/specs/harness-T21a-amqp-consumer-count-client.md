## Title
feat(bootstrap): AmqpClient can say how many consumers a queue has

## Why
Draft ADR-0045 §3: the test harness's `auto` backend uses RabbitMQ only when a harness service
actually consumes the machine's queue. Otherwise it degrades, announced, to the machine lock, so a
push never waits on a queue nobody reads. "Does anyone consume this queue?" is a passive
`queue.declare`, whose `Declare-Ok` carries the consumer count. The family's AMQP client
(`vibey_bootstrap.amqp`, lane rmq-r04-bootstrap-amqp) does not offer it. Sub-doctrine 10.e
(`src/vibey_tools/gh/docs/doctrines.md:417`): a capability gap "is closed by teaching ours, not by
replacing it", so the method goes into the family, not into vibey.

This lane teaches the real client; harness-T21 teaches the in-memory client and the interface
together, so the two never disagree on the interface.

## Required behaviour
In `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/client.py` (lane rmq-r04):
1. **`async def consumer_count(self, queue: str) -> int | None`** on `AmqpClient`. It connects
   lazily, as every other method does (rmq-r04: "Any other method called before `connect()` connects lazily"):
   1. open a **temporary** channel on the connection (`await connection.channel()`), never the
      publish channel: a failed passive declare closes the channel it ran on;
   2. `declared = await channel.declare_queue(queue, passive=True)`;
   3. return `declared.declaration_result.consumer_count`;
   4. `aio_pika.exceptions.ChannelNotFoundEntity` (the queue does not exist) returns `None`;
   5. always close the temporary channel in `finally`, ignoring the error of an already-closed one
      (`contextlib.suppress(Exception)` around `await channel.close()`, with a comment saying why).

## Where to change
- `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/client.py` (with `edit_file`).
- `src/vibey_tools/bootstrap/test/amqp/test_client_unit.py` (append) and
  `src/vibey_tools/bootstrap/test/amqp/test_client_integration.py` (append one `integration` test:
  the opt-in twin of the unit tests, kept in rmq-r04's integration file by that lane's convention).

## Acceptance criteria
- [ ] Unit, through rmq-r04's fake connector (read it in `test_client_unit.py`; if its fake channel's `declare_queue` does not accept `passive=`, add a small fake channel class in the appended tests instead of editing rmq-r04's classes): a passive declare happens on a channel other than the publish channel, that channel is closed afterwards (also when it is already closed), the count is returned, and `ChannelNotFoundEntity` gives `None`.
- [ ] Integration (`@pytest.mark.integration`, skipped unless `VIBEY_TEST_AMQP_URL` is set): against a real broker, a declared queue reports 0, then 1 while a consumer is attached, and a missing queue reports `None`. This is the ADR-0045 *Verification owed* item for the pinned `rabbitmq:4-management-alpine`.
- [ ] The tenant's suite (`-m "not integration"`) and static gates pass.

## Tests to write first (TDD)
- `test/amqp/test_client_unit.py`: `test_consumer_count_uses_a_passive_declare_on_its_own_channel`, `test_consumer_count_of_a_missing_queue_is_none`, `test_consumer_count_closes_an_already_closed_channel_quietly`
- `test/amqp/test_client_integration.py`: `test_consumer_count_against_a_real_broker`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/amqp -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)
    uv run lint-imports

## Out of scope
- `InMemoryAmqpClient` and `AmqpClientInterface` (harness-T21). Anything under `src/vibey/`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** rmq-r04-bootstrap-amqp.
- **Files touched:** `vibey_bootstrap/amqp/client.py`, `test/amqp/test_client_unit.py`, `test/amqp/test_client_integration.py` (all under `src/vibey_tools/bootstrap/`).
- **Shares a file with:** rmq-r04's module (it lands first).
- **Must keep passing unchanged:** every rmq-r04 test; the whole vibey-bootstrap suite, `(cd src/vibey_tools/bootstrap && pytest test/ -m "not integration")`; and the protected root tests.
- **Registry (amendment A4):** nothing new; the in-memory fake gains the method in harness-T21.
- **Standing constraints (every vibey-bootstrap harness lane):**
  - This lane changes the vibey-bootstrap tenant and runs its own gates (ADR-0022).
  - No lane needs a running RabbitMQ: unit tests use rmq-r04's fake connector or `vibey_bootstrap.amqp.memory.InMemoryAmqpClient`; a real-broker test is `integration` and skips without `VIBEY_TEST_AMQP_URL`.
  - Substitute only at a declared seam (rmq-r04's injected `connector`). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - Protected root tests are never edited. Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
