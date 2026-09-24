## Title
feat(ledger): every routed sovereign answer is a `LoopRouted` ledger event against the job that asked

## Why
7.c (`src/vibey_tools/gh/docs/doctrines.md:82`) is the thorough ledger: record as much as
possible, append-only, and never omit silently. ADR-0046 names `LoopRouted` as the ledger
event that shows which seat a run was routed to (`specs/ADR-two-loops.md` §2-§3 and §10,
`domain/ledger.py (PaidFallbackDeclared, LoopRouted)`), and makes residency switches visible
through it. Today nothing records which model answered a sovereign DESIGN, DECOMPOSE or
VISUAL question: the ledger's actor is the provider's fixed `engine_id`
(`src/vibey/infrastructure/engines/qwenloop_design.py:182`), and the model is not recorded at all.

Lane `gap-design-via-sovereignloop-2` hands every routed answer to a `RoutedChatRecorder`
(lane `-1`); lane `-3` makes the running job readable as `JOB_SCOPE.current()`. This lane is
the production recorder: one append through the ledger repository's existing seam, which lane
`orm-ledger` puts on the ORM. No new SQL.

## Required behaviour
1. `EventKind` (`src/vibey/domain/ledger.py:37-70`) gains, after `DELIVERY_ESTIMATE_RECORDED`
   (`:70`), the member `LOOP_ROUTED = "LoopRouted"` with a one-line comment: "Which loop, seat
   and model answered a run (ADR-0046); written by the caller that asked." If `EventKind`
   already has `LOOP_ROUTED` because an ADR-0046 lane landed first, use that member unchanged
   and add nothing. It is deliberately not added to `DEFAULT_ALLOWLIST`
   (`src/vibey/domain/publication_policy.py:78-127`): routing facts are not published by default.
2. New `src/vibey/infrastructure/ledger/routed_chat_recorder.py` (provenance line 1, copied
   from `src/vibey/infrastructure/db/review_ledger.py:1`) holds `class LedgerRoutedChatRecorder`:
   - `__init__(self, *, ledger: PostgresLedgerRepositoryInterface, scope: JobScopeInterface = JOB_SCOPE, logger: Logger | None = None, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION) -> None`.
     `PostgresLedgerRepositoryInterface` is `src/vibey/infrastructure/interfaces/class_contracts.py:78`;
     `JOB_SCOPE`/`JobScopeInterface` are lane `-3`'s; `Logger` is
     `src/vibey/application/interfaces/observability.py:23`; the default logger is
     `StructlogAppLogger()` (`src/vibey/infrastructure/logging.py:224`).
   - `async def record(self, request: PinnedChatRequest, answer: RoutedChatAnswer) -> None`:
     - `job = self._scope.current()`. When `job is None`, or `not isinstance(job.phase, Phase)`,
       it appends nothing and calls
       `self._log.warning("sovereign_route_not_ledgered", reason=..., caller=request.caller, loop_id=answer.loop_id, engine_id=answer.engine_id, seat=answer.seat, model=answer.model, run_id=answer.run_id)`
       with `reason="no running job"` or `reason="unknown phase"`. That is the stated omission
       7.c requires instead of a silent one (a CLI one-shot has no job).
     - Otherwise the payload is exactly
       `{"loop_id": answer.loop_id, "engine_id": answer.engine_id, "seat": answer.seat, "model": answer.model, "run_id": answer.run_id, "caller": request.caller, "model_pin": request.model_pin, "num_ctx": request.num_ctx}`
       and it awaits `self._ledger.append(LedgerEventDraft(project_id=job.project_id, cycle=job.cycle, phase=job.phase, kind=EventKind.LOOP_ROUTED, engine_id=ENGINE_ID_PARSER.known(answer.engine_id), job_id=job.id, causation_id=None, correlation_id=self._correlation.for_project(job.project_id).value, provenance=Provenance.TRUSTED, produced_at=datetime.now(UTC), payload=payload, digest=digest_event(payload)))`.
       Copy the draft's construction from `review_ledger.py:42-58`. `ENGINE_ID_PARSER` is
       `src/vibey/domain/engine.py:73`: an id this vibey does not know is stored as `None` in
       the column and kept verbatim in the payload. The prompt text, the schema and the answer
       are never written here: they are the providers' business, not routing facts.
3. New `src/vibey/infrastructure/ledger/interfaces/routed_chat_recorder_interface.py`
   (provenance line 1) declares `@runtime_checkable class LedgerRoutedChatRecorderInterface(RoutedChatRecorder, Protocol)`
   with a docstring and no new members, and `src/vibey/infrastructure/ledger/interfaces/__init__.py`
   exports it.

## Where to change
- `src/vibey/domain/ledger.py` (one member, edit_file).
- New `src/vibey/infrastructure/ledger/routed_chat_recorder.py` and its interface; edit
  `src/vibey/infrastructure/ledger/interfaces/__init__.py` (edit_file).
- New `tests/infrastructure/ledger/test_routed_chat_recorder.py`, using `InMemoryLedger`
  (`tests/fakes/ledger.py`, lane `fakes-ledger`), `JobScope` (lane `-3`), `make_job`
  (`tests/application/fakes.py:282`), and a small recording `Logger` class written in the test
  file with real list-appending methods (no `unittest.mock`).

## Acceptance criteria
- [ ] One routed answer inside a bound job appends exactly one `LoopRouted` event whose
      `project_id`, `cycle`, `phase` and `job_id` are the job's.
- [ ] Outside a job nothing is appended and one `sovereign_route_not_ledgered` warning is logged.
- [ ] `grep -n "text(\|execute(\|asyncpg" src/vibey/infrastructure/ledger/routed_chat_recorder.py` prints nothing.
- [ ] Every existing test under `tests/domain` passes (the parametrized `EventKind` tests
      include the new member).
- [ ] 100% branch coverage of `src/vibey/domain/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/ledger/test_routed_chat_recorder.py`:
- `test_a_routed_answer_is_ledgered_against_the_running_job` -- inside `scope.bound(job)`, one `record(...)` appends one event with kind `EventKind.LOOP_ROUTED`, the job's ids and phase, and the exact eight-key payload.
- `test_the_payload_never_carries_the_prompt_or_the_answer` -- the payload keys equal the eight named keys; no key is `system`, `user`, `schema` or `value`.
- `test_a_known_engine_id_fills_the_column_and_an_unknown_one_stays_in_the_payload` -- `"qwenloop"` gives `EngineId.QWENLOOP`; `"future-engine"` gives column `None` and payload `"future-engine"`.
- `test_outside_a_job_the_omission_is_logged_not_silent` -- no bound job: the ledger stays empty and the logger holds one `("sovereign_route_not_ledgered", {"reason": "no running job", ...})`.
- `test_the_digest_is_computed_over_the_payload` -- the appended draft's `digest == digest_event(payload)`.
- `test_recorder_satisfies_both_interfaces` -- `RoutedChatRecorder` and `LedgerRoutedChatRecorderInterface`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/ledger tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Composing this recorder into the worker (owed with the service-mode composition lane).
- `PaidFallbackDeclared` and the BUILD path's `LoopRouted` write (ADR-0046 lanes).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(ledger): every routed sovereign answer is a LoopRouted ledger event`. Do not push.

## Lane card
- **Depends on:** `gap-design-via-sovereignloop-1`, `gap-design-via-sovereignloop-3`,
  `fakes-ledger` (the `InMemoryLedger` fake), `orm-ledger` (the ledger append seam on the ORM).
- **Must keep passing unchanged:** `tests/domain/test_ledger.py`,
  `tests/domain/test_forward_compatible_readers.py`, every protected test.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
