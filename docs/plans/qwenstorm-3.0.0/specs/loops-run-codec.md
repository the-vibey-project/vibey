## Title
feat(domain): a strict run-protocol codec that refuses every capacity and completion key

ADR-0046 lane L04b (slug `loops-run-codec`).

## Why
- **The law.** Non-negotiable 2 (CLAUDE.md): `CreditsExhausted` never acquires a `resets_at`
  (`src/vibey/domain/capacity.py:20-24`). Non-negotiable 3: a capacity rejection outranks a
  completion claim. Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-234`) puts both
  rotation layers on the bus, so messages now cross a process boundary where either rule could
  leak.
- **The decision.** ADR-0046 §3 "Messages" (`specs/ADR-two-loops.md:158`): "pure dataclasses with
  a strict codec. The codec refuses any extra key. In particular it refuses `resets_at`,
  `capacity`, `capacity_state`, `credits`, `complete` and `success`." Non-negotiable 2 as the ADR
  states it (`:333`): "Capacity never crosses the wire: the codec refuses ... and a property test
  proves no such key survives encoding." The design sheet puts the codec in its own module,
  `domain/run_codec.py`, beside `domain/run_protocol.py` (decision D14).
- **Carried from R19** (`specs/rmq-r19-run-protocol.md` behaviour 4; `issue-audit/updates/366.md`):
  `encode` / `decode` dispatching on `schema`, `to_bytes` / `from_bytes`, and the
  `MalformedRunMessage(VibeyError)` error for an unknown schema, a missing key, any extra key, a
  wrong type or a naive datetime.
- **The gap, at integration `d3b4a388`.** There is no codec for run messages. The closest pattern
  is `LedgerRecordCodec` (`src/vibey/domain/ledger_record.py:57-159`): strict key sets, typed
  readers, and `bool` refused where an integer is expected. This lane copies that style.
- **9.b** (`doctrines.md:349`): the class gets an interface beside it. An exception type does not
  (the style of `src/vibey/domain/ledger_record.py:49-54`).

## Required behaviour
1. **`src/vibey/domain/errors.py`**: append at the end of the file (after
   `SovereignResearchUnavailable`, which ends at `:83`):
   ```python


   class MalformedRunMessage(VibeyError):
       """A run-protocol message that is not one (ADR-0046 §3): an unknown schema, a missing or
       unknown key -- every capacity or completion key among them -- a wrong type, or a time with
       no zone. The message names the key at fault. An exception type, so it has no interface
       beside it: a `Protocol` cannot be raised or caught."""
   ```
2. **`src/vibey/domain/run_codec.py`** (new) is exactly this module, after the provenance line
   and a module docstring. The docstring cites ADR-0046 §3 and non-negotiables 2 and 3, and says
   decoding is strict because a message arrives from another process.
   ```python
   import json
   import math
   from collections.abc import Callable, Mapping
   from dataclasses import fields
   from datetime import datetime
   from enum import StrEnum
   from types import MappingProxyType
   from typing import Final
   from uuid import UUID

   from vibey.domain.errors import MalformedRunMessage
   from vibey.domain.interfaces.run_codec_interface import RunProtocolCodecInterface
   from vibey.domain.loop import LoopId
   from vibey.domain.run_protocol import (
       SCHEMA_ACCEPTED,
       SCHEMA_CONTROL,
       SCHEMA_PROGRESS,
       SCHEMA_REQUEST,
       SCHEMA_RESULT,
       SCHEMA_ROUTE,
       SCHEMA_ROUTED,
       RouteCandidate,
       RouteRequest,
       RouteStatus,
       RunAccepted,
       RunControl,
       RunControlCommand,
       RunMessage,
       RunProgress,
       RunPurpose,
       RunRequest,
       RunResult,
       RunRouted,
       RunStatus,
       RunSupersede,
   )

   FORBIDDEN_KEYS: Final[frozenset[str]] = frozenset(
       {"resets_at", "capacity", "capacity_state", "credits", "complete", "success"}
   )
   """Keys no run message may carry (non-negotiables 2 and 3). No message class has one, so
   decoding refuses each of them as an unknown key."""

   SCHEMA_OF: Final[Mapping[type[RunMessage], str]] = MappingProxyType(
       {
           RouteRequest: SCHEMA_ROUTE,
           RunRouted: SCHEMA_ROUTED,
           RunRequest: SCHEMA_REQUEST,
           RunAccepted: SCHEMA_ACCEPTED,
           RunProgress: SCHEMA_PROGRESS,
           RunResult: SCHEMA_RESULT,
           RunControl: SCHEMA_CONTROL,
       }
   )

   CLASS_OF: Final[Mapping[str, type[RunMessage]]] = MappingProxyType(
       {schema: cls for cls, schema in SCHEMA_OF.items()}
   )

   type _Raw = Mapping[str, object]


   class RunProtocolCodec:
       """Writes and reads run messages as JSON objects. Stateless."""

       def __init__(self) -> None:
           self._decoders: Mapping[str, Callable[[_Raw], RunMessage]] = {
               SCHEMA_ROUTE: self._route_request,
               SCHEMA_ROUTED: self._run_routed,
               SCHEMA_REQUEST: self._run_request,
               SCHEMA_ACCEPTED: self._run_accepted,
               SCHEMA_PROGRESS: self._run_progress,
               SCHEMA_RESULT: self._run_result,
               SCHEMA_CONTROL: self._run_control,
           }

       def encode(self, message: RunMessage) -> dict[str, object]:
           return {"schema": SCHEMA_OF[type(message)], **self._fields(message)}

       def decode(self, raw: Mapping[str, object]) -> RunMessage:
           schema = raw.get("schema")
           if not isinstance(schema, str) or schema not in self._decoders:
               raise MalformedRunMessage(f"unknown schema {schema!r}")
           expected = frozenset({"schema", *(field.name for field in fields(CLASS_OF[schema]))})
           self._keys(schema, raw, expected)
           try:
               return self._decoders[schema](raw)
           except ValueError as exc:
               raise MalformedRunMessage(f"{schema}: {exc}") from exc

       def to_bytes(self, message: RunMessage) -> bytes:
           return json.dumps(self.encode(message), sort_keys=True, separators=(",", ":")).encode(
               "utf-8"
           )

       def from_bytes(self, body: bytes) -> RunMessage:
           try:
               raw = json.loads(body.decode("utf-8"))
           except ValueError as exc:
               raise MalformedRunMessage(f"not a JSON message: {exc}") from exc
           if not isinstance(raw, dict):
               raise MalformedRunMessage(f"a message must be a JSON object, not {type(raw).__name__}")
           return self.decode(raw)

       # -- encoding --------------------------------------------------------------------------

       def _fields(self, value: RunMessage | RunSupersede | RouteCandidate) -> dict[str, object]:
           return {field.name: self._json(getattr(value, field.name)) for field in fields(value)}

       def _json(self, value: object) -> object:
           if isinstance(value, UUID):
               return str(value)
           if isinstance(value, datetime):
               return value.isoformat()
           if isinstance(value, StrEnum):
               return value.value
           if isinstance(value, tuple):
               return [self._json(item) for item in value]
           if isinstance(value, RunSupersede | RouteCandidate):
               return self._fields(value)
           return value

       # -- decoding: one method per message ------------------------------------------------

       def _route_request(self, raw: _Raw) -> RunMessage:
           return RouteRequest(
               route_id=self._uuid(raw, "route_id"),
               loop_id=self._member(raw, "loop_id", LoopId),
               project_id=self._optional(raw, "project_id", self._uuid),
               candidates=self._candidates(raw, "candidates"),
               pin=self._optional(raw, "pin", self._text),
               model_pin=self._optional(raw, "model_pin", self._text),
               min_context=self._optional(raw, "min_context", self._integer),
               requested_at=self._instant(raw, "requested_at"),
               caller=self._text(raw, "caller"),
           )

       def _run_routed(self, raw: _Raw) -> RunMessage:
           return RunRouted(
               route_id=self._uuid(raw, "route_id"),
               loop_id=self._member(raw, "loop_id", LoopId),
               status=self._member(raw, "status", RouteStatus),
               engine_id=self._optional(raw, "engine_id", self._text),
               seat=self._optional(raw, "seat", self._text),
               model=self._optional(raw, "model", self._text),
               switched=self._flag(raw, "switched"),
               reason=self._text(raw, "reason"),
               routed_at=self._instant(raw, "routed_at"),
               route_ms=self._number(raw, "route_ms"),
               seat_depth=self._optional(raw, "seat_depth", self._integer),
               seat_oldest_wait_seconds=self._optional(raw, "seat_oldest_wait_seconds", self._number),
           )

       def _run_request(self, raw: _Raw) -> RunMessage:
           return RunRequest(
               run_id=self._uuid(raw, "run_id"),
               loop_id=self._member(raw, "loop_id", LoopId),
               engine_id=self._text(raw, "engine_id"),
               route_id=self._optional(raw, "route_id", self._uuid),
               model_pin=self._optional(raw, "model_pin", self._text),
               purpose=self._member(raw, "purpose", RunPurpose),
               args=self._strings(raw, "args"),
               cwd=self._text(raw, "cwd"),
               run_dir=self._optional(raw, "run_dir", self._text),
               supersedes=self._optional(raw, "supersedes", self._supersede),
               deadline_seconds=self._integer(raw, "deadline_seconds"),
               start_by=self._instant(raw, "start_by"),
               capture_output=self._flag(raw, "capture_output"),
               requested_at=self._instant(raw, "requested_at"),
               caller=self._text(raw, "caller"),
           )

       def _run_accepted(self, raw: _Raw) -> RunMessage:
           return RunAccepted(
               run_id=self._uuid(raw, "run_id"),
               loop_id=self._member(raw, "loop_id", LoopId),
               engine_id=self._text(raw, "engine_id"),
               seat=self._text(raw, "seat"),
               model=self._optional(raw, "model", self._text),
               instance=self._text(raw, "instance"),
               pid=self._optional(raw, "pid", self._integer),
               started_at=self._instant(raw, "started_at"),
               queued_seconds=self._number(raw, "queued_seconds"),
           )

       def _run_progress(self, raw: _Raw) -> RunMessage:
           return RunProgress(
               run_id=self._uuid(raw, "run_id"),
               seq=self._integer(raw, "seq"),
               line=self._text(raw, "line"),
           )

       def _run_result(self, raw: _Raw) -> RunMessage:
           return RunResult(
               run_id=self._uuid(raw, "run_id"),
               status=self._member(raw, "status", RunStatus),
               exit_code=self._optional(raw, "exit_code", self._integer),
               meta_status=self._optional(raw, "meta_status", self._text),
               started_at=self._optional(raw, "started_at", self._instant),
               finished_at=self._instant(raw, "finished_at"),
               detail=self._text(raw, "detail"),
               stdout=self._optional(raw, "stdout", self._text),
               stderr=self._optional(raw, "stderr", self._text),
               cached_at=self._optional(raw, "cached_at", self._instant),
           )

       def _run_control(self, raw: _Raw) -> RunMessage:
           return RunControl(
               run_id=self._optional(raw, "run_id", self._uuid),
               command=self._member(raw, "command", RunControlCommand),
               text=self._optional(raw, "text", self._text),
               supersedes=self._optional(raw, "supersedes", self._supersede),
           )

       # -- readers ---------------------------------------------------------------------------

       @staticmethod
       def _keys(where: str, raw: _Raw, expected: frozenset[str]) -> None:
           missing = expected - raw.keys()
           if missing:
               raise MalformedRunMessage(f"{where}: missing key(s): {', '.join(sorted(missing))}")
           extra = raw.keys() - expected
           if extra:
               raise MalformedRunMessage(f"{where}: unknown key(s): {', '.join(sorted(extra))}")

       @staticmethod
       def _optional[T](raw: _Raw, key: str, read: Callable[[_Raw, str], T]) -> T | None:
           return None if raw[key] is None else read(raw, key)

       @staticmethod
       def _text(raw: _Raw, key: str) -> str:
           value = raw[key]
           if not isinstance(value, str):
               raise MalformedRunMessage(f"{key!r} must be a string, not {type(value).__name__}")
           return value

       @staticmethod
       def _integer(raw: _Raw, key: str) -> int:
           value = raw[key]
           # bool is an int subclass; `true` is not a count.
           if isinstance(value, bool) or not isinstance(value, int):
               raise MalformedRunMessage(f"{key!r} must be an integer, not {type(value).__name__}")
           return value

       @staticmethod
       def _number(raw: _Raw, key: str) -> float:
           value = raw[key]
           if isinstance(value, bool) or not isinstance(value, int | float):
               raise MalformedRunMessage(f"{key!r} must be a number, not {type(value).__name__}")
           if not math.isfinite(value):
               raise MalformedRunMessage(f"{key!r} must be a finite number, not {value!r}")
           return float(value)

       @staticmethod
       def _flag(raw: _Raw, key: str) -> bool:
           value = raw[key]
           if not isinstance(value, bool):
               raise MalformedRunMessage(f"{key!r} must be true or false, not {type(value).__name__}")
           return value

       def _uuid(self, raw: _Raw, key: str) -> UUID:
           text = self._text(raw, key)
           try:
               return UUID(text)
           except ValueError as exc:
               raise MalformedRunMessage(f"{key!r} is not a UUID: {text!r}") from exc

       def _instant(self, raw: _Raw, key: str) -> datetime:
           text = self._text(raw, key)
           try:
               moment = datetime.fromisoformat(text)
           except ValueError as exc:
               raise MalformedRunMessage(f"{key!r} is not an ISO-8601 time: {text!r}") from exc
           if moment.utcoffset() is None:
               raise MalformedRunMessage(f"{key!r} has no zone: {text!r}")
           return moment

       def _member[E: StrEnum](self, raw: _Raw, key: str, enum: type[E]) -> E:
           text = self._text(raw, key)
           try:
               return enum(text)
           except ValueError as exc:
               raise MalformedRunMessage(f"{key!r} has no member {text!r}") from exc

       @staticmethod
       def _strings(raw: _Raw, key: str) -> tuple[str, ...]:
           value = raw[key]
           if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
               raise MalformedRunMessage(f"{key!r} must be a list of strings")
           return tuple(value)

       def _supersede(self, raw: _Raw, key: str) -> RunSupersede:
           value = raw[key]
           if not isinstance(value, dict):
               raise MalformedRunMessage(f"{key!r} must be an object, not {type(value).__name__}")
           self._keys(key, value, frozenset({"key", "attempt"}))
           return RunSupersede(key=self._text(value, "key"), attempt=self._integer(value, "attempt"))

       def _candidates(self, raw: _Raw, key: str) -> tuple[RouteCandidate, ...]:
           value = raw[key]
           if not isinstance(value, list):
               raise MalformedRunMessage(f"{key!r} must be a list, not {type(value).__name__}")
           candidates = []
           for index, item in enumerate(value):
               where = f"{key}[{index}]"
               if not isinstance(item, dict):
                   raise MalformedRunMessage(f"{where} must be an object, not {type(item).__name__}")
               self._keys(where, item, frozenset({"engine_id", "weight"}))
               candidates.append(
                   RouteCandidate(
                       engine_id=self._text(item, "engine_id"), weight=self._integer(item, "weight")
                   )
               )
           return tuple(candidates)


   RUN_CODEC: Final[RunProtocolCodecInterface] = RunProtocolCodec()
   """The codec every loop process shares. Stateless, so one instance serves; annotated with the
   interface so `mypy --strict` checks the class against its seam."""
   ```
   This exact module (with a local stand-in for `MalformedRunMessage`) passed `mypy --strict` and
   the Hypothesis round trip below on a scratch copy. Keep it as written.

   What it guarantees:
   - `encode` adds `"schema"` and turns `UUID` into `str`, `datetime` into `isoformat()`, an enum
     into its value, a tuple into a list, and `RunSupersede` / `RouteCandidate` into an object.
   - `decode` requires the **exact** key set: a missing key, an unknown key (every forbidden key
     among them), a wrong type, a bad UUID, a naive or unreadable time, an unknown enum value, a
     non-finite number, or a nested object with the wrong keys raises `MalformedRunMessage`. So
     does a `ValueError` from a message's own `__post_init__`, prefixed with the schema.
   - `to_bytes` is canonical: sorted keys and no spaces. `from_bytes` refuses bytes that are not
     UTF-8, text that is not JSON, and JSON that is not an object.
3. **`src/vibey/domain/interfaces/run_codec_interface.py`** (new):
   ```python
   from __future__ import annotations

   from collections.abc import Mapping
   from typing import TYPE_CHECKING, Protocol, runtime_checkable

   if TYPE_CHECKING:
       from vibey.domain.run_protocol import RunMessage


   @runtime_checkable
   class RunProtocolCodecInterface(Protocol):
       """Writes and reads run-protocol messages; decoding is strict."""

       def encode(self, message: RunMessage) -> dict[str, object]: ...

       def decode(self, raw: Mapping[str, object]) -> RunMessage: ...

       def to_bytes(self, message: RunMessage) -> bytes: ...

       def from_bytes(self, body: bytes) -> RunMessage: ...
   ```
   Put a module docstring before `from __future__` saying that it mirrors
   `vibey/domain/run_codec.py` (ADR-0016) and that interfaces declare and never consume.
4. The module is pure (`json` and `math` are stdlib; nothing reads a clock or a file).
   `tests/domain/test_domain_purity.py` walks it.

## Where to change
- `src/vibey/domain/errors.py` (83 lines): append with `edit_file`, using its last three lines as
  `old_string`.
- New: `src/vibey/domain/run_codec.py`, `src/vibey/domain/interfaces/run_codec_interface.py`,
  `tests/domain/test_run_codec.py`. Line 1 of each new file is the provenance comment, copied byte
  for byte from line 1 of `src/vibey/domain/engine.py`.
- If `src/vibey/domain/run_protocol.py` does not exist, stop and report
  `blocked: loops-run-protocol-messages has not landed`.
- No fake is registered: the codec is pure and is used directly in tests.

## Acceptance criteria
- [ ] `test_every_message_round_trips` (Hypothesis) holds for all seven message types, through
      both `encode`/`decode` and `to_bytes`/`from_bytes`.
- [ ] `test_no_encoded_message_carries_a_forbidden_key` (Hypothesis) holds.
- [ ] Each forbidden key is refused as an unknown key (`test_decode_refuses_each_forbidden_key`).
- [ ] Every malformation in `test_decode_refuses_each_malformation` raises `MalformedRunMessage`
      with the listed text.
- [ ] `tests/domain/test_errors.py` and `tests/domain/test_run_protocol.py` pass unedited.
- [ ] `tests/domain/test_domain_purity.py` passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_run_codec.py` (pure objects only). Start it with these strategies, which were
checked on a scratch copy:
```python
instants = st.datetimes(timezones=st.just(UTC))
texts = st.text(max_size=20)
names = st.text(min_size=1, max_size=20)
counts = st.integers(min_value=0, max_value=10**6)
seconds = st.floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False)
supersedes = st.builds(RunSupersede, key=names, attempt=counts)
candidates = st.builds(RouteCandidate, engine_id=names, weight=counts)
loops = st.sampled_from(LoopId)

route_requests = st.builds(
    RouteRequest, route_id=st.uuids(), loop_id=loops, project_id=st.none() | st.uuids(),
    candidates=st.lists(candidates, max_size=4, unique_by=lambda c: c.engine_id).map(tuple),
    pin=st.none() | names, model_pin=st.none() | names,
    min_context=st.none() | st.integers(min_value=1, max_value=10**6),
    requested_at=instants, caller=names,
)
routed = st.builds(
    RunRouted, route_id=st.uuids(), loop_id=loops, status=st.just(RouteStatus.ROUTED),
    engine_id=names, seat=names, model=st.none() | names, switched=st.booleans(), reason=texts,
    routed_at=instants, route_ms=seconds, seat_depth=st.none() | counts,
    seat_oldest_wait_seconds=st.none() | seconds,
)
unrouted = st.builds(
    RunRouted, route_id=st.uuids(), loop_id=loops,
    status=st.sampled_from([RouteStatus.UNROUTABLE, RouteStatus.DEAD_LETTERED]),
    engine_id=st.none(), seat=st.none() | names, model=st.none() | names,
    switched=st.booleans(), reason=texts, routed_at=instants, route_ms=seconds,
    seat_depth=st.none() | counts, seat_oldest_wait_seconds=st.none() | seconds,
)
run_requests = st.builds(
    RunRequest, run_id=st.uuids(), loop_id=loops, engine_id=names,
    route_id=st.none() | st.uuids(), model_pin=st.none() | names,
    purpose=st.sampled_from(RunPurpose), args=st.lists(texts, max_size=4).map(tuple),
    cwd=texts.map(lambda path: "/" + path), run_dir=st.none() | texts,
    supersedes=st.none() | supersedes, deadline_seconds=st.integers(min_value=1, max_value=10**6),
    start_by=instants, capture_output=st.booleans(), requested_at=instants, caller=texts,
)
accepted = st.builds(
    RunAccepted, run_id=st.uuids(), loop_id=loops, engine_id=names, seat=names,
    model=st.none() | names, instance=texts, pid=st.none() | counts, started_at=instants,
    queued_seconds=seconds,
)
progress = st.builds(
    RunProgress, run_id=st.uuids(), seq=st.integers(min_value=1, max_value=10**6), line=texts
)
results = st.builds(
    RunResult, run_id=st.uuids(), status=st.sampled_from(RunStatus),
    exit_code=st.none() | st.integers(min_value=-255, max_value=255),
    meta_status=st.none() | texts, started_at=st.none() | instants, finished_at=instants,
    detail=texts, stdout=st.none() | texts, stderr=st.none() | texts,
    cached_at=st.none() | instants,
)
supersede_controls = st.builds(
    RunControl, run_id=st.none(), command=st.just(RunControlCommand.SUPERSEDE), text=st.none(),
    supersedes=supersedes,
)
run_controls = st.builds(
    RunControl, run_id=st.uuids(),
    command=st.sampled_from([RunControlCommand.STOP, RunControlCommand.WIND_DOWN,
                             RunControlCommand.PROMPT_NOW, RunControlCommand.PROMPT_AT_BREAK]),
    text=names, supersedes=st.none(),
)
messages = st.one_of(
    route_requests, routed, unrouted, run_requests, accepted, progress, results,
    supersede_controls, run_controls,
)
```
(`ruff format` will reflow it.) Build a valid `RunResult` for the example tests with
`datetime(2026, 9, 22, 10, 0, tzinfo=UTC)` and `UUID(int=1)`.
- `test_every_message_round_trips` (`@given(messages)`): `RUN_CODEC.decode(RUN_CODEC.encode(m)) == m`
  and `RUN_CODEC.from_bytes(RUN_CODEC.to_bytes(m)) == m`.
