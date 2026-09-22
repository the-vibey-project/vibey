## Title
feat(qwenloop): SandboxTools takes its shell timeout, instead of 120 seconds in the code

## Why
`SandboxTools.execute` kills every shell command after a literal
`asyncio.wait_for(process.communicate(), timeout=120)`
(`src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py:60`). Sub-doctrine 12.c
(`src/vibey_tools/gh/docs/doctrines.md:455`) makes that a key; harness-T20a declared it. This lane
makes the sandbox take the value through its constructor, with today's value as the default, so
every existing caller is unchanged. The model-facing error stays exactly `"command timed out"`.

## Required behaviour
In `src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py`:
1. `SandboxTools.__init__(self, worktree: Path, *, allow_network: bool = False, shell_timeout_seconds: float = 120.0)`
   (`:10-12`). A value that is not finite or is ≤ 0 raises
   `ValueError("shell_timeout_seconds must be a positive number of seconds")`
   (`math.isfinite`). Keep it as `self.shell_timeout_seconds`.
2. `:60` becomes `await asyncio.wait_for(process.communicate(), timeout=self.shell_timeout_seconds)`.
   The timeout branch (`:61-64`) and its text `"command timed out"` are unchanged.

## Where to change
- `src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py` (with `edit_file`).
- `src/vibey_runners/qwen/tests/test_runner.py`: delete `test_sandbox_command_timeout` (`:660-683`, the
  `@pytest.mark.asyncio` line through `assert process.killed`), which reaches the timeout branch only by
  patching `asyncio.create_subprocess_exec`; append the two tests below, which cover the same branch with
  a real child (new imports go in the file's import block). The tenant loses one `monkeypatch.setattr`.

## Acceptance criteria
- [ ] `SandboxTools(tmp_path, shell_timeout_seconds=0.5)` answers `{"error": "command timed out"}` for `{"argv": [sys.executable, "-c", "import time; time.sleep(5)"]}`, in well under 5 s, with a real child process (no patching).
- [ ] `0`, `-1` and `float("nan")` are refused with `ValueError`.
- [ ] `SandboxTools(tmp_path).shell_timeout_seconds == 120.0`.
- [ ] `grep -c "monkeypatch.setattr" src/vibey_runners/qwen/tests/test_runner.py` is one less than before this lane.
- [ ] The tenant suite passes at its 100% floor, and its static gates pass.

## Tests to write first (TDD)
In `src/vibey_runners/qwen/tests/test_runner.py`, replacing `test_sandbox_command_timeout`:
- `test_sandbox_shell_timeout_is_configurable` (the real sleeper child above; assert the answer came back in under 3 s)
- `test_sandbox_rejects_a_non_positive_timeout` (parametrized: `0`, `-1`, `float("nan")`)

## Checks the lane must run (all must pass)
    (cd src/vibey_runners/qwen && uv run python -m pytest -q -p no:cacheprovider)
    (cd src/vibey_runners/qwen && uv run mypy --strict src/qwenloop && uv run lint-imports && uv run bandit -q -r src/qwenloop)
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Passing the configured value in (harness-T20). The other patches in `test_runner.py` and `test_notifications.py` (the tenant fakes lanes).
- Any vibey code. The storm driver.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** none (the default keeps every caller unchanged).
- **Files touched:** `src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py`, `src/vibey_runners/qwen/tests/test_runner.py`.
- **Shares a file with:** `tools.py` (qwenloop-edit-tool is integrated; none in flight).
- **Must keep passing unchanged:** the whole qwenloop suite at its 100% floor, and the protected root tests.
- **Registry (amendment A4):** nothing new; `SandboxTools` already implements the declared `ToolExecutor` port (`src/qwenloop/application/interfaces/__init__.py:51-52`).
- **Standing constraints (every qwenloop harness lane):**
  - This lane changes a runner tenant and runs that tenant's own gates (ADR-0022); qwenloop does not import vibey.
  - The tenant's in-memory fakes live in `src/vibey_runners/qwen/tests/fakes.py` (it exists; append to it, never recreate it).
  - Substitute only at a declared seam. Never add `monkeypatch.setattr`, `mock.patch` or `MagicMock`; a child of `sys.executable` is inside the default tier.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - No test needs a model server or waits longer than 5 s.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
