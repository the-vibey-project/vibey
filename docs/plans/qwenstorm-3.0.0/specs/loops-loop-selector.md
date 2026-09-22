## Title
feat(rotation): LoopSelector, the outer rotation layer, chooses sovereignloop first and names what a paid fallback passed over

ADR-0046 lane L12 (slug `loops-loop-selector`).

## Why
Draft ADR-0046 §2 (`specs/ADR-two-loops.md:118-127`) puts the outer rotation layer in vibey:
`LOOP_PREFERENCE = (sovereignloop, paidloop)` is "a deterministic preference, not a round robin";
`LoopSelector` "chooses the first loop that holds a candidate of positive weight"; paidloop's
choice is declared with "every sovereign adapter in the pool and why that adapter could not
take the job", the reasons including "unroutable (§4)"; and "there is no affinity across
loops … 8.a outranks ADR-0005's affinity factor, which now applies only inside a loop".
Sub-doctrine 8.a (`src/vibey_tools/gh/docs/doctrines.md:99-112`) is the rule.

At integration `d3b4a388` the outer layer exists only as policy inside one call:
`select(preferred_tier(candidates))` (`src/vibey/application/engine_selector.py:212`, with
`preferred_tier` at `src/vibey/domain/rotation.py:89-110`). Nothing chooses a *loop*, and nothing
can say why the sovereign tier lost. This lane adds the pure policy that does both, over the
`WeightedCandidates` lane `loops-weighted-candidates` produces. It performs no I/O; the two lanes
after it (`loops-subprocess-fallback-declared`, `loops-selecting-loop-provider`) call it.

## Required behaviour
1. **`LoopDecision`** is appended to `src/vibey/application/dto.py`, after `WeightedCandidates`:
   ```python
   @dataclass(frozen=True, slots=True)
   class LoopDecision:
       """The outer rotation layer's answer (ADR-0046 §2): the loop that takes the job, its
       candidates (the adapters its inner round robin may pick, each with its effective
       weight), and why each sovereign adapter could not take the job -- what a
       ``PaidFallbackDeclared`` names when ``loop_id`` is paidloop."""

       loop_id: LoopId
       candidates: tuple[Candidate, ...]
       sovereign_exclusions: tuple[AdapterExclusion, ...]
   ```
   plus `from vibey.domain.loop import LoopId` in `dto.py`'s imports.
2. **`LoopSelector.choose(weighted, *, excluded=None) -> LoopDecision | None`**: loops are tried
   in `LOOP_PREFERENCE` order (`domain/loop.py`, lane `loops-domain-loop-id`), skipping every
   loop that is a key of `excluded`. The first loop whose candidates (by
   `LoopMembership.split`, i.e. by `Candidate.tier`) include one with `effective_weight > 0`
   wins: `LoopDecision(loop_id, candidates=<all of that loop's candidates, weight 0 included, in input order>, sovereign_exclusions=self.sovereign_exclusions(weighted, excluded=excluded))`.
   No loop qualifies → `None`.
3. **No affinity crosses loops.** A paid candidate with `affinity_factor=2.0` never beats a
   sovereign candidate of positive weight: sovereignloop is chosen.
4. **`LoopSelector.sovereign_exclusions(weighted, *, excluded=None) -> tuple[AdapterExclusion, ...]`**
   (a public method, so the subprocess path can declare without re-choosing), in this order:
   - every exclusion in `weighted.exclusions` whose `engine_id` is a sovereign engine, in the
     order given (sovereign = its descriptor's loop is `LoopId.SOVEREIGNLOOP` by
     `LoopMembership.loop_of`, i.e. tier LOCAL);
   - then, for each sovereign candidate (`split(...)[LoopId.SOVEREIGNLOOP]`, in order), **exactly
     one** of: effective weight 0 →
     `AdapterExclusion(<id>, ExclusionReason.NO_WEIGHT, detail="eligible, but its effective weight is 0")`
     (decision D8); otherwise, when `LoopId.SOVEREIGNLOOP` is a key of `excluded` →
     `AdapterExclusion(<id>, ExclusionReason.UNROUTABLE, detail=excluded[LoopId.SOVEREIGNLOOP])`
     (decision D7); otherwise nothing (that adapter could take the job).
   Paid engines' exclusions never appear in it.
