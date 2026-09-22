## Title
fix(surfaces): the SMTP email adapter opens every connection with a timeout

## Why
Doctrine 10 (`src/vibey_tools/gh/docs/doctrines.md:366-369`): never assumed, always self-healed
around. `ForwardEmailAdapter` opens `smtplib.SMTP_SSL(host, port)` and `smtplib.SMTP(host, port)`
with no timeout (`src/vibey/infrastructure/email/forward_email.py:45`, `:50` at integration
`d3b4a388`), so a relay that accepts the TCP connection and never greets blocks the thread
forever (gap K3; ADR-0047 `specs/ADR-surface-lanes.md:562`).

Lane `fakes-sovereign-smtp` moves those two calls behind `SmtpConnectorInterface`
(`plain(host, port)` and `implicit_tls(host, port)`, in
`src/vibey/infrastructure/email/interfaces/forward_email_interface.py`), served in production by
`STDLIB_SMTP` and in tests by `InMemorySmtpServer` (`tests/fakes/smtp.py`). This lane gives that
seam a `timeout`, and the adapter passes `DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`
(`gap-surface-timeouts-1`, 12.c) unless told otherwise.

## Required behaviour
1. **The seam.** In `SmtpConnectorInterface`, both methods gain a third parameter with no
   default: `def plain(self, host: str, port: int, timeout: float) -> SmtpSessionInterface` and
   `def implicit_tls(self, host: str, port: int, timeout: float) -> SmtpSessionInterface`.
2. **Production.** In `forward_email.py`, the class whose instance is `STDLIB_SMTP` returns
   `smtplib.SMTP(host, port, timeout=timeout)` and `smtplib.SMTP_SSL(host, port, timeout=timeout)`.
   (typeshed types smtplib's `timeout` as `float`, so no `None` is passed.)
3. **The adapter.** `ForwardEmailAdapter.__init__` gains the keyword-only parameter
   `timeout: float = DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS` (imported from
   `vibey.domain.config`), directly after `smtp`, stored as `self._timeout`. `_send_sync` calls
   `self._smtp.implicit_tls(self._smtp_host, self._smtp_port, timeout=self._timeout)` and
   `self._smtp.plain(self._smtp_host, self._smtp_port, timeout=self._timeout)`. The SMTP steps and
   their order (EHLO, STARTTLS, EHLO, LOGIN; none of them on 465) do not change.
4. **The fake.** In `tests/fakes/smtp.py`, `InMemorySmtpServer.plain` and `.implicit_tls` gain
   `timeout: float | None = None` (a default, so every existing caller in
   `tests/fakes/test_fake_smtp.py` keeps working) and append it to a new public list
   `self.timeouts: list[float | None]`, initialised empty in `__init__`. `connections` keeps its
   tuple shape. The registry's parity test (`tests/fakes/test_port_parity.py`) still passes: the
   parameter names and kinds match the interface.

If `sovereign-surfaces-ports` or `fakes-sovereign-smtp` named anything differently, apply the
same change to what exists and name it in the commit body.

## Where to change
- `src/vibey/infrastructure/email/interfaces/forward_email_interface.py`
- `src/vibey/infrastructure/email/forward_email.py`
- `tests/fakes/smtp.py`
- New `tests/infrastructure/test_surface_timeouts_email.py` (provenance line first, copied from
  `tests/infrastructure/test_sovereign_surfaces.py:1`).
- edit_file only; then `uv run ruff format` on the four files.

## Acceptance criteria
- [ ] `grep -n "smtplib.SMTP(host, port)\|smtplib.SMTP_SSL(host, port)" src/vibey/infrastructure/email/forward_email.py` prints nothing.
- [ ] A submission (port 587) and an implicit-TLS send (port 465) each open one connection
      bounded by the adapter's timeout; the default is `DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`.
- [ ] `fakes-sovereign-smtp`'s three adapter tests and `tests/fakes/test_fake_smtp.py` pass unchanged.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`; bandit clean.

## Tests to write first (TDD)
`tests/infrastructure/test_surface_timeouts_email.py`, using
`from tests.fakes.smtp import InMemorySmtpServer` and `STDLIB_SMTP` from
`vibey.infrastructure.email.forward_email`. No `MagicMock`, no `patch`.
- `test_forward_email_submission_is_bounded_by_its_timeout`: a server that accepts `u`/`pw`;
  `ForwardEmailAdapter(smtp_host="smtp.test", smtp_port=587, username="u", password="pw", smtp=server, timeout=7)`;
  one `send_email("ops@example.org", "s", "b")`; `server.timeouts == [7]` and the message is in
  `server.mailbox("ops@example.org")`.
- `test_forward_email_implicit_tls_is_bounded_by_its_timeout`: port 465; `server.timeouts == [7]`
  and `server.connections[0][0] == "tls"`.
- `test_forward_email_defaults_to_the_surface_timeout`: no `timeout`;
  `server.timeouts == [DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS]`.
- `test_the_stdlib_connector_requires_a_timeout`: for `STDLIB_SMTP.plain` and
  `STDLIB_SMTP.implicit_tls`, `inspect.signature(...).parameters["timeout"].default is inspect.Parameter.empty`.
  No connection is opened.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_surface_timeouts_email.py tests/infrastructure/test_sovereign_surfaces.py tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The HTTP adapters (`gap-surface-timeouts-2` to `-4`) and the `build_app` wiring (`-6`).
- ADR-0047's `Message-ID` and `idempotency_key` on `send_email` (lanes S04–S06).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `fix(surfaces): bound every SMTP connection with the surface timeout`. Do not push.

## Lane card
- **Depends on:** `gap-surface-timeouts-1`, `fakes-sovereign-smtp`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/fakes/test_fake_smtp.py`, the email tests in
  `tests/infrastructure/test_sovereign_surfaces.py`, and the protected tests
  (`tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
