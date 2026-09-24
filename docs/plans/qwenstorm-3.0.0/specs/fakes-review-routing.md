## Title
test(fakes): the review collect, triage and loop-back tests run on the shared queue, gate, project, spec and ledger fakes

## Why
The families these tests need all exist by now:
- the queue and gates (`fakes-queue-gates`);
- projects (`fakes-projects`);
- the ledger and its real phase views (`fakes-ledger`);
- specs (`fakes-design`).

Four modules still carry private copies of them:
- `tests/application/test_review_collect_handler.py`: `FakeGateRepo`, `FakeReviewCollectLedger`;
- `test_review_triage_handler.py`: `FakeProjectTransitioner`, `FakeReviewTriageLedger`,
  `FakeSpecRepo`, `FakeSpecStore`;
- `test_review_loopback_routing.py`: `FakeProjectRepo`, `FakeReviewTriageLedger`, `FakeSpecRepo`;
- `test_forward_compatibility_columns.py:220-240`: the nested `FakeSpecRepo` and `FakeReviewLedger`.

A private `FakeGateRepo` that does not re-ready the parked job, or a private project double
that does not compare-and-set, lets a routing bug pass. The shared fakes behave like
PostgreSQL (`fakes-queue-gates`, `fakes-projects`).

## Required behaviour
1. In each of the four modules, delete the private doubles and use:
   - `FakeHumanGateRepository(store=...)` sharing an `InMemoryQueueStore` with the
     `FakeJobRepository` the handler uses (`tests/fakes/queue.py`), wherever a gate is raised
     or answered;
   - `InMemoryProjectRepository` (`tests/fakes/projects.py`). Create the project, then
     `transition` it to the phase the test starts in, so the compare-and-set sees the true
     phase;
   - `InMemoryDesignSpecRepository` (`tests/fakes/design.py`) for spec readers and stores;
   - `review_ledger(InMemoryLedger())` (`tests/fakes/ledger.py`) for the review ledger, and
     `InMemoryLedger` where a test only reads events.
2. Assertions that read a private list now read the shared fake's public state:
   - `ledger.events`, `gates.raised`, `projects.transition_drafts` or the ledger's
     `PHASE_TRANSITIONED` events;
   - `store.jobs[job_id].state`.
   Keep every assertion's meaning. Where the real behaviour now differs, for example the
   answer re-readies the job, assert the real behaviour and list it in the commit body.
3. Lower the four files' entries in `tests/meta/patching_baseline.json` if any counted.

## Where to change
- The four test modules, and `tests/meta/patching_baseline.json`.

## Acceptance criteria
- [ ] `grep -n "class Fake" tests/application/test_review_collect_handler.py tests/application/test_review_triage_handler.py tests/application/test_review_loopback_routing.py tests/application/test_forward_compatibility_columns.py` prints nothing.
- [ ] The number of tests in each module is unchanged (`--collect-only -q`).
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/application` passes.

## Tests to write first (TDD)
- No new test module. Convert one test at a time and run it.
- Add `test_triage_loopback_transition_is_refused_from_the_wrong_phase` to
  `test_review_loopback_routing.py`. It proves the handler surfaces the compare-and-set
  refusal that the old double hid. If the handler does not surface it, stop and report
  rather than change production code.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/application
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Production code. If a converted test exposes a handler bug, stop and report it.
- New fakes.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-review-visual` (which brings design, ledger and projects),
  `fakes-queue-gates`.
- **Files touched:** the four test modules, `tests/meta/patching_baseline.json`.
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

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
