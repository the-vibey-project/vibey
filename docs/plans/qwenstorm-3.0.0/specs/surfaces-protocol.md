## Title
feat(domain): the versioned surface wire protocol — request, reply and dead letter, with a strict codec

## Why
Draft ADR-0047 §5 (`specs/ADR-surface-lanes.md`) defines three JSON messages and a strict,
versioned codec "like R19's": decoding rejects an unknown schema, a missing key, **any extra
key**, a wrong type, a naive datetime, an unknown surface or operation, and an `op_id` outside
`^[A-Za-z0-9._:-]{1,200}$`. "An extra key is always rejected, so a `resets_at` can never ride
along" (non-negotiable 2, "Credits ≠ rate limit"), and "no reply claims more than the
operation" (non-negotiable 3). ADR-0044's convention of `start_by` in the body instead of an
AMQP expiration (§13 of ADR-0044) carries over. Pure, so the domain owns it. ADR-0047 lane S03.

The request also carries its caller: the calling process, and, when the caller is working for a
project, that project and job. That is what lets the lane write each operation to the ledger
(sub-doctrine 7.c, "the thorough ledger"), which is project-scoped (`event.project_id` is
`NOT NULL`, `src/vibey/domain/ledger.py` `LedgerEvent.project_id`).

## Required behaviour
In the new `src/vibey/domain/surface_protocol.py`:

1. Constants: `REQUEST_SCHEMA = "vibey.surface.request/1"`, `REPLY_SCHEMA = "vibey.surface.reply/1"`,
   `DEAD_SCHEMA = "vibey.surface.dead/1"`, `ID_PATTERN = r"^[A-Za-z0-9._:-]{1,200}$"`,
   `DETAIL_MAX = 2000`.
2. Enums: `ReplyStatus` (`OK="ok"`, `NOT_FOUND="not_found"`, `ERROR="error"`,
   `REJECTED="rejected"`, `EXPIRED="expired"`, `PARKED="parked"`) and `DeadLetterReason`
   (`MALFORMED="malformed"`, `WRONG_SURFACE="wrong_surface"`, `DELIVERY_LIMIT="delivery_limit"`,
   `RETRIES_EXHAUSTED="retries_exhausted"`, `FAILED="failed"`, `EXPIRED="expired"`,
   `OUTCOME_UNKNOWN="outcome_unknown"`, `KEY_REUSED="key_reused"`).
3. Frozen, slotted dataclasses, each validating in `__post_init__` (a violation raises
   `ValueError` naming the field):
   - `SurfaceCaller(process: str, project_id: UUID | None = None, job_id: UUID | None = None)`;
     `process` non-empty; a `job_id` without a `project_id` is refused.
   - `SurfaceRequest(request_id: str, op_id: str, surface: SurfaceName, operation: str, args: Mapping[str, object], requested_at: datetime, start_by: datetime, caller: SurfaceCaller, grant: bool = False)`;
     both ids match `ID_PATTERN`; both datetimes are timezone-aware; `start_by >= requested_at`.
   - `SurfaceReply(request_id: str, op_id: str, status: ReplyStatus, result: object, detail: str, replayed: bool, instance: str, finished_at: datetime)`;
     `len(detail) <= DETAIL_MAX`; aware datetime; non-empty instance.
   - `SurfaceDeadLetter(surface: SurfaceName, operation: str, op_id: str, request_id: str, reason: DeadLetterReason, detail: str, attempts: int, delivery_count: int, instance: str, dead_lettered_at: datetime, request: Mapping[str, object], retained: bool)`;
     counts `>= 0`; `len(detail) <= DETAIL_MAX`; aware datetime. `message_id` property returns
     `f"{request_id}:{reason.value}"` (ADR §5 table).
