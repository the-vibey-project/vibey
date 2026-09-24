## Title
test(fakes): the design phase's ports — providers, researcher, synthesizer, spec store — get shared fakes, and the design handler tests use them

## Why
`fakes-registry` lists six ports as `PENDING` under this lane. They are all in
`application/interfaces/design.py:20-77`: `DesignProvider`, `DesignQuestionProvider`,
`DesignSpecReader`, `DesignSpecRepository`, `ResearchProvider` and `SpecSynthesizer`.

The tests rewrite them privately:
- `ScriptedQuestionProvider` is written twice (`tests/application/test_design_handler.py:39`,
  `test_reentrant_design.py:39`);
- `FakeSynthesizer` and `FakeSpecs` are in `test_design_synthesis_handler.py:35-60`;
- the design handlers' tests carry their own `FakeLedger` and `FakeDesignLedger`
  (`test_design_research_handler.py`, `test_design_synthesis_handler.py`,
  `test_design_handler.py`, `test_reentrant_design.py`).

Production already has an honest in-memory `DesignProvider`, `ScriptedDesignProvider`
(`src/vibey/infrastructure/engines/scripted_design.py:24-60`). `FileDesignSpecRepository`
(`src/vibey/infrastructure/db/design_spec_repository.py:21-56`) touches no database. It only
calls `projects.get` and then reads and writes files under the project's `repo_path`.
Yet it is typed with the concrete `PostgresProjectRepository`.

## Required behaviour
1. **Retype the file repository's collaborator.** `FileDesignSpecRepository.__init__(self, projects: ProjectStore)`.
   `ProjectStore` is `application/interfaces/projects.py:18`, which has `get`. Do the same for
   `FileVisualInventoryRepository` (`db/visual_inventory_repository.py:27-29`). Nothing else changes.
2. **`tests/fakes/design.py`**:
   - `InMemoryDesignSpecRepository` implements `DesignSpecRepository` and `DesignSpecReader`:
     - `specs: dict[tuple[UUID, int], DesignSpec]`;
     - `published: list[tuple[UUID, int, DesignSpec]]`;
     - `save` replaces;
     - `load` returns `None` when absent;
     - `publish` appends to `published` and does not require an earlier `save` (the file
       repository does not);
     - a constructor argument `known_projects: set[UUID] | None`. When it is given, an
       unknown project raises `LookupError(f"unknown project {project_id}")`, as the file
       repository's `_path` does (`:25-29`).
   - `ScriptedQuestionProvider` implements `DesignQuestionProvider`. Its constructor takes
     `batches: Mapping[DesignStage, QuestionBatch] | None`. `batch(stage, prior_events)`
     records `(stage, len(prior_events))` in `self.asked`. It returns the scripted batch, or,
     when none was scripted, delegates to `ScriptedDesignProvider().batch(...)`, the
     production default.
   - `ScriptedResearchProvider` implements `ResearchProvider`. It holds a
     `results: Mapping[str, ResearchResult]` with a default factory, and records `topics`.
   - `ScriptedSpecSynthesizer` implements `SpecSynthesizer`. It returns the spec it was
     given, records `self.inputs`, and raises the exception it was given, if any
     (`fail_with: BaseException | None`).
3. **Registry.**
   - `DesignProvider → ScriptedDesignProvider()` (production).
   - `DesignSpecRepository` and `DesignSpecReader` → `InMemoryDesignSpecRepository()`.
   - The three scripted classes for their ports.
   - Delete the six `PENDING` lines.
4. **Switch the design tests.** In `test_design_handler.py`, `test_reentrant_design.py`,
   `test_design_research_handler.py` and `test_design_synthesis_handler.py`:
   - delete the private provider, synthesizer, spec and ledger classes;
   - use the shared fakes, plus `design_ledger(InMemoryLedger())` from `tests/fakes/ledger.py`
     for the design ledger;
   - assert on `ledger.events`, which are the real `LedgerEvent`s the real
     `PostgresDesignLedger` view appended, where the old tests asserted on a private list.
   A test whose expectation changes because the real view now redacts or digests is fixed to
   the real behaviour, and listed in the commit body.

## Where to change
- `src/vibey/infrastructure/db/design_spec_repository.py`,
  `src/vibey/infrastructure/db/visual_inventory_repository.py` (annotation and import).
- New `tests/fakes/design.py`, `tests/fakes/test_fake_design.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json` and the four test modules above.

## Acceptance criteria
- [ ] `grep -n "^class " tests/application/test_design_handler.py tests/application/test_reentrant_design.py tests/application/test_design_research_handler.py tests/application/test_design_synthesis_handler.py`
      prints no provider, synthesizer, spec or ledger double.
- [ ] `FileDesignSpecRepository(InMemoryProjectRepository())` saves and loads a spec under
      `tmp_path` with no database (a new test).
- [ ] The registry has no `PENDING` entry naming `fakes-design`, and there is 100% `infrastructure/` coverage.

## Tests to write first (TDD)
`tests/fakes/test_fake_design.py`:
- `test_spec_repository_round_trips_and_records_publication`
- `test_spec_repository_rejects_an_unknown_project_when_told_the_projects`
- `test_question_provider_scripts_a_stage_and_defaults_to_production`
- `test_synthesizer_returns_or_raises_as_scripted`
- `test_file_spec_repository_runs_over_the_in_memory_projects` (`tmp_path` as `repo_path`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/application
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- `tests/application/test_automated_review.py`, `test_review_demo_handler.py` and
  `test_forward_compatibility_columns.py`, which carry their own spec readers (`fakes-review-visual`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-ledger`, which brings `fakes-projects` with it.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_design_*` (integration) and the protected tests.
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
