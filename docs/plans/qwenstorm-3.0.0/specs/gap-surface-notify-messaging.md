## Title
feat(notify): operator notifications go to the Matrix room, and to declared email and SMS recipients, through their sovereign ports

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:120-194`) makes Matrix, SMTP and Kannel
the sovereign messaging, email and SMS surfaces. `NotificationService` delivers gate, park,
budget and phase notifications (`src/vibey/application/worker.py:314-347`,
`src/vibey/infrastructure/db/project_repository.py:265-297`) only to desktop alerts and webhooks
(`src/vibey/infrastructure/notify/service.py:14-26`); no production code uses a surface port
(gap K2; ADR-0047 `specs/ADR-surface-lanes.md:38-46`). This lane is K2's first consumer.

It is written against the ports only (`MessagingPort`, `EmailPort`, `SmsPort` in
`src/vibey/application/interfaces/`), so it is transport-agnostic: it works over today's direct
adapters, over the in-memory adapters an unconfigured deployment runs, and over ADR-0047's
queued adapters (a send there returns on the broker's confirm, and a failure becomes a dead
letter instead of an exception). Delivery stays best-effort, as it is today
(`service.py:62-86`): a failed channel is reported as `False`, never raised. Recipients are
people's contact details (SD-01 §1; 7.c at `doctrines.md:82-91`), so no result, log or event
carries one.

## Required behaviour
1. `NotificationService.__init__` (`service.py:15-26`) gains keyword-only parameters, after
   `enable_desktop`: `messaging: MessagingPort | None = None`, `messaging_room: str | None = None`,
   `email: EmailPort | None = None`, `sms: SmsPort | None = None`, `send_messaging: bool = False`,
   `email_to: Sequence[str] = ()`, `sms_to: Sequence[str] = ()`. It stores
   `self._messaging_room` as the stripped room, or `None` when absent or blank, and the two
   recipient sequences as tuples.
2. `for_project_config` (`:28-60`): the disabled branch (`:37`) is unchanged. The enabled branch
   passes `messaging`, `messaging_room`, `email` and `sms` through from `self`, and sets
   `send_messaging=raw.get("messaging", True) is True`,
   `email_to=self._recipients(raw.get("email_to", ()))`,
   `sms_to=self._recipients(raw.get("sms_to", ()))`. The new
   `@staticmethod _recipients(raw: object) -> tuple[str, ...]` returns `()` for anything that is
   not a non-string `Sequence`, and otherwise the stripped non-empty `str` entries, in order —
   the same tolerance the webhook list has (`:39-54`).
3. New public method `has_channels(self) -> bool`: true when desktop is enabled, or a webhook is
   configured, or (`send_messaging` and a messaging port and a room), or (an email port and at
   least one `email_to`), or (an SMS port and at least one `sms_to`). `notify` (`:74`) returns
   its disabled result when `not service.has_channels()` (today's condition is its first two terms).
4. `dispatch` (`:88-111`) also gathers one task per surface delivery, built by a new private
   method `_surface_tasks(event) -> list[tuple[str, asyncio.Task[None]]]`, with
   `subject = f"[vibey] {event.title}"`:
   - messaging, when `send_messaging` and the port and room exist:
     `send_message(room, f"{subject}\n{event.message}")`, labelled `"messaging"`;
   - email, when the port exists: one `send_email(address, subject, event.message)` per
     `email_to` entry, labelled `"email"`;
   - SMS, when the port exists: one `send_sms(number, f"{subject}: {event.message}")` per
     `sms_to` entry, labelled `"sms"`.
   Narrow each optional port into a local variable before use (mypy --strict). The surface
   tasks join the existing `asyncio.gather(..., return_exceptions=True)` after the webhook
   tasks. The result keeps `"desktop"` and `"webhooks"` exactly as today and adds
   `"messaging": bool` only when a messaging task ran, and `"email": list[bool]` /
   `"sms": list[bool]` (one entry per recipient, in order) only when those tasks ran. A task
   that raised is `False`; one that returned is `True`. Existing results are therefore
   byte-for-byte unchanged when no surface channel is active.
5. New `src/vibey/infrastructure/notify/interfaces/service_interface.py`:
   `@runtime_checkable class NotificationServiceInterface(NotificationSink, Protocol)` declaring
   `for_project_config(self, config: Mapping[str, object] | None) -> "NotificationServiceInterface"`,
   `has_channels(self) -> bool` and `async dispatch(self, event: NotificationEvent) -> dict[str, Any]`,
   exported from `src/vibey/infrastructure/notify/interfaces/__init__.py` (the package
   `fakes-sockets` creates and registers in `.importlinter`).
6. Nothing reads configuration here: the ports and room arrive by constructor
   (`gap-surface-notify-wiring`), and the per-project keys are the ones `gap-surface-notify-config`
   validates.

## Where to change
- `src/vibey/infrastructure/notify/service.py` (edit_file only).
- New `src/vibey/infrastructure/notify/interfaces/service_interface.py`; one export line in
  `src/vibey/infrastructure/notify/interfaces/__init__.py`.
- New `tests/infrastructure/notify/test_surface_notifications.py` (provenance line first,
  copied from `tests/infrastructure/notify/test_notifications.py:1`).
- Run `uv run ruff format` on the touched files.

## Acceptance criteria
- [ ] Every test in `tests/infrastructure/notify/test_notifications.py`,
      `tests/application/` and `tests/infrastructure/db/` that touches notifications passes unchanged.
- [ ] An enabled project with the room configured sends exactly one Matrix message and reports
      `"messaging": True`; the in-memory adapters are enough to run it.
- [ ] A failing sink reports `False` and the other channels still deliver.
- [ ] No address, number or room id appears in any result.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/notify/test_surface_notifications.py`. Sinks are the production
in-memory adapters (`InMemoryMessaging().sent`, `InMemoryEmail().sent`, `InMemorySms().sent_sms`);
the failing sink is `MatrixMessagingAdapter(url="https://matrix.test", token="t", opener=server)`
over `tests.fakes.http.InMemoryHttpServer` with `server.route_prefix("PUT", "https://matrix.test/", status=502)`.
Every call goes through `notify(..., config={"notifications": {"enabled": True, "desktop": False, ...}})`,
and every service is built with
`desktop_notifier=DesktopNotifier(executor=lambda command: True, platform_override="linux")`, as
`tests/infrastructure/notify/test_notifications.py:222-224` does, so no desktop alert can fire.
No `MagicMock`, no patching.
- `test_an_enabled_project_notifies_the_matrix_room`: result
  `{"desktop": False, "webhooks": [], "messaging": True}`; one message to `"!ops:matrix.test"`
  whose text is `"[vibey] Human Gate Raised\nanswer the gate"`.
