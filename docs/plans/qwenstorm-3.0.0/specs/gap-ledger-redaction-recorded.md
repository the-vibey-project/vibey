## Title
feat(ledger): each redaction is recorded with its path and class, never its value

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:88-90`) says the redaction "is itself
recorded — never a silent omission". Today `redact_payload` replaces a value with `[REDACTED]`
and records nothing (`src/vibey/infrastructure/ledger/redact.py`, which after
`gap-ledger-redact-pii-2` is `PayloadRedactor.redact`). A reader of the ledger cannot tell a
payload that said "[REDACTED]" from one that was redacted, or which field was redacted, or why.

Recording it in the same payload keeps the write atomic, which is non-negotiable 7: every job
is idempotent under replay. The redaction then needs no second event and no second transaction.
The appender digests the redacted payload (`src/vibey/infrastructure/db/ledger_repository.py:103-109`),
so the chain digest covers the record too. The in-memory ledger fake does the same
(`specs/fakes-ledger.md:40-41`). No strict payload decoder exists in `src/vibey` that would
reject an extra key: grep for "unknown key", "extra key", `set(payload)` and `payload.keys()`
returns nothing at `d3b4a388`.

## Required behaviour
1. `src/vibey/infrastructure/ledger/redact.py` gains two constants:
   - `REDACTIONS_FIELD: Final = "_redactions"`;
   - `class RedactionClass(StrEnum)` with members `CREDENTIAL_KEY = "credential-key"`,
     `CREDENTIAL_VALUE = "credential-value"`, `PRIVATE_DETAIL_KEY = "private-detail-key"`,
     `EMAIL = "email"`, `PHONE = "phone"`, `STREET_ADDRESS = "street-address"`. The last three
     values equal `PrivateDetailClass`'s, and a test pins that.
2. `PayloadRedactor.redact(payload)` walks the payload with a JSON Pointer path (RFC 6901).
   The root is `""`, a key `k` appends `"/" + k.replace("~", "~0").replace("/", "~1")`, and a
   list index `i` appends `"/" + str(i)`. For every value it redacts, it notes `(path, class)`:
   - a key matching `_SENSITIVE_KEY_NAMES` gives `CREDENTIAL_KEY` at the key's path. This check
     is first: a key matching both gives only this class;
   - a key matching `is_private_key` gives `PRIVATE_DETAIL_KEY`;
   - in a string, a vendor credential pattern gives `CREDENTIAL_VALUE`, and each class that
     `PrivateDetailPatterns.replace` returns is recorded in its order. All of these carry the
     string's path.
3. The output is exactly today's redacted mapping when nothing was noted. Otherwise it is that
   mapping plus `REDACTIONS_FIELD: [{"path": p, "class": c}, ...]`, with one entry per distinct
   `(path, class)`, in walk order (the payload's insertion order, depth first).
4. `REDACTIONS_FIELD` at the top level is never walked or redacted. If the input already has
   it, as a list of mappings, the output keeps those entries first. New entries follow and are
   appended only when not already present. This makes redaction idempotent:
   `redact(redact(p)) == redact(p)`.
5. The record never holds a redacted value. No original secret or private detail appears
   anywhere in `json.dumps(redact(p))`.
6. `contains_secret(p)` is still `redact_payload(p) != dict(p)`, and is True whenever anything
   was redacted.
7. In the existing test `test_the_credential_redactor_is_redact_payload_behind_the_policys_seam`
   (`tests/infrastructure/ledger/test_redact.py:81-85`), change the last assertion (`:85`) with
   edit_file. Its right-hand side becomes
   `{"note": f"use {REDACTED}", "token": REDACTED, "_redactions": [{"path": "/note", "class": "credential-value"}, {"path": "/token", "class": "credential-key"}]}`.
   That order is the walk order of the input `{"note": ..., "token": ...}`. Change no other
   existing assertion. If another existing test fails, stop and report it; do not edit it.
8. The public export is unaffected in kind. `_redactions` is not in any publication allowlist,
   so the policy trims it and counts it as a withheld field (`publication_policy.py:316-321`),
   which is not silent. When the export's own last redaction pass redacts something, the
   published record carries its own `_redactions`.

## Where to change
- `src/vibey/infrastructure/ledger/redact.py`: edit_file only.
- The interface `src/vibey/infrastructure/ledger/interfaces/redact_interface.py`: update the
  `redact` docstring to state the `_redactions` contract. The signature is unchanged.
- `tests/infrastructure/ledger/test_redact.py`: append the new tests, plus the one assertion
  edit in point 7.

## Acceptance criteria
- [ ] `redact_payload({"summary": "clean"}) == {"summary": "clean"}`, with no `_redactions` key.
- [ ] For `{"note": "use sk-" + "a"*20, "outer": {"password": "p", "who": ["x", "mail jane@example.org"]}}`
      the `_redactions` value is
      `[{"path": "/note", "class": "credential-value"}, {"path": "/outer/password", "class": "credential-key"}, {"path": "/outer/who/1", "class": "email"}]`.
- [ ] `{"a/b": {"c~d": "jane@example.org"}}` records the path `/a~1b/c~0d`.
- [ ] `{"t": "call +14155550132 or jane@example.org"}` records `phone` then `email` for `/t`.
- [ ] Idempotent: `redact_payload(redact_payload(p)) == redact_payload(p)` for every payload above.
- [ ] `json.dumps(redact_payload(p))` contains neither `jane@example.org` nor the `sk-` value.
- [ ] `digest_event(redact_payload(p))` differs from the digest of the same mapping without
      `_redactions` (`from vibey.domain.ledger import digest_event`). This proves the record
      is inside what the appender digests.
- [ ] Each of `RedactionClass.EMAIL`, `PHONE` and `STREET_ADDRESS` has the value of the
      same-named `PrivateDetailClass` member.
- [ ] All the tests named in `gap-ledger-redact-pii-2`'s checks pass, with the single assertion edit in point 7.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
Append to `tests/infrastructure/ledger/test_redact.py`:
- `test_a_clean_payload_gets_no_redaction_record`
- `test_each_redaction_is_recorded_with_its_json_pointer_and_class`
- `test_json_pointer_escapes_slash_and_tilde`
- `test_two_classes_in_one_string_record_two_entries_in_order`
- `test_a_credential_key_wins_over_a_private_detail_key`
- `test_redaction_with_its_record_is_idempotent`
- `test_the_record_never_holds_a_redacted_value`
- `test_the_record_is_inside_the_digested_payload`
- `test_redaction_classes_share_the_private_detail_values`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/ledger tests/infrastructure/test_logging.py tests/cli/test_errors_and_logging.py tests/cli/test_ledger_publication_cli.py tests/domain/test_publication_policy.py tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- A separate `RedactionRecorded` event kind. The record rides in the payload so the write stays one append.
- Publishing `_redactions` in the public export (a publication-rules decision for the operator).
- Readers that display the record (`vibey ledger show`/`search`); a follow-up.
- Docs (the docs wave records the field in `docs/plans/data-model.md`).

Commit as `feat(ledger): each redaction is recorded with its path and class`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
