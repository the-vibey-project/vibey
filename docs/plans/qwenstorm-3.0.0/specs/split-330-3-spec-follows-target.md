<!-- split of #330: child 3 of 4; audit: issue-audit/updates/330.md -->
## Title
feat(deploy)!: the synthesized spec's provider, region and IaC follow [deploy].target, and survive a reload

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:136-137`) makes self-hosted OpenStack the
cloud default and every hosted cloud declared-only, and ADR-0042
(`docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:58-64`)
makes the target scope carry its provider. At runtime nothing honours the declaration:
`build_deployment_spec` (`src/vibey/application/deploy_design_handler.py:36-76`) never sets
`provider` (so every scope is the dataclass default `"openstack"`, an Azure adopter's included) and
hard-codes region `"eastus"` (`:59`) and IaC `"bicep"` (`:67`); `RUNTIME_CONFIG_KEYS`
(`src/vibey/infrastructure/config_loader.py:10`) leaves `deploy` out, so `vibey new`
(`src/vibey/cli/main.py:217`) never stores the `[deploy]` table with the project; and
`FileDeploymentStateRepository.load_spec` (`src/vibey/infrastructure/deploy/state_repository.py:63-70`)
drops `provider` on reload, so a saved Azure spec would come back as OpenStack and its consent
would stop matching. Lane `split-330-1-deploy-target-config` made `[deploy]` validated data
(`DeployConfig.from_mapping`, `DEPLOY_REGION_BY_TARGET`), and lane `split-330-2-scope-digest` kept
the pre-#319 Azure digest; this lane wires the declaration through: the synthesized spec follows
`[deploy].target`, the table is stored with the project, the worker reads it, and a reloaded spec
keeps its provider.

## Required behaviour
1. `build_deployment_spec(*, project_id, cycle, answers, deploy: DeployConfig | None = None)`:
   `None` means `DeployConfig()` (openstack, heat). The spec's `target_scope.provider` is
   `deploy.target`; an answer key `"provider"` is ignored (only the declaration picks the cloud).
   `region` is `answers["region"]` if given, else `DEPLOY_REGION_BY_TARGET[deploy.target]` (was
   `"eastus"`). `topology.iac_provider` is `answers["iac_provider"]` if given, else `deploy.iac`
   (was `"bicep"`). Every other field is as today. The default spec
   (openstack / `RegionOne` / `heat`) passes `validate()`.
2. `DeploySynthesizeHandler.__init__` takes keyword-only `deploy: DeployConfig | None = None`, keeps
   it, and passes it to `build_deployment_spec`. Without it the handler behaves as the default in
   behaviour 1.
3. `FileDeploymentStateRepository.load_spec` restores `provider` from spec.json's `target_scope`;
   a spec.json without the key predates the field (#319) and was written by the Azure-only pipeline,
   so it loads as `"azure"`, and a consent holding its pre-#319 4-field digest still matches (lane
   `split-330-2-scope-digest`). A spec saved with any provider reloads equal to what was saved.
4. `RUNTIME_CONFIG_KEYS == ("notifications", "telemetry", "deploy")`. `load_runtime_config_from_path`
   copies a `[deploy]` table into the project's stored config after the existing `parse_config` call
   (`config_loader.py:116-122`) has validated it by lane `split-330-1`'s rules, so `vibey new`
   stores it and `target = "aws"` is refused with a `ConfigError` whose path is `deploy.target`.
5. `bootstrap.build_full_worker` takes keyword-only `deploy: DeployConfig | None = None`; `None`
   resolves to `DeployConfig.from_mapping(project.config)`, and the result is passed to
   `DeploySynthesizeHandler(deploy=...)`. Every existing caller (the `worker` command,
   `tests/system/test_full_worker_faked.py`) is unchanged.
6. `tests/system/test_delivery_stage_set.py` (protected) and `tests/system/test_full_worker_faked.py`
   pass unedited. No SQL is added anywhere (the state repository is file-based).

## Where to change
Line numbers are from the storm integration branch at `4317cff6`; if one has moved, find the quoted
text. If lane `engines-pool` (#321) has landed on the integration branch when this lane starts,
rebase over it first: it also edits `bootstrap.py` (`build_full_worker`, around lines 364-370).
Use `edit_file` for every existing file. This lane spans four source files because one behaviour
crosses them: the declaration must be stored (`config_loader.py`), read (`bootstrap.py`), applied
(`deploy_design_handler.py`) and kept across a reload (`state_repository.py`); any subset leaves a
spec that follows a declaration nothing stores, or a stored Azure spec that reloads as OpenStack.
No new class is added, so no new interface; `DeploySynthesizeHandlerInterface`
(`application/interfaces/class_contracts.py:275-277`) declares only `handle` and is unchanged.

1. **`src/vibey/application/deploy_design_handler.py`** (222 lines)
   - Imports: before line 21 (`from vibey.domain.deployment import (`), add
     `from vibey.domain.config import DEPLOY_REGION_BY_TARGET, DeployConfig`.
   - `build_deployment_spec` (lines 36-76): the signature becomes
     ```python
     def build_deployment_spec(
         *,
         project_id: UUID,
         cycle: int,
         answers: Mapping[str, object],
         deploy: DeployConfig | None = None,
     ) -> DeploymentSpec:
     ```
     Replace the docstring (lines 39-46) with:
     ```python
         """Synthesizes the DeploymentSpec from the elicitation answers.

         The cloud is the project's declared `[deploy].target` (sub-doctrine 8.b: self-hosted
         OpenStack unless a paid cloud is declared; `None` means `DeployConfig()`). It is never
         an interview answer: an answer key "provider" is ignored, so only the declaration picks
         the cloud. The region and IaC format default from that target
         (`DEPLOY_REGION_BY_TARGET`, `[deploy].iac`), and an answer may still override them.
         "accept_defaults" supplies none of the cloud identifiers, so the tenant, subscription
         and resource-group defaults below are deliberately visible placeholders -- fine for the
         in-memory adapter and the faked harness, and exactly the values a real cloud run must
         override by answering the interview.
         """
         config = deploy if deploy is not None else DeployConfig()
     ```
     (the `config = ...` line goes after the docstring, before `def _get`). In the
     `AzureTargetScope(...)` call, replace `region=_get("region", "eastus"),` (line 59) with
     `region=_get("region", DEPLOY_REGION_BY_TARGET[config.target]),` and add
     `provider=config.target,` on the next line. Replace `iac_provider=_get("iac_provider", "bicep"),`
     (line 67) with `iac_provider=_get("iac_provider", config.iac),`.
   - `DeploySynthesizeHandler.__init__` (lines 156-167): add `deploy: DeployConfig | None = None,`
     after `spec_store: DeploymentSpecStore | None = None,`, and `self._deploy = deploy` after
     `self._spec_store = spec_store`.
   - The call at lines 185-187 becomes
     `spec = build_deployment_spec(project_id=job.project_id, cycle=job.cycle, answers=answers, deploy=self._deploy)`
     (let `ruff format` wrap it).
2. **`src/vibey/infrastructure/deploy/state_repository.py`** (113 lines): in `load_spec`, after
   `                region=str(scope["region"]),` (line 68), add
   ```python
                   # A spec.json without the key predates the field (#319) and was written by
                   # the Azure-only pipeline, so it is an Azure spec; reading it as the dataclass
                   # default ("openstack") would orphan its consent.
                   provider=str(scope.get("provider", "azure")),
   ```
3. **`src/vibey/infrastructure/config_loader.py`** (123 lines):
   - Line 10: `RUNTIME_CONFIG_KEYS = ("notifications", "telemetry", "deploy")`.
   - Docstring of `load_runtime_config_from_path` (lines 104-111): replace
     `    notification and telemetry tables in ``vibey.toml`` effective at runtime.` with the two lines
     `    notification, telemetry and deploy tables in ``vibey.toml`` effective at` /
     `    runtime (the worker's synthesized deployment spec follows ``[deploy].target``).`
   - Lines 116-122 stay as they are: the existing `parse_config(...)` call already validates every
     copied table, `[deploy]` included, before it is returned.
4. **`src/vibey/bootstrap.py`** (962 lines):
   - Line 77: `from vibey.domain.config import VibeyConfig` becomes
     `from vibey.domain.config import DeployConfig, VibeyConfig`.
   - `build_full_worker` (lines 341-352): add `deploy: DeployConfig | None = None,` after
     `azure_client: AzureClientPort | None = None,`. In its docstring (lines 353-363) add, before the
     closing `"""`: `` `deploy` defaults to the project's stored [deploy] table: the synthesized
     deployment spec follows its target (sub-doctrine 8.b).``
   - After line 371 (`azure = azure_client if azure_client is not None else InMemoryAzureClientAdapter()`),
     add `deploy_config = deploy if deploy is not None else DeployConfig.from_mapping(project.config)`.
   - In the `"deploy.synthesize": DeploySynthesizeHandler(` call (lines 568-573), add
     `deploy=deploy_config,` after `spec_store=deploy_state,`.
5. **Tests** (append only; below): `tests/application/test_deploy_design_and_acceptance.py`,
   `tests/infrastructure/deploy/test_state_repository.py`,
   `tests/infrastructure/test_config_loader.py`, `tests/test_bootstrap.py`. Put any import a new
   test needs inside that test function (the pattern at
   `tests/application/test_deploy_design_and_acceptance.py:515-517`), so no import block is edited
   and ruff's E402 is not tripped.

## Acceptance criteria
- [ ] The application tests below pass: the default spec is openstack/RegionOne/heat and valid; an
      Azure declaration gives azure/eastus/bicep; answers cannot switch the provider; the synthesize
      handler stamps the configured target, and defaults to openstack without one.
- [ ] `test_the_provider_round_trips` and `test_a_spec_written_before_the_provider_field_loads_as_azure`
      pass (a legacy consent holding `hashlib.sha256(b"t-1:s-1:rg-one:dev").hexdigest()` matches the
      reloaded spec).
- [ ] `test_the_deploy_table_is_stored_for_project_creation` and
      `test_a_deploy_target_without_an_adapter_is_refused_before_persistence` pass.
- [ ] `test_the_full_worker_hands_the_projects_deploy_config_to_synthesis` passes.
- [ ] `tests/system/test_delivery_stage_set.py` passes unedited (`git diff --stat` does not name it),
      and `tests/system/test_full_worker_faked.py` passes unedited (system tier, PostgreSQL).
- [ ] `git diff --stat` names only the four source files and four test files above.
- [ ] `! git grep -nE "(SELECT|INSERT|UPDATE|DELETE) " -- src/vibey/application/deploy_design_handler.py src/vibey/infrastructure/deploy src/vibey/infrastructure/config_loader.py src/vibey/bootstrap.py`
      exits 0 (it does at `4317cff6`): no SQL added.
- [ ] All checks below pass, including 100% branch coverage for `src/vibey/application/*` and
      `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
All four files are default tier: no database, no network, no marker, nothing patched.

**`tests/application/test_deploy_design_and_acceptance.py`** (append five tests). Build every
handler and job exactly as the module's own
`test_synthesize_skips_foreign_stages_and_non_mapping_answers` (lines 666-707) does: the job is
`replace(make_job(uuid4()), phase=Phase.DEPLOY_DESIGN, kind="deploy.synthesize")`, the ledger
`FakeDeployLedger()`, the clock `FakeClock()`, the store `FakeSpecStore()` (lines 531-536; its
`saved` list holds each saved spec). If lane `fakes-deploy` has landed and those module doubles are
gone, use the doubles that test now uses (`InMemoryDeploymentStateStore` from `tests/fakes/deploy.py`,
whose `saved_specs` list holds each saved spec) — add no new private double.
1. `test_the_default_spec_is_sovereign_and_valid` (plain `def`):
   `spec = build_deployment_spec(project_id=uuid4(), cycle=1, answers={})`;
   `spec.target_scope.provider == "openstack"`, `spec.target_scope.region == "RegionOne"`,
   `spec.topology.iac_provider == "heat"`, `spec.validate() == []`.
2. `test_the_spec_follows_an_azure_target`:
   `deploy = DeployConfig.from_mapping({"deploy": {"target": "azure"}})`;
   `spec = build_deployment_spec(project_id=uuid4(), cycle=1, answers={}, deploy=deploy)`;
   `(spec.target_scope.provider, spec.target_scope.region, spec.topology.iac_provider) == ("azure", "eastus", "bicep")`
   and `spec.validate() == []`.
3. `test_answers_cannot_switch_the_cloud`: with no `deploy`,
   `answers={"provider": "azure", "region": "westeurope", "iac_provider": "heat"}` gives provider
   `"openstack"`, region `"westeurope"` (an answer still sets the region) and iac `"heat"`.
4. `test_the_synthesize_handler_stamps_the_configured_target` (`@pytest.mark.asyncio`, as the
   module's other async tests): a handler built with
   `deploy=DeployConfig.from_mapping({"deploy": {"target": "azure"}})` and the spec store, run on
   the job, returns `Success`; the one saved spec has provider `"azure"`, region `"eastus"` and iac
   `"bicep"`.
5. `test_the_synthesize_handler_defaults_to_the_sovereign_target`: the same without `deploy=`; the
   one saved spec has provider `"openstack"`, region `"RegionOne"` and iac `"heat"`.
Imports inside the functions: `from dataclasses import replace`,
`from vibey.application.deploy_design_handler import build_deployment_spec`,
`from vibey.domain.config import DeployConfig`.

**`tests/infrastructure/deploy/test_state_repository.py`** (append two tests; `_spec()` at lines
22-46 builds scope `t-1` / `s-1` / `rg-one` / `dev`; `DeploymentConsent`, `datetime`, `UTC`, `uuid4`,
`Path` are already imported):
1. `test_the_provider_round_trips(tmp_path)`: `azure = replace(_spec(), target_scope=replace(_spec().target_scope, provider="azure"))`;
   save it, load it; `loaded == azure` and `loaded.target_scope.provider == "azure"`.
2. `test_a_spec_written_before_the_provider_field_loads_as_azure(tmp_path)`: save `_spec()`; read
   `repo.spec_path` as JSON, `del raw["target_scope"]["provider"]`, write it back; `load_spec`
   returns a spec whose `target_scope.provider == "azure"`; and
   `DeploymentConsent(consent_id="c-legacy", target_scope_digest=hashlib.sha256(b"t-1:s-1:rg-one:dev").hexdigest(), granted_by="user", granted_at=datetime(2026, 8, 19, 12, 0, tzinfo=UTC)).matches_spec(loaded) is True`.
Imports inside the functions: `hashlib`, `json`, `from dataclasses import replace`.

**`tests/infrastructure/test_config_loader.py`** (append two tests; `re`, `pytest`, `ConfigError`
and `load_runtime_config_from_path` are already imported):
1. `test_the_deploy_table_is_stored_for_project_creation(tmp_path)`: `vibey.toml` holds
   `'[deploy]\ntarget = "azure"\n'`; `load_runtime_config_from_path(path) == {"deploy": {"target": "azure"}}`.
2. `test_a_deploy_target_without_an_adapter_is_refused_before_persistence(tmp_path)`:
   `'[deploy]\ntarget = "aws"\n'` raises `ConfigError` with `match=re.escape("deploy.target")`.

**`tests/test_bootstrap.py`** (append one structural test, in the style of
`test_every_composed_worker_is_given_the_structured_logger` at lines 116-142; `ast`, `Path` and
`bootstrap` are already imported):
```python
def test_the_full_worker_hands_the_projects_deploy_config_to_synthesis() -> None:
    """The composition root passes the project's [deploy] declaration to synthesis."""
    import inspect

    parameter = inspect.signature(bootstrap.build_full_worker).parameters["deploy"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is None
    assert "DeployConfig.from_mapping(project.config)" in inspect.getsource(
        bootstrap.build_full_worker
    )
    tree = ast.parse(Path(bootstrap.__file__).read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "DeploySynthesizeHandler"
    ]
    assert calls, "bootstrap must still construct DeploySynthesizeHandler"
    for call in calls:
        assert any(keyword.arg == "deploy" for keyword in call.keywords), (
            f"DeploySynthesizeHandler at bootstrap.py:{call.lineno} is built without deploy="
        )
```

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
# Focused tests (default tier: no service needed)
uv run pytest -q -p no:cacheprovider tests/application/test_deploy_design_and_acceptance.py \
  tests/infrastructure/deploy/test_state_repository.py tests/infrastructure/test_config_loader.py \
  tests/test_bootstrap.py tests/domain
# The protected system test and the faked full worker, unedited (PostgreSQL 17 reachable)
uv run pytest -q -p no:cacheprovider tests/system/test_delivery_stage_set.py \
  tests/system/test_full_worker_faked.py
# Per-layer 100% branch coverage over the whole suite (the CI gate; PostgreSQL 17 reachable)
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/application/*' --fail-under=100
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
uv run coverage report --include='src/vibey/cli/*' --fail-under=100
```
One coverage run at a time. Until lane `fakes-harness-decouple` lands, `tests/conftest.py:146-156`
connects to PostgreSQL at session start; the focused default-tier command needs nothing else and
can run with `--noconftest -n 0` added. The system-tier tests are never this lane's only proof: the
four default-tier files prove every behaviour above.

## Out of scope
- `[deploy]` validation itself (lane `split-330-1-deploy-target-config`), the digest forms (lane
  `split-330-2-scope-digest`), and the az adapter's provider check (lane
  `split-330-4-az-scope-guard`). Do not touch `domain/`, `infrastructure/azure/` or `cli/`.
- The in-memory Azure adapter, an OpenStack or AWS adapter (#331 and follow-ups), and an ADR-0016
  interface for `FileDeploymentStateRepository` (it satisfies `DeploymentSpecStore` /
  `DeploymentConsentStore` today; converging it is another lane).
- Do not edit `tests/system/test_delivery_stage_set.py` (protected), CHANGELOG.md, docs/, ADRs,
  CLAUDE.md, AGENTS.md, GEMINI.md or the skill trees. Do not push, open PRs, or change git remotes.
  Commit locally as
  `feat(deploy)!: the synthesized spec's provider, region and IaC follow [deploy].target, and survive a reload`,
  with a body saying: a spec.json written between #319 and this change reads
  `"provider": "openstack"` even for an Azure adopter, and must be re-synthesized (re-run
  DEPLOY_DESIGN) once lane `split-330-4-az-scope-guard` lands; and the footer
  `BREAKING CHANGE: a synthesized deployment spec now follows [deploy].target (default openstack, region RegionOne, iac heat) instead of always azure-shaped defaults, and vibey new stores the validated [deploy] table.`

## Standing constraints
- Substitute only at declared seams (constructor keywords such as `deploy=`, `spec_store=`); never
  `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock` (sub-doctrine 9.b). Add no new
  private test double: reuse the module's (or `tests/fakes/deploy.py`'s) doubles.
- No new raw SQL anywhere (the ORM rule); the state repository stays file-based.
- Every job idempotent under replay: re-running `deploy.synthesize` rewrites the same spec for the
  same declaration and answers.
- Sovereign by default (8.b): no declaration means OpenStack; a paid cloud is only ever declared.
- Configurable (12.c): the region and IaC defaults come from `DEPLOY_REGION_BY_TARGET` and
  `[deploy].iac`, never from literals in the handler.
- OpenCode is repealed (8.b): no new test names it.
- Arch Linux and macOS (8.h): nothing here is platform-specific; the same check block is the proof
  on both.
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- Change existing files with `edit_file` (or a checked replacement); add tests by appending; never
  rewrite an existing file with `write_file` (`STORM/EDITING-RULES.md`).

**Depends on:** split-330-1-deploy-target-config, split-330-2-scope-digest
- split-330-1-deploy-target-config: `DeployConfig` (default openstack/heat), `DeployConfig.from_mapping`,
  `DEPLOY_REGION_BY_TARGET`, and `_parse_deploy`'s refusal of `target = "aws"`.
- split-330-2-scope-digest: the 4-field Azure digest, without which the legacy-consent test in
  `test_state_repository.py` cannot match. Also rebase over `engines-pool` (#321) if it has landed:
  it also edits `bootstrap.py`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
