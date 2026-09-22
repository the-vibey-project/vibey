## Title
feat(provision): BUILD worktrees get a router file for the VS Code adapter's agent extension, and nested router paths are provisioned correctly

## Why
Every BUILD worktree gets one vibey-owned router file per engine, carrying the project's
non-negotiables and plugins between vibey's markers (`src/vibey/domain/provision.py:20-27`,
`RouterFile`: `CLAUDE.md`, `AGENTS.md`, `CURSOR.md`, `GEMINI.md`, `QWEN.md`; written by
`AgentSurfaceProvisioner.provision`, `src/vibey/infrastructure/provision/agent_surface.py:68-87`).
The VS Code adapter of ADR-0046 §8 (`specs/ADR-two-loops.md`, runner `vscodeloop`, run
directories under `.vscodeloop/runs/`) has none, so an agent driven through VS Code builds
without the guidance every other engine receives (7.b, `src/vibey_tools/gh/docs/doctrines.md:80`;
SD-01 §8, carried in the block by lane `gap-sd01-carriage`).

An agent extension reads its rules from a directory, not a top-level file, and the provisioner
cannot write one: it writes `worktree / router.value` without creating parents (`:71-77`), and
it registers only `path.name` in `.git/info/exclude` (`:85`), which for a nested file would
exclude every file of that name anywhere. Both are fixed here.

**Gated on `loops-vscode-verification`**, for the same reason as `gap-vscode-agent-tree`: the
router path is a fact about the extension V-VS2 records, not a preference a key could default.

## Required behaviour
1. Read the recorded V-VS2 result (lane `loops-vscode-verification`): the extension's
   workspace-relative rules directory and file suffix. Choose the router path
   `<rules_dir>/vibey<suffix>`. **Stop and report, changing nothing, if** the record names no
   rules directory, or says a rules file needs front matter (a marker block alone could not be
   a valid rules file; the operator decides).
2. `RouterFile` gains `VSCODE = "<rules_dir>/vibey<suffix>"`, and its docstring names the
   extension V-VS2 recorded.
3. `AgentSurfaceProvisioner.provision` (`agent_surface.py:68-87`):
   - before writing, `path.parent.mkdir(parents=True, exist_ok=True)`;
   - registers each written router by its worktree-relative POSIX path,
     `path.relative_to(worktree_path).as_posix()`, instead of `path.name` (`:85`). For today's
     top-level routers the registered text is unchanged.
4. `_ARTIFACT_PATTERNS` (`agent_surface.py:48-61`) gains `".vscodeloop/"` after `".qwenloop/"`:
   the runner's state directory is machinery, never product.
5. Re-provisioning an already-correct worktree still performs zero writes and no git calls.

## Where to change
- `src/vibey/domain/provision.py` (one member, edit_file).
- `src/vibey/infrastructure/provision/agent_surface.py` (edit_file).
- `tests/domain/test_provision.py`: `test_router_file_names_match_adr_0011` (`:21-28`) gains the
  new value in its expected set (edit_file).
- `tests/infrastructure/provision/test_agent_surface.py`: the two assertions that compare
  `{path.name for path in written}` with the members' values (`:42`, `:84`) compare
  `{path.relative_to(worktree).as_posix() for path in written}` instead (edit_file); then
  append the tests below.

## Acceptance criteria
- [ ] A fresh worktree gets the nested router file with vibey's block, and git status is clean.
- [ ] `.git/info/exclude` holds the router's relative path and `.vscodeloop/`, and not a bare
      `vibey<suffix>` line.
- [ ] Every other test in both files passes unchanged.
- [ ] 100% branch coverage of `src/vibey/domain/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
Append to `tests/infrastructure/provision/test_agent_surface.py`:
- `test_provision_creates_the_vscode_router_directory` -- after `provision`, `worktree / RouterFile.VSCODE.value` exists and contains `vibey:begin`.
- `test_nested_routers_are_excluded_by_their_relative_path` -- the exclude file has the exact line `RouterFile.VSCODE.value`, and a same-named file created elsewhere in the worktree still shows in `git status --porcelain`.
- `test_vscodeloop_state_is_excluded` -- `.vscodeloop/` is in the exclude file and a file under `.vscodeloop/runs/x/` is invisible to `git status`.
- `test_reprovisioning_with_the_nested_router_writes_nothing` -- a second `provision` returns `()`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_provision.py tests/infrastructure/provision
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The repository's own fifth tree (`gap-vscode-agent-tree`); the `vscodeloop` runner and its
  descriptors (ADR-0046 lanes); the block's content (SD-01: `gap-sd01-carriage`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(provision): a router file for the VS Code adapter's agent extension`. Do not push.

## Lane card
- **Depends on:** `loops-vscode-verification` (gate), `gap-sd01-carriage` (the block it writes
  carries SD-01).
- **Must keep passing unchanged:** every other test in `tests/infrastructure/provision/`,
  `tests/infrastructure/db/test_build_implement_end_to_end.py`, every protected test.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
