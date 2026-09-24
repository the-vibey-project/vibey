## Title
feat(domain): the CDD distance D(R) and the converging, neutral or diverging classifier

## Why
CLAUDE.md's non-negotiable "Convergence-Driven Development (CDD) is the enclosing development
loop" and sub-doctrine 9.c (`src/vibey_tools/gh/docs/doctrines.md:351`) both require that
each iteration "explicitly classifies the trajectory as converging, neutral or diverging".
ADR-0039 (`docs/architecture/decisions/0039-convergence-driven-development.md:40-47`) defines
the distance:
`D(R) = unverified criteria + failing checks + unresolved blockers + unreviewed or unrelated repository changes`.
It measures D(R) at four scopes (`:49-56`): project, phase or milestone, epic, and item.
`:98-107` defines the three trajectories. It also says "unknown parent context remains unknown
and is reported, never invented".

Only the out-of-tree storm and qwenloop's prompt text classify trajectories today
(`src/vibey_runners/qwen/src/qwenloop/application/storm.py:29`, `runner.py:53-62`). Nothing in
vibey's domain represents D(R), and the BUILD loop records no trajectory
(`issue-audit/gaps.md` N7, lines 757-763). This lane adds the pure vocabulary.
`gap-cdd-build-trajectory` then records it on every verify attempt.

## Required behaviour
1. New pure module `src/vibey/domain/cdd.py`, with the provenance header on line 1 and stdlib
   imports only:
   - `class CddScope(StrEnum)`: `PROJECT = "project"`, `PHASE = "phase"`, `EPIC = "epic"`, `ITEM = "item"`.
   - `class Trajectory(StrEnum)`: `CONVERGING = "converging"`, `NEUTRAL = "neutral"`, `DIVERGING = "diverging"`.
   - `@dataclass(frozen=True, slots=True) class CddDistance` with four fields, each
     `int | None`, in this order: `unverified_criteria`, `failing_checks`,
     `unresolved_blockers`, `unrelated_changes`. `None` means unknown. It is reported and never
     counted as zero.
     - `__post_init__` raises `ValueError(f"{name} must be >= 0, got {value}")` for a
       negative known part.
     - Property `known_total -> int`: the sum of the known parts.
     - Property `unknowns -> int`: the number of `None` parts.
     - `to_payload(self) -> dict[str, int | None]`: the four fields by name.
     - `@classmethod from_payload(cls, payload: Mapping[str, object]) -> "CddDistance | None"`.
       This is a forward-compatible reader: unknown keys are ignored. It returns `None` when a
       field is missing, is not an `int` or `None`, is a `bool`, or is negative.
   - `class TrajectoryClassifier` with
     `classify(self, previous: CddDistance | None, current: CddDistance) -> Trajectory`. The
     rules apply in this order:
     1. `previous is None` gives `NEUTRAL`. The first measurement gathers evidence; there is
        no earlier state to converge from.
     2. A part known in `previous` and unknown in `current` gives `DIVERGING`, because the
        iteration "loses a previously established fact".
     3. Let `delta` be the sum of `current` minus the sum of `previous`, over the parts known
        in both. `delta < 0` gives `CONVERGING`, and `delta > 0` gives `DIVERGING`.
     4. `delta == 0` and a part unknown in `previous` but known in `current` gives
        `CONVERGING`: a discovery step replaced an unknown.
     5. Otherwise `NEUTRAL`.
   - `TRAJECTORIES: Final[TrajectoryClassifierInterface] = TrajectoryClassifier()`.
   - `__all__` with every public name.
2. New interface `src/vibey/domain/interfaces/cdd_interface.py`, in the style of
   `publication_policy_interface.py:1-13`, holding two `@runtime_checkable` Protocols:
   - `CddDistanceInterface`, with the two properties and `to_payload`;
   - `TrajectoryClassifierInterface`, with `classify`.
   Both are exported from `src/vibey/domain/interfaces/__init__.py`, in the import block and
   in `__all__`, in sorted position.
3. `src/vibey/domain/ledger.py` `EventKind` (`:37-69`) gains
   `TRAJECTORY_RECORDED = "TrajectoryRecorded"`, appended after `DELIVERY_ESTIMATE_RECORDED`,
   with a one-line comment: "An iteration's CDD distance and trajectory (ADR-0039)". No
   migration is needed: `event.kind` is plain `text` with no CHECK (`migrations/0002_event.sql:9`).
4. Nothing else changes. The publication policy withholds the new kind by default, because it
   is not in `DEFAULT_ALLOWLIST` (`publication_policy.py:79`).

## Where to change
- New: `src/vibey/domain/cdd.py`, `src/vibey/domain/interfaces/cdd_interface.py`.
- Edit with edit_file: `src/vibey/domain/interfaces/__init__.py` and `src/vibey/domain/ledger.py`
  (one member).
- New test file: `tests/domain/test_cdd.py`, with the provenance header.
- These are pure values and policy, so there is no fake to register (the fakes registry scans
  application ports only, `specs/fakes-registry.md:93-96`).

## Acceptance criteria
- [ ] `CddDistance(2, 1, 0, None).known_total == 3` and `.unknowns == 1`.
- [ ] `CddDistance(-1, 0, 0, 0)` raises `ValueError`.
- [ ] `CddDistance.from_payload(d.to_payload()) == d` for mixed known and unknown values.
      `from_payload({"unverified_criteria": True, ...})` is `None`. Extra keys are ignored.
- [ ] `classify(None, anything)` is `NEUTRAL`.
- [ ] `classify(CddDistance(2,1,0,None), CddDistance(2,0,0,None))` is `CONVERGING`.
- [ ] `classify(CddDistance(2,0,0,None), CddDistance(2,1,0,None))` is `DIVERGING`.
- [ ] `classify(CddDistance(2,0,0,None), CddDistance(2,0,0,None))` is `NEUTRAL`.
- [ ] `classify(CddDistance(2,None,0,None), CddDistance(2,0,0,None))` is `CONVERGING` (discovery).
- [ ] `classify(CddDistance(2,0,0,None), CddDistance(2,None,0,None))` is `DIVERGING` (a lost fact).
- [ ] `classify(CddDistance(2,None,0,None), CddDistance(1,3,0,None))` is `CONVERGING`: delta is
      -1 on the common parts, and the rule order is pinned.
- [ ] `EventKind("TrajectoryRecorded") is EventKind.TRAJECTORY_RECORDED`.
- [ ] `isinstance(TRAJECTORIES, TrajectoryClassifierInterface)` and
      `isinstance(CddDistance(0,0,0,0), CddDistanceInterface)`.
- [ ] `tests/domain/test_domain_purity.py` passes. Every existing domain test passes unchanged.
      100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_cdd.py`:
- `test_known_total_and_unknowns`
- `test_a_negative_part_is_refused`
- `test_payload_round_trip_and_forward_compatible_reader` (parametrized, including the bool and missing-key cases)
- `test_first_measurement_is_neutral`
- `test_classifier_rules` (parametrized over the six cases above, with ids naming the rule)
- `test_the_trajectory_kind_is_a_ledger_event_kind`
- `test_values_and_classifier_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Recording trajectories (`gap-cdd-build-trajectory`).
- Distances at the project, phase and epic scopes. The vocabulary carries `CddScope`; which
  evidence feeds those scopes is a follow-up.
- Bounding divergence, for example parking after N diverging iterations: a follow-up lane.
- Docs.

Commit as `feat(domain): the CDD distance and trajectory classifier`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
