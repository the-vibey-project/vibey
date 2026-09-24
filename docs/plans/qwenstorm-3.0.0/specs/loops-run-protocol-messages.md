## Title
feat(domain): the two-loop run protocol's messages and queue names

ADR-0046 lane L04a (slug `loops-run-protocol-messages`).

## Why
- **The law.** Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-234`) says both
  rotation layers run on the bus, "with dead-letter queues and idempotency". The outer layer goes
  from vibey to a loop, and the inner from a loop to its adapters. Non-negotiables 2 and 3
  (CLAUDE.md) forbid a capacity field and a completion claim on anything that crosses a process
  boundary.
- **The decision.** ADR-0046 §3 (`specs/ADR-two-loops.md:140-191`):
  - the queue and exchange table (`:144-152`): `vibey.runs`, `vibey.runs.<loop>`,
    `vibey.runs.<loop>.<seat>`, `vibey.runs.<loop>.probe`, `vibey.runs.dlx`, the dead queues and
    `vibey.runs.control`, all under `[bus] prefix` (`:142`);
  - seat names (`:154-155`);
  - the seven schemas (`:158-167`), with `RunStatus.UNROUTABLE`, the `SUPERSEDE` control command,
    and "pure dataclasses with a strict codec".
  - §10 (`:302`) puts `run_protocol.py` in `domain/`, replacing R19.
  - The design sheet splits the codec (lane `loops-run-codec`) and the argument policy (lane
    `loops-run-args-policy`) into sibling modules (decision D14).
- **What carries over from R19** (`specs/rmq-r19-run-protocol.md`, closed as superseded in
  `issue-audit/updates/366.md`): frozen, slotted, timezone-aware dataclasses; a `RunResult` with no
  completion, success or capacity field; `RunSupersede`; and the purposes and statuses. R19's
  per-engine wire (`vibey.runs.<engine_id>`, ADR-0044 §13) is replaced by the loop-keyed one.
- **The gap, at integration `d3b4a388`.** No run protocol exists in `src/vibey/domain/` (R19 was
  never merged). Every loop-service lane (router, seat host, client, adapter) builds on these
  messages.
- **9.b** (`doctrines.md:349`): every class gets an interface beside it.

## Required behaviour
1. **`src/vibey/domain/run_protocol.py`** (new). Its module docstring cites ADR-0046 §3 and says:
   no message carries a completion claim or a capacity field; every datetime is timezone-aware;
   the module has no clock, I/O or async.
2. **Schema constants** (`Final`, exact text): `SCHEMA_ROUTE = "vibey.run.route/1"`,
   `SCHEMA_ROUTED = "vibey.run.routed/1"`, `SCHEMA_REQUEST = "vibey.run.request/1"`,
   `SCHEMA_ACCEPTED = "vibey.run.accepted/1"`, `SCHEMA_PROGRESS = "vibey.run.progress/1"`,
   `SCHEMA_RESULT = "vibey.run.result/1"` and `SCHEMA_CONTROL = "vibey.run.control/1"`.
3. **Enums** (`StrEnum`):

   | enum | members = values |
   |---|---|
   | `RunPurpose` | `RUN = "run"`, `PROBE = "probe"` |
   | `RunStatus` | `EXITED = "exited"`, `SUPERSEDED = "superseded"`, `ABANDONED = "abandoned"`, `REJECTED = "rejected"`, `DEAD_LETTERED = "dead_lettered"`, `DEADLINE_EXCEEDED = "deadline_exceeded"`, `UNROUTABLE = "unroutable"` |
   | `RouteStatus` | `ROUTED = "routed"`, `UNROUTABLE = "unroutable"`, `DEAD_LETTERED = "dead_lettered"` |
   | `RunControlCommand` | `STOP = "stop"`, `WIND_DOWN = "wind_down"`, `PROMPT_NOW = "prompt-now"`, `PROMPT_AT_BREAK = "prompt-at-break"`, `SUPERSEDE = "supersede"` |

4. **Messages.** Each is `@dataclass(frozen=True, slots=True)` with exactly these fields, in this
   order and with no defaults. `__post_init__` raises `ValueError` with exactly the message given.
   `aware` means `value.utcoffset() is not None`, else `"<Class>.<field> must be timezone-aware"`.

   | class | fields | `__post_init__` checks (message) |
   |---|---|---|
   | `RunSupersede` | `key: str`, `attempt: int` | `key` empty → `"RunSupersede.key must not be empty"`; `attempt < 0` → `f"RunSupersede.attempt must be at least 0, got {attempt}"` |
   | `RouteCandidate` | `engine_id: str`, `weight: int` | empty → `"RouteCandidate.engine_id must not be empty"`; `weight < 0` → `f"RouteCandidate.weight must be at least 0, got {weight}"` |
   | `RouteRequest` | `route_id: UUID`, `loop_id: LoopId`, `project_id: UUID \| None`, `candidates: tuple[RouteCandidate, ...]`, `pin: str \| None`, `model_pin: str \| None`, `min_context: int \| None`, `requested_at: datetime`, `caller: str` | a repeated `engine_id` among `candidates` → `f"RouteRequest.candidates repeats engine {engine_id}"`; `min_context < 1` → `f"RouteRequest.min_context must be at least 1, got {min_context}"`; `requested_at` aware; `caller` empty → `"RouteRequest.caller must not be empty"` |
   | `RunRouted` | `route_id: UUID`, `loop_id: LoopId`, `status: RouteStatus`, `engine_id: str \| None`, `seat: str \| None`, `model: str \| None`, `switched: bool`, `reason: str`, `routed_at: datetime`, `route_ms: float`, `seat_depth: int \| None`, `seat_oldest_wait_seconds: float \| None` | `(engine_id is not None and seat is not None) != (status is RouteStatus.ROUTED)` → `"RunRouted.engine_id and RunRouted.seat are both set exactly when status is routed (status=…, engine_id=…, seat=…)"` (the snippet below); `routed_at` aware; `route_ms < 0` → `f"RunRouted.route_ms must be at least 0, got {route_ms}"` |
   | `RunRequest` | `run_id: UUID`, `loop_id: LoopId`, `engine_id: str`, `route_id: UUID \| None`, `model_pin: str \| None`, `purpose: RunPurpose`, `args: tuple[str, ...]`, `cwd: str`, `run_dir: str \| None`, `supersedes: RunSupersede \| None`, `deadline_seconds: int`, `start_by: datetime`, `capture_output: bool`, `requested_at: datetime`, `caller: str` | `cwd` not starting with `"/"` → `f"RunRequest.cwd must be absolute, got {cwd!r}"`; `deadline_seconds < 1` → `f"RunRequest.deadline_seconds must be at least 1, got {deadline_seconds}"`; `start_by` and `requested_at` aware |
   | `RunAccepted` | `run_id: UUID`, `loop_id: LoopId`, `engine_id: str`, `seat: str`, `model: str \| None`, `instance: str`, `pid: int \| None`, `started_at: datetime`, `queued_seconds: float` | `started_at` aware; `queued_seconds < 0` → `f"RunAccepted.queued_seconds must be at least 0, got {queued_seconds}"` |
   | `RunProgress` | `run_id: UUID`, `seq: int`, `line: str` | `seq < 1` → `f"RunProgress.seq must be at least 1, got {seq}"` |
   | `RunResult` | `run_id: UUID`, `status: RunStatus`, `exit_code: int \| None`, `meta_status: str \| None`, `started_at: datetime \| None`, `finished_at: datetime`, `detail: str`, `stdout: str \| None`, `stderr: str \| None`, `cached_at: datetime \| None` | `started_at`, `finished_at` and `cached_at` aware when not None |
   | `RunControl` | `run_id: UUID \| None`, `command: RunControlCommand`, `text: str \| None`, `supersedes: RunSupersede \| None` | see the snippet below |

   `RunResult` has **no** completion, success or capacity field (non-negotiable 3). No class has
   a field named `resets_at`, `capacity`, `capacity_state`, `credits`, `complete` or `success`
   (non-negotiable 2).

   Two of the checks, verbatim:
   ```python
   @dataclass(frozen=True, slots=True)
   class RunRouted:
       ...  # the twelve fields above

       def __post_init__(self) -> None:
           named = self.engine_id is not None and self.seat is not None
           if named != (self.status is RouteStatus.ROUTED):
               raise ValueError(
                   "RunRouted.engine_id and RunRouted.seat are both set exactly when status is "
                   f"routed (status={self.status}, engine_id={self.engine_id!r}, seat={self.seat!r})"
               )
           if self.routed_at.utcoffset() is None:
               raise ValueError("RunRouted.routed_at must be timezone-aware")
           if self.route_ms < 0:
               raise ValueError(f"RunRouted.route_ms must be at least 0, got {self.route_ms}")


   @dataclass(frozen=True, slots=True)
   class RunControl:
       run_id: UUID | None
       command: RunControlCommand
       text: str | None
       supersedes: RunSupersede | None

       def __post_init__(self) -> None:
           if self.command is RunControlCommand.SUPERSEDE:
               if self.supersedes is None or self.run_id is not None:
                   raise ValueError(
                       "RunControl.supersedes is required and RunControl.run_id must be None "
                       "for supersede"
                   )
               return
           if self.run_id is None or self.supersedes is not None:
               raise ValueError(
                   "RunControl.run_id is required and RunControl.supersedes must be None "
                   f"for {self.command}"
               )
           prompts = (RunControlCommand.PROMPT_NOW, RunControlCommand.PROMPT_AT_BREAK)
           if self.command in prompts and not self.text:
               raise ValueError(f"RunControl.text must not be empty for {self.command}")
   ```
   For `RouteRequest`, find the first repeat with a `seen: set[str]` loop over `candidates`. For
   several aware checks in one class, loop over `(name, value)` pairs as
   `src/vibey/domain/ledger_query.py:196-198` does.
5. **The union**, after the classes:
   ```python
   type RunMessage = (
       RouteRequest | RunRouted | RunRequest | RunAccepted | RunProgress | RunResult | RunControl
   )
   ```
6. **`class RunQueueNames`** (ADR-0046 §3 table; `loop` renders as its value, because a
   `StrEnum` formats as its value):
   ```python
   _SEAT: Final = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)?$")


   class RunQueueNames:
       def __init__(self, prefix: str = "vibey") -> None:
           self._prefix = prefix

       @property
       def prefix(self) -> str:
           return self._prefix

       def runs_exchange(self) -> str:
           return f"{self._prefix}.runs"

       def dead_exchange(self) -> str:
           return f"{self._prefix}.runs.dlx"

       def control_exchange(self) -> str:
           return f"{self._prefix}.runs.control"

       def intake_queue(self, loop: LoopId) -> str:
           return f"{self._prefix}.runs.{loop}"

       def intake_key(self, loop: LoopId) -> str:
           return str(loop)

       def seat_queue(self, loop: LoopId, seat: str) -> str:
           return f"{self._prefix}.runs.{loop}.{self._seat(seat)}"

       def seat_key(self, loop: LoopId, seat: str) -> str:
           return f"{loop}.{self._seat(seat)}"

       def probe_queue(self, loop: LoopId) -> str:
           return f"{self._prefix}.runs.{loop}.probe"

       def probe_key(self, loop: LoopId) -> str:
           return f"{loop}.probe"

       def intake_dead_queue(self, loop: LoopId) -> str:
           return f"{self._prefix}.runs.{loop}.dead"

       def seat_dead_queue(self, loop: LoopId, seat: str) -> str:
           return f"{self._prefix}.runs.{loop}.{self._seat(seat)}.dead"

       def control_keys(self, loop: LoopId) -> tuple[str, str]:
           return (str(loop), "all")

       def queue_arguments(
           self, *, dead_key: str, delivery_limit: int, consumer_timeout_seconds: int
       ) -> dict[str, object]:
           return {
               "x-queue-type": "quorum",
               "x-delivery-limit": delivery_limit,
               "x-dead-letter-exchange": self.dead_exchange(),
               "x-dead-letter-routing-key": dead_key,
               "x-dead-letter-strategy": "at-least-once",
               "x-overflow": "reject-publish",
               "x-consumer-timeout": consumer_timeout_seconds * 1000,
           }

       @staticmethod
       def _seat(seat: str) -> str:
           if not _SEAT.fullmatch(seat):
               raise ValueError(
                   f"seat {seat!r} is not a seat name: lower-case letters, digits and '-', "
                   "with at most one '.'"
               )
           if seat in RESERVED_SEATS:
               raise ValueError(f"seat {seat!r} is reserved")
           return seat
   ```
   `RESERVED_SEATS` is imported from `vibey.domain.residency` (lane `loops-residency-policy`), so
   there is one reserved list, not two.
7. **`src/vibey/domain/interfaces/run_protocol_interface.py`** (new). It starts with
   `from __future__ import annotations`, and it imports `UUID`, `datetime`, `LoopId` and the four
   enums (and `RunSupersede`, `RouteCandidate`) only under `if TYPE_CHECKING:`. It declares one
   `@runtime_checkable` Protocol per class:
   - `RunQueueNamesInterface`: the `prefix` property and every public method of `RunQueueNames`,
     with the same signatures;
   - one Protocol per message: `RunSupersedeInterface`, `RouteCandidateInterface`,
     `RouteRequestInterface`, `RunRoutedInterface`, `RunRequestInterface`,
     `RunAcceptedInterface`, `RunProgressInterface`, `RunResultInterface` and
     `RunControlInterface`. Each has one read-only `@property` per dataclass field, with the same
     name and type. For example:
     ```python
     @runtime_checkable
     class RunProgressInterface(Protocol):
         @property
         def run_id(self) -> UUID: ...

         @property
         def seq(self) -> int: ...

         @property
         def line(self) -> str: ...
     ```
   A frozen dataclass satisfies such a Protocol under `mypy --strict` (checked on a scratch copy).
   The enums need no new interface: a member satisfies the existing `StringValueInterface`
   (`src/vibey/domain/interfaces/value_objects_interface.py:20-22`).
8. **Shared instance:** `RUN_QUEUE_NAMES: Final[RunQueueNamesInterface] = RunQueueNames()`, with
   the docstring "The default names (`[bus] prefix` = `vibey`). Annotated with the interface so
   `mypy --strict` checks the class against its seam." The pattern is
   `src/vibey/domain/ledger_record.py:157-159`.
9. The module is pure: `re`, `uuid`, `datetime` (the type only) and `dataclasses` are stdlib, and
   nothing calls a clock. `tests/domain/test_domain_purity.py` walks it.

## Where to change
- New: `src/vibey/domain/run_protocol.py`, `src/vibey/domain/interfaces/run_protocol_interface.py`,
  `tests/domain/test_run_protocol.py`.
- Line 1 of each new file is the provenance comment, copied byte for byte from line 1 of
  `src/vibey/domain/engine.py`.
- Imports in `run_protocol.py`: `re`; `dataclass`; `datetime` from `datetime`; `StrEnum`; `Final`;
  `UUID`; `LoopId` from `vibey.domain.loop`; `RESERVED_SEATS` from `vibey.domain.residency`;
  `RunQueueNamesInterface` from the new interface module.
- No fake is registered: these are pure values.
- If `vibey.domain.loop` or `vibey.domain.residency` does not exist, stop and report which
  dependency has not landed.

## Acceptance criteria
- [ ] The seven schema strings and all enum values are exactly as listed (`test_schema_constants`,
      `test_enum_values`).
- [ ] Every validation in behaviour 4 has a test that matches its message.
- [ ] No message class has a field in `{"resets_at", "capacity", "capacity_state", "credits",
      "complete", "success"}` (`test_no_message_carries_a_capacity_or_completion_field`).
- [ ] `RunQueueNames()` gives exactly the names in `test_queue_names`, and `RunQueueNames("acme")`
      gives the same names with `acme` in place of `vibey`.
- [ ] `tests/domain/test_domain_purity.py` passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_run_protocol.py` (pure objects only). Define one module-level factory per
message that returns a valid instance, e.g. `_route()`, `_routed()`, `_request()`, `_accepted()`,
`_progress()`, `_result()`, `_control()`. Use `datetime(2026, 9, 22, 10, 0, tzinfo=UTC)` and
`UUID(int=1)`, and change fields with `dataclasses.replace`.
- `test_schema_constants`: the seven exact strings.
- `test_enum_values`: `[s.value for s in RunStatus] == ["exited", "superseded", "abandoned",
  "rejected", "dead_lettered", "deadline_exceeded", "unroutable"]`, and the same for `RouteStatus`,
  `RunControlCommand` and `RunPurpose`.
