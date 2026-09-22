<!-- split of #331: child 1 of 5; audit: issue-audit/updates/331.md -->

## Title
feat(openstack): HeatTemplateRenderer renders a DeploymentSpec as a Heat template

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:136-137`) makes **self-hosted OpenStack**
the cloud default, and ADR-0042
(`docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:58-64`)
promises "the self-hosted OpenStack adapter (a real `openstack` CLI adapter plus the existing
in-memory default)". Only Azure has a real client (`src/vibey/infrastructure/azure/az_cli.py:47-165`),
and it deploys by rendering the spec into an ARM template (`src/vibey/infrastructure/azure/arm.py`).
The OpenStack adapter (lane `split-331-2-openstack-cli-adapter`) needs the same thing for OpenStack's
orchestration service, Heat: a template it can hand to `openstack stack create|update --template FILE`.
This lane builds that renderer as a class with its interface (ADR-0016, sub-doctrine 9.b at
`doctrines.md:349`; `arm.py`'s module function `render_template` is the older shape and is not
copied), and it follows `arm.py`'s rule (`arm.py:13-14`): an autonomous deploy never improvises the
shape of infrastructure, so anything it cannot render is refused.

This lane creates the `src/vibey/infrastructure/openstack/` package with one class. It runs no
subprocess and touches no CLI.

## Required behaviour
1. `src/vibey/infrastructure/openstack/heat.py` declares
   `DEFAULT_IMAGE = "docker.io/library/nginx:stable"`, `class UnsupportedHeatTopology(ValueError)`,
   and `class HeatTemplateRenderer`.
2. `HeatTemplateRenderer(*, image: str = DEFAULT_IMAGE)` has a read-only property `image` (returns
   the constructor's `image`) and the method `render(spec: DeploymentSpec) -> dict[str, Any]`, which
   returns a HOT template.
3. `render` raises `UnsupportedHeatTopology` before building anything, checking in this order:
   - `spec.topology.iac_provider.lower() != "heat"` → reason `f"iac_provider {spec.topology.iac_provider!r}"`;
   - `spec.topology.service_type != "container_app"` → reason `f"service_type {spec.topology.service_type!r}"`;
   - `spec.topology.instances < 1` → reason `f"instances {spec.topology.instances}"`.

   The exception message is exactly
   `f"{reason}: the Heat renderer runs iac_provider 'heat', service_type 'container_app' and at least one instance"`.
4. The template shape. With `app = "vibey-" + spec.spec_id[:20].lower().replace("_", "-")` (as at
   `arm.py:38`) and `scope = spec.target_scope`, the result has exactly these four keys:
   - `"heat_template_version": "2018-08-31"`;
   - `"description": f"vibey deployment {spec.spec_id}"`;
   - `"parameters": {"image": {"type": "string", "default": <self.image>, "description": "Container image to run"}}`;
   - `"resources"`: when `spec.topology.ingress_enabled`, first an `"ingress"` resource
     `{"type": "OS::Neutron::SecurityGroup", "properties": {"name": f"{app}-ingress", "rules": [{"direction": "ingress", "protocol": "tcp", "port_range_min": PORT, "port_range_max": PORT, "remote_ip_prefix": "0.0.0.0/0"}]}}`,
     where `PORT` is `443` when `spec.topology.tls_enabled` and `80` otherwise; then, for each `i`
     in `range(spec.topology.instances)`, a resource `f"app_{i}"`:
     `{"type": "OS::Zun::Container", "properties": {"name": f"{app}-{i}", "image": {"get_param": "image"}, "restart_policy": "always", "labels": {**scope.tags, "vibey.spec_id": spec.spec_id, "vibey.environment": scope.environment}, "security_groups": [{"get_resource": "ingress"}]}}`,
     where the `security_groups` key is present only when the `ingress` resource is;
   - `"outputs": {"endpoint": {"description": "Network addresses of the first container", "value": {"get_attr": ["app_0", "addresses"]}}}`.
5. Ingress rules, stated plainly:
   - `tls_enabled` opens only port 443, never a plaintext port. The image must terminate TLS itself:
     no Octavia load balancer is created.
   - `tls_enabled=False` opens port 80.
   - `ingress_enabled=False` gives no `ingress` resource and no `security_groups` key.
   - `OS::Zun::Container` has no port property, so the security group is how ingress is exposed.
     The properties used are those of `heat/engine/resources/openstack/zun/container.py`.
6. `render` is pure: no file, no subprocess, no network, and the same spec always gives an equal
   dict built from fresh objects (lane `split-331-2-openstack-cli-adapter` writes it to a temporary
   file and hands it to the CLI). Two renders share no mutable sub-object.
7. `HeatTemplateRendererInterface` sits beside the class (ADR-0016, 9.b), in
   `src/vibey/infrastructure/openstack/interfaces/heat_interface.py`, and the new
   `vibey.infrastructure.openstack.interfaces` package is held by import-linter's
   `infrastructure-interfaces-declare-only` contract: interfaces declare and never consume.

The worked sample: a spec with `spec_id="spec-os-1"`, `tags={"owner": "vibey"}`,
`environment="dev"`, `instances=2`, `ingress_enabled=True`, `tls_enabled=True`,
`iac_provider="heat"`, `service_type="container_app"`, rendered with the default image, equals:
```json
{"heat_template_version": "2018-08-31",
 "description": "vibey deployment spec-os-1",
 "parameters": {"image": {"type": "string", "default": "docker.io/library/nginx:stable",
                          "description": "Container image to run"}},
 "resources": {
   "ingress": {"type": "OS::Neutron::SecurityGroup", "properties": {
      "name": "vibey-spec-os-1-ingress",
      "rules": [{"direction": "ingress", "protocol": "tcp", "port_range_min": 443,
                 "port_range_max": 443, "remote_ip_prefix": "0.0.0.0/0"}]}},
   "app_0": {"type": "OS::Zun::Container", "properties": {
      "name": "vibey-spec-os-1-0", "image": {"get_param": "image"}, "restart_policy": "always",
      "labels": {"owner": "vibey", "vibey.spec_id": "spec-os-1", "vibey.environment": "dev"},
      "security_groups": [{"get_resource": "ingress"}]}},
   "app_1": {"type": "OS::Zun::Container", "properties": {
      "name": "vibey-spec-os-1-1", "image": {"get_param": "image"}, "restart_policy": "always",
      "labels": {"owner": "vibey", "vibey.spec_id": "spec-os-1", "vibey.environment": "dev"},
      "security_groups": [{"get_resource": "ingress"}]}}},
 "outputs": {"endpoint": {"description": "Network addresses of the first container",
                          "value": {"get_attr": ["app_0", "addresses"]}}}}
