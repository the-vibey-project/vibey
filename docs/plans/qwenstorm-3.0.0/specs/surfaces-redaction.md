## Title
feat(domain): surface requests are redacted for the ledger and for dead letters, and every redaction is recorded

## Why
Two records keep a surface request after its operation is over, and they need different
redaction:

- **The ledger** (sub-doctrine 7.c, `src/vibey_tools/gh/docs/doctrines.md` "7.c"): "secrets,
  credentials and people's private details are redacted where they would appear, and the
  redaction is itself recorded — never a silent omission." SD-01 §1 forbids relaying private
  details. So a secret value, a person's address, number or message, and raw bytes never enter
  the ledger; each is replaced by a digest, and the payload lists what was redacted and why.
- **A dead letter** (draft ADR-0047 §9, `specs/ADR-surface-lanes.md`): "A sensitive argument
  becomes `sha256:<digest>`. A bytes argument becomes its length and digest. `retained` says
  whether the request can be rebuilt from the row." Email bodies and SMS text **are** retained
  ("Security impact", last bullets), because a person must be able to decide and requeue them.

A guarded operation also needs a stable digest of its full request, stored in
`surface_operation.request_digest`, so that one idempotency key reused with other arguments is
rejected (ADR §8). Pure; one class serves all three. Part of ADR-0047 lanes S03 and S25.

## Required behaviour
In the new `src/vibey/domain/surface_redaction.py`:

1. `class RedactionClass(StrEnum)`: `SENSITIVE="sensitive"`, `PERSONAL="personal"`, `BYTES="bytes"`.
2. Frozen, slotted dataclasses: `Redaction(path: str, kind: RedactionClass)` and
   `RedactedArgs(args: Mapping[str, object], redactions: tuple[Redaction, ...])` with a
   property `retained -> bool` (`not redactions`).
3. `class SurfaceRequestRedactor` (stateless), over wire arguments (the output of
   `SurfaceArgsCodec.to_wire`, lane `surfaces-args-codec`):
   - `digest(self, value: object) -> str`: a `str` → `"sha256:" + sha256(value.encode("utf-8")).hexdigest()`;
     anything else → `"sha256:" + sha256(canonical_bytes({"v": value})).hexdigest()`, with
     `canonical_bytes` from `vibey.domain.ledger`.
   - `for_ledger(self, spec: OperationSpec, wire_args: Mapping[str, object]) -> RedactedArgs`:
     for each parameter in spec order, a `None` value is kept as is; otherwise a `sensitive`
     parameter becomes `digest(v)` with `Redaction(f"args.{name}", SENSITIVE)`; a `personal`
     one becomes `digest(v)` with `PERSONAL` (sensitive wins when both); a `BYTES` value
     `{"b64": s}` becomes `{"bytes": n, "sha256": hex}` over the decoded bytes, with `BYTES`;
     anything else is kept verbatim.
   - `for_dead_letter(self, spec, wire_args) -> RedactedArgs`: the same, except `personal`
     values are **kept** verbatim and not listed.
   - `result_for_ledger(self, spec, wire_result: object) -> tuple[object, tuple[Redaction, ...]]`:
     `None` → `(None, ())`; `spec.result_sensitive` → `(digest(v), (Redaction("result", SENSITIVE),))`;
     a `BYTES` result → `({"bytes": n, "sha256": hex}, (Redaction("result", BYTES),))`;
     otherwise the value with no redaction.
   - `request_digest(self, spec, wire_args) -> str`: the hex SHA-256 of
     `canonical_bytes({"surface": spec.surface.value, "operation": spec.operation, "args": dict(wire_args)})`
     over the **unredacted** wire arguments. The same arguments always give the same digest.
4. `SURFACE_REDACTOR: Final[SurfaceRequestRedactorInterface] = SurfaceRequestRedactor()`.
5. `src/vibey/domain/interfaces/surface_redaction_interface.py`:
   `@runtime_checkable class SurfaceRequestRedactorInterface(Protocol)` with the five
   methods; exported from `src/vibey/domain/interfaces/__init__.py`.
6. Pure (`hashlib`, `base64`, `json`).

## Where to change
- New `src/vibey/domain/surface_redaction.py`, `src/vibey/domain/interfaces/surface_redaction_interface.py`.
- `src/vibey/domain/interfaces/__init__.py` (export).
- New `tests/domain/test_surface_redaction.py`.

## Acceptance criteria
- [ ] For `secrets.set_secret` with `value="hunter2"`, `for_ledger` and `for_dead_letter` both hide the value (`"sha256:" + sha256(b"hunter2").hexdigest()`) and list `args.value` as sensitive; `retained` is false.
- [ ] For `email.send_email`, `for_ledger` hides all three arguments as personal; `for_dead_letter` keeps them and `retained` is true.
- [ ] For `files.upload_file`, both replace `content` with `{"bytes": n, "sha256": ...}`, and `retained` is false.
- [ ] `result_for_ledger` hides `secrets.get_secret`'s result and summarises `files.download_file`'s bytes.
- [ ] `request_digest` is stable across argument order and changes when any value changes.
- [ ] No output of `for_ledger` contains the plaintext of a sensitive or personal value (Hypothesis over generated strings).
- [ ] `test_domain_purity.py` passes; 100% `domain/` branch coverage.

## Tests to write first (TDD)
`tests/domain/test_surface_redaction.py` (no service):
- `test_secret_values_are_digested_everywhere`
- `test_personal_values_are_hidden_from_the_ledger_but_kept_for_requeue`
- `test_bytes_become_length_and_digest`
- `test_results_are_redacted_for_the_ledger`
- `test_request_digest_is_stable_and_sensitive_to_every_value`
- `test_no_plaintext_survives_ledger_redaction` (Hypothesis)
- `test_redactor_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/domain/test_surface_redaction.py tests/domain/test_domain_purity.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- The ledger's own `redact_payload` (`src/vibey/infrastructure/ledger/redact.py`), which still
  runs at append and is unchanged. Writing ledger events (`surfaces-ledger-recorder`).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `surfaces-catalogue`, `surfaces-args-codec`.
- **Shares a file with:** `src/vibey/domain/interfaces/__init__.py` (exports only).
- **Must keep passing unchanged:** `tests/domain/*`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from a sibling file.
  - The default run needs no service; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
