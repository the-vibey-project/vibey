## Title
feat(preflight): conductor probes pass measured coordinates to the feasibility bridge through a declared port

## Why
Issue #134, "Proposed child issues" 5 (rewrite `issue-audit/updates/134.md`, Scope 1: one
measured probe per material, each "returning `unknown` with a reason when it cannot look").
This is the channel the information probe (`-p3`) needs.

Today the bridge sees only the engine sweep. `ConductorPreflight.run`
(`src/vibey/application/preflight.py:37-66`) hands the evaluator three things: `project_id`,
the preflight results and the engine-health records (`:58-62`). The port declares only those
(`RunFeasibilityEvaluatorInterface.evaluate`,
`src/vibey/application/interfaces/preflight_interface.py:54-66`). So a coordinate the sweep
cannot see, such as whether the specification or a credential is at hand, has no way in, and
stays `unknown` for good.

Sub-doctrine 9.b (`src/vibey_tools/gh/docs/doctrines.md:349`) says every new seam is a
declared port with a registered fake. 8.g (`:316-324`) says a component that cannot report
its measurements is incomplete. 10.f (`:419`) says unknown stays unknown.

vibey-gh already takes the shape, with no change on its side:
`Coordinate(material, prop, value | None, source)` validates the vocabulary
(`src/vibey_tools/gh/vibey_gh/feasibility.py:136-142`), and `StateVector.with_measurements`
lets a later reading of a coordinate replace an earlier one (`:197-200`).

## Required behaviour
1. **The reading.** `src/vibey/application/dto.py`, after `FeasibilityAssessment` (`:139-152`):
   ```python
   @dataclass(frozen=True, slots=True)
   class CoordinateReading:
       """One feasibility coordinate a conductor probe measured (#134): a material and a
       property in vibey-gh's vocabulary, a value on 0..1 where 1 is peak or None for
       unknown, and always the source that says how it was read or why it could not be."""

       material: str
       prop: str
       value: float | None
       source: str
   ```
2. **The port.** In `preflight_interface.py`:
   - Import `CoordinateReading` in the existing `from vibey.application.dto import (...)`
     (`:10-15`).
   - After `FeasibilityAssessmentInterface` (`:20-40`), add
     `@runtime_checkable class CoordinateReadingInterface(Protocol)`, with read-only properties
     `material: str`, `prop: str`, `value: float | None` and `source: str`.
   - After `RunFeasibilityEvaluatorInterface`, add:
     ```python
     @runtime_checkable
     class FeasibilityProbeInterface(Protocol):
         """Measures coordinates the engine sweep cannot see, for one project."""

         async def read(self, project_id: UUID) -> tuple[CoordinateReading, ...]:
             """Every coordinate this probe looked at, measured or unknown with its reason."""
             ...
     ```
   - `RunFeasibilityEvaluatorInterface.evaluate` gains a last keyword-only parameter
     `readings: Sequence[CoordinateReading] = ()`. The docstring adds "Readings fill
     coordinates the sweep does not measure; the sweep's own measurement of a coordinate wins."
3. **The conductor.** `ConductorPreflight` (`preflight.py:20-66`):
   - `__init__` gains a last keyword-only parameter
     `probes: Sequence[FeasibilityProbeInterface] = ()`, stored as `self._probes = tuple(probes)`.
   - In `run`, after `records = await self._health.list_for_project(project_id)` (`:51`):
     ```python
     readings: list[CoordinateReading] = []
     for probe in self._probes:
         readings.extend(await probe.read(project_id))
     ```
     The probes are read one after another, in the order given. The `evaluate(...)` call (`:58-62`)
     adds `readings=tuple(readings)`.
   - Import `Sequence` from `collections.abc`, `CoordinateReading` from `vibey.application.dto`,
     and `FeasibilityProbeInterface` in the existing import (`:12-16`).
4. **The bridge.** `VibeyGhFeasibilityAdapter.evaluate`
   (`src/vibey/infrastructure/preflight_feasibility.py:54-60`) gains
   `readings: Sequence[CoordinateReading] = ()`.
   - The `measurements` list starts with
     `[Coordinate(r.material, r.prop, r.value, r.source) for r in readings]`, and the sweep's
     own coordinates are appended after it. So `with_measurements` keeps the sweep's reading
     wherever both name one coordinate.
   - A reading outside vibey-gh's vocabulary raises vibey-gh's `ValueError` unchanged: a
     probe that names no coordinate is a programming error and fails loudly.
   - Comment the ordering in one line.
