## Title
feat(config): `[notifications]` declares the sovereign channels — the Matrix room by default, and explicit email and SMS recipients

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:120-194`) makes Matrix, SMTP and Kannel
the sovereign messaging, email and SMS surfaces, but operator notifications reach only desktop
alerts and webhooks (`src/vibey/infrastructure/notify/service.py:14-26`); no production code uses
any surface (gap K2; ADR-0047 `specs/ADR-surface-lanes.md:38-46`, "Who calls them: nobody yet").
`[messaging] room_id` (`VIBEY_MESSAGING_ROOM_ID`, `src/vibey/domain/config.py:263-269`,
`src/vibey/infrastructure/config_loader.py:42`) is declared and read by nothing.

This lane declares, per project, which sovereign channels a notification uses (12.c,
`doctrines.md:455`). `gap-surface-notify-messaging` sends through them and
`gap-surface-notify-wiring` hands them the ports. The rule stays the one
`NotificationsConfig` states (`config.py:152-162`): notifications are opt-in; once enabled,
desktop defaults on and destinations are explicit. The Matrix room is an explicit,
deployment-wide destination, so once enabled it defaults on too; email and SMS recipients are
listed per project. Recipients are people's contact details (SD-01 §1, 7.c at `doctrines.md:82-91`):
they are validated here and never echoed anywhere else.

## Required behaviour
1. `NotificationsConfig` (`src/vibey/domain/config.py:151-162`) gains three fields after
   `webhooks`: `messaging: bool = True`, `email_to: tuple[str, ...] = ()`,
   `sms_to: tuple[str, ...] = ()`. Its docstring becomes: "Operator notifications for a project.
   Notifications stay opt-in because every channel is a side effect. Once enabled, desktop
   delivery and the deployment's Matrix room (`[messaging] room_id`) default on; webhook, email
   and SMS destinations are explicit."
2. `_parse_notifications` (`:462-481`) becomes the classmethod
   `NotificationsConfig.from_table(cls, table: dict[str, Any], path: str) -> "NotificationsConfig"`
   (the pattern of `ClaudeloopLocalConfig.from_table`, `:88-107`). Its webhook loop and every
   existing message are unchanged, with `"notifications"` replaced by `path`. It adds:
   - `messaging=_optional(table, "messaging", f"{path}.messaging", bool, True)`;
   - `email_to` and `sms_to` through one private static method
     `_recipients(table, key, path, pattern, example) -> tuple[str, ...]`: the value is read with
     `_optional(table, key, f"{path}.{key}", list, [])`; each entry that is not a `str`, or whose
     `.strip()` does not `fullmatch` the pattern, raises
     `ConfigError(f"{path}.{key}[{index}]", f"must be {example}")`; the stripped values are kept
     in order.
   - Patterns, as module constants directly above the `@dataclass` line of
     `NotificationWebhookConfig` (`:143`),
     with `import re` added to the imports:
     `_EMAIL_ADDRESS = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")` with example
     `"an email address such as ops@example.org"`, and
     `_E164_NUMBER = re.compile(r"\+[1-9][0-9]{6,14}")` with example
     `"an E.164 number such as +15551234567"`.
3. `parse_config` passes
   `notifications=NotificationsConfig.from_table(_optional(data, "notifications", "notifications", dict, {}), "notifications")`
   (`:704`), and `_parse_notifications` is deleted (it has no other caller).
4. `NotificationsConfigInterface` (`src/vibey/domain/interfaces/config_interface.py:19-28`)
   gains the read-only properties `messaging -> bool`, `email_to -> tuple[str, ...]` and
   `sms_to -> tuple[str, ...]`.
5. `vibey new` already validates the runtime tables before storing them
   (`load_runtime_config_from_path`, `config_loader.py:103-123`), so a bad recipient is refused
   at project creation with the path named. Nothing in this lane sends anything.

## Where to change
- `src/vibey/domain/config.py` (edit_file only; 724 lines).
- `src/vibey/domain/interfaces/config_interface.py`.
- New `tests/domain/test_notification_channels_config.py` (provenance line first, copied from
  `tests/domain/test_config.py:1`).
- Run `uv run ruff format` on the three files before the checks.

## Acceptance criteria
- [ ] Every existing test in `tests/domain/test_config.py` and
      `tests/infrastructure/test_config_loader.py` passes unchanged (same messages, same paths).
- [ ] `[notifications] enabled = true` alone gives `messaging is True`, `email_to == ()`, `sms_to == ()`.
- [ ] `email_to = [" ops@example.org "]` gives `("ops@example.org",)`;
      `sms_to = ["+15551234567"]` gives `("+15551234567",)`.
- [ ] `email_to = ["nobody"]` raises `ConfigError` with path `notifications.email_to[0]`;
      `sms_to = ["5551234567"]` and `sms_to = [7]` raise with path `notifications.sms_to[0]`;
      `email_to = "ops@example.org"` raises naming `notifications.email_to`.
- [ ] `grep -n "_parse_notifications" src/vibey` prints nothing.
- [ ] `tests/domain/test_domain_purity.py` passes; 100% branch coverage of `domain/` and `infrastructure/`.

## Tests to write first (TDD)
`tests/domain/test_notification_channels_config.py`:
- `test_enabled_notifications_default_to_the_matrix_room_only`
- `test_email_and_sms_recipients_are_parsed_and_stripped`
- `test_messaging_can_be_switched_off` (`messaging = false`)
- `test_messaging_must_be_a_bool` (`messaging = "yes"` names `notifications.messaging`)
- `test_recipient_lists_must_be_lists` (parametrized over `email_to` and `sms_to` given a string)
- `test_a_malformed_recipient_is_refused_with_its_index` (parametrized: `email_to = ["nobody"]`,
  `email_to = ["a b@example.org"]`, `sms_to = ["5551234567"]`, `sms_to = ["+0123456"]`,
  `sms_to = [7]`; each asserts the indexed path and the example in the message)
- `test_project_creation_refuses_a_malformed_recipient` (`load_runtime_config_from_path` on a
  `tmp_path` file with `[notifications]\nsms_to = ["call me"]` raises naming `notifications.sms_to[0]`)
- `test_notifications_config_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_notification_channels_config.py tests/domain/test_config.py tests/domain/test_domain_purity.py tests/infrastructure/test_config_loader.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Sending anything (`gap-surface-notify-messaging`) and wiring ports (`gap-surface-notify-wiring`).
- The other surface consumers (`gap-spike-surface-consumers`).
- `docs/reference/configuration.md` (the docs wave), CHANGELOG.md, ADRs, CLAUDE.md, AGENTS.md,
  GEMINI.md, skill trees.

Commit as `feat(config): declare the sovereign notification channels`. Do not push.

## Lane card
- **Depends on:** none.
- **Shares a file with:** `gap-surface-timeouts-1` (`domain/config.py`, a different region:
  that lane adds constants after `:35`, a class before `VibeyConfig` and one `parse_config` argument).
- **Must keep passing unchanged:** `tests/domain/test_config.py`,
  `tests/infrastructure/test_config_loader.py`, `tests/infrastructure/notify/test_notifications.py`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
