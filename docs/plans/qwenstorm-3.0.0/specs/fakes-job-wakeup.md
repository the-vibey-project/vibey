## Title
test(cli): the CLI takes its composition from the click context, and the job wakeup, handler factory and handlers get in-memory fakes

## Why
`tests/cli/test_operational_commands.py` patches
`vibey.infrastructure.db.notifier.PostgresJobReadyNotifier` 26 times. That is the most
repeated import patch in the root suite, and exactly what sub-doctrine 9.b forbids.

After lane `rmq-r02-wakeup-composition`, `vibey worker` gets its notifier from
`await resources.wakeup.open()` (`AppResources.wakeup: JobWakeupOpenerInterface`). R02 kept a
call-time import only so that those patches would keep working. The CLI still has no
declared seam through which a test can hand it a different composition: all 20 sites in
`src/vibey/cli/main.py` read `async with build_app() as resources:`.

`fakes-registry` lists `JobReadyNotifier`, `JobHandlerFactory` and `JobHandler`
(`application/interfaces/queue.py:66-87`) as `PENDING` under this lane.

Click already provides the seam. `CliRunner.invoke(app, args, obj=...)` puts an object on the
root context, and `click.get_current_context().find_object(T)` finds it from any command.
That is substitution at a declared seam with no import patched.

## Required behaviour
1. **`src/vibey/cli/composition.py` — `class CliComposition`**, with
   `src/vibey/cli/interfaces/composition_interface.py` (`CliCompositionInterface`) beside it:
   - `__init__(self, *, open_app: Callable[[], AbstractAsyncContextManager[AppResources]] | None = None)`,
     where the default is `vibey.bootstrap.build_app`;
   - `open_app(self) -> AbstractAsyncContextManager[AppResources]`;
   - `@classmethod current(cls) -> CliComposition` returns
     `ctx.find_object(CliComposition)` when `click.get_current_context(silent=True)` gives a
     context and the lookup finds one. Otherwise it returns `CliComposition()`.
   - Later lanes add more factories to this class (`fakes-cli-composition`).
2. **`src/vibey/cli/main.py`**: every `async with build_app() as resources:` (20 sites) becomes
   `async with CliComposition.current().open_app() as resources:`. Use one checked
   replacement: assert that the count is 20 before replacing. Remove `build_app` from the
   import at `:32` if nothing else uses it.
3. **`cli/ledger_search.py:155` and `cli/ledger_publication.py:134`**: the `open_app` default
   becomes `_composed_app`. That is a module function, with this reason at its definition:
   "resolves the CLI composition at call time, so the module-level command singletons honour
   the context". Its body is `return CliComposition.current().open_app()`.
4. **`tests/fakes/queue.py`**:
   - `InMemoryJobReadyNotifier` (`JobReadyNotifier`):
     - `wait_for_job_ready(project_id, *, timeout)` waits on a fresh `asyncio.Future`
       registered for that project, bounded by `timeout.total_seconds()`. It returns `True`
       when notified, and `False` on timeout. The waiter is always removed afterwards.
     - `notify(project_id)` resolves the project's current waiters and returns how many it
       woke. A notification with no waiter is not buffered, as with `LISTEN`
       (`db/notifier.py:34-38`). It is counted in `self.missed`.
     - `InMemoryQueueStore(on_ready=notifier.notify)` wires it to the fake queue.
   - `InMemoryJobWakeupOpener` (`JobWakeupOpenerInterface` from R02):
     - `open()` returns its notifier and increments `opened`;
     - `close(notifier)` increments `closed`.
   - `ScriptedJobHandler` (`JobHandler`) returns its outcomes in order, repeats the last one,
     and records each job in `handled`.
   - `FakeJobHandlerFactory` (`JobHandlerFactory`) maps `job.kind` to a handler, or to a
     default. `create` records `(job.id, job.kind)`, and an unknown kind with no default
     raises `LookupError`.
5. **Registry.** Register the four fakes. Add `JobWakeupOpenerInterface` to `DRIVER_SEAMS`.
   Delete the three `PENDING` lines.
6. **Replace the 26 notifier patches** in `tests/cli/test_operational_commands.py`:
   - Add a helper class `_ComposedWithFakeWakeup` in the test module. Its `open_app()`
     enters the real `build_app()`, and yields
     `dataclasses.replace(resources, wakeup=InMemoryJobWakeupOpener(notifier))`.
   - Each test invokes with `runner.invoke(app, [...], obj=CliComposition(open_app=helper.open_app))`.
   - Assertions on the patched mock (`connect` called, `close` awaited) become assertions on
     the opener's `opened` and `closed`.
   These tests still use PostgreSQL through the real `build_app()`, and stay `integration`.
   `fakes-cli-operational-*` moves them off it.
7. Lower the file's `patch` and `mock` counts in `tests/meta/patching_baseline.json` by what
   was removed.

## Where to change
- New `src/vibey/cli/composition.py`, `src/vibey/cli/interfaces/composition_interface.py`.
- `src/vibey/cli/main.py`, `src/vibey/cli/ledger_search.py`, `src/vibey/cli/ledger_publication.py`.
- `tests/fakes/queue.py`, `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`,
  `tests/cli/test_operational_commands.py`.
- New `tests/cli/test_composition.py`, `tests/fakes/test_fake_wakeup.py`.

## Acceptance criteria
- [ ] `grep -c 'PostgresJobReadyNotifier' tests/cli/test_operational_commands.py` prints `0`.
- [ ] `grep -c 'build_app()' src/vibey/cli/main.py` prints `0`.
- [ ] `CliComposition.current()` outside any click context returns a default composition.
      Under `CliRunner.invoke(..., obj=c)` it returns `c`.
- [ ] 100% `cli/` coverage. The registry has no `PENDING` entry naming `fakes-job-wakeup`.

## Tests to write first (TDD)
- `tests/cli/test_composition.py`:
  - `test_current_defaults_outside_a_context`
  - `test_current_finds_the_object_the_runner_passed` (a tiny typer app)
  - `test_the_composition_satisfies_its_interface`
- `tests/fakes/test_fake_wakeup.py`:
  - `test_notify_wakes_a_waiter`
  - `test_wait_times_out_and_cleans_up`
  - `test_a_notification_with_no_waiter_is_missed_not_buffered`
  - `test_the_fake_queue_announces_through_the_notifier`
  - `test_handler_factory_routes_by_kind`
  - `test_scripted_handler_repeats_its_last_outcome`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The other patches in `test_operational_commands.py`: `PostgresLocalService`, `shutil.which`,
  `subprocess.run`, the dashboard apps, `asyncio.sleep`, `SIGTERM_LATCH` and `operator.run`
  (`fakes-cli-composition`).
- Taking these tests off PostgreSQL (`fakes-cli-operational-1..3`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-queue-gates`, **`rmq-r02-wakeup-composition`** (it adds `AppResources.wakeup`).
- **Files touched:** see *Where to change*.
- **Shares a file with:** `src/vibey/cli/main.py`. R02, R17, R27, R28, R33 and T15 edit other
  parts of it; this lane only replaces the 20 `build_app()` lines and one import.
- **Must keep passing unchanged:** `tests/test_bootstrap.py` (R02's opener tests) and the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
