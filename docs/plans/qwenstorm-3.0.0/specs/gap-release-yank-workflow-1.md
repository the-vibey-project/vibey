## Title
feat(gh): `report-superseded --checklist-out` writes Article V.4's yank checklist as Markdown

## Why
Constitution V.4 (`src/vibey_tools/gh/docs/constitution.md:140-148`) says any ratified change to
the canon "immediately yanks all previous versions … where an index offers no yank API the
demand falls to the maintainer as their immediate next act". `vibey_gh/yank.py` already works
out the list, including governance detection (`governance_changed`, `SupersededReport.governance`).
It prints to the log only (`cli.py:473-521`). PyPI has no yank API (`yank.py:4-26`). Nothing
turns the list into a tracked task for the maintainer, and no workflow runs the command
(`issue-audit/gaps.md` L9). This lane makes the list a checklist. `-2` runs it after every
publish and opens the issue.

## Required behaviour
1. `vibey_gh/yank.py`: `SupersededReport` gains the method `checklist_markdown(self, version: str) -> str`.
   - It returns `""` when `self.superseded` is empty.
   - Otherwise it returns exactly these lines, joined with `\n`, with a trailing newline:
     ```
     ## Releases superseded by {version} on {index}

     {LAW}

     PyPI offers no yank API (see vibey_gh/yank.py), so each release is yanked by hand at {manage_url} — Options, Yank.

     - [ ] {v1}
     - [ ] {v2}
     ...
     ```
   - `{LAW}` is
     `"**Article V.4 — a ratified governance change.** Every previous release is named, zero exceptions, no retention window. This is the maintainer's immediate next act."`
     when `self.governance` is true. Otherwise it is
     `"Retention housekeeping: releases older than the configured keep window."`.
   - Versions follow `self.superseded`'s order.
   - `{index}` is `PyPI` for `pypi` and `TestPyPI` for `testpypi`.
2. `vibey_gh/cli.py`, the `report-superseded` parser (`:1469-1485`), gains
   `--checklist-out PATH` (default empty). `_report_superseded` writes
   `report.checklist_markdown(args.version)` to that path when both the path and the checklist
   are non-empty, then prints `vibey-gh: wrote the yank checklist to PATH`. It never writes an
   empty file; the workflow tests for the file's existence. The exit code stays 0 (`:519-521`).
3. There is no new class, so there is no new interface: this adds a method to an existing
   dataclass and an option to an existing command.

## Where to change
- `src/vibey_tools/gh/vibey_gh/yank.py` and `src/vibey_tools/gh/vibey_gh/cli.py` (edit_file).
- Tests: append to `src/vibey_tools/gh/test/test_yank.py`. Use `main([...])` with
  `--checklist-out tmp_path/…`, and substitute the index reader through whatever seam
  `test_yank.py` already uses for `released_versions`. Read the file first; if it patches, keep
  its pattern for this lane and say so in the commit body. The fakes-tenant-gh lanes own converting it.

## Acceptance criteria
- [ ] A governance report superseding `2.1.0`, `2.0.0` gives the exact Markdown with the Article V.4 line, both checkboxes and the manage URL.
- [ ] A non-governance report gives the housekeeping line.
- [ ] No superseded versions: no file is written, and the exit code is 0.
- [ ] `vibey-gh report-superseded … --checklist-out F` writes `F` and prints the path.
- [ ] vibey-gh's gates pass.

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_yank.py`:
- `test_checklist_names_article_v4_for_governance`
- `test_checklist_for_housekeeping`
- `test_empty_report_writes_no_checklist`
- `test_cli_writes_the_checklist_file`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Running it in `release.yml` and opening issues (`gap-release-yank-workflow-2`), the one-off yank for #392 (`gap-ops-yank-392`), and docs.

Commit as `feat(gh): report-superseded writes the Article V.4 yank checklist`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
