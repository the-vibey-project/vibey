## Title
feat(domain): the residency schedule that bounds how long a waiting model can starve

ADR-0046 lane L02b (slug `loops-residency-schedule`).

## Why
- **The law.** Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-234`) keeps one model
  resident per machine, with waiting that is "ordered, visible and safe". 8.g (`:316-324`) says
  residency is chosen "from live evidence, never from assumption". The evidence here is each
  seat's queue depth and its oldest wait, which the caller measures and passes in.
- **The decision.** ADR-0046 §4 (`specs/ADR-two-loops.md:207-210`): execution consumes only the
  resident seat, and `ResidencySchedule` decides a switch, only between runs. It switches when:
  - the resident seat is empty and another seat has work; or
  - another seat's oldest request has waited at least `residency_max_wait_seconds` (default 900),
    and at least `residency_min_hold_runs` runs (default 1) have finished since the last switch.

  "This is the starvation bound: a request waits at most that long plus one run's deadline."
  Ages after a restart are counted from the restart (`:214`). Non-negotiable 4 (`:335`) keeps it
  pure: "`residency.py` ... take[s] `now` and ages as arguments."
- **The gap, at integration `d3b4a388`.** No schedule exists. Lane `loops-residency-policy`
  creates `src/vibey/domain/residency.py` with `SeatSlug` and `ResidencyPolicy` only. The seat
  scheduler (lane `loops-resident-schedule`, infrastructure) needs this pure decision to call.
- **9.b** (`doctrines.md:349`): every class gets an interface beside it.

## Required behaviour
1. **Append to `src/vibey/domain/residency.py`**, after the last definition that lane
   `loops-residency-policy` wrote (`ResidencyPolicy._can_carry`):
   ```python
   @dataclass(frozen=True, slots=True)
   class SeatLoad:
       """One seat's backlog as the caller measured it: ready messages, and the age of the
       oldest one in seconds (None when unknown, e.g. just after a restart)."""

       seat: str
       depth: int
       oldest_wait_seconds: float | None


   class ResidencySchedule:
       """When to change the resident seat (ADR-0046 §4). Pure: every age is an argument."""

       def next_seat(
           self,
           *,
           resident: str,
           resident_busy: bool,
           runs_since_switch: int,
           loads: Sequence[SeatLoad],
           max_wait_seconds: float,
           min_hold_runs: int,
       ) -> str | None:
           if resident_busy:
               return None
           others = [load for load in loads if load.seat != resident and load.depth > 0]
           if not others:
               return None
           resident_depth = next((load.depth for load in loads if load.seat == resident), 0)
           if resident_depth == 0:
               return max(others, key=self._wait).seat
           if runs_since_switch < min_hold_runs:
               return None
           starved = [load for load in others if self._wait(load) >= max_wait_seconds]
           if not starved:
               return None
           return max(starved, key=self._wait).seat

       @staticmethod
       def _wait(load: SeatLoad) -> float:
           return load.oldest_wait_seconds if load.oldest_wait_seconds is not None else 0.0
   ```
   The rules, in order:
   - a busy resident never switches (`None`): switches happen only between runs;
   - the candidates are the other seats with `depth > 0`, and none means `None`;
   - when the resident's depth is 0 (or the resident is missing from `loads`), return the
     candidate with the largest oldest wait;
   - otherwise switch only when `runs_since_switch >= min_hold_runs` **and** some candidate has
     waited at least `max_wait_seconds`; then return the one that waited longest;
   - otherwise `None`.

   An unknown wait (`None`) counts as `0.0` everywhere. Ties go to the earlier load in `loads`,
   because `max` returns the first maximal item.
2. **Append to `src/vibey/domain/interfaces/residency_interface.py`** two `@runtime_checkable`
   Protocols:
   - `SeatLoadInterface`, with read-only properties `seat: str`, `depth: int` and
     `oldest_wait_seconds: float | None`;
   - `ResidencyScheduleInterface`, with `next_seat` (the keyword-only signature above; `loads` is
     `Sequence[SeatLoad]`).

   Add `SeatLoad` to the interface module's `if TYPE_CHECKING:` import from
   `vibey.domain.residency`.
3. Nothing else in either file changes. `SeatSlug`, `ModelDeclaration`, `ModelChoice` and
   `ResidencyPolicy` keep their code and tests.
4. The module stays pure. `tests/domain/test_domain_purity.py` walks it.

## Where to change
- `src/vibey/domain/residency.py` is over 100 lines once lane `loops-residency-policy` has
  landed, so do not use `write_file` on it. Append with `edit_file`: use as `old_string` the last
  three non-blank lines of the file exactly as `read_file` shows them (the end of `_can_carry`),
  and as `new_string` those lines followed by two blank lines and the new code.
- `src/vibey/domain/interfaces/residency_interface.py`: append the two Protocols the same way,
  and extend its `TYPE_CHECKING` import with `edit_file`.
- New test file `tests/domain/test_residency_schedule.py`. Line 1 is the provenance comment,
  copied byte for byte from line 1 of `tests/domain/test_residency_policy.py`.
- If `residency.py` does not exist or has no `ResidencyPolicy`, stop and report
  `blocked: loops-residency-policy has not landed`.

## Acceptance criteria
- [ ] A busy resident never switches (`test_a_busy_resident_never_switches`).
- [ ] An idle resident yields to the longest-waiting seat, and ties go to input order.
- [ ] With work on the resident, a seat that waited `max_wait_seconds` or longer takes over only
      after `min_hold_runs` runs (`test_the_starvation_bound_forces_a_switch_after_the_hold`).
- [ ] The Hypothesis property holds: the answer is `None` or another seat with work.
- [ ] `tests/domain/test_residency_policy.py` passes unedited, and 100% branch coverage of
      `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_residency_schedule.py` (pure objects only). Call with
`max_wait_seconds=900.0`, `min_hold_runs=1` unless the test says otherwise, and use
`schedule = ResidencySchedule()`.
- `test_a_busy_resident_never_switches`: resident `"a"` busy, loads `[SeatLoad("a", 0, None),
  SeatLoad("b", 5, 5000.0)]` → `None`.
- `test_no_other_seat_with_work_never_switches`: loads `[SeatLoad("a", 3, 10.0),
  SeatLoad("b", 0, None)]` → `None`.
- `test_an_idle_resident_yields_to_the_longest_waiting_seat`: loads `[SeatLoad("a", 0, None),
  SeatLoad("b", 2, 5.0), SeatLoad("c", 1, 9.0)]`, `runs_since_switch=0` → `"c"` (the hold does
  not apply when the resident is idle).
- `test_ties_go_to_the_earlier_seat`: loads `[SeatLoad("a", 0, None), SeatLoad("b", 1, 7.0),
  SeatLoad("c", 1, 7.0)]` → `"b"`.
- `test_a_resident_missing_from_loads_counts_as_idle`: resident `"a"`, loads
  `[SeatLoad("b", 1, None)]` → `"b"`.
- `test_below_the_bound_the_resident_keeps_its_seat`: loads `[SeatLoad("a", 3, 1.0),
  SeatLoad("b", 2, 899.0)]`, `runs_since_switch=5` → `None`.
- `test_the_hold_prevents_a_switch_before_min_hold_runs`: loads `[SeatLoad("a", 3, 1.0),
  SeatLoad("b", 2, 901.0)]`, `runs_since_switch=0` → `None`.
- `test_the_starvation_bound_forces_a_switch_after_the_hold`: the same loads with
  `runs_since_switch=1` → `"b"`; and with loads `[SeatLoad("a", 3, 1.0), SeatLoad("b", 1, 950.0),
  SeatLoad("c", 1, 1200.0)]` → `"c"`.
- `test_unknown_wait_counts_as_zero`: loads `[SeatLoad("a", 3, 1.0), SeatLoad("b", 2, None)]`,
  `runs_since_switch=1`: with `max_wait_seconds=900.0` → `None`; with `max_wait_seconds=0.0` → `"b"`.
- `test_next_seat_is_only_ever_a_waiting_other_seat` (Hypothesis): draw `resident` from
  `st.sampled_from(["a", "b", "c"])`, `resident_busy` from `st.booleans()`, `runs_since_switch` from
  `st.integers(0, 5)`, `loads` as `st.lists(st.builds(SeatLoad, seat=st.sampled_from(["a", "b",
  "c"]), depth=st.integers(0, 5), oldest_wait_seconds=st.none() | st.floats(0, 5000)), max_size=4)`,
  `max_wait_seconds` from `st.floats(0, 2000)` and `min_hold_runs` from `st.integers(0, 3)`. The
  result is `None`, or a seat `!= resident` that appears in `loads` with `depth > 0`; and it is
  always `None` when `resident_busy`.
- `test_classes_satisfy_their_interfaces`: `ResidencySchedule()` against
  `ResidencyScheduleInterface`, and `SeatLoad("a", 0, None)` against `SeatLoadInterface`.

## Checks the lane must run (all must pass)
At `d3b4a388` the root `tests/conftest.py:146-151` creates a per-worker PostgreSQL database in
`pytest_configure`, so every pytest command below needs a reachable PostgreSQL
(`VIBEY_TEST_DATABASE_URL`) until lane `fakes-harness-decouple` lands.

    uv run ruff format src/vibey/domain/residency.py src/vibey/domain/interfaces/residency_interface.py tests/domain/test_residency_schedule.py
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_residency_schedule.py tests/domain/test_residency_policy.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    git diff --stat HEAD~1 -- tests/domain/test_residency_policy.py

## Out of scope
- Measuring depth and waits (the family client's `queue_depth`, lane `loops-amqp-queue-depth`, and
  `SeatBacklog`, lane `loops-resident-schedule`).
- Acting on a switch (cancel, unload, consume): lane `loops-resident-schedule`.
- Validating the bounds' ranges: lane `loops-config-loop-services` does that for the config keys.
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-residency-policy`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