- `test_valid_messages_construct`: every factory returns an instance of its class.
- `test_naive_datetimes_are_refused` (parametrized over `(factory, field)`: `(_route,
  "requested_at")`, `(_routed, "routed_at")`, `(_request, "start_by")`, `(_request,
  "requested_at")`, `(_accepted, "started_at")`, `(_result, "finished_at")`, `(_result,
  "started_at")`, `(_result, "cached_at")`): `replace(factory(), **{field: datetime(2026, 9, 22)})`
  raises `ValueError` matching `f"{field} must be timezone-aware"`.
- `test_lower_bounds_are_enforced` (parametrized): `RunSupersede("k", -1)`,
  `RouteCandidate("claudeloop", -1)`, `replace(_route(), min_context=0)`,
  `replace(_request(), deadline_seconds=0)`, `replace(_accepted(), queued_seconds=-0.5)`,
  `replace(_progress(), seq=0)` and `replace(_routed(), route_ms=-1.0)`. Each raises `ValueError`
  matching `"must be at least"`.
- `test_empty_texts_are_refused`: `RunSupersede("", 0)`, `RouteCandidate("", 1)` and
  `replace(_route(), caller="")` raise `ValueError` matching `"must not be empty"`.
- `test_route_request_candidates_are_unique`: two candidates for `"claudeloop"` raise with
  `"RouteRequest.candidates repeats engine claudeloop"`.
