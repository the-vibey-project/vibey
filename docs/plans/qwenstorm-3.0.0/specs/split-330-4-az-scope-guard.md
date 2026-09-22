<!-- split of #330: child 4 of 4; audit: issue-audit/updates/330.md -->
## Title
feat(azure): the az adapter refuses a target scope for another provider

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:136-137`) makes self-hosted OpenStack the
cloud default and Azure declared-only, and ADR-0042
(`docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:58-64`)
makes every target scope carry its provider. `AzCliClientAdapter`
(`src/vibey/infrastructure/azure/az_cli.py:47-165`), the one adapter that mutates real
infrastructure, accepts a scope for any provider: an OpenStack spec handed to it would be rendered
to an ARM template and submitted with `az deployment group create`. After lane
`split-330-3-spec-follows-target`, every synthesized spec names the declared provider, so the
adapter can refuse anything that is not Azure before any subprocess runs. Together with lane
`split-330-2-scope-digest`'s colon-free digest fields, a consent can then never be spent on another
cloud. The in-memory adapter (`src/vibey/infrastructure/azure/adapter.py`) stays provider-agnostic:
it is the offline default for every target.

## Required behaviour
1. `src/vibey/application/azure_port.py` defines
   `class ScopeProviderMismatchError(Exception)` with the docstring
   `"""Raised when a cloud adapter is handed a target scope for another provider."""`, and lists it
   in `__all__`. Like `MutationNotAuthorizedError` (`azure_port.py:14-15`) it carries no behaviour
   and gets no interface file.
2. `AzCliClientAdapter` has a class attribute `PROVIDER = "azure"` (the provider this adapter
   deploys) and a method `_require_provider(self, scope: AzureTargetScope) -> None` that raises
   `ScopeProviderMismatchError(f"the az adapter deploys provider {self.PROVIDER!r} only; this scope is {scope.provider!r}")`
   when `scope.provider != self.PROVIDER`. For an OpenStack scope the text is
   `the az adapter deploys provider 'azure' only; this scope is 'openstack'`.
3. `_require_provider` is the first statement of `discover_environment` and
   `get_resource_status`, and runs before `_require_consent` in `execute_plan` (on
   `spec.target_scope`) and `delete_resource`. So for a non-Azure scope no `az` subprocess runs, and
   the provider refusal wins over a consent refusal.
4. An Azure scope behaves exactly as before; every existing test in
   `tests/infrastructure/azure/test_az_cli.py` passes once its `_spec()` names `provider="azure"`.
5. `InMemoryAzureClientAdapter` keeps accepting any provider (`adapter.py` is not edited).

## Where to change
Line numbers are from the storm integration branch at `4317cff6`; if one has moved, find the quoted
text. Use `edit_file` for every file. Two source files because the error is a port-level contract
(any cloud adapter may raise it, and it sits beside `MutationNotAuthorizedError` in the application
port module), while the check itself belongs to the one adapter that talks to Azure.

1. **`src/vibey/application/azure_port.py`** (26 lines): after `MutationNotAuthorizedError`
   (lines 14-15), add
   ```python


   class ScopeProviderMismatchError(Exception):
       """Raised when a cloud adapter is handed a target scope for another provider."""
   ```
   and add `"ScopeProviderMismatchError",` to `__all__` after `"MutationNotAuthorizedError",`
   (line 25).
2. **`src/vibey/infrastructure/azure/az_cli.py`** (165 lines):
   - Imports: the stdlib block ends at line 22 (`from typing import Any`) and the first-party block
     starts at line 24 (`from vibey.application.interfaces import (`). Add
     `from vibey.application.azure_port import ScopeProviderMismatchError` on its own line directly
     before line 24, which is isort order.
   - In `class AzCliClientAdapter:` (line 47), add before `def __init__`:
     ```python
         #: The one provider this adapter deploys (ADR-0042: a scope names its provider).
         PROVIDER = "azure"
     ```
   - After `_az_json` (ends line 62), add:
     ```python
         def _require_provider(self, scope: AzureTargetScope) -> None:
             # A scope synthesized for another cloud (8.b's default is OpenStack) must never
             # reach `az`: refuse before any subprocess runs, and before consent is judged.
             if scope.provider != self.PROVIDER:
                 raise ScopeProviderMismatchError(
                     f"the az adapter deploys provider {self.PROVIDER!r} only; "
                     f"this scope is {scope.provider!r}"
                 )
     ```
   - `discover_environment` (line 64): make `self._require_provider(scope)` its first statement.
   - `execute_plan` (lines 97-100): add `self._require_provider(spec.target_scope)` before
     `self._require_consent(spec.scope_digest(), consent)`.
   - `get_resource_status` (line 145): make `self._require_provider(scope)` its first statement.
   - `delete_resource` (lines 159-162): add `self._require_provider(scope)` before
     `self._require_consent(scope.digest(), consent)`.
3. **`tests/infrastructure/azure/test_az_cli.py`** (247 lines): in `_spec()` (lines 32-71), inside
   the `AzureTargetScope(` call (lines 36-43), add `            provider="azure",` after
   `            region="eastus",` (line 41). Append the new tests at the end of the file.
   No other file changes; `src/vibey/infrastructure/azure/adapter.py` is not edited.

## Acceptance criteria
- [ ] `test_every_method_refuses_a_non_azure_scope` and `test_the_provider_is_checked_before_consent`
      pass, with the injected executor's `calls` empty.
- [ ] Every pre-existing test in `tests/infrastructure/azure/test_az_cli.py` passes (their `_spec()`
      now names `provider="azure"`).
- [ ] `uv run pytest -q -p no:cacheprovider tests/infrastructure/azure tests/application/test_azure_port.py`
      passes, and `tests/infrastructure/azure/test_azure_adapter.py` is unedited.
- [ ] `git diff --stat` names only `src/vibey/application/azure_port.py`,
      `src/vibey/infrastructure/azure/az_cli.py` and `tests/infrastructure/azure/test_az_cli.py`.
- [ ] All checks below pass, including 100% branch coverage for `src/vibey/infrastructure/*` and
      `src/vibey/application/*`.

## Tests to write first (TDD)
**`tests/infrastructure/azure/test_az_cli.py`** (add `provider="azure",` to `_spec()`'s
`AzureTargetScope(` after `region="eastus",` at line 41, then append two tests;
default tier: no service, no marker, nothing patched). The executor is the module's
constructor-injected double, built exactly as `test_mutations_are_refused_without_digest_bound_consent`
(lines 185-208) builds it: `FakeExecutor()` today (lines 84-95), or `ScriptedCommandExecutor` from
`tests/fakes/process.py` if lane `fakes-process-executor` has landed and replaced it. Both record
every argv in `.calls`. Put the imports inside each function:
`import dataclasses`, `import re`,
`from vibey.application.azure_port import ScopeProviderMismatchError`.
1. `test_every_method_refuses_a_non_azure_scope` (`async def`; `asyncio_mode = "auto"`):
   ```python
   spec = _spec()
   foreign = dataclasses.replace(
       spec, target_scope=dataclasses.replace(spec.target_scope, provider="openstack")
   )
   executor = FakeExecutor()
   adapter = AzCliClientAdapter(executor=executor)
   consent = _consent(foreign)  # a valid consent: only the provider is wrong
   message = "the az adapter deploys provider 'azure' only; this scope is 'openstack'"
   with pytest.raises(ScopeProviderMismatchError, match=re.escape(message)):
       await adapter.discover_environment(foreign.target_scope)
   with pytest.raises(ScopeProviderMismatchError, match=re.escape(message)):
       await adapter.execute_plan(foreign, consent)
   with pytest.raises(ScopeProviderMismatchError, match=re.escape(message)):
       await adapter.get_resource_status(foreign.target_scope, "res-1")
   with pytest.raises(ScopeProviderMismatchError, match=re.escape(message)):
       await adapter.delete_resource(foreign.target_scope, "res-1", consent)
   assert executor.calls == []
   ```
2. `test_the_provider_is_checked_before_consent`: with the same `foreign` spec and a stale consent
   `DeploymentConsent(consent_id="c", target_scope_digest="a-different-digest", granted_by="operator", granted_at=NOW, explicit_mutation_authorized=True)`,
   both `execute_plan(foreign, stale)` and
   `delete_resource(foreign.target_scope, "res-1", stale)` raise `ScopeProviderMismatchError` (not
   `MutationNotAuthorized`), and `executor.calls == []`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
# Focused tests (default tier: no service needed)
uv run pytest -q -p no:cacheprovider tests/infrastructure/azure tests/application/test_azure_port.py
# The adapter is fully covered by its own test file alone
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= \
  tests/infrastructure/azure/test_az_cli.py
uv run coverage report --include='src/vibey/infrastructure/azure/az_cli.py' --fail-under=100
# Per-layer 100% branch coverage over the whole suite (the CI gate)
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
uv run coverage report --include='src/vibey/application/*' --fail-under=100
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
uv run coverage report --include='src/vibey/cli/*' --fail-under=100
```
One coverage run at a time. Until lane `fakes-harness-decouple` lands, `tests/conftest.py:146-156`
connects to PostgreSQL at session start, so the whole-suite coverage run needs it; the focused
commands need nothing else and can run with `--noconftest -n 0` added.

## Out of scope
- The in-memory Azure adapter (`infrastructure/azure/adapter.py`), the ARM renderer (`arm.py`), and
  the `vibey worker --azure az` login check (`cli/main.py:1481-1494`).
- The spec builder, its persistence and `[deploy]` (lanes `split-330-1` to `split-330-3`); an
  OpenStack or AWS CLI adapter (#331 and follow-ups); an ADR-0016 interface for
  `AzCliClientAdapter` (it satisfies the application port `CloudClientPort` today).
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or the skill trees. Do not
  push, open PRs, or change git remotes. Commit locally as
  `feat(azure): the az adapter refuses a target scope for another provider`.

## Standing constraints
- Substitute only at the declared seam (`AzCliClientAdapter(executor=...)`); never
  `monkeypatch.setattr` an import or attribute, `mock.patch`, `MagicMock` or `AsyncMock`
  (sub-doctrine 9.b). Add no new private test double.
- Fail closed: the provider check runs before consent and before any subprocess, so a refused
  scope never reaches `az`.
- Sovereign by default (8.b): Azure is declared-only; this adapter serves only an Azure declaration.
- Configurable (12.c): the adapter's provider is one named class attribute, not a literal repeated
  per method.
- No SQL anywhere. OpenCode is repealed (8.b): no new test names it.
- Arch Linux and macOS (8.h): nothing here is platform-specific (the tests never run `az`); the same
  check block is the proof on both.
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- Change existing files with `edit_file` (or a checked replacement); add tests by appending; never
  rewrite an existing file with `write_file` (`STORM/EDITING-RULES.md`).

**Depends on:** split-330-3-spec-follows-target
- split-330-3-spec-follows-target: synthesized specs stamped with the declared provider, and
  `load_spec` restoring it (legacy specs as `"azure"`). Before it every spec is stamped
  `openstack`, and this check would stop every Azure deploy.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
