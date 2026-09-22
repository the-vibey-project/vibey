## Title
fix(gh): turn on `repository-profile.yml` — the repo-topics/description reconciler already built and tested, never installed

## Why
`.vibey-gh.toml`'s `[repository_profile]` table already declares this repository's
description and a 15-term topics list (its `enabled` field defaults to `True` —
`src/vibey_tools/gh/vibey_gh/config.py:1034-1055`, `RepositoryProfileConfig`). vibey-gh
already ships a complete, tested GitHub Actions workflow template that reconciles
exactly that data against the live repository —
`src/vibey_tools/gh/vibey_gh/templates/workflows/repository-profile.yml` — which, on
every successful `release-surfaces.yml` run (or manual dispatch), `gh api PATCH
repos/${REPO}` the description and Pages homepage, `gh api PUT repos/${REPO}/topics`
the topics list, sets vulnerability-alert/security-fix flags, reconciles branch
rulesets, and then verifies the live repository actually matches. It is covered by
`src/vibey_tools/gh/test/test_repository_profile.py` and
`src/vibey_tools/gh/test/test_templates.py:2225-2227`. This is precisely "GitHub repo
metadata as code" (sub-doctrine 12.c) — already built, already tested, and simply never
switched on for its own home repository.

The reason it is inert here: `.vibey-gh.toml`'s `[install] workflows` array — the list
`vibey-gh install` actually renders into `.github/workflows/` — is
`["merge-train.yml", "promote-to-main.yml", "provenance.yml", "release-surfaces.yml",
"pr-evaluate.yml", "pr-review.yml", "automation-bootstrap.yml", "github-release.yml",
"conventional-commits.yml"]`. `"repository-profile.yml"` is not in it, and no comment in
the file explains an intentional exclusion. Confirmed: `.github/workflows/` has no
`repository-profile.yml` (`ls .github/workflows/`). The result: the description and 15
topics declared in `.vibey-gh.toml` have reconciled nothing, ever, for this repository —
a search engine and a would-be adopter both see whatever description/topics (if any)
were last set by hand, not the ones this repository actually declares.

## Required behaviour
1. In `.vibey-gh.toml`'s `[install]` table, add `"repository-profile.yml"` to the
   `workflows` array (alongside the nine already listed — order does not matter to
   `vibey-gh install`, but append it last to keep the diff a pure addition).
2. Run `uv run vibey-gh install` (or the equivalent entry point this checkout's
   `vibey-gh` exposes — check `vibey_gh/cli.py`'s `install` subparser if `uv run
   vibey-gh install` is not it) from the repository root. This renders
   `.github/workflows/repository-profile.yml` from the template plus the now-updated
   config. Do not hand-write that file — it must be byte-for-byte what the installer
   renders, or `tools-lint`'s drift check fails it.
3. Commit both `.vibey-gh.toml` and the newly-created `.github/workflows/repository-profile.yml` together.
4. New `tests/meta/test_repository_profile_is_installed.py` asserting:
   - `.vibey-gh.toml`'s parsed `install.workflows` contains `"repository-profile.yml"`.
   - `.github/workflows/repository-profile.yml` exists and its content equals
     `vibey_gh.install.render_workflow(WORKFLOWS / "repository-profile.yml", load_config())`
     called against this repository's own root — i.e. the installed copy is not stale.
     Import `vibey_gh` the same way `src/vibey_tools/gh/test/test_repository_profile.py`
     does (`from vibey_gh import install`, `from vibey_gh.config import load_config`);
     this repository already has `src/vibey_tools/gh` on the path it uses for its own
     `vibey-gh` console script (`pyproject.toml`'s `[tool.hatch.build.targets.wheel]`
     entry `"src/vibey_tools/gh/vibey_gh" = "vibey_gh"`), so the import works the same
     way `tests/meta/test_adr_counts.py`-style meta-tests already reach into other
     tenants' code when needed — check for an existing precedent of a root `tests/meta`
     test importing `vibey_gh` before assuming the import path; if none exists, add
     `src/vibey_tools/gh` to that one test module's own `sys.path` rather than changing
     any shared configuration.

## Where to change
- `.vibey-gh.toml`: add one string to `[install] workflows`.
- Create `.github/workflows/repository-profile.yml` (via `vibey-gh install`, not by hand).
- Create `tests/meta/test_repository_profile_is_installed.py`. Copy the provenance
  header from `tests/meta/test_adr_counts.py:1`.

## Acceptance criteria
- [ ] `grep -c '"repository-profile.yml"' .vibey-gh.toml` is 1.
- [ ] `.github/workflows/repository-profile.yml` exists.
- [ ] `uv run vibey-gh install` run a second time in a row produces no further diff
      (the render is idempotent and already matches what is committed).
- [ ] `cd src/vibey_tools/gh && python -m pytest -q test/test_repository_profile.py test/test_templates.py -k repository_profile` still passes unmodified — this lane does not touch the template or its own tests, only the consuming repository's config.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_repository_profile_is_installed.py` passes.
- [ ] `git diff --stat` touches exactly `.vibey-gh.toml`, the new
      `.github/workflows/repository-profile.yml`, and the new test file.

## Tests to write first (TDD)
`tests/meta/test_repository_profile_is_installed.py`:
- `test_repository_profile_workflow_is_declared_for_install`: parse `.vibey-gh.toml`
  (via `vibey_gh.config.load_config` if importable, else a minimal `tomllib` read) and
  assert `"repository-profile.yml"` is in `install.workflows`.
- `test_installed_workflow_file_exists`: `.github/workflows/repository-profile.yml`.is_file().
- `test_installed_workflow_matches_a_fresh_render`: re-render the template against
  `load_config()` for this repository's own root and assert it equals the committed
  file's text exactly — the same "generate, then diff against what's committed" idiom
  `vibey-gh corpus-index --check` and `generate_llms_txt.py --check` already use
  elsewhere in this family.
- `test_repository_profile_is_enabled`: `RepositoryProfileConfig` parsed from this
  repository's `.vibey-gh.toml` has `enabled is True` (it is the dataclass default and
  nothing here overrides it — this test pins that fact so a future edit cannot silently
  flip it off).

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run vibey-gh install
    git status --porcelain .github/workflows/repository-profile.yml
    uv run pytest -q -p no:cacheprovider tests/meta/test_repository_profile_is_installed.py
    (cd src/vibey_tools/gh && python -m pytest -q test/test_repository_profile.py)

## Out of scope
- The template itself (`src/vibey_tools/gh/vibey_gh/templates/workflows/repository-profile.yml`)
  and its own package's tests — both are already correct and untouched by this lane.
- Changing `.vibey-gh.toml`'s `[repository_profile] description`/`topics` values — this
  lane only turns on the reconciler; `seo-pypi-metadata` is the lane that reads (not
  writes) the same `topics` list for `pyproject.toml`'s `keywords`.
- Any of the other eight already-installed workflows in `[install] workflows`.
- README.md, pyproject.toml, docs/, ADRs, CHANGELOG.md, and CLAUDE.md/AGENTS.md/GEMINI.md.

Commit as `fix(gh): install repository-profile.yml so declared repo metadata actually reconciles`.
Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
