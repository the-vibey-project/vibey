## Title
feat(notify): operator notifications reach the Matrix room through the messaging surface — the first production caller of a sovereign surface

## Why
`issue-audit/gaps.md` K2: "No production code uses any surface … Surface ports are read only by
`bootstrap.py` wiring and `tests/infrastructure/test_sovereign_surfaces.py`. Notifications go to
desktop alerts and webhooks (`src/vibey/infrastructure/notify/service.py:14-26`)." Sub-doctrine
8.b makes Matrix the default messaging surface, and draft ADR-0047 ("Who calls them: nobody
yet", `specs/ADR-surface-lanes.md`) says "the first consumer of each surface will be written
against the lane, not migrated to it". Operator notifications (a gate raised, a phase moved, a
budget crossed, a run completed — `infrastructure/notify/events.py:11-15`) are the natural first
caller: project-scoped (so the lane ledgers them, 7.c), one-way (the `accept` mode, §7), and
already defined as "never a failure path" (`service.py:79-81`).

The event's idempotency key makes a replayed notification land once (Matrix deduplicates the
transaction id, `surfaces-adapter-messaging`). The caller binds the event's project around the
send (`surfaces-caller-scope`), so the lane's ledger event lands in that project's ledger. It is
opt-in per project, like desktop and webhooks (12.c), through `[notifications] matrix = true`
and the room `[messaging] room_id` the chart already sets (`VIBEY_MESSAGING_ROOM_ID`,
`deploy/helm/vibey/templates/worker.yaml:210-211`).

## Required behaviour
1. **`src/vibey/domain/config.py`**: `NotificationsConfig` gains `matrix: bool = False`, parsed
   from `[notifications] matrix` (a `bool`, error on anything else, dotted key
   `notifications.matrix`); `NotificationsConfigInterface` gains the property.
2. **`src/vibey/infrastructure/notify/matrix.py`** (new), `class MatrixNotificationPublisher`:
   `__init__(self, messaging: MessagingPort, *, room_id: str, caller: SurfaceCallerScopeInterface | None = None)`
   (an empty `room_id` raises `ValueError`).
   `async publish(self, event: NotificationEvent) -> bool`:
   - `text = f"[vibey] {event.title}\n{event.message}"`;
   - `key = f"notify.{event.project_id}.{event.kind.value.replace('_', '-')}.{digest}"`, where
     `digest` is the first 32 hex characters of the SHA-256 of `canonical_bytes` of
     `{"kind", "project_id", "title", "message", "payload"}` (the event without its timestamp),
     so a replay of the same event has the same key and matches the lane's `ID_PATTERN`;
   - inside `caller.bind(project_id=event.project_id)` when a caller scope is given, `await
     messaging.send_message(room_id, text, idempotency_key=key)`;
   - returns True; any `Exception` is swallowed and returns False (the service's contract).
   Interface `MatrixNotificationPublisherInterface` in
   `src/vibey/infrastructure/notify/interfaces/matrix_interface.py` (the `notify/interfaces/`
   package exists after `fakes-sockets`), exported.
3. **`NotificationService`** (`notify/service.py`): `__init__` gains
   `matrix: MatrixNotificationPublisherInterface | None = None`, kept by `for_project_config`
   only when the project's `notifications` table has `matrix` true. `notify`'s early return
   also requires the Matrix channel to be off. `dispatch` adds `matrix.publish(event)` as one
   more task when present, and only then adds `"matrix": <bool>` to its result, so every existing
   result dictionary is unchanged.
4. **`build_app`**: build `notifications` after `selected = surface_composition.select()`
   (lane `surfaces-composition`), as
   `NotificationService(matrix=MatrixNotificationPublisher(selected.messaging, room_id=resolved_config.messaging.room_id, caller=surface_composition.caller))`
   when `resolved_config` has a `messaging.room_id`, else `NotificationService()` as today.
   Nothing else moves.
5. **Registry.** `MatrixNotificationPublisherInterface → functools.partial(MatrixNotificationPublisher, InMemoryMessaging(), room_id="!room:test")`
   in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- `src/vibey/domain/config.py`, `src/vibey/domain/interfaces/config_interface.py`.
- New `src/vibey/infrastructure/notify/matrix.py`, `src/vibey/infrastructure/notify/interfaces/matrix_interface.py`;
  `src/vibey/infrastructure/notify/interfaces/__init__.py`; `src/vibey/infrastructure/notify/service.py`.
- `src/vibey/bootstrap.py` (the `notifications` construction only); `tests/fakes/registry.py`.
- New `tests/infrastructure/notify/test_matrix_notifications.py`; append to `tests/domain/test_surfaces_config.py`.

## Acceptance criteria
- [ ] Publishing an event sends one message to the room with the `[vibey]` text and the key; publishing the same event again (a new timestamp) sends nothing more through `InMemoryMessaging`.
- [ ] The send runs inside the event's project binding (a messaging class in the test records `caller.current()` at call time).
- [ ] A messaging port that raises makes `publish` return False; the service result has `"matrix": False`, and nothing raises.
- [ ] A project without `matrix = true` sends nothing to Matrix, and its result dictionaries are exactly today's (the existing notify tests pass unchanged).
- [ ] Through `InMemoryApp` with `[messaging] room_id` set and a project whose config enables Matrix, `resources.notifications.notify(...)` puts one message in `resources.messaging`; with `transport = queue` over the in-memory broker and a running messaging lane (the `surfaces-contracts-lane` helper), the lane records a `SurfaceOperationRecorded` event in that project's ledger.
- [ ] `notifications.matrix = "yes"` is refused naming the key; 100% branch coverage of `domain/` and `infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/notify/test_matrix_notifications.py` (no service):
- `test_an_event_is_one_message_with_a_stable_key`
- `test_a_replayed_event_is_delivered_once`
- `test_the_send_is_bound_to_the_event_s_project`
- `test_a_failing_room_never_fails_the_work`
- `test_matrix_is_opt_in_per_project_and_leaves_old_results_unchanged`
- `test_build_app_wires_matrix_when_a_room_is_configured`
- `test_a_queued_notification_is_ledgered_in_its_project`
- `test_publisher_satisfies_its_interface`
Append to `tests/domain/test_surfaces_config.py`:
- `test_notifications_matrix_is_a_boolean`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/notify tests/domain tests/fakes tests/contracts/test_surface_contracts.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/test_bootstrap_surfaces.py tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Email and SMS sinks for notifications, and the other surfaces' first callers (named as
  `PENDING` by `surfaces-callers-registry`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md,
  GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes.
  Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-composition`, `surfaces-adapter-messaging`, `surfaces-contracts-lane` (the in-process lane helper), `fakes-sockets` (`notify/interfaces/`).
- **Shares a file with:** `src/vibey/domain/config.py`, `src/vibey/bootstrap.py`, `src/vibey/infrastructure/notify/service.py`, `tests/fakes/registry.py`.
- **Must keep passing unchanged:** `tests/infrastructure/notify/test_notifications.py`, `tests/infrastructure/notify/test_publishers.py`, `tests/domain/test_config.py`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file. `config.py` and `bootstrap.py` are long: `edit_file` only.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol beside it.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - Never block a worker on a human; a notification is never a failure path.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