- `test_run_request_cwd_must_be_absolute`: `replace(_request(), cwd="work/repo")` raises with
  `"RunRequest.cwd must be absolute, got 'work/repo'"`.
- `test_run_routed_names_engine_and_seat_exactly_when_routed`: routed with both set constructs;
  routed with `seat=None` raises; `UNROUTABLE` with `engine_id="claudeloop"` and
  `seat="claudeloop"` raises; `UNROUTABLE` with both None constructs; `DEAD_LETTERED` with
  `engine_id=None` and `seat="x"` constructs.
- `test_run_control_rules`: `RunControl(None, SUPERSEDE, None, RunSupersede("job", 2))` constructs;
  `RunControl(UUID(int=1), SUPERSEDE, None, RunSupersede("job", 2))` raises;
  `RunControl(None, SUPERSEDE, None, None)` raises; `RunControl(UUID(int=1), STOP, None, None)`
  constructs; `RunControl(None, STOP, None, None)` raises;
  `RunControl(UUID(int=1), WIND_DOWN, None, RunSupersede("job", 2))` raises;
  `RunControl(UUID(int=1), PROMPT_NOW, "", None)` raises with
  `"RunControl.text must not be empty for prompt-now"`; `RunControl(UUID(int=1), PROMPT_AT_BREAK,
  "hi", None)` constructs.
