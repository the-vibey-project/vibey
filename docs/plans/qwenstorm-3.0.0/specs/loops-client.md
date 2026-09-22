## Title
feat(loop-service): LoopClient, the caller-side RPC over the bus that routes a job and submits a run

ADR-0046 lane L56 (slug `loops-client`).

## Why
Draft ADR-0046 §3 (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md:140-191`)
puts the whole outer-layer conversation over AMQP: "It publishes a route request to `<loop>` and
awaits `RunRouted`, bounded by `route_wait_seconds`" (the *Flow for a BUILD job*, step 2), and
"The handler's `start` publishes the run request to `<loop>`" (step 5), replying on `reply_to`
with `RunAccepted`, then zero or more `RunProgress`, then one `RunResult` (§3's message table).
§10 (`:304`) names `infrastructure/loop_service/client.py` directly. This is the one class on the
caller's side of the bus that does both conversations: `LoopRoutingPort.route()` (lane
`loops-routing-ports` declared the port; `loops-selecting-loop-provider` is its only caller so
far) and submitting a `RunRequest` and reading back its replies (consumed by
`loops-service-adapter-run`'s `EngineAdapter` and by `loops-probe-consumer`'s injected `submit`
callable). Sub-doctrine 10.e (`doctrines.md:417`): one correlation mechanism, not one per caller.

At integration `d3b4a388` there is no AMQP-backed request/reply client anywhere in `src/vibey`.
The pattern is the classic AMQP RPC one: one private, exclusive, server-named reply queue per
`LoopClient` instance (`declare_queue("", exclusive=True, auto_delete=True)`, confirmed as a
family capability by `harness-T21a`'s sibling lane and `split-351-2-amqp-client`'s "server-named
queue" note), one non-exclusive consumer on it, and a table of pending futures keyed by
`correlation_id`, each resolved by the reply whose `correlation_id` matches.

## Required behaviour
All in `src/vibey/infrastructure/loop_service/client.py`.
1. **`class LoopClient`**, built as
   `LoopClient(*, amqp: AmqpClientInterface, names: RunQueueNamesInterface, codec:
   RunProtocolCodec, clock: Clock, route_ids: Callable[[], UUID] = uuid4, logger: Logger | None =
   None)`. It owns no seat and no loop: one client instance serves every loop and every run a
   process needs to talk to, since a reply queue and its correlation table are per **process**,
   not per loop.
2. **`async def start(self) -> None`**: declares its private reply queue
   (`self._reply_queue = await self._amqp.declare_queue("", exclusive=True, auto_delete=True)`)
   and consumes it (`prefetch` generous -- `256`, since replies are small and numerous --
   `handler=self._on_reply`). Idempotent: a second call does nothing while already started.
3. **`async def stop(self) -> None`**: cancels the consumer tag (if any). Every pending future is
   resolved with `None` first (a caller mid-await sees "no answer", not a hang) -- iterate a
   snapshot of `self._pending.values()`, set each to `None` if not already done, then clear the
   table.
4. **`async def route(self, request: RouteRequest, *, wait: timedelta) -> RunRouted | None`**
   (satisfies `LoopRoutingPort`, lane `loops-routing-ports`): publish to
   `names.runs_exchange()` keyed `names.intake_key(request.loop_id)` with
   `AmqpProperties(message_id=str(request.route_id), correlation_id=str(request.route_id),
   reply_to=self._reply_queue, type="RouteRequest")`, then await a reply of type `RunRouted`
   correlated to `str(request.route_id)` for at most `wait`; `None` on timeout (§5's rule: no
   answer within `route_wait_seconds` is queue saturation for the caller to classify, never this
   client's job to interpret).
5. **`async def submit_and_wait(self, request: RunRequest, *, accept_wait: timedelta,
   run_wait: timedelta) -> RunResult`** -- the shape `loops-service-adapter-run` and
   `loops-probe-consumer` both need: publish `request` to `names.runs_exchange()` keyed
   `names.intake_key(request.loop_id)` with `correlation_id=str(request.run_id)`,
   `reply_to=self._reply_queue`, `message_id=str(request.run_id)`; await a `RunAccepted`
   correlated to it within `accept_wait`, else raise `EngineQueueSaturated(clock.now() +
   accept_wait, f"no {request.loop_id.value} seat accepted run {request.run_id} within
   {accept_wait.total_seconds():g}s")` (the exact exception `loops-queue-saturated` defines, so a
   caller building an `EngineAdapter` on top of this client needs no translation step); then keep
   awaiting messages correlated to the same id, forwarding every `RunProgress` to an optional
   `on_progress: Callable[[RunProgress], None] | None = None` keyword, until a `RunResult`
   arrives, which is returned; if `run_wait` elapses first, return a synthesized
   `RunResult(run_id=request.run_id, status=RunStatus.DEADLINE_EXCEEDED, exit_code=None,
   meta_status=None, started_at=None, finished_at=clock.now(), detail=f"no result within
   {run_wait.total_seconds():g}s of acceptance", stdout=None, stderr=None, cached_at=None)`
   rather than raising -- a run that was accepted is a real attempt, and its caller (the seat
   host's own deadline already bounds the true run; this is the client's own defence against a
   reply that is simply lost) must see a terminal status, not an exception, so it can settle the
   job exactly as any other `RunResult` would.
6. **`async def submit(self, request: RunRequest) -> str`** (fire-and-forget; used by
   `loops-control-and-dead-letters`-style callers that want no reply at all): publishes with
   `reply_to=None`, and returns the `route_id`/`run_id` used as the outgoing `message_id`. Not
   used by `submit_and_wait`, which builds its own publish inline (behaviour 5) so that
   `reply_to` is always this client's own queue.
7. **`async def _on_reply(self, delivery: AmqpDeliveryInterface) -> None`**:
   ```python
   await delivery.complete()
   try:
       message = self._codec.from_bytes(delivery.body)
   except MalformedRunMessage:
       return
   correlation_id = delivery.properties.correlation_id
   if correlation_id is None:
       return
   pending = self._pending.get(correlation_id)
   if pending is None:
       return
   pending.deliver(message)
   ```
   Acknowledging first (rather than after dispatch) is deliberate: a reply queue is this client's
   own private mailbox, never shared, so there is nothing to protect by delaying the ack, and a
   crash between ack and dispatch would otherwise strand the reply on a queue nobody will ever
   consume again.
8. **`class _Pending`** (private, not exported), one per correlation id, holding an
   `asyncio.Queue[RunMessage]` for `submit_and_wait`'s multi-message stream and a single
   `asyncio.Future[RunRouted | None]` for `route`'s single-message wait; `deliver(message)` routes
   a `RunRouted`/`RunAccepted`/`RunProgress`/`RunResult` to whichever the caller registered for.
   Exact shape is this lane's own choice, kept private; only `route` and `submit_and_wait`'s
   signatures are the seam other lanes depend on.
9. **`src/vibey/infrastructure/loop_service/interfaces/client_interface.py`** (new):
   `@runtime_checkable class LoopClientInterface(Protocol)` with `async start(self) -> None`,
   `async stop(self) -> None`, `async route(self, request: RouteRequest, *, wait: timedelta) ->
   RunRouted | None`, `async submit_and_wait(self, request: RunRequest, *, accept_wait: timedelta,
   run_wait: timedelta, on_progress: Callable[[RunProgress], None] | None = None) -> RunResult`,
   `async submit(self, request: RunRequest) -> str`, each with a one-line docstring. This
   `Protocol` is a strict superset of `LoopRoutingPort` (lane `loops-routing-ports`):
   `isinstance(LoopClient(...), LoopRoutingPort)` must also hold.
10. **In-memory fake**, appended to `tests/fakes/loops.py`:
    ```python
    class FakeLoopClient:
        """LoopClientInterface in memory: scripted per-loop route replies and per-request run
        results, so a test never needs a broker to exercise a caller built on LoopClient."""

        def __init__(
            self,
            *,
            routes: Mapping[LoopId, RunRouted | None] | None = None,
            results: Mapping[UUID, RunResult] | None = None,
        ) -> None:
            self._routes = dict(routes or {})
            self._results = dict(results or {})
            self.started = False
            self.route_requests: list[RouteRequest] = []
            self.submitted: list[RunRequest] = []

        async def start(self) -> None:
            self.started = True

        async def stop(self) -> None:
            self.started = False

        async def route(self, request: RouteRequest, *, wait: timedelta) -> RunRouted | None:
            self.route_requests.append(request)
            reply = self._routes.get(request.loop_id)
            return None if reply is None else replace(reply, route_id=request.route_id)

        async def submit_and_wait(
            self,
            request: RunRequest,
            *,
            accept_wait: timedelta,
            run_wait: timedelta,
            on_progress: Callable[[RunProgress], None] | None = None,
        ) -> RunResult:
            self.submitted.append(request)
            result = self._results.get(request.run_id)
            if result is None:
                raise EngineQueueSaturated(
                    datetime.now(UTC) + accept_wait, f"no scripted result for run {request.run_id}"
                )
            return result

        async def submit(self, request: RunRequest) -> str:
            self.submitted.append(request)
            return str(request.run_id)
    ```
11. **Registry**: `LoopClientInterface` is appended to `DRIVER_SEAMS`; `REGISTRY` gains
    `FakeRegistration(port=LoopClientInterface, build=lambda: FakeLoopClient(), note="scripted per-loop routes and per-run results")`.
    `FakeLoopClient` also satisfies `LoopRoutingPort`, so `loops-routing-ports`'s own
    `FakeLoopRouting` and this fake may coexist: a test that only needs routing keeps using the
    smaller `FakeLoopRouting`, and one that needs the fuller client uses this one.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of
`src/vibey/infrastructure/process/reaper.py`.
- **New** `src/vibey/infrastructure/loop_service/client.py` (behaviours 1-8). Imports: `asyncio`,
  `from collections.abc import Callable`, `from datetime import UTC, datetime, timedelta`,
  `from uuid import UUID, uuid4`, `structlog`, `from vibey_bootstrap.amqp import AmqpProperties`,
  `from vibey_bootstrap.amqp.interfaces import AmqpClientInterface, AmqpDeliveryInterface`,
  `from vibey.application.interfaces import Clock, Logger`,
  `from vibey.application.worker import EngineQueueSaturated`,
  `from vibey.domain.errors import MalformedRunMessage`,
  `from vibey.domain.interfaces.run_protocol_interface import RunQueueNamesInterface`,
  `from vibey.domain.run_codec import RunProtocolCodec`, `from vibey.domain.run_protocol import
  RouteRequest, RunAccepted, RunMessage, RunProgress, RunRequest, RunResult, RunRouted,
  RunStatus`. `__all__ = ["LoopClient"]`.
- **New** `src/vibey/infrastructure/loop_service/interfaces/client_interface.py` (behaviour 9).
- **`tests/fakes/loops.py`**: add `EngineQueueSaturated`, `datetime`, `UTC`, `replace` to its
  imports if missing (`edit_file`); append the class of behaviour 10.
- **`tests/fakes/registry.py`**: run the registration script of lane `loops-result-store` (the
  `register_fakes.py` block) with only these lists, then delete the script:
  ```python
  IMPORTS = [
      "from tests.fakes.loops import FakeLoopClient",
      "from vibey.infrastructure.loop_service.interfaces.client_interface import LoopClientInterface",
  ]
  SEAMS = ["LoopClientInterface"]
  ENTRIES = [
      'FakeRegistration(port=LoopClientInterface, build=lambda: FakeLoopClient(), note="scripted per-loop routes and per-run results")',
  ]
  ```
- Then `uv run ruff check --fix` and `uv run ruff format` on
  `src/vibey/infrastructure/loop_service tests/fakes/loops.py tests/fakes/registry.py
  tests/infrastructure/loop_service`.
- **New** `tests/infrastructure/loop_service/test_client.py`.

## Acceptance criteria
- [ ] `isinstance(LoopClient(...), LoopRoutingPort)` and `isinstance(LoopClient(...),
      LoopClientInterface)` both hold.
- [ ] `route` returns the reply correlated to its own `route_id`, and `None` on a timeout with no
      reply.
- [ ] `submit_and_wait` raises `EngineQueueSaturated` when no `RunAccepted` arrives within
      `accept_wait`, forwards every `RunProgress` to `on_progress` in order, and returns the
      terminal `RunResult`; a run accepted but never resulted returns a synthesized
      `DEADLINE_EXCEEDED` result rather than raising.
- [ ] A reply for an id nobody is waiting on, or one that fails to decode, is acknowledged and
      dropped without raising.
- [ ] `stop()` releases every caller still waiting with `None`/a synthesized deadline result
      rather than hanging forever.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json`
      does not change; `tests/fakes/test_port_parity.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_client.py`. Use an `InMemoryAmqpClient`, `RunQueueNames()`,
`RunProtocolCodec()`, a `_Clock` (the four-line class of `test_seat_host_core.py`). Declare and
bind the loop's topology on the broker with the test's own helper before publishing to it, so the
client's publishes land where a real router/seat host would consume them; drive the "server side"
of each conversation by hand with `await amqp.get(queue)` / `await amqp.publish(...)` rather than
a real router, so this lane's tests do not depend on `loops-router-routing` having landed.
- `test_route_returns_the_correlated_reply`: `client.start()`; call `route(request,
  wait=timedelta(seconds=1))` as a background task; `get` the intake queue, decode the
  `RouteRequest`, publish a `RunRouted` back to its `reply_to` with the same `correlation_id`; the
  awaited result equals that `RunRouted`.
- `test_route_times_out_with_no_reply`: nothing answers → `route(..., wait=timedelta(milliseconds=50))
  is None`.
- `test_submit_and_wait_raises_saturated_without_an_accept`: nothing answers →
  `pytest.raises(EngineQueueSaturated)` within `accept_wait=timedelta(milliseconds=50)`.
- `test_submit_and_wait_forwards_progress_then_returns_the_result`: answer with `RunAccepted`,
  then two `RunProgress` (seq 1, 2), then a `RunResult`, all correlated to the run id; `on_progress`
  is called with both, in order, before the awaited call returns the result.
- `test_submit_and_wait_synthesizes_a_deadline_result_after_acceptance`: answer only
  `RunAccepted`, then nothing → the returned `RunResult.status is RunStatus.DEADLINE_EXCEEDED`
  within `run_wait=timedelta(milliseconds=50)`.
- `test_an_uncorrelated_or_malformed_reply_is_dropped`: publish a `RunResult` correlated to a
  random UUID nobody awaits, and `b"not json"` with a real `correlation_id`, both to the reply
  queue directly → neither raises, and a subsequent real exchange still works.
- `test_submit_publishes_with_no_reply_to`: `await client.submit(request)` → the published
  message's `properties.reply_to is None`, and the returned string equals `str(request.run_id)`.
- `test_stop_releases_every_pending_caller`: start a `route(...)` call as a background task with a
  long `wait`; call `stop()` → the task resolves to `None` promptly, and `submit_and_wait`
  awaited concurrently resolves to a `DEADLINE_EXCEEDED` result rather than hanging.
- `test_the_client_satisfies_both_interfaces`: `isinstance(LoopClient(...), LoopRoutingPort)` and
  `isinstance(LoopClient(...), LoopClientInterface)`; `isinstance(FakeLoopClient(),
  LoopClientInterface)` and `isinstance(FakeLoopClient(), LoopRoutingPort)`.
- `test_the_fake_scripts_routes_and_results`: `FakeLoopClient(routes={LoopId.SOVEREIGNLOOP: routed},
  results={run_id: result})`: `route` rebinds `route_id`; `submit_and_wait` for `run_id` returns
  `result`; for any other run id it raises `EngineQueueSaturated`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/fakes tests/meta/test_patching_ratchet.py tests/application/test_interfaces_convention.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
git status --short
```

## Out of scope
- `EngineAdapter`/`RoutedAdapterBinder` built on top of `submit_and_wait` (lane
  `loops-service-adapter-run`); the command executor built on top of it (lane
  `loops-command-executor`); the probe consumer's own submitter (lane `loops-probe-consumer`).
- Any router or seat host: this lane's tests drive both sides of the wire by hand.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests
  are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow
  `EDITING-RULES.md`.

**Depends on:** `loops-amqp-exclusive-consume`, `loops-routing-ports`, `loops-result-store`.

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
