## Title
feat(cli)!: DESIGN and DECOMPOSE default to the sovereign qwenloop provider

## Why
With qwenloop always on under sub-doctrine 8.b, `_resolve_provider` (src/vibey/cli/main.py:375-387)
should always choose the sovereign provider when no `--provider` is given. Today it returns
`"qwenloop"` only when `LocalEngineSettings(...).any_enabled`, else `"scripted"` — the scripted
fake is a test double, not a delivery path. The worker's unknown-provider message also omits
`opencode` (src/vibey/cli/main.py:1479), though `_PROVIDERS` (main.py:366) accepts it.

## Required behaviour
1. `_resolve_provider(explicit, config)` returns `explicit` when given, else `"qwenloop"`.
   Paid providers (`claudeloop`, `opencode` is not paid but is a stated choice) are never a default.
2. `vibey work --provider bogus` and `vibey worker --provider bogus` both exit 3 with
   `Error: provider must be 'scripted', 'claudeloop', 'qwenloop', or 'opencode'` (one shared
   message constant used by both commands).
3. The `--provider` help text (main.py ~368-372) states the default is `qwenloop`.
4. Nothing else about provider construction changes.

## Where to change
- src/vibey/cli/main.py:375-387 (`_resolve_provider`), ~368-372 (help text), ~1478-1480 and the
  `work` command's equivalent check (search for "provider must be").
- Tests that relied on the old `scripted` default must now pass `--provider scripted`
  explicitly (search tests/ for `invoke(app, ["work"` and `["worker"` without `--provider`).

## Acceptance criteria
- [ ] With no `--provider` and no local switch set, `work` and `worker` pick `qwenloop`.
- [ ] Both commands print the same four-provider error for an unknown provider.
- [ ] The chart is unaffected (deploy/helm/vibey/values.yaml sets `worker.provider: scripted`).
- [ ] Checks pass; cli/ stays at 100% branch coverage.

## Tests to write first (TDD)
- tests/cli/test_sovereign_provider_options.py: default is qwenloop with no switches; explicit
  scripted still honoured; unknown provider message lists all four, for both commands.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider tests/cli tests/system
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
Engine pool resolution (lane engines-pool), VISUAL_DESIGN provider (lane visual-design-provider),
docs. Do not push. Commit as `feat(cli)!: ...` with a `BREAKING CHANGE:` footer: "with no
--provider, DESIGN and DECOMPOSE use qwenloop on local Ollama instead of the scripted provider".

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