- `test_no_encoded_message_carries_a_forbidden_key` (`@given(messages)`): walk the encoded object
  recursively (dict keys, including inside lists); no key is in `FORBIDDEN_KEYS`.
- `test_encode_writes_json_types`: for the example `RunResult`, `raw["schema"] ==
  "vibey.run.result/1"`, `raw["run_id"] == "00000000-0000-0000-0000-000000000001"`,
  `raw["status"] == "exited"`, `raw["finished_at"] == "2026-09-22T10:00:00+00:00"`, and
  `set(raw) == {"schema", *(f.name for f in dataclasses.fields(RunResult))}`. For a
  `RouteRequest` with one candidate, `raw["candidates"] == [{"engine_id": "claudeloop",
  "weight": 1}]`; for a `RunRequest` with `supersedes=RunSupersede("job", 2)` and
  `args=("run", "p.md")`, `raw["supersedes"] == {"key": "job", "attempt": 2}` and
  `raw["args"] == ["run", "p.md"]`.
- `test_decode_refuses_each_forbidden_key` (parametrized over `sorted(FORBIDDEN_KEYS)`):
  `{**RUN_CODEC.encode(result), key: None}` raises `MalformedRunMessage` matching
  `f"unknown key\(s\): {key}"`. Also, a `supersedes` object with an extra `"resets_at"` raises
  matching `"supersedes: unknown key\(s\): resets_at"`, and a candidate with an extra
  `"capacity"` raises matching `r"candidates\[0\]: unknown key\(s\): capacity"`.
