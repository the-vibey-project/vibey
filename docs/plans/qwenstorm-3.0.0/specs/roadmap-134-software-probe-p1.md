## Title
feat(gh): `vibey-gh estimate` measures other materials through declared probes, and the fit's two coordinates stay authoritative

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, Scope 1: "One measured probe per material ...
returning `unknown` with a reason when it cannot look"; "Proposed child issues" 1-4). Sub-doctrine
8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`: "Nothing runs unmeasured; a component that
cannot report its measurements is incomplete") and 10.f (`doctrines.md:419`: missing evidence is
reported as unknown). Today `OperationEstimator` measures exactly two coordinates, both from the fit
(`src/vibey_tools/gh/vibey_gh/operation_estimate.py:127-133`, `_fit_coordinates` at `:154-220`), and
its docstring says so (`:9-15`; `:28-29`: "The other sixteen coordinates have no probe yet"). Its
constructor (`:70-84`) has no seam a probe could arrive through. This lane adds that seam — one
Protocol, `MaterialProbeInterface`, and a `probes` keyword — and nothing else. The probes are later
lanes: `roadmap-134-software-probe-p2`, `roadmap-134-network-probe-p2`,
`roadmap-134-hardware-series-p3` and `roadmap-134-agency-probe-p3`. Sub-doctrine 9.b
(`doctrines.md:349`): the seam is declared, and its in-memory fake exists from the first day,
registered in the tenant registry that `fakes-tenant-gh-1` created.

Every path below is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package `vibey_gh`,
stdlib-only: `pyproject.toml:30` `dependencies = []`) unless it starts with `src/`.

## Required behaviour
1. **The seam.** New `vibey_gh/interfaces/material_probe_interface.py`. Line 1 is the provenance
   line copied byte for byte from line 1 of `vibey_gh/interfaces/memory_sampler_interface.py`; the
   rest is exactly:
   ```python
   """The seam for measuring one raw material's coordinates before a run (#134; ADR-0016).

   `vibey-gh estimate` measures the fit's two coordinates itself. Every other coordinate comes
   from a probe: one class per material, handed to `OperationEstimator` at construction. A
   probe that cannot look returns its coordinates as unknown -- `value=None` with a `source`
   saying exactly why -- and never a number it did not read (doctrine 10, sub-doctrine 10.f).

   `Coordinate` and `Stage` are imported for typing only -- frozen records, the same standing
   `Machine` has in the memory seam.
   """

   from __future__ import annotations

   from collections.abc import Sequence
   from typing import TYPE_CHECKING, Protocol, runtime_checkable

   if TYPE_CHECKING:
       from vibey_gh.feasibility import Coordinate, Stage


   @runtime_checkable
   class MaterialProbeInterface(Protocol):
       """Measures the coordinates of one material for the path a run must pass."""

       def measure(
           self, stages: Sequence[Stage], *, offline: bool, at: float
       ) -> tuple[Coordinate, ...]:
           """The coordinates this probe read for `stages`, each stamped `at`.

           A coordinate it could not read comes back with `value=None` and a `source` naming
           why. `offline` is the estimate's switch: a probe that would leave this machine does
           not while it is true, and says so. A failed reading is an answer, never a raise.
           """
           ...
   ```
2. **The constructor.** In `vibey_gh/operation_estimate.py`, `OperationEstimator.__init__`
   (`:70-84`) gains one keyword parameter, last, after `environ`:
   `probes: Sequence[MaterialProbeInterface] = (),` and its body gains, after
   `self._clock = clock or time.time` (`:104`), the line
   `self._probes: tuple[MaterialProbeInterface, ...] = tuple(probes)`.
   The class docstring (`:61-68`) gains, as its last sentence before the closing quotes:
   `` `probes` measure the other materials, in the order given; there are none by default.``
   Imports: `from collections.abc import Callable, Mapping` (`:41`) becomes
   `from collections.abc import Callable, Mapping, Sequence`, and
   `from vibey_gh.interfaces.material_probe_interface import MaterialProbeInterface` joins the
   `vibey_gh.interfaces` imports in alphabetical position (between `graded_estimator_interface`
   and `memory_sampler_interface`).
3. **The estimate.** In `estimate()` the three lines at `:131-133`
   ```python
           state = StateVector.unknown().with_measurements(
               self._fit_coordinates(machine, model, runner_read=runner_read, at=at)
           )
   ```
   become exactly:
   ```python
           state = StateVector.unknown()
           for probe in self._probes:
               state = state.with_measurements(probe.measure(stages, offline=self.offline, at=at))
           # The fit's two coordinates go in last, so no probe ever replaces what the fit read.
           state = state.with_measurements(
               self._fit_coordinates(machine, model, runner_read=runner_read, at=at)
           )
   ```
   `StateVector.with_measurements` (`feasibility.py:197-200`) already lets a later reading of a
   coordinate replace an earlier one, so a later probe wins over an earlier probe, and the fit
   wins over every probe for hardware and software availability. Nothing else in `estimate()`
   changes; with `probes=()` the result is identical to today's.
4. **The module docstring** (`:2-34`) is corrected in three places, each with `edit_file`
   (old text copied from `read_file` output):
   - The bullet at `:13-15` (`- **The other sixteen are `unknown`**, each naming ...`) becomes:
     ```
     - **The other sixteen come from probes** (`probes`, one per material, #134). A
       coordinate no probe measured stays `unknown`, naming what would measure it, and the
       reported confidence falls accordingly. None is defaulted: an unmeasured coordinate that
       quietly read as healthy would turn "we do not know" into "yes" (doctrine 10). The fit's
       two coordinates go in last, so no probe replaces what the fit read.
     ```
   - The last two lines of the offline paragraph (`:28-29`, from `` `unknown` and say why. The
     other sixteen`` to `will sit behind the same switch.`) become:
     ```
     `unknown` and say why. Every probe is handed the same switch (`offline`): a probe that
     would leave the machine does not while it is on, and its coordinates say so.
     ```
   - The paragraph at `:31-33` (`Nothing is written: ...`) becomes:
     ```
     The estimator writes nothing: the fit journal's observations are read, never appended
     to. An estimate is not an admission, and recording it as one would put a projection where
     the loop keeps its decisions. A probe that keeps a series of its own measurements may
     append those -- measurements, never the estimate -- to the store it was built with.
     ```
5. **The fake.** `test/fakes.py` (created by `fakes-tenant-gh-1`) gains, appended at the end,
   ```python
   class ScriptedMaterialProbe:
       """A material probe that answers fixed coordinates, stamped with the estimate's moment,
       and records every call as `(stage names, offline, at)` (#134)."""

       def __init__(self, *coordinates: Coordinate) -> None:
           self.coordinates = coordinates
           self.calls: list[tuple[tuple[str, ...], bool, float]] = []

       def measure(
           self, stages: Sequence[Stage], *, offline: bool, at: float
       ) -> tuple[Coordinate, ...]:
           self.calls.append((tuple(stage.name for stage in stages), offline, at))
           return tuple(replace(coordinate, measured_at=at) for coordinate in self.coordinates)
   ```
   with `from collections.abc import Sequence`, `from dataclasses import replace` and
   `from vibey_gh.feasibility import Coordinate, Stage` added to the file's import block (merge
   into an existing `from collections.abc import ...` / `from dataclasses import ...` line if
   there is one). Register it in `test/test_port_parity.py`: one entry mapping
   `MaterialProbeInterface` to `ScriptedMaterialProbe`, written exactly the way that file
   registers `ScriptedGitRunner` for `GitRunnerInterface`.

## Where to change
- New: `vibey_gh/interfaces/material_probe_interface.py`.
- Edit (always `edit_file`; `operation_estimate.py` is 220 lines): `vibey_gh/operation_estimate.py`
  (behaviours 2-4).
- Tests: append to `test/test_operation_estimate.py` (452 lines; add the two new imports to its
  top import block with `edit_file`, never below code); append to `test/fakes.py` and
  `test/test_fakes.py`; one entry in `test/test_port_parity.py`.
- Pattern to copy for the Protocol: `vibey_gh/interfaces/memory_sampler_interface.py:14-33`
  (TYPE_CHECKING import of a frozen record, `runtime_checkable`, docstrings).

## Acceptance criteria
- [ ] Every existing test in `test/test_operation_estimate.py` passes unmodified (`probes=()` is
      today's estimate exactly).
- [ ] A probe's coordinates reach the state and the verdict; the fit's two coordinates are never
      replaced by a probe (`test_a_probe_never_replaces_what_the_fit_measured`).
- [ ] `isinstance(ScriptedMaterialProbe(), MaterialProbeInterface)` holds and the fake is registered.
- [ ] The whole vibey-gh suite passes at its 100% line+branch floor; black, isort, mypy, ruff and
      import-linter are clean.

## Tests to write first (TDD)
Append to `test/test_operation_estimate.py`. Add to its top import block
`from vibey_gh.feasibility import Coordinate` (merge into the existing
`from vibey_gh.feasibility import NO, UNKNOWN, YES, Pipeline, Stage` line so it reads
`from vibey_gh.feasibility import NO, UNKNOWN, YES, Coordinate, Pipeline, Stage`),
`from vibey_gh.interfaces.material_probe_interface import MaterialProbeInterface`, and
`from fakes import ScriptedMaterialProbe` (directly after `import pytest`; then run
`isort test/test_operation_estimate.py` once so isort and ruff agree on its place). Then append a
helper and the tests:
```python
def _probed(*probes: MaterialProbeInterface, offline: bool = True) -> OperationEstimator:
    return OperationEstimator(
        "qwen2.5-coder:14b",
        base_url=LOCAL,
        offline=offline,
        machine_sampler=Machines(),
        model_sampler=Models(),
        clock=lambda: 1_800_000_000.0,
        probes=probes,
    )
```
- `test_the_probe_seam_is_declared` — `isinstance(ScriptedMaterialProbe(), MaterialProbeInterface)`.
- `test_probes_join_the_state_before_the_verdict` — a probe answering
  `Coordinate("network", "availability", 1.0, "probe: every endpoint answered")` and
  `Coordinate("agency", "availability", 0.0, "probe: no merge rights")`;
  `result = _probed(probe).estimate("develop")`: `result.state.measured == 4`;
  `result.state.get("network", "availability").measured_at == 1_800_000_000.0`;
  `result.verdict.verdict == NO`, `result.verdict.blocked_at == "install"` and
  `result.verdict.shortfalls[0].name == "agency.availability"` (agency first, as always).
- `test_every_probe_is_asked_about_the_path_with_the_switch_and_the_moment` —
  `probe = ScriptedMaterialProbe()`; `_probed(probe).estimate("main", start="develop-validation")`
  then `_probed(probe, offline=False).estimate("main", start="main")`;
  `probe.calls == [(("develop-validation", "main"), True, 1_800_000_000.0), (("main",), False, 1_800_000_000.0)]`.
- `test_a_probe_never_replaces_what_the_fit_measured` — a probe answering
  `Coordinate("hardware", "availability", 0.0, "probe: wrong")`; the result's
  `hardware.availability` is `1.0` and its `source` starts with `"fit: "`.
- `test_a_later_probe_replaces_an_earlier_reading` — two probes answering `network.availability`
  `0.5` then `1.0`; the state holds `1.0` with the second probe's source.
- `test_without_probes_the_estimate_is_the_fit_alone` —
  `_estimator().estimate("develop").state.measured == 2`.

Append to `test/test_fakes.py`:
- `test_material_probe_fake_answers_stamped_coordinates_and_records_calls` —
  `ScriptedMaterialProbe(Coordinate("network", "stability", 0.5, "s"))` asked with
  `(Stage("a"), Stage("b"))`, `offline=False`, `at=7.0` answers one coordinate whose
  `measured_at == 7.0` and `value == 0.5`, and `calls == [(("a", "b"), False, 7.0)]`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && (python -c "import vibey_gh" || python -m pip install -e ".[dev]")
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_operation_estimate.py test/test_fakes.py test/test_port_parity.py test/test_feasibility.py
    cd src/vibey_tools/gh && python -m pytest -q      # whole suite: --cov-fail-under=100 --cov-branch (pyproject.toml:66-70)
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git diff --stat   # exactly the six files named under "Where to change"

Formatter trap (`specs/forge-adapter.md` C8): black and ruff format both check this tenant. Keep
lines at or under 100 columns, one argument per line with a trailing comma in any wrapped call,
no backslash continuations; if they disagree on a line, restructure it rather than alternating.

## Out of scope
- Every probe (the four lanes named under "Why"), the probe composition and the CLI wiring
  (`roadmap-134-software-probe-p3`), `vibey_gh/cli.py`, `vibey_gh/config.py`.
- `vibey_gh/feasibility.py` (its `MEASURED_BY` texts stay as they are) and
  `vibey_gh/estimate_report.py` (probe coordinates render through the existing state lines; the
  cost lanes `roadmap-134-cost-integral-p3`/`-p4` own that file and the billing reading).
- If `roadmap-134-cost-integral-p3` has already landed, `test/test_operation_estimate.py` carries
  its `MeasuredCost` imports and its changed `cost` assertion: keep them exactly; this lane only
  merges its own imports into the existing lines and appends at the end.
- The cost integral, the billing export, the conductor-bridge probes
  (`roadmap-134-agent-information-probes`) and the validation harness (#134 children 5-7, 9).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
