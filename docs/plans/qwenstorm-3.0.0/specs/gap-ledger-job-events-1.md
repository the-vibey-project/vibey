## Title
feat(ledger): the job lifecycle's event kinds and one draft builder for every queue transition

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) requires the ledger to hold
"every job, run … and outcome, with its time, its actor and its evidence, written as it
happens". The ledger has no job vocabulary: `EventKind` (`src/vibey/domain/ledger.py:37-70`)
has no job kind, and job state lives only in the mutable `job` table
(`src/vibey/infrastructure/db/job_repository.py`). No DB CHECK constrains `event.kind`
(`migrations/0002_event.sql:9`, `kind text NOT NULL`), so new kinds need no migration.

This lane adds the vocabulary and one pure builder that turns a job row into a
`LedgerEventDraft`, copying the pattern of `PhaseTransitionedDraftBuilder`
(`src/vibey/infrastructure/db/project_repository.py:64-137`). It wires nothing. The
repository and fake lanes (`gap-ledger-job-events-2` … `-8`) append these drafts in the same
transaction as the job row.

## Required behaviour
1. `src/vibey/domain/ledger.py`: after `DELIVERY_ESTIMATE_RECORDED` (`:70`), add a comment
   `# The job lifecycle (7.c): one event per queue transition, written in the same`
   `# transaction as the job row it describes.` and these members, in this order:
   `JOB_ENQUEUED = "JobEnqueued"`, `JOB_CLAIMED = "JobClaimed"`,
   `JOB_LEASE_RENEWED = "JobLeaseRenewed"`, `JOB_SUCCEEDED = "JobSucceeded"`,
   `JOB_ATTEMPT_FAILED = "JobAttemptFailed"`, `JOB_DEFERRED = "JobDeferred"`,
   `JOB_PARKED = "JobParked"`, `JOB_ATTEMPTS_GRANTED = "JobAttemptsGranted"`,
   `JOB_LEASE_EXPIRED = "JobLeaseExpired"`, `JOB_RELEASED = "JobReleased"`,
   `JOB_DISPATCHED = "JobDispatched"`. Nothing else in the module changes.