5. `LoopSelector(*, descriptors: Mapping[EngineId, EngineDescriptor], membership: LoopMembershipInterface | None = None)`;
   `membership` defaults to `LoopMembership()`. The sovereign set is computed once in
   `__init__`. The class does no I/O, reads no clock, and raises nothing.
6. **`LoopSelectorInterface`** is declared in the new module
   `src/vibey/application/interfaces/loop_routing.py` and exported from
   `vibey.application.interfaces`. (`tests/application/test_interfaces_convention.py:64-78`
   fails unless every Protocol declared under `application/interfaces/` is in its `__all__`, so
   the export lands with the declaration, here.)
7. **Registry.** `tests/fakes/registry.py`'s `EXEMPT` gains
   `LoopSelectorInterface: ExemptReason.PURE_POLICY` (no I/O: the tests use the real class).

## Where to change
Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` first. Line 1 of every new
file is the provenance comment copied byte for byte from line 1 of
`src/vibey/application/engine_selector.py`.

- `src/vibey/application/dto.py` (over 100 lines after lane `loops-weighted-candidates`:
  `edit_file` only): the import and the class of behaviour 1, appended after `WeightedCandidates`.
- New `src/vibey/application/interfaces/loop_routing.py` (lane `loops-routing-ports` appends two
  more Protocols to it later):
  ```python
  """The outer rotation layer's seams (ADR-0046 §2-§3): choosing the loop a BUILD job runs on,
  and -- lane loops-routing-ports -- routing it over the bus and binding the routed adapter."""

  from __future__ import annotations

  from collections.abc import Mapping
  from typing import Protocol, runtime_checkable

  from vibey.application.dto import LoopDecision, WeightedCandidates
  from vibey.domain.loop import LoopId
  from vibey.domain.loop_events import AdapterExclusion


  @runtime_checkable
  class LoopSelectorInterface(Protocol):
      """The contract of `application/loop_selector.py::LoopSelector`: pure, no I/O."""

      def choose(
          self, weighted: WeightedCandidates, *, excluded: Mapping[LoopId, str] | None = None
      ) -> LoopDecision | None:
          """The first loop in `LOOP_PREFERENCE`, not a key of `excluded`, that holds a
          candidate of positive weight; None when no loop does. `excluded` maps a loop that
          answered UNROUTABLE for this selection to the reason it gave."""
          ...

      def sovereign_exclusions(
          self, weighted: WeightedCandidates, *, excluded: Mapping[LoopId, str] | None = None
      ) -> tuple[AdapterExclusion, ...]:
          """Why each sovereign adapter of the pool could not take the job: the selector's
          own reasons, then NO_WEIGHT or UNROUTABLE for each sovereign candidate."""
          ...
  ```
- New `src/vibey/application/loop_selector.py`:
  ```python
  """The outer rotation layer (ADR-0046 §2): which loop takes a BUILD job.

  sovereignloop whenever it holds a candidate of positive weight, and paidloop only when it
  cannot (sub-doctrine 8.a): a deterministic preference in ``LOOP_PREFERENCE`` order, never a
  round robin. The inputs are ``EngineSelector.weighted_candidates``: the same health rows,
  eligibility and weights as the subprocess path. When the choice is paidloop, the decision
  names every sovereign adapter it passed over and why -- what ``PaidFallbackDeclared`` records.

  No affinity crosses loops: an affinity factor raises a candidate's weight inside its own
  loop only, and any positive sovereign weight wins, so a warm paid session never outranks a
  recovered sovereign adapter (8.a over ADR-0005's affinity).
  """

  from collections.abc import Mapping

  from vibey.application.dto import LoopDecision, WeightedCandidates
  from vibey.domain.engine import EngineDescriptor, EngineId
  from vibey.domain.interfaces.loop_interface import LoopMembershipInterface
  from vibey.domain.loop import LOOP_PREFERENCE, LoopId, LoopMembership
  from vibey.domain.loop_events import AdapterExclusion, ExclusionReason

  NO_WEIGHT_DETAIL = "eligible, but its effective weight is 0"


  class LoopSelector:
      """Declared by ``interfaces/loop_routing.py::LoopSelectorInterface``."""

      def __init__(
          self,
          *,
          descriptors: Mapping[EngineId, EngineDescriptor],
          membership: LoopMembershipInterface | None = None,
      ) -> None:
          self._membership = membership if membership is not None else LoopMembership()
          self._sovereign_ids = frozenset(
              engine_id.value
              for engine_id, descriptor in descriptors.items()
              if self._membership.loop_of(descriptor) is LoopId.SOVEREIGNLOOP
          )

      def choose(
          self, weighted: WeightedCandidates, *, excluded: Mapping[LoopId, str] | None = None
      ) -> LoopDecision | None:
          skipped: Mapping[LoopId, str] = excluded if excluded is not None else {}
          by_loop = self._membership.split(weighted.candidates)
          for loop_id in LOOP_PREFERENCE:
              if loop_id in skipped:
                  continue
              candidates = by_loop[loop_id]
              if any(candidate.effective_weight > 0 for candidate in candidates):
                  return LoopDecision(
                      loop_id=loop_id,
                      candidates=tuple(candidates),
                      sovereign_exclusions=self.sovereign_exclusions(weighted, excluded=skipped),
                  )
          return None

      def sovereign_exclusions(
          self, weighted: WeightedCandidates, *, excluded: Mapping[LoopId, str] | None = None
      ) -> tuple[AdapterExclusion, ...]:
          skipped: Mapping[LoopId, str] = excluded if excluded is not None else {}
          found = [e for e in weighted.exclusions if e.engine_id in self._sovereign_ids]
          unroutable = skipped.get(LoopId.SOVEREIGNLOOP)
          for candidate in self._membership.split(weighted.candidates)[LoopId.SOVEREIGNLOOP]:
              engine = candidate.engine_id.value
              if candidate.effective_weight == 0:
                  found.append(
                      AdapterExclusion(engine, ExclusionReason.NO_WEIGHT, detail=NO_WEIGHT_DETAIL)
                  )
              elif unroutable is not None:
                  found.append(
                      AdapterExclusion(engine, ExclusionReason.UNROUTABLE, detail=unroutable)
                  )
          return tuple(found)


  __all__ = ["NO_WEIGHT_DETAIL", "LoopSelector"]
  ```
  If `LoopMembership.split` or `loop_of` (lane `loops-domain-loop-id`) differ from the design
  sheet's signatures (`split(candidates: Sequence[Candidate]) -> Mapping[LoopId, tuple[Candidate, ...]]`
  with every `LoopId` key present; `loop_of(descriptor: EngineDescriptor) -> LoopId`), stop and report.
- `src/vibey/application/interfaces/__init__.py` (over 100 lines: `edit_file`): add
  `from vibey.application.interfaces.loop_routing import LoopSelectorInterface` directly above the
  unique line `from vibey.application.interfaces.messaging import MessagingPort`, and
  `"LoopSelectorInterface",` in `__all__` directly after the unique line `    "LedgerSiteWriter",`.
- `tests/fakes/registry.py` (lane `fakes-registry`): in the `EXEMPT` mapping literal, add
  `LoopSelectorInterface: ExemptReason.PURE_POLICY,` beside the other `PURE_POLICY` entries, and
  its import `from vibey.application.interfaces import LoopSelectorInterface` (merge it into the
  existing import from that package if there is one).
- New test file `tests/application/test_loop_selector.py`.

## Acceptance criteria
- [ ] Every test below passes; `tests/application/test_interfaces_convention.py` and
      `tests/fakes/test_port_parity.py` pass.
- [ ] `grep -nE "import (asyncio|datetime)|datetime.now|await " src/vibey/application/loop_selector.py` prints nothing.
- [ ] `uv run mypy --strict src/vibey` and `uv run lint-imports` pass.
- [ ] `src/vibey/application/*` stays at 100% branch coverage.

## Tests to write first (TDD)
`tests/application/test_loop_selector.py` (line 1: the provenance comment). Build inputs directly:
`Candidate(engine_id=..., base_weight=1, current=0, order=i, health_factor=h, fidelity_factor=1.0, cost_factor=1.0, affinity_factor=a, tier=EngineTier.LOCAL | EngineTier.PAID)`
and `WeightedCandidates(project_id=uuid4(), candidates=(...), exclusions=(...))`. The selector is
`LoopSelector(descriptors=BY_ENGINE_ID)` (`vibey.infrastructure.engines.descriptors`). Use
`EngineId.SOVEREIGNLOOP` with `tier=EngineTier.LOCAL` for the sovereign adapter.
- `test_a_positive_weight_sovereign_candidate_wins`: sovereign (weight 1) and claudeloop (PAID,
  weight 1) → `loop_id is LoopId.SOVEREIGNLOOP`, `candidates == (sovereign,)`,
  `sovereign_exclusions == ()`.
- `test_a_warm_paid_session_never_beats_a_sovereign_candidate`: claudeloop with
  `affinity_factor=2.0` (weight 2) and sovereign weight 1 → `LoopId.SOVEREIGNLOOP`.
- `test_paidloop_is_chosen_when_every_sovereign_candidate_has_no_weight`: sovereign with
  `health_factor=0.0`, claudeloop weight 1 → `LoopId.PAIDLOOP`, `candidates == (claudeloop,)`,
  `sovereign_exclusions == (AdapterExclusion("sovereignloop", ExclusionReason.NO_WEIGHT, detail=NO_WEIGHT_DETAIL),)`.
- `test_the_selectors_reasons_are_kept_for_sovereign_engines_only`: exclusions
  `(AdapterExclusion("claudeloop", ExclusionReason.CIRCUIT_OPEN, capacity_state="CreditsExhausted"), AdapterExclusion("sovereignloop", ExclusionReason.CONFORMANCE_FAILED))`,
  one codexloop candidate (PAID, weight 1) → `LoopId.PAIDLOOP` and
  `sovereign_exclusions == (AdapterExclusion("sovereignloop", ExclusionReason.CONFORMANCE_FAILED),)`.
- `test_an_unroutable_sovereign_loop_is_skipped_and_named`: sovereign weight 1, claudeloop
  weight 1, `excluded={LoopId.SOVEREIGNLOOP: "no local model can carry this job"}` →
  `LoopId.PAIDLOOP` and `sovereign_exclusions == (AdapterExclusion("sovereignloop", ExclusionReason.UNROUTABLE, detail="no local model can carry this job"),)`.
- `test_a_weightless_sovereign_candidate_is_named_once_even_when_unroutable`: sovereign
  `health_factor=0.0` and the same `excluded` → its only exclusion is `NO_WEIGHT`.
- `test_no_loop_qualifies`: every candidate weight 0 → `None`; both loops in `excluded` →
  `None`; no candidates at all → `None`.
- `test_the_chosen_loop_keeps_its_zero_weight_members_in_order`: claudeloop (weight 1, order 0)
  and codexloop (PAID, `health_factor=0.0`, order 1) → `candidates == (claudeloop, codexloop)`.
- `test_sovereign_exclusions_equal_the_decisions`: for the unroutable case,
  `selector.sovereign_exclusions(weighted, excluded=ex) == selector.choose(weighted, excluded=ex).sovereign_exclusions`.
- `test_membership_is_the_declared_seam`: `LoopSelector(descriptors=BY_ENGINE_ID, membership=LoopMembership())`
  decides as the default one.
- `test_the_selector_satisfies_its_interface`: `isinstance(LoopSelector(descriptors=BY_ENGINE_ID), LoopSelectorInterface)`,
  and `from vibey.application.interfaces import LoopSelectorInterface` works.

## Checks the lane must run (all must pass)
First run `uv run ruff format src/vibey/application tests/application/test_loop_selector.py tests/fakes/registry.py`.

    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_loop_selector.py tests/application/test_weighted_candidates.py tests/application/test_interfaces_convention.py tests/fakes tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    git diff --stat

## Out of scope
- Writing `PaidFallbackDeclared` or `LoopRouted` (lanes `loops-subprocess-fallback-declared` and
  `loops-selecting-loop-provider`); `LoopRoutingPort` and `RoutedAdapterBinderInterface` (lane
  `loops-routing-ports`); the loop's inner round robin (`domain/seat_choice.py`).
- `domain/rotation.py`, `domain/loop.py`, `EngineSelector`.
- Protected tests: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-weighted-candidates`, `loops-domain-loop-id`, `fakes-registry`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
