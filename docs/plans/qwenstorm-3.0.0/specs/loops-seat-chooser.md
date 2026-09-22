## Title
feat(domain): SeatChooser, the loop's own smooth-weighted round robin over the candidates a caller sends

ADR-0046 lane L05 (slug `loops-seat-chooser`).

## Why
- **The law.** Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-234`) puts the inner
  rotation layer inside each loop, "fed by a queue", running "its own round robin across its
  adapters and models". ADR-0005 (cited throughout ADR-0046 §2) is nginx's smooth weighted round
  robin: `current += weight` for every candidate, pick the largest `current`, subtract the total
  weight from the winner.
- **The decision.** ADR-0046 §2 (`specs/ADR-two-loops.md:129-136`): "Inner layer: the loop. SWRR
  (ADR-0005's `select`) runs over the candidates vibey sends. Each candidate is an engine id with
  its effective weight. The loop keeps its own cursors … The loop's cursors persist, per project,
  in its own state directory (§10)." §1 (`:116`): "In paidloop's round robin, `claudeloop` has
  order 0, so it wins ties." §3's idempotency table (`:187`): "a route (outer layer) … never
  advances SWRR twice" -- the persisted cursor advance happens once per stored route, which is
  this module's caller's job (`loops-router-routing`), not this module's.

  This is **not** the same algorithm object as `domain/rotation.py::select`, which the outer layer
  and the subprocess path use over `Candidate` (a richer type carrying `health_factor`,
  `fidelity_factor`, `cost_factor` and `affinity_factor` computed from live health rows). The
  message a caller sends a loop carries only `RouteCandidate(engine_id, weight)` pairs -- capacity
  never crosses the wire (non-negotiable 2; the codec of lane `loops-run-codec` enforces it) -- so
  the loop's own round robin has no health signal to combine. `SeatChooser` is therefore the same
  nginx SWRR algorithm, implemented over the loop's own plain-weight candidates and its own
  persisted `SeatCursor` rows, kept in its own module so `domain/rotation.py` (the outer layer's
  algorithm, unchanged by ADR-0046) is never asked to serve two different candidate shapes.
- **The gap, at integration `d3b4a388`.** No inner-layer chooser exists. `loops-router-routing`
  and `loops-state-stores` already call the exact shape this lane must produce:
  `self._chooser.choose(loop_id=..., candidates=request.candidates, cursors=self._cursors.load(request.project_id),
  model=model, pin=request.pin, default_adapter=self._default_adapter)`, whose result has
  `.choice` (a `SeatChoice | None`, with `.engine_id`, `.seat` and `.cursors`) and `.reason` (a
  string used verbatim as `RunRouted.reason` when unroutable); `loops-state-stores` persists
  `SeatCursor(engine_id: str, current: int, order: int)` tuples through `LoopCursorStore`.
- **9.b** (`doctrines.md:349`): every class gets an interface beside it.

## Required behaviour
1. **`src/vibey/domain/seat_choice.py`** (new). Module docstring cites ADR-0046 §1-§2 and ADR-0005,
   and says: pure, no I/O, no clock; the algorithm is nginx's SWRR, run over the loop's own
   plain-weight candidates because capacity and health never cross the wire into a loop.
2. **`@dataclass(frozen=True, slots=True) class SeatCursor`**:
   ```python
   @dataclass(frozen=True, slots=True)
   class SeatCursor:
       """One adapter's SWRR state inside one loop, for one project (or the pinned/project-less
       bucket, keyed None by the caller). `order` is fixed the first time an adapter is seen for
       a project, so ties break by first-seen order, matching `default_adapter`'s claim to
       order 0 when it is the first candidate offered."""

       engine_id: str
       current: int
       order: int
   ```
3. **`@dataclass(frozen=True, slots=True) class SeatChoice`**:
   ```python
   @dataclass(frozen=True, slots=True)
   class SeatChoice:
       """The chosen adapter and seat, plus every candidate's updated cursor (to persist)."""

       engine_id: str
       seat: str
       cursors: tuple[SeatCursor, ...]
   ```
4. **`@dataclass(frozen=True, slots=True) class SeatChoiceDecision`**:
   ```python
   @dataclass(frozen=True, slots=True)
   class SeatChoiceDecision:
       """`choice` is None exactly when nothing could be chosen; `reason` is always set, and is
       the text a router turns into `RunRouted.reason` on an unroutable result."""

       choice: SeatChoice | None
       reason: str
   ```
5. **`class SeatChooser`** (no state):
   ```python
   class SeatChooser:
       """The loop's own smooth weighted round robin (ADR-0005) over the plain-weight
       candidates a caller sends, tie-broken by `default_adapter` and overridable by `pin`.
       """

       def choose(
           self,
           *,
           loop_id: LoopId,
           candidates: Sequence[RouteCandidate],
           cursors: Sequence[SeatCursor],
           model: str | None,
           pin: str | None,
           default_adapter: str,
       ) -> SeatChoiceDecision:
           offered = {c.engine_id: c.weight for c in candidates}
           if pin is not None:
               if pin not in offered:
                   return SeatChoiceDecision(
                       None, f"pinned engine {pin} is not offered as a candidate"
                   )
               return SeatChoiceDecision(
                   self._build(pin, model=model, cursors=cursors), reason=""
               )
           if not any(weight > 0 for weight in offered.values()):
               return SeatChoiceDecision(
                   None, f"no adapter of {loop_id.value} has positive weight"
               )
           by_id, order = self._seed(cursors, candidates, default_adapter)
           winner = self._advance(by_id, offered)
           updated = tuple(
               SeatCursor(engine_id=eid, current=state.current, order=order[eid])
               for eid, state in sorted(by_id.items(), key=lambda item: order[item[0]])
           )
           return SeatChoiceDecision(
               SeatChoice(
                   engine_id=winner,
                   seat=self._seat(winner, model),
                   cursors=updated,
               ),
               reason="",
           )

       def _build(
           self, engine_id: str, *, model: str | None, cursors: Sequence[SeatCursor]
       ) -> SeatChoice:
           # A pinned choice does not advance the round robin: it bypasses weight entirely,
           # so the cursors it returns are exactly what was already stored (nothing to save
           # beyond what the caller already has, but the shape stays uniform for the caller).
           return SeatChoice(engine_id=engine_id, seat=self._seat(engine_id, model), cursors=tuple(cursors))

       @staticmethod
       def _seat(engine_id: str, model: str | None) -> str:
           return SeatSlug().of(model) if model is not None else SeatSlug().of_paid(engine_id)

       @staticmethod
       def _seed(
           cursors: Sequence[SeatCursor],
           candidates: Sequence[RouteCandidate],
           default_adapter: str,
       ) -> tuple[dict[str, SeatCursor], dict[str, int]]:
           by_id = {cursor.engine_id: cursor for cursor in cursors}
           order: dict[str, int] = {cursor.engine_id: cursor.order for cursor in cursors}
           next_order = (max(order.values()) + 1) if order else 0
           # default_adapter claims order 0 (ADR-0046 §1) whenever it is a candidate and has
           # never been seen before; every other newly-seen candidate is ordered after it, in
           # the order the candidates were offered.
           ordered_ids = [c.engine_id for c in candidates]
           if default_adapter in ordered_ids and default_adapter not in order:
               order[default_adapter] = 0
               by_id[default_adapter] = SeatCursor(default_adapter, current=0, order=0)
               next_order = max(next_order, 1)
           for engine_id in ordered_ids:
               if engine_id not in order:
                   order[engine_id] = next_order
                   by_id[engine_id] = SeatCursor(engine_id, current=0, order=next_order)
                   next_order += 1
           return by_id, order

       @staticmethod
       def _advance(by_id: dict[str, SeatCursor], offered: Mapping[str, int]) -> str:
           total = sum(offered.values())
           for engine_id, weight in offered.items():
               state = by_id[engine_id]
               by_id[engine_id] = SeatCursor(engine_id, current=state.current + weight, order=state.order)
           winner = max(
               (eid for eid in offered if offered[eid] > 0),
               key=lambda eid: (by_id[eid].current, -by_id[eid].order),
           )
           won = by_id[winner]
           by_id[winner] = SeatCursor(winner, current=won.current - total, order=won.order)
           return winner
   ```
   - A candidate with weight 0 still gets its cursor seeded and advanced by `+0` (so it keeps its
     place and its stored `current`), but can never win (the `max` is restricted to
     `offered[eid] > 0`); this mirrors ADR-0046 §1's own tie rule ("all base weights stay 1") while
     letting a caller send a genuinely excluded candidate at weight 0 without it ever winning.
   - Ties in `current` break toward the **lower** `order` (`-by_id[eid].order` inside the `max`
     key, since `max` prefers the larger key and a lower order should win), which is how
     `claudeloop`'s order-0 claim actually wins a tie against a later-seen adapter of equal
     weight.
   - `cursors` returned always include **every** candidate offered this turn, in ascending
     `order`, whether or not it won: the caller persists the whole set (`LoopCursorStore.save`).
   - A `pin` bypasses weight and cursor advancement entirely: the pinned engine is chosen if (and
     only if) it is one of the candidates offered, and the stored cursors are returned unchanged.
6. **`src/vibey/domain/interfaces/seat_choice_interface.py`** (new): `@runtime_checkable` Protocols
   `SeatCursorInterface` (properties `engine_id: str`, `current: int`, `order: int`),
   `SeatChoiceInterface` (properties `engine_id: str`, `seat: str`, `cursors: tuple[SeatCursor,
   ...]`), `SeatChoiceDecisionInterface` (properties `choice: SeatChoice | None`, `reason: str`)
   and `SeatChooserInterface` (the `choose` method, same keyword-only signature). It starts with
   `from __future__ import annotations` and imports `LoopId`, `RouteCandidate`, `SeatChoice`,
   `SeatCursor` only under `if TYPE_CHECKING:`, following
   `src/vibey/domain/interfaces/ledger_query_interface.py:1-21`.
7. **Shared instance:** `SEAT_CHOOSER: Final[SeatChooserInterface] = SeatChooser()`, with the
   `LEDGER_RECORDS` docstring pattern (`src/vibey/domain/ledger_record.py:157-159`).
8. The module is pure. `tests/domain/test_domain_purity.py` walks it.

## Where to change
- New: `src/vibey/domain/seat_choice.py`, `src/vibey/domain/interfaces/seat_choice_interface.py`,
  `tests/domain/test_seat_choice.py`.
- Line 1 of each new file is the provenance comment, copied byte for byte from line 1 of
  `src/vibey/domain/engine.py`.
- Imports in `seat_choice.py`: `dataclass` from `dataclasses`; `Mapping`, `Sequence` from
  `collections.abc`; `Final` from `typing`; `LoopId` from `vibey.domain.loop`; `SeatSlug` from
  `vibey.domain.residency`; `RouteCandidate` from `vibey.domain.run_protocol`;
  `SeatChooserInterface` from the new interface module.
- If `vibey.domain.residency` or `vibey.domain.run_protocol` does not exist, stop and report
  which dependency has not landed.
- No fake is registered: the chooser is pure and tested with the real class.

## Acceptance criteria
- [ ] `default_adapter`, when offered and never seen before, gets `order == 0` and wins any tie
      against a candidate seen at the same turn (`test_the_default_adapter_wins_ties`).
- [ ] A repeated `choose` call with the same weights alternates fairly between two equally
      weighted candidates over several turns (`test_equal_weights_alternate_over_several_turns`).
- [ ] `pin` bypasses weight entirely and never advances a cursor.
- [ ] Nothing offered at positive weight is unroutable with a reason naming the loop.
- [ ] `tests/domain/test_domain_purity.py` passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_seat_choice.py` (pure objects only). Use `chooser = SeatChooser()` and
`CLAUDE = RouteCandidate("claudeloop", 1)`, `CODEX = RouteCandidate("codexloop", 1)`.
- `test_the_first_turn_seeds_cursors_in_offered_order`: `choose(loop_id=LoopId.PAIDLOOP,
  candidates=(CLAUDE, CODEX), cursors=(), model=None, pin=None, default_adapter="claudeloop")` →
  `choice.engine_id == "claudeloop"` (order 0 wins the first tie), `choice.seat ==
  "claudeloop"`, and `[c.order for c in choice.cursors] == [0, 1]`.
