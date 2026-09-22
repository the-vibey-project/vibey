## Title
refactor(engines)!: delete the OpenCode DESIGN/DECOMPOSE providers, and drop opencode from a VibeyProject

ADR-0046 lane L38b (slug `loops-retire-opencode-infra`).

## Why
ADR-0046 §9 (`specs/ADR-two-loops.md:290-293`): after `vscode` passes live conformance, L38
"takes `opencode` out of the defaults, the providers and the descriptors … The CRD keeps the
value, so that stored custom resources stay valid, and the operator handler drops it with a
warning." Lane `loops-retire-opencode-refusals` already refuses `--provider opencode` and
`opencode` in config, so the three provider modules are now unreachable code. This lane deletes
them and their seams, and makes the operator drop a stored CR's `opencode`. The descriptor,
classifier, event map and enum member go in lane `loops-retire-opencode-id`, together, because
the suite requires every `EngineId` member to have all of them
(`tests/infrastructure/engines/test_descriptors.py:39-42`, `test_classify.py:24-54`,
`test_loop_events.py:378-384`, integration `d3b4a388`).

## Required behaviour
0. **Gate (ADR-0046 §9: live conformance first).** Unless
   `grep "V-VS CONFORMANCE: PASS" /private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`
   prints a line naming Arch Linux and a line naming macOS, change nothing and report
   `gated: vscode has not passed live conformance on both OSes`.
1. **Delete** (with `git rm`):
   - `src/vibey/infrastructure/engines/opencodeloop_design.py`
   - `src/vibey/infrastructure/engines/opencodeloop_decompose.py`
   - `src/vibey/infrastructure/engines/opencodeloop_process.py`
   - `src/vibey/infrastructure/engines/interfaces/opencodeloop_design_interface.py`
   - `src/vibey/infrastructure/engines/interfaces/opencodeloop_decompose_interface.py`
   - `tests/infrastructure/engines/test_opencodeloop_design.py`
   - `tests/infrastructure/engines/test_opencodeloop_decompose.py`
   - `tests/infrastructure/engines/test_opencodeloop_process.py`
2. **Seams**: `src/vibey/infrastructure/interfaces/__init__.py` loses the `TYPE_CHECKING` import
   of `OpenCodeLoopResult` (`:56-58`), the `BoundedOpenCodeLoop` Protocol (`:66-68`) and its
   `__all__` entry (`:78`); `src/vibey/infrastructure/engines/interfaces/__init__.py` loses
   every export of the two deleted interface modules. Remove any registry entry for those seams
   in `tests/fakes/registry.py` (EXEMPT, PENDING or REGISTRY).
3. **Operator** (`src/vibey/infrastructure/operator/handlers.py`, `_project_config`, `:53-67`):
   when `spec.engines` names `opencode`, it is dropped from the list written to
   `config["engines"]`, and one warning is logged per handled resource:
   `"opencode was retired (sub-doctrine 8.b, ADR-0046 §9); dropped from spec.engines of <name>"`.
   An `engines` list that becomes empty is omitted, exactly as an empty `spec.engines` is today
   (`:61-62`). The CRD enum still accepts `opencode` (stored resources stay valid).
4. Nothing else changes: the `OPENCODE` descriptor, `_classify_opencode`, the fixtures and the
   event map stay until `loops-retire-opencode-id`.

## Where to change
- The deletions in behaviour 1; `src/vibey/infrastructure/interfaces/__init__.py`;
  `src/vibey/infrastructure/engines/interfaces/__init__.py`; `src/vibey/infrastructure/operator/handlers.py`;
  `tests/fakes/registry.py` (only if it names a deleted seam).
- New test: `tests/infrastructure/test_opencode_retired.py`.

## Acceptance criteria
- [ ] `grep -rn "opencodeloop_design\|opencodeloop_decompose\|opencodeloop_process\|BoundedOpenCodeLoop\|OpenCodeLoopResult" src tests` prints nothing.
- [ ] A VibeyProject with `spec.engines: [claudeloop, opencode]` yields `config["engines"] == ["claudeloop"]` and the warning; `[opencode]` alone yields no `engines` key.
- [ ] The rest of the suite passes; 100% branch coverage on `infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_opencode_retired.py`:
- `test_operator_drops_opencode_from_spec_engines_with_a_warning` (calls `_project_config`
  directly; the warning asserted with `caplog`)
- `test_operator_omits_engines_when_only_opencode_was_listed`
- `test_the_opencode_provider_modules_are_gone` (`importlib.util.find_spec` is None for the three module paths)
- `test_the_opencode_loop_seam_is_gone` (`not hasattr(vibey.infrastructure.interfaces, "BoundedOpenCodeLoop")`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure tests/fakes tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The descriptor, classifier, fixtures, event map, argv goldens and the `EngineId` member
  (`loops-retire-opencode-id`); the tenant (`loops-remove-opencode-tenant`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject and a
  `BREAKING CHANGE:` footer: "the OpenCode DESIGN/DECOMPOSE providers are removed; a
  VibeyProject's spec.engines entry opencode is dropped with a warning".

**Depends on:** `loops-retire-opencode-refusals`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
