## Title
feat(config): [deploy] target = "paid" resolves to aws, 8.b's default paid cloud, and remembers that it was declared

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:136-137` and `:188-194` at integration
HEAD `d3b4a388`) makes self-hosted OpenStack the cloud default, every hosted cloud declared-only,
and fixes AWS as the cloud an unnamed paid declaration reaches. Gap C2
(`issue-audit/gaps.md:189-200`): `deploy.target` accepts only concrete targets, so a human who
writes "a paid cloud, whichever is the default" has no way to say it. Lane `gap-paid-defaults`
added the catalogue (`vibey.domain.paid_defaults.PAID_DEFAULTS`); this lane makes the `[deploy]`
parser consult it, exactly once, at the only point the target is read
(`_parse_deploy`, `src/vibey/domain/config.py:453-459`, as rewritten by lane
`openstack-client-p1`, #330 child 1). The declaration word is kept beside the resolved target so
status output can show both (lane `gap-deploy-target-status`): a paid platform must never arrive
silently (ADR-0042, `docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:108-109`).
The default stays `openstack` (8.a): only the exact word `"paid"` resolves.

## Required behaviour
1. `[deploy]\ntarget = "paid"\n` parses to `DeployConfig(target="aws", iac=DEPLOY_IAC_BY_TARGET["aws"][0], declared_target="paid")`.
   `iac` defaults and is validated exactly as for a literal `target = "aws"` (the resolved target
   is what the `DEPLOY_IAC_BY_TARGET` lookup and the `iac` check see).
2. `DeployConfig.from_mapping({"deploy": {"target": "paid"}})` gives the same result.
3. Every other target is untouched and keeps `declared_target == ""`: `"openstack"`, `"azure"`,
   `"aws"`, and the default (no `[deploy]` table).
4. `DeployConfig` gains the field `declared_target: str = field(default="", compare=False)`, so
   `DeployConfig(target="aws", iac=X, declared_target="paid") == DeployConfig(target="aws", iac=X)`
   (a resolved config deploys exactly like one that names the target), and the method
   `target_line(self) -> str`:
   - when `declared_target` is set: `PAID_DEFAULTS.default_for(PaidSurface.CLOUD).explain(self.declared_target)`,
     i.e. `"aws (declared 'paid': AWS is the default paid cloud, sub-doctrine 8.b)"`;
   - otherwise `self.target`.
5. The unknown-target `ConfigError("deploy.target", ...)` that `openstack-client-p1` wrote keeps its
   text and gains the declaration: its message becomes
   `f"must be one of {', '.join(sorted(DEPLOY_IAC_BY_TARGET))} (the targets with an adapter), or {PAID_DECLARATION!r} for 8.b's default paid cloud, got {target!r}"`.
6. `DeployConfigInterface` (added by `openstack-client-p1` in
   `src/vibey/domain/interfaces/config_interface.py`) gains the read-only property
   `declared_target: str` and the method `target_line(self) -> str`.
7. Nothing else in `config.py` changes; `tests/domain/test_config.py` and
   `tests/domain/test_deploy_target_config.py` (from `openstack-client-p1`) pass unedited.

## Where to change
Line numbers are at `d3b4a388`, before `openstack-client-p1` lands; after it, find the quoted text.
Use `edit_file` for every change (`config.py` is 724 lines).
- `src/vibey/domain/config.py`
  - Imports (lines 9-13): add `from vibey.domain.paid_defaults import PAID_DECLARATION, PAID_DEFAULTS, PaidSurface`
    after `from vibey.domain.errors import VibeyError`. (`field` is already imported at line 10.)
  - `class DeployConfig` (line 137): after its `iac: str = ...` line add, with this comment:
    ```python
        # The word a human wrote when it declared a target without naming it ("paid", 8.b's
        # paid defaults); empty when `target` was written as-is. Outside equality: the
        # resolved config deploys exactly like one that names the target.
        declared_target: str = field(default="", compare=False)

        def target_line(self) -> str:
            """The target as status output shows it, naming the declaration when there was one."""
            if self.declared_target:
                return PAID_DEFAULTS.default_for(PaidSurface.CLOUD).explain(self.declared_target)
            return self.target
    ```
  - `_parse_deploy`: immediately after the line
    `target = _optional(table, "target", "deploy.target", str, "openstack")` add:
    ```python
        declared_target = ""
        if PAID_DEFAULTS.is_declaration(target):
            # 8.b: a paid cloud declared without a name is always the default paid cloud.
            declared_target = target
            target = PAID_DEFAULTS.resolve(PaidSurface.CLOUD, target)
    ```
    extend the unknown-target message as in behaviour 5, and pass `declared_target=declared_target`
    in the `return DeployConfig(...)`.
- `src/vibey/domain/interfaces/config_interface.py`: in `DeployConfigInterface`, add
  ```python
      @property
      def declared_target(self) -> str: ...

      def target_line(self) -> str: ...
  ```
- New test file `tests/domain/test_deploy_target_paid.py`. No other file changes.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_deploy_target_paid.py tests/domain/test_deploy_target_config.py tests/domain/test_config.py tests/domain/test_domain_purity.py` passes; the last three files are unedited.
- [ ] `git diff --stat` names only `config.py`, `config_interface.py` and the new test file.
- [ ] `src/vibey/domain/*` keeps 100% branch coverage.

