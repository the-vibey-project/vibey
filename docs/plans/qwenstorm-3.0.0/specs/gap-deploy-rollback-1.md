## Title
feat(domain): DeploymentSpecCodec turns a deployment spec into a ledger payload and back, with a content digest

## Why
Gap C5 (`issue-audit/gaps.md:232-241`): `vibey deploy rollback` must return "to the last accepted
deployment state" (`src/vibey/cli/main.py:1123-1152` is a placeholder). The state vibey deployed is
a `DeploymentSpec` (`src/vibey/domain/deployment.py:72-158`), but nothing keeps an earlier one:
`FileDeploymentStateRepository` holds exactly one `spec.json`
(`src/vibey/infrastructure/deploy/state_repository.py:36-47`), and `spec_id` is per cycle
(`f"dep-{project_id.hex[:8]}-c{cycle}"`, `src/vibey/application/deploy_design_handler.py:53`), so a
⑥ → ④ loop in the same cycle re-synthesizes a *different* spec under the *same* id. The thorough
ledger (7.c, `src/vibey_tools/gh/docs/doctrines.md:82-91` at `d3b4a388`) is where the accepted state
belongs: lane `gap-deploy-execute-control` records the verified spec in its
`deployment_verification` artifact, and lane `gap-deploy-rollback-2` reads it back. Both need one
pure codec and a content digest that tells two specs apart when their ids match.

The codec is pure domain (no I/O), so the application layer can use it. The parsing in
`state_repository.py:55-101` does the same job for a file but lives in infrastructure, where the
application cannot reach it; this codec states that reason at its definition (10.e,
`doctrines.md:417`), and moving the repository onto it is a later convergence, not this lane.
Secrets never enter it: `secret_references` are references (validated as such,
`deployment.py:139-153`), never values.

