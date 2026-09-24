## Title
feat(measure): every surface port is measured at the composition root

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`): "Nothing runs unmeasured."
`build_app` composes the twelve sovereign surface ports and hands them out unmeasured
(`src/vibey/bootstrap.py:751-914`, yielded at `:939-950`). `bootstrap.py` is the sole composition
root (CLAUDE.md), so wrapping each port there, once, with lane `gap-measure-surfaces-1`'s
`SurfaceMeter`, measures every caller of every surface, the in-memory defaults included, and
registers the meter as a `MeasurementSource` for the worker's ticker (lane `gap-measure-ticker`).

## Required behaviour
1. In `build_app`, before the yield, build
   `surfaces = SurfaceMeter(clock=clock, instance=platform.node())` (`clock` is the one
   `SystemClock()` lane `gap-measure-queue-sampler` binds).
2. The yield passes every surface through it, with these exact names and Protocols:
   `tracker=surfaces.wrap("tracker", tracker_port, IssueTrackerPort)`,
   `docs=surfaces.wrap("docs", docs_port, DocsPort)`,
   `secrets=surfaces.wrap("secrets", secrets_port, SecretsPort)`,
   `files=surfaces.wrap("files", files_port, FilesPort)`,
   `email=surfaces.wrap("email", email_port, EmailPort)`,
   `sms=surfaces.wrap("sms", sms_port, SmsPort)`,
   `messaging=surfaces.wrap("messaging", messaging_port, MessagingPort)`,
   `config_store=surfaces.wrap("config_store", config_store_port, ConfigStorePort)`,
   `cache=surfaces.wrap("cache", cache_port, CachePort)`,
   `bus=surfaces.wrap("bus", bus_port, BusPort)`,
   `blob=surfaces.wrap("blob", blob_port, BlobPort)`,
   `siem=surfaces.wrap("siem", siem_port, SiemPort)`.
3. `measurement_sources` gains `surfaces` after the `JobQueueSampler`.
4. Once ADR-0047's lane host composes surfaces (`surfaces-lane-host`), whatever port it hands to
   `AppResources` is the one wrapped here; that lane rebases onto these lines rather than
   bypassing them (say so in a comment above the first `wrap`).

## Where to change
- `src/vibey/bootstrap.py` only (`edit_file`; import `SurfaceMeter` and the twelve Protocols from
  `vibey.application.interfaces`).
- Append to `tests/test_bootstrap.py`.

## Acceptance criteria
- [ ] An AST test finds, in `build_app`'s `AppResources(` call, each of the twelve keywords bound
      to a `Call` of `surfaces.wrap` whose first argument is that keyword's name as a string
      literal and whose third is the Protocol above.
- [ ] Against a migrated database (integration), `resources.cache` is a `MeasuredSurface` and a
      `CachePort`, a `set`/`get` round trip works, and the `SurfaceMeter` in
      `resources.measurement_sources` then collects a `cache.get` and a `cache.set` measurement.
- [ ] Every existing surface and bootstrap test passes unchanged.

## Tests to write first (TDD)
Append to `tests/test_bootstrap.py`:
- `test_build_app_wraps_every_surface_port` (the AST check; no database)
- `test_a_surface_call_is_collected_by_the_meter` (`@pytest.mark.integration`, skipped when
  `VIBEY_TEST_DATABASE_URL` is unset; `async with build_app(url=dsn) as resources`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/infrastructure/measure
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/cli/test_operational_commands.py -m integration
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The meter (`gap-measure-surfaces-1`); ADR-0047's lanes and their own measurement (S32).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): every surface port is measured at the composition root`. Do not push.

## Lane card
- **Depends on:** `gap-measure-surfaces-1`, `gap-measure-queue-sampler`.
- **Shares a file with:** `bootstrap.py` (the R/T chain and `surfaces-lane-host`); rebase and keep
  their code.
- **Must keep passing unchanged:** `tests/test_bootstrap.py`, every surface adapter test, the
  protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
