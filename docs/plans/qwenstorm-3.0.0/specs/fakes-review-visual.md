## Title
test(fakes): the REVIEW and VISUAL_DESIGN ports get shared fakes, and the review, demo and visual tests use them

## Why
`fakes-registry` lists four ports as `PENDING` under this lane:
- `AutomatedReviewRunner` and `ReviewArtifactWriter` (`application/interfaces/review.py:24-40`);
- `VisualInventoryProducer` and `VisualInventoryRepository` (`application/interfaces/visual.py:16-28`).

Their tests fake them privately:
- `tests/application/test_automated_review.py`: `FakeAutomatedReviewRunner`,
  `FakeReviewArtifactWriter`, `FakeReviewLedger`, `FakeSpecRepo`;
- `test_review_demo_handler.py`: `FakeReviewArtifactWriter`, `FakeReviewLedger`,
  `FakeSpecRepository`;
- `test_visual_handler.py`: `FakeProducer`, `FakeInventories`, `FakeLedger` (`:43-70`);
- `tests/infrastructure/test_automated_review_runner.py`: `FakeGateRunner`,
  `RecordingGateRunner`, plus its project double (moved by `fakes-projects`).

Production already has `ScriptedVisualProvider` (`infrastructure/engines/scripted_visual.py:21`),
an honest in-memory `VisualInventoryProducer`. `FileVisualInventoryRepository` runs over the
in-memory projects once `fakes-design` has retyped it.

## Required behaviour
1. **`tests/fakes/review.py`**:
   - `ScriptedAutomatedReviewRunner` (`AutomatedReviewRunner`). Its constructor takes
     `findings: Mapping[tuple[UUID, int], tuple[AutomatedFinding, ...]] | None` and
     `default: tuple[AutomatedFinding, ...] = ()`. `run_automated_reviews` records
     `(project_id, cycle)` in `runs` and returns the scripted findings.
   - `InMemoryReviewArtifactWriter` (`ReviewArtifactWriter`):
     - `root: Path`, passed in;
     - `write_review_artifacts(project_id, cycle, artifacts, *, executable=())` writes each
       artifact under `root / str(cycle) / "review" / name`, marks the names in `executable`
       as `0o755`, and returns `{name: path}`. Match the real layout in
       `infrastructure/review_artifact_writer.py`: if the real writer resolves `repo_path`
       from the project, take a `ProjectStore` instead of `root`, exactly as the real one does;
     - `written` records every call.
2. **`tests/fakes/visual.py`**:
   - `InMemoryVisualInventoryRepository` (`VisualInventoryRepository`) has the same shape as
     `InMemoryDesignSpecRepository` (`tests/fakes/design.py`): a store, a `published` list,
     and the optional unknown-project `LookupError`.
3. **Registry.**
   - `AutomatedReviewRunner → ScriptedAutomatedReviewRunner()`.
   - `ReviewArtifactWriter → InMemoryReviewArtifactWriter(<a fresh temp dir or an InMemoryProjectRepository>)`.
   - `VisualInventoryProducer → ScriptedVisualProvider()` (production).
   - `VisualInventoryRepository → InMemoryVisualInventoryRepository()`.
   - Delete the four `PENDING` lines.
4. **Switch four modules:**
   - `tests/application/test_automated_review.py` and `test_review_demo_handler.py`: use the
     shared review fakes, `InMemoryDesignSpecRepository` for the spec, and
     `review_ledger(InMemoryLedger())` for the ledger;
   - `test_visual_handler.py`: for the producer, use `ScriptedVisualProvider()`. Where a
     test needs one specific inventory, use `ScriptedInventoryProducer(result)`, a class you
     add to `tests/fakes/visual.py` that returns `result` and records `inputs`. It needs no
     registry entry, because the port is already registered. Use
     `InMemoryVisualInventoryRepository` for the repository, and `InMemoryLedger` for the ledger;
   - `tests/infrastructure/test_automated_review_runner.py`: `ScriptedGateRunner` from
     `tests/fakes/build.py`, whose `ran` list gives the recording.
   In every case, delete the private classes and lower the baseline.

## Where to change
- New `tests/fakes/review.py`, `tests/fakes/visual.py`, `tests/fakes/test_fake_review_visual.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json` and the four modules.

## Acceptance criteria
- [ ] `grep -n "^class Fake\|^class Recording" <the four modules>` prints nothing.
- [ ] The registry has no `PENDING` entry naming `fakes-review-visual`.
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/application tests/infrastructure/test_automated_review_runner.py` passes.

## Tests to write first (TDD)
`tests/fakes/test_fake_review_visual.py`:
- `test_review_runner_returns_scripted_findings_per_cycle`
- `test_artifact_writer_writes_where_the_real_writer_writes`, which compares against the real
  writer run over `InMemoryProjectRepository` with the same inputs
- `test_artifact_writer_marks_executables`
- `test_inventory_repository_round_trips_and_records_publication`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/application tests/infrastructure/test_automated_review_runner.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- `test_review_collect_handler.py`, `test_review_triage_handler.py`,
  `test_review_loopback_routing.py` and `test_forward_compatibility_columns.py` (`fakes-review-routing`).
- `test_review_deployment_choice.py` and `test_deployment_opt_in_handoff.py` (`fakes-deploy-review`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-design`, `fakes-build`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/test_review_artifact_writer.py`, `tests/system/**` and the protected tests.
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
