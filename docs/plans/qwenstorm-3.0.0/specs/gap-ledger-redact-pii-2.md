## Title
feat(ledger): redaction covers people's private details, not only credentials

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) requires that "secrets,
credentials and people's private details are redacted where they would appear". The redactor
that every ledger write, every log line and the public export pass through matches credential
key names and vendor token shapes only:
- `src/vibey/infrastructure/ledger/redact.py:17-32` holds the patterns;
- `:35-58` holds `_redact_string`, `_redact_value` and `redact_payload`.

Its callers:
- the ledger appender (`src/vibey/infrastructure/db/ledger_repository.py:108`, and after
  `orm-ledger` the same call in `_append_through_orm`);
- the structlog processor (`src/vibey/infrastructure/logging.py:51`);
- the in-memory ledger of `fakes-ledger` (`specs/fakes-ledger.md:40`);
- the publication policy, through `CREDENTIAL_REDACTOR` (`src/vibey/cli/ledger_publication.py:59-63`).

`gap-ledger-redact-pii-1` added the pure catalogue `vibey.domain.private_details`. This lane
applies it in the one redactor, so every one of those paths redacts private details at once.
The lane also moves the functions into a class with an interface (9.b), because
`gap-ledger-redaction-recorded` needs per-path state next.

## Required behaviour
1. In `src/vibey/infrastructure/ledger/redact.py`:
   - Add `class PayloadRedactor` with
     `__init__(self, *, private_details: PrivateDetailPatternsInterface | None = None) -> None`,
     which stores `private_details if private_details is not None else PRIVATE_DETAILS`. It
     has these methods:
     - `redact(self, payload: Mapping[str, object]) -> dict[str, object]`:
       `{key: self._value(key, value) for key, value in payload.items()}`.
     - `_value(self, key: str | None, value: object) -> object`. This is today's
       `_redact_value` (`:42-51`), with one change: the whole-value rule fires when the key
       matches `_SENSITIVE_KEY_NAMES` **or** `self._private.is_private_key(key)`. A
       private-detail key such as `phone_number: 4155550132` is replaced whatever the
       value's type. Nested mappings recurse through `self.redact`, and lists through `self._value(None, item)`.
     - `_text(self, value: str) -> str`: today's `_redact_string` (`:35-39`), followed by
       `self._private.replace(text, REDACTED)[0]`.
   - Delete the module functions `_redact_string` and `_redact_value`; their bodies now live in the class.
   - Add `DEFAULT_PAYLOAD_REDACTOR: Final[PayloadRedactorInterface] = PayloadRedactor()`.
   - Keep `redact_payload(payload)` as a module function returning
     `DEFAULT_PAYLOAD_REDACTOR.redact(payload)`. Write its reason in its docstring: it is the
     stable call site of `ledger_repository.py`, `logging.py` and the in-memory ledger fake.
   - `contains_secret`, `CredentialRedactor`, `CREDENTIAL_REDACTOR` and `REDACTED` keep their
     names and behaviour. Update `CredentialRedactor`'s docstring to say it now also redacts
     people's private details (7.c).
   - Rewrite the module docstring's first sentence to name both credentials and private
     details. Add `DEFAULT_PAYLOAD_REDACTOR` and `PayloadRedactor` to `__all__`.
2. New interface `src/vibey/infrastructure/ledger/interfaces/redact_interface.py`:
   `class PayloadRedactorInterface(Protocol)`, marked `@runtime_checkable`, with
   `def redact(self, payload: Mapping[str, object]) -> dict[str, object]: ...` and a
   docstring saying it is pure, with no I/O. Export it from
   `src/vibey/infrastructure/ledger/interfaces/__init__.py`: the import block and `__all__`, in sorted order.
3. Imports: `from vibey.domain.private_details import PRIVATE_DETAILS` and
   `from vibey.domain.interfaces import PrivateDetailPatternsInterface`. The dependency points
   inward, infrastructure to domain, which is allowed.
4. Behaviour on today's inputs is unchanged. Every existing test in
   `tests/infrastructure/ledger/test_redact.py` passes untouched.

## Where to change
- `src/vibey/infrastructure/ledger/redact.py`: 90 lines, so `write_file` is allowed only with
  the complete new content. `edit_file` is preferred.
- New: `src/vibey/infrastructure/ledger/interfaces/redact_interface.py`.
- Edit with edit_file: `src/vibey/infrastructure/ledger/interfaces/__init__.py`.
- Append tests to `tests/infrastructure/ledger/test_redact.py`. Do not rewrite it.

## Acceptance criteria
- [ ] `redact_payload({"t": "mail jane.doe@example.org"}) == {"t": "mail [REDACTED]"}`.
- [ ] `redact_payload({"t": "call (415) 555-0132"}) == {"t": "call [REDACTED]"}`.
- [ ] `redact_payload({"t": "at 1600 Pennsylvania Avenue"}) == {"t": "at [REDACTED]"}`.
- [ ] `redact_payload({"author_email": "a@b.co", "phone_number": 4155550132, "home_address": {"line1": "x"}})`
      gives `[REDACTED]` for all three values.
- [ ] `redact_payload({"t": "from noreply@anthropic.com"})` is unchanged.
      `PayloadRedactor(private_details=PrivateDetailPatterns(public_addresses=())).redact(...)`
      redacts that address.
- [ ] `redact_payload({"t": "sk-" + "a" * 20 + " jane@example.org"}) == {"t": "[REDACTED] [REDACTED]"}`.
- [ ] Redaction is idempotent: `redact_payload(redact_payload(p)) == redact_payload(p)` for the mixed payloads above.
- [ ] The log processor redacts private details:
      `_redact_processor(None, "info", {"event": "x", "who": "jane@example.org"})["who"] == "[REDACTED]"`
      (`from vibey.infrastructure.logging import _redact_processor`).
- [ ] `isinstance(DEFAULT_PAYLOAD_REDACTOR, PayloadRedactorInterface)`.
- [ ] Every existing test passes unchanged in `tests/infrastructure/ledger`,
      `tests/infrastructure/test_logging.py`, `tests/cli/test_errors_and_logging.py`,
      `tests/cli/test_ledger_publication_cli.py`, `tests/domain/test_publication_policy.py` and `tests/test_bootstrap.py`.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
Append to `tests/infrastructure/ledger/test_redact.py`:
- `test_an_email_in_free_text_is_redacted`
- `test_a_phone_number_in_free_text_is_redacted`
- `test_a_street_address_in_free_text_is_redacted`
- `test_a_private_detail_key_is_redacted_whatever_its_value`
- `test_a_noreply_address_is_kept`
- `test_the_redactor_takes_its_private_detail_patterns`
- `test_credentials_and_private_details_in_one_string_are_both_redacted`
- `test_redaction_is_idempotent`
- `test_the_log_processor_redacts_private_details`
- `test_the_default_payload_redactor_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/ledger tests/infrastructure/test_logging.py tests/cli/test_errors_and_logging.py tests/cli/test_ledger_publication_cli.py tests/domain/test_publication_policy.py tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Recording which paths were redacted (`gap-ledger-redaction-recorded`).
- The ledger appender, the ORM seam and the in-memory ledger fake: they call `redact_payload`
  and change with it automatically.
- The publication policy's own address token (`[email]`, `publication_policy.py:345`), which
  stays as it is.
- Docs.

Commit as `feat(ledger): redaction covers people's private details, not only credentials`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