- `test_the_default_adapter_wins_ties`: two equally weighted candidates offered for the first
  time, `default_adapter="codexloop"` → `codexloop` wins (order 0), not the first-listed one.
- `test_equal_weights_alternate_over_several_turns`: feeding each turn's returned `cursors` back
  in as the next turn's `cursors`, six calls with `(CLAUDE, CODEX)` give exactly three
  `"claudeloop"` and three `"codexloop"` results, alternating.
- `test_a_zero_weight_candidate_never_wins_but_keeps_its_place`: `candidates=(CLAUDE,
  RouteCandidate("codexloop", 0))` chosen five times in a row always picks `"claudeloop"`, and
  the returned cursors always include both engines with `codexloop`'s `current` unmoving (stuck
  at 0) and its `order` unchanged.
- `test_nothing_at_positive_weight_is_unroutable`: `candidates=(RouteCandidate("claudeloop", 0),)`
  → `choice is None`, `reason == "no adapter of paidloop has positive weight"`.
- `test_a_pin_bypasses_weight_and_the_cursor`: `candidates=(CLAUDE, CODEX)`, `pin="codexloop"`,
  `cursors=(SeatCursor("claudeloop", 5, 0), SeatCursor("codexloop", -5, 1))` → `choice.engine_id
  == "codexloop"`, and `choice.cursors == (SeatCursor("claudeloop", 5, 0),
  SeatCursor("codexloop", -5, 1))` unchanged.
