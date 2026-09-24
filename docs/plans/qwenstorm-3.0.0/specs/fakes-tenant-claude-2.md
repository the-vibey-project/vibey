## Title
test(claudeloop): resume and the remaining CLI commands read the typer-context composition, and their tests patch nothing

## Why
After `fakes-tenant-claude-1`, the CLI patching left in claudeloop is in:
- `tests/cli/test_resume_cmd.py` (50): `claudeloop.cli.commands.resume.configure_logging` ×7,
  `bootstrap` ×7, `load_config` ×6, `resolve_most_recent` ×2 and `resume_explicit`;
- `tests/cli/test_cli_commands.py` (24);
- `tests/cli/test_backend_profiles_cli.py` (10);
- `tests/cli/test_app.py` (9).
These patch the same kind of names in other command modules under `claudeloop/cli/commands/`,
plus `shutil.which` ×2, `os.replace` and `shutil.copy`.

## Required behaviour
1. **`ClaudeloopComposition` gains** `resolve_most_recent` and `resume_explicit`, plus any other
   command-module collaborator that these four test modules patch. Name each one after the
   function it defaults to. It also gains `locator` (default `shutil.which`) and `fs`, a small
   `FileOps` interface with `replace(src, dst)` and `copy(src, dst)` over `os` and `shutil`.
   Each command module reads them through `current()`.
2. **Fakes** in `tests/application/fakes.py`:
   - a `ScriptedRunResolver`, holding a table of runs, for `resolve_most_recent` and `resume_explicit`;
   - `FakeExecutableLocator`;
   - `InMemoryFileOps`, over a dict of path to bytes, or `tmp_path`. Prefer real files under
     `tmp_path`: the file system is local. Use the fake only where a test must simulate an
     `OSError`.
   Register each new interface's fake.
3. **Switch the four test modules.** Every `patch` of a `claudeloop.cli.*` name, `shutil` or
   `os` goes. Lower the baseline.

## Where to change
- `src/claudeloop/cli/composition.py` and its interface; the command modules whose names the four test modules patch.
- `tests/application/fakes.py`, `tests/application/test_port_parity.py`, `tests/patching_baseline.json`,
  `tests/cli/test_resume_cmd.py`, `tests/cli/test_cli_commands.py`, `tests/cli/test_backend_profiles_cli.py`, `tests/cli/test_app.py`.

## Acceptance criteria
- [ ] `grep -cE "patch\(|monkeypatch.setattr" src/vibey_runners/claude/tests/cli/*.py` prints `0` for every file, apart from any baseline entry carrying a written reason.
- [ ] claudeloop's CI row passes.

## Tests to write first (TDD)
- `tests/cli/test_composition.py` (appended): `test_resume_collaborators_default_to_production`.
- Then convert one command's tests at a time.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/claude && python -m pytest -q
    cd src/vibey_runners/claude && mypy --strict src/claudeloop && lint-imports && bandit -q -r src/claudeloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- `claudeloop/infrastructure/*` (`fakes-tenant-claude-3`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-claude-1`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the protected root tests.
- **Standing constraints (every tenant lane):**
  - The tenant's own gates and floor pass on its Python floor (ADR-0022).
  - A fake is a plain class with real in-memory behaviour, and never `unittest.mock`.
  - Substitution happens at a declared seam: a constructor or keyword argument, a typer
    `ctx.obj`, or a parameter with a production default. It never happens by patching an
    import. `monkeypatch.setenv` and `delenv` stay allowed.
  - The tenant keeps its own registry and parity test and its own patching ratchet
    (`test_patching_ratchet.py` plus `patching_baseline.json`) in its test directory. Lower
    the ratchet for every file you convert, and never raise it.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - Protected root tests are never edited. Change existing files with `edit_file`, and never
    rewrite an existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