2. New `src/vibey/infrastructure/db/job_events.py` (provenance header on line 1, copied from
   `job_repository.py:1`), `class JobEventDraftBuilder`:
   - `__init__(self, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION) -> None`
     (`vibey.domain.correlation`, `vibey.domain.interfaces.correlation_interface`).
   - `_draft(self, record: JobRecord, kind: EventKind, produced_at: datetime, fields: Mapping[str, object]) -> LedgerEventDraft`:
     - if `not isinstance(record.phase, Phase)`: raise
       `ValueError(f"job {record.id} is in phase {record.phase.value!r}, which this vibey does not know; it will not ledger it")`
       (writers stay strict, vibey#287);
     - `payload = {"job_kind": record.kind, "state": record.state.value, "attempts": record.attempts, "max_attempts": record.max_attempts, **fields}`;
     - returns `LedgerEventDraft(project_id=record.project_id, cycle=record.cycle, phase=record.phase, kind=kind, engine_id=None, job_id=record.id, causation_id=None, correlation_id=self._correlation.for_project(record.project_id).value, provenance=Provenance.TRUSTED, produced_at=produced_at, payload=payload, digest=digest_event(payload))`.
   - Every value in `fields` is JSON-native: datetimes as `.isoformat()` (or `None`), UUIDs as
     `str(...)`, mappings as `dict(...)`. The appender serializes with `json.dumps` and no
     `default` (`ledger_repository.py:127`).
   - The public methods, each returning `LedgerEventDraft`. `produced_at` is `record.updated_at`
     unless stated; the listed keys are the `fields`:
     | method | kind | `produced_at` | fields |
     |---|---|---|---|
     | `enqueued(record, *, depends_on: Sequence[UUID])` | `JOB_ENQUEUED` | `record.created_at` | `idempotency_key`, `priority`, `run_after`, `work_item_id`, `depends_on` (list of str, in the given order), `job_payload` (`dict(record.payload)`), `requirement` (`dict(record.requirement)`) |
     | `claimed(record, *, dispatch_seq: int \| None = None)` | `JOB_CLAIMED` | | `owner` (`record.lease_owner`), `lease_expires_at`, `assigned_engine`; plus `dispatch_seq` only when it is not `None` |
     | `lease_renewed(record, *, lease: timedelta)` | `JOB_LEASE_RENEWED` | `record.lease_expires_at - lease` | `owner`, `lease_expires_at`, `lease_seconds` (`lease.total_seconds()`) |
     | `succeeded(record, *, owner: str)` | `JOB_SUCCEEDED` | | `owner` |
     | `attempt_failed(record, *, owner: str, error: Mapping[str, object])` | `JOB_ATTEMPT_FAILED` | | `owner`, `error`, `run_after`, `final` (`record.state is JobState.FAILED`) |
     | `deferred(record, *, owner: str, error: Mapping[str, object])` | `JOB_DEFERRED` | | `owner`, `error`, `retry_at` (`record.run_after`) |
     | `parked(record, *, owner: str \| None, reason: str \| None = None)` | `JOB_PARKED` | | `owner`, `reason` |
     | `attempts_granted(record, *, owner: str)` | `JOB_ATTEMPTS_GRANTED` | | `owner` |
     | `lease_expired(record, *, expired_owner: str \| None, expired_at: datetime \| None)` | `JOB_LEASE_EXPIRED` | | `expired_owner`, `expired_at` |
     | `released(record, *, gate_id: UUID, gate_kind: str, answered_by: str \| None)` | `JOB_RELEASED` | | `gate_id`, `gate_kind`, `answered_by` |
     | `dispatched(record, *, dispatch_seq: int, not_before: datetime, key: str)` | `JOB_DISPATCHED` | | `dispatch_seq`, `not_before`, `key` |
   - `lease_renewed` raises `ValueError(f"job {record.id} was renewed but carries no lease expiry")`
     when `record.lease_expires_at is None`.
   - `JOB_EVENT_DRAFTS: Final[JobEventDraftBuilderInterface] = JobEventDraftBuilder()` with the
     one-line docstring "The builder every job writer shares. Stateless, so one instance serves."
   - The class docstring says: the actor is vibey's queue (`engine_id=None`, `TRUSTED`);
     `produced_at` is the time the row's own statement wrote (database time), for the reason
     `PhaseTransitionedDraftBuilder` gives (`project_repository.py:72-84`); a renewal is dated
     `lease_expires_at - lease`, which is exactly the `now()` the renewal wrote.
3. New `src/vibey/infrastructure/db/interfaces/job_events_interface.py`: `@runtime_checkable
   class JobEventDraftBuilderInterface(Protocol)` declaring the eleven public methods with the
   same signatures and one-line docstrings. Copy the header, docstring and `TYPE_CHECKING`
   import style of `interfaces/project_repository_interface.py:1-19`. Export it from
   `src/vibey/infrastructure/db/interfaces/__init__.py`: the import block and `__all__`, in
   sorted position.

## Where to change
- `src/vibey/domain/ledger.py` (one insertion, with edit_file).
- New `src/vibey/infrastructure/db/job_events.py` and
  `src/vibey/infrastructure/db/interfaces/job_events_interface.py`.
- `src/vibey/infrastructure/db/interfaces/__init__.py` (two insertions).
- New test file `tests/infrastructure/orm/test_job_event_drafts.py` (no database; the directory
  exists since lane `orm-test-harness`).
- Registry: a pure builder with no I/O is its own in-memory implementation; the fakes registry
  scans application ports (`specs/fakes-registry.md:93-96`), so nothing is registered.

## Acceptance criteria
- [ ] `{k.value for k in EventKind if k.name.startswith("JOB_")}` is exactly the eleven values above.
- [ ] Every draft has `engine_id is None`, `provenance is Provenance.TRUSTED`, `job_id == record.id`,
      `cycle`/`phase`/`project_id` from the record, `correlation_id == DELIVERY_CORRELATION.for_project(record.project_id).value`
      and `digest == digest_event(draft.payload)`.
- [ ] `json.loads(json.dumps(draft.payload)) == draft.payload` for every method.
- [ ] A renewal with `lease_expires_at = T` and `lease = 30 s` has `produced_at == T - 30 s`.
- [ ] A record whose phase is `UnrecognizedPhase("FUTURE_PHASE")` raises `ValueError` from every method.
- [ ] `tests/domain/test_ledger_query.py`, `tests/domain/test_forward_compatible_readers.py` and
      `tests/domain/test_domain_purity.py` pass unchanged.
- [ ] 100% branch coverage of `src/vibey/domain/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_job_event_drafts.py` (provenance header on line 1). A helper
`_record(**changes: object) -> JobRecord` builds a full `JobRecord` (phase `Phase.BUILD`, state
`JobState.LEASED`, `lease_owner="w1"`, fixed aware datetimes) and applies
`dataclasses.replace(base, **changes)`.
- `test_every_job_kind_is_an_event_kind`
- `test_enqueued_names_the_request_and_its_dependencies` (two `depends_on` ids, in order; `produced_at == created_at`)
- `test_claimed_carries_owner_lease_and_only_a_given_generation` (`dispatch_seq` absent, then `3`)
- `test_a_renewal_is_dated_at_the_renewal_not_the_expiry`
- `test_a_renewal_without_an_expiry_is_refused`
- `test_attempt_failed_says_whether_it_was_final` (state `READY` → `final is False`; `FAILED` → `True`)
- `test_deferred_carries_retry_at_and_error`
- `test_parked_expired_released_and_dispatched_carry_their_fields` (one assertion block per method)
- `test_every_draft_is_trusted_unattributed_and_correlated` (parametrized over all eleven methods)
- `test_every_payload_survives_a_json_round_trip` (parametrized likewise)
- `test_a_job_in_an_unknown_phase_is_not_ledgered` (parametrized likewise)
- `test_the_builder_is_its_declared_seam` (`isinstance(JOB_EVENT_DRAFTS, JobEventDraftBuilderInterface)`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_job_event_drafts.py tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Appending any of these events (`gap-ledger-job-events-2` … `-8`).
- Publication rules: no job kind is added to `DEFAULT_ALLOWLIST`
  (`src/vibey/domain/publication_policy.py:79`), so the public export withholds them and counts
  them, as it does every unlisted kind. Publishing them is an operator decision.
- Docs (the docs wave records the kinds in `docs/plans/data-model.md`).

Commit as `feat(ledger): the job lifecycle's event kinds and one draft builder`. Do not push.

## Lane card
- **Depends on:** `orm-test-harness` (creates `tests/infrastructure/orm/`).
- **Must keep passing unchanged:** the protected tests.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
