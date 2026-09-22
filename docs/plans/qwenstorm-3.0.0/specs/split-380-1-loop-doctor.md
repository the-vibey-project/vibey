<!-- split of #380: child 1 of 2; audit: issue-audit/updates/380.md -->

## Title
feat(loop-service): a loop doctor that checks the broker, each loop's router and each model's seat

## Why
Once #381 flips the defaults, two failures are silent without this check:
- a laptop with no broker fails with R17's `QueueBackendNotConfigured` (#364);
- a worker whose runs sit on a queue that nobody consumes looks healthy.

`vibey doctor` (`src/vibey/cli/main.py:1185-1391` at integration `4317cff6`) checks only PostgreSQL (the line printed at `:1341`) and the engines.

**The install half of #380 is gone.** The draft installer ADR (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-installer.md:257-260`) drops `RabbitMqLocalService` and `install --rabbitmq` from #380: RabbitMQ is catalogue data on Arch Linux and macOS, lane `installer-broker-cache` declares it and lane `installer-cli` owns `vibey install --rabbitmq` (sub-doctrine 8.h, `src/vibey_tools/gh/docs/doctrines.md:326-333`; 10.e, `:417`).

**The doctor follows draft ADR-0046** (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md`), not ADR-0044's service per engine:
- there are exactly two loops (8.c, `doctrines.md:196-234`);
- each loop has one **router** consuming `vibey.runs.<loop>` and one **seat host** per model consuming `vibey.runs.<loop>.<seat>`, both exclusively (ADR-0046 §3);
- probes go to `vibey.runs.<loop>.probe` and are answered by the loop, from its last real result, marked cached with its time, when the model is not resident (§4, lines 216-220);
- on a machine, sovereignloop consumes **only the resident seat** (§4, line 207), so an idle non-resident sovereign seat is normal, not a fault. paidloop has no residency, so each of its declared seats must have its host.

Sub-doctrine 8.g (`doctrines.md:316-324`) asks that every queue report its depth, so the doctor prints it. This child builds the check as an infrastructure class, tested in memory. Child 2 (`split-380-2-doctor-cli`) wires it into `vibey doctor`.

## Required behaviour
1. **Value types**, in `src/vibey/infrastructure/loop_service/doctor.py`:
   - `@dataclass(frozen=True, slots=True) class LoopCheck` with `loop_id: LoopId`, `seats: tuple[str, ...]` (declared names: model names such as `gpt-oss:20b` for sovereignloop, engine ids for paidloop) and `residency: bool` (True for sovereignloop). (The audit wrote `loop_id: str`; it is typed `LoopId` so it passes to the loop client and the queue names unchanged, and every line prints `loop_id.value`.)
   - `@dataclass(frozen=True, slots=True) class LoopDoctorReport` with `lines: tuple[str, ...]` and `ok: bool`.
   - A module constant `DEFAULT_PROBE_TIMEOUT: Final = timedelta(seconds=10)`.
2. **`class LoopDoctor`**, built with keyword arguments only:
   - `amqp: AmqpClientInterface`, the family client from `vibey_bootstrap.amqp`;
   - `redacted_url: str`, from `AmqpSettings(url).redacted_url()`;
   - `queues: LoopQueueNamesInterface`, ADR-0046's loop queue names;
   - `client: LoopProbeClientInterface`, the probe side of ADR-0046's loop client (behaviour 5);
   - `loops: Sequence[LoopCheck]`, stored as a tuple;
   - `probe_cwd: str`, the `[loop_services] root`;
   - `probe_timeout: timedelta = DEFAULT_PROBE_TIMEOUT`.

   It exposes two read-only properties, `loops -> tuple[LoopCheck, ...]` and `probe_cwd -> str`, and one method, `async def check(self) -> LoopDoctorReport`, which produces these lines in this order:
   - **Broker.** `await amqp.connect()`. If it raises any `Exception`, the report is exactly one line, `broker: unreachable (<str(exc)>)`, with `ok=False`, and **nothing else runs** (no probe, no declare, no close). Otherwise the first line is `broker: ok <redacted_url>`, and every step below runs inside `try:` with `finally: await amqp.close()`.
   - **Per loop, in the given order.** Let `L = check.loop_id.value`, `N = f"{probe_timeout.total_seconds():g}"` (`10` by default) and `START = f"start one with vibey loop-service --loop {L}"`.
     - **Router.** `answer = await client.probe(check.loop_id, ("--version",), cwd=probe_cwd, timeout=probe_timeout)`. An `AmqpError` raised by the probe (for example an unroutable mandatory publish when no router declared the probe queue) counts as no answer.
       - An answer gives `loop {L}: router answering ({first})`, where `text = (answer.stdout or "").strip()` and `first = text.splitlines()[0].strip()[:80]` when `text` is non-empty, else `""`. If `answer.cached_at` is not `None`, append ` (cached {answer.cached_at.isoformat()})`.
       - No answer (`None`, or an `AmqpError`) gives `loop {L}: no router answered within {N}s; {START}`, and `ok` becomes False.
     - **Seats, in declared order.** For each seat name: `slug = SeatSlug.of(name)`, `queue = queues.seat(check.loop_id, slug)`, `depth = await amqp.queue_depth(queue)`, `consumers = await amqp.consumer_count(queue)`. Let `S = f"seat {L}.{slug}"`.
       - When `depth is None or consumers is None` (the queue does not exist): the line is `{S}: 0 waiting, 0 consumer(s) (not declared yet)`, and the seat counts as 0 consumers.
       - Otherwise the line is `{S}: {depth} waiting, {consumers} consumer(s)`, with the suffix ` (not resident)` when `check.residency` is True and `consumers == 0`.
       - Then, each on its own line directly after that seat's line, and each making `ok` False:
         - `{S}: {count} consumers; sub-doctrine 8.c allows a single instance per model`, when the seat's count is more than 1;
         - `{S}: no seat host; {START}`, when `check.residency` is False and the seat's count is 0.
     - **After the seats**, when `check.residency` is True and no seat of the loop has a count of at least 1: `loop {L}: no seat host consumes; {START}`, and `ok` becomes False.
   - `ok` is True only when no line above made it False.
3. **The doctor only reads.** It never publishes a run and never declares, binds or consumes a queue; `queue_depth` and `consumer_count` are passive declares. An undeclared seat queue is still undeclared after `check()`.
4. **Interfaces**, in `src/vibey/infrastructure/loop_service/interfaces/doctor_interface.py`, all `@runtime_checkable`:
   - `ProbeAnswerInterface`: read-only properties `stdout -> str | None` and `cached_at -> datetime | None`. ADR-0046's `RunResult` satisfies it.
   - `LoopProbeClientInterface`: `async def probe(self, loop_id: LoopId, args: tuple[str, ...], *, cwd: str, timeout: timedelta) -> ProbeAnswerInterface | None`. ADR-0046's `LoopServiceClient` satisfies it; the doctor depends on this one method only, so its fake needs only this method.
   - `LoopCheckInterface`: properties `loop_id -> LoopId`, `seats -> tuple[str, ...]`, `residency -> bool`.
   - `LoopDoctorReportInterface`: properties `lines -> tuple[str, ...]`, `ok -> bool`.
   - `LoopDoctorInterface`: properties `loops -> tuple[LoopCheckInterface, ...]` and `probe_cwd -> str`, and `async def check(self) -> LoopDoctorReportInterface`.
   `LoopCheck`, `LoopDoctorReport` and `LoopDoctor` satisfy their interfaces.
5. **Fakes**, in `tests/fakes/loop_service.py`, each a plain class with real in-memory behaviour:
   - `@dataclass(frozen=True, slots=True) class ProbeAnswer` with `stdout: str | None` and `cached_at: datetime | None = None` (satisfies `ProbeAnswerInterface`).
   - `class FakeLoopClient(answers: Mapping[str, ProbeAnswer | BaseException] | None = None)` (`LoopProbeClientInterface`), with scripted probe results per loop id value. `probe(loop_id, args, *, cwd, timeout)` appends `(loop_id.value, args, cwd, timeout)` to `self.probes`, raises the scripted answer if it is an exception, else returns it (`None` for a loop with no script).
   - `class UnreachableAmqpClient(InMemoryAmqpClient)`, a broker that refuses every connection: `__init__(self, error: str = "connection refused")` calls `super().__init__()` and sets `self.error` and `self.attempts = 0`; `async def connect(self) -> None` increments `attempts` and raises `AmqpNotConnected(self.error)`. Every other method is the in-memory broker's.

## Where to change
**Step 0, before any edit:** run the preflight block under *Conventions this lane relies on*. If any command prints nothing, or prints a signature different from the one stated there, make no edit: stop and report `blocked: <the missing or different interface>: <what grep printed>`.

- **New `src/vibey/infrastructure/loop_service/doctor.py`**: `LoopCheck`, `LoopDoctorReport`, `DEFAULT_PROBE_TIMEOUT`, `LoopDoctor`; `__all__` lists the four. Imports: `from collections.abc import Sequence`, `from dataclasses import dataclass`, `from datetime import timedelta`, `from typing import Final`, `from vibey_bootstrap.amqp import AmqpClientInterface, AmqpError`, `from vibey.domain.interfaces.run_protocol_interface import LoopQueueNamesInterface`, `from vibey.domain.loop import LoopId`, `from vibey.domain.residency import SeatSlug`, and `LoopProbeClientInterface` from the interface module. No Protocol is declared in this file (`tests/application/test_interfaces_convention.py:130-146` refuses one outside an `interfaces` package). A module docstring cites ADR-0046 §3-§4 and 8.c/8.g.
- **New `src/vibey/infrastructure/loop_service/interfaces/doctor_interface.py`** (behaviour 4). Copy the style of `src/vibey/infrastructure/engines/interfaces/local_engines_interface.py` (docstring "Mirrors `vibey/infrastructure/loop_service/doctor.py` (ADR-0016). Interfaces declare; they never consume."). It imports only `datetime`, `timedelta`, `typing` and `vibey.domain.loop.LoopId`. The `loop_service` packages, and their line in `.importlinter`'s `infrastructure-interfaces-declare-only` contract, come from ADR-0046's first loop-service lane; do not edit `.importlinter` or either `__init__.py`.
- **New or appended `tests/fakes/loop_service.py`** (behaviour 5). If the file does not exist, create it with the provenance line 1 and a module docstring. If it exists (ADR-0046's client lane may have created it), append with `open(path, "a")` and change no existing line; if a class with one of these three names is already there, stop and report the clash.
- **If `tests/fakes/registry.py` exists** (lane `fakes-registry`): append `LoopProbeClientInterface` to `DRIVER_SEAMS`, and add `FakeRegistration(port=LoopProbeClientInterface, build=FakeLoopClient)` and `FakeRegistration(port=AmqpClientInterface, build=UnreachableAmqpClient, note="a broker that refuses every connection")` to `REGISTRY`. If it does not exist, skip this step.
- **New `tests/infrastructure/loop_service/test_doctor.py`.** If `tests/infrastructure/loop_service/__init__.py` does not exist, create it holding the provenance line only.
- Line 1 of every new file is the provenance comment, copied byte for byte from a sibling, for example line 1 of `src/vibey/infrastructure/engines/loop_process_adapter.py`: `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
- **The AMQP capabilities are not added here.** `queue_depth` (ADR-0046 §4 "Backlog", lane L21) and `consumer_count` (ADR-0045 lane T21) are the family client's. If either is missing, stop and report; 10.e says they are taught to `vibey_bootstrap.amqp`, never rewritten here.

## Acceptance criteria
- [ ] Every line format in behaviour 2 has a test, and `ok` is correct in each.
- [ ] An unreachable broker gives exactly one line, and the loop client was never called (`client.probes == []`).
- [ ] An idle non-resident sovereign seat is not a fault; a paid seat without a host is.
- [ ] More than one consumer on a seat is reported as an 8.c violation.
- [ ] An undeclared seat queue is still undeclared after `check()` (the doctor only reads).
- [ ] `test_the_loop_client_probe_matches_the_port` passes against ADR-0046's real `LoopServiceClient` and `RunResult`.
- [ ] The tests need no broker, no Ollama and no network. They use no `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`. If `tests/meta/patching_baseline.json` exists, it does not change.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_doctor.py`. Shared setup in the module: `REDACTED = "amqp://guest:***@localhost:5672/"`; `names = LoopQueueNames("vibey")`; a helper that builds `LoopDoctor(amqp=..., redacted_url=REDACTED, queues=names, client=..., loops=..., probe_cwd="/work")`; an `async def _ignore(delivery: AmqpDeliveryInterface) -> None` handler that settles nothing; and an async helper `_seat(amqp, loop_id, name, *, consumers=0, waiting=0)` that does `queue = names.seat(loop_id, SeatSlug.of(name))`, `await amqp.declare_queue(queue)`, then `consumers` times `await amqp.consume(queue, prefetch=1, handler=_ignore)`, and for `waiting > 0` declares a direct exchange `"test.seats"`, binds `queue` to it with routing key `queue`, and publishes `waiting` messages `b"{}"` with `AmqpProperties(message_id=str(n))`. Never publish to a seat that also has a consumer. Every test uses a fresh `InMemoryAmqpClient()`.
- `test_unreachable_broker_is_a_single_failing_line`: `UnreachableAmqpClient()` → `lines == ("broker: unreachable (connection refused)",)`, `ok is False`, `client.probes == []`, `amqp.attempts == 1`.
- `test_router_answering_and_resident_seat_consumed_is_ok`: sovereignloop, seats `("gpt-oss:20b",)`, residency; the seat has 1 consumer; the client answers `ProbeAnswer("sovereignloop 3.0.0\n")`. `lines == ("broker: ok amqp://guest:***@localhost:5672/", "loop sovereignloop: router answering (sovereignloop 3.0.0)", "seat sovereignloop.gpt-oss-20b: 0 waiting, 1 consumer(s)")`, `ok is True`, and `client.probes == [("sovereignloop", ("--version",), "/work", timedelta(seconds=10))]`.
- `test_silent_router_fails_and_names_the_command`: the client has no script. The lines contain `"loop sovereignloop: no router answered within 10s; start one with vibey loop-service --loop sovereignloop"`; `ok is False`.
- `test_an_unroutable_probe_reads_as_a_silent_router`: the client's script for sovereignloop is `AmqpPublishError("unroutable")`. The lines contain `"loop sovereignloop: no router answered within 10s; start one with vibey loop-service --loop sovereignloop"`; `ok is False`.
- `test_idle_non_resident_sovereign_seat_is_not_a_fault`: seats `("gpt-oss:20b", "qwen3:14b")`; the first has 1 consumer, the second is declared with none. The lines contain `"seat sovereignloop.qwen3-14b: 0 waiting, 0 consumer(s) (not resident)"`; `ok is True`.
- `test_sovereign_loop_with_no_consuming_seat_fails`: seats `("gpt-oss:20b",)`, declared with no consumer. The lines end with `"seat sovereignloop.gpt-oss-20b: 0 waiting, 0 consumer(s) (not resident)"` and `"loop sovereignloop: no seat host consumes; start one with vibey loop-service --loop sovereignloop"`; `ok is False`.
- `test_paid_seat_without_a_host_fails`: paidloop, seats `("claudeloop",)`, no residency, declared with no consumer; the client answers paidloop. The lines end with `"seat paidloop.claudeloop: 0 waiting, 0 consumer(s)"` and `"seat paidloop.claudeloop: no seat host; start one with vibey loop-service --loop paidloop"`; `ok is False`.
- `test_more_than_one_consumer_on_a_seat_fails_citing_8c`: sovereign seat `gpt-oss:20b` with 2 consumers. The lines contain `"seat sovereignloop.gpt-oss-20b: 0 waiting, 2 consumer(s)"` directly followed by `"seat sovereignloop.gpt-oss-20b: 2 consumers; sub-doctrine 8.c allows a single instance per model"`; `ok is False`.
- `test_seat_depth_is_reported`: seats `("gpt-oss:20b", "qwen3:14b")`; the first has 1 consumer, the second has 3 waiting messages and no consumer. The lines contain `"seat sovereignloop.qwen3-14b: 3 waiting, 0 consumer(s) (not resident)"`; `ok is True`.
- `test_undeclared_seat_queue_reads_as_zero`: sovereign seat `gpt-oss:20b` never declared. The lines contain `"seat sovereignloop.gpt-oss-20b: 0 waiting, 0 consumer(s) (not declared yet)"`; `ok is False`; and afterwards `await amqp.queue_depth(names.seat(LoopId.SOVEREIGNLOOP, "gpt-oss-20b"))` is still `None`.
- `test_cached_probe_answer_is_marked`: the answer is `ProbeAnswer("sovereignloop 3.0.0\nmore\n", cached_at=datetime(2026, 9, 22, 11, 0, tzinfo=UTC))`. The router line is `"loop sovereignloop: router answering (sovereignloop 3.0.0) (cached 2026-09-22T11:00:00+00:00)"`.
- `test_router_line_keeps_the_first_80_characters_and_accepts_no_stdout`: an answer with `stdout="x" * 120` gives `"loop sovereignloop: router answering (" + "x" * 80 + ")"`; an answer with `stdout=None` gives `"loop sovereignloop: router answering ()"`.
- `test_probe_timeout_is_printed_and_passed`: with `probe_timeout=timedelta(seconds=2.5)` and no answer, the line says `within 2.5s`, and the recorded probe timeout is `timedelta(seconds=2.5)`.
- `test_classes_satisfy_their_interfaces`: `isinstance` of a `LoopCheck` (`LoopCheckInterface`), a `LoopDoctorReport` (`LoopDoctorReportInterface`), a `LoopDoctor` (`LoopDoctorInterface`), `FakeLoopClient()` (`LoopProbeClientInterface`) and `ProbeAnswer(None)` (`ProbeAnswerInterface`); and the doctor's `loops` and `probe_cwd` return what it was built with.
- `test_the_loop_client_probe_matches_the_port`: `inspect.signature(LoopServiceClient.probe)` and `inspect.signature(LoopProbeClientInterface.probe)` have the same parameter names and kinds, in order; `inspect.iscoroutinefunction(LoopServiceClient.probe)`; and `{"stdout", "cached_at"} <= {f.name for f in dataclasses.fields(RunResult)}`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/fakes tests/meta tests/application/test_interfaces_convention.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
```
The full-suite coverage run needs PostgreSQL today (the root `tests/conftest.py` opens it at session start, defaulting to `postgresql://$USER@localhost:5432/vibey_test`); the doctor's own tests touch no service.

## Out of scope
- Wiring into `vibey doctor`, `bootstrap.build_loop_doctor`, and choosing the loops and seats from config (child 2, `split-380-2-doctor-cli`).
- Installing RabbitMQ (lanes `installer-broker-cache` and `installer-cli`).
- `vibey doctor --cluster` (a follow-up may add the broker to `ClusterPreflight`).
- Teaching `vibey_bootstrap.amqp` queue depth or consumer count (lanes L21 and T21), and the loop client itself (ADR-0046's client lane).
- A config key for the probe timeout (it is a constructor value here).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject.

## Conventions this lane relies on (everything needed is here)
None of these exists on the integration branch at `4317cff6`; each comes from a lane this one depends on. The names and signatures below are the ones this lane assumes. **Preflight** (run from the repository root; each command must print at least one line, and what it prints must match the signature given below):
```bash
grep -n "class InMemoryAmqpClient" src/vibey_tools/bootstrap/vibey_bootstrap/amqp/memory.py
grep -n "async def connect\|async def close\|async def consume\|async def queue_depth\|async def consumer_count" src/vibey_tools/bootstrap/vibey_bootstrap/amqp/interfaces/client_interface.py
grep -n "AmqpClientInterface\|AmqpError\|AmqpNotConnected\|AmqpPublishError\|AmqpProperties\|InMemoryAmqpClient\|AmqpDeliveryInterface" src/vibey_tools/bootstrap/vibey_bootstrap/amqp/__init__.py
grep -n "class LoopId\|SOVEREIGNLOOP\|PAIDLOOP" src/vibey/domain/loop.py
grep -n "class SeatSlug\|def of" src/vibey/domain/residency.py
grep -n "class LoopQueueNames\|def seat\|class RunResult\|stdout\|cached_at" src/vibey/domain/run_protocol.py
grep -n "class LoopQueueNamesInterface" src/vibey/domain/interfaces/run_protocol_interface.py
grep -n -A6 "class LoopServiceClient\|async def probe" src/vibey/infrastructure/loop_service/client.py
grep -n "vibey.infrastructure.loop_service.interfaces" .importlinter
```

**From `split-351-1-amqp-contract` (`vibey_bootstrap.amqp`, all exported from `vibey_bootstrap/amqp/__init__.py`):**
- `AmqpClientInterface` (`vibey_bootstrap/amqp/interfaces/client_interface.py`), whose async methods include `connect() -> None`, `close() -> None`, `declare_exchange(name, kind)` (`kind` in `direct`, `topic`, `fanout`), `declare_queue(name, *, arguments=None, durable=True, exclusive=False, auto_delete=False) -> str`, `bind(queue, exchange, routing_key)`, `publish(exchange, routing_key, body, properties, *, mandatory=True)` and `consume(queue, *, prefetch, handler) -> str`.
- `AmqpDeliveryInterface`, the type a `consume` handler receives.
- `InMemoryAmqpClient()`: a real in-memory broker with no network; declaring the same exchange or queue twice with equal arguments is a no-op.
- `AmqpProperties(message_id: str | None = None, ...)`.
- `AmqpError(Exception)`, `AmqpPublishError(AmqpError)`, `AmqpNotConnected(AmqpError)`.
- `AmqpSettings(url).redacted_url() -> str` replaces the password with `***`.

**From `loops-queue-depth` (ADR-0046 lane L21), assumed:** `async def queue_depth(self, queue: str) -> int | None` on `AmqpClientInterface`, `AmqpClient` and `InMemoryAmqpClient`: the number of messages waiting in the queue, read by a passive declare; `None` when the queue does not exist.

**From `harness-T21-amqp-consumer-count` (ADR-0045 lane T21):** `async def consumer_count(self, queue: str) -> int | None` on the same three: the number of active consumers, by a passive declare on its own channel; `None` when the queue does not exist; a cancelled consumer no longer counts.

**From `loops-run-protocol` (ADR-0046 §3, §10), assumed:**
- `vibey.domain.loop.LoopId`, a `StrEnum` with `SOVEREIGNLOOP = "sovereignloop"` and `PAIDLOOP = "paidloop"`.
- `vibey.domain.residency.SeatSlug.of(name: str) -> str` (a classmethod or staticmethod): lower case, every character outside `[a-z0-9-]` becomes `-`, so `gpt-oss:20b` → `gpt-oss-20b` and `qwen3:14b` → `qwen3-14b`; an engine id such as `claudeloop` is unchanged.
- `vibey.domain.run_protocol.LoopQueueNames(prefix: str = "vibey")` with `seat(self, loop_id: LoopId, seat: str) -> str` returning `"<prefix>.runs.<loop>.<seat>"`, declared by `vibey.domain.interfaces.run_protocol_interface.LoopQueueNamesInterface`.
- `vibey.domain.run_protocol.RunResult`, a frozen dataclass whose fields include `stdout: str | None` and `cached_at: datetime | None` (the time of the real result a cached probe answer repeats, ADR-0046 §4; `None` when the probe really ran).

**From `loops-client` (ADR-0046 §10 `infrastructure/loop_service/client.py`), assumed:**
- `class LoopServiceClient` with `async def probe(self, loop_id: LoopId, args: tuple[str, ...], *, cwd: str, timeout: timedelta) -> RunResult | None`, which publishes a probe to `vibey.runs.<loop>.probe` and returns `None` when nothing answers within `timeout`.
- The packages `src/vibey/infrastructure/loop_service/` and `src/vibey/infrastructure/loop_service/interfaces/`, and `vibey.infrastructure.loop_service.interfaces` listed in `.importlinter`'s `infrastructure-interfaces-declare-only` contract (added by ADR-0046's first loop-service lane).

## Standing constraints
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`. They must keep passing.
- **Line 1 of every new file** is the provenance comment, copied byte for byte from a sibling file.
- **Substitution at a declared seam only:** constructor or keyword injection. Never `monkeypatch.setattr` on a module or class attribute, `mock.patch`, `MagicMock` or `AsyncMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` are allowed.
- **A fake is a plain class with real in-memory behaviour for every method of its port.** `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only `pass`, only `return None`, or only `raise NotImplementedError`.
- **The default run needs no outside service.** Tests against a real broker are marked `integration` and skip unless `VIBEY_TEST_AMQP_URL` is set; this lane writes none.
- **Defaults stay today's until #381 (R34):** `queue.backend = "postgres"` and `engines.invocation = "subprocess"`. Nothing here reads either.
- **Editing:** change existing files with `edit_file` (an exact, unique `old_string` copied from `read_file`), never `write_file`, for any existing file over 100 lines. Never rewrite an existing test file.
- **Arch Linux and macOS (8.h):** nothing here is OS-specific; the tests are pure in-memory Python.

**Depends on:** split-351-1-amqp-contract, loops-run-protocol, loops-client, loops-queue-depth, harness-T21-amqp-consumer-count
- split-351-1-amqp-contract: `AmqpClientInterface`, `InMemoryAmqpClient`, `AmqpProperties`, `AmqpSettings.redacted_url()` and the `AmqpError` family.
- loops-run-protocol: `LoopId`, `SeatSlug.of`, `LoopQueueNames.seat` and its interface, and `RunResult` with `stdout` and `cached_at`.
- loops-client: `LoopServiceClient.probe`, the `loop_service` packages and their `.importlinter` line.
- loops-queue-depth: `queue_depth(queue)` on the family AMQP client and its in-memory double.
- harness-T21-amqp-consumer-count: `consumer_count(queue)` on the family AMQP client and its in-memory double.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
