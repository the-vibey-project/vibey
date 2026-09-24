## Title
feat(loop-service): a loop's probe queue answers from cache unless the target model is resident

ADR-0046 lane L32 (slug `loops-probe-consumer`).

## Why
Draft ADR-0046 §3's queue table
(`STORM/specs/ADR-two-loops.md:149`) declares
`vibey.runs.<loop>.probe`, a classic queue, for "preflight probes". §4, "Probes never thrash"
(`:216-220`): "A probe that would load a model runs only when that model is resident. An example
is `claudeloop doctor --profile`'s tool-call check. Otherwise the probe is answered from its last
real result, marked cached with its time. It is never a fabricated pass. The first probe ever for
a model always runs." This is the rule that keeps a doctor sweep from thrashing sovereignloop's
one resident model: probing every declared model in turn would force a switch (and a 13-16 GB
model load) per probe, which §4's own *Context* explains is exactly what residency exists to
avoid. 8.g (`doctrines.md:316-324`): every probe is measured.

A probe is a `RunRequest` with `purpose=RunPurpose.PROBE` (`domain/run_protocol.py`), sent by
`vibey doctor` or a preflight check (through `LoopClient`/`CommandExecutor`, lanes `loops-client`
and `loops-command-executor`) directly to the loop's probe queue rather than to a seat -- it is
addressed to the *loop*, not to any one seat, because the caller does not know (and must not
guess) which model is currently resident. This lane is the one thing that consumes that queue and
decides, per request, whether to actually run it (delegating to the resident seat's host) or
answer from the cache.

## Required behaviour
All in `src/vibey/infrastructure/loop_service/probe_consumer.py`.
1. **`class ProbeCache`** -- in memory by design, one entry per `(engine_id, model)` pair:
   ```python
   class ProbeCache:
       """The last real probe result for each (engine_id, model) pair this process has ever
       run, and whether that model has ever been probed at all (ADR-0046 §4: "the first probe
       ever for a model always runs"). In memory: a fresh process has probed nothing yet, which
       is the correct starting state -- it never fabricates a pass for a model it has never
       actually reached."""

       def __init__(self) -> None:
           self._results: dict[tuple[str, str | None], RunResult] = {}

       def ever_probed(self, engine_id: str, model: str | None) -> bool:
           return (engine_id, model) in self._results

       def get(self, engine_id: str, model: str | None) -> RunResult | None:
           return self._results.get((engine_id, model))

       def record(self, engine_id: str, model: str | None, result: RunResult) -> None:
           self._results[(engine_id, model)] = result
   ```
2. **`class ProbeConsumer`**, built as
   `ProbeConsumer(*, loop_id: LoopId, amqp: AmqpClientInterface, names: RunQueueNamesInterface,
   codec: RunProtocolCodec, hosts: Mapping[str, SeatHostInterface], resident_model: Callable[[],
   str | None], cache: ProbeCacheInterface, clock: Clock, measurements: LoopMeasurementLogInterface,
   logger: Logger | None = None)`:
   - `async def start(self) -> None`: declares the probe queue (`names.probe_queue(loop_id)`,
     bound on `names.probe_key(loop_id)` to `names.runs_exchange()`, no special arguments -- it
     is a classic queue, not a quorum one, per ADR-0046 §3's table), then consumes it
     non-exclusively: `self._tag = await self._amqp.consume(queue, prefetch=1,
     handler=self._handle)`. Prefetch 1 keeps probes serialized, so a probe that must run never
     competes with another probe for the same resident model at once.
   - `async def stop(self) -> None` cancels the tag; a second call does nothing.
   - `async def _handle(self, delivery: AmqpDeliveryInterface) -> None`:
     ```python
     try:
         message = self._codec.from_bytes(delivery.body)
     except MalformedRunMessage:
         await delivery.complete()
         return
     if not isinstance(message, RunRequest) or message.purpose is not RunPurpose.PROBE:
         await delivery.complete()
         return
     model = message.model_pin if self._loop_id is LoopId.SOVEREIGNLOOP else None
     should_run = (
         self._loop_id is not LoopId.SOVEREIGNLOOP
         or model == self._resident_model()
         or not self._cache.ever_probed(message.engine_id, model)
     )
     started = self._clock.now()
     if should_run:
         result = await self._run(message)
         self._cache.record(message.engine_id, model, result)
         outcome = f"ran:{result.status.value}"
     else:
         cached = self._cache.get(message.engine_id, model)
         assert cached is not None  # ever_probed() is True whenever should_run is False
         result = replace(cached, cached_at=started)
         outcome = f"cached:{cached.status.value}"
     await self._reply(delivery, message.run_id, result)
     await delivery.complete()
     self._measurements.record(
         LoopMeasurement(
             loop_id=self._loop_id, subject=MeasurementSubject.PROBE, at=started,
             seat=None, engine_id=message.engine_id, model=model,
             latency_ms=(self._clock.now() - started).total_seconds() * 1000, outcome=outcome,
         )
     )
     ```
   - `async def _run(self, request: RunRequest) -> RunResult`: finds the seat host that can
     actually run the probe -- for sovereignloop, the host of `self._resident_model()`'s seat
     (via a caller-supplied `seat` on the request is never trusted for a probe: the loop decides
     which host runs it, exactly as a route decides a seat, so `_run` looks up
     `self._hosts.get(self._seat_of(request))`); for paidloop, the host named by
     `request.engine_id` directly (a paid seat is its adapter). No host found → a synthesized
     `RunResult(run_id=request.run_id, status=RunStatus.REJECTED, exit_code=None,
     meta_status=None, started_at=None, finished_at=self._clock.now(),
     detail=f"no seat host for a {request.engine_id} probe on {self._loop_id.value}",
     stdout=None, stderr=None, cached_at=None)`. Otherwise `await host.handle(...)` is **not**
     called directly (that method settles a delivery, which this probe's own delivery is not);
     instead the consumer forwards the probe as an ordinary `RunRequest` publish to that host's
     seat queue and awaits the reply on its own private reply mechanism, exactly the way
     `LoopClient` (lane `loops-client`) submits any other run -- **so `ProbeConsumer` is built
     with an injected `LoopClient`-shaped submitter, not a direct reference to `SeatHost.handle`,
     to avoid re-implementing request/reply correlation a second time (10.e).** Revise the
     constructor: replace `hosts: Mapping[str, SeatHostInterface]` with
     `submit: Callable[[RunRequest], Awaitable[RunResult]]` (the shape `LoopClient.submit_and_wait`
     exposes, lane `loops-client`), and `_run` becomes simply `return await self._submit(request)`.
     `_seat_of` and the `hosts` mapping are removed from the design above; the constructor and
     `_handle` are otherwise unchanged.
3. **Interfaces** in `src/vibey/infrastructure/loop_service/interfaces/probe_consumer_interface.py`:
   `@runtime_checkable class ProbeCacheInterface(Protocol)` (the three `ProbeCache` methods) and
   `@runtime_checkable class ProbeConsumerInterface(Protocol)` (`async start(self) -> None`,
   `async stop(self) -> None`).
4. **Fakes**, appended to `tests/fakes/loops.py`:
   ```python
   class FakeProbeConsumer:
       """ProbeConsumerInterface in memory: records whether it is running."""

       def __init__(self) -> None:
           self.started = False

       async def start(self) -> None:
           self.started = True

       async def stop(self) -> None:
           self.started = False
   ```
   `ProbeCache` needs no separate fake: it has no external dependency, so the production class is
   itself the in-memory double, registered directly.
5. **Registry**: `ProbeCacheInterface` and `ProbeConsumerInterface` are appended to
   `DRIVER_SEAMS`; `REGISTRY` gains
   `FakeRegistration(port=ProbeCacheInterface, build=ProbeCache, note="production in-memory: a fresh process has probed nothing yet (ADR-0046 §4)")`
   and `FakeRegistration(port=ProbeConsumerInterface, build=FakeProbeConsumer)`.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of
`src/vibey/infrastructure/process/reaper.py`.
- **Precondition.** `grep -n "class LoopClient" src/vibey/infrastructure/loop_service/client.py`
  must print a line; if it does not, stop and report `blocked: loops-client has not landed`
  (behaviour 2's final revision needs `LoopClient.submit_and_wait`'s exact shape -- read that
  method before writing `_handle` and `_run`, and if its name or signature differs from
  `Callable[[RunRequest], Awaitable[RunResult]]`, adapt the one call site to match it exactly
  rather than inventing a second submission path).
- **New** `src/vibey/infrastructure/loop_service/probe_consumer.py` (behaviours 1-2, with the
  revision at the end of behaviour 2 applied as written -- do not build the `hosts`-mapping
  version first and then change it; write the final, submit-based shape directly). Imports:
  `structlog`, `from collections.abc import Awaitable, Callable, Mapping`,
  `from dataclasses import replace`, `from vibey_bootstrap.amqp.interfaces import
  AmqpClientInterface, AmqpDeliveryInterface`, `from vibey.application.interfaces import Clock,
  Logger`, `from vibey.domain.errors import MalformedRunMessage`,
  `from vibey.domain.interfaces.run_protocol_interface import RunQueueNamesInterface`,
  `from vibey.domain.loop import LoopId`, `from vibey.domain.loop_events import LoopMeasurement,
  MeasurementSubject`, `from vibey.domain.run_codec import RunProtocolCodec`,
  `from vibey.domain.run_protocol import RunPurpose, RunRequest, RunResult, RunStatus`,
  `from vibey.infrastructure.loop_service.interfaces.measurement_log_interface import
  LoopMeasurementLogInterface`. `__all__ = ["ProbeCache", "ProbeConsumer"]`. Module docstring:
  ADR-0046 §4's "probes never thrash" rule; the first probe of a model always runs, every later
  one is cached unless that model is currently resident.
- **New** `src/vibey/infrastructure/loop_service/interfaces/probe_consumer_interface.py`
  (behaviour 3).
- **`tests/fakes/loops.py`**: append the class of behaviour 4 with `edit_file`.
- **`tests/fakes/registry.py`**: run the registration script of lane `loops-result-store` (the
  `register_fakes.py` block) with only these lists, then delete the script:
  ```python
  IMPORTS = [
      "from tests.fakes.loops import FakeProbeConsumer",
      "from vibey.infrastructure.loop_service.interfaces.probe_consumer_interface import ProbeCacheInterface, ProbeConsumerInterface",
      "from vibey.infrastructure.loop_service.probe_consumer import ProbeCache",
  ]
  SEAMS = ["ProbeCacheInterface", "ProbeConsumerInterface"]
  ENTRIES = [
      'FakeRegistration(port=ProbeCacheInterface, build=ProbeCache, note="production in-memory: a fresh process has probed nothing yet (ADR-0046 §4)")',
      "FakeRegistration(port=ProbeConsumerInterface, build=FakeProbeConsumer)",
  ]
  ```
- Then `uv run ruff check --fix` and `uv run ruff format` on
  `src/vibey/infrastructure/loop_service tests/fakes/loops.py tests/fakes/registry.py
  tests/infrastructure/loop_service`.
- **New** `tests/infrastructure/loop_service/test_probe_consumer.py`.

## Acceptance criteria
- [ ] The first probe of a given `(engine_id, model)` pair always runs, whatever the resident
      model is.
- [ ] A later probe of a model that is **not** resident is answered from cache, timestamped
      `cached_at` to the moment it was asked (not the moment it was originally run).
- [ ] A later probe of the model that **is** currently resident always runs again.
- [ ] A paid probe always runs (paidloop has no residency concept).
- [ ] Every probe is measured once, subject `PROBE`, with `outcome` naming whether it ran or was
      cached and the result's status.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json`
      does not change; `tests/fakes/test_port_parity.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_probe_consumer.py`. `NOW = datetime(2026, 9, 22, 12, 0,
tzinfo=UTC)`; a `_Clock` that advances on each `now()` call by a fixed step (so `cached_at` and a
freshly-run result's `finished_at` are distinguishable); `submit` is a small recording async
callable the test controls: `async def submit(request: RunRequest) -> RunResult: calls.append
(request); return scripted.pop(0)`. Build the consumer with `resident_model=lambda: resident[0]`
(a one-item box the test mutates between calls).
- `test_the_first_probe_of_a_model_always_runs`: `resident[0] = "gpt-oss:20b"`; a probe for
  `model_pin="qwen3-coder:30b"` (not resident) still runs, because it has never been probed;
  `calls == [request]`.
- `test_a_later_probe_of_a_non_resident_model_is_cached`: probe `"qwen3-coder:30b"` once (runs,
  cached), set `resident[0] = "gpt-oss:20b"`, probe it again → `len(calls) == 1` (only the first
  call reached `submit`); the reply's `cached_at` is the second call's clock reading, not the
  first's `finished_at`.
- `test_a_probe_of_the_resident_model_always_runs`: probe `"gpt-oss:20b"` twice while it stays
  resident → `len(calls) == 2`.
- `test_a_paid_probe_always_runs`: `loop_id=LoopId.PAIDLOOP`, two probes for the same
  `engine_id="claudeloop"` → both reach `submit`.
- `test_a_non_probe_or_foreign_message_is_ignored`: a `RunRequest` with
  `purpose=RunPurpose.RUN`, and `b"not json"`, are each acknowledged with no call to `submit`.
- `test_probes_are_measured_with_their_outcome`: one run and one cached probe give measurements
  whose `outcome` starts `"ran:"` and `"cached:"` respectively.
- `test_stop_cancels_the_consumer`: after `stop()`, a fresh probe published to the queue is never
  answered.
- `test_the_cache_starts_empty_and_records_what_it_is_told`: a fresh `ProbeCache()`:
  `ever_probed("claudeloop", None) is False`; after `record("claudeloop", None, result)`,
  `ever_probed(...) is True` and `get(...) == result`.
- `test_the_consumer_and_its_fake_satisfy_their_interfaces`: `isinstance` of `ProbeConsumer(...)`
  and `FakeProbeConsumer()` against `ProbeConsumerInterface`; of `ProbeCache()` against
  `ProbeCacheInterface`.

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
- `LoopClient`/`submit_and_wait` itself (lane `loops-client`); assembling this consumer into the
  router's process (lane `loops-service-process`).
- Which paths inside vibey send a `RunRequest` with `purpose=PROBE` to a loop's probe queue
  (`vibey doctor`, preflight checks): out of scope for this lane, which only answers what arrives.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests
  are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow
  `EDITING-RULES.md`.

**Depends on:** `loops-control-and-dead-letters`, `loops-resident-schedule`.

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
