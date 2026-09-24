## Title
feat(measure): MeasurementPort and MeasurementSource, a fan-out over sinks, and a registered in-memory fake

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) binds every loop, lane, queue,
surface, test run and model to record measurements, and "a component that cannot report its
measurements is incomplete". A component can only report through a declared seam (9.b, `:349`):
this lane declares the one every measuring component takes, `MeasurementPort`, and the one every
periodic sampler implements, `MeasurementSource`. Every seam gets a registered in-memory fake the
day it exists (`specs/fakes-registry.md`, `specs/ADR-test-harness-fakes-amendment.md`), so any
later lane can inject the port and assert on what was recorded without a database.

The sinks behind the port come next: the ledger sink (`gap-measure-ledger-sink`, 7.c) and the
family telemetry sink (`gap-measure-otel-sink`, 10.e). `MeasurementFanOut` is how the
composition root puts more than one behind a single port.

## Required behaviour
1. New `src/vibey/application/interfaces/measurement.py` (the measurement port family; copy the
   module docstring style of `application/interfaces/observability.py:1-8`):
   ```python
   @runtime_checkable
   class MeasurementPort(Protocol):
       """Records one measurement (8.g). Implementations: the ledger sink, the family
       telemetry sink, a fan-out over both, and the in-memory fake."""
       async def record(self, measurement: Measurement) -> None: ...

   @runtime_checkable
   class MeasurementSource(Protocol):
       """Something sampled on a period: a queue, a surface window, a model runtime."""
       @property
       def name(self) -> str: ...
       async def collect(self) -> tuple[Measurement, ...]: ...

   @runtime_checkable
   class MeasurementFanOutInterface(Protocol):
       """The contract of `application/measurement_fanout.py::MeasurementFanOut`."""
       @property
       def sinks(self) -> tuple[MeasurementPort, ...]: ...
       async def record(self, measurement: Measurement) -> None: ...
   ```
   `Measurement` is imported from `vibey.domain.measurement` (lane `gap-measure-domain`).
2. `src/vibey/application/interfaces/__init__.py` imports and exports the three names (import
   beside `messaging` at `:112`; add them to `__all__` beside `"MessagingPort"` at `:270`).
3. New `src/vibey/application/measurement_fanout.py`, `class MeasurementFanOut`:
   - `__init__(self, sinks: Sequence[MeasurementPort])`; an empty sequence raises
     `ValueError("a measurement fan-out needs at least one sink")`; kept as a tuple.
   - `sinks` property returns the tuple.
   - `async def record(self, measurement)`: awaits each sink in order. An exception from a sink
     propagates at once and the later sinks are not called. The docstring says why: the
     composition root puts the ledger sink first, so a measurement never reaches telemetry
     without reaching the ledger (7.c).
   - `FanOut` is never given itself as a sink: construction raises `ValueError` if any sink
     `is` a `MeasurementFanOut` (nesting would hide the order).
4. New `tests/fakes/measurement.py` (line 1 is the provenance line, copied from a sibling):
   - `class InMemoryMeasurements` (implements `MeasurementPort`): `recorded: list[Measurement]`;
     `record` appends; `fail_next(self, exc: BaseException) -> None` makes the next `record`
     raise `exc` and store nothing; `of(self, kind: SubjectKind) -> tuple[Measurement, ...]`;
     `named(self, name: str) -> tuple[Measurement, ...]` (by `subject.name`).
   - `class ScriptedMeasurementSource` (implements `MeasurementSource`):
     `__init__(self, name: str, batches: Sequence[tuple[Measurement, ...] | BaseException] = ())`;
     `collect` pops the next scripted batch (raising it when it is an exception) and returns
     `()` once the script is spent; `calls: int` counts collects.
5. Registry (`tests/fakes/registry.py`, lane `fakes-registry`): `REGISTRY` gains
   `FakeRegistration(MeasurementPort, InMemoryMeasurements)` and
   `FakeRegistration(MeasurementSource, lambda: ScriptedMeasurementSource("scripted"))`;
   `EXEMPT` gains `MeasurementFanOutInterface: ExemptReason.CLASS_CONTRACT`.

## Where to change
- New `src/vibey/application/interfaces/measurement.py`, `src/vibey/application/measurement_fanout.py`.
- `src/vibey/application/interfaces/__init__.py` (imports and `__all__`).
- New `tests/fakes/measurement.py`; `tests/fakes/registry.py` (three lines).
- New `tests/application/test_measurement_fanout.py`.

## Acceptance criteria
- [ ] `tests/fakes/test_port_parity.py` passes: both fakes satisfy their ports, their signatures
      match, neither is a stub, and every new Protocol is registered or exempt.
- [ ] A fan-out over two `InMemoryMeasurements` records to both in order; when the first
      `fail_next`s, the exception reaches the caller and the second recorded nothing.
- [ ] `MeasurementFanOut(())` and a nested fan-out raise `ValueError`.
- [ ] 100% branch coverage of `src/vibey/application/`.

## Tests to write first (TDD)
`tests/application/test_measurement_fanout.py` (build measurements with a small helper around
`Measurement(measurement_id=uuid4(), subject=MeasurementSubject(SubjectKind.LANE, "x"), …)`):
- `test_fan_out_records_to_every_sink_in_order`
- `test_a_failing_sink_stops_the_fan_out_and_reaches_the_caller`
- `test_a_fan_out_needs_a_sink_and_refuses_to_nest`
- `test_fan_out_satisfies_its_interfaces` (`MeasurementPort` and `MeasurementFanOutInterface`)
- `test_in_memory_measurements_filters_by_kind_and_name`
- `test_scripted_source_replays_batches_then_raises_then_runs_dry`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_measurement_fanout.py tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Any sink (`gap-measure-ledger-sink`, `gap-measure-otel-sink`), any source, any composition.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): MeasurementPort and MeasurementSource, a fan-out over sinks, and a registered in-memory fake`. Do not push.

## Lane card
- **Depends on:** `gap-measure-domain`, `fakes-registry`.
- **Standing constraints (every fakes-touching lane):** a fake is a plain class with real
  in-memory behaviour, never `unittest.mock`; substitute at a declared seam, never by
  `monkeypatch.setattr`, `mock.patch` or `MagicMock` (9.b); never raise a number in
  `tests/meta/patching_baseline.json`.
- **Must keep passing unchanged:** `tests/fakes/test_port_parity.py`, the protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
