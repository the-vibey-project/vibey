## Title
feat(domain): SurfaceArgsCodec types each operation's arguments and result for the wire, bytes as base64

## Why
Draft ADR-0047 §5 (`specs/ADR-surface-lanes.md`): "Arguments are typed by the catalogue. Bytes
travel as `{"b64": …}`." ADR-0044's messages carry only ids, but surface operations carry
values and bytes ("What does not fit", "Some arguments are secrets or bytes"): `upload_file`
and `put_blob` send bytes, `download_file` and `get_blob` return them. One pure codec, read by
the client (before publishing) and the lane (before calling the adapter), keeps the two sides
of the wire from drifting. Part of ADR-0047 lane S03.

## Required behaviour
In the new `src/vibey/domain/surface_args.py`, `class SurfaceArgsCodec` (stateless), over
`OperationSpec` and `ParamKind`/`ResultKind` from `surface_catalogue.py`:

1. `to_wire(self, spec: OperationSpec, args: Mapping[str, object]) -> dict[str, object]`
   (the caller's side; a caller's bug is a `ValueError`, raised before anything is published):
   - the key set must equal the spec's parameter names exactly; a missing or extra name raises
     `ValueError(f"{spec.surface.value}.{spec.operation}: expected arguments {names}, got {given}")`;
   - per kind: `STR` must be a `str`; `OPTIONAL_STR` a `str` or `None`; `OPTIONAL_INT` an `int`
     that is not a `bool`, or `None`; `BYTES` `bytes`, `bytearray` or `memoryview`, encoded as
     `{"b64": base64.b64encode(bytes(v)).decode("ascii")}`; `MAPPING` a `Mapping` with `str`
     keys whose `json.dumps(v, sort_keys=True)` succeeds, stored as
     `json.loads(json.dumps(v))` (a JSON-safe copy). Anything else raises `ValueError` naming
     the parameter and the expected kind.
2. `from_wire(self, spec, wire: Mapping[str, object]) -> dict[str, object]` (the lane's side):
   the exact inverse, with the same checks, raising `MalformedSurfaceMessage` instead of
   `ValueError`. A `BYTES` value must be exactly `{"b64": <str>}` and decode with
   `base64.b64decode(value, validate=True)`.
3. `result_to_wire(self, spec, value: object) -> object` (the lane's side): `NONE` → value must
   be `None`, returns `None`; `STR` → `str`; `OPTIONAL_STR` → `str` or `None`; `BYTES` →
   `{"b64": ...}`; `MAPPING` → a JSON-safe `dict`. A mismatch raises `ValueError` naming the
   operation (an adapter broke its port).
4. `result_from_wire(self, spec, wire: object) -> object` (the caller's side): the inverse,
   raising `MalformedSurfaceMessage` on a mismatch.
5. `SURFACE_ARGS: Final[SurfaceArgsCodecInterface] = SurfaceArgsCodec()`.
6. `src/vibey/domain/interfaces/surface_args_interface.py`:
   `@runtime_checkable class SurfaceArgsCodecInterface(Protocol)` with the four methods;
   exported from `src/vibey/domain/interfaces/__init__.py`.
7. Pure (`base64` and `json` are stdlib and do no I/O).

## Where to change
- New `src/vibey/domain/surface_args.py`, `src/vibey/domain/interfaces/surface_args_interface.py`.
- `src/vibey/domain/interfaces/__init__.py` (export).
- New `tests/domain/test_surface_args.py`.

## Acceptance criteria
- [ ] Hypothesis: for every catalogue row, `from_wire(spec, to_wire(spec, args)) == args` for generated valid arguments (bytes compare equal as `bytes`).
- [ ] `to_wire` refuses a missing name, an extra name (including `idempotency_key`, which is never an argument on the wire), a `bool` for `ttl_seconds`, a `str` for `content`, and a non-JSON mapping, each with a `ValueError` naming the parameter.
- [ ] `from_wire` refuses `{"b64": "!!"}`, `{"b64": 1}` and `{"b64": "", "x": 1}` with `MalformedSurfaceMessage`.
- [ ] Results round-trip for every `ResultKind`; `result_to_wire` refuses a `str` for a `NONE` result.
- [ ] `test_domain_purity.py` passes; 100% `domain/` branch coverage.

## Tests to write first (TDD)
`tests/domain/test_surface_args.py` (no service):
- `test_every_operation_round_trips_its_arguments` (Hypothesis, parametrized over `OPERATIONS`)
- `test_to_wire_refuses_each_caller_mistake` (parametrized)
- `test_from_wire_refuses_bad_base64_as_malformed`
- `test_results_round_trip_for_every_kind`
- `test_result_to_wire_refuses_a_broken_adapter_result`
- `test_codec_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/domain/test_surface_args.py tests/domain/test_domain_purity.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- The payload size limit (the client checks the encoded request, `surfaces-lane-client`).
  Redaction (`surfaces-redaction`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md
  and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit
  locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-catalogue`, `surfaces-errors`.
- **Shares a file with:** `src/vibey/domain/interfaces/__init__.py` (exports only).
- **Must keep passing unchanged:** `tests/domain/*`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from a sibling file.
  - The default run needs no service; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
