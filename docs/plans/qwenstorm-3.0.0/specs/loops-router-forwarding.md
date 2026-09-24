## Title
feat(loop-service): the router forwards a run request to its stored route's seat, unchanged

ADR-0046 lane L30b (slug `loops-router-forwarding`).

## Why
Draft ADR-0046 §3, "Flow for a BUILD job" (`STORM/specs/ADR-two-loops.md:169-179`),
steps 5-6: "The handler's `start` publishes the run request to `<loop>`. The loop's router looks
up the stored route and forwards the request, unchanged, to `<loop>.<seat>`." The idempotency
table (`:188`): "a forward (inner layer) | `run_id` = `message_id` | The router forwards a run
only to the seat of its stored route, so a redelivered intake message lands in the same seat
queue." §3, "Pinned runs send one message" (`:181`): "These are DESIGN and DECOMPOSE through the
command executor, and `vibey loop submit --engine`. The router routes the run request itself,
with the pin, and forwards it" -- a pinned `RunRequest` carries no prior `route_id` (there was no
separate Route step), so the router must decide the seat itself, from the request's own
`engine_id` and `model_pin`, using the same pure policies (`ResidencyPolicy`, `SeatChooser`) its
`route()` method already runs, weighted as a single candidate at weight 1 (the pin *is* the whole
candidate list for a pinned run). §4's backlog (`:214`): "The age of a seat's oldest request comes
from the router's in-memory first-seen times" -- `SeatBacklog.forwarded` (lane
`loops-resident-schedule`) is the router's own bookkeeping, and this lane is the one place a run
first becomes visible to the router, so this lane is the one that calls it.

`loops-router-routing` wrote `router.py` in full and left the exact seam this lane fills: its
`handle` method's final branch is "not a `<loop>` route or run request" → dead-letter, with the
comment "(Lane `loops-router-forwarding` inserts the `RunRequest` branch before the final
dead-letter line.)"

## Required behaviour
1. **`handle`**'s dispatch (`router.py`, from lane `loops-seat-host-core`'s sibling
   `loops-router-routing`) gains a `RunRequest` branch, inserted **before** the final
   `await self._dead_letter(delivery, f"not a {self._loop_id.value} route or run request")` line
   and **after** the existing `RouteRequest` branch:
   ```python
   if isinstance(message, RunRequest) and message.loop_id == self._loop_id:
       await self._forward(delivery, message)
       return
   ```
2. **`async def _forward(self, delivery: AmqpDeliveryInterface, request: RunRequest) -> None`**.
   `RunStatus` (lane `loops-run-protocol-messages`) already has an `UNROUTABLE` member, the exact
   twin of `RouteStatus.UNROUTABLE`: an unresolvable pin is answered directly with a `RunResult`,
   never dead-lettered -- dead-lettering is reserved for a message that is malformed or addressed
   to the wrong loop (the branch above this one in `handle`), never for one this loop understood
   perfectly well and simply could not place:
   ```python
   seat = await self._seat_for(request)
   if seat is None:
       result = RunResult(
           run_id=request.run_id, status=RunStatus.UNROUTABLE, exit_code=None, meta_status=None,
           started_at=None, finished_at=self._clock.now(),
           detail=f"no route or pinned seat for run {request.run_id} on {self._loop_id.value}",
           stdout=None, stderr=None, cached_at=None,
       )
       await self._reply(delivery, request.run_id, result)
       await delivery.complete()
       self._log.info(
           "run_unroutable", loop=self._loop_id.value, run_id=str(request.run_id), detail=result.detail
       )
       return
   self._backlog.forwarded(seat, request.run_id, self._clock.now())
   await self._amqp.publish(
       self._names.runs_exchange(),
       self._names.seat_key(self._loop_id, seat),
       delivery.body,
       delivery.properties,
       mandatory=True,
   )
   await delivery.complete()
   self._log.info(
       "run_forwarded", loop=self._loop_id.value, run_id=str(request.run_id), seat=seat
   )
   ```
   `_reply` is the method `loops-router-routing` already wrote for a `RouteRequest`'s answer; it
   is reused unchanged here (`_reply(delivery, correlation_id, message)` publishes to
   `delivery.properties.reply_to` with `correlation_id` and does nothing when `reply_to is None`),
   so a pinned submit with no `reply_to` at all (fire-and-forget) is still handled safely. A
   forwarded (routable) request republishes the **exact bytes** the router received
   (`delivery.body`), so the seat host's codec decodes the identical message it would have decoded
   had it consumed the intake directly -- ADR-0046 says "forwards the request, unchanged" and this
   is what makes that literal.
