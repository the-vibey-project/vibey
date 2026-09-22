## Title
feat(domain): the job-dispatch envelope, queue names and wait-tier plan

## Why
ADR-0044 §2, §3 and §7 put four pure pieces in the domain:

- the RabbitMQ message that points at a `job` row;
- the names of every exchange and queue;
- the rule that picks a delay tier;
- the configurable prefix (12.c), so that vibey's objects stay apart from Plane's
  Celery queues on a shared broker (`deploy/helm/vibey/values.yaml:246`).

They are pure, so the domain owns them and the 100% domain floor covers them
(ADR-0023).

## Required behaviour
1. `JOB_DISPATCH_SCHEMA = "vibey.job.dispatch/1"`.
2. `@dataclass(frozen=True, slots=True) class JobDispatch`:
   - `job_id: UUID`
   - `project_id: UUID`
   - `dispatch_seq: int`, which must be ≥ 1
   - `kind: str`, which must be non-empty
   - `not_before: datetime`, which must be timezone-aware

   A violation raises `ValueError` in `__post_init__`. The property `message_id`
   returns `f"{job_id}:{dispatch_seq}"`.
3. `class JobDispatchCodec`:
   - `encode(d) -> dict[str, object]` has exactly these keys: `schema`, `job_id`,
     `project_id`, `dispatch_seq`, `kind`, `not_before` (ISO 8601).
   - `decode(raw: Mapping[str, object]) -> JobDispatch` raises the new
     `MalformedDispatch(VibeyError)` (in `domain/errors.py`) on a wrong or missing
     schema, a missing or extra key, a wrong type, a naive datetime, or a sequence
     below 1.
   - `to_bytes(d) -> bytes` is `json.dumps(encode(d), sort_keys=True)` encoded as
     UTF-8. `from_bytes(b) -> JobDispatch` decodes, and invalid JSON or UTF-8 raises
     `MalformedDispatch`.
4. `class QueueNames(prefix: str = "vibey")`, which returns exactly these strings.
   The duration label is `Ns` below 60 seconds, `Nm` for whole minutes below an hour,
   `Nh` for whole hours, and `Ns` for anything else.

   | method | returns |
   |---|---|
   | `jobs_exchange()` | `"<p>.jobs"` |
   | `project_queue(pid)` | `"<p>.jobs.<pid>"` |
   | `project_key(pid)` | `"job.<pid>"` |
   | `project_bindings(pid)` | `("job.<pid>", "*.job.<pid>")` |
   | `wait_exchange()` | `"<p>.jobs.wait"` |
   | `wait_queue(t)` | `"<p>.jobs.wait.w<label>"` |
   | `wait_key(t, pid)` | `"w<label>.job.<pid>"` |
   | `wait_binding(t)` | `"w<label>.#"` |
   | `dead_exchange()` | `"<p>.jobs.dlx"` |
   | `dead_queue()` | `"<p>.jobs.dead"` |
   | `runs_exchange()` | `"<p>.runs"` |
   | `run_queue(e)` | `"<p>.runs.<e>"` |
   | `probe_queue(e)` | `"<p>.runs.<e>.probe"` |
   | `probe_key(e)` | `"<e>.probe"` |
   | `run_dead_exchange()` | `"<p>.runs.dlx"` |
   | `run_dead_queue(e)` | `"<p>.runs.<e>.dead"` |
   | `control_exchange()` | `"<p>.runs.control"` |

5. `class WaitTierPlan(tiers_seconds: tuple[int, ...])` validates the tiers
   (non-empty, each ≥ 1, strictly ascending) and raises `ValueError` otherwise.
   `choose(remaining: timedelta) -> int | None` returns:
   - `None` when `remaining <= 0`;
   - otherwise the largest tier ≤ `remaining` (in seconds);
   - or the smallest tier when `remaining` is shorter than every tier.
6. Nothing in the module reads a clock, performs I/O or uses async.

## Where to change
- `src/vibey/domain/job_dispatch.py`.
- Copy the frozen-dataclass and validation style of `src/vibey/domain/job.py`.
- Add `MalformedDispatch` beside the other `VibeyError` subclasses in `domain/errors.py`.
- The interface module declares `JobDispatchCodecInterface`, `QueueNamesInterface` and
  `WaitTierPlanInterface`. Copy `domain/interfaces/stored_value_interface.py`.

## Acceptance criteria
- [ ] The Hypothesis round trip `decode(encode(d)) == d` holds, and so does `from_bytes(to_bytes(d)) == d`.
- [ ] Every malformed input named in behaviour 3 raises `MalformedDispatch`.
- [ ] `choose` never returns a tier longer than `remaining`, except when `remaining` is shorter than the smallest tier.
- [ ] `choose` returns `None` exactly when `remaining <= 0`.
- [ ] `test_domain_purity.py` passes; 100% domain coverage.

## Tests to write first (TDD)
- `tests/domain/test_job_dispatch.py`:
  - `test_round_trip_property` (Hypothesis)
  - `test_decode_rejects_each_malformation` (parametrized)
  - `test_message_id_is_job_and_generation`
  - `test_queue_names_table` (parametrized over the table above, with the default prefix and with `"acme"`)
  - `test_tier_labels`
  - `test_wait_plan_validation`
  - `test_choose_property` (Hypothesis)
  - `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Any broker or database code.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/domain/job_dispatch.py` (new)
  - `src/vibey/domain/interfaces/job_dispatch_interface.py` (new)
  - `src/vibey/domain/errors.py` (add one exception)
  - `tests/domain/test_job_dispatch.py` (new)
- **Parallel-safe with:** every wave-1 lane.
- **Must keep passing unchanged:**
  - `tests/domain/test_domain_purity.py`
  - `tests/domain/test_errors.py`
  - all protected tests
- **Standing constraints:** see the list above.

## Standing constraints for every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
  `tests/system/test_delivery_stage_set.py`, `tests/live/**` (`.vibey-gh.toml:78-85`,
  `.github/CODEOWNERS`). They must keep passing.
- **The first line of every new source file** is the provenance comment, copied
  byte-for-byte from line 1 of a sibling file (`vibey-gh check` compares it exactly).
- **No lane needs a running RabbitMQ.** Unit tests use
  `vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (lane R04). Tests against a real
  broker are marked `integration` and skip unless `VIBEY_TEST_AMQP_URL` is set.
- **SQL runs on PostgreSQL 14:** no `MERGE`, no PostgreSQL 15+ syntax. The 14–18 matrix
  runs `tests/infrastructure/db`.
- **Defaults stay today's until R34:** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.

---
