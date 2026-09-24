## Title
feat(domain): the test harness's request and answer, and their strict codec

## Why
Draft ADR-0045 §4 and §12. A test-run request crosses a process boundary in both harness
backends: as a file handed to a detached supervisor (`local`) and as an AMQP message
(`rabbitmq`). The answer comes back the same way. Like ADR-0044's run protocol, the messages
are pure, versioned and strictly decoded: an unknown key is refused rather than guessed at, so
nothing can smuggle a field in (ADR-0045, "How each non-negotiable still holds" 2).

The raw values of the pass-through variables travel in the request, because the child needs
them. The request also proves its own digests: `environment.env` must be the digests of those
values. The codec's helpers are public, because harness-T04 reuses them for records.

The error class lives in this module, not in `domain/errors.py`, following
`InvalidLedgerRecord` in `src/vibey/domain/ledger_record.py:49` and `ConfigError` in
`src/vibey/domain/config.py:38`: it keeps this lane to one source file.
`tests/domain/test_domain_purity.py:52-61` forbids `pathlib` in `domain/`, so "absolute" is a
string check.

## Required behaviour
Create `src/vibey/domain/test_harness_protocol.py`. Dataclasses are `@dataclass(frozen=True, slots=True)`.
It imports `CoverageGate`, `TestSelection`, `TestEnvironment`, `TestOutcome` and `ValueDigest`
from `vibey.domain.test_harness` (harness-T01) and `VibeyError` from `vibey.domain.errors`.

1. **`MalformedTestHarnessMessage(VibeyError)`**, with a one-line docstring, defined in this module.
2. **`AnswerStatus(StrEnum)`**: `EXECUTED = "executed"`, `REUSED = "reused"`, `PARKED = "parked"`,
   `SATURATED = "saturated"`, `STILL_RUNNING = "still_running"`.
3. **`GateReport`**: `include: str`, `fail_under: int`, `passed: bool`, `exit_code: int`, `output: str`.
4. **`TestRunRequest`**:
   - `request_id: UUID`
   - `cwd: str` — must start with `"/"` (absolute; no `pathlib` in `domain/`)
   - `selection: TestSelection`
   - `environment: TestEnvironment`
   - `env: tuple[tuple[str, str], ...]` — `(name, raw value)`, names strictly increasing
   - `fresh: bool`
   - `grant: bool`
   - `requested_at: datetime` — timezone-aware
   - `start_by: datetime` — timezone-aware and `>= requested_at`
   - `requester: str` — non-empty

   `environment.env` must equal `tuple((n, ValueDigest.of(v)) for n, v in env)`, else
   `ValueError("the environment's digests do not match the request's values")`.
5. **`TestRunResult`** (the answer):
   - `request_id: UUID`, `status: AnswerStatus`, `backend: str` (non-empty)
   - `run_id: UUID | None`, `key: str | None`, `outcome: TestOutcome | None`, `exit_code: int | None`
   - `flaky: bool`, `flaky_runs: tuple[str, ...]`
   - `recorded_at: datetime | None` (timezone-aware when set)
   - `tested_tree: str | None`, `output_tail: str`, `gate_reports: tuple[GateReport, ...]`
   - `detail: str`, `log_path: str | None`

   Consistency, else `ValueError`: `EXECUTED` and `REUSED` need `run_id`, `key` and `outcome`;
   `PARKED` needs `run_id`; `SATURATED` and `STILL_RUNNING` need `outcome is None`.
