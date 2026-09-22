## Title
test(fakes): the deployment stage set gets a cloud fake that can fail on cue, and state stores you can read back

## Why
`fakes-registry` lists three deployment ports as `PENDING` under this lane
(`application/interfaces/azure.py:44-90`): `CloudClientPort`, `DeploymentSpecStore` and
`DeploymentConsentStore`.

Production has an honest in-memory cloud, `InMemoryAzureClientAdapter`
(`src/vibey/infrastructure/azure/adapter.py:16-77`). It verifies consent and its scope
digest before any mutation, as the real adapter must. The tests do not use it. They fake the
cloud four times, and none of those fakes checks consent:
- `FakeAzureClient` ×3: `tests/application/test_deploy_execute_handler.py:88-140`,
  `test_deploy_review_routing.py`, `tests/system/test_delivery_stage_set.py` (protected);
- `DummyAzureClient` in `tests/application/test_azure_port.py:37-`.

The stores are faked as `FakeSpecStore` and `FakeConsentStore`
(`tests/application/test_deploy_design_and_acceptance.py:531-545`). The ledgers are faked as
`FakeDeployLedger` ×4.

A deploy handler that forgot to carry consent would pass today's tests.

## Required behaviour
1. **`tests/fakes/deploy.py`**:
   - `FaultyCloudClient` (`CloudClientPort`) is a decorator over the production in-memory
     client:
     - `__init__(self, inner: CloudClientPort | None = None, *, fail_at: DeployStep | None = None, failure: BaseException | None = None, degrade_at_verify: bool = False)`,
       where `inner` defaults to `InMemoryAzureClientAdapter()`;
     - each method appends its `DeployStep` to `steps_run`: `DISCOVER`, `APPLY`, `VERIFY`,
       and `DELETE` if the enum has one;
     - at `fail_at` it raises `failure`, which defaults to
       `RuntimeError(f"cloud failure at {step}")`. Otherwise it delegates to `inner`, so
       consent verification stays real;
     - with `degrade_at_verify` set, `get_resource_status` returns
       `AzureResourceStatus(resource_id, "Failed", "Degraded")`.
   - `InMemoryDeploymentStateStore` implements `DeploymentSpecStore` and
     `DeploymentConsentStore`, and the sync loaders `load_spec(project_id)` and
     `load_consent(project_id)` that bootstrap passes as callables
     (`infrastructure/deploy/state_repository.py:1-9`):
     - it keeps per-project dictionaries, and `saved_specs` and `saved_consents` lists in
       call order;
     - a round trip returns an equal object. The file repository serialises with `asdict`,
       so check the equality the real round trip gives in
       `tests/infrastructure/deploy/test_state_repository.py` and match it.
2. **Registry.** `CloudClientPort → FaultyCloudClient()`. `DeploymentSpecStore` and
   `DeploymentConsentStore` → `InMemoryDeploymentStateStore()`. Delete the three `PENDING` lines.
3. **Switch four modules.** Delete the private cloud clients, state stores, clocks and ledgers,
   and use:
   - `FaultyCloudClient`, with `fail_at` where the old fake had `fail_at_step`;
   - `InMemoryDeploymentStateStore`;
   - `FakeClock` (`tests/fakes/system.py`);
   - `review_ledger(InMemoryLedger(), phase=Phase.DEPLOY_DESIGN)` or `DEPLOY_EXECUTE`, as
     `src/vibey/bootstrap.py:379-380` wires them;
   - `InMemoryProjectRepository` in place of `FakeProjectTransitioner`.
   The modules are `tests/application/test_deploy_design_and_acceptance.py`,
   `test_deploy_execute_handler.py`, `test_deploy_design_bridge.py` and `test_azure_port.py`.
   Where a test's consent did not match the spec's scope digest, the real in-memory client
   now refuses it. Fix the test's consent to be valid, unless the test is about refusal, in
   which case assert `MutationNotAuthorizedError`. List every such change in the commit body.

## Where to change
- New `tests/fakes/deploy.py`, `tests/fakes/test_fake_deploy.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json` and the four modules.

## Acceptance criteria
- [ ] `grep -n "class FakeAzureClient\|class DummyAzureClient\|class FakeSpecStore\|class FakeConsentStore\|class FakeDeployLedger\|class FakeClock" <the four modules>` prints nothing.
- [ ] A new test shows `FaultyCloudClient()` refusing `execute_plan` without explicit consent.
- [ ] The registry has no `PENDING` entry naming `fakes-deploy`.
- [ ] `tests/system/test_delivery_stage_set.py` is unchanged and passes.

## Tests to write first (TDD)
`tests/fakes/test_fake_deploy.py`:
- `test_cloud_records_steps_and_delegates`
- `test_cloud_fails_at_the_scripted_step`
- `test_cloud_keeps_real_consent_checks`
- `test_cloud_can_degrade_at_verify`
- `test_state_store_round_trips_spec_and_consent_per_project`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/application tests/system
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- `test_deploy_review_handlers.py`, `test_deploy_review_routing.py`,
  `test_review_deployment_choice.py` and `test_deployment_opt_in_handoff.py` (`fakes-deploy-review`).
- The Azure CLI adapter and its executor (`fakes-process-executor`).
- `tests/system/test_delivery_stage_set.py` (protected).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-ledger`, `fakes-observability`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/system/test_delivery_stage_set.py` (protected),
  `tests/infrastructure/deploy/test_state_repository.py`.
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
