## Title
feat(loop-service): ServiceEngineAdapter's prompt, stop and preflight methods, sent as control commands over the bus

ADR-0046 lane L57b (slug `loops-service-adapter-control`).

## Why
Lane `loops-service-adapter-run` implemented `ServiceEngineAdapter.start`/`tail`/
`release_diagnostics` -- the three methods a BUILD job's happy path needs -- and left every other
`EngineAdapter` method for this lane, because a run's mid-flight controls (a prompt, a stop, wind
down) are a different conversation over the bus: `vibey.run.control/1`
(`STORM/specs/ADR-two-loops.md:167`), consumed by
`loops-control-and-dead-letters`' `ControlConsumer` and answered by whichever `SeatHost` actually
holds the run (`SeatHost.control`, lane `loops-seat-host-drain`). §3's queue table
(`:152`): "`vibey.runs.control` | topic exchange | each loop binds `<loop>` and `all`". ADR-0044's
handoff and wind-down machinery (`domain/noloss.py`, `handoff_orchestration.py`, `wind_down.py`)
is unchanged by ADR-0046 (non-negotiable 11, `docs/CLAUDE.md`), so this lane's job is narrow:
translate the same `EngineAdapter` calls `LoopProcessAdapter` already answers locally into
`RunControl` publishes, so nothing above the adapter boundary can tell the two apart.

## Required behaviour
All appended to `src/vibey/infrastructure/loop_service/adapter.py` (lane
`loops-service-adapter-run`'s file), on `ServiceEngineAdapter`.
1. **First, read the exact seam.** `grep -n "class EngineAdapter" -A 40
   src/vibey/application/interfaces/engines.py`. This lane implements every method that file
   declares beyond `descriptor`, `start`, `tail` and `release_diagnostics` (already done by
   `loops-service-adapter-run`). Wherever this spec's assumed signature differs from what `grep`
   shows, follow the actual declaration and say so in the commit body.
2. **`async def send_prompt(self, handle: RunHandle, text: str, *, now: bool) -> None`**:
   ```python
   command = RunControlCommand.PROMPT_NOW if now else RunControlCommand.PROMPT_AT_BREAK
   await self._publish_control(RunControl(run_id=handle.run_id, command=command, text=text, supersedes=None))
   ```
3. **`async def stop(self, handle: RunHandle, *, grace_seconds: float) -> StopSummary`** (or
   whatever return type `grep` shows -- `LoopProcessAdapter.stop` waits for and reads a
   `stop-summary.md`; this adapter must do the same, but the summary lives on the **shared
   volume**, not locally, so it can read it directly rather than asking the seat host for it a
   second time):
   ```python
   await self._publish_control(RunControl(run_id=handle.run_id, command=RunControlCommand.STOP, text=None, supersedes=None))
   summary, complete = await StopSummaryReader(self.descriptor).read(handle.run_dir, wait_seconds=grace_seconds)
   remaining_work: list[str] = []
   # (mirror whatever LoopProcessAdapter.stop does with `summary`/`complete`/`remaining_work`
   # from here on -- read that method's tail first with
   # `grep -n "async def stop" -A 40 src/vibey/infrastructure/engines/loop_process_adapter.py`
   # and copy its post-summary behaviour verbatim, since it is unchanged by ADR-0046.)
   ```
4. **`async def wind_down(self, handle: RunHandle) -> None`** (if `EngineAdapter` declares a
   separate wind-down method rather than folding it into `stop`):
   `await self._publish_control(RunControl(run_id=handle.run_id, command=RunControlCommand.WIND_DOWN, text=None, supersedes=None))`.
5. **`async def preflight(self, ...) -> ...`** and **`async def help_text(self, ...) -> ...`**
   (exact signatures from the grep of behaviour 1): these are **not** run-scoped -- they ask
   whether the engine can run at all, or what its own `--help` says -- so they are sent as
   `purpose=RunPurpose.PROBE` `RunRequest`s through `self._client.submit_and_wait`, not as
   `RunControl` commands (a probe has no prior route: build the request exactly as
   `loops-service-adapter-run`'s `start` does, but with `purpose=RunPurpose.PROBE`, `capture_output=True`,
   `deadline_seconds=self._config.doctor_probe_timeout_seconds`, `start_by=clock.now() +
   timedelta(seconds=self._config.probe_timeout_seconds)`, and `args` from whatever `descriptor`
   and the caller's arguments say `help_text`/`preflight` build locally today -- read
   `LoopProcessAdapter.help_text`/`.preflight` first to copy their argv-building unchanged). The
   probe's `RunResult.stdout` (when `capture_output=True`) is this adapter's return value's raw
   text, translated exactly as the local adapter would translate its own subprocess output.
6. **`async def _publish_control(self, control: RunControl) -> None`**: `await
   self._client.submit(RunControl.__class__` is not a `RunRequest`, so this cannot reuse
   `LoopClient.submit`'s `RunRequest`-only signature as written by `loops-client` -- **add one
   additive method to `LoopClient`**, `async def publish_control(self, loop_id: LoopId, control:
   RunControl) -> None`, which publishes `control` to `names.control_exchange()` keyed
   `names.control_keys(loop_id)[0]` (the loop's own key, never `"all"`: this adapter always
   targets one specific loop, the one its own `route_id`/`loop_id` already names) with
   `reply_to=None` -- a control command gets no reply; its effect is observed later, through the
   run's own `RunResult`. This adapter calls `await self._client.publish_control(self._loop_id,
   control)`.
7. Every method in this lane raises nothing new: a control command for a run this loop no longer
   holds (already finished, or its seat host restarted and forgot it) is silently a no-op on the
   broker side (`ControlConsumer` tries every host and none answers `True`); this adapter does not
   need to know whether the command actually reached anything; it only needs to publish it.

## Where to change
- **Preconditions.** Run the `grep` of behaviour 1 before writing anything, and
  `grep -n "async def stop" -A 40 src/vibey/infrastructure/engines/loop_process_adapter.py` to
  copy `stop`'s post-summary behaviour exactly.
- `src/vibey/infrastructure/loop_service/adapter.py` (`edit_file`, created by
  `loops-service-adapter-run`, now over 100 lines): append the methods of behaviours 2-6 to
  `ServiceEngineAdapter`, and add `RunControl`, `RunControlCommand`, `StopSummary` (if it exists;
  from step 3's grep) and `StopSummaryReader` to the file's imports.
- `src/vibey/infrastructure/loop_service/client.py` (`edit_file`): add `publish_control` (behaviour
  6) as one additional public method; every existing method and test of `LoopClient` stays
  unedited.
- `src/vibey/infrastructure/loop_service/interfaces/client_interface.py` (`edit_file`): add
  `publish_control` to `LoopClientInterface` with the same signature.
- **Fake.** `tests/fakes/loops.py`'s `FakeLoopClient` (lane `loops-client`) gains
  `self.controls: list[tuple[LoopId, RunControl]] = []` in `__init__` and
  `async def publish_control(self, loop_id: LoopId, control: RunControl) -> None:
  self.controls.append((loop_id, control))`, appended with `edit_file`.
- **New** test file `tests/infrastructure/loop_service/test_adapter_control.py`.

## Acceptance criteria
- [ ] `tests/infrastructure/loop_service/test_adapter.py` (lane `loops-service-adapter-run`)
      passes unedited.
- [ ] `send_prompt(..., now=True)` and `now=False` publish `PROMPT_NOW` and `PROMPT_AT_BREAK`
      respectively, each carrying the given text.
- [ ] `stop` publishes a `STOP` control and reads the same-shaped stop summary a subprocess
      adapter would, from the shared volume.
- [ ] `preflight`/`help_text` go over the bus as `PROBE` runs, not as control commands, and return
      the probe's captured output translated the same way the local adapter's own output is.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json`
      does not change; `tests/fakes/test_port_parity.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_adapter_control.py`. Build the adapter exactly as
