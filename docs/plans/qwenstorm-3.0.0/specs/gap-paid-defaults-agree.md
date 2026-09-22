## Title
test(meta): vibey's paid-defaults catalogue and vibey-gh's paid forge default can never disagree

## Why
Sub-doctrine 8.b's paid defaults (`src/vibey_tools/gh/docs/doctrines.md:188-194` at `d3b4a388`)
name GitHub as the default paid forge. That one fact now lives in two places, deliberately:
- vibey's pure catalogue, `vibey.domain.paid_defaults.PAID_DEFAULTS` (lane `gap-paid-defaults`),
  whose FORGE entry's `adapter` is `"github"` and whose declaration word is `PAID_DECLARATION = "paid"`;
- vibey-gh's `vibey_gh.config.PAID_DEFAULT_PLATFORM_KIND` and `PAID_PLATFORM_KIND` (lane
  `gap-gh-platform-paid`), because the tenant cannot import vibey (ADR-0022).

A second copy of a fact is allowed only with a written reason and a check that binds it (10.e,
`doctrines.md:417`; 12.c, `doctrines.md:455`). vibey's test suite can import `vibey_gh`, which ships
inside the one distribution (`pyproject.toml:209`, `:234`; precedent `tests/meta/test_paper_renders.py`
imports it). This lane is that check: a meta test that fails, naming both files, the moment either
copy moves alone.

## Required behaviour
1. New `tests/meta/test_paid_defaults_agree.py` holds the three tests below and nothing else.
2. Each assertion message names both sources, so a failure says what to change:
   `"vibey.domain.paid_defaults and vibey_gh.config disagree on 8.b's default paid forge; change both in one commit"`.
3. No production file changes.

## Where to change
- New `tests/meta/test_paid_defaults_agree.py`. Line 1 is the provenance header copied
  byte-for-byte from line 1 of `tests/meta/test_paper_renders.py`, then a one-paragraph module
  docstring saying why the fact is held twice (the text of *Why*'s second paragraph, shortened).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_paid_defaults_agree.py` passes.
- [ ] Temporarily editing `PAID_DEFAULT_PLATFORM_KIND` to `"gitlab"` in a scratch copy makes
      `test_both_name_the_same_default_paid_forge` fail with the message of behaviour 2 (the
      reviewer checks this by reading the assertion; do not commit the edit).
- [ ] `git diff --stat` names only the new test file.

## Tests to write first (TDD)
`tests/meta/test_paid_defaults_agree.py`, importing
`PAID_DECLARATION, PAID_DEFAULTS, PaidSurface` from `vibey.domain.paid_defaults` and
`PAID_DEFAULT_PLATFORM_KIND, PAID_PLATFORM_KIND, PlatformConfig` from `vibey_gh.config`:
- `test_both_name_the_same_default_paid_forge` —
  `PAID_DEFAULTS.default_for(PaidSurface.FORGE).adapter == PAID_DEFAULT_PLATFORM_KIND`.
- `test_both_speak_the_same_declaration_word` — `PAID_DECLARATION == PAID_PLATFORM_KIND`, and
  `PAID_DEFAULTS.declaration == PAID_PLATFORM_KIND`.
- `test_vibey_gh_resolves_the_declaration_where_vibey_says_it_goes` —
  `PlatformConfig(kind=PAID_DECLARATION).kind == PAID_DEFAULTS.resolve(PaidSurface.FORGE, PAID_DECLARATION)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider tests/meta
    cd src/vibey_tools/gh && python -m pytest -q

## Out of scope
- Changing either copy (`gap-paid-defaults`, `gap-gh-platform-paid`).
- The engines, IDE and cloud entries: they have one copy each, inside vibey.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `test(meta): vibey's paid defaults and vibey-gh's paid forge default agree`. Do not push.

## Lane card
- **Depends on:** `gap-paid-defaults`, `gap-gh-platform-paid`.
- **Files touched:** the new test file only.
- **Must keep passing unchanged:** every other `tests/meta` test.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
