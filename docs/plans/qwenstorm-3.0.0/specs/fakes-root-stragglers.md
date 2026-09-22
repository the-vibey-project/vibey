## Title
test(fakes): the last root patches and private doubles move onto declared seams, and the root baseline reaches zero

## Why
By this lane the fake families and seams all exist. A handful of root test files still patch,
mock or keep private copies. They are not big enough to justify a lane each:
- `tests/infrastructure/test_skills_context.py:154-180` assigns `AsyncMock()` to the private
  methods `compiler._ensure_index` and `compiler._run`, with `# type: ignore[method-assign]`.
  `VibeySkillsContextCompiler` runs a subprocess through its private `_run`.
- `tests/infrastructure/db/test_build_ledger.py:12,29` builds the ledger from `AsyncMock()`.
  `PostgresBuildLedger` takes a `LedgerRepositoryInterface` since `fakes-ledger`.
- `FakeProcess` ×4 (`tests/infrastructure/engines/test_claudeloop_decompose.py:17`,
  `test_claudeloop_design.py`, and the two opencodeloop twins) and `FakeChat`
  (`test_qwenloop_decompose.py`) are private doubles of `BoundedClaudeLoop` and its siblings
  (`src/vibey/infrastructure/interfaces/__init__.py`).
- Any other entry left in `tests/meta/patching_baseline.json` for a root file.

## Required behaviour
1. **Skills context.** Give `VibeySkillsContextCompiler` (`src/vibey/infrastructure/skills_context.py`)
   a constructor keyword `executor: CommandExecutor = AsyncSubprocessExecutor()` for what
   `_run` does today, and make `_run` call it. Tests pass a `ScriptedCommandExecutor`
   (`tests/fakes/process.py`), scripting the index build and the packet command. The `AsyncMock`
   assignments go. If `_ensure_index` does more than run a command, inject that too, by the
   same pattern.
2. **Build ledger.** `test_build_ledger.py` uses `InMemoryLedger` and asserts on
   `ledger.events`. It needs no database, so it moves out of the database directory (whose
   conftest marks items `integration`) to `tests/infrastructure/ledger/test_build_ledger_view.py`,
   with `git mv`, then the edits.
3. **Bounded loop doubles.** Add `ScriptedBoundedLoop` to `tests/fakes/engines.py`. It
   implements `BoundedClaudeLoop`, scripted by a list of responses, and records
   `(spec, web_search)`. Register it, since `BoundedClaudeLoop` is a driver seam: add it and
   its siblings to `DRIVER_SEAMS`. Replace `FakeProcess` in the two claudeloop test modules,
   and `FakeChat` if it fakes the same seam. The opencodeloop twins are left alone
   (opencode is retiring).
4. **Sweep the baseline.** For every remaining root entry in
   `tests/meta/patching_baseline.json`, convert the file onto the declared seam its patch
   stands in for. If no seam exists, stop and name it in the commit body, with the lane that
   should add it. The only entries allowed to remain carry a `"retiring"` reason:
   `tests/infrastructure/engines/test_opencodeloop_*.py`.
5. **Tighten the ratchet.** `tests/meta/test_patching_ratchet.py` gains
   `test_root_suite_patches_nothing_but_retiring_files`. It fails if any baseline
   entry lacks the `"retiring"` reason. The root ratchet only scans `tests/**`; tenants have
   their own.

## Where to change
- `src/vibey/infrastructure/skills_context.py` (constructor keyword).
- `tests/infrastructure/test_skills_context.py`, `tests/infrastructure/db/test_build_ledger.py`
  (moved to `tests/infrastructure/ledger/test_build_ledger_view.py`), `tests/infrastructure/engines/test_claudeloop_decompose.py`,
  `test_claudeloop_design.py`, `test_qwenloop_decompose.py`, and any file behaviour 4 finds.
- `tests/fakes/engines.py`, `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`,
  `tests/meta/test_patching_ratchet.py`.

## Acceptance criteria
- [ ] `python -c "import json; d=json.load(open('tests/meta/patching_baseline.json')); print([k for k,v in d.items() if v.get('reason')!='retiring'])"` prints `[]`.
- [ ] `grep -rn "AsyncMock\|MagicMock" tests --include=*.py | grep -v opencodeloop` prints nothing.
- [ ] 100% `infrastructure/` coverage.

## Tests to write first (TDD)
- `tests/fakes/test_fake_engines.py` (appended): `test_scripted_bounded_loop_returns_in_order_and_records`.
- `test_root_suite_patches_nothing_but_retiring_files`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/infrastructure
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Tenant suites (the tenant lanes). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-cli-operational-3`, `fakes-process-spawner`, `fakes-sockets`, `fakes-tui-system`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).
  - The ratchet's baseline may carry a `"reason"` key per entry. Extend the format in `test_patching_ratchet.py` if `fakes-registry` did not.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