- `test_decode_refuses_each_malformation` (parametrized; each changes the encoded example
  `RunResult` and matches the message):
  `{"schema": "vibey.run.result/2"}` → `"unknown schema"`; `{"exit_code": "0"}` and
  `{"exit_code": True}` → `"'exit_code' must be an integer"`; `{"detail": 5}` → `"'detail' must be a
  string"`; `{"finished_at": "2026-09-22T10:05:00"}` → `"'finished_at' has no zone"`;
  `{"finished_at": "yesterday"}` → `"'finished_at' is not an ISO-8601 time"`;
  `{"run_id": "nope"}` → `"'run_id' is not a UUID"`; `{"status": "finished"}` →
  `"'status' has no member 'finished'"`.
- `test_decode_refuses_missing_keys_and_bad_shapes`: deleting `"detail"` → `"missing key\(s\):
  detail"`; a raw object with no `"schema"` → `"unknown schema None"`; a `RunRequest` with
  `"cwd": "relative"` → `"vibey.run.request/1: RunRequest.cwd must be absolute"`; `"args":
  ["run", 5]` → `"'args' must be a list of strings"`; `"supersedes": "job"` → `"'supersedes' must
  be an object"`; `"candidates": {}` → `"'candidates' must be a list"`; `"candidates": [1]` →
  `r"candidates\[0\] must be an object"`; `"loop_id": "thirdloop"` → `"'loop_id' has no member
  'thirdloop'"`; `"capture_output": 1` → `"'capture_output' must be true or false"`; a
  `RunAccepted` with `"queued_seconds": "1"` → `"'queued_seconds' must be a number"`.