`test_adapter.py` does, with a `FakeLoopClient`.
- `test_send_prompt_now_publishes_prompt_now`: `await adapter.send_prompt(handle, "hi", now=True)`
  → `client.controls == [(loop_id, RunControl(handle.run_id, RunControlCommand.PROMPT_NOW, "hi", None))]`.
- `test_send_prompt_at_break_publishes_prompt_at_break`: `now=False` → `PROMPT_AT_BREAK`.
- `test_stop_publishes_stop_and_reads_the_shared_summary`: write `stop-summary.md` under
  `handle.run_dir` containing the descriptor's done marker before calling `stop`; the one control
  published is `STOP`; the returned summary reflects the file's content, matching what
  `StopSummaryReader` alone would give for the same file.
- `test_stop_without_a_summary_times_out_like_the_local_adapter`: no `stop-summary.md`,
  `grace_seconds=0.2` → the same empty-summary behaviour `StopSummaryReader.read` documents.
- `test_wind_down_publishes_wind_down` (only if `EngineAdapter` declares it separately).
- `test_preflight_and_help_text_run_as_probes_not_controls`: a scripted probe result on the fake
  client → `client.controls == []` (nothing published as a control), and the adapter's return
  value matches the probe's captured `stdout`.
- `test_classes_satisfy_their_interfaces`: `isinstance(ServiceEngineAdapter(...), EngineAdapter)`
  still holds with every method now implemented; `isinstance(LoopClient(...), LoopClientInterface)`
  and `isinstance(FakeLoopClient(), LoopClientInterface)` after `publish_control` is added.

## Checks the lane must run (all must pass)
```bash
export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/application/test_conformance.py tests/fakes
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
git diff --stat HEAD~1 -- tests/infrastructure/loop_service/test_adapter.py
git status --short
```

## Out of scope
- `start`, `tail` and `release_diagnostics` (lane `loops-service-adapter-run`, unedited beyond the
  new imports this lane's methods need).
- The control consumer that receives these commands (lane `loops-control-and-dead-letters`,
  already landed) and `SeatHost.control` (lane `loops-seat-host-drain`, already landed).
- Building `ServiceEngineAdapter` instances for a pool (lane `loops-adapter-factory`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests
  are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow
  `EDITING-RULES.md`.

**Depends on:** `loops-service-adapter-run`.

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
