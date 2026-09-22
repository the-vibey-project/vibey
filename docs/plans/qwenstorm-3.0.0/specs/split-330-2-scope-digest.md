<!-- split of #330: child 2 of 4; audit: issue-audit/updates/330.md -->
## Title
feat(deploy): an Azure scope keeps its pre-provider digest, and a spec must name a colon-free provider

## Why
ADR-0042 (`docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:58-61`)
made the target scope carry its provider "so the digest differs per provider", and runbook 03
requires the Azure alias to be "proven byte-compatible"
(`docs/runbooks/expansion/03-multicloud-aws-gcp.md:58-59`). Since c67495e4 (#319),
`AzureTargetScope.digest()` (`src/vibey/domain/deployment.py:24-28`) hashes
`provider:tenant:subscription:resource_group:environment`. Every consent recorded by 2.0.0 and
earlier hashed `tenant:subscription:resource_group:environment`, and every one of them is an Azure
consent (Azure was the only cloud then), so all of them stopped matching: an in-flight Azure deploy
now fails closed at `DeploymentConsent.matches_spec` (`deployment.py:169-170`;
`application/deploy_execute_handler.py:70-72`). This lane keeps the old 4-field form for Azure and
the provider-first 5-field form for every other provider, and makes `validate()` refuse a blank
provider and a `:` inside any digested field, so the two forms differ structurally (3 separators
against 4) and a consent can never cross clouds. It touches only the pure domain.

## Required behaviour
1. `LEGACY_DIGEST_PROVIDER = "azure"` is a module constant in `src/vibey/domain/deployment.py`,
   declared above `AzureTargetScope`, with a comment saying consents recorded before #319 hash the
   4-field form and all of them are Azure consents.
2. `AzureTargetScope.digest()` returns the SHA-256 hex digest of
   `f"{tenant_id}:{subscription_id}:{resource_group}:{environment}"` when
   `provider == LEGACY_DIGEST_PROVIDER`, and of
   `f"{provider}:{tenant_id}:{subscription_id}:{resource_group}:{environment}"` otherwise. For every
   non-Azure provider the bytes hashed are identical to today's code.
   - With `tenant_id="tenant-123"`, `subscription_id="sub-456"`, `resource_group="rg-vibey-dev"`,
     `environment="dev"`, `region="eastus"`: the Azure digest is
     `a3aca17c2ecbacc58a642eebf46c8698516c80b467e177e1bd5afa8c9cb94fe9` and the OpenStack digest
     is `57d727a9ffb8ec9eb505422ed834872e36ca66ee3072d0c8e110b69b66b66cb9` (both recomputed with
     `hashlib` for this spec).
3. `DeploymentSpec.validate()` adds `"provider is required"` when `target_scope.provider` is blank
   (empty or whitespace), and `f"{name} must not contain ':'"` for each of `provider`, `tenant_id`,
   `subscription_id`, `resource_group` and `environment` whose value contains `:`. Every existing
   message and check stays as it is.
4. `DeploymentConsent`, `DeploymentSpec.scope_digest()` and every other class are unchanged;
   `tests/domain/test_deployment_domain.py` passes unedited.

## Where to change
Line numbers are from the storm integration branch at `4317cff6`; if one has moved, find the quoted
text. Only `src/vibey/domain/deployment.py` (200 lines; use `edit_file`) and the new test file.

1. Above line 14 (`@dataclass(slots=True, frozen=True)` of `AzureTargetScope`), after the blank
   lines that follow the imports, add:
   ```python
   # Consents recorded before #319 hash the four-field form
   # `tenant:subscription:resource_group:environment`, and every one of them is an Azure
   # consent: Azure was the only cloud then. An Azure scope keeps that form so those
   # consents still match; every other provider hashes the provider-first five-field form.
   # `validate()` forbids ':' inside every digested field, so the two forms cannot collide.
   LEGACY_DIGEST_PROVIDER = "azure"
   ```
2. Replace `digest()` (lines 24-28) with:
   ```python
       def digest(self) -> str:
           fields: tuple[str, ...] = (
               self.tenant_id,
               self.subscription_id,
               self.resource_group,
               self.environment,
           )
           if self.provider != LEGACY_DIGEST_PROVIDER:
               fields = (self.provider, *fields)
           return hashlib.sha256(":".join(fields).encode()).hexdigest()
   ```
3. In `validate()` (lines 88-155), after the target-scope checks that end with
   `            errors.append("region is required")` (line 107), add:
   ```python
           if not t.provider.strip():
               errors.append("provider is required")
           for name, value in (
               ("provider", t.provider),
               ("tenant_id", t.tenant_id),
               ("subscription_id", t.subscription_id),
               ("resource_group", t.resource_group),
               ("environment", t.environment),
           ):
               if ":" in value:
                   errors.append(f"{name} must not contain ':'")
   ```
4. New test file `tests/domain/test_scope_digest.py` (below). No other file changes; no new class,
   so no new interface.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_scope_digest.py` passes.
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_deployment_domain.py tests/domain/test_domain_purity.py`
      passes with those files unedited.
- [ ] `git diff --stat` names only `src/vibey/domain/deployment.py` and
      `tests/domain/test_scope_digest.py`.
- [ ] `src/vibey/domain/*` keeps 100% branch coverage, and every line this lane adds is covered by
      `tests/domain` alone.

## Tests to write first (TDD)
New `tests/domain/test_scope_digest.py` (pure domain: no database, no network, no marker, no
patching). Line 1 is the provenance line copied from `tests/domain/test_deployment_domain.py`.
Imports: `hashlib`, `from dataclasses import replace`, `from datetime import UTC, datetime`,
`pytest`, and from `vibey.domain.deployment`: `LEGACY_DIGEST_PROVIDER`, `AzureTargetScope`,
`CostBoundary`, `DeploymentConsent`, `DeploymentSpec`, `IdentityAuthority`, `RecoveryPolicy`,
`TopologyConfig`, `VerificationContract`.
Helpers:
```python
AZURE_DIGEST = "a3aca17c2ecbacc58a642eebf46c8698516c80b467e177e1bd5afa8c9cb94fe9"
OPENSTACK_DIGEST = "57d727a9ffb8ec9eb505422ed834872e36ca66ee3072d0c8e110b69b66b66cb9"


def _scope(provider: str) -> AzureTargetScope:
    return AzureTargetScope(
        tenant_id="tenant-123",
        subscription_id="sub-456",
        resource_group="rg-vibey-dev",
        environment="dev",
        region="eastus",
        provider=provider,
    )


def _spec(scope: AzureTargetScope) -> DeploymentSpec:
    return DeploymentSpec(
        spec_id="spec-dep-1",
        version="1.0.0",
        target_scope=scope,
        identity=IdentityAuthority("workload_identity_oidc", "principal-789", ("Contributor",)),
        topology=TopologyConfig("container_app", "bicep", "Standard_B1s"),
        recovery_policy=RecoveryPolicy("revision", True),
        verification=VerificationContract("/health", (), 60),
        cost_boundary=CostBoundary(100.0, 10.0),
    )
```
- `test_the_legacy_provider_is_azure`: `LEGACY_DIGEST_PROVIDER == "azure"`.
- `test_an_azure_scope_keeps_its_pre_provider_digest`: `_scope("azure").digest() == AZURE_DIGEST`
  and `== hashlib.sha256(b"tenant-123:sub-456:rg-vibey-dev:dev").hexdigest()`.
- `test_an_openstack_scope_hashes_the_provider_first_form`:
  `_scope("openstack").digest() == OPENSTACK_DIGEST`,
  `== hashlib.sha256(b"openstack:tenant-123:sub-456:rg-vibey-dev:dev").hexdigest()`, and a scope
  built without `provider=` (the default, `"openstack"`) has the same digest.
- `test_every_provider_has_its_own_digest`:
  `len({_scope(p).digest() for p in ("azure", "openstack", "aws")}) == 3`.
- `test_a_legacy_consent_matches_the_azure_spec_only`: a `DeploymentConsent("c-legacy",
  hashlib.sha256(b"tenant-123:sub-456:rg-vibey-dev:dev").hexdigest(), "operator",
  datetime(2026, 8, 15, tzinfo=UTC), True)` gives `matches_spec(_spec(_scope("azure"))) is True`
  and `matches_spec(_spec(_scope("openstack"))) is False`.
- `test_valid_scopes_pass_validation`: parametrized over `"azure"` and `"openstack"`:
  `_spec(_scope(provider)).validate() == []`.
- `test_a_blank_provider_is_refused`: parametrized over `""` and `"   "`:
  `"provider is required" in _spec(_scope(provider)).validate()`.
- `test_a_colon_is_refused_in_every_digested_field`: parametrized over `"provider"`,
  `"tenant_id"`, `"subscription_id"`, `"resource_group"` and `"environment"`:
  `spec = _spec(replace(_scope("azure"), **{name: "a:b"}))`; `f"{name} must not contain ':'" in spec.validate()`
  and `spec.is_valid() is False`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
# Focused tests (default tier: no service needed)
uv run pytest -q -p no:cacheprovider tests/domain
# Every added line of deployment.py is covered by the domain tests alone
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/domain
uv run coverage report --include='src/vibey/domain/deployment.py' --fail-under=100
# Per-layer 100% branch coverage over the whole suite (the CI gate)
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
uv run coverage report --include='src/vibey/application/*' --fail-under=100
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
uv run coverage report --include='src/vibey/cli/*' --fail-under=100
```
One coverage run at a time. Until lane `fakes-harness-decouple` lands, `tests/conftest.py:146-156`
connects to PostgreSQL at session start, so the whole-suite coverage run needs it; the focused
domain commands need nothing and can run with `--noconftest -n 0` added. If the focused
`deployment.py` report misses a line this lane did not add, say so in the verdict rather than
editing another file; the whole-suite gate is the rule.

## Out of scope
- `[deploy]` configuration (lane `split-330-1-deploy-target-config`), the spec builder, its
  persistence, the runtime config keys and bootstrap (lane `split-330-3-spec-follows-target`), and
  the az adapter's provider check (lane `split-330-4-az-scope-guard`). Do not touch
  `domain/config.py`, `application/`, `infrastructure/` or `bootstrap.py`.
- Renaming `AzureTargetScope` to `TargetScope` (the aliases at `deployment.py:31-32` stay as they
  are), and any AWS/GCP digest form.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or the skill trees. Do not
  push, open PRs, or change git remotes. Commit locally as
  `feat(deploy): an Azure scope keeps its pre-provider digest, and a spec must name a colon-free provider`.

## Standing constraints
- `domain/` stays pure: `hashlib` is already imported and is stdlib; no I/O, no async, no clock.
- Tests patch nothing: no `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`
  (sub-doctrine 9.b).
- The ledger and consent are append-only records: this lane changes how a digest is computed, never
  a stored consent.
- OpenCode is repealed (8.b): no new test names it. No SQL anywhere (this lane is pure).
- Arch Linux and macOS (8.h): nothing here is platform-specific; the same check block is the proof
  on both.
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- Change existing files with `edit_file` (or a checked replacement); never rewrite an existing file
  with `write_file` (`STORM/EDITING-RULES.md`).

**Depends on:** none
- Nothing unmerged: `deployment.py` is as #319 (c67495e4) left it on the integration branch.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