- `test_a_pin_outside_the_offered_candidates_is_unroutable`: `pin="cursorloop"`,
  `candidates=(CLAUDE,)` → `choice is None`, `reason == "pinned engine cursorloop is not offered as a candidate"`.
- `test_the_sovereign_seat_is_the_models_slug`: `choose(loop_id=LoopId.SOVEREIGNLOOP,
  candidates=(RouteCandidate("sovereignloop", 1),), cursors=(), model="gpt-oss:20b", pin=None,
  default_adapter="sovereignloop").choice.seat == "gpt-oss-20b"`.
- `test_the_paid_seat_is_the_engine_id_with_no_model`: `choose(loop_id=LoopId.PAIDLOOP,
  candidates=(CLAUDE,), cursors=(), model=None, pin=None,
  default_adapter="claudeloop").choice.seat == "claudeloop"`.
- `test_an_established_cursor_keeps_its_order_across_turns`: a candidate offered with
  `cursors=(SeatCursor("codexloop", 3, 7),)` and now also offering `"claudeloop"` for the first
  time keeps `codexloop`'s `order == 7` and gives `claudeloop` a fresh order after it (`8`, since
  `claudeloop` is not `default_adapter` in this call).
- `test_classes_satisfy_their_interfaces`: `isinstance(SeatChooser(), SeatChooserInterface)` and
  `isinstance(SEAT_CHOOSER, SeatChooserInterface)`; a `SeatCursor`, a `SeatChoice` and a
  `SeatChoiceDecision` against their Protocols.

## Checks the lane must run (all must pass)
At `d3b4a388` the root `tests/conftest.py:146-151` creates a per-worker PostgreSQL database in
`pytest_configure`, so every pytest command below needs a reachable PostgreSQL
(`VIBEY_TEST_DATABASE_URL`) until lane `fakes-harness-decouple` lands.

    uv run ruff format src/vibey/domain/seat_choice.py src/vibey/domain/interfaces/seat_choice_interface.py tests/domain/test_seat_choice.py
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_seat_choice.py tests/domain/test_residency_policy.py tests/domain/test_run_protocol.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Persisting `SeatCursor` rows (lane `loops-state-stores`) and calling `choose` from a router
  (lane `loops-router-routing`).
- Choosing the *model* (that is `ResidencyPolicy`, lane `loops-residency-policy`); this module
  only turns an already-chosen model (or `None`, for paidloop) into a seat name.
- `domain/rotation.py` and its `Candidate`/`select()`, which stay exactly as they are: the outer
  layer's algorithm, over health-derived weights, is untouched by this lane.
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-residency-policy`, `loops-run-protocol-messages`.

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