- `test_no_message_carries_a_capacity_or_completion_field`: for each of the nine classes,
  `{f.name for f in dataclasses.fields(cls)}` has no name from the forbidden set; and
  `{f.name for f in fields(RunResult)} == {"run_id", "status", "exit_code", "meta_status",
  "started_at", "finished_at", "detail", "stdout", "stderr", "cached_at"}`.
- `test_messages_are_frozen`: assigning `_result().detail = "x"` raises
  `dataclasses.FrozenInstanceError`.
- `test_queue_names`: for `names = RunQueueNames()` and `loop = LoopId.SOVEREIGNLOOP`:
  `runs_exchange() == "vibey.runs"`, `dead_exchange() == "vibey.runs.dlx"`,
  `control_exchange() == "vibey.runs.control"`, `intake_queue(loop) == "vibey.runs.sovereignloop"`,
  `intake_key(loop) == "sovereignloop"`, `seat_queue(loop, "gpt-oss-20b") ==
  "vibey.runs.sovereignloop.gpt-oss-20b"`, `seat_key(loop, "gpt-oss-20b") ==
  "sovereignloop.gpt-oss-20b"`, `probe_queue(loop) == "vibey.runs.sovereignloop.probe"`,
  `probe_key(loop) == "sovereignloop.probe"`, `intake_dead_queue(loop) ==
  "vibey.runs.sovereignloop.dead"`, `seat_dead_queue(LoopId.PAIDLOOP, "claudeloop") ==
  "vibey.runs.paidloop.claudeloop.dead"`, `control_keys(LoopId.PAIDLOOP) == ("paidloop", "all")`,
  and `RunQueueNames("acme").intake_queue(loop) == "acme.runs.sovereignloop"`.
