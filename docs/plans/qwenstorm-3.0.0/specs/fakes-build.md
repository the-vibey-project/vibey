## Title
test(fakes): the BUILD phase's ports — worktrees, provisioner, gates, integration branch and lock, skills, budget — get shared fakes

## Why
`fakes-registry` lists nine BUILD ports as `PENDING` under this lane
(`application/interfaces/build.py:37-104`): `BudgetSource`, `SkillsContextCompiler`,
`BuildProvisioner`, `BuildWorktrees`, `GateRunner`, `IntegrationBranch`, `IntegrationLock`,
`VerifyWorktrees` and `WorkPlanProducer`.

The BUILD handler tests fake them privately, 15 classes in three files:
- `tests/application/test_build_implement_handler.py`: `FakeLedger`, `FakeProvisioner`,
  `FakeWorktrees`, `_FakeSkillsContext`, `_RecordingWindDown`;
- `test_build_integrate_handler.py`: `FakeGateRunner`, `FakeIntegration`,
  `FakeIntegrationLock` (`:243-253`), `FakeLedger`, `FakeTransitioner`;
- `test_build_verify_handler.py`: `FakeGateRunner`, `FakeLedger`, `FakeWorktrees`.

`FakeIntegrationLock` answers whatever it was told (`available`). The real lock
(`db/advisory_lock.py:28-54`) refuses a second holder of `(project_id, cycle)`, even on the
same instance (`:33-37`). A handler that forgets to release would pass every test.

## Required behaviour
`tests/fakes/build.py`:
1. **`InMemoryIntegrationLock`** (`IntegrationLock`):
   - `held: set[tuple[UUID, int]]`, plus `acquired` and `released` lists;
   - `try_acquire` returns `False` when the key is held, and otherwise adds it and returns `True`;
   - `release` of a key that is not held is a no-op, as the real one is (`:49-52`);
   - `contend(project_id, cycle)` marks a key held by "another worker", so that tests can
     script contention.
2. **`InMemoryWorktrees`** (`BuildWorktrees` and `VerifyWorktrees`):
   - `root: Path`, passed in, usually `tmp_path`;
   - `create(item_id, base_ref="HEAD")` makes `root / item_id`, records
     `(item_id, base_ref)` in `created`, and returns the path. Creating an item a second time
     returns the same path and records nothing new;
   - `path_for(item_id)` returns `root / item_id` whether or not it exists, as the real
     `VerifyWorktrees` does. Check `infrastructure/git/worktree_manager.py` and match it.
3. **`RecordingProvisioner`** (`BuildProvisioner`). `provision(worktree_path, spec)` records
   the call, writes each file the `ProvisionSpec` names under `worktree_path` (read
   `domain` or `application/dto` for `ProvisionSpec`), and returns the paths written.
4. **`ScriptedGateRunner`** (`GateRunner`):
   - `results: dict[tuple[str, ...], GateResult]`, and `default: GateResult`, which passes
     unless it is set otherwise;
   - `run(argv, *, cwd)` records `(argv, cwd)` in `ran` and returns the scripted result;
   - `fail(argv, stdout="", stderr="")` is a helper that scripts a failure.
5. **`InMemoryIntegrationBranch`** (`IntegrationBranch`):
   - `ensure()` creates and returns `root / "integration"` and counts calls;
   - `merge_item(item_id)` returns the scripted `MergeOutcome` for that item, or a clean
     merge by default, and records the item in `merged`. Merging the same item twice returns
     the first outcome again. The real merge is idempotent on an already-merged branch; check
     `infrastructure/git/integration_branch.py` and match it.
6. **`ScriptedSkillsContext`** (`SkillsContextCompiler`) returns the `SkillsContextResult` it
   was given, and records `(job.id, worktree_path)`.
7. **Registry.**
   - The six classes above, for their ports.
   - `BudgetSource → LedgerBudgetSource(<its real constructor arguments>, ledger=InMemoryLedger())`:
     the real class over the in-memory ledger (`application/budget_source.py:49-110`).
   - `WorkPlanProducer → ScriptedWorkPlanProducer()` (production, `infrastructure/engines/scripted_decompose.py:19`).
   - Delete the nine `PENDING` lines.
8. **Switch the three BUILD test modules.** Delete their private doubles, and use the shared
   fakes plus:
   - `build_ledger(InMemoryLedger())` from `tests/fakes/ledger.py`;
   - `InMemoryProjectRepository` from `tests/fakes/projects.py` in place of `FakeTransitioner`.
     The test creates the project in the expected phase first.
   `_RecordingWindDown` stays if it records a callable collaborator that is not a port.
   Otherwise replace it.

## Where to change
- New `tests/fakes/build.py`, `tests/fakes/test_fake_build.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`,
  `tests/application/test_build_implement_handler.py`, `test_build_integrate_handler.py`,
  `test_build_verify_handler.py`.

## Acceptance criteria
- [ ] `test_lock_contention_defers_instead_of_merging` now scripts contention with
      `InMemoryIntegrationLock.contend(...)`, and still asserts `Defer`.
- [ ] A new test shows that a handler which forgets to release blocks the next `try_acquire`,
      which is the behaviour the old fake hid.
- [ ] The registry has no `PENDING` entry naming `fakes-build`.
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/application` passes.

## Tests to write first (TDD)
`tests/fakes/test_fake_build.py`:
- `test_lock_refuses_a_second_holder_and_release_is_idempotent`
- `test_lock_contention_can_be_scripted`
- `test_worktrees_create_once_and_path_for_is_stable`
- `test_provisioner_writes_what_the_spec_names`
- `test_gate_runner_returns_scripted_results_and_records_runs`
- `test_integration_branch_merges_are_idempotent_per_item`
- `test_budget_source_reads_spend_from_the_in_memory_ledger`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/application
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- The real git worktree, integration and gate-runner adapters, and their tests.
- `tests/infrastructure/test_automated_review_runner.py`'s gate runners (`fakes-review-visual`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-ledger`, `fakes-engines`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_advisory_lock.py`,
  `test_build_implement_end_to_end.py` (integration), `tests/system/**` and the protected tests.
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

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
