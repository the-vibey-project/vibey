## Title
feat(domain): the record of a test run's attempt, its dead letter and the answer to it

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:283-286`): a run that
crashes the harness, exceeds its bound or cannot be executed "is moved to a dead-letter queue
with its evidence, where a human or a repair lane can see it — it is never retried forever and
never silently dropped". Draft ADR-0045 §9 lists that evidence.

A record is mutable only while it is running. Once terminal it is never rewritten, and an
answer to a dead letter is a separate object, never an edit: the discipline the ledger keeps
(CLAUDE.md, "the ledger is append-only"), although these records are not the ledger. A dead
letter never carries a raw pass-through value (ADR-0045 "Security impact": names and digests only).

## Required behaviour
Create `src/vibey/domain/test_run_record.py`. Dataclasses are `@dataclass(frozen=True, slots=True)`.
It imports from `vibey.domain.test_harness` (harness-T01: `TestSelection`, `TestEnvironment`,
`TestOutcome`, `MachineLoad`), `vibey.domain.test_reuse` (harness-T02: `RecordedAttempt`) and
`vibey.domain.test_harness_protocol` (harness-T03: `GateReport`, `TestRunRequest`,
`MalformedTestHarnessMessage`, and the codec helpers through the injected codec).

1. **`TestRunRecord`**, fields in this order:
   `run_id: UUID`, `request_id: UUID`, `key: str`, `attempt: int` (≥ 0; 0 means "not yet numbered",
   the store assigns it), `cwd: str`, `selection: TestSelection`, `environment: TestEnvironment`,
   `requester: str`, `instance: str`, `pid: int`, `delivery_count: int`,
   `started_at: datetime` (aware), `tree_before: str`, `load_before: MachineLoad | None`,
   `log_path: str`, `outcome: TestOutcome | None = None`, `exit_code: int | None = None`,
   `timed_out: bool = False`, `reusable: bool = False`, `tree_after: str | None = None`,
   `finished_at: datetime | None = None`, `duration_seconds: float | None = None`,
   `load_after: MachineLoad | None = None`, `output_tail: str = ""`,
   `gate_reports: tuple[GateReport, ...] = ()`, `detail: str = ""`, `coverage_data: str | None = None`.

   Invariants, else `ValueError`:
   - a running record (`outcome is None`) has `finished_at is None` and `reusable is False`;
   - a terminal record has an aware `finished_at >= started_at`;
   - `reusable` implies `outcome.is_reusable()`, `tree_after == tree_before` and `selection.reusable`.
2. **`finish(self, *, outcome, exit_code, timed_out, tree_after, finished_at, duration_seconds, load_after, output_tail, gate_reports, detail, coverage_data) -> TestRunRecord`**
   returns a `dataclasses.replace` copy with
   `reusable = outcome.is_reusable() and tree_after == self.tree_before and self.selection.reusable`.
   Finishing a terminal record raises `ValueError("a terminal test-run record is never rewritten")`.
3. **`as_attempt(self, *, answered: bool = False) -> RecordedAttempt`** returns
   `RecordedAttempt(str(self.run_id), self.attempt, self.outcome, self.finished_at, self.reusable, answered)`.
4. **`DeadLetter`**: `run_id: UUID`, `request_id: UUID`, `cwd: str`, `selection: TestSelection`,
   `env_names: tuple[str, ...]`, `requester: str`, `outcome: TestOutcome` (must satisfy
   `is_dead_letter()`), `reason: str` (non-empty), `record: TestRunRecord | None`,
   `dead_lettered_at: datetime` (aware). The classmethod
   `from_request(cls, request: TestRunRequest, *, run_id, outcome, reason, record, at) -> DeadLetter`
   copies `request_id`, `cwd`, `selection`, the env **names** only (`tuple(n for n, _ in request.env)`)
   and `requester`.
5. **`DeadLetterAnswer`**: `run_id: UUID`, `answered_by: str`, `answered_at: datetime` (aware),
   `requeued_request_id: UUID`.
6. **`TestRunRecordCodec(messages: TestHarnessCodecInterface)`**:
   - `encode(self, value: TestRunRecord | DeadLetter | DeadLetterAnswer) -> dict[str, object]` and
     `decode(self, raw: Mapping[str, object])`, under the schemas `vibey.test.record/1`,
     `vibey.test.dead_letter/1` and `vibey.test.dead_letter_answer/1`;
   - `to_bytes` and `from_bytes`, as in harness-T03;
   - `MachineLoad` encodes as `{"load1": ..., "load5": ..., "load15": ..., "cpu_count": ...}` or `null`;
   - nested selections, environments and gate reports go through the injected codec's public
     helpers (`encode_selection`, `decode_selection`, …). Compose; do not copy them.

   It is exactly as strict as harness-T03, raising `MalformedTestHarnessMessage`.
7. **The interface** `src/vibey/domain/interfaces/test_run_record_interface.py` declares
   `TestRunRecordCodecInterface` (`@runtime_checkable`, every public method).

## Where to change
- New `src/vibey/domain/test_run_record.py`, `src/vibey/domain/interfaces/test_run_record_interface.py`,
  `tests/domain/test_test_run_record.py`.

## Acceptance criteria
- [ ] `finish` computes `reusable` for each combination of outcome, tree change and selection reusability.
- [ ] Each invariant is enforced.
- [ ] All three types round-trip; a record round-trips both while running and when finished.
- [ ] A dead letter never carries a raw env value (`from_request` keeps names only).
- [ ] 100% coverage of `src/vibey/domain/`; `tests/domain/test_domain_purity.py` passes.

## Tests to write first (TDD)
`tests/domain/test_test_run_record.py` (modules only: `from vibey.domain import test_run_record as trr`, …):
- `test_finish_computes_reusable` (parametrized)
- `test_finishing_a_terminal_record_is_refused`
- `test_record_invariants` (parametrized)
- `test_as_attempt_carries_the_answered_flag`
- `test_dead_letter_requires_a_dead_letter_outcome`
- `test_dead_letter_from_request_keeps_env_names_only`
- `test_round_trips` (parametrized over the three types, and over a running and a finished record)
- `test_decode_rejects_extra_and_missing_keys`
- `test_codec_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Storing records (harness-T10).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T02-test-reuse-policy, harness-T03-test-harness-messages.
- **Files touched:** the three files above.
- **Shares a file with:** none.
- **Must keep passing unchanged:** `tests/domain/test_domain_purity.py`, the harness-T01–T03 tests, and the protected tests.
- **Registry (amendment A4):** nothing. The codec is a pure policy and the records are values.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