## Tests to write first (TDD)
New `tests/domain/test_deploy_target_paid.py` (pure; no marker, no patching). Import
`ConfigError`, `DeployConfig`, `DEPLOY_IAC_BY_TARGET` and `load_config_from_string` from
`vibey.domain.config`, `DeployConfigInterface` from `vibey.domain.interfaces`.
- `test_paid_declares_the_default_paid_cloud` — `load_config_from_string('[project]\nname = "x"\n[deploy]\ntarget = "paid"\n').deploy`
  has `target == "aws"`, `declared_target == "paid"`, `iac == DEPLOY_IAC_BY_TARGET["aws"][0]`.
- `test_paid_resolves_through_a_stored_project_config` — `DeployConfig.from_mapping({"deploy": {"target": "paid"}})`
  has `target == "aws"` and `declared_target == "paid"`.
- `test_a_named_target_is_not_a_declaration` — parametrized over `"openstack"`, `"azure"`, `"aws"`:
  `declared_target == ""` and `target` is the value written.
- `test_the_default_stays_sovereign` — `load_config_from_string('[project]\nname = "x"\n').deploy`
  has `target == "openstack"` and `declared_target == ""` (8.a).
- `test_paid_takes_only_an_iac_its_default_cloud_runs` — `[deploy]\ntarget = "paid"\niac = "heat"\n`
  raises `ConfigError` whose `.path == "deploy.iac"`.
- `test_the_declaration_is_outside_equality` — `DeployConfig.from_mapping({"deploy": {"target": "paid"}}) == DeployConfig.from_mapping({"deploy": {"target": "aws"}})`.
- `test_target_line_names_the_declaration` — the paid config's `target_line()` equals
  `"aws (declared 'paid': AWS is the default paid cloud, sub-doctrine 8.b)"`; `DeployConfig().target_line() == "openstack"`.
- `test_an_unknown_target_offers_the_declaration` — `target = "gcp"` raises `ConfigError` matching
  `the targets with an adapter` and `or 'paid' for 8.b's default paid cloud`.
- `test_case_matters` — `target = "Paid"` raises `ConfigError` with `.path == "deploy.target"`.
- `test_the_interface_declares_the_declaration` — `isinstance(DeployConfig(), DeployConfigInterface)`.

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
- Showing the resolution in `vibey deploy status` (`gap-deploy-target-status`).
- Adding `"aws"` to `DEPLOY_IAC_BY_TARGET` / `DEPLOY_REGION_BY_TARGET` (`gap-aws-target`, a child of
  `gap-spike-aws-iac`), and anything that deploys to AWS.
- The engines' `paidloop` word (ADR-0046 §1) and vibey-gh's `[platform] kind = "paid"` (`gap-gh-platform-paid`).
- CHANGELOG.md, docs/ (for example `docs/reference/configuration.md`'s `[deploy]` table), ADRs,
  CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).

Commit as `feat(config): [deploy] target = "paid" resolves to aws, 8.b's default paid cloud`. Do not push.

## Lane card
- **Depends on:** `gap-paid-defaults`, `openstack-client-p1`, `gap-aws-target`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/domain/test_config.py`, `tests/domain/test_deploy_target_config.py`,
  `tests/domain/test_domain_purity.py`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
