## Title
feat(surfaces): QueuedSecrets, QueuedFiles, QueuedBlob and QueuedCache implement their ports through the surface lanes

## Why
Draft ADR-0047 §2 and §6 (`specs/ADR-surface-lanes.md`): in `queue` transport each port is a
`Queued<Surface>` adapter over `SurfaceLaneClient`. This lane covers the four storage surfaces:
secrets (OpenBao), files (Nextcloud), blob storage (Garage) and the cache (Valkey). Two of them
carry bytes, which travel as base64 within `inline_max_bytes` (§5); a larger payload is refused
before it is published with `SurfacePayloadTooLarge` — "a regression for large objects, stated
rather than hidden" ("Where the operator's rule … falls short", item 9). The cache pays a broker
round trip per read; §10 states that cost and `surfaces-bench` measures it. ADR-0047 lane S21.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/queued_stores.py`, four classes, each
`__init__(self, client: SurfaceLaneClientInterface)`:

1. `QueuedSecrets(SecretsPort)`: `get_secret(key) -> str` (`{"key"}`);
   `set_secret(key, value) -> None` (`{"key", "value"}`).
2. `QueuedFiles(FilesPort)`: `upload_file(remote_path, content) -> str`
   (`{"remote_path", "content"}`, `content` passed as `bytes`); `download_file(remote_path) -> bytes`.
3. `QueuedBlob(BlobPort)`: `put_blob(bucket, key, content, content_type=None) -> str`
   (`{"bucket", "key", "content", "content_type"}`); `get_blob(bucket, key) -> bytes`.
4. `QueuedCache(CachePort)`: `get(key) -> str | None`; `set(key, value, ttl_seconds=None) -> None`
   (`{"key", "value", "ttl_seconds"}`); `delete(key) -> None`.
5. Every call is `await client.call(SurfaceName.<S>, "<operation>", <mapping>)` with the names
   above (none of these operations takes an idempotency key). A result of the wrong type
   (`str`, `bytes`, `str | None`) raises `RuntimeError(f"{surface}.{operation} answered {type(result).__name__}, not {expected}")`.
   Client exceptions (`KeyError`, `FileNotFoundError`, `SurfacePayloadTooLarge`,
   `SurfaceLaneUnavailable`, `RuntimeError`) propagate unchanged.
6. **Interfaces** in `surface_lanes/interfaces/queued_stores_interface.py`: one
   `@runtime_checkable` Protocol per class extending its port; exported. **Registry**: each over
   a fresh `RecordingSurfaceLaneClient`, in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/queued_stores.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/queued_stores_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_queued_stores.py`.

## Acceptance criteria
- [ ] Each of the nine methods calls the client once with exactly the surface, operation and mapping above, and returns the scripted result.
- [ ] `download_file` and `get_blob` return `bytes`; `get` returns `None` for a scripted `None`.
- [ ] A wrongly typed answer raises `RuntimeError`; scripted `FileNotFoundError` and `SurfacePayloadTooLarge` propagate.
- [ ] Each class satisfies its port under `isinstance` and `mypy --strict`.
- [ ] 100% `infrastructure/` branch coverage; the parity test passes.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_queued_stores.py` (no service; `RecordingSurfaceLaneClient`):
- `test_each_method_is_one_lane_call` (parametrized over the nine methods)
- `test_bytes_come_back_as_bytes`
- `test_a_cache_miss_is_none`
- `test_a_wrongly_typed_answer_is_an_error`
- `test_lane_errors_propagate_unchanged`
- `test_queued_stores_satisfy_their_ports`

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
- Staging large payloads by reference (a follow-up the ADR names). The bus (no lane, §11).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the Title
  as the subject.

## Lane card
- **Depends on:** `surfaces-lane-client`.
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
