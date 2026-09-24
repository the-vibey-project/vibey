## Title
feat(surfaces): SurfaceTransportSelector chooses queued or direct surfaces from one key — loudly, and never silently falling back

## Why
Draft ADR-0047 §2 (`specs/ADR-surface-lanes.md`): `[surfaces] transport` chooses between
`queue` (`Queued<Surface>` adapters that publish to the lanes; the default after
`surfaces-default-flip`) and `direct` (today's adapters, "kept per 12.c for unit tests and for
deployments without a bus"). Three rules:

- "**No silent fallback.** `queue` without an AMQP URL fails at start with
  `SurfaceTransportNotConfigured`, which names both remedies" (ADR-0002's and ADR-0044 §1's
  posture);
- "**`direct` is loud after the flip.** From S33 on, `build_app` logs a warning that 8.f is not
  held when `direct` is chosen and any surface resolved to a real adapter";
- the bus stays direct in both transports (§11; 8.f's own text).

The selector is a small class over injected factories, so the choice is tested with no broker
and `build_app` only wires it (`surfaces-composition`). ADR-0047 lane S26.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/selection.py`:

1. `@dataclass(frozen=True, slots=True) class SelectedSurfaces`: `transport: str`, the twelve
   ports (`tracker, docs, secrets, files, email, sms, messaging, config_store, cache, bus, blob, siem`),
   and `lane_client: SurfaceLaneClientInterface | None`.
2. `class SurfaceTransportSelector`,
   `__init__(self, *, settings: SurfacesConfigInterface, direct: DirectSurfaceFactoryInterface, amqp_url: str | None, lane_client: Callable[[], SurfaceLaneClientInterface], logger: Logger, default_transport: str = DEFAULT_SURFACE_TRANSPORT, catalogue: SurfaceCatalogueInterface = CATALOGUE)`.
   `select(self) -> SelectedSurfaces`:
   - `settings.transport == "direct"`: `d = direct.all()`; when `default_transport == "queue"`
     and any surface `direct.is_real(s)`, log `surface.transport.direct` at `warning` with
     `surfaces` (the real ones, sorted) and
     `message="sub-doctrine 8.f is not held: these surfaces are reached in-process, not through their lanes (VIBEY_SURFACES_TRANSPORT=direct)"`.
     Return `SelectedSurfaces("direct", <the twelve from d>, lane_client=None)`. The lane
     client factory is never called.
   - `settings.transport == "queue"`: `amqp_url` is `None` or blank → raise
     `SurfaceTransportNotConfigured()`. Otherwise `client = lane_client()` (once) and return
     `SelectedSurfaces("queue", tracker=QueuedTracker(client), docs=QueuedDocs(client), secrets=QueuedSecrets(client), files=QueuedFiles(client), email=QueuedEmail(client), sms=QueuedSms(client), messaging=QueuedMessaging(client), config_store=QueuedConfigStore(client), cache=QueuedCache(client), bus=direct.bus(), blob=QueuedBlob(client), siem=QueuedSiem(client), lane_client=client)`,
     after logging `surface.transport.queue` at `info` with the eleven surface names.
   - Anything else raises `ValueError` (the config parser already refuses it; this guards a
     hand-built settings object).
3. **Interface** `surface_lanes/interfaces/selection_interface.py`:
   `@runtime_checkable class SurfaceTransportSelectorInterface(Protocol)` with `select`;
   exported. Registry: the real selector over `DirectSurfaceFactory(None)`,
   `SurfacesConfig()` and a `RecordingSurfaceLaneClient` factory, in `REGISTRY` and
   `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/selection.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/selection_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_selection.py`.

## Acceptance criteria
- [ ] Default settings select `direct`, the twelve in-memory ports, no lane client, no warning, and the lane-client factory is not called.
- [ ] `default_transport="queue"` with `direct` and one configured surface logs the 8.f warning naming exactly that surface; with no real surface it logs nothing.
- [ ] `queue` without a URL raises `SurfaceTransportNotConfigured` whose message holds both remedies; with a URL every surface but the bus is its `Queued*` class over the one client, and the bus is the direct one.
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_selection.py` (no service; `RecordingSurfaceLaneClient`, `RecordingLogger`):
- `test_direct_is_the_default_and_quiet`
- `test_direct_after_the_flip_warns_about_real_surfaces_only`
- `test_queue_without_a_url_names_both_remedies`
- `test_queue_builds_every_queued_adapter_over_one_client`
- `test_the_bus_is_always_direct`
- `test_an_unknown_transport_is_refused`
- `test_selector_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surface_lanes tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Resolving the AMQP URL and building the real client (`surfaces-composition`, over R17's
  `QueueBackendSettings`); a per-surface override (rejected by the ADR as "the quiet exemption
  the operator forbade"). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the
  skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally
  with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-direct-factory`, `surfaces-queued-records`, `surfaces-queued-stores`, `surfaces-queued-sends`, `surfaces-errors`.
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - `[surfaces] transport` stays `direct` by default until `surfaces-default-flip`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
