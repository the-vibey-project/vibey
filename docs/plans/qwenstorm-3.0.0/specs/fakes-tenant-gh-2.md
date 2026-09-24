## Title
test(vibey-gh): the merge train, PR automation and issue automation take their forge through the transport, and their tests patch nothing

## Why
The merge train is how every feature PR reaches `develop` (ADR-0028). Its tests replace the
train's own functions:
- in `test/test_gh_cli.py`: `merge_train.open_pull_requests` ×17, `merge_train.judge` ×13,
  `merge_train._gh_json` ×5, and `merge_train.merge` ×2 (`:213-280`, and more);
- in `test/test_pr_automation.py`: `pr_automation.fetch_pr` ×10, `pa.upsert_state` ×5, and
  `subprocess` ×11;
- in `test/test_issue_automation.py`: `subprocess` ×2 and the module's own functions.

`vibey_gh/merge_train.py` runs `gh` through its own `_gh_json` (`:67`) and `_gh` (`:76`).
`gh_transport.py`'s docstring names these as "its twin" and the source of `probe`'s shape.
They have not moved onto the transport yet.

`fakes-tenant-gh-1` added `ScriptedGhTransport` and `ScriptedGitRunner`.

## Required behaviour
1. **The merge train.** `vibey_gh/merge_train.py` becomes
   `class MergeTrain(gh: GhTransportInterface = GhTransport(), git: GitRunnerInterface = GIT)`,
   with an interface beside it in `vibey_gh/interfaces/merge_train_interface.py`:
   - `open_pull_requests`, `judge`, `merge` and the train's run become methods;
   - `_gh_json` and `_gh` become `self._gh.json(...)` and `self._gh.probe(..., strip=False, with_stderr=True)`,
     byte-for-byte the shapes `gh_transport.py:1-15` documents;
   - keep module-level aliases bound to `TRAIN = MergeTrain()` for the CLI and for any
     importer, with a comment saying why.
2. **PR automation and issue automation**, by the same pattern: `class PrAutomation(gh=..., git=...)`
   and `class IssueAutomation(gh=...)`, with interfaces beside them. Every `subprocess.run`
   of `gh` or `git` in those modules goes through the injected transport or runner. The
   evaluate and review gates (#317) keep their exact outputs.
3. **The CLI** (`vibey_gh/cli.py`) builds the default instances in one place, and passes them
   to the subcommands. Tests call the command functions with instances built over
   `ScriptedGhTransport` and `ScriptedGitRunner`. If the CLI is argparse-based, add the
   instance as a keyword parameter of the handler functions it dispatches to. No global is
   replaced in a test.
4. **Switch the tests.** `test_gh_cli.py`'s merge-train tests, `test_pr_automation.py` and
   `test_issue_automation.py`:
   - every `monkeypatch.setattr` on `merge_train`, `pa`, `pr_automation`, `issue_automation`
     or `subprocess` goes;
   - a scripted transport answers `gh pr list --json …`, `gh pr view`, `gh pr merge`,
     `gh api …`, exactly as the replaced lambdas did;
   - lower the baseline.
5. Register the new classes' collaborators' fakes in `test/test_port_parity.py`. The classes
   themselves are class contracts, and belong in `EXEMPT`.

## Where to change
- `vibey_gh/merge_train.py`, `vibey_gh/pr_automation.py`, `vibey_gh/issue_automation.py`, `vibey_gh/cli.py` (the dispatch sites), and three new interface files.
- `test/test_gh_cli.py`, `test/test_pr_automation.py`, `test/test_issue_automation.py`, `test/test_port_parity.py`, `test/patching_baseline.json`.

## Acceptance criteria
- [ ] `grep -cE "monkeypatch.setattr\((merge_train|pa|pr_automation|issue_automation|subprocess)" src/vibey_tools/gh/test/test_gh_cli.py src/vibey_tools/gh/test/test_pr_automation.py src/vibey_tools/gh/test/test_issue_automation.py` prints `0` for each.
- [ ] `(cd src/vibey_tools/gh && python -m pytest -q)` passes at 100%. The merge train's CLI output is byte-identical in every existing assertion.
- [ ] black, isort and mypy pass. The managed-automation drift check passes.

## Tests to write first (TDD)
- `test/test_merge_train.py` (new, or append if it exists):
  - `test_train_reads_open_prs_through_the_transport`
  - `test_train_merge_uses_the_probe_shape`
  These pin the transport shape before the conversion.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The remaining modules (`fakes-tenant-gh-3`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-gh-1`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the merge train's behaviour (`vibey-gh merge-train` output), and the protected root tests.
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
