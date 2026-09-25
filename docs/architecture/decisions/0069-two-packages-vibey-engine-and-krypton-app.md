# 0069 — Two packages, vibey-engine and krypton-app

**Status:** accepted · **Date:** 2026-09-25 · **Supersedes in part:** ADR-0037 (its single `vibey` distribution; its one-wheel-for-the-whole-family decision stands) · **Cites:** sub-doctrine 9.e, 12.c · **Related:** ADR-0028, ADR-0059, ADR-0065 · **Evidence:** `develop` at `30356862`, read 2026-09-25

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`, and a nav entry in `properdocs.yml`, all done in the change that
carries it.

## Context

On 2026-09-25 the operator ruled that the canon names exactly four names — `vibey` (the
project and its engine), `vibey-engine` (the engine's package), `krypton` (every app and
interface) and `krypton-app` (the apps' package) — and that only the two packages are
published, each by its own workflow. The operator registered the trusted publishers on
PyPI (environment `pypi`) and TestPyPI (environment `testpypi`):

- `vibey-engine`, published by `.github/workflows/vibey-engine.yml`;
- `krypton-app`, published by `.github/workflows/krypton-app.yml`.

No `vibey` package is published any more; on TestPyPI that name belongs to an unrelated
project. #1152 had already renamed `release.yml` to `vibey-engine.yml`, and it published
the engine as `vibey-engine` by rewriting `name = "vibey"` with `sed` in the runner, just
before the build.

## Decision

1. **`pyproject.toml` names the project `vibey-engine`.** The runner no longer renames
   anything: `vibey-engine.yml` only checks that the name is `vibey-engine`, and it refuses
   to build under these publishers if it is not.
2. **The importable packages and the console scripts are unchanged.** `vibey`, the twelve
   commands (`vibey`, `vibey-gh`, `claudeloop`, `gptossloop` and the rest) and the ten
   importable trees are exactly as ADR-0037 left them. Only the distribution's name
   changes.
3. **`krypton-app` is a real package** in `clients/krypton-app/`, with its own
   `pyproject.toml`, tests and version, and one command, `krypton`. For now it is an honest
   launcher: it starts `vibey serve` and opens the local web app once the engine provides
   one, and until then it says plainly that nothing was started and what is available
   instead, with exit status 1. It depends on `vibey-engine` and is not a uv workspace
   member, so it has no effect on `uv.lock`.
4. **`krypton-app.yml` mirrors `vibey-engine.yml`**: build (with its tests), then TestPyPI,
   then a verify job that installs that exact version from TestPyPI and runs `krypton`, on
   `develop`, and PyPI on `main`. It runs only when `clients/krypton-app/` or the workflow
   itself changes; a pull request runs the build job alone.
5. **vibey-gh's `[install] fallback_package` default is `vibey-engine`.** That is the
   package a rendered workflow or hook installs `vibey-gh` from when a repository has no
   copy of its own. Left at `vibey`, every adopter would keep installing the last `vibey`
   release forever.

## Why rename the project rather than the runner

The evidence, from this tree:

- **What the tree builds is what the index gets.** With the runner rename, `uv build` or
  `python -m build` on any checkout produced `vibey-2.1.0-py3-none-any.whl`, a package no
  index carries under that name, and only CI's copy was `vibey-engine`. After the rename, a
  local build yields `vibey_engine-2.1.0-py3-none-any.whl`, byte-for-byte the artifact the
  workflow publishes, and that is how this change's own install proof was made.
- **vibey-gh already compares the two names.** `fallback_pin.py` pins rendered workflows
  only when `[project] name` equals `[install] fallback_package`. With the name rewritten
  only in CI, the tree said `vibey` and the index said `vibey-engine`, and no value of the
  key could match both.
- **The lock is unaffected.** `uv lock` replaced the root entry `vibey` with `vibey-engine`
  (282 packages resolved, no version changed), and `uv lock --check` passes. The workspace
  members do not depend on the root project by name.
- **A self-referencing extra follows the project.** `bootstrap-all` already spells the
  Azure set out rather than naming `vibey[azure]`, because a runner-side rename made the
  self-reference resolve to somebody else's package. There is now nothing left to rename.

The cost is a breaking change for packagers and anyone who pinned `vibey`: they install
`vibey-engine` instead. The commands they run do not change.

## Consequences

- Every install instruction reads `pip install vibey-engine` (or `uv tool install
  vibey-engine`); `pip install krypton-app` adds the apps and brings the engine with it.
- `vibey-dev`, the TestPyPI name of the develop builds before #1152, is retired.
- vibey-gh's managed workflows re-render with `vibey-engine` as their fallback install.
- The CHANGELOG marks the rename BREAKING for packagers.
