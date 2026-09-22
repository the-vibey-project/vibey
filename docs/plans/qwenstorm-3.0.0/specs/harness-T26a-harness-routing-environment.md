## Title
feat(test-harness): the environment overlay that routes an engine's pytest to the harness

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:274-276`) covers "a storm lane",
which is a model running `uv run pytest` through its shell. Draft ADR-0045 §10 routes that through
the pytest plugin (harness-T07, T17), which reads `VIBEY_HARNESS_ROUTE` from its environment, so every
engine vibey launches must carry the route in its environment. It also carries
`VIBEY_HARNESS_WAIT_SECONDS` below qwenloop's shell limit (`engine_wait_seconds`, default 110,
against the 120 s default of harness-T20's `shell_timeout_seconds`): a model then reads "still
running; run the same command again" instead of a killed command, and its retry is answered from
the record (ADR-0045 §11).

This lane computes that overlay from the settings (harness-T05: `route_engines`,
`engine_wait_seconds`); harness-T26b and T26 put it under every engine's environment.

## Required behaviour
Create `src/vibey/infrastructure/test_harness/routing_env.py`:
1. **`HarnessRoutingEnvironment(settings: TestHarnessSettingsInterface)`**.
   `overlay(self) -> dict[str, str]` returns:
   - `{}` when `settings.route_engines is TestRouteMode.OFF`;
   - otherwise `{"VIBEY_HARNESS_ROUTE": settings.route_engines.value, "VIBEY_HARNESS_WAIT_SECONDS": str(settings.engine_wait_seconds)}`.
2. **The interface** `src/vibey/infrastructure/test_harness/interfaces/routing_env_interface.py`:
   `@runtime_checkable` `HarnessRoutingEnvironmentInterface` (`overlay`).

## Where to change
- New `src/vibey/infrastructure/test_harness/routing_env.py` and its interface module.
- New `tests/infrastructure/test_harness/test_routing_env.py`.

## Acceptance criteria
- [ ] The overlay is empty when the mode is `off`, and carries both variables for `locked` and `queue`, with `engine_wait_seconds` as a string.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_routing_env.py` (`from vibey.infrastructure.test_harness import routing_env as rte`;
settings from `TestHarnessSettings.from_sources(<VibeyConfig with [test_harness] route_engines and engine_wait_seconds>, {"HOME": str(tmp_path)}, hostname="t")`):
- `test_overlay_table` (parametrized: `off`, `locked`, `queue`)
- `test_routing_env_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Putting the overlay into engine environments (harness-T26b, T26). Changing the default (harness-T28).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T05-test-harness-config.
- **Files touched:** the two new source files and the new test file.
- **Shares a file with:** none.
- **Must keep passing unchanged:** harness-T05's tests, and the protected tests.
- **Registry (amendment A4):** nothing. The overlay is a pure policy over the settings (`PURE_POLICY`).
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
