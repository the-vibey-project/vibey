## Title
feat(engines): EngineSelector splits into weighted_candidates and select_from, and names why each pool engine is not a candidate

ADR-0046 lane L11 (slug `loops-weighted-candidates`).

## Why
Draft ADR-0046 §2 (`specs/ADR-two-loops.md:122-126`): the outer rotation layer, `LoopSelector`,
"reads the same health rows and applies the same eligibility and weights as today. Those come
from `EngineSelector.weighted_candidates`, which is extracted from `select_engine` unchanged",
and whenever it chooses paidloop, vibey writes `PaidFallbackDeclared` naming "every sovereign
adapter in the pool and why that adapter could not take the job". Sub-doctrine 8.a
(`src/vibey_tools/gh/docs/doctrines.md:99-112`) requires that a paid fallback be "declared loudly
to a human", and 7.c (`doctrines.md:82`) asks the ledger to record as much as possible.

At integration `d3b4a388` the reasons are thrown away. `EngineSelector.select_engine`
(`src/vibey/application/engine_selector.py:102-226`) builds runtimes (`:115-155`), skips a row
whose circuit state it does not know (`:131-133`), filters with `eligible()`
(`src/vibey/domain/rotation.py:67-86`, called at `engine_selector.py:158`), and raises
`NoEligibleEngine` at `:159-160` with no word about which engine failed which rule. This lane
splits the method into two public halves with the same behaviour, and makes the first half say
why each pool engine is not a candidate. Nothing is declared yet: lanes `loops-loop-selector`,
`loops-subprocess-fallback-declared` and `loops-selecting-loop-provider` consume this.