- `test_from_bytes_refuses_non_messages`: `b"\xff"`, `b"{"`, `b"[]"` and `b"null"` raise
  `MalformedRunMessage`; the bytes of an accepted message with `"queued_seconds":NaN` raise
  matching `"must be a finite number"`.
- `test_to_bytes_is_canonical`: `RUN_CODEC.to_bytes(result).startswith(b'{"cached_at":null,"detail":""')`
  for the example (with `detail=""` and `cached_at=None`), and it contains no `b": "` or `b", "`.
- `test_malformed_run_message_is_a_vibey_error`: `issubclass(MalformedRunMessage, VibeyError)`.
- `test_the_codec_satisfies_its_interface`: `isinstance(RUN_CODEC, RunProtocolCodecInterface)` and
  `isinstance(RunProtocolCodec(), RunProtocolCodecInterface)`.

## Checks the lane must run (all must pass)
At `d3b4a388` the root `tests/conftest.py:146-151` creates a per-worker PostgreSQL database in
`pytest_configure`, so every pytest command below needs a reachable PostgreSQL
(`VIBEY_TEST_DATABASE_URL`) until lane `fakes-harness-decouple` lands.

    uv run ruff format src/vibey/domain/errors.py src/vibey/domain/run_codec.py src/vibey/domain/interfaces/run_codec_interface.py tests/domain/test_run_codec.py
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_run_codec.py tests/domain/test_run_protocol.py tests/domain/test_errors.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- The message classes and queue names (lane `loops-run-protocol-messages`); do not edit
  `run_protocol.py`.
- The argument policy (lane `loops-run-args-policy`).
- AMQP publishing, message ids and reply routing (the loop-service lanes).
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-run-protocol-messages`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
