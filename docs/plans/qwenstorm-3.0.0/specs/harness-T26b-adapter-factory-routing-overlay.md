## Title
feat(engines): subprocess engine adapters take an overlay the engine's own keys override

## Why
Draft ADR-0045 §10: every engine vibey launches must carry the test-harness route in its
environment (harness-T26a computes the overlay). After ADR-0044's lane rmq-r28, every subprocess
engine adapter is built by `SubprocessAdapterFactory` (`LoopProcessAdapter(descriptor, env_overlay=...)`),
including the local engines, which today get their endpoint overlay at
`src/vibey/infrastructure/engines/local_engines.py:143-148` and after rmq-r28 through the factory.
So the factory is the one place to put a routing overlay **under** each adapter's own overlay: an
engine's own key of the same name always wins. With no routing overlay, every environment is
byte-identical to today's.

## Required behaviour
In rmq-r28's `SubprocessAdapterFactory` (find it with
`grep -rn "class SubprocessAdapterFactory" src/vibey/infrastructure/engines`):
1. The constructor gains the keyword `routing_overlay: Mapping[str, str] | None = None`
   (stored as a dict; `None` means empty).
2. Each adapter it builds gets `env_overlay = {**self._routing_overlay, **<the overlay it builds today>}`,
   so the adapter's own keys win.
3. Its interface (`EngineAdapterFactoryInterface`, rmq-r28) is unchanged: the overlay is a
   construction detail.

## Where to change
- The module holding `SubprocessAdapterFactory` (with `edit_file`).
- `tests/infrastructure/engines/test_adapter_factory.py` (rmq-r28's; append).

## Acceptance criteria
- [ ] With `routing_overlay={"VIBEY_HARNESS_ROUTE": "queue", "VIBEY_HARNESS_WAIT_SECONDS": "110"}`, a built adapter's launcher environment (rmq-r20's `EngineProcessLauncher.environment()`) contains both variables, for a paid and for a local engine.
- [ ] An engine overlay key of the same name wins over the routing overlay.
- [ ] With no routing overlay, the built adapters' overlays equal today's exactly.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Appended to `tests/infrastructure/engines/test_adapter_factory.py`:
- `test_routing_overlay_sits_under_the_engine_overlay`
- `test_no_routing_overlay_changes_nothing`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/system tests/live
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Composing the overlay in `bootstrap.py` (harness-T26). `ServiceAdapterFactory`: a loop service's
  runners get the route from the service's own environment (harness-T26).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** rmq-r28-invocation-selection (and through it rmq-r20's launcher).
- **Files touched:** the `SubprocessAdapterFactory` module and `tests/infrastructure/engines/test_adapter_factory.py`.
- **Shares a file with:** rmq-r28's module (it lands first).
- **Must keep passing unchanged:** `tests/infrastructure/engines/*` (including `test_loop_process_adapter.py` and `test_local_engines.py`), `tests/system/*`, `tests/live/**` (protected), every rmq-r27 and rmq-r28 test, and the protected tests.
- **Registry (amendment A4):** nothing new; `EngineAdapterFactoryInterface` is rmq-r28's seam.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - Substitute only at a declared seam (the constructor keyword). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out): no engine CLI is spawned.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
