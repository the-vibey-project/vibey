## Title
test(meta): the free path is the whole tool — a CI-checkable parity test for the Right to Full Capability

## Why
Issue #86 (rewrite: `issue-audit/updates/86.md`, Scope 7 and "Proposed child issues" 4): "a CI
test runs the free configuration and asserts it exercises every capability. No capability is gated
behind a paid flag." The rule is already ratified as Bill of Rights IV
(`src/vibey_tools/gh/docs/bill-of-rights.md:29-32`: "Every engineer receives the whole tool — free,
at full strength, forever … no capability built here, is ever degraded to make a paid tier look
better"), and sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:120-135`) makes the sovereign
engine always on and paid engines declared-only; `:136-137` makes the cloud default OpenStack.
Nothing checks it. Today the free defaults happen to hold:

- `src/vibey/domain/config.py:21` `DEFAULT_ENGINES = ("qwenloop", "opencode")`, and `_parse_engines`
  (`config.py:403-420`) always appends them; both descriptors are `EngineTier.LOCAL`
  (`src/vibey/infrastructure/engines/descriptors.py:242-289` and `:290-318`).
- `src/vibey/cli/main.py:380-389` `_resolve_provider(None) == "qwenloop"` (#322: DESIGN and
  DECOMPOSE default to the sovereign provider).
- `config.py:137-141` `DeployConfig.target = "openstack"`.

This lane pins those facts as a regression guard, so a future change that gates a capability
behind a paid declaration fails CI. It is independent of #86's blocked billing questions: it
tests capability, not billing. Tests only.

## Required behaviour
One new module `tests/meta/test_free_path_parity.py` (module-level test functions, with the reason
`tests/meta/test_protected_paths_agree.py:15-17` gives, in the module docstring). "The free
configuration" is `FREE = parse_config({})` (`vibey.domain.config.parse_config`, `config.py:652`):
a `vibey.toml` that declares nothing. Paid credentials are the environment names every paid
descriptor declares in `auth_env` — compute them as
`PAID_ENV = sorted({name for d in ALL_DESCRIPTORS if d.tier is EngineTier.PAID for name in d.auth_env})`
from `vibey.infrastructure.engines.descriptors.ALL_DESCRIPTORS` (`descriptors.py:413`); never
hard-code the list.

1. `test_the_always_on_engines_are_all_sovereign`: `FREE.engines.enabled` is non-empty, and for
   every id in it `BY_ENGINE_ID[EngineId(id)].tier is EngineTier.LOCAL`
   (`BY_ENGINE_ID`: `descriptors.py:415`).
2. `test_no_paid_engine_is_on_without_a_declaration`: no id in `FREE.engines.enabled` has a
   `PAID`-tier descriptor.
3. `test_design_and_decompose_default_to_a_sovereign_provider`:
   `BY_ENGINE_ID[EngineId(_resolve_provider(None))].tier is EngineTier.LOCAL`
   (`from vibey.cli.main import _resolve_provider`).
4. `test_the_default_cloud_is_the_sovereign_one`: `FREE.deploy.target == "openstack"`.
5. `test_every_command_is_present_and_answers_without_paid_credentials`: with
   `runner = typer.testing.CliRunner()` and `env = {name: None for name in PAID_ENV}` (a `None`
   value unsets the variable for the invocation), every top-level command
   (`app.registered_commands`) and every command of every sub-app (`app.registered_groups`, each
   `group.typer_instance.registered_commands`) is invoked as `[<group>?, <name>, "--help"]` and exits
   0. Non-vacuity: assert at least 22 command paths were exercised — the integration tree has 22
   `@…app.command` decorators in `src/vibey/cli/main.py` across `app` and its four sub-apps
   (`main.py:81-87`); a later lane that adds commands only raises the count.
6. The module docstring quotes Bill of Rights IV's first sentence and says the test must never be
   weakened to make a paid feature pass.

## Where to change
- New `tests/meta/test_free_path_parity.py` only (provenance header copied from
  `tests/meta/test_protected_paths_agree.py:1`). No production change: every assertion must PASS
  on the integration tree as it is. If one fails, stop and report it — do not change production code.

## Acceptance criteria
- [ ] The five tests pass on the current tree.
- [ ] Changing `DEFAULT_ENGINES` to include `"claudeloop"` (try it locally, then revert) makes
      test 2 fail; changing `_resolve_provider`'s default to `"claudeloop"` makes test 3 fail.
      Record both in the commit body; do not commit the probes.
- [ ] No network, no database: the module runs in the default tier.

## Tests to write first (TDD)
The five tests of Required behaviour are the deliverable:
`test_the_always_on_engines_are_all_sovereign`, `test_no_paid_engine_is_on_without_a_declaration`,
`test_design_and_decompose_default_to_a_sovereign_provider`,
`test_the_default_cloud_is_the_sovereign_one`,
`test_every_command_is_present_and_answers_without_paid_credentials`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider tests/meta/test_free_path_parity.py
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Billing, FOSS classification, metering and settlement (#86 children 1–3, 5, 6 are blocked on
  its open questions 1–4).
- The engine pool's contents (`engines-pool`, #321; gaps.md §A3; ADR-0046's rename lanes): this
  test states only that whatever is always on is sovereign, so it survives those lanes.
- Surface wiring (gaps.md §K2). Docs, CHANGELOG. Do not push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
