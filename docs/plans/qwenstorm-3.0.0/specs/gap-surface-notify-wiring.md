## Title
feat(bootstrap): build_app gives the notification service the messaging, email and SMS ports and the declared Matrix room

## Why
`gap-surface-notify-messaging` teaches `NotificationService` to deliver through `MessagingPort`,
`EmailPort` and `SmsPort`, but `build_app` still constructs it bare,
`notifications = NotificationService()` (`src/vibey/bootstrap.py:713` at integration `d3b4a388`),
before the surfaces are even selected (`:740-914`). So vibey's operations still use no surface
(gap K2; ADR-0047 `specs/ADR-surface-lanes.md:38-46`). The service must be built after the ports
it needs, and before anything that holds it: `PostgresProjectRepository(pool, notifications=...)`
(`:714-717`) today, and `ResourcesFactoryInterface.open(url, *, notifications=...)` once
`fakes-bootstrap-seam` lands. `[messaging] room_id` (`VIBEY_MESSAGING_ROOM_ID`,
`src/vibey/infrastructure/config_loader.py:42`) becomes the room it posts to (12.c,
`src/vibey_tools/gh/docs/doctrines.md:455`). Unconfigured surfaces stay in memory, so a bare
install changes nothing it can observe outside the process.

## Required behaviour
1. The configuration and surface-selection block — from the line `resolved_config = config`
   through the line `siem_port = InMemorySiem()` (`:740-914`) — moves, unchanged in content,
   to directly before the construction of `notifications`, at that line's indentation. The
   notification service is then built from the selected ports:
   ```python
   notifications = NotificationService(
       messaging=messaging_port,
       messaging_room=resolved_config.messaging.room_id if resolved_config else None,
       email=email_port,
       sms=sms_port,
   )
   ```
   Do both with this checked script through the `shell` tool (it anchors on text, because
   `surfaces-env`, `fakes-bootstrap-seam`, the `orm-*` lanes and `gap-surface-timeouts-6` also
   edit `build_app`):
   ```python
   import textwrap
   from pathlib import Path
   p = Path("src/vibey/bootstrap.py")
   s = p.read_text()
   start_marker = "resolved_config = config\n"
   end_marker = "siem_port = InMemorySiem()\n"
   anchor_marker = "notifications = NotificationService()\n"
   for marker in (start_marker, end_marker, anchor_marker):
       assert s.count(marker) == 1, (marker, s.count(marker))
   start = s.rindex("\n", 0, s.index(start_marker)) + 1
   end = s.index(end_marker) + len(end_marker)
   assert s.index(anchor_marker) < start, "the service must be built before the surfaces today"
   block = textwrap.dedent(s[start:end])
   s = s[:start] + s[end:]
   anchor = s.rindex("\n", 0, s.index(anchor_marker)) + 1
   pad = s[anchor : s.index(anchor_marker)]
   assert pad.strip() == "", repr(pad)
   wired = (
       f"{pad}notifications = NotificationService(\n"
       f"{pad}    messaging=messaging_port,\n"
       f"{pad}    messaging_room=resolved_config.messaging.room_id if resolved_config else None,\n"
       f"{pad}    email=email_port,\n"
       f"{pad}    sms=sms_port,\n"
       f"{pad})\n"
   )
   rest = s[anchor + len(pad) + len(anchor_marker) :]
   p.write_text(s[:anchor] + textwrap.indent(block, pad) + "\n" + wired + rest)
   ```
   Then run `uv run ruff format src/vibey/bootstrap.py`.
2. **If `src/vibey/infrastructure/surface_lanes/direct_factory.py` exists** (ADR-0047 lane S14
   has moved the selection), do not edit anything: stop with the verdict
   `BLOCKED: gap-surface-notify-wiring predates S14; S14 must build NotificationService from its selected ports`.
