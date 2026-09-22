## Title
feat(email): send_email takes an idempotency key that fixes the Message-ID, and SMTP connections are opened with a timeout

## Why
- **No timeout.** `ForwardEmailAdapter` opens `smtplib.SMTP_SSL(host, port)` and
  `smtplib.SMTP(host, port)` with no timeout (`src/vibey/infrastructure/email/forward_email.py:45`,
  `:50`); lane `fakes-sovereign-smtp` moved those calls behind `SmtpConnectorInterface`
  (`plain(host, port)` / `implicit_tls(host, port)`), still with no timeout
  (`issue-audit/gaps.md` K3).
- **The key.** Draft ADR-0047 §2–§3 (`specs/ADR-surface-lanes.md`) adds an optional
  `idempotency_key` to `send_email` and classes it **guarded**: SMTP has no idempotency key, so
  the lane guards it (§8). The adapter still derives a stable `Message-ID` from the key — "a
  courtesy to receivers, not a guarantee" (§3 table). The in-memory outbox must not deduplicate:
  the backend cannot (draft amendment A2).

ADR-0047 lane S05 (email), and gaps K3 for this adapter.

## Required behaviour
1. **The port.** `EmailPort.send_email` (`src/vibey/application/interfaces/email.py:11-13`)
   becomes `async def send_email(self, to_addr: str, subject: str, body: str, *, idempotency_key: str | None = None) -> None`.
   Docstring adds: "The key names one logical message and fixes its Message-ID; SMTP cannot
   deduplicate, so the surface lane guards it (ADR-0047 §8)."
2. **`InMemoryEmail`** (`src/vibey/infrastructure/email/in_memory.py`): appends on every call,
   as today, and records the key in a new `self.sent_keys: list[str | None]` (same index as
   `self.sent`).
3. **The SMTP seam** (`src/vibey/infrastructure/email/interfaces/forward_email_interface.py`,
   from `fakes-sovereign-smtp`): `SmtpConnectorInterface.plain(self, host: str, port: int, *, timeout: float)`
   and `implicit_tls(self, host: str, port: int, *, timeout: float)`. `STDLIB_SMTP` passes
   `timeout=timeout` to `smtplib.SMTP` and `smtplib.SMTP_SSL`. `tests/fakes/smtp.py`
   `InMemorySmtpServer` accepts the keyword and records it in a new `timeouts: list[float]`
   (its `connections` tuples keep their shape).
4. **`ForwardEmailAdapter`**:
   - `__init__` gains `timeout: float = 30.0` (`<= 0` raises `ValueError("timeout must be positive")`)
     and passes it to both connector calls.
   - With a key: `message["Message-ID"] = f"<vibey.{hashlib.sha256(idempotency_key.encode('utf-8')).hexdigest()[:32]}@{domain}>"`,
     where `domain` is the part of the From address after its last `@`, or `"localhost"`.
     Without a key, no `Message-ID` is set (today's behaviour).
   - The EHLO / STARTTLS / LOGIN order is unchanged.

## Where to change
- `src/vibey/application/interfaces/email.py`, `src/vibey/infrastructure/email/in_memory.py`,
  `src/vibey/infrastructure/email/forward_email.py`,
  `src/vibey/infrastructure/email/interfaces/forward_email_interface.py`, `tests/fakes/smtp.py`.
- New `tests/infrastructure/surfaces/test_forward_email_adapter.py` (create
  `tests/infrastructure/surfaces/__init__.py` if missing).
- Append to `tests/contracts/test_surface_contracts.py`, using its email fixture.

## Acceptance criteria
- [ ] Both connector calls receive the default and a configured timeout (`InMemorySmtpServer.timeouts`).
- [ ] Two sends with key `k` from `vibey@example.org` carry the same `Message-ID`, `<vibey.<32 hex>@example.org>`; two sends without a key carry none.
- [ ] `InMemoryEmail` records both keyed sends and both keys.
- [ ] The three existing SMTP-order tests of `fakes-sovereign-smtp` pass unchanged.
- [ ] 100% `infrastructure/` branch coverage; the fakes parity test passes.

## Tests to write first (TDD)
`tests/infrastructure/surfaces/test_forward_email_adapter.py` (no service; `InMemorySmtpServer`):
- `test_smtp_connections_carry_the_timeout`
- `test_a_key_fixes_the_message_id_on_the_from_domain`
- `test_without_a_key_no_message_id_is_set`
- `test_forward_email_refuses_a_non_positive_timeout`
- `test_in_memory_email_records_every_send_and_its_key`
Append to `tests/contracts/test_surface_contracts.py`:
- `test_email_send_accepts_an_idempotency_key`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surfaces tests/contracts/test_surface_contracts.py tests/infrastructure/test_sovereign_surfaces.py tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The guard (`surfaces-guarded-execution`); the configured timeout (`surfaces-direct-factory`).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `fakes-sovereign-smtp` (the connector seam and `InMemorySmtpServer`), `fakes-contracts-surfaces`.
- **Shares a file with:** `tests/contracts/test_surface_contracts.py`, `tests/fakes/smtp.py`.
- **Must keep passing unchanged:** `tests/fakes/test_fake_smtp.py`, `tests/infrastructure/test_sovereign_surfaces.py`, the contract suite, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file. Change existing files with `edit_file` or a checked replacement; add tests by appending or in a new file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Substitute only at a declared seam (`smtp=`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