- `test_each_email_and_sms_recipient_gets_the_notification`: two `email_to`, one `sms_to`;
  `"email": [True, True]`, `"sms": [True]`; subjects `"[vibey] Run Completed"`, SMS text
  `"[vibey] Run Completed: done"`.
- `test_messaging_can_be_switched_off_per_project`: `"messaging": False` in the project config
  and no other channel gives `{"enabled": False, "desktop": False, "webhooks": []}`.
- `test_no_room_or_no_port_means_no_matrix_delivery` (parametrized: room `None`, room `"  "`, port `None`).
- `test_recipients_without_their_port_are_not_delivered`.
- `test_a_failing_sovereign_sink_is_reported_not_raised`: Matrix answers 502 and one email
  recipient is set; `"messaging": False`, `"email": [True]`.
- `test_malformed_recipient_lists_are_ignored` (a string, `[None, " ", 7]`).
- `test_a_disabled_project_uses_no_channel` (`enabled` false; nothing sent).
- `test_results_never_carry_a_recipient` (no address, number or room id in `repr(result)`).
- `test_the_service_satisfies_its_interface`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/notify tests/application tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- `build_app` wiring (`gap-surface-notify-wiring`) and config parsing (`gap-surface-notify-config`).
- Passing ADR-0047's `idempotency_key` (lanes S04–S06 add it to the ports; a follow-up passes a
  key derived from the event once they land). Ledgering deliveries (7.c) and measuring them
  (8.g, `gap-measure-port`) are named by `gap-spike-surface-consumers`.
- The failure classifiers in `worker.py:98-128` and `project_repository.py:157-171`: they keep
  reading `desktop` and `webhooks` only (teaching them the new keys is named by
  `gap-spike-surface-consumers`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(notify): deliver operator notifications through the sovereign surfaces`. Do not push.

## Lane card
- **Depends on:** `gap-surface-notify-config`, `fakes-sockets` (creates
  `notify/interfaces/` and its `.importlinter` line; it follows `fakes-http-transport`, whose
  `InMemoryHttpServer` the failing-sink test uses).
- **Must keep passing unchanged:** `tests/infrastructure/notify/test_notifications.py`,
  `tests/infrastructure/notify/test_publishers.py`, and the protected tests
  (`tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
