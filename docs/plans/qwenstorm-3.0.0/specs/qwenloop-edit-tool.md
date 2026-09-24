## Title
feat(qwenloop): an edit_file tool, and write_file refuses to gut an existing file

## Why
qwenloop gives the model three tools: read_file, write_file, shell
(src/vibey_runners/qwen/src/qwenloop/infrastructure/inference.py:441-490, executed by
src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py `SandboxTools.execute`). `write_file`
replaces the whole file, and its description ("Write UTF-8 text to a file") does not say so. On
2026-09-22 a storm lane asked to add tests rewrote tests/cli/test_sovereign_provider_options.py and
deleted 450 of its 468 lines. A small local model cannot reliably reproduce a large file byte-for-byte;
it needs a targeted edit.

## Required behaviour
1. New tool `edit_file(path, old_string, new_string)`: reads the file (confined to the worktree by
   the same `_path` check as the other tools), counts exact occurrences of `old_string`:
   - 0 → `{"error": "old_string not found in <path>; read the file again and copy the text exactly"}`
   - more than 1 → `{"error": "old_string matches N times in <path>; include more surrounding lines"}`
   - exactly 1 → replace it, write the file, return `{"replaced": 1, "path": <path>}`.
   An empty `old_string` is an error. A missing file is an error (use write_file to create files).
2. `write_file` on an EXISTING file whose new content has fewer than half the old line count (when
   the old file has 40+ lines) returns
   `{"error": "write_file would remove X of Y lines from <path>; use edit_file for a targeted change, or pass allow_shrink=true if you mean to replace the file"}`
   and writes nothing, unless the call passes `"allow_shrink": true`. New files and ordinary
   rewrites are unaffected.
3. Tool descriptions say what each does: write_file "Create a file, or REPLACE an existing file's
   entire content"; edit_file "Replace one exact occurrence of old_string with new_string in an
   existing file — use this for changes to existing files".
4. The prompt strings that list the tools (src/vibey_runners/qwen/src/qwenloop/application/runner.py
   lines ~30, ~36, ~312) name edit_file, and runner.py:218 counts edit_file as a progress tool.

## Where to change
- inference.py `_CODING_TOOLS` (441-490): add the edit_file schema; update write_file's schema
  (optional boolean `allow_shrink`) and description.
- tools.py `SandboxTools.execute`: the edit_file branch and the write_file guard.
- runner.py: lines ~30, ~36, ~218, ~312.

## Acceptance criteria
- [ ] edit_file replaces exactly one occurrence and refuses 0, >1, empty, and missing-file cases.
- [ ] edit_file cannot touch a path outside the worktree.
- [ ] write_file refuses to shrink a 100-line file to 10 lines without allow_shrink, and allows it with.
- [ ] The tenant's gates pass at its 100% coverage floor.

## Tests to write first (TDD)
- New tests/test_tools.py (or extend the existing tools tests — search tests/ for SandboxTools):
  one test per acceptance item, using tmp_path worktrees.
- tests/test_inference.py: `_CODING_TOOLS` names read_file, write_file, edit_file, shell.
- tests/test_runner.py: an edit_file call counts as progress.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen
    python -m pytest -q -p no:cacheprovider
    python -m mypy --strict src/qwenloop
    cd ../../.. && uv run ruff check . && uv run ruff format --check .

## Out of scope
The request timeout (separate issue). Docs, CHANGELOG. Do not push. Commit as `feat(qwenloop): ...`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
