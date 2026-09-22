## Title
feat(test-harness): vibey test-harness serve runs the machine's harness service, and drains on SIGTERM

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:271-277`): the harness runs as a
single instance per deployment, fed by a queue. Draft ADR-0045 §1 gives the `rabbitmq` backend's
instance a command a laptop or a chart can run: `vibey test-harness serve`, which starts the
service harness-T25b composes and drains on SIGTERM. It copies the worker's shutdown
(`src/vibey/cli/main.py:1515-1540`): install the handler first (`add_signal_handler`, `:1525`), then
release the SIGTERM latch armed at import (`:1537`), then act at once if the latch fired. The
latch's `release()` only restores the default disposition while its own handler is installed
(`src/vibey/cli/early_signals.py:64-86`), so the handler survives.

With T25b the composition may hold an AMQP connection, so the CLI commands that use a composition
also close it.

## Required behaviour
In `src/vibey/cli/test_harness.py` (add; do not rewrite):
1. **`TestHarnessServeCommand(*, composition_factory: Callable[..., TestHarnessCompositionInterface] = build_test_harness, latch: SigtermLatchInterface = SIGTERM_LATCH, config_loader: Callable[[Path], VibeyConfig] = load_config_from_path, after_start: Callable[[TestHarnessCompositionInterface], Awaitable[None]] | None = None)`**
   (`after_start` is a declared seam for tests and embedders; production passes nothing).
   - `request_stop(self) -> None` sets the stop event (what the signal handler calls).
   - `run(self, *, config: Path | None, environ: Mapping[str, str]) -> int`, via `asyncio.run(self._serve(...))`:
     1. build the composition (`composition_factory(<config>, environ, config_path=config)`) and
        `service = composition.service()`; `TestHarnessNotConfigured` echoes its message to stderr and returns 2;
     2. `await service.start()`; echo
        `test-harness started: instance=<settings.instance> queue=<names().request_queue()> state_dir=<settings.state_dir>`;
     3. `loop.add_signal_handler(signal.SIGTERM, self.request_stop)` and the same for `SIGINT`;
        then `self._latch.release()`; if `self._latch.fired`, `request_stop()` at once;
     4. if `after_start` is set, `await after_start(composition)`;
     5. wait for the stop event; then `await service.stop(grace_seconds=settings.run_bound_seconds)`
        and `await composition.aclose()`; return 0.
2. **Typer.** On `harness_app`, a command `serve [--config FILE]` whose module-level function finds
   `ctx.find_object(TestHarnessServeCommand) or TEST_HARNESS_SERVE` and raises `typer.Exit(code=...)`.
3. **Closing compositions.** `TestRunCommand` (harness-T15b) and `TestRequeueCommand`
   (harness-T16) call `await composition.aclose()` in a `finally` after their request.
4. **Interface**: `TestHarnessServeCommandInterface` (`run`, `request_stop`) in
   `src/vibey/cli/interfaces/test_harness_interface.py`.

## Where to change
- `src/vibey/cli/test_harness.py` and `src/vibey/cli/interfaces/test_harness_interface.py` (with `edit_file`).
- `tests/cli/test_test_harness_cli.py` (tests appended).

## Acceptance criteria
- [ ] `serve` starts, handles one request from the in-memory queue, and drains on a simulated SIGTERM, exiting 0: through `CliRunner` with `obj=TestHarnessServeCommand(composition_factory=lambda *a, **k: comp, latch=SigtermLatch(), after_start=<publish>)`, where `comp` is an `InMemoryTestHarnessComposition` and `<publish>` publishes a `TestRunRequest` to `comp.names().exchange()` on the routing key through `comp.amqp`, waits (at most 2 s) until `comp.store().answer(request_id)` exists, then calls the command's `request_stop()`.
- [ ] A latch that already fired stops the service at once and exits 0.
- [ ] `serve` without a URL (a composition whose `service()` raises `TestHarnessNotConfigured`) exits 2 with both remedies.
- [ ] `vibey test run --backend rabbitmq` with no URL exits 2 with the same message (through a real composition from `build_test_harness` on `tmp_path`, whose `client()` resolves `rabbitmq`).
- [ ] `TestRunCommand` closes its composition (`comp.closed` is `True` afterwards).
- [ ] 100% coverage of `src/vibey/cli/`.

## Tests to write first (TDD)
Appended to `tests/cli/test_test_harness_cli.py`. The latch is a fresh, never-armed `SigtermLatch()`
(no process signal disposition changes), or a plain in-test latch with `fired = True`:
- `test_serve_starts_handles_and_drains`
- `test_serve_stops_at_once_when_the_latch_fired`
- `test_serve_without_a_url_exits_2`
- `test_run_with_rabbitmq_backend_and_no_url_exits_2`
- `test_run_and_requeue_close_the_composition`
- `test_serve_command_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/cli tests/infrastructure/test_harness tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The chart (harness-T27a). `vibey install --rabbitmq` (rmq-r33).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T25b-test-harness-composition-amqp, harness-T16-test-inspect-cli.
- **Files touched:** `src/vibey/cli/test_harness.py`, `src/vibey/cli/interfaces/test_harness_interface.py`, `tests/cli/test_test_harness_cli.py`.
- **Shares a file with:** `cli/test_harness.py` (after harness-T16).
- **Must keep passing unchanged:** harness-T15b's, T15's and T16's tests, `tests/test_bootstrap.py`, `tests/cli/*`, and the protected tests.
- **Registry (amendment A4):** nothing new.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (`obj=` and constructor keywords). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`, and never send a real signal to the test process.
  - No lane needs a running RabbitMQ (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out). No test waits longer than 5 s.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
