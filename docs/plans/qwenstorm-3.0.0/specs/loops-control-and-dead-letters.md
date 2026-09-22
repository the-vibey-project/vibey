## Title
feat(loop-service): the router's process answers dead letters and routes control commands to the seat that holds each run

ADR-0046 lane L31 (slug `loops-control-and-dead-letters`).

## Why
Draft ADR-0046 §3's idempotency table
(`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md:191`), the "dead letters"
row: "`x-delivery-limit` at each layer | Dead queues are answered `DEAD_LETTERED`; the caller
fails the attempt, and ADR-0024 parks." A message the broker dead-letters (its own
`x-delivery-limit` exhausted, ADR-0046 §3's queue table, `:147-151`) never reaches a seat host or
a router again, so whoever is waiting on `reply_to` gets nothing at all unless something answers
on the dead-letter path -- this lane is that something. §3's queue table also puts
`vibey.runs.control` (a topic exchange, "each loop binds `<loop>` and `all`") in "both" layers, for
"stop, wind-down, prompts; `SUPERSEDE` broadcast." §6 (`:253`): "The router also honours a
`SUPERSEDE` control broadcast by stopping any lower attempt it holds." §11's design premise (one
router process per loop) plus decision D5 (recorded by `loops-router-routing`'s Why: "answering
dead letters and probes is lanes `loops-control-and-dead-letters` and `loops-probe-consumer`
(decision D5: all three run in the router's process)") puts both jobs -- dead-letter answers and
control-command dispatch -- in one module, `control.py`, which ADR-0046 §10's infrastructure table
(`:304`) names directly. 8.g (`doctrines.md:316-324`): every rejection is measured.

`RunControl` and its `SUPERSEDE`/`STOP`/`WIND_DOWN`/`PROMPT_NOW`/`PROMPT_AT_BREAK` commands
(`domain/run_protocol.py`, lane `loops-run-protocol-messages`) and `SeatHost.control`/
`stop_lower_attempts` (lane `loops-seat-host-drain`) already exist by this lane; this lane is the
first thing that actually consumes `vibey.runs.control` and calls them.

## Required behaviour
All in `src/vibey/infrastructure/loop_service/control.py`.
1. **`class DeadLetterReplier`**, built as
   `DeadLetterReplier(*, loop_id: LoopId, amqp: AmqpClientInterface, names: RunQueueNamesInterface,
   codec: RunProtocolCodec, seats: Sequence[str], clock: Clock, measurements:
   LoopMeasurementLogInterface, logger: Logger | None = None)`:
   - `async def start(self) -> None` consumes, **not** exclusively (a dead-letter queue holds one
     message per poison delivery and several instances answering it would each try to reply --
     but the *reply* itself is idempotent, since `DEAD_LETTERED` is the terminal, cacheable answer
     a redelivery of the same original message would also get, so a non-exclusive consumer here
     costs nothing and needs no 8.c exclusivity): for the intake dead queue
     (`names.intake_dead_queue(loop_id)`) and every seat's dead queue
     (`names.seat_dead_queue(loop_id, seat)` for `seat in seats`), `tag =
     await self._amqp.consume(queue, prefetch=1, handler=self._answer)`, keeping every tag.
   - `async def stop(self) -> None` cancels every tag it holds; a second call does nothing.
   - `async def _answer(self, delivery: AmqpDeliveryInterface) -> None`:
     ```python
     try:
         message = self._codec.from_bytes(delivery.body)
     except MalformedRunMessage:
         await delivery.complete()  # unreadable poison: nothing to reply to, do not requeue it
         return
     reply_to = delivery.properties.reply_to
     if reply_to is not None:
         answer = self._dead_answer(message)
         if answer is not None:
             await self._amqp.publish(
                 "", reply_to, self._codec.to_bytes(answer),
                 AmqpProperties(correlation_id=delivery.properties.correlation_id,
                                 type=type(answer).__name__),
                 mandatory=False,
             )
     self._measurements.record(
         LoopMeasurement(
             loop_id=self._loop_id, subject=MeasurementSubject.DEAD_LETTER,
             at=self._clock.now(), seat=None, engine_id=None, model=None,
             outcome=type(message).__name__,
         )
     )
     self._log.warning("run_dead_lettered", loop=self._loop_id.value, kind=type(message).__name__)
     await delivery.complete()
     ```
   - `_dead_answer(self, message: RunMessage) -> RunMessage | None`: a `RouteRequest` gives
     `RunRouted(route_id=message.route_id, loop_id=self._loop_id, status=RouteStatus.DEAD_LETTERED,
     engine_id=None, seat=None, model=None, switched=False,
     reason="route request dead-lettered after repeated delivery", routed_at=self._clock.now(),
     route_ms=0.0, seat_depth=None, seat_oldest_wait_seconds=None)`; a `RunRequest` gives
     `RunResult(run_id=message.run_id, status=RunStatus.DEAD_LETTERED, exit_code=None,
     meta_status=None, started_at=None, finished_at=self._clock.now(),
     detail="run request dead-lettered after repeated delivery", stdout=None, stderr=None,
     cached_at=None)`; anything else (a stray `RunAccepted`, `RunProgress`, `RunResult` or
     `RunControl` that somehow dead-lettered) gives `None` -- there is nothing meaningful to
     answer, so only the measurement and the log line record it.
2. **`class ControlConsumer`**, built as
   `ControlConsumer(*, loop_id: LoopId, amqp: AmqpClientInterface, names: RunQueueNamesInterface,
   codec: RunProtocolCodec, hosts: Mapping[str, SeatHostInterface], logger: Logger | None = None)`:
   - `async def start(self) -> None`: binds a fresh, non-exclusive queue (server-named,
     `declare_queue("", exclusive=True, auto_delete=True)`) to `names.control_exchange()` on both
     of `names.control_keys(loop_id)` (the loop's own key and `"all"`), then `tag =
     await self._amqp.consume(queue, prefetch=self._prefetch, handler=self._handle)`. Every router
     process gets its own private control queue this way: a fanout to every router of this loop,
     which is exactly what a topic exchange bound on the same two keys by more than one consumer
     already gives (ADR-0046 §3's queue table: "each loop binds `<loop>` and `all`" -- one binding
     per router instance, not a shared queue, so a control command reaches every process that
     needs to act on it, not just one).
   - `async def stop(self) -> None` cancels the tag; a second call does nothing.
   - `async def _handle(self, delivery: AmqpDeliveryInterface) -> None`:
     ```python
     try:
         message = self._codec.from_bytes(delivery.body)
     except MalformedRunMessage as exc:
         self._log.warning("control_message_malformed", loop=self._loop_id.value, error=str(exc))
         await delivery.complete()
         return
     if not isinstance(message, RunControl):
         await delivery.complete()
         return
     if message.command is RunControlCommand.SUPERSEDE:
         supersedes = message.supersedes
         assert supersedes is not None  # RunControl.__post_init__ guarantees this
         for host in self._hosts.values():
             host.stop_lower_attempts(supersedes.key, supersedes.attempt)
     else:
         assert message.run_id is not None  # guaranteed for every non-SUPERSEDE command
         for host in self._hosts.values():
             if host.control(message.run_id, message.command, message.text):
                 break
     await delivery.complete()
     ```
     A control message names no seat, so every local host is tried; `stop_lower_attempts` is
     itself a no-op for a host holding nothing of that key (lane `loops-seat-host-drain`), and
     `control` returns `False` for a run id it does not hold, so trying every host is always safe
     and each host answers only for what it actually has.
3. **Interfaces** in `src/vibey/infrastructure/loop_service/interfaces/control_interface.py`, both
   `@runtime_checkable`, one-line docstring per member: `DeadLetterReplierInterface` (`async
   start(self) -> None`, `async stop(self) -> None`); `ControlConsumerInterface` (the same two).
4. **Fakes**, appended to `tests/fakes/loops.py`:
   ```python
   class FakeDeadLetterReplier:
       """DeadLetterReplierInterface in memory: records whether it is running."""

       def __init__(self) -> None:
           self.started = False

       async def start(self) -> None:
           self.started = True

       async def stop(self) -> None:
           self.started = False


   class FakeControlConsumer:
       """ControlConsumerInterface in memory: records whether it is running."""

       def __init__(self) -> None:
           self.started = False

       async def start(self) -> None:
           self.started = True

       async def stop(self) -> None:
           self.started = False
   ```
5. **Registry**: both interfaces are appended to `DRIVER_SEAMS`; `REGISTRY` gains
   `FakeRegistration(port=DeadLetterReplierInterface, build=FakeDeadLetterReplier)` and
   `FakeRegistration(port=ControlConsumerInterface, build=FakeControlConsumer)`.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of
`src/vibey/infrastructure/process/reaper.py`.
- **New** `src/vibey/infrastructure/loop_service/control.py` (behaviours 1-2). Imports:
  `structlog`, `from collections.abc import Mapping, Sequence`,
  `from vibey_bootstrap.amqp import AmqpProperties`,
  `from vibey_bootstrap.amqp.interfaces import AmqpClientInterface, AmqpDeliveryInterface`,
  `from vibey.application.interfaces import Clock, Logger`,
  `from vibey.domain.errors import MalformedRunMessage`,
  `from vibey.domain.interfaces.run_protocol_interface import RunQueueNamesInterface`,
  `from vibey.domain.loop import LoopId`, `from vibey.domain.loop_events import LoopMeasurement,
  MeasurementSubject`, `from vibey.domain.run_codec import RunProtocolCodec`,
  `from vibey.domain.run_protocol import RouteRequest, RouteStatus, RunControl,
  RunControlCommand, RunMessage, RunRequest, RunResult, RunRouted, RunStatus`,
  `from vibey.infrastructure.loop_service.interfaces.measurement_log_interface import
  LoopMeasurementLogInterface`, `from vibey.infrastructure.loop_service.interfaces.seat_host_interface
  import SeatHostInterface`. `__all__ = ["ControlConsumer", "DeadLetterReplier"]`. Module
  docstring: ADR-0046 §3's control exchange and dead-letter answers; a redelivered poison message
  is answered once, terminally, never retried.
- **New** `src/vibey/infrastructure/loop_service/interfaces/control_interface.py` (behaviour 3).
- **`tests/fakes/loops.py`**: append the two classes of behaviour 4 with `edit_file`.
- **`tests/fakes/registry.py`**: run the registration script of lane `loops-result-store` (the
  `register_fakes.py` block) with only these lists, then delete the script:
  ```python
  IMPORTS = [
      "from tests.fakes.loops import FakeControlConsumer, FakeDeadLetterReplier",
      "from vibey.infrastructure.loop_service.interfaces.control_interface import ControlConsumerInterface, DeadLetterReplierInterface",
  ]
  SEAMS = ["DeadLetterReplierInterface", "ControlConsumerInterface"]
  ENTRIES = [
      "FakeRegistration(port=DeadLetterReplierInterface, build=FakeDeadLetterReplier)",
      "FakeRegistration(port=ControlConsumerInterface, build=FakeControlConsumer)",
  ]
  ```
- Then `uv run ruff check --fix` and `uv run ruff format` on
  `src/vibey/infrastructure/loop_service tests/fakes/loops.py tests/fakes/registry.py
  tests/infrastructure/loop_service`.
- **New** `tests/infrastructure/loop_service/test_control_and_dead_letters.py`.

## Acceptance criteria
- [ ] A dead-lettered `RouteRequest`/`RunRequest` gets a terminal `DEAD_LETTERED` reply on
      `reply_to`, and the dead-letter delivery is always acknowledged, even with no `reply_to`.
- [ ] A `STOP`/`WIND_DOWN`/`PROMPT_NOW`/`PROMPT_AT_BREAK` control message reaches whichever local
      host actually holds the named run, and no other host is affected.
- [ ] A `SUPERSEDE` broadcast reaches every local host's `stop_lower_attempts`, whether or not that
      host holds anything of that key.
- [ ] Every dead letter is measured once, subject `DEAD_LETTER`.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`;
      `tests/meta/patching_baseline.json` does not change; `tests/fakes/test_port_parity.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_control_and_dead_letters.py`. `NOW = datetime(2026, 9, 22,
12, 0, tzinfo=UTC)`; an `InMemoryAmqpClient`, `RunQueueNames()`, `RunProtocolCodec()`, a `_Clock`
(the four-line class of `test_seat_host_core.py`), `InMemoryLoopMeasurementLog()`. Declare the
loop's topology on the broker the way `test_seat_host_core.py`'s rig does before consuming.
- `test_a_dead_lettered_route_request_is_answered_dead_lettered`: publish a `RouteRequest`'s bytes
  directly into `names.intake_dead_queue(SOVEREIGNLOOP)` with `reply_to="caller.replies"`; after
  `DeadLetterReplier(...).start()`, the one reply is a `RunRouted` with
  `status == RouteStatus.DEAD_LETTERED`, matching `route_id`; the dead queue is empty; one
  `DEAD_LETTER` measurement.
- `test_a_dead_lettered_run_request_is_answered_dead_lettered`: the same for a `RunRequest` on a
  seat's dead queue → a `RunResult` with `status == RunStatus.DEAD_LETTERED`, matching `run_id`.
- `test_a_dead_letter_with_no_reply_to_is_still_acknowledged`: `reply_to=None` → no publish, the
  dead queue still empties, one measurement still recorded.
- `test_unreadable_dead_letter_bytes_are_acknowledged_without_a_reply`: `b"not json"` on the dead
  queue → no reply, no exception, the queue empties.
- `test_stop_cancels_both_dead_letter_consumers`: after `stop()`, a fresh dead-lettered message on
  either queue is never answered (`await amqp.get(reply queue)` stays `None`).
- `test_a_control_command_reaches_the_host_that_holds_the_run`: two `FakeSeatHost`s (`A`, `B`),
  `A.active = [run_id]` so `A.control(...)` returns `True`; publish a `RunControl(run_id, STOP,
  None, None)` to `names.control_exchange()` keyed `"sovereignloop"`; after
  `ControlConsumer(hosts={"gpt-oss-20b": A, "qwen3-coder-30b": B}, ...).start()` and the publish,
  `A.controls == [(run_id, STOP, None)]` and `B.controls == []`.
- `test_a_control_command_tries_every_host_until_one_holds_it`: neither host holds the run id →
  both `control` calls happen, in host-mapping order, and nothing raises.
- `test_a_control_message_keyed_all_is_also_received`: publish keyed `"all"` instead of the loop's
  own key → the same delivery as the loop-keyed case.
- `test_a_supersede_broadcast_reaches_every_host`: publish
  `RunControl(None, SUPERSEDE, None, RunSupersede("job-1", 2))` → both hosts'
  `lower_attempt_stops == [("job-1", 2)]`.
- `test_malformed_or_foreign_control_bytes_are_acknowledged_and_ignored`: `b"not json"` and the
  bytes of a `RunProgress` (not a `RunControl`) each acknowledge without calling any host.
- `test_the_consumers_and_their_fakes_satisfy_their_interfaces`: `isinstance` of a real
  `DeadLetterReplier`/`ControlConsumer` and of `FakeDeadLetterReplier()`/`FakeControlConsumer()`
  against their interfaces; `start()`/`stop()` toggle `started` on the fakes.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/fakes tests/meta/test_patching_ratchet.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
git status --short
```

## Out of scope
- Forwarding run requests and routing (lane `loops-router-forwarding`); the resident schedule and
  probes (lanes `loops-resident-schedule`, `loops-probe-consumer`).
- Assembling this consumer, the router and the resident schedule into one running process (lane
  `loops-service-process`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests
  are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow
  `EDITING-RULES.md`.

**Depends on:** `loops-seat-host-drain`, `loops-router-forwarding`.

## Hard repository rules (always)
- `domain/` stays pure: no I/O, no async, no clock, no network. Enforced by `tests/domain/test_domain_purity.py`, which walks the AST.
- Dependencies point inward only: `domain -> application -> infrastructure -> cli`, enforced by `import-linter` (`uv run lint-imports`).
- `CreditsExhausted` never has a `resets_at` field. A capacity rejection always outranks a completion claim.
- Code lives in classes, and every class gets an interface declared beside it (ADR-0016, sub-doctrine 9.b): `pkg/x.py` implies `pkg/interfaces/x_interface.py` (or an entry in an existing `interfaces/` module in the same package). A module-level function is the method of last resort, and needs a written reason at its definition. Interfaces declare; they never consume, and no Protocol is declared outside a package named `interfaces`.
- Every job is idempotent under replay; the ledger is append-only (no updates, no deletes; a correction is a new event that supersedes the prior one).
- `write_file` REPLACES the whole file. Never use it on a file that already exists unless the complete content with the change applied is written back. Every line not meant to change must still be there. For any existing file longer than 100 lines, do not use `write_file` at all.
- Change an existing file with the `edit_file` tool: `path`, an `old_string` copied exactly from `read_file` output (enough lines to be unique), and the `new_string`. It replaces one occurrence and reports when the text is missing or not unique. Only if `edit_file` cannot express a change, use a checked replacement through the `shell` tool, and the `shell` tool takes an **argv list**, never a shell string: a shell here-document that redirects a block of text into a command never works this way and must never be written. For any one-off script, write it with `write_file` to `.qwenstorm/<name>.py`, then run it as `["python3", ".qwenstorm/<name>.py"]`. To append to an existing file, use `edit_file` with `old_string` equal to the file's exact last few lines. Copy `old_string` exactly, including indentation; if a checked assert fails, read the file again and fix the string; never fall back to rewriting the whole file.
- Add tests by appending to an existing test file (read it, append, write the whole file back with everything before the addition unchanged) or by creating a new test file. Never rewrite an existing test file's prior content.
- Every source file begins with the provenance header line `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`. Keep it on every file touched, and put it on every file created (copy it from a neighbour file in the same package, byte for byte).
- Only edit the files named under "Where to change" and the tests named under "Tests to write first". If another file seems like it must change, say so in the verdict instead of editing it.
- After each change, run the focused tests named in this spec. If a test not meant to be affected fails, undo the change with a targeted replacement and try again rather than pushing forward.
- Before the final verdict, run `git diff --stat` and confirm no file lost lines that were not meant to be removed.
- Tests substitute only at declared seams: constructor injection, keyword injection, or a named fixture. Never `monkeypatch.setattr` on an import, a module attribute or a class attribute; never `mock.patch`; never a bare `MagicMock` or `AsyncMock` standing in for a port. A fake is a plain class with real in-memory behaviour for every method it implements; no method body is only `...`, only `pass`, only `return None`, or only `raise NotImplementedError`.
- Persistence goes only through the ORM seams declared in the `orm-*.md` specs in this same directory. No raw `asyncpg` SQL, no `text()`, no `exec_driver_sql()` and no SQL string literal in a loops lane.
- No failure-text string a lane writes may trail off with an ellipsis character: write every failure message out in full, to its last word.
- Do not edit `CHANGELOG.md`, anything under `docs/`, any ADR, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` or a skill tree (the docs wave owns those). Do not push, open a pull request, or change a git remote. Commit locally, with the Title as the Conventional Commit subject.
- Protected tests are never edited, under any circumstance: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`. They must keep passing.
