## Title
feat(domain): the five surface-lane errors, each naming its remedy

## Why
Draft ADR-0047 (`specs/ADR-surface-lanes.md` §2, §5, §6, §12) names five errors the surface
lanes raise: a malformed message, a lane that is unavailable, an operation that is parked, a
payload too large for the bus, and `queue` transport with no AMQP URL. §6 requires that
`SurfaceLaneUnavailable` and `SurfaceOperationParked` **subclass `RuntimeError`**, "so any code
that handles today's adapter errors handles these too" (every sovereign adapter raises
`RuntimeError` today, for example `src/vibey/infrastructure/tracker/plane.py:64`), and that
their messages name the command to run. §2 requires `SurfaceTransportNotConfigured` to name
both remedies, as `DatabaseNotConfigured` does (`src/vibey/bootstrap.py:641-648`). ADR-0047
lanes S01–S03 need them first, so they land alone. The domain stays pure (non-negotiable 4).

## Required behaviour
Append to `src/vibey/domain/errors.py` (after the last class; other lanes append too):

1. `class MalformedSurfaceMessage(VibeyError)`: `__init__(self, reason: str)`; keeps
   `self.reason`; message `f"malformed surface message: {reason}"`.
2. `class SurfaceLaneUnavailable(VibeyError, RuntimeError)`:
   `__init__(self, surface: str, reason: str)`; keeps `surface` and `reason`; message
   `f"the {surface} surface lane is unavailable: {reason}. Start it with `vibey surface serve {surface}`, and check the bus (VIBEY_BUS_AMQP_URL)."`
3. `class SurfaceOperationParked(VibeyError, RuntimeError)`:
   `__init__(self, surface: str, operation: str, op_id: str)`; keeps all three; message
   `f"{surface}.{operation} (op {op_id}) is parked: its outcome is unknown, or it failed where nobody was waiting. See `vibey surface dead-letters --surface {surface}`; a person decides with `vibey surface requeue <id>`."`
4. `class SurfacePayloadTooLarge(VibeyError, ValueError)`:
   `__init__(self, surface: str, operation: str, size: int, limit: int)`; keeps all four;
   message `f"{surface}.{operation} encodes to {size} bytes, over the {limit}-byte limit ([surfaces] inline_max_bytes, VIBEY_SURFACES_INLINE_MAX_BYTES)"`.
5. `class SurfaceTransportNotConfigured(VibeyError)`: no arguments; message, verbatim:
   ```
   [surfaces] transport is "queue" but no AMQP URL is configured. Either
     export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/
   or keep every surface in-process (sub-doctrine 8.f is then not held):
     export VIBEY_SURFACES_TRANSPORT=direct
   ```
The backticks in 2 and 3 are literal characters in the message.

## Where to change
- `src/vibey/domain/errors.py` (append five classes; copy the style of `EscalationExhausted`, `:24-29`).
- New `tests/domain/test_surface_errors.py`.

## Acceptance criteria
- [ ] `issubclass(SurfaceLaneUnavailable, RuntimeError)` and `issubclass(SurfaceOperationParked, RuntimeError)`; both are `VibeyError`s.
- [ ] `issubclass(SurfacePayloadTooLarge, ValueError)`.
- [ ] Each message contains the remedy named above (the serve command, the dead-letters command, the key and variable, both exports).
- [ ] `tests/domain/test_domain_purity.py` passes; 100% `domain/` branch coverage.

## Tests to write first (TDD)
`tests/domain/test_surface_errors.py` (no service):
- `test_lane_unavailable_is_a_runtime_error_naming_the_serve_command`
- `test_parked_is_a_runtime_error_naming_the_dead_letters_command`
- `test_payload_too_large_names_the_key_and_the_variable`
- `test_transport_not_configured_names_both_remedies`
- `test_malformed_message_keeps_its_reason`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/domain/test_surface_errors.py tests/domain/test_errors.py tests/domain/test_domain_purity.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Raising any of them (later lanes). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md
  and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit
  locally with the Title as the subject.

## Lane card
- **Depends on:** none.
- **Shares a file with:** `src/vibey/domain/errors.py` (R06, R19, T03, T15 each append one exception; append after whatever is last).
- **Must keep passing unchanged:** `tests/domain/test_errors.py`, `tests/domain/test_domain_purity.py`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file. Change existing files with `edit_file` or a checked replacement; add tests by appending or in a new file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
