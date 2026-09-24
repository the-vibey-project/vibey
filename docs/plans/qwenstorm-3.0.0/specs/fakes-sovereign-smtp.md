## Title
test(fakes): the email adapter opens SMTP through a declared seam, and an in-memory SMTP server takes the mail

## Why
`ForwardEmailAdapter` (`src/vibey/infrastructure/email/forward_email.py:16-56`) calls
`smtplib.SMTP_SSL` for port 465 and `smtplib.SMTP` otherwise, directly at `:45` and `:50`.
There is no seam, so its test (`tests/infrastructure/test_sovereign_surfaces.py:330-355`)
does `patch("smtplib.SMTP", return_value=MagicMock())` and asserts calls on the mock.

The TLS rule the adapter exists to get right has no honest test:
- 465 is implicit TLS and never STARTTLS;
- submission with a password is EHLO, STARTTLS, EHLO, LOGIN;
- no password means no STARTTLS and no LOGIN.

The mock accepts any order. `SMTP_SSL` is never exercised.

Lane `sovereign-surfaces-ports` may revise the email port or adapter. This lane runs after it,
on the email adapter it leaves, and applies to any other stdlib SMTP adapter it adds.

## Required behaviour
1. **The seam.** In `src/vibey/infrastructure/email/interfaces/forward_email_interface.py`
   (it exists; extend it), add
   `@runtime_checkable class SmtpConnectorInterface(Protocol)` with:
   - `def plain(self, host: str, port: int) -> SmtpSessionInterface`;
   - `def implicit_tls(self, host: str, port: int) -> SmtpSessionInterface`.
   `SmtpSessionInterface` is a context manager with `ehlo()`, `starttls()`,
   `login(user, password)` and `send_message(message)`. The production
   `STDLIB_SMTP: Final` is a stateless class instance whose methods return
   `smtplib.SMTP(host, port)` and `smtplib.SMTP_SSL(host, port)`.
2. **`ForwardEmailAdapter.__init__`** gains `smtp: SmtpConnectorInterface = STDLIB_SMTP`.
   `_send_sync` uses `self._smtp.implicit_tls(...)` and `self._smtp.plain(...)`. The protocol
   steps and their order do not change.
3. **`tests/fakes/smtp.py` — `class InMemorySmtpServer`** implements `SmtpConnectorInterface`:
   - each `plain` or `implicit_tls` opens an `InMemorySmtpSession`, and records
     `("plain" | "tls", host, port)` in `connections`;
   - the session keeps an ordered `commands: list[str]` (`EHLO`, `STARTTLS`, `LOGIN`, `DATA`);
   - it enforces what a real server enforces:
     - `STARTTLS` on an implicit-TLS session raises `smtplib.SMTPNotSupportedError`;
     - `LOGIN` on a plain session before `STARTTLS` raises `smtplib.SMTPNotSupportedError`
       when the server was built with `require_tls_for_auth=True`, the default;
     - a bad credential (`accounts: Mapping[str, str]`) raises `smtplib.SMTPAuthenticationError(535, b"...")`;
   - `send_message` stores the `EmailMessage` in `outbox`.
   - `mailbox(address) -> list[EmailMessage]` returns the messages sent to that address.
4. **Registry.** Register `SmtpConnectorInterface → InMemorySmtpServer()`, and add it to `DRIVER_SEAMS`.
5. **Switch the test.** `test_forward_email_adapter_sends_via_smtp` is split into three tests
   (below), which use the fake. Delete the `patch("smtplib.SMTP"...)` blocks, and lower the
   baseline.

## Where to change
- `src/vibey/infrastructure/email/forward_email.py`, `src/vibey/infrastructure/email/interfaces/forward_email_interface.py`.
- New `tests/fakes/smtp.py`, `tests/fakes/test_fake_smtp.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`,
  `tests/infrastructure/test_sovereign_surfaces.py` (the email test only).

## Acceptance criteria
- [ ] `grep -n 'patch("smtplib' tests/infrastructure/test_sovereign_surfaces.py` prints nothing.
- [ ] Removing the first `starttls()` from the adapter fails a test.
- [ ] 100% `infrastructure/` coverage.

## Tests to write first (TDD)
- `tests/fakes/test_fake_smtp.py`:
  - `test_plain_session_requires_starttls_before_login`
  - `test_implicit_tls_refuses_starttls`
  - `test_bad_credentials_are_refused`
  - `test_outbox_and_mailbox`
- In `tests/infrastructure/test_sovereign_surfaces.py`, replacing the old test:
  - `test_forward_email_submission_is_ehlo_starttls_ehlo_login_data`
  - `test_forward_email_port_465_is_implicit_tls_without_starttls`
  - `test_forward_email_without_a_password_neither_upgrades_nor_logs_in`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/infrastructure/test_sovereign_surfaces.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- HTTP adapters (`fakes-sovereign-http`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** **`sovereign-surfaces-ports`** (supplied later), `fakes-registry`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
