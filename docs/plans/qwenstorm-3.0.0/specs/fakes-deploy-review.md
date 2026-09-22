## Title
test(fakes): the deploy-review handlers and the REVIEW→DEPLOY opt-in run on the shared fakes

## Why
Four modules still carry private doubles of ports that now have shared fakes. Those fakes
behave like the real adapters (`fakes-queue-gates`, `fakes-projects`, `fakes-ledger`,
`fakes-deploy`):
- `tests/application/test_deploy_review_handlers.py`: `FakeDeployLedger`;
- `test_deploy_review_routing.py`: `FakeAzureClient`, `FakeDeployLedger`, `FakeProjectTransitioner`;
- `test_review_deployment_choice.py`: `FakeGateRepo`, `FakeProjectRepo`, `FakeReviewDeploymentLedger`;
- `test_deployment_opt_in_handoff.py`: `FakeGateRepo`, `FakeProjectRepo`, `FakeReviewDeploymentLedger`.

The deployment opt-in is a human gate (the six-phase model: "user opts into deployment").
Its test's `FakeGateRepo` does not re-ready the parked job when the gate is answered, so the
handoff from gate answer to next job is never exercised.

## Required behaviour
1. In each module, delete the private doubles and use:
   - `FakeJobRepository` and `FakeHumanGateRepository` over one shared `InMemoryQueueStore`,
     so an answered gate re-readies the parked job;
   - `InMemoryProjectRepository`, created in the phase the test starts in;
   - `review_ledger(InMemoryLedger(), phase=Phase.REVIEW)` for the review ledger, and
     `review_ledger(InMemoryLedger(), phase=Phase.DEPLOY_REVIEW)` for the deploy review ledger
     (`src/vibey/bootstrap.py:925-926`);
   - `FaultyCloudClient` (`tests/fakes/deploy.py`).
2. Where the opt-in test answers the gate, add one assertion that the parked job is `READY`
   in the shared store afterwards.
3. Lower the four files' entries in `tests/meta/patching_baseline.json` if any counted.

## Where to change
- The four test modules, and `tests/meta/patching_baseline.json`.

## Acceptance criteria
- [ ] `grep -n "^class Fake" <the four modules>` prints nothing.
- [ ] The number of tests in each module is unchanged, plus one assertion in the opt-in test.
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/application` passes.

## Tests to write first (TDD)
- Convert one test at a time and run it after each.
- Add `test_answering_the_opt_in_gate_re_readies_the_parked_job` to
  `test_deployment_opt_in_handoff.py`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/application
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Production code. If a converted test exposes a handler bug, stop and report it.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-deploy`, `fakes-review-routing`.
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
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