3. Every surface still resolves exactly as before, and every other `AppResources` field is
   unchanged. The same `notifications` object reaches the project repository (or the resources
   factory) and `AppResources.notifications`, so the worker's gate notifications
   (`src/vibey/application/worker.py:314-347`) and the repository's phase notifications
   (`src/vibey/infrastructure/db/project_repository.py:265-297`) both use the surfaces.
4. Behaviour is transport-agnostic: the service receives whatever `messaging_port`,
   `email_port` and `sms_port` hold (direct, in-memory, or later ADR-0047's queued adapters).

## Where to change
- `src/vibey/bootstrap.py` (the script above; no other edit).
- New `tests/test_bootstrap_notification_surfaces.py` (provenance line first, copied from
  `tests/test_bootstrap.py:1`).

## Acceptance criteria
- [ ] `grep -n "NotificationService()" src/vibey/bootstrap.py` prints nothing.
- [ ] With `[messaging] room_id` set and no messaging URL, an enabled project's notification is
      recorded by `resources.messaging` (the in-memory adapter) in that room.
- [ ] Without a room, the same project gets `{"enabled": False, "desktop": False, "webhooks": []}`
      when desktop is off and it lists no recipient.
- [ ] `test_build_app_defaults_to_in_memory_surfaces`,
      `test_build_app_wires_concrete_adapters_from_config` and `tests/test_bootstrap.py` pass unchanged.

## Tests to write first (TDD)
`tests/test_bootstrap_notification_surfaces.py`. Open the app with `tests/fakes/app.py`'s
`InMemoryApp` (lane `fakes-bootstrap-seam`; read its constructor, which takes the `config`), as
`async with app.open_app() as resources:`. No PostgreSQL, no `patch`, no `MagicMock`. Every
`notify` call passes `config={"notifications": {"enabled": True, "desktop": False, ...}}`.
- `test_build_app_hands_the_sovereign_ports_to_notifications`: a `VibeyConfig` with
  `messaging=MessagingConfig(room_id="!ops:matrix.test")`; the project config adds
  `"email_to": ["ops@example.org"]`; `await resources.notifications.notify(project_id=uuid4(), kind="run_completed", title="Run Completed", message="done", config=...)`
  returns `{"desktop": False, "webhooks": [], "messaging": True, "email": [True]}`;
  `resources.messaging.sent[0]["channel_id"] == "!ops:matrix.test"` and
  `resources.email.sent[0]["to"] == "ops@example.org"`.
- `test_build_app_without_a_room_sends_no_matrix_message`: default `VibeyConfig`; the result is
  the disabled result and `resources.messaging.sent == []`.
- `test_the_room_is_declared_by_the_environment`: `monkeypatch.chdir(tmp_path)`,
  `monkeypatch.setenv("VIBEY_MESSAGING_ROOM_ID", "!env:matrix.test")`, the app with no config;
  the message lands in `"!env:matrix.test"`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap_notification_surfaces.py tests/test_bootstrap.py tests/infrastructure/test_sovereign_surfaces.py tests/infrastructure/notify tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- `NotificationService` itself (`gap-surface-notify-messaging`) and the config keys
  (`gap-surface-notify-config`).
- ADR-0047's transport selection (S26) and lane host: S14/S26 inherit this wiring (see
  behaviour 2).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(bootstrap): notifications use the selected messaging, email and SMS ports`. Do not push.

## Lane card
- **Depends on:** `gap-surface-notify-messaging`, `surfaces-env`, `fakes-bootstrap-seam`.
- **Shares a file with:** `src/vibey/bootstrap.py` (`surfaces-env`, `fakes-bootstrap-seam`,
  the `orm-*` bootstrap lanes, R17, `gap-surface-timeouts-6`, ADR-0047 S14/S26). If an `assert`
  in the script fails, read the file, report which anchor moved, and stop.
- **Must keep passing unchanged:** the two `build_app` wiring tests, `tests/test_bootstrap.py`,
  and the protected tests (`tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
