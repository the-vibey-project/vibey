## Title
ci(rulesets): the Arch Linux and macOS gates are required checks on develop and main

## Why
8.h (`src/vibey_tools/gh/docs/doctrines.md:326-333`) says a change that works on one default OS
but not the other "is not done". A check that is not required can be red on a merged PR. The
rulesets in `.vibey-gh.toml` (`[rulesets.integration]` `:137-142`, `[rulesets.release]`
`:157-163`) require `gates` and the no-loss suite, and name no OS check (`issue-audit/gaps.md` F4).
12.c keeps the rule declared. `.vibey-gh.toml:134-135` notes that the list also renders into
`automation-bootstrap.yml`, so `vibey-gh install` must re-render it.

The tenant rows are not added individually. There are about twenty, and requiring each makes
every tenant rename a ruleset change. The per-OS `gates` checks carry the root. The tenants'
OS rows stay visible, non-required checks. That split is a proposal: the operator can widen it
by adding names.

## Required behaviour
1. `.vibey-gh.toml`:
   - `[rulesets.integration] required_checks` becomes
     `["gates", "gates (Arch Linux)", "gates (macOS)", "No-loss property suite (10,000 examples)"]`,
     plus `"PostgreSQL 17 compatibility"` if `fakes-ci-no-services` added it.
   - `[rulesets.release] required_checks` gains the same two names, after `"gates"`.
   - The comment above `[rulesets.integration]` (`:126-135`) gains one sentence: the two OS
     gates are required under 8.h.
2. Re-render with `uv run vibey-gh install` at the root and in `src/vibey_tools/gh`. Keep only
   the changes to `.vibey-gh.toml` and the re-rendered `automation-bootstrap.yml` copies;
   revert anything else `install` touched.
3. Append a meta-test to `tests/meta/test_ci_default_os.py`:
   `test_both_rulesets_require_the_default_os_gates`. It loads `.vibey-gh.toml` with `tomllib`
   and asserts that both `required_checks` lists contain `"gates (Arch Linux)"` and
   `"gates (macOS)"`. It also asserts that those names equal the `name:` of the ci.yml jobs
   `gates-arch` and `gates-macos`, so a rename in one place fails here.

## Where to change
- `.vibey-gh.toml` (edit_file).
- The re-rendered `automation-bootstrap.yml` copies, by `vibey-gh install` only.
- `tests/meta/test_ci_default_os.py` (append).

## Acceptance criteria
- [ ] The new meta-test passes, and fails if either name is removed or the ci.yml job is renamed.
- [ ] `src/vibey_tools/gh/test/test_templates.py::test_repository_dogfoods_the_exact_rendered_workflows_and_hooks` passes after re-rendering.
- [ ] **Operator step, recorded:** after merge, `vibey-gh reconcile` (ADR-0036) applies the
      rulesets on GitHub. The reviewer records the reconciled ruleset JSON's `required_status_checks`.

## Tests to write first (TDD)
Append to `tests/meta/test_ci_default_os.py`:
- `test_both_rulesets_require_the_default_os_gates`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider test/test_templates.py

## Out of scope
- Requiring the tenant OS rows, the Forgejo ruleset profile (`gap-gh-forgejo-ruleset-profile-*`), and docs.

Commit as `ci(rulesets): require the Arch Linux and macOS gates`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
