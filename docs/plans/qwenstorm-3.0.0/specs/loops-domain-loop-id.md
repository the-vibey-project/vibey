## Title
feat(domain): the two loops as a vocabulary, and loop membership derived from the engine tier

ADR-0046 lane L01 (slug `loops-domain-loop-id`).

## Why
- **The law.** Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-234`) says the family
  runs **exactly two loops**, `sovereignloop` and `paidloop`, and that the outer rotation layer
  chooses `sovereignloop` by default, always (8.a, `:99-118`). 8.b (`:127-134`) makes `claudeloop`
  paidloop's default adapter.
- **The decision.** ADR-0046 §1 (`specs/ADR-two-loops.md:104-116`) adds a `LoopId` vocabulary
  "with a forward-compatible parser" (`:112`). It derives membership from the descriptor's tier
  (`LOCAL → sovereignloop`, `PAID → paidloop`, `:113`), "so there is only one classification to
  keep true". §2 fixes `LOOP_PREFERENCE = (sovereignloop, paidloop)` (`:122`). §10 places
  `loop.py` in `domain/` (`:302`).
- **The gap, at integration `d3b4a388`.** No loop vocabulary exists in `src/vibey/domain/`. The
  only sovereign-first preference is per tier: `TIER_PREFERENCE` (`src/vibey/domain/engine.py:51`)
  and `preferred_tier` (`src/vibey/domain/rotation.py:89-110`). Every later loops lane (router,
  seat host, loop selector, ledger kinds) needs `LoopId`.
- **Forward compatibility.** Stored vocabularies are read with `StoredValueParser`, never with the
  enum constructor (`src/vibey/domain/stored_value.py:10-24`, vibey#275/#287). `LoopId` follows
  that rule from day one.
- **9.b** (`doctrines.md:349`): every class gets an interface beside it.

## Required behaviour
1. **`src/vibey/domain/loop.py`** (new) defines, in this order:
   - `class LoopId(StrEnum)`: `SOVEREIGNLOOP = "sovereignloop"`, `PAIDLOOP = "paidloop"`.
   - `@dataclass(frozen=True, slots=True) class UnrecognizedLoopId(UnrecognizedValue)` with
     `members: ClassVar[frozenset[str]] = frozenset(loop.value for loop in LoopId)` and a
     docstring. Copy `UnrecognizedEngineId` (`src/vibey/domain/engine.py:54-65`).
   - `type StoredLoopId = LoopId | UnrecognizedLoopId`, with a docstring like
     `StoredEngineId`'s (`engine.py:68-71`).
   - `LOOP_ID_PARSER: Final[StoredValueParserInterface[LoopId, UnrecognizedLoopId]] =
     StoredValueParser(LoopId, UnrecognizedLoopId)`. Copy `ENGINE_ID_PARSER`'s shape
     (`engine.py:73-76`) **without** `aliases`, because `LoopId` has no legacy spellings.
   - `LOOP_PREFERENCE: Final[tuple[LoopId, ...]] = (LoopId.SOVEREIGNLOOP, LoopId.PAIDLOOP)`.
   - `LOOP_OF_TIER: Final[Mapping[EngineTier, LoopId]] = MappingProxyType({EngineTier.LOCAL:
     LoopId.SOVEREIGNLOOP, EngineTier.PAID: LoopId.PAIDLOOP})`.
   - `DEFAULT_ADAPTER: Final[Mapping[LoopId, EngineId]] = MappingProxyType({LoopId.SOVEREIGNLOOP:
     EngineId.SOVEREIGNLOOP, LoopId.PAIDLOOP: EngineId.CLAUDELOOP})` (8.b).
   - `class LoopMembership` (no state):
     ```python
     class LoopMembership:
         def loop_of(self, descriptor: EngineDescriptor) -> LoopId:
             return LOOP_OF_TIER[descriptor.tier]

         def split(self, candidates: Sequence[Candidate]) -> Mapping[LoopId, tuple[Candidate, ...]]:
             return MappingProxyType(
                 {
                     loop_id: tuple(c for c in candidates if LOOP_OF_TIER[c.tier] is loop_id)
                     for loop_id in LoopId
                 }
             )

         def default_adapter(self, loop_id: LoopId) -> EngineId:
             return DEFAULT_ADAPTER[loop_id]
     ```
     `split` always has both `LoopId` keys, in `LoopId` order. Each tuple keeps the input order,
     and a loop with no candidate maps to `()`.
   - `LOOP_MEMBERSHIP: Final[LoopMembershipInterface] = LoopMembership()`, with a docstring:
     "Stateless, so one instance serves. Annotated with the interface so `mypy --strict` checks
     the class against its seam." This is the pattern of `LEDGER_RECORDS`
     (`src/vibey/domain/ledger_record.py:157-159`).
   - Imports: `Mapping` and `Sequence` from `collections.abc`; `dataclass`; `StrEnum`;
     `MappingProxyType`; `ClassVar` and `Final`; `EngineDescriptor`, `EngineId` and `EngineTier`
     from `vibey.domain.engine`; `StoredValueParserInterface`; `Candidate` from
     `vibey.domain.rotation`; `StoredValueParser` and `UnrecognizedValue` from
     `vibey.domain.stored_value`; `LoopMembershipInterface` from the new interface module.
   - A module docstring that cites ADR-0046 §1–§2 and sub-doctrine 8.c, and says membership is
     derived from `EngineDescriptor.tier` and never declared twice.
2. **`src/vibey/domain/interfaces/loop_interface.py`** (new) declares
   `@runtime_checkable class LoopMembershipInterface(Protocol)` with the three methods and the same
   signatures. It starts with `from __future__ import annotations`, and it imports
   `EngineDescriptor`, `EngineId`, `LoopId` and `Candidate` only under `if TYPE_CHECKING:`. Copy
   the layout of `src/vibey/domain/interfaces/ledger_query_interface.py:1-21`. It never imports
   `vibey.domain.loop` at run time.
3. `LoopId` and `UnrecognizedLoopId` need no new interface. A `LoopId` member satisfies the
   existing `StringValueInterface` (`src/vibey/domain/interfaces/value_objects_interface.py:20-22`),
   and an `UnrecognizedLoopId` satisfies `UnrecognizedValueInterface`
   (`src/vibey/domain/interfaces/stored_value_interface.py:15-22`). The tests assert both.
4. The module is pure: no I/O, no clock, no async. `tests/domain/test_domain_purity.py` walks it.

## Where to change
- New: `src/vibey/domain/loop.py`, `src/vibey/domain/interfaces/loop_interface.py`,
  `tests/domain/test_loop.py`.
- Line 1 of each new file is the provenance comment, copied byte for byte from line 1 of
  `src/vibey/domain/engine.py`.
- Do not edit `src/vibey/domain/interfaces/__init__.py`. The new interface is imported from its
  module.
- No fake is registered. `tests/fakes/registry.py` (lane `fakes-registry`) walks
  `vibey.application.interfaces` and the infrastructure driver seams, and domain policies are
  tested with the real pure classes.

## Acceptance criteria
- [ ] `LOOP_ID_PARSER.parse("thirdloop") == UnrecognizedLoopId("thirdloop")`,
      `LOOP_ID_PARSER.known("thirdloop") is None`, and
      `LOOP_ID_PARSER.parse("paidloop") is LoopId.PAIDLOOP` (`test_a_stored_loop_id_reads_forward_compatibly`).
- [ ] `tuple(LOOP_OF_TIER[t] for t in TIER_PREFERENCE) == LOOP_PREFERENCE`
      (`test_loop_preference_follows_the_tier_preference`).
- [ ] `DEFAULT_ADAPTER[LoopId.PAIDLOOP] is EngineId.CLAUDELOOP` and
      `DEFAULT_ADAPTER[LoopId.SOVEREIGNLOOP] is EngineId.SOVEREIGNLOOP`.
- [ ] `isinstance(LOOP_MEMBERSHIP, LoopMembershipInterface)`.
- [ ] `tests/domain/test_domain_purity.py` passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_loop.py` (pure objects only). Build descriptors with a copy of the
`_descriptor` helper of `tests/domain/test_engine.py:15-30`, plus `dataclasses.replace(...,
tier=EngineTier.LOCAL)`. Build candidates with a copy of `_tiered` from
`tests/domain/test_rotation.py:353-364`.
- `test_there_are_exactly_two_loops`: `[loop.value for loop in LoopId] == ["sovereignloop", "paidloop"]`.
- `test_a_stored_loop_id_reads_forward_compatibly`: as in the acceptance criteria; also
  `str(UnrecognizedLoopId("thirdloop")) == "thirdloop"`, and `UnrecognizedLoopId("paidloop")`
  raises `ValueError`.
