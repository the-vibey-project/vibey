## Title
feat(domain): the loop's ledger vocabulary — LoopRouted, PaidFallbackDeclared, and every loop measurement's shape

ADR-0046 lane L50 (slug `loops-ledger-kinds`).

## Why
- **The law.** 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) makes the ledger record as much
  as possible, append-only. 8.a (`:99-112`) requires a paid fallback to be "declared loudly to a
  human". 8.g (`:316-324`) says every loop, lane, queue, surface, test run and model records
  latency, throughput, depth and outcome, and optimizes from that evidence. Non-negotiable 2
  (CLAUDE.md): `CreditsExhausted` never acquires a `resets_at`; no payload that crosses a process
  boundary or lands in a durable record may carry a capacity time.
- **The decision.** ADR-0046 §2 (`specs/ADR-two-loops.md:125-127`): "Whenever the choice is
  paidloop, vibey writes a `PaidFallbackDeclared` ledger event. It names every sovereign adapter
  in the pool and why that adapter could not take the job … The event is written in both
  invocation modes." §3, "Flow for a BUILD job" (`:173`): "It records the selection, assigns the
  routed engine to the job, and writes `LoopRouted`." §10 (`:302`) places both in `domain/ledger.py`
  (the `EventKind` additions) and `domain/loop_events.py` (the record shapes), beside `LoopId`.
  The possible paid-fallback reasons are named at §2 (`:125`): "no health row, not installed,
  conformance failed, authentication stale, circuit open (with its capacity state), excluded by
  the job, missing capability, or unroutable (§4)." Design-sheet decision D8 adds one more:
  `NO_WEIGHT`, for a sovereign candidate that is eligible but whose effective weight rounded to 0
  (ADR-0005's SWRR), so that "eligible but never selected" is distinguishable from every excluding
  rule. D9 puts every loop's own timing evidence (a route, a run, a rejection, a residency switch)
  into one measurement shape the loop-service lanes share, so 8.g has a single sink instead of one
  ad hoc log line per lane.
- **The gap, at integration `d3b4a388`.** No `domain/loop_events.py` exists, and `domain/ledger.py`'s
  `EventKind` has no `LOOP_ROUTED` or `PAID_FALLBACK_DECLARED` member. Sibling specs already call
  the types this lane must produce: `loops-selecting-loop-provider` builds
  `LoopRoutedRecord(route_id=..., loop_id=..., engine_id=..., seat=..., model=..., switched=...,
  reason=..., route_ms=..., seat_depth=..., seat_oldest_wait_seconds=...).to_payload()` and
  `PaidFallbackDeclaration(engine_id=..., invocation=..., sovereign=...).to_payload()`;
  `loops-weighted-candidates` and `loops-loop-selector` build `AdapterExclusion(<id>,
  ExclusionReason.<X>, capacity_state=..., detail=...)`; `loops-result-store`,
  `loops-resident-schedule` and `loops-router-routing` build `LoopMeasurement(loop_id=...,
  subject=MeasurementSubject.<X>, at=..., seat=..., engine_id=..., model=..., latency_ms=...,
  waited_seconds=..., queue_depth=..., outcome=...)` and call `.to_record()` on it. This lane is
  the one place all of those names are declared, so every consumer agrees on the same shape.
- **9.b** (`doctrines.md:349`): every class gets an interface beside it.

## Required behaviour
1. **`src/vibey/domain/loop_events.py`** (new). Module docstring: cites ADR-0046 §2, §3, §10 and
   8.g; says every payload here is JSON-safe and carries no clock-derived deadline (non-negotiable
   2), and that the module is pure (no I/O, no clock — every `at` and `latency_ms` value is
   supplied by the caller).
2. **`class ExclusionReason(StrEnum)`**, nine members, in this exact order (the order ADR-0046 §2
   lists eight of them, then D8's `NO_WEIGHT` last):
   ```python
   class ExclusionReason(StrEnum):
       NO_HEALTH_ROW = "no_health_row"
       NOT_INSTALLED = "not_installed"
       CONFORMANCE_FAILED = "conformance_failed"
       AUTHENTICATION_STALE = "authentication_stale"
       CIRCUIT_OPEN = "circuit_open"
       EXCLUDED_BY_JOB = "excluded_by_job"
       MISSING_CAPABILITY = "missing_capability"
       UNROUTABLE = "unroutable"
       NO_WEIGHT = "no_weight"
   ```
3. **`@dataclass(frozen=True, slots=True) class AdapterExclusion`**, fields in this order, all
   with defaults on the last two so a caller need only ever name what it knows:
   ```python
   @dataclass(frozen=True, slots=True)
   class AdapterExclusion:
       """Why one adapter of the pool could not take a job (ADR-0046 §2). ``capacity_state``
       names a capacity type by its class name only (non-negotiable 2: never a time or a
       credit count), and is set only for ``CIRCUIT_OPEN``."""

       engine_id: str
       reason: ExclusionReason
       capacity_state: str | None = None
       detail: str = ""

       def to_payload(self) -> dict[str, object]:
           return {
               "engine_id": self.engine_id,
               "reason": self.reason.value,
               "capacity_state": self.capacity_state,
               "detail": self.detail,
           }
   ```
   `AdapterExclusion("claudeloop", ExclusionReason.NO_HEALTH_ROW)` must construct with
   `capacity_state is None` and `detail == ""`.
4. **`@dataclass(frozen=True, slots=True) class PaidFallbackDeclaration`**:
   ```python
   @dataclass(frozen=True, slots=True)
   class PaidFallbackDeclaration:
       """What a paid selection declares (ADR-0046 §2, sub-doctrine 8.a): the paid engine
       chosen, how it was invoked, and every sovereign adapter the pool held with the reason
       each could not take the job. ``loop_id`` and ``rule`` are fixed: this record only ever
       fires when the loop is paidloop, and the rule it enforces never changes."""

       engine_id: str
       invocation: str
       sovereign: tuple[AdapterExclusion, ...]
       loop_id: str = "paidloop"
       rule: str = "sub-doctrine 8.a"

       def __post_init__(self) -> None:
           if self.invocation not in {"subprocess", "service"}:
               raise ValueError(
                   f"PaidFallbackDeclaration.invocation must be 'subprocess' or 'service', "
                   f"got {self.invocation!r}"
               )

       def to_payload(self) -> dict[str, object]:
           return {
               "loop_id": self.loop_id,
               "engine_id": self.engine_id,
               "invocation": self.invocation,
               "sovereign_adapters": [exclusion.to_payload() for exclusion in self.sovereign],
               "rule": self.rule,
           }
   ```
5. **`@dataclass(frozen=True, slots=True) class LoopRoutedRecord`**:
   ```python
   @dataclass(frozen=True, slots=True)
   class LoopRoutedRecord:
       """What a route decision writes to the ledger (ADR-0046 §3): the route's measurements
       travel with it (decision D9), so the ledger and the loop's own measurement log agree on
       one set of numbers for the same route."""

       route_id: UUID
       loop_id: LoopId
       engine_id: str
       seat: str
       model: str | None
       switched: bool
       reason: str
       route_ms: float
       seat_depth: int | None
       seat_oldest_wait_seconds: float | None

       def to_payload(self) -> dict[str, object]:
           return {
               "route_id": str(self.route_id),
               "loop_id": self.loop_id.value,
               "engine_id": self.engine_id,
               "seat": self.seat,
               "model": self.model,
               "switched": self.switched,
               "reason": self.reason,
               "route_ms": self.route_ms,
               "seat_depth": self.seat_depth,
               "seat_oldest_wait_seconds": self.seat_oldest_wait_seconds,
           }
   ```
6. **`class MeasurementSubject(StrEnum)`**, six members, one per kind of thing 8.g asks a loop to
   measure about itself:
   ```python
   class MeasurementSubject(StrEnum):
       ROUTE = "route"
       RUN = "run"
       REJECT = "reject"
       SWITCH = "switch"
       PROBE = "probe"
       DEAD_LETTER = "dead_letter"
   ```
7. **`@dataclass(frozen=True, slots=True) class LoopMeasurement`**:
   ```python
   @dataclass(frozen=True, slots=True)
   class LoopMeasurement:
       """One measured fact about a loop (8.g): every loop-service lane records into this one
       shape, appended to the loop's own ``measurements.jsonl`` (lane loops-result-store) and
       logged as ``loop_measured``. ``at`` is supplied by the caller's clock: this module never
       reads one. Every optional field defaults to ``None`` (or ``""`` for ``outcome``) so a
       caller states only what it measured -- a REJECT has no ``latency_ms``, a SWITCH has no
       ``engine_id``."""

       loop_id: LoopId
       subject: MeasurementSubject
       at: datetime
       seat: str | None
       engine_id: str | None
       model: str | None
       latency_ms: float | None = None
       waited_seconds: float | None = None
       queue_depth: int | None = None
       outcome: str = ""

       def __post_init__(self) -> None:
           if self.at.utcoffset() is None:
               raise ValueError("LoopMeasurement.at must be timezone-aware")

       def to_record(self) -> dict[str, object]:
           return {
               "loop_id": self.loop_id.value,
               "subject": self.subject.value,
               "at": self.at.isoformat(),
               "seat": self.seat,
               "engine_id": self.engine_id,
               "model": self.model,
               "latency_ms": self.latency_ms,
               "waited_seconds": self.waited_seconds,
               "queue_depth": self.queue_depth,
               "outcome": self.outcome,
           }
   ```
8. **`domain/ledger.py`**: `class EventKind(StrEnum)` gains two members at the end of its member
   list, in this order: `LOOP_ROUTED = "loop_routed"` and
   `PAID_FALLBACK_DECLARED = "paid_fallback_declared"`. Copy the exact indentation and blank-line
   style of the member immediately above them; add no comment the surrounding members do not
   already have a matching style for.
9. **`src/vibey/domain/interfaces/loop_events_interface.py`** (new): one `@runtime_checkable`
   Protocol per record class (`AdapterExclusionInterface`, `PaidFallbackDeclarationInterface`,
   `LoopRoutedRecordInterface`, `LoopMeasurementInterface`), each with one read-only `@property`
   per dataclass field (same name, same type) plus the class's own `to_payload`/`to_record`
   method. It starts with `from __future__ import annotations`, and imports `LoopId`, `UUID` and
   `datetime` only under `if TYPE_CHECKING:`, following the layout of
   `src/vibey/domain/interfaces/ledger_query_interface.py:1-21`. `ExclusionReason` and
   `MeasurementSubject` need no new interface: a member satisfies the existing
   `StringValueInterface` (`src/vibey/domain/interfaces/value_objects_interface.py:20-22`).
10. The module is pure: `dataclasses`, `datetime`, `enum`, `uuid` are stdlib; `LoopId` comes from
    `vibey.domain.loop` (also pure). `tests/domain/test_domain_purity.py` walks it.

## Where to change
- New: `src/vibey/domain/loop_events.py`, `src/vibey/domain/interfaces/loop_events_interface.py`,
  `tests/domain/test_loop_events.py`. Line 1 of each new file is the provenance comment, copied
  byte for byte from line 1 of `src/vibey/domain/engine.py`.
- `src/vibey/domain/ledger.py` (`edit_file` only; it is well over 100 lines): first
  `grep -n "class EventKind" src/vibey/domain/ledger.py` to find it, then `read_file` the enum's
  full member list and `edit_file` with `old_string` equal to its last member line (copied
  exactly, including trailing whitespace) and `new_string` equal to that same line followed by
  the two new members. **Stop and report** if no `class EventKind(StrEnum)` (or `class
  EventKind(str, Enum)`) exists in that file: this lane cannot invent the ledger's whole event
  vocabulary.
- Do not edit `src/vibey/domain/interfaces/__init__.py`; the new interface module is imported by
  its own path, following `loops-domain-loop-id`'s pattern for `loop_interface.py`.
- No fake is registered: every type here is a pure value, used directly in tests.

## Acceptance criteria
- [ ] `EventKind.LOOP_ROUTED.value == "loop_routed"` and
      `EventKind.PAID_FALLBACK_DECLARED.value == "paid_fallback_declared"`; every existing
      `EventKind` member keeps its value (`test_no_existing_event_kind_changed_value`, built from
      a `git show HEAD:src/vibey/domain/ledger.py` diff of just the two new lines).
- [ ] `AdapterExclusion`, `PaidFallbackDeclaration`, `LoopRoutedRecord` and `LoopMeasurement` each
      round-trip through `json.dumps(x.to_payload())` / `json.dumps(x.to_record())` with no
      `TypeError` (every field is a JSON-safe type once converted).
- [ ] No dataclass field anywhere in this module is named `resets_at`, `capacity`,
      `capacity_state` holding a time, `credits`, `complete` or `success`
      (`test_no_record_carries_a_capacity_time_or_completion_field`).
- [ ] `tests/domain/test_domain_purity.py` passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_loop_events.py` (pure objects only). Use `NOW = datetime(2026, 9, 22, 12, 0,
tzinfo=UTC)` and `ROUTE_ID = UUID(int=1)`.
- `test_exclusion_reasons_are_exactly_the_nine_in_order`: `[r.value for r in ExclusionReason] ==
  ["no_health_row", "not_installed", "conformance_failed", "authentication_stale", "circuit_open",
  "excluded_by_job", "missing_capability", "unroutable", "no_weight"]`.
- `test_an_adapter_exclusion_defaults_capacity_state_and_detail`:
  `AdapterExclusion("claudeloop", ExclusionReason.NO_HEALTH_ROW).to_payload() ==
  {"engine_id": "claudeloop", "reason": "no_health_row", "capacity_state": None, "detail": ""}`.
- `test_an_adapter_exclusion_carries_capacity_state_and_detail`:
  `AdapterExclusion("sovereignloop", ExclusionReason.CIRCUIT_OPEN, capacity_state="WindowExhausted",
  detail="unrecognized circuit state tripped").to_payload()["capacity_state"] ==
  "WindowExhausted"`.
- `test_a_paid_fallback_declaration_names_the_fixed_loop_and_rule`: with one exclusion,
  `.to_payload() == {"loop_id": "paidloop", "engine_id": "claudeloop", "invocation": "subprocess",
  "sovereign_adapters": [{"engine_id": "sovereignloop", "reason": "circuit_open",
  "capacity_state": "WindowExhausted", "detail": ""}], "rule": "sub-doctrine 8.a"}` for
  `PaidFallbackDeclaration(engine_id="claudeloop", invocation="subprocess",
  sovereign=(AdapterExclusion("sovereignloop", ExclusionReason.CIRCUIT_OPEN,
  capacity_state="WindowExhausted"),))`.
- `test_a_paid_only_pool_declares_an_empty_sovereign_list`:
  `PaidFallbackDeclaration("claudeloop", "service", ()).to_payload()["sovereign_adapters"] == []`.
- `test_an_invalid_invocation_is_refused`: `PaidFallbackDeclaration("claudeloop", "batch", ())`
  raises `ValueError` matching `"invocation must be 'subprocess' or 'service'"`.
- `test_a_loop_routed_record_matches_the_route`: build one with every field set and confirm
  `.to_payload()` renders `route_id` as `str(ROUTE_ID)`, `loop_id` as `"sovereignloop"`, and every
  other field verbatim, including `model=None` and `seat_depth=None` staying `None`.
- `test_measurement_subjects_are_exactly_the_six`: `[s.value for s in MeasurementSubject] ==
  ["route", "run", "reject", "switch", "probe", "dead_letter"]`.
- `test_a_loop_measurement_defaults_every_optional_field`:
  `LoopMeasurement(LoopId.SOVEREIGNLOOP, MeasurementSubject.REJECT, NOW, "gpt-oss-20b",
  "sovereignloop", "gpt-oss:20b").to_record()` has `latency_ms`, `waited_seconds` and
  `queue_depth` all `None` and `outcome == ""`.
- `test_a_naive_measurement_instant_is_refused`: `replace(LoopMeasurement(LoopId.PAIDLOOP,
  MeasurementSubject.RUN, NOW, None, None, None), at=datetime(2026, 9, 22, 12, 0))` raises
  `ValueError` matching `"must be timezone-aware"`.
- `test_a_measurement_record_is_json_safe`: `json.dumps(LoopMeasurement(LoopId.SOVEREIGNLOOP,
  MeasurementSubject.SWITCH, NOW, "gpt-oss-20b", None, "gpt-oss:20b", latency_ms=210.5,
  outcome="gpt-oss-20b->qwen3-coder-30b").to_record())` does not raise.
- `test_no_record_carries_a_capacity_time_or_completion_field`: for each of the four dataclasses,
  `{f.name for f in dataclasses.fields(cls)}` has no name in
  `{"resets_at", "capacity", "credits", "complete", "success"}`.
- `test_classes_satisfy_their_interfaces`: one instance of each of the four dataclasses against
  its Protocol; `ExclusionReason.NO_WEIGHT` and `MeasurementSubject.PROBE` against
  `StringValueInterface`.

## Checks the lane must run (all must pass)
At `d3b4a388` the root `tests/conftest.py:146-151` creates a per-worker PostgreSQL database in
`pytest_configure`, so every pytest command below needs a reachable PostgreSQL
(`VIBEY_TEST_DATABASE_URL`) until lane `fakes-harness-decouple` lands.

    uv run ruff format src/vibey/domain/loop_events.py src/vibey/domain/interfaces/loop_events_interface.py src/vibey/domain/ledger.py tests/domain/test_loop_events.py
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_loop_events.py tests/domain/test_ledger.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    git diff --stat HEAD -- tests/domain/test_ledger.py

## Out of scope
- Anything that appends a `LOOP_ROUTED` or `PAID_FALLBACK_DECLARED` event (lanes
  `loops-selecting-loop-provider`, `loops-subprocess-fallback-declared`).
- Anything that produces an `AdapterExclusion` from live health rows (lane
  `loops-weighted-candidates`) or from a loop decision (lane `loops-loop-selector`).
- The measurement log that persists a `LoopMeasurement` (lane `loops-result-store`) and every
  caller that records one (`loops-resident-schedule`, `loops-router-routing`,
  `loops-seat-host-core` and its siblings, `loops-probe-consumer`,
  `loops-control-and-dead-letters`).
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-domain-loop-id`.

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
