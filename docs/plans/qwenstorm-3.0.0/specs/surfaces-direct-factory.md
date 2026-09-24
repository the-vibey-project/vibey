## Title
refactor(surfaces): DirectSurfaceFactory is build_app's surface selection in one class, and passes the configured adapter timeout to every adapter

## Why
Draft ADR-0047 §2 (`specs/ADR-surface-lanes.md`): "The lane uses the same adapters `direct` does.
`DirectSurfaceFactory` (lane S14) is today's selection code (`bootstrap.py:751-914`) moved into
one class. `direct` calls it inside every process; the lane calls it once, inside itself.
Nothing is implemented twice." Today that code is twelve inline `if resolved_config … else`
blocks in `build_app` (`src/vibey/bootstrap.py:751-914` at integration `d3b4a388`), each building
a sovereign adapter or its in-memory twin.

Moving it also closes `issue-audit/gaps.md` K3's last step: the adapter lanes gave every adapter
a `timeout` keyword; this factory passes `[surfaces] adapter_timeout_seconds` (lane
`surfaces-config`) to each of them, so "every sovereign adapter passes a bounded timeout, from
config, to every network call". ADR-0047 lane S14.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/direct_factory.py`:

1. `@dataclass(frozen=True, slots=True) class DirectSurfaces` with the twelve fields
   `tracker, docs, secrets, files, email, sms, messaging, config_store, cache, bus, blob, siem`,
   typed by their ports, and `get(self, surface: SurfaceName) -> object` (the port for a surface;
   `SurfaceName.CONFIGURATION` → `config_store`).
2. `class DirectSurfaceFactory`:
   `__init__(self, config: VibeyConfig | None, *, opener: UrlOpener = urllib.request.urlopen, smtp: SmtpConnectorInterface = STDLIB_SMTP, redis_connect: SocketConnectorInterface = TCP_CONNECTOR)`.
   The timeout is `config.surfaces.adapter_timeout_seconds` when `config` is given, else
   `SurfacesConfig().adapter_timeout_seconds`.
   - One method per surface — `tracker()`, `docs()`, `secrets()`, `files()`, `email()`, `sms()`,
     `messaging()`, `config_store()`, `cache()`, `bus()`, `blob()`, `siem()` — each with **exactly**
     today's condition and constructor arguments from `bootstrap.py`, plus `timeout=` and the
     injected `opener=` (HTTP adapters), `smtp=` (email) or `connect=` (Redis). The lazy imports
     `build_app` used for config store, cache, bus, blob and SIEM become ordinary imports.
   - `build(self, surface: SurfaceName) -> object` dispatches to those methods.
   - `all(self) -> DirectSurfaces` builds all twelve.
   - `backend_name(self, surface) -> str`: `type(self.build(surface)).__name__`;
     `is_real(self, surface) -> bool`: the name does not start with `"InMemory"`.
3. **`build_app`** (`src/vibey/bootstrap.py`): replace the twelve selection blocks (from the
   `if (` whose first condition is `resolved_config.tracker.url` through the end of the SIEM
   `else:` branch, immediately before `yield AppResources(`) with
   `direct = DirectSurfaceFactory(resolved_config).all()`, and pass `tracker=direct.tracker` …
   `siem=direct.siem` in the `yield`. Remove every import that becomes unused (ruff F401 names
   them). If lane `fakes-bootstrap-seam` or `surfaces-env` has moved these lines, apply the same
   replacement where they now are; behaviour must not change.
4. **Interface** `surface_lanes/interfaces/direct_factory_interface.py`:
   `@runtime_checkable class DirectSurfaceFactoryInterface(Protocol)` with the fifteen methods;
   exported. Registry: `DirectSurfaceFactoryInterface → functools.partial(DirectSurfaceFactory, None)`
   (every surface in memory), in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/direct_factory.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/direct_factory_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- `src/vibey/bootstrap.py` (the block, the yield arguments, the imports).
- New `tests/infrastructure/surface_lanes/test_direct_factory.py`.

## Acceptance criteria
- [ ] With `config=None`, `all()` holds the twelve `InMemory*` classes and `is_real` is false for every surface.
- [ ] With a config naming every surface (the fixture `test_build_app_wires_concrete_adapters_from_config` uses), each field is the same sovereign class `build_app` builds today, and `is_real` is true.
- [ ] With `[surfaces] adapter_timeout_seconds = 7`, one call through each HTTP adapter (tracker, docs, secrets, files, SMS, messaging, configuration, blob, SIEM, bus) records `timeout == 7` on `InMemoryHttpServer`, the email connector records 7 (`InMemorySmtpServer.timeouts`), and the Redis connector is given 7.
- [ ] `grep -n "PlaneTrackerAdapter\|InMemoryTracker" src/vibey/bootstrap.py` prints nothing; `build_app`'s two wiring tests in `tests/infrastructure/test_sovereign_surfaces.py` pass unchanged.
- [ ] 100% `infrastructure/` branch coverage; `mypy --strict src/vibey` clean.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_direct_factory.py` (no service; `InMemoryHttpServer` with `route_prefix` per base URL, `InMemorySmtpServer`, `InMemoryRedis().connector()`):
- `test_no_config_is_all_in_memory`
- `test_a_full_config_builds_every_sovereign_adapter` (parametrized per surface)
- `test_every_adapter_gets_the_configured_timeout` (parametrized per surface)
- `test_build_and_get_agree_for_every_surface_name`
- `test_backend_names_and_realness`
- `test_factory_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surface_lanes tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_sovereign_surfaces.py tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Choosing `queue` or `direct` (`surfaces-transport-selection`, `surfaces-composition`).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the Title
  as the subject.

## Lane card
- **Depends on:** `surfaces-config`, `surfaces-catalogue`, `surfaces-caller-scope` (package), every adapter lane (`surfaces-adapter-tracker`, `surfaces-adapter-docs`, `surfaces-adapter-messaging`, `surfaces-adapter-siem`, `surfaces-adapter-email`, `surfaces-adapter-sms`, `surfaces-adapter-timeouts-secrets-files`, `surfaces-adapter-timeouts-config-blob-bus`), `surfaces-env` (#323 edits the lines before this block), `fakes-sockets` (`TCP_CONNECTOR`, `connect=`).
- **Shares a file with:** `src/vibey/bootstrap.py` (R02 → T15 → R17 → T25 → R27 → R28 → T26, `orm-app-resources`, `fakes-bootstrap-seam`, `surfaces-env`). Keep everything they added.
- **Must keep passing unchanged:** `tests/infrastructure/test_sovereign_surfaces.py`, `tests/test_bootstrap.py`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file. `bootstrap.py` is long: `edit_file` or a checked replacement only.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam (`opener=`, `smtp=`, `redis_connect=`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