## Required behaviour
1. New `src/vibey/domain/deployment_codec.py` declares:
   - `class InvalidDeploymentPayload(VibeyError)` (no interface: an exception).
   - `class DeploymentSpecCodec` with:
     - `to_payload(self, spec: DeploymentSpec) -> dict[str, object]`: exactly this shape, JSON
       types only (tuples as lists, the tags mapping as a dict):
       ```python
       {"spec_id": ..., "version": ...,
        "target_scope": {"tenant_id", "subscription_id", "resource_group", "environment",
                         "region", "provider", "tags": {...}},
        "identity": {"identity_type", "principal_id", "approved_roles": [...]},
        "topology": {"service_type", "iac_provider", "sku", "instances",
                     "ingress_enabled", "tls_enabled"},
        "recovery_policy": {"progressive_exposure", "auto_rollback_on_health_failure",
                            "max_rollback_attempts"},
        "verification": {"health_endpoint", "smoke_tests": [...], "bake_window_seconds"},
        "cost_boundary": {"max_monthly_budget_usd", "max_deployment_cost_usd"},
        "secret_references": [...]}
       ```
     - `from_payload(self, payload: Mapping[str, object]) -> DeploymentSpec`: the inverse. Every
       key above is required except `tags` (default `{}`), `approved_roles`, `smoke_tests` and
       `secret_references` (default empty). `provider` is required: a payload vibey writes always
       carries it. Sequence fields become tuples. Unknown extra keys are ignored (a newer vibey may
       add fields; forward compatibility as in vibey#287). Types are checked: strings are `str`;
       `instances`, `max_rollback_attempts` and `bake_window_seconds` are `int` and not `bool`;
       the booleans are `bool`; the two budget fields are `int` or `float` and not `bool`, returned
       as `float`; lists hold only strings; `tags` maps strings to strings. Any violation raises
       `InvalidDeploymentPayload(f"deployment spec payload: {path} {problem}")` with `path` dotted
       (`"target_scope.region"`, `"topology.instances"`) and `problem` one of `"is missing"`,
       `"must be a string"`, `"must be an integer"`, `"must be a boolean"`, `"must be a number"`,
       `"must be a table"`, `"must be a list of strings"`, `"must map strings to strings"`.
     - `digest(self, spec: DeploymentSpec) -> str`: `digest_event(self.to_payload(spec))`
       (`vibey.domain.ledger.digest_event`, the ledger's own canonical hash — 10.e).
     - Helpers are private methods of the class, not module functions (9.b).
   - `DEPLOYMENT_SPEC_CODEC: Final[DeploymentSpecCodecInterface] = DeploymentSpecCodec()`.
   - The class docstring states the reason it duplicates `state_repository.py:55-101` (the
     application cannot import infrastructure) and that secret references are references.
2. New `src/vibey/domain/interfaces/deployment_codec_interface.py`:
   `@runtime_checkable class DeploymentSpecCodecInterface(Protocol)` with the three methods,
   `DeploymentSpec` imported under `TYPE_CHECKING` only (copy
   `src/vibey/domain/interfaces/ledger_record_interface.py:9-36`).
3. Exported from `src/vibey/domain/interfaces/__init__.py`: a new import block directly after the
   `correlation_interface` block (lines 8-11), and `"DeploymentSpecCodecInterface",` in `__all__`
   directly after `"DeliveryCorrelationInterface",`.
4. `tests/domain/test_domain_purity.py` passes: the module imports only `collections.abc`,
   `typing` and `vibey.domain` modules (the hash is `digest_event`'s, so no `hashlib` or `json` here).

## Where to change
- New `src/vibey/domain/deployment_codec.py`, `src/vibey/domain/interfaces/deployment_codec_interface.py`
  (line 1: the provenance header of `src/vibey/domain/deployment.py`).
- `src/vibey/domain/interfaces/__init__.py` (`edit_file` only).
- New `tests/domain/test_deployment_codec.py`. No other file changes.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_deployment_codec.py tests/domain/test_domain_purity.py tests/domain/test_deployment_domain.py` passes.
- [ ] `git diff --stat` names only the two new source files, `domain/interfaces/__init__.py` and the new test.
- [ ] `src/vibey/domain/*` keeps 100% branch coverage.

## Tests to write first (TDD)
`tests/domain/test_deployment_codec.py` (pure). A full spec: scope
`AzureTargetScope("t-1", "s-1", "rg-one", "dev", "RegionOne", provider="openstack", tags={"owner": "vibey"})`,
`IdentityAuthority("managed_identity", "p-1", ("reader",))`,
`TopologyConfig("container_app", "heat", "m1.small", instances=2)`, `RecoveryPolicy("canary")`,
`VerificationContract("/health", ("curl /health",), 30)`, `CostBoundary(100.0, 10.0)`,
`secret_references=("vault:app/db",)`.
- `test_round_trip_returns_an_equal_spec` — `from_payload(to_payload(spec)) == spec`.
- `test_the_payload_is_plain_json` — `json.loads(json.dumps(to_payload(spec))) == to_payload(spec)`,
  and `payload["target_scope"]["provider"] == "openstack"`.
- `test_the_digest_is_the_ledgers_hash_of_the_payload` — `digest(spec) == digest_event(to_payload(spec))`.
- `test_the_digest_tells_same_id_specs_apart` — `dataclasses.replace(spec, topology=replace(spec.topology, instances=3))`
  has the same `spec_id` and a different digest; an equal spec has an equal digest.
- `test_optional_sequences_default_empty` — a payload without `tags`, `approved_roles`,
  `smoke_tests`, `secret_references` parses with empty values.
- `test_extra_keys_are_ignored` — adding `"future": 1` at the top and in `topology` parses equal.
- `test_every_violation_names_its_path` — parametrized: delete `target_scope.region` →
  `"deployment spec payload: target_scope.region is missing"`; `topology.instances = True` →
  `"... topology.instances must be an integer"`; `topology.tls_enabled = "yes"` → `must be a boolean`;
  `cost_boundary.max_monthly_budget_usd = "10"` → `must be a number`; `identity = []` →
  `identity must be a table`; `smoke_tests = [1]` → `verification.smoke_tests must be a list of strings`;
  `tags = {"a": 1}` → `target_scope.tags must map strings to strings`; `target_scope.provider` deleted →
  `target_scope.provider is missing`.
- `test_integer_budgets_become_floats` — `max_monthly_budget_usd = 100` parses to `100.0`.
- `test_the_codec_satisfies_its_interface` — `isinstance(DEPLOYMENT_SPEC_CODEC, DeploymentSpecCodecInterface)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

One coverage run at a time.

## Out of scope
- Recording the spec (`gap-deploy-execute-control`), rolling back (`gap-deploy-rollback-2`),
  moving `FileDeploymentStateRepository` onto the codec (a later convergence lane).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(domain): DeploymentSpecCodec, a deployment spec as a ledger payload and back`. Do not push.

## Lane card
- **Depends on:** nothing.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/domain/test_deployment_domain.py`, `tests/domain/test_domain_purity.py`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
