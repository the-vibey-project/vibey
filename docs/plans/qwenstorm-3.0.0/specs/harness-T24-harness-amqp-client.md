## Title
feat(test-harness): the requester puts a run on the machine's queue and waits for its answer

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:274-276`): "a commit hook, a
storm lane, a reviewer and the command line all put their run on the queue and wait for its
result". Draft ADR-0045 §3 and §12 set out what the `rabbitmq` requester does:
- it uses the same request builder and fast path as the `local` one (harness-T14a), so a repeat is
  answered without touching the broker;
- before publishing, it can say whether a service consumes the queue (harness-T21's
  `consumer_count`), so `auto` degrades, announced, instead of waiting on a queue nobody reads
  (harness-T25a/T25b);
- it publishes persistent and mandatory, with **no expiration** (`start_by` travels in the body),
  and waits on its own exclusive, server-named reply queue, correlated by request id.

## Required behaviour
Create `src/vibey/infrastructure/test_harness/amqp_client.py`:
1. **`AmqpHarnessClient`**, built with keyword-only arguments: `client: AmqpClientInterface`,
   `names: TestHarnessNamesInterface`, `codec: TestHarnessCodecInterface`,
   `builder: TestRunRequestBuilderInterface`, `fast_path: ReuseFastPathInterface`,
   `settings: TestHarnessSettingsInterface`. It implements `HarnessClientInterface` (harness-T14).
2. **`async def unavailable_reason(self) -> str | None`**:
   - any exception from `client.consumer_count(names.request_queue())` → `f"broker unreachable: {exc}"`;
   - a count of `None` → `f"no harness service has declared {names.request_queue()}"`;
   - `0` → `f"no harness service consumes {names.request_queue()}"`;
   - otherwise `None`.
3. **`async def request(self, *, cwd, argv, gates, fresh, grant=False, environ) -> TestRunResult`**
   (the signature of `HarnessClientInterface.request`): build the request, return the fast path's
   answer when there is one, else `await self.submit(request)`.
4. **`async def submit(self, request: TestRunRequest) -> TestRunResult`**:
   1. on first use, `self._reply = await client.declare_queue("", durable=False, exclusive=True, auto_delete=True)`
      and consume it with `prefetch=16`; the handler routes each reply by
      `delivery.properties.correlation_id` to its pending future and completes the delivery; an
      unknown correlation id or an undecodable body is completed and dropped with a log line
      (`structlog.get_logger(__name__)`);
   2. register a future for `str(request.request_id)`, then publish `codec.to_bytes(request)` to
      `names.exchange()` on `names.routing_key()` with
      `AmqpProperties(message_id=str(request.request_id), correlation_id=str(request.request_id), reply_to=self._reply, type="test.request", delivery_mode=2)`
      and `mandatory=True`; set no expiration;
   3. wait for the future up to `settings.wait_seconds`; on timeout drop the future and return
      `STILL_RUNNING` (`backend="rabbitmq"`, `outcome=None`) with the detail
      `"the run is queued or running; run the same command again to receive its result"`.
5. **`async def close(self) -> None`** cancels the reply consumer, if any.
6. **The interface** `src/vibey/infrastructure/test_harness/interfaces/amqp_client_interface.py`:
   `@runtime_checkable` `AmqpHarnessClientInterface`, extending `HarnessClientInterface` with
   `unavailable_reason` and `close`.

## Where to change
- New `src/vibey/infrastructure/test_harness/amqp_client.py` and its interface module.
- New `tests/infrastructure/test_harness/test_amqp_client.py`.

## Acceptance criteria
With `InMemoryAmqpClient` (the `memory_amqp` fixture), the real `TestHarnessTopology` declared on it,
the registered `FixedRequestBuilder` and `ScriptedFastPath` (`tests/fakes/harness_requests.py`), and
a plain in-test responder that consumes the request queue and publishes a `TestRunResult` to exchange
`""` on the request's `reply_to` with its `correlation_id` (harness-T21 guarantees the in-memory default
exchange and server-named queues):
- [ ] A request round-trips.
- [ ] Two concurrent requests never receive each other's answers.
- [ ] The fast path answers without publishing anything (`memory_amqp.published` is empty).
- [ ] `unavailable_reason` returns each of its four values (the unreachable case with a plain in-test client whose `consumer_count` raises `OSError`).
- [ ] A missing answer gives `STILL_RUNNING` after `wait_seconds` (settings with `VIBEY_HARNESS_WAIT_SECONDS=1`).
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_amqp_client.py` (`from vibey.infrastructure.test_harness import amqp_client as ac`):
- `test_request_round_trip`
- `test_concurrent_requests_do_not_cross`
- `test_fast_path_publishes_nothing`
- `test_unavailable_reasons` (parametrized)
- `test_still_running_after_the_wait`
- `test_unknown_and_undecodable_replies_are_dropped`
- `test_close_cancels_the_reply_consumer`
- `test_client_satisfies_its_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Choosing between backends (harness-T25a, T25b).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** rmq-r04-bootstrap-amqp, harness-T14-local-client, harness-T21-amqp-consumer-count, harness-T22-harness-topology.
- **Files touched:** the two new source files and the new test file.
- **Shares a file with:** none.
- **Must keep passing unchanged:** harness-T14's and T22's tests, `tests/fakes/*`, and the protected tests.
- **Registry (amendment A4):** nothing new. It implements `HarnessClientInterface`, whose registered fake is harness-T14's `ScriptedHarnessClient`; the composition builds this class and never takes it as a collaborator.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (the constructor keywords). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; in-test doubles are plain classes.
  - No lane needs a running RabbitMQ (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out). No test waits longer than 5 s.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