```

## Where to change
Every new file starts with the provenance header: copy line 1 of
`src/vibey/infrastructure/azure/az_cli.py` byte for byte. Line numbers are from the storm
integration branch at `4317cff6`; if one has moved, find the quoted text.
- New `src/vibey/infrastructure/openstack/__init__.py`: a one-paragraph module docstring (the
  self-hosted OpenStack cloud adapter, sub-doctrine 8.b) and
  `from vibey.infrastructure.openstack.heat import DEFAULT_IMAGE, HeatTemplateRenderer, UnsupportedHeatTopology`
  with `__all__ = ["DEFAULT_IMAGE", "HeatTemplateRenderer", "UnsupportedHeatTopology"]`. Lane
  `split-331-2-openstack-cli-adapter` adds its own names later.
- New `src/vibey/infrastructure/openstack/heat.py`: Required behaviour 1-6. A module docstring in
  the style of `arm.py:1-15` (what it renders, why the image is a parameter: the DeploymentSpec
  deliberately carries no image, and why unsupported shapes are refused). Imports: `typing.Any`
  and `vibey.domain.deployment.DeploymentSpec` only. The renderer is a class; any helper (for
  example building one container resource) is a method, not a module function.
- New `src/vibey/infrastructure/openstack/interfaces/heat_interface.py`, copying the docstring
  shape of `src/vibey/infrastructure/secrets/interfaces/openbao_interface.py:1-6`
  ("Mirrors `vibey/infrastructure/openstack/heat.py` (ADR-0016). Interfaces declare; they never
  consume."). Import only `typing` (`Any`, `Protocol`, `runtime_checkable`) and
  `vibey.domain.deployment.DeploymentSpec`:
  ```python
  @runtime_checkable
  class HeatTemplateRendererInterface(Protocol):
      @property
      def image(self) -> str:
          """The container image the template's `image` parameter defaults to."""
          ...

      def render(self, spec: DeploymentSpec) -> dict[str, Any]:
          """A HOT template for the spec, or UnsupportedHeatTopology -- never a guess."""
          ...
  ```
- New `src/vibey/infrastructure/openstack/interfaces/__init__.py`: the docstring
  `"""Seams the OpenStack adapter declares. Interfaces declare; they never consume."""`, the import
  `from vibey.infrastructure.openstack.interfaces.heat_interface import HeatTemplateRendererInterface`
  and `__all__ = ["HeatTemplateRendererInterface"]`, following
  `src/vibey/infrastructure/secrets/interfaces/__init__.py`.
- `.importlinter`: after line 129 (`    vibey.infrastructure.tracker.interfaces`), add the line
  `    vibey.infrastructure.openstack.interfaces` to the `source_modules` of
  `[importlinter:contract:infrastructure-interfaces-declare-only]` (the contract at lines 108-133).
  Use `edit_file`.
- The new tests below. No other file changes.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/infrastructure/openstack` passes.
- [ ] `uv run pytest -q -p no:cacheprovider --noconftest -n 0 tests/infrastructure/openstack/test_heat_renderer.py`
      passes with PostgreSQL stopped (the new tests need no service).
- [ ] `uv run lint-imports` reports `infrastructure-interfaces-declare-only` KEPT with the new package
      listed, and `uv run pytest -q -p no:cacheprovider tests/meta/test_import_contracts_bind.py tests/application/test_interfaces_convention.py` passes.
- [ ] `git diff --stat` names only the four new source files, `.importlinter` and the two new test files.
- [ ] `uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100` passes after the
      whole-suite coverage run.