4. `class SurfaceProtocolCodec`, stateless:
   - `encode_request(r) -> dict[str, object]` with exactly the keys `schema, request_id, op_id,
     surface, operation, args, requested_at, start_by, caller, grant`; `caller` is exactly
     `{"process": str, "project_id": str | None, "job_id": str | None}`; datetimes are
     `isoformat()`.
   - `encode_reply(r)`: exactly `schema, request_id, op_id, status, result, detail, replayed, instance, finished_at`.
   - `encode_dead(d)`: exactly `schema, surface, operation, op_id, request_id, reason, detail,
     attempts, delivery_count, instance, dead_lettered_at, request, retained`.
   - `decode_request`, `decode_reply`, `decode_dead` take `Mapping[str, object]` and raise
     `MalformedSurfaceMessage` (lane `surfaces-errors`) on: a wrong or missing `schema`; a
     missing or extra key (top level and inside `caller`); a wrong type (a `bool` is never
     accepted where an `int` is required, and an `int` never where a `bool` is); an unparseable
     or naive datetime; an unknown surface (`"bus"` included); an operation the catalogue does
     not know for that surface (`CATALOGUE.get` raises; `_ping` is known); an id outside
     `ID_PATTERN`; a malformed UUID; `args` or `request` not a JSON object with `str` keys;
     `detail` too long; or anything the dataclass refuses.
   - `request_to_bytes`, `reply_to_bytes`, `dead_to_bytes`:
     `json.dumps(encode_x(v), sort_keys=True, separators=(",", ":")).encode("utf-8")`.
     `request_from_bytes`, `reply_from_bytes`, `dead_from_bytes`: invalid UTF-8, invalid JSON
     or a non-object raise `MalformedSurfaceMessage`.
   - `clip(detail: str) -> str` returns `detail[:DETAIL_MAX]`, for producers.
5. `SURFACE_PROTOCOL: Final[SurfaceProtocolCodecInterface] = SurfaceProtocolCodec()`.
6. `src/vibey/domain/interfaces/surface_protocol_interface.py`:
   `@runtime_checkable class SurfaceProtocolCodecInterface(Protocol)` with every codec method;
   exported from `src/vibey/domain/interfaces/__init__.py`.
7. Pure: no clock (every time is a field), I/O or async.

## Where to change
- New `src/vibey/domain/surface_protocol.py`, `src/vibey/domain/interfaces/surface_protocol_interface.py`.
- `src/vibey/domain/interfaces/__init__.py` (export).
- New `tests/domain/test_surface_protocol.py`. If R06's `src/vibey/domain/job_dispatch.py`
  exists, copy its codec style.

## Acceptance criteria
- [ ] Hypothesis: `decode_x(encode_x(v)) == v` and `x_from_bytes(x_to_bytes(v)) == v` for all three messages.
- [ ] Every malformation in behaviour 4 raises `MalformedSurfaceMessage` (one parametrized case each), including a request carrying an extra `resets_at` key.
- [ ] A request for surface `bus` and a request for `cache.nope` are refused; `cache._ping` is accepted.
- [ ] `to_bytes` output is byte-stable (sorted keys, no spaces).
- [ ] `test_domain_purity.py` passes; 100% `domain/` branch coverage.

## Tests to write first (TDD)
`tests/domain/test_surface_protocol.py` (no service):
- `test_request_round_trip_property` (Hypothesis)
- `test_reply_round_trip_property` (Hypothesis)
- `test_dead_letter_round_trip_property` (Hypothesis)
- `test_decode_rejects_each_malformation` (parametrized)
- `test_an_extra_resets_at_key_is_refused`
- `test_the_bus_and_unknown_operations_are_refused`
- `test_bytes_are_stable_and_bad_bytes_are_malformed`
- `test_dataclasses_validate_their_fields`
- `test_dead_letter_message_id_is_request_and_reason`
- `test_codec_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/domain/test_surface_protocol.py tests/domain/test_domain_purity.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Typing `args` per operation (`surfaces-args-codec`) and redaction (`surfaces-redaction`).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `surfaces-catalogue`, `surfaces-errors`.
- **Shares a file with:** `src/vibey/domain/interfaces/__init__.py` (exports only).
- **Must keep passing unchanged:** `tests/domain/*`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from a sibling file.
  - Every new class has a `@runtime_checkable` Protocol beside it; frozen dataclasses and enums need none.
  - The default run needs no service; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