- `test_loop_preference_is_sovereign_first`: `LOOP_PREFERENCE == (LoopId.SOVEREIGNLOOP, LoopId.PAIDLOOP)`.
- `test_every_tier_belongs_to_exactly_one_loop`: `set(LOOP_OF_TIER) == set(EngineTier)` and
  `set(LOOP_OF_TIER.values()) == set(LoopId)`.
- `test_loop_preference_follows_the_tier_preference`.
- `test_each_loop_has_its_default_adapter`: the `DEFAULT_ADAPTER` values, and
  `LOOP_MEMBERSHIP.default_adapter(loop) is DEFAULT_ADAPTER[loop]` for both loops.
- `test_membership_follows_the_descriptor_tier`: a LOCAL descriptor → `SOVEREIGNLOOP`; a PAID
  (the default) descriptor → `PAIDLOOP`.
- `test_split_keeps_both_loops_and_the_input_order`: candidates `[paid_a, local_a, paid_b]` split
  to `{SOVEREIGNLOOP: (local_a,), PAIDLOOP: (paid_a, paid_b)}`; `split([])` has both keys mapping
  to `()`; the key order is `list(LoopId)`.
- `test_the_tables_are_read_only`: assigning into `LOOP_OF_TIER` or `DEFAULT_ADAPTER` raises
  `TypeError` (`# type: ignore[index]` on each line).
- `test_classes_satisfy_their_interfaces`: `isinstance(LoopMembership(), LoopMembershipInterface)`,
  `isinstance(LoopId.PAIDLOOP, StringValueInterface)`, and
  `isinstance(UnrecognizedLoopId("x"), UnrecognizedValueInterface)`.

## Checks the lane must run (all must pass)
At `d3b4a388` the root `tests/conftest.py:146-151` creates a per-worker PostgreSQL database in
`pytest_configure`, so every pytest command below needs a reachable PostgreSQL
(`VIBEY_TEST_DATABASE_URL`) until lane `fakes-harness-decouple` lands.

    uv run ruff format src/vibey/domain/loop.py src/vibey/domain/interfaces/loop_interface.py tests/domain/test_loop.py
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_loop.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Any use of `LoopId` outside `domain/`: the loop selector, router and seat host are later lanes.
- The residency policy, seat slugs and run protocol (lanes `loops-residency-policy` and
  `loops-run-protocol-messages`).
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-engine-id-sovereignloop`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