## Required behaviour
1. **`WeightedCandidates`** is appended to `src/vibey/application/dto.py`, after `RotationCursor`
   (the file's last class, `:236-245`):
   ```python
   @dataclass(frozen=True, slots=True)
   class WeightedCandidates:
       """One BUILD selection's outer-layer inputs (ADR-0046 §2): every eligible engine as an
       SWRR candidate with its effective weight, and every other pool engine with the reason it
       is not one. ``EngineSelector.weighted_candidates`` builds it, ``select_from`` picks from
       it, and ``LoopSelector`` reads it to choose a loop and to name the sovereign adapters a
       paid fallback passed over."""

       project_id: UUID
       candidates: tuple[Candidate, ...]
       exclusions: tuple[AdapterExclusion, ...]
   ```
   with two new imports in `dto.py`: `from vibey.domain.loop_events import AdapterExclusion` and
   `from vibey.domain.rotation import Candidate` (ruff's isort order puts them after
   `from vibey.domain.job import ...` and `from vibey.domain.phase import ...` respectively).
2. **`EngineSelector.weighted_candidates(self, project_id: UUID, requirement: JobRequirement, allow_list: frozenset[EngineId] | None = None, cost_aware: bool = False, affinity_engine: EngineId | None = None) -> WeightedCandidates`**
   (async). It is today's `select_engine` body `:115-206` with exactly these changes:
   - it never raises `NoEligibleEngine`: where `:159-160` raised, it returns
     `WeightedCandidates(project_id=project_id, candidates=(), exclusions=<the exclusions>)`
     **before** reading the cursor repository (today's raise also came before `:165`);
   - otherwise it returns `WeightedCandidates(project_id=project_id, candidates=tuple(candidates), exclusions=<the exclusions>)`
     where `candidates` is built exactly as `:175-206` builds it (cursor initialization `:162-173`
     included, unchanged);
   - **the pool** is `allow_list`, or every health row when `allow_list` is None. For each pool
     engine that is not a candidate it adds exactly one `AdapterExclusion`, from the first rule
     it fails, in `eligible()`'s order:
     | the engine | exclusion |
     |---|---|
     | in `allow_list`, has a descriptor, has no health row | `AdapterExclusion(<id>, ExclusionReason.NO_HEALTH_ROW)` |
     | `record.installed` is false | `NOT_INSTALLED` |
     | `record.conformance_ok` is false | `CONFORMANCE_FAILED` |
     | authentication stale (`auth_ok_at` None, or at least `AUTH_TTL` old — the same `auth_valid` as `:136`) | `AUTHENTICATION_STALE` |
     | circuit state unknown (`_circuit_state` returns None) | `CIRCUIT_OPEN`, `capacity_state=record.capacity_state`, `detail=f"unrecognized circuit state {record.circuit}"` (decision D8) |
     | circuit OPEN after the half-open time check of `_circuit_state` (`:59-96`) | `CIRCUIT_OPEN`, `capacity_state=record.capacity_state`, `detail=""` |
     | in `requirement.excluded` | `EXCLUDED_BY_JOB` |
     | `requirement.capabilities - descriptor.capabilities` non-empty | `MISSING_CAPABILITY`, `detail="missing " + ", ".join(sorted(c.value for c in missing))` |
     A half-open circuit is a candidate (weight 0.25, which rounds up to 1), never an exclusion.
     A closed circuit whose failure EWMA reached 1.0 is a candidate with effective weight 0,
     never an exclusion here (lane `loops-loop-selector` names it `NO_WEIGHT`).
   - Rows skipped as today are skipped here too and produce no exclusion: an engine id that is
     not an `EngineId` (`:125-127`), and an engine this selector has no descriptor for
     (`:128-130`). A health row outside `allow_list` produces none: it is not in the pool.
   - `exclusions` is sorted by `engine_id` (each engine appears at most once).
3. **`EngineSelector.select_from(self, weighted: WeightedCandidates) -> tuple[EngineId, Selection]`**
   (async): empty `weighted.candidates` raises
   `NoEligibleEngine(f"No engines meet requirements for project {weighted.project_id}")` (today's
   message, `:160`); otherwise `select(preferred_tier(weighted.candidates))` and the cursor
   update, exactly as `:208-226`, with `project_id` replaced by `weighted.project_id`.
4. **`select_engine`** keeps its signature and docstring; its body becomes
   `return await self.select_from(await self.weighted_candidates(project_id, requirement, allow_list=allow_list, cost_aware=cost_aware, affinity_engine=affinity_engine))`.
   Its behaviour is byte-identical: `tests/application/test_engine_selector.py`,
   `tests/application/test_engine_selection.py` and `tests/application/test_rotation_handoff.py`
   pass **unedited**.
5. **`EngineSelectorInterface`** (`src/vibey/application/interfaces/engines.py:196-212`) gains
   both methods with the same signatures, so `isinstance(EngineSelector(...), EngineSelectorInterface)`
   (`tests/application/test_engine_selector.py:527-536`) still holds.
6. No payload anywhere carries a time: an exclusion names a capacity state by its name only
   (non-negotiable 2; `AdapterExclusion` from lane `loops-ledger-kinds` enforces it).

## Where to change
Read `STORM/EDITING-RULES.md` first. All three source
files are over 100 lines: change them with `edit_file` (or the checked replacement below), never
`write_file`.

- `src/vibey/application/dto.py` (245 lines): the two imports and the appended class (behaviour 1).
- `src/vibey/application/engine_selector.py` (229 lines), in this order:
  1. Imports. `from vibey.application.dto import EngineHealthRecord, RotationCursor` becomes
     `from vibey.application.dto import EngineHealthRecord, RotationCursor, WeightedCandidates`;
     add `from vibey.domain.loop_events import AdapterExclusion, ExclusionReason` after the
     `vibey.domain.errors` import.
  2. Replace the body of `select_engine` **first**, while its two markers are still unique. Save
     this program to a scratch file outside the repository (for example `/tmp/l11_splice.py`)
     and run `python3 /tmp/l11_splice.py` from the repository root:
     ```python
     from pathlib import Path

     p = Path("src/vibey/application/engine_selector.py")
     s = p.read_text()
     start_marker = "        # Get health records\n"
     end_marker = "        return selection.engine_id, selection\n"
     assert s.count(start_marker) == 1, s.count(start_marker)
     assert s.count(end_marker) == 1, s.count(end_marker)
     start = s.index(start_marker)
     end = s.index(end_marker) + len(end_marker)
     new = (
         "        return await self.select_from(\n"
         "            await self.weighted_candidates(\n"
         "                project_id,\n"
         "                requirement,\n"
         "                allow_list=allow_list,\n"
         "                cost_aware=cost_aware,\n"
         "                affinity_engine=affinity_engine,\n"
         "            )\n"
         "        )\n"
     )
     p.write_text(s[:start] + new + s[end:])
     ```
  3. Then `edit_file` with `old_string` = `    async def select_engine(` and `new_string` = the three
     new methods below, a blank line, and `    async def select_engine(` again. The body of
     `weighted_candidates` is the old `:115-206` text (read it from `git show HEAD:src/vibey/application/engine_selector.py`)
     with the changes marked `# NEW`:
     ```python
         async def weighted_candidates(
             self,
             project_id: UUID,
             requirement: JobRequirement,
             allow_list: frozenset[EngineId] | None = None,
             cost_aware: bool = False,
             affinity_engine: EngineId | None = None,
         ) -> WeightedCandidates:
             """Every eligible engine as an SWRR candidate, and why each other pool engine is not.

             `select_engine`'s first half, moved here unchanged (ADR-0046 §2) except that it
             never raises: no candidate is an answer, and `select_from` turns it into today's
             `NoEligibleEngine`. The pool is `allow_list`, or every health row when it is None.
             A pool engine with no health row, or one `eligible()` refuses, gets one
             `AdapterExclusion` naming the first rule it fails, in `eligible()`'s own order
             (`domain/rotation.py`). A row or pool member this worker has no descriptor for is
             skipped, as before: this worker could never run it.
             """
             # Get health records
             health_records = await self._health_service.list_for_project(project_id)

             # Build EngineRuntime objects
             now = datetime.now(UTC)
             runtimes = []
             exclusions: list[AdapterExclusion] = []  # NEW
             recorded: set[EngineId] = set()  # NEW
             for record in health_records:
                 # (the vibey#287 comment of :122-124, unchanged)
                 engine_id = record.engine_id
                 if not isinstance(engine_id, EngineId):
                     continue
                 descriptor = self._descriptors.get(engine_id)
                 if descriptor is None:
                     continue
                 recorded.add(engine_id)  # NEW
                 state = self._circuit_state(record, now=now)

                 # Check auth TTL
                 auth_valid = record.auth_ok_at is not None and (now - record.auth_ok_at) < AUTH_TTL

                 if allow_list is None or engine_id in allow_list:  # NEW (5 lines)
                     exclusion = self._exclusion(
                         record, descriptor, state=state, auth_valid=auth_valid, requirement=requirement
                     )
                     if exclusion is not None:
                         exclusions.append(exclusion)
                 if state is None:
                     continue

                 circuit = Circuit(...)          # :138-144 unchanged
                 runtimes.append(EngineRuntime(...))  # :146-155 unchanged

             if allow_list is not None:  # NEW (6 lines)
                 exclusions.extend(
                     AdapterExclusion(engine_id.value, ExclusionReason.NO_HEALTH_ROW)
                     for engine_id in allow_list
                     if engine_id in self._descriptors and engine_id not in recorded
                 )
             ordered = tuple(sorted(exclusions, key=lambda exclusion: exclusion.engine_id))  # NEW

             # Filter to eligible engines
             eligible_runtimes = eligible(runtimes, requirement=requirement, allow_list=allow_list)
             if not eligible_runtimes:
                 return WeightedCandidates(project_id=project_id, candidates=(), exclusions=ordered)  # NEW

             # :162-206 unchanged (cursor read and initialization, the candidates loop)

             return WeightedCandidates(  # NEW
                 project_id=project_id, candidates=tuple(candidates), exclusions=ordered
             )

         @staticmethod
         def _exclusion(
             record: EngineHealthRecord,
             descriptor: EngineDescriptor,
             *,
             state: CircuitState | None,
             auth_valid: bool,
             requirement: JobRequirement,
         ) -> AdapterExclusion | None:
             """The first `eligible()` rule this row fails, in that function's order, or None.

             An OPEN circuit is named with its capacity state and never a time, so a credits
             refusal cannot grow a deadline here (non-negotiable 2). A circuit state a newer
             vibey wrote reads as open: this selector cannot tell whether it admits a run
             (`_circuit_state`), so it says so instead of guessing (ADR-0046 decision D8).
             """
             engine = descriptor.engine_id.value
             if not record.installed:
                 return AdapterExclusion(engine, ExclusionReason.NOT_INSTALLED)
             if not record.conformance_ok:
                 return AdapterExclusion(engine, ExclusionReason.CONFORMANCE_FAILED)
             if not auth_valid:
                 return AdapterExclusion(engine, ExclusionReason.AUTHENTICATION_STALE)
             if state is None:
                 return AdapterExclusion(
                     engine,
                     ExclusionReason.CIRCUIT_OPEN,
                     capacity_state=record.capacity_state,
                     detail=f"unrecognized circuit state {record.circuit}",
                 )
             if state is CircuitState.OPEN:
                 return AdapterExclusion(
                     engine, ExclusionReason.CIRCUIT_OPEN, capacity_state=record.capacity_state
                 )
             if descriptor.engine_id in requirement.excluded:
                 return AdapterExclusion(engine, ExclusionReason.EXCLUDED_BY_JOB)
             missing = requirement.capabilities - descriptor.capabilities
             if missing:
                 return AdapterExclusion(
                     engine,
                     ExclusionReason.MISSING_CAPABILITY,
                     detail="missing " + ", ".join(sorted(capability.value for capability in missing)),
                 )
             return None

         async def select_from(self, weighted: WeightedCandidates) -> tuple[EngineId, Selection]:
             """SWRR over `weighted`'s candidates, sovereign tier first, then the cursor update:
             `select_engine`'s second half (ADR-0005, ADR-0038). No candidate raises today's
             `NoEligibleEngine`."""
             if not weighted.candidates:
                 raise NoEligibleEngine(
                     f"No engines meet requirements for project {weighted.project_id}"
                 )
             # (the "Sovereign before paid" comment of :208-211, unchanged)
             selection = select(preferred_tier(weighted.candidates))

             # Update rotation cursors
             updated_cursors = tuple(
                 RotationCursor(
                     project_id=weighted.project_id,
                     engine_id=c.engine_id,
                     current=c.current,
                     order=c.order,
                 )
                 for c in selection.candidates
             )
             await self._cursor_repository.update_many(weighted.project_id, updated_cursors)

             return selection.engine_id, selection
     ```
     Write the `...` placeholders out in full from the old text; the finished file has none.
     Keep `__all__ = ["EngineSelector"]`.
- `src/vibey/application/interfaces/engines.py` (212 lines): add `WeightedCandidates` to the
  `from vibey.application.dto import (...)` list (after `StopSummary`), and append to
  `EngineSelectorInterface`, after `select_engine`'s docstring and `...` (anchor: the unique line
  ``        Raises `domain.errors.NoEligibleEngine` when none qualify.``):
  ```python
      async def weighted_candidates(
          self,
          project_id: UUID,
          requirement: JobRequirement,
          allow_list: frozenset[EngineId] | None = None,
          cost_aware: bool = False,
          affinity_engine: EngineId | None = None,
      ) -> WeightedCandidates:
          """Every eligible engine as a weighted SWRR candidate, and one `AdapterExclusion`
          for each other pool engine (ADR-0046 §2). Never raises `NoEligibleEngine`."""
          ...

      async def select_from(self, weighted: WeightedCandidates) -> tuple[EngineId, Selection]:
          """SWRR over the candidates, sovereign tier first; saves the cursors.

          Raises `domain.errors.NoEligibleEngine` when there is no candidate.
          """
          ...
  ```
- The registry needs nothing: `EngineSelectorInterface` is already `EXEMPT` as a
  `CLASS_CONTRACT` in `tests/fakes/registry.py` (lane `fakes-registry`).
- New test file `tests/application/test_weighted_candidates.py`; line 1 is the provenance
  comment copied byte for byte from line 1 of `tests/application/test_engine_selector.py`.

## Acceptance criteria
- [ ] Every test named below passes.
- [ ] `git diff --stat HEAD -- tests/application/test_engine_selector.py tests/application/test_engine_selection.py tests/application/test_rotation_handoff.py` prints nothing.
- [ ] `grep -n "NoEligibleEngine" src/vibey/application/engine_selector.py` shows the import and
      the one raise in `select_from`; `weighted_candidates` has no `raise`.
- [ ] `uv run mypy --strict src/vibey` passes; `src/vibey/application/*` stays at 100% branch coverage.
- [ ] No test uses `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.

## Tests to write first (TDD)
`tests/application/test_weighted_candidates.py`. Fakes: `FakeEngineHealthRepository` and
`FakeRotationCursorRepository` from `tests.fakes.engines` (lane `fakes-engines`), the real
`EngineHealthService` and `EngineSelector`, and `BY_ENGINE_ID` from
`vibey.infrastructure.engines.descriptors`. Copy the record helper from
`tests/application/test_engine_selector.py:70-94` into the new file as `_record(project_id, engine_id, **overrides)`.
Use `EngineId.SOVEREIGNLOOP` (never `QWENLOOP`) for the sovereign engine.
- `test_weighted_candidates_carry_every_eligible_engine_with_its_weight`: healthy claudeloop and
  codexloop rows, `allow_list=None` → candidate ids `{CLAUDELOOP, CODEXLOOP}`, every
  `effective_weight == 1`, `exclusions == ()`, `project_id` echoed.
- `test_nothing_eligible_returns_no_candidates_and_leaves_the_cursors_alone`: no rows,
  `allow_list=frozenset({EngineId.CLAUDELOOP})` → `candidates == ()`,
  `exclusions == (AdapterExclusion("claudeloop", ExclusionReason.NO_HEALTH_ROW),)`, and
  `await cursors.list_for_project(project_id) == ()` afterwards.
- `test_each_ineligible_engine_names_the_first_rule_it_fails` (parametrized over one claudeloop
  row's overrides; `allow_list=None`; the expected tuple is `(expected,)`):
  `{"installed": False, "conformance_ok": False}` → `NOT_INSTALLED`;
  `{"conformance_ok": False, "auth_ok_at": None}` → `CONFORMANCE_FAILED`;
  `{"auth_ok_at": None}` → `AUTHENTICATION_STALE`;
  `{"auth_ok_at": datetime.now(UTC) - timedelta(hours=25)}` → `AUTHENTICATION_STALE`;
  `{"circuit": "open", "capacity_state": "CreditsExhausted"}` →
  `AdapterExclusion("claudeloop", ExclusionReason.CIRCUIT_OPEN, capacity_state="CreditsExhausted")`;
  `{"circuit": "tripped"}` →
  `AdapterExclusion("claudeloop", ExclusionReason.CIRCUIT_OPEN, detail="unrecognized circuit state tripped")`.
  Each case also asserts `candidates == ()`.
- `test_a_job_exclusion_and_a_missing_capability_are_named`: a healthy claudeloop row with
  `JobRequirement(effort=Effort.STANDARD, excluded=frozenset({EngineId.CLAUDELOOP}))` →
  `EXCLUDED_BY_JOB`; with `JobRequirement(effort=Effort.STANDARD, capabilities=frozenset({Capability.WEB_SEARCH}))`
  → `AdapterExclusion("claudeloop", ExclusionReason.MISSING_CAPABILITY, detail="missing web_search")`.
- `test_a_half_open_circuit_is_a_candidate_not_an_exclusion`: `circuit="open"`,
  `probe_next_at=datetime.now(UTC) - timedelta(minutes=1)` → one candidate with
  `health_factor == 0.25` and `effective_weight == 1`; `exclusions == ()`.
- `test_rows_outside_the_pool_or_without_a_descriptor_are_not_reported`: (a) healthy claudeloop
  row and an agyloop row with `installed=False`, `allow_list={CLAUDELOOP}` → `exclusions == ()`;
  (b) a selector built with `descriptors={EngineId.CLAUDELOOP: BY_ENGINE_ID[EngineId.CLAUDELOOP]}`,
  a healthy claudeloop row and a codexloop row with `installed=False`,
  `allow_list={CLAUDELOOP, CODEXLOOP}` → `exclusions == ()` (no descriptor: neither a reason nor
  a `NO_HEALTH_ROW`).
- `test_exclusions_are_sorted_by_engine_id`: `allow_list={SOVEREIGNLOOP, AGYLOOP, CODEXLOOP}`,
  an agyloop row with `auth_ok_at=None`, a codexloop row with `installed=False`, no sovereign
  row → `[e.engine_id for e in exclusions] == ["agyloop", "codexloop", "sovereignloop"]`.
- `test_affinity_reaches_the_candidate`: healthy claudeloop and codexloop,
  `affinity_engine=EngineId.CLAUDELOOP` → claudeloop's candidate has `affinity_factor == 2.0`
  and `effective_weight == 2`; codexloop's has 1.
- `test_select_from_nothing_raises_todays_message`: `select_from(WeightedCandidates(project_id, (), ()))`
  raises `NoEligibleEngine` whose `str()` equals `f"No engines meet requirements for project {project_id}"`.
- `test_select_from_prefers_the_sovereign_tier_and_saves_the_cursors`: healthy claudeloop and
  sovereignloop rows → `select_from(await weighted_candidates(...))` returns `EngineId.SOVEREIGNLOOP`,
  and afterwards `await cursors.get(project_id, EngineId.SOVEREIGNLOOP)` is not None.
- `test_select_engine_equals_select_from_over_weighted_candidates`: two independent setups
  (separate repositories) with healthy claudeloop and codexloop; six picks through
  `select_engine` and six through `select_from(await weighted_candidates(...))` give the same
  list of engine ids.
- `test_the_selector_still_satisfies_its_interface`: `isinstance(selector, EngineSelectorInterface)`,
  and `EngineSelectorInterface` has the attributes `weighted_candidates` and `select_from`.

## Checks the lane must run (all must pass)
First run `uv run ruff format src/vibey/application/dto.py src/vibey/application/engine_selector.py src/vibey/application/interfaces/engines.py tests/application/test_weighted_candidates.py`.

    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_weighted_candidates.py tests/application/test_engine_selector.py tests/application/test_engine_selection.py tests/application/test_rotation_handoff.py tests/application/test_interfaces_convention.py tests/fakes tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    git diff --stat HEAD -- tests/application/test_engine_selector.py tests/application/test_engine_selection.py tests/application/test_rotation_handoff.py
    git diff --stat

## Out of scope
- Choosing a loop, `NO_WEIGHT`, `UNROUTABLE` (lane `loops-loop-selector`); writing any ledger
  event (lanes `loops-subprocess-fallback-declared`, `loops-selecting-loop-provider`).
- Changing `SelectingEngineProvider`, `RotationHandoffService` or `domain/rotation.py`.
- Protected tests: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the Conventional
  Commit subject.

**Depends on:** `loops-ledger-kinds`, `fakes-engines`, `orm-engine-health`, `orm-rotation-cursor`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