3. **`async def _seat_for(self, request: RunRequest) -> str | None`** -- the seat a `RunRequest`
   belongs on, found two ways:
   - **Already routed.** `request.route_id is not None`: `routed = self._routes.get(request.route_id)`;
     when `routed is not None and routed.status is RouteStatus.ROUTED and routed.engine_id ==
     request.engine_id`, its `routed.seat` is authoritative (idempotency: "the router forwards a
     run only to the seat of its stored route"). A `route_id` naming a route this router has never
     stored, or one whose engine no longer matches the request, is treated as unrouted (fall
     through to the pinned case below) rather than refused outright: a route older than this
     router's own `prune` window must not permanently strand a redelivered run.
   - **Pinned, no route.** `request.route_id is None`: this loop routes the request itself, as a
     single candidate at weight 1, exactly as `route()` does for a `RouteRequest`, but sourced
     from the `RunRequest`'s own fields instead of a separate message:
     ```python
     if request.engine_id not in self._adapters:
         return None
     model: str | None = None
     if self._loop_id is LoopId.SOVEREIGNLOOP:
         residency = self._residency.choose(
             resident=self._resident_model(), default=self._default_model,
             declared=self._declarations, model_pin=request.model_pin, min_context=None,
         )
         if residency is None:
             return None
         model = residency.model
     decision = self._chooser.choose(
         loop_id=self._loop_id,
         candidates=(RouteCandidate(request.engine_id, 1),),
         cursors=(),
         model=model,
         pin=request.engine_id,
         default_adapter=self._default_adapter,
     )
     if decision.choice is None or decision.choice.seat not in self._seats:
         return None
     return decision.choice.seat
     ```
     `cursors=()` and `pin=request.engine_id` together mean this call never advances or persists
     a project's stored round-robin cursors: a pinned run is not a rotation decision, and
     `SeatChooser.choose` with a `pin` never touches `cursors` (lane `loops-seat-chooser`). Nothing
     is written to `self._cursors` for a pinned forward.
4. Any message that is neither a `RouteRequest` for this loop nor a `RunRequest` for this loop
   still reaches the existing final dead-letter line, unchanged.

## Where to change
`src/vibey/infrastructure/loop_service/router.py` only (plus the test file). It is longer than 100
lines after `loops-router-routing`: use `edit_file` only, never `write_file`.
- **Imports.** Add `RouteCandidate`, `RunRequest`, `RunResult` and `RunStatus` to the existing
  `from vibey.domain.run_protocol import (...)` line, whichever of the four are missing from it.
- **The dispatch branch.** `old_string`:
  ```
      await self._dead_letter(delivery, f"not a {self._loop_id.value} route or run request")
  ```
  `new_string`:
  ```python
      if isinstance(message, RunRequest) and message.loop_id == self._loop_id:
          await self._forward(delivery, message)
          return
      await self._dead_letter(delivery, f"not a {self._loop_id.value} route or run request")
  ```
- **New methods**, appended directly after `_answer_route` (the method `_reply` follows in
  `loops-router-routing`'s text; insert `_forward` and `_seat_for` between `_answer_route` and
  `_reply`, using `old_string` = the blank line and the `async def _reply(` line together, and
  `new_string` = the two new methods (behaviours 2-3) followed by that same blank line and
  `async def _reply(` line).
- Then `uv run ruff check --fix src/vibey/infrastructure/loop_service/router.py tests/infrastructure/loop_service`
  and `uv run ruff format` on the same paths.
- **New** `tests/infrastructure/loop_service/test_router_forwarding.py`. Line 1 is the provenance
  comment, copied byte for byte from line 1 of `src/vibey/infrastructure/process/reaper.py`.

## Acceptance criteria
- [ ] `tests/infrastructure/loop_service/test_router_routing.py` passes **unedited**.
- [ ] A `RunRequest` naming a stored route's seat is republished to that seat's queue with its
      body and properties unchanged, and the intake delivery is acknowledged.
- [ ] A pinned `RunRequest` (no `route_id`) is forwarded to the seat its own `engine_id` (and, for
      sovereignloop, `model_pin`) resolves to, and advances no project's stored cursor.
- [ ] An unroutable pin is answered with `RunResult(status=RunStatus.UNROUTABLE, ...)`, acknowledged,
      and never forwarded to any seat; a `route_id` naming nothing this router has stored falls back
      to the pinned path rather than being treated as an error.
- [ ] Every forward records the seat's backlog entry (`SeatBacklog.forwarded`) before publishing.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json`
      does not change.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_router_forwarding.py`. Copy the `_Clock`, `_Rig`,
`_route_request` and `_send` helpers from `test_router_routing.py` (do not import across test
modules); extend `_send` with a `_run_request(loop_id=LoopId.SOVEREIGNLOOP, *, route_id=None,
engine_id="sovereignloop", model_pin=None, run_id=None) -> RunRequest` factory (`cwd="/work/repo"`,
`args=("run", "plan.md")`, `deadline_seconds=60`, `start_by=NOW + timedelta(minutes=5)`,
`requested_at=NOW`, `caller="w1"`, `purpose=RunPurpose.RUN`, `capture_output=False`,
`supersedes=None`, `run_dir=None`).
- `test_a_routed_request_forwards_to_its_stored_seat`: route and store a `RunRouted` for
  `route_id=r` with `seat="gpt-oss-20b"`, `engine_id="sovereignloop"`; send a `RunRequest` naming
  `route_id=r` → it lands, body and `message_id`/`reply_to` unchanged, on
  `names.seat_queue(SOVEREIGNLOOP, "gpt-oss-20b")`; the intake is empty; `backlog.pending("gpt-oss-20b") == 1`.
- `test_a_pinned_request_with_no_route_resolves_its_own_seat`: sovereign rig, no stored route;
  send `_run_request(engine_id="sovereignloop", model_pin="qwen3-coder:30b")` → it lands on
  `names.seat_queue(SOVEREIGNLOOP, "qwen3-coder-30b")`; `rig.cursors.saves == []` (no cursor
  advance for a pin).
- `test_a_paid_pinned_request_resolves_to_its_engine_seat`: paid rig; send `_run_request(
  loop_id=LoopId.PAIDLOOP, engine_id="codexloop")` → lands on
  `names.seat_queue(PAIDLOOP, "codexloop")`.
- `test_a_route_id_naming_nothing_stored_falls_back_to_the_pin`: send a `RunRequest` with a
  `route_id` this router has never stored, `engine_id="sovereignloop"` → forwarded exactly as the
  no-route case, not dead-lettered.
- `test_a_route_whose_engine_no_longer_matches_falls_back_to_the_pin`: store a route for
  `engine_id="sovereignloop"`; send a `RunRequest` naming that `route_id` but
  `engine_id="opencode"` → resolved by the pinned path for `"opencode"`, not by the stale route.
- `test_an_unroutable_pin_is_answered_unroutable`: sovereign rig, `_run_request(engine_id=
  "sovereignloop", model_pin="undeclared-model:1b")` (a model no seat declares, so `ResidencyPolicy`
  finds nothing that can carry it) → the one reply is `RunResult(status=RunStatus.UNROUTABLE,
  run_id=request.run_id, detail=f"no route or pinned seat for run {request.run_id} on
  sovereignloop")`; the delivery is acknowledged; no publish to any seat queue; the intake's dead
  queue stays empty.
- `test_a_pin_outside_the_loops_adapters_is_answered_unroutable`: `_run_request(engine_id=
  "claudeloop")` on the sovereign rig → the same `UNROUTABLE` answer, never forwarded and never
  dead-lettered.
- `test_an_unroutable_pin_with_no_reply_to_is_still_acknowledged`: send with `reply_to=None` → no
  publish anywhere, the intake delivery is still acknowledged, and nothing raises.
- `test_forwarding_records_the_backlog_before_publishing`: after one forward,
  `backlog.oldest_wait_seconds(seat, NOW) == 0.0`, and a second identical forward (same `run_id`)
  keeps the first-seen time (`SeatBacklog.forwarded`'s own `setdefault` behaviour, unchanged by
  this lane, exercised through the router).
- `test_route_and_run_requests_for_the_other_loop_are_still_dead_lettered`: a `RunRequest` with
  `loop_id=PAIDLOOP` sent to the sovereign rig lands in the sovereign intake's dead queue, exactly
  as `test_anything_else_on_the_intake_is_dead_lettered` already proves for other shapes.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/fakes tests/meta/test_patching_ratchet.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
# after the local commit, this must print nothing:
git diff --stat HEAD~1 -- tests/infrastructure/loop_service/test_router_routing.py
```
Nothing here is OS-specific (8.h: Arch Linux and macOS alike).

## Out of scope
- Answering dead letters and control commands, and the `SUPERSEDE` broadcast (lane
  `loops-control-and-dead-letters`); probes (lane `loops-probe-consumer`).
- Choosing the outer loop or building the `RouteRequest`/`RunRequest` in the first place (lanes
  `loops-selecting-loop-provider`, `loops-command-executor`, `loops-cli-loop-submit`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests
  are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow
  `EDITING-RULES.md`.

**Depends on:** `loops-router-routing`.

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