## Tests to write first (TDD)
- New `tests/infrastructure/openstack/__init__.py`, holding only the provenance header line, as in
  `tests/infrastructure/deploy/__init__.py`.
- New `tests/infrastructure/openstack/test_heat_renderer.py` (no database, no network, no marker, no
  patching). Build specs with a `_spec(**topology_changes)` helper modelled on `_spec()` in
  `tests/infrastructure/azure/test_az_cli.py:32-71`: `spec_id="spec-os-1"`, `version="1.0.0"`, an
  `AzureTargetScope(tenant_id="proj-1", subscription_id="cloud-1", resource_group="rg-vibey-dev", environment="dev", region="RegionOne", provider="openstack", tags={"owner": "vibey"})`,
  the same `IdentityAuthority`, `RecoveryPolicy`, `VerificationContract` and `CostBoundary` values as
  that helper, and `topology=dataclasses.replace(TopologyConfig("container_app", "heat", "m1.small", instances=2), **topology_changes)`.
  - `test_render_matches_the_sample_template`: `HeatTemplateRenderer().render(_spec())` equals the
    whole worked sample in Required behaviour (the JSON block), written out as a Python dict literal in the test.
  - `test_plain_ingress_opens_port_80`: `_spec(tls_enabled=False)` gives an `ingress` resource whose
    `rules` is exactly one rule with `port_range_min == port_range_max == 80`.
  - `test_no_ingress_means_no_security_group`: `_spec(ingress_enabled=False)` gives no `ingress`
    key in `resources`, and no `app_*` resource has a `security_groups` key.
  - `test_custom_image_is_the_parameter_default`: `HeatTemplateRenderer(image="registry.local/app:1")`
    puts that image in `template["parameters"]["image"]["default"]` and reports it through `.image`;
    `HeatTemplateRenderer().image == DEFAULT_IMAGE == "docker.io/library/nginx:stable"`.
  - `test_render_refuses_what_it_cannot_run`: parametrized over
    `({"iac_provider": "bicep"}, "iac_provider 'bicep'")`,
    `({"service_type": "kubernetes_fleet"}, "service_type 'kubernetes_fleet'")` and
    `({"instances": 0}, "instances 0")`; each `render(_spec(**changes))` raises
    `UnsupportedHeatTopology` whose message contains the reason and ends with
    `"the Heat renderer runs iac_provider 'heat', service_type 'container_app' and at least one instance"`.
    Also `issubclass(UnsupportedHeatTopology, ValueError)`.
  - `test_iac_provider_is_matched_without_case`: `_spec(iac_provider="HEAT")` renders (no error).
  - `test_render_is_deterministic`: two renders of one spec are equal; after
    `first["resources"]["app_0"]["properties"]["labels"]["owner"] = "changed"`, the second render's
    label is still `"vibey"`, and a third render still equals the sample.
  - `test_renderer_satisfies_its_interface`: `isinstance(HeatTemplateRenderer(), HeatTemplateRendererInterface)`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/openstack tests/meta/test_import_contracts_bind.py tests/application/test_interfaces_convention.py
uv run pytest -q -p no:cacheprovider --noconftest -n 0 tests/infrastructure/openstack/test_heat_renderer.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
uv run coverage report --include='src/vibey/application/*' --fail-under=100
uv run coverage report --include='src/vibey/cli/*' --fail-under=100
```
One coverage run at a time. Until lane `fakes-harness-decouple` lands, `tests/conftest.py:146-156`
(`pytest_configure`) connects to PostgreSQL at session start, so every run except the
`--noconftest` one needs PostgreSQL 17 reachable. If `ruff check` reports only import order
(`I001`), run `uv run ruff check --select I --fix` on the files you changed, then
`uv run ruff format` on them.

## Out of scope
- Lanes `split-331-2` to `split-331-5`: the `openstack` CLI adapter, the az adapter's preflight,
  `vibey worker --cloud`, and installing the CLI.
- TLS termination through Octavia/Barbican, mapping SKU to Zun cpu/memory, and choosing a network.
- AWS (8.b's default paid cloud) and GCP targets; `arm.py` and the Azure adapters.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md, README.md or the skill
  trees; the docs wave owns them. Do not push, open PRs, or change git remotes. Commit locally as
  `feat(openstack): HeatTemplateRenderer renders a DeploymentSpec as a Heat template`; the hooks add
  the `Made-With:` trailer, so do not bypass them.

## Standing constraints
- Exception classes carry no behaviour and follow the existing precedent of having no interface
  (`src/vibey/infrastructure/cache/redis.py:20`, `class RedisError(RuntimeError)`).
- Tests substitute only at a declared seam: never `monkeypatch.setattr`, `mock.patch`, `MagicMock`
  or `AsyncMock` (9.b). This lane needs no substitution at all.
- Change `.importlinter` with `edit_file`; create new files with `write_file`. Never rewrite an
  existing file (EDITING-RULES.md).
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.

**Depends on:** none
- The renderer needs nothing unmerged. (`split-330-3-spec-follows-target` is what makes an
  OpenStack spec carry `iac_provider = "heat"` by default; these tests build their own specs.)

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
