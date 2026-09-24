## Title
test(domain): an adversarial corpus against `MutationScope` — traversal and secret paths refused, and the sibling-prefix escape pinned as a strict xfail

## Why
Issue #301 (rewrite: `issue-audit/updates/301.md`, "Proposed child issues" 10), as in
`roadmap-301-adversarial-injection-suite-p1`. `src/vibey/domain/scope_guard.py` documents that
`MutationScope` "Enforces that mutations are confined within declared scope boundaries" (`:23`) and
refuses a path that "escapes worktree root or targets sensitive files" (`:86`); the sensitive set is
`_FORBIDDEN_FILE_RE` (`:16-21`). Probed on the integration tree (2026-09-22) with
`worktree_root="/work/proj"`: traversal, `.git`, `.env*`, `secrets.json` and SSH keys are refused,
but `/work/projX/evil.py` is **allowed** — `_resolve_relative` tests `p_str.startswith(self.worktree_root)`
(`:49-53`) with no path-separator boundary, so a sibling directory whose name extends the root's
passes. 10.f (`src/vibey_tools/gh/docs/doctrines.md:419`). Tests only.

## Required behaviour
New `tests/domain/test_adversarial_scope_guard.py` (provenance header copied from
`tests/domain/test_scope_guard.py:1`). `from vibey.domain.scope_guard import MutationScope, ScopeViolation`.
`ROOT = "/work/proj"`.

**Unscoped (`MutationScope(worktree_root=ROOT)`), refused (`is_path_allowed` False and
`validate_path` raises `ScopeViolation`):** `../x`, `a/../../x`, `/etc/passwd`,
`/work/proj/../proj2/x`, `.git/config`, `a/.git/hooks/pre-commit`, `.GIT/config`, `.env`,
`.env.local`, `config/.env`, `secrets.json`, `home/id_rsa`, `id_ed25519.pub`, `src\..\..\x`, `""`.

**Unscoped, allowed:** `src/a.py`, `/work/proj/src/a.py`, `src/./a.py` (normalised to `src/a.py`
by `validate_path`).

**Scoped (`allowed_paths=["src/"]`):** allowed `src/a.py`, `./src/b.py`, `src`; refused
`srcx/a.py` (prefix without a boundary is correctly refused here, `:79`), `src/../tests/a.py`,
`tests/a.py`.

**Known escape — `xfail(strict=True)` asserting it is refused:** `MutationScope(worktree_root=ROOT).is_path_allowed("/work/projX/evil.py") is False`
— reason: "an absolute path in a sibling directory whose name extends the worktree root passes
(scope_guard.py:51 checks startswith without a separator boundary)".

## Where to change
- New `tests/domain/test_adversarial_scope_guard.py` only. No production change.

## Acceptance criteria
- [ ] Every refused/allowed case passes; exactly one strict xfail reports `xfailed`.

## Tests to write first (TDD)
`test_traversal_and_secret_paths_are_refused` (parametrized), `test_paths_inside_the_root_are_allowed`,
`test_a_declared_scope_confines_mutation` (parametrized), `test_a_sibling_prefix_directory_is_refused`
(strict xfail).

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider -rx tests/domain/test_adversarial_scope_guard.py tests/domain/test_scope_guard.py

## Out of scope
- Fixing `_resolve_relative` (a later lane that flips the xfail); symlink resolution (the guard is
  pure and string-based by design). Docs. Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