- `test_seat_names_are_validated`: `"claudeloop"`, `"gpt-oss-20b"` and `"vscode-paid.gpt-5-mini"`
  are accepted by `seat_key`; `"gpt-oss:20b"`, `"a.b.c"`, `"Upper"` and `""` raise with
  `"is not a seat name"`; `"probe"` and `"dead"` raise with `"is reserved"`.
- `test_queue_arguments_are_the_quorum_set`: `queue_arguments(dead_key="paidloop.claudeloop",
  delivery_limit=3, consumer_timeout_seconds=21600)` equals the exact dict in behaviour 6, with
  `"x-consumer-timeout": 21600000`.
- `test_classes_satisfy_their_interfaces`: `RUN_QUEUE_NAMES` against `RunQueueNamesInterface`,
  every factory's instance against its Protocol, `RunSupersede("k", 0)` and
  `RouteCandidate("claudeloop", 1)` against theirs, and `RunStatus.EXITED` against
  `StringValueInterface`.

## Checks the lane must run (all must pass)
At `d3b4a388` the root `tests/conftest.py:146-151` creates a per-worker PostgreSQL database in
`pytest_configure`, so every pytest command below needs a reachable PostgreSQL
(`VIBEY_TEST_DATABASE_URL`) until lane `fakes-harness-decouple` lands.

    uv run ruff format src/vibey/domain/run_protocol.py src/vibey/domain/interfaces/run_protocol_interface.py tests/domain/test_run_protocol.py
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_run_protocol.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- The codec and `MalformedRunMessage` (lane `loops-run-codec`).
- The argument policy (lane `loops-run-args-policy`).
- Any broker, process or file code: the loop-service lanes.
- The `[bus] prefix` configuration key (lane `rmq-r01-queue-config`). The caller passes `prefix`.
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-domain-loop-id`, `loops-residency-policy`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
