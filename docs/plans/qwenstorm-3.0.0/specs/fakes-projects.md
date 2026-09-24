## Title
test(fakes): the project repository gets a port and an in-memory twin that compare-and-sets like PostgreSQL

## Why
Two ports split the project repository: `ProjectStore` (`get`, `transition`) and
`ProjectTransitioner` (`transition`), both in `application/interfaces/projects.py:17-37`.
Neither covers what `AppResources.projects` is used for. The CLI and the TUI call `create`
and `get_latest` on the concrete `PostgresProjectRepository`
(`src/vibey/infrastructure/db/project_repository.py:140-298`; `AppResources.projects` is
typed with it at `src/vibey/bootstrap.py:135`). So no fake can stand in for it, and the
bootstrap seam (`fakes-bootstrap-seam`) has nothing to type the field with.

The tests carry 11 private doubles of this one repository: `FakeProjectRepo` ×5,
`FakeProjectTransitioner` ×4 and `FakeTransitioner` ×2. Each one mirrors only the method its
test needs. None enforces the compare-and-set that makes `transition` replay-safe
(`:207-260`: `WHERE id = $1 AND phase = $2`, else `ValueError`), or the ledger event that
must commit with it.

## Required behaviour
1. **A port for the whole repository.** In `src/vibey/application/interfaces/projects.py`, add
   `@runtime_checkable class ProjectRepository(Protocol)` with the exact signatures of
   `PostgresProjectRepository`:
   - `create(name, repo_path, *, max_cycles, config) -> ProjectRecord`;
   - `get(project_id) -> ProjectRecord | None`;
   - `get_latest() -> ProjectRecord | None`;
   - `transition(project_id, *, expected, to, cycle=None, guard=None) -> ProjectRecord`.

   Export it from `vibey.application.interfaces`, beside `ProjectStore`. Add a test that
   `PostgresProjectRepository` satisfies it structurally, using `isinstance` on an instance
   built with `pool=object()`, without calling anything.
2. **`tests/fakes/projects.py` — `class InMemoryProjectRepository`** implements
   `ProjectRepository`, and so `ProjectStore` and `ProjectTransitioner` too:
   - `__init__(self, *, clock: Clock | None = None, ledger: LedgerAppender | None = None, notifications: NotificationSink | None = None)`.
     `LedgerAppender` is a small Protocol in the same module:
     `async def append(self, draft: LedgerEventDraft) -> LedgerEvent`.
   - `create`:
     - assigns `uuid4()`, `phase=Phase.INTAKE`, `cycle=1`, and
       `repo_path=repo_path.resolve()`;
     - sets `created_at=updated_at=clock.now()`;
     - raises `ValueError` for a `repo_path` another project already uses (the
       `project_repo_uniq` index, `migrations/0001_project.sql:18`);
     - raises `ValueError` unless `1 <= cycle <= max_cycles + 1`.
   - `get`, and `get_latest`, which takes the maximum by `(created_at, str(project_id))`.
   - `transition` compare-and-sets:
     - if the stored phase is not `expected`, raise
       `ValueError(f"project {project_id} is not in expected phase {expected.value!r}")`,
       leaving the state and the ledger untouched;
     - otherwise update the phase, the cycle when it is given, and `updated_at`;
     - build the event with the real `PhaseTransitionedDraftBuilder` (`project_repository.py:64-`);
     - `await ledger.append(draft)` when a ledger is wired, otherwise append the draft to
       `self.transition_drafts`;
     - notify exactly as `:260-298` does. The `kind`, `title` and `message` strings are copied
       verbatim;
     - return the new record.
   - `self.calls: list[str]` records method names.
3. **Registry.** Register `ProjectRepository`, `ProjectStore` and `ProjectTransitioner` →
   `InMemoryProjectRepository()`, and delete the two `PENDING` lines.
4. **Switch two tests now.** In `tests/infrastructure/test_automated_review_runner.py` and
   `tests/infrastructure/test_review_artifact_writer.py`, `FakeProjectRepo` is replaced by
   `InMemoryProjectRepository`: create the project, then use its id. The other nine
   private doubles move in the lanes that own their files: `fakes-build`,
   `fakes-review-visual` and `fakes-deploy`.

## Where to change
- `src/vibey/application/interfaces/projects.py`, `src/vibey/application/interfaces/__init__.py`.
- New `tests/fakes/projects.py`, `tests/fakes/test_fake_projects.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json` (if the switched files counted anything),
  `tests/infrastructure/test_automated_review_runner.py`, `tests/infrastructure/test_review_artifact_writer.py`.

## Acceptance criteria
- [ ] `ProjectRepository` is exported, and `PostgresProjectRepository` satisfies it.
- [ ] A second `transition` with the same `expected` raises, and it appends no second event.
- [ ] The registry has no `PENDING` entry naming `fakes-projects`.
- [ ] 100% `application/` coverage.

## Tests to write first (TDD)
`tests/fakes/test_fake_projects.py`:
- `test_create_defaults_match_the_schema` (phase `intake`, cycle 1)
- `test_create_refuses_a_repo_path_already_in_use`
- `test_get_latest_is_the_newest_project`
- `test_transition_compare_and_sets_and_ledgers_the_move`
- `test_a_replayed_transition_raises_and_ledgers_nothing`
- `test_transition_to_done_notifies_run_completed`
- `test_postgres_repository_satisfies_the_port` (it can live in `tests/application/test_interfaces_convention.py`
  instead, if that file already holds this kind of check)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/application tests/infrastructure/test_automated_review_runner.py tests/infrastructure/test_review_artifact_writer.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Changing `AppResources` (`fakes-bootstrap-seam`).
- The other nine private doubles (the domain lanes).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_project_repository.py`
  (integration) and the protected tests.
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
  - The new port Protocol is itself the interface (ADR-0016), so no separate interface file is needed.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
