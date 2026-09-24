## Title
feat(surfaces): QueuedEmail, QueuedSms, QueuedMessaging and QueuedSiem hand each send to its lane and return once the broker holds it

## Why
Draft ADR-0047 §7 (`specs/ADR-surface-lanes.md`, "Operations that are one-way: sends"):
`send_email`, `send_sms`, `send_message` and `send_event` use the `accept` mode. "The caller's
`await` returns once the broker has confirmed a persistent publish to the lane's quorum queue.
The send is then durable. If the lane is down it waits, and it goes out when the lane returns."
"Failure no longer reaches the caller … For the SIEM that is already the port's contract
(`siem.py:12-13`). For email, SMS and messaging it is a real change from today, where
`await send_email()` raises on an SMTP error." `[surfaces] sends_await_outcome = true` restores
an answered round trip (12.c); the client (`surfaces-lane-client`) implements both. Each send
takes the optional `idempotency_key` the adapter lanes added. ADR-0047 lane S22.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/queued_sends.py`, four classes, each
`__init__(self, client: SurfaceLaneClientInterface)`:

1. `QueuedEmail(EmailPort)`: `send_email(to_addr, subject, body, *, idempotency_key=None) -> None`
   → `call(SurfaceName.EMAIL, "send_email", {"to_addr", "subject", "body"}, idempotency_key=…)`.
2. `QueuedSms(SmsPort)`: `send_sms(phone_number, message, *, idempotency_key=None)` →
   `{"phone_number", "message"}`.
3. `QueuedMessaging(MessagingPort)`: `send_message(channel_id, message, *, idempotency_key=None)` →
   `{"channel_id", "message"}`.
4. `QueuedSiem(SiemPort)`: `send_event(index, event, *, idempotency_key=None)` →
   `{"index", "event": dict(event)}`.
5. Each returns `None` and discards the client's result. Client exceptions propagate unchanged:
   with the default settings the only ones a caller can see are `SurfaceLaneUnavailable` (the
   broker refused or is unreachable) and `ValueError` / `SurfacePayloadTooLarge` (a caller's
   bug); every later failure is a dead letter, not an exception (§7).
6. The class docstrings say, in one sentence each, that a send returning means "the broker holds
   it", not "it was delivered", and name `vibey surface dead-letters` as where a failure shows.
7. **Interfaces** in `surface_lanes/interfaces/queued_sends_interface.py`: one
   `@runtime_checkable` Protocol per class extending its port; exported. **Registry**: each over
   a fresh `RecordingSurfaceLaneClient`, in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/queued_sends.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/queued_sends_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_queued_sends.py`.

## Acceptance criteria
- [ ] Each send calls the client once with exactly the surface, operation, mapping and key shown, and returns `None`.
- [ ] `send_event` passes a copy of the event (mutating the caller's dict afterwards does not change the recorded call).
- [ ] A scripted `SurfaceLaneUnavailable` propagates unchanged.
- [ ] Each class satisfies its port under `isinstance` and `mypy --strict`, `idempotency_key` included.
- [ ] 100% `infrastructure/` branch coverage; the parity test passes.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_queued_sends.py` (no service; `RecordingSurfaceLaneClient`):
- `test_each_send_is_one_lane_call_with_its_key` (parametrized over the four)
- `test_send_event_copies_the_event`
- `test_an_unavailable_lane_propagates`
- `test_queued_sends_satisfy_their_ports`

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
- The first production sender (`surfaces-consumer-notifications`). CHANGELOG.md, docs/, ADRs,
  CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open
  PRs or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-lane-client`, `surfaces-adapter-email`, `surfaces-adapter-sms`, `surfaces-adapter-messaging`, `surfaces-adapter-siem` (the ports' `idempotency_key`).
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