6. **`TestHarnessCodec`**, stateless:
   - `encode(self, message: TestRunRequest | TestRunResult) -> dict[str, object]`;
   - `decode(self, raw: Mapping[str, object]) -> TestRunRequest | TestRunResult`, dispatching on
     `raw["schema"]`: `"vibey.test.request/1"` or `"vibey.test.result/1"`;
   - `to_bytes(self, message) -> bytes` (`json.dumps(encode(message), sort_keys=True).encode("utf-8")`);
   - `from_bytes(self, data: bytes) -> TestRunRequest | TestRunResult`;
   - public helpers, reused by harness-T04: `encode_selection`, `decode_selection`,
     `encode_environment`, `decode_environment`, `encode_gate_report`, `decode_gate_report`.

   The encoded shapes are exact (`null` for `None`; datetimes written with `isoformat()` and read
   with `datetime.fromisoformat`; UUIDs as `str(uuid)`):
   ```json
   {"schema": "vibey.test.request/1", "request_id": "<uuid>", "cwd": "/abs",
    "selection": {"command": ["uv","run","--no-sync","pytest"], "argv": ["-q"],
                  "gates": [{"include": "src/vibey/domain/*", "fail_under": 100}]},
    "environment": {"python": "cpython-3.12.7-darwin-arm64", "distributions": "<hex>",
                    "database": "17.2", "env": [["VIBEY_TEST_DATABASE_URL", "<hex>"]]},
    "env": [["VIBEY_TEST_DATABASE_URL", "postgresql://..."]],
    "fresh": false, "grant": false,
    "requested_at": "2026-09-22T12:00:00+00:00", "start_by": "2026-09-22T13:00:00+00:00",
    "requester": "adam@laptop:4242"}
   ```
   ```json
   {"schema": "vibey.test.result/1", "request_id": "<uuid>", "status": "executed",
    "backend": "local", "run_id": "<uuid>", "key": "<hex>", "outcome": "passed",
    "exit_code": 0, "flaky": false, "flaky_runs": [],
    "recorded_at": "2026-09-22T12:04:19+00:00", "tested_tree": "wt1:<hex>",
    "output_tail": "...", "gate_reports": [{"include": "src/vibey/domain/*",
    "fail_under": 100, "passed": true, "exit_code": 0, "output": "..."}],
    "detail": "", "log_path": "/.../logs/<uuid>.log"}
   ```
7. **Strict decoding.** Each of these raises `MalformedTestHarnessMessage` (with the cause chained):
   an unknown schema; a missing key; **any extra key** (at every nesting level); a wrong JSON type
   (a `bool` is not an `int`: check `isinstance(v, bool)` before `isinstance(v, int)`); an invalid
   UUID or enum value; a naive datetime; and any `ValueError` from a constructor. `from_bytes`
   also raises it on invalid UTF-8 or invalid JSON, and when the top level is not an object.
8. **The interface** `src/vibey/domain/interfaces/test_harness_protocol_interface.py` declares
   `TestHarnessCodecInterface` (`@runtime_checkable`), with every public method above.

## Where to change
- New `src/vibey/domain/test_harness_protocol.py` and
  `src/vibey/domain/interfaces/test_harness_protocol_interface.py`. Copy the strict-codec style of
  `src/vibey/domain/ledger_record.py` (its `InvalidLedgerRecord` and codec).
- New `tests/domain/test_test_harness_protocol.py`.
- Do **not** edit `src/vibey/domain/errors.py`.

## Acceptance criteria
- [ ] Both message types round-trip through `to_bytes` and `from_bytes`, with every optional field both set and `None`.
- [ ] Every malformation in behaviour 7 is rejected, each by its own test case.
- [ ] A request whose digests do not match its values is rejected, both at construction and on decode.
- [ ] 100% coverage of `src/vibey/domain/`; `tests/domain/test_domain_purity.py` passes.

## Tests to write first (TDD)
`tests/domain/test_test_harness_protocol.py` imports modules only
(`from vibey.domain import test_harness_protocol as thp`, `from vibey.domain import test_harness as th`):
- `test_request_round_trip`
- `test_result_round_trip_for_each_status` (parametrized over the five statuses)
- `test_decode_rejects_each_malformation` (parametrized: unknown schema, missing key, extra top-level key, extra nested key, bool for int, bad uuid, bad enum, naive datetime)
- `test_request_digests_must_match_values`
- `test_request_cwd_must_be_absolute_and_start_by_not_before_requested_at`
- `test_result_status_consistency` (parametrized)
- `test_from_bytes_rejects_invalid_json_and_utf8`
- `test_codec_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Records and dead letters (harness-T04). Any transport (harness-T10, T23, T24).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T01-test-run-key.
- **Files touched:** the three files above.
- **Shares a file with:** none (the error class stays in this module, so `domain/errors.py` is not shared).
- **Must keep passing unchanged:** `tests/domain/test_domain_purity.py`, every test under `tests/domain/`, and the protected tests.
- **Registry (amendment A4):** nothing. The codec is a pure policy (`PURE_POLICY`), not a seam.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
