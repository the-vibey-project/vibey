## Title
test(vibey-bootstrap): ApplicationBootstrap takes its config-repository factory and telemetry manager by injection, and its tests patch nothing

## Why
`test/services/test_application_bootstrap.py` has 51 patch sites. It decorates test after
test with:
- `@patch("vibey_bootstrap.services.application_bootstrap.create_enhanced_config_repository")`;
- `@patch("vibey_bootstrap.services.application_bootstrap.telemetry_manager")` (`:89-170`, 30 such patches).

The cause is the source. `vibey_bootstrap/services/application_bootstrap.py` imports the
module-level `telemetry_manager` singleton (`:34`), and reads it at `:146`, `:190-192` and
`:247-259`. It calls the module function `create_enhanced_config_repository` to build its
repository. `ApplicationBootstrap` (`:37`) already has an interface, but not these two
collaborators as constructor parameters.

`test/coverage_fill/test_pdf_telemetry_fill.py` (26) and `test_observability_fill.py` (19)
patch the same telemetry singleton from other angles.

## Required behaviour
1. **`ApplicationBootstrap.__init__`** gains two keyword arguments, with the production
   defaults:
   - `config_repository_factory: ConfigRepositoryFactoryInterface = create_enhanced_config_repository`;
   - `telemetry: TelemetryManagerInterface = telemetry_manager`.
   `initialize_application(...)` (`:358`) passes them through. Every read of the singleton
   inside the class becomes `self._telemetry`. Declare the two interfaces beside their
   implementations, in `services/interfaces/`.
2. **`test/fakes/telemetry.py`** — `InMemoryTelemetryManager` (`TelemetryManagerInterface`):
   - `configure()` records the call and sets `tracer` to an in-memory tracer, which records
     spans and events;
   - `try_upgrade_from_config(repo)` reads the App Insights key from the repository, and
     upgrades when it is present, as the real one does;
   - `tracer` is `None` until configured.
   It is registered in `test/fakes/test_port_parity.py`.
3. **Switch the tests:**
   - `test/services/test_application_bootstrap.py` builds `ApplicationBootstrap(config_repository_factory=lambda **kw: EnhancedConfigRepository(provider_factory=InMemoryAppConfiguration(...)), telemetry=InMemoryTelemetryManager())`.
     The fakes come from `fakes-tenant-bootstrap-1`. Every `@patch` goes;
   - in `test/coverage_fill/test_pdf_telemetry_fill.py` and `test_observability_fill.py`,
     every patch of the telemetry singleton or of `application_bootstrap` becomes injection.
     Patches in those files of other targets stay for `fakes-tenant-bootstrap-3`, and remain
     in the baseline.
   - Lower the baseline.

## Where to change
- `vibey_bootstrap/services/application_bootstrap.py`, `vibey_bootstrap/services/interfaces/` (two interfaces).
- New `test/fakes/telemetry.py`; `test/fakes/test_port_parity.py`, `test/patching_baseline.json`,
  `test/services/test_application_bootstrap.py`, `test/coverage_fill/test_pdf_telemetry_fill.py`,
  `test/coverage_fill/test_observability_fill.py`.

## Acceptance criteria
- [ ] `grep -c "@patch\|patch(" src/vibey_tools/bootstrap/test/services/test_application_bootstrap.py` prints `0`.
- [ ] The package suite passes at its coverage level, and mypy passes (as its CI row runs them).

## Tests to write first (TDD)
- `test/fakes/test_telemetry_fake.py`:
  - `test_manager_is_unconfigured_until_configure`
  - `test_upgrade_from_config_reads_the_repository`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/bootstrap && pytest test/ --cov=vibey_bootstrap --cov-report=term
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Transports, the service bus, alerts and the remaining `coverage_fill` targets (`fakes-tenant-bootstrap-3`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-bootstrap-1`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the protected root tests.
- **Standing constraints (every tenant lane):**
  - The tenant's own gates and floor pass on its Python floor (ADR-0022).
  - A fake is a plain class with real in-memory behaviour, and never `unittest.mock`.
  - Substitution happens at a declared seam: a constructor or keyword argument, a typer
    `ctx.obj`, or a parameter with a production default. It never happens by patching an
    import. `monkeypatch.setenv` and `delenv` stay allowed.
  - The tenant keeps its own registry and parity test and its own patching ratchet
    (`test_patching_ratchet.py` plus `patching_baseline.json`) in its test directory. Lower
    the ratchet for every file you convert, and never raise it.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - Protected root tests are never edited. Change existing files with `edit_file`, and never
    rewrite an existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