5. **The fakes** (lanes `fakes-engines`, `fakes-registry`):
   - In `tests/fakes/engines.py`, `ScriptedFeasibilityEvaluator.evaluate` gains the same
     keyword-only `readings: Sequence[CoordinateReading] = ()`. It records `readings` in each
     `self.calls` entry exactly as it records the other arguments.
   - Add `class ScriptedFeasibilityProbe` (implements `FeasibilityProbeInterface`):
     - `__init__(self, readings: Sequence[CoordinateReading] = ()) -> None` stores
       `self.readings = tuple(readings)` and `self.calls: list[UUID] = []`;
     - `async def read(self, project_id: UUID) -> tuple[CoordinateReading, ...]` appends
       `project_id` to `self.calls` and returns `self.readings`.
   - `tests/fakes/registry.py`:
     - `REGISTRY` gains `FeasibilityProbeInterface → ScriptedFeasibilityProbe()`, noted
       "scripted readings";
     - `EXEMPT` gains `CoordinateReadingInterface: ExemptReason.VALUE_CONTRACT`.

## Where to change
- `src/vibey/application/dto.py`, `src/vibey/application/interfaces/preflight_interface.py`,
  `src/vibey/application/preflight.py`, `src/vibey/infrastructure/preflight_feasibility.py`.
  Use `edit_file` throughout; `dto.py` is long.
- `tests/fakes/engines.py`, `tests/fakes/registry.py`.
- New `tests/application/test_preflight_readings.py`. Line 1 is the provenance header, copied
  byte-for-byte from `tests/infrastructure/test_preflight_feasibility.py:1`.
- Append to `tests/infrastructure/test_preflight_feasibility.py`. Do not rewrite it.
- `src/vibey/bootstrap.py` is not touched here: production passes no probe until `-p4`.

## Acceptance criteria
- [ ] `tests/fakes/test_port_parity.py` passes: the new port has a registered fake whose
      signature matches, and the reading contract is exempt.
- [ ] A probe's readings reach the evaluator in probe order. With no probes, `readings == ()`.
- [ ] A reading of `information.availability = 1.0` raises `required_measured` from 2 to 3 in
      the default path. A reading of `0.0` blocks at `interview`.
- [ ] A probe reading of `agent.availability = 0.0` does not override a conformant engine.
- [ ] 100% branch coverage of `src/vibey/application/` and `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/application/test_preflight_readings.py` (default tier). Use
`RecordingPreflightHealthService`, `ScriptedFeasibilityEvaluator` and
`ScriptedFeasibilityProbe` from `tests/fakes/engines.py`, and `adapters={}`. The assessment is
`FeasibilityAssessment("unknown", None, None, 0.0, 0, 0)`.
- `test_every_probe_is_read_for_the_project_in_order`: two probes with one reading each. The
  evaluator's one call carries `readings == (first, second)`. Each probe's `calls == [project_id]`.
- `test_no_probe_passes_no_readings`: the recorded `readings == ()`.
- `test_the_probe_port_is_satisfied_by_its_fake`:
  `isinstance(ScriptedFeasibilityProbe(), FeasibilityProbeInterface)` and
  `isinstance(CoordinateReading("information", "availability", None, "x"), CoordinateReadingInterface)`.

Append to `tests/infrastructure/test_preflight_feasibility.py`. It reuses `_health` and
`_preflight`, one conformant, authenticated `CLAUDELOOP`, and the real evaluator:
- `test_a_probe_reading_fills_its_coordinate`: `information.availability` 1.0 gives status
  `unknown`, `required == 6` and `required_measured == 3`.
- `test_a_measured_information_shortfall_blocks_at_interview`: `information.availability` 0.0
  with source `no spec` gives `infeasible`, `blocked_at == "interview"`, and a first repair
  that starts `information.availability — no spec`.
- `test_the_sweep_outranks_a_probe_on_the_same_coordinate`: `agent.availability` 0.0 gives
  status `unknown`, not `infeasible`.
- `test_a_reading_outside_the_vocabulary_is_refused`: material `weather` raises
  `pytest.raises(ValueError, match="is not a material")`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_preflight_readings.py tests/application/test_preflight.py tests/infrastructure/test_preflight_feasibility.py tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Any concrete probe (`roadmap-134-agent-information-probes-p3`) and the wiring in `bootstrap.py`
  (`-p4`).
- Timestamps on readings, writing readings to the ledger (the gaps.md §D1 measure lanes), and
  showing all 18 coordinates at worker start.
- vibey-gh (unchanged). Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
