## Title
feat(domain): the surface operation catalogue — what goes on the wire and how each operation may be retried

## Why
Draft ADR-0047 §3 (`specs/ADR-surface-lanes.md`) puts one pure table in the domain that
declares, for every operation on every sovereign surface, its parameters, how it answers, and
its idempotency class. "The client, the lane, the codec and the redaction all read it" — so it
is the one definition of the surface wire, and the lane validates every request against it
before calling anything ("Security impact", last bullet: "The operation names a method from a
fixed table, never an attribute taken from a message"). The surfaces are 8.f's list
(`src/vibey_tools/gh/docs/doctrines.md`, "8.f"); the bus is exempt by that same text ("The
bus itself, RabbitMQ, is the one surface that cannot be driven by itself"). The ports are
`src/vibey/application/interfaces/{tracker,docs,secrets,files,email,sms,messaging,config_store,cache,blob,siem}.py`.
ADR-0047 lane S02.

## Required behaviour
In the new `src/vibey/domain/surface_catalogue.py`:

1. Enums (`StrEnum`):
   - `SurfaceName`: `TRACKER="tracker"`, `DOCS="docs"`, `SECRETS="secrets"`, `FILES="files"`,
     `EMAIL="email"`, `SMS="sms"`, `MESSAGING="messaging"`, `CONFIGURATION="configuration"`,
     `CACHE="cache"`, `BLOB="blob"`, `SIEM="siem"`. Property `config_table -> str` returns the
     `vibey.toml` table: `"config_store"` for `CONFIGURATION`, otherwise the value.
   - `ReplyMode`: `ANSWER="answer"`, `ACK="ack"`, `ACCEPT="accept"`.
   - `IdempotencyClass`: `READ="read"`, `OVERWRITE="overwrite"`, `NATIVE="native"`, `GUARDED="guarded"`.
   - `ParamKind`: `STR="str"`, `OPTIONAL_STR="optional_str"`, `OPTIONAL_INT="optional_int"`, `BYTES="bytes"`, `MAPPING="mapping"`.
   - `ResultKind`: `NONE="none"`, `STR="str"`, `OPTIONAL_STR="optional_str"`, `BYTES="bytes"`, `MAPPING="mapping"`.
   - `NotFound`: `NONE="none"`, `KEY_ERROR="KeyError"`, `FILE_NOT_FOUND="FileNotFoundError"`.
2. Frozen, slotted dataclasses:
   - `ParamSpec(name: str, kind: ParamKind, sensitive: bool = False, personal: bool = False)`.
     `sensitive` is a secret value; `personal` is a person's private detail (SD-01 §1).
   - `OperationSpec(surface: SurfaceName, operation: str, params: tuple[ParamSpec, ...], reply: ReplyMode, idempotency: IdempotencyClass, result: ResultKind, not_found: NotFound = NotFound.NONE, accepts_key: bool = False, result_sensitive: bool = False)`
     with properties `is_read` (`idempotency is READ`) and `is_send` (`reply is ACCEPT`).
     `operation` is the port method's name.
3. `OPERATIONS: Final[tuple[OperationSpec, ...]]`, exactly these rows, in this order
   (`S`=STR, `OS`=OPTIONAL_STR, `OI`=OPTIONAL_INT, `B`=BYTES, `M`=MAPPING; `*` = `sensitive=True`,
   `†` = `personal=True`):

   | surface | operation | params | reply | class | result | not_found | accepts_key | result_sensitive |
   |---|---|---|---|---|---|---|---|---|
   | tracker | create_ticket | title S, description S | answer | native | S | none | yes | no |
   | tracker | get_ticket_status | ticket_id S | answer | read | S | KeyError | no | no |
   | docs | create_page | title S, content S | answer | guarded | S | none | yes | no |
   | docs | update_page | page_id S, content S | ack | overwrite | none | KeyError | no | no |
   | secrets | get_secret | key S | answer | read | S | KeyError | no | yes |
   | secrets | set_secret | key S, value S* | ack | overwrite | none | none | no | no |
   | files | upload_file | remote_path S, content B | answer | overwrite | S | none | no | no |
   | files | download_file | remote_path S | answer | read | B | FileNotFoundError | no | no |
   | email | send_email | to_addr S†, subject S†, body S† | accept | guarded | none | none | yes | no |
   | sms | send_sms | phone_number S†, message S† | accept | guarded | none | none | yes | no |
   | messaging | send_message | channel_id S, message S† | accept | native | none | none | yes | no |
   | configuration | create_config | key S, value S* | ack | overwrite | none | none | no | no |
   | configuration | get_config | key S | answer | read | S | KeyError | no | yes |
   | cache | get | key S | answer | read | OS | none | no | yes |
   | cache | set | key S, value S*, ttl_seconds OI | ack | overwrite | none | none | no | no |
   | cache | delete | key S | ack | overwrite | none | none | no | no |
   | blob | put_blob | bucket S, key S, content B, content_type OS | answer | overwrite | S | none | no | no |
   | blob | get_blob | bucket S, key S | answer | read | B | FileNotFoundError | no | no |
   | siem | send_event | index S, event M† | accept | native | none | none | yes | no |

   Parameter order equals the port method's positional order.
4. `PING_OPERATION: Final = "_ping"`. It is not a row: every lane answers it itself.
5. `BUS_EXEMPT_MESSAGE: Final = "RabbitMQ is the medium the surface lanes run on, so the bus has no lane: a request for the bus would have to travel on the bus (sub-doctrine 8.f; ADR-0047 §11)."`
6. `class SurfaceCatalogue`, `__init__(self, operations: tuple[OperationSpec, ...] = OPERATIONS)`:
   - `get(self, surface: SurfaceName, operation: str) -> OperationSpec`: the row, or, for
     `PING_OPERATION`, `OperationSpec(surface, PING_OPERATION, (), ReplyMode.ANSWER, IdempotencyClass.READ, ResultKind.MAPPING)`.
     Anything else raises `KeyError(f"no operation {operation!r} on the {surface.value} surface")`.
   - `for_surface(self, surface) -> tuple[OperationSpec, ...]` (rows only, table order).
   - `surfaces(self) -> tuple[SurfaceName, ...]`: every `SurfaceName`, enum order.
   - `parse_surface(self, raw: str) -> SurfaceName`: strips and lower-cases; `"bus"` raises
     `ValueError(BUS_EXEMPT_MESSAGE)`; an unknown name raises
     `ValueError(f"unknown surface {raw!r}; one of: tracker, docs, secrets, files, email, sms, messaging, configuration, cache, blob, siem")`.
   - Constructing it with two rows for one `(surface, operation)` raises `ValueError`.
7. `CATALOGUE: Final[SurfaceCatalogueInterface] = SurfaceCatalogue()`, with the one-line
   "stateless; one instance serves" comment `EVENT_KIND_PARSER` uses (`src/vibey/domain/ledger.py:128-129`).
8. `src/vibey/domain/interfaces/surface_catalogue_interface.py`:
   `@runtime_checkable class SurfaceCatalogueInterface(Protocol)` with the four methods;
   exported from `src/vibey/domain/interfaces/__init__.py`.
9. No clock, I/O or async (non-negotiable 4).

## Where to change
- New `src/vibey/domain/surface_catalogue.py`, `src/vibey/domain/interfaces/surface_catalogue_interface.py`.
- `src/vibey/domain/interfaces/__init__.py` (export).
- New `tests/domain/test_surface_catalogue.py`.

## Acceptance criteria
- [ ] The table has exactly 19 rows; every `(surface, operation)` names a method that exists on its port (`hasattr(IssueTrackerPort, "create_ticket")` and so on — the test imports the ports, the source does not).
- [ ] Every row's parameter names equal the port method's parameter names after `self`, in order, ignoring `idempotency_key`.
- [ ] `get(SurfaceName.CACHE, "_ping")` is an answer-mode read with a mapping result; an unknown operation is a `KeyError` naming the surface.
- [ ] `parse_surface(" Bus ")` raises with `BUS_EXEMPT_MESSAGE`; `parse_surface("nope")` lists all eleven names.
- [ ] Guarded rows are exactly `docs.create_page`, `email.send_email`, `sms.send_sms`; native rows exactly `tracker.create_ticket`, `messaging.send_message`, `siem.send_event` (ADR §3, §8).
- [ ] `test_domain_purity.py` passes; 100% `domain/` branch coverage.

## Tests to write first (TDD)
`tests/domain/test_surface_catalogue.py` (no service):
- `test_every_row_names_a_port_method_with_the_same_parameters`
- `test_guarded_and_native_rows_are_exactly_the_adr_s`
- `test_sensitive_and_personal_parameters` (set_secret.value, create_config.value, cache set value sensitive; email's three, sms's two, messaging message and siem event personal)
- `test_ping_is_answered_for_every_surface`
- `test_unknown_operation_is_a_key_error_naming_the_surface`
- `test_parse_surface_refuses_the_bus_and_unknown_names`
- `test_config_table_names_the_vibey_toml_table`
- `test_duplicate_rows_are_refused`
- `test_catalogue_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/domain/test_surface_catalogue.py tests/domain/test_domain_purity.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- The `idempotency_key` keyword on the ports (the `surfaces-adapter-*` lanes). The queue names
  (`surfaces-queue-names`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the
  skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally
  with the Title as the subject.

## Lane card
- **Depends on:** none.
- **Shares a file with:** `src/vibey/domain/interfaces/__init__.py` (exports only).
- **Must keep passing unchanged:** `tests/domain/*`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file. Change existing files with `edit_file` or a checked replacement.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol beside it; frozen dataclasses and enums are values and need none.
  - The default run needs no service; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
