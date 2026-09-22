## Title
feat(domain): decide what a dispatch that could not be claimed means

## Why
ADR-0044 §5. In the RabbitMQ backend a worker takes a delivery, then claims its row
with a fenced compare-and-set. When that claim misses, the worker must choose one of
two actions:

- drop the message, because it is stale, terminal, parked, or blocked behind a
  dependency that a release will re-dispatch;
- re-delay it, because a live lease holds it or it is not due yet.

Getting that wrong either loses a job or spins it forever, so the decision is a pure,
property-tested function. `now` is an argument, never a clock (domain purity).

## Required behaviour
1. `@dataclass(frozen=True, slots=True) class DispatchSnapshot`:
   - `state: str`, the stored `job.state` text
   - `dispatch_seq: int`
   - `run_after: datetime`
   - `lease_expires_at: datetime | None`
   - `deps_met: bool`
2. `class DispatchVerdict(StrEnum)` has two members, `DROP = "drop"` and
   `REDELAY = "redelay"`. `@dataclass(frozen=True, slots=True) class DispatchDecision`
   has `verdict`, `not_before: datetime | None` and `reason: str`.
3. `class DispatchMissPolicy.decide(snapshot: DispatchSnapshot | None, message_seq: int, now: datetime) -> DispatchDecision`.
   Apply the first rule that matches, in this order:

   | # | condition | verdict | `not_before` | reason |
   |---|---|---|---|---|
   | a | snapshot is `None` | `DROP` | — | `"unknown job"` |
   | b | `snapshot.dispatch_seq != message_seq` | `DROP` | — | `"stale generation"` |
   | c | state is `succeeded`, `failed`, `cancelled`, `awaiting_human`, `awaiting_capacity`, or anything that is not `ready` or `leased` | `DROP` | — | `"not claimable: <state>"` |
   | d | state `leased`, and `lease_expires_at` is not `None` and `>= now` | `REDELAY` | `max(lease_expires_at, run_after)` | `"held by a live lease"` |
   | e | state `ready` and `not deps_met` | `DROP` | — | `"blocked; its release will dispatch it"` |
   | f | `run_after > now` | `REDELAY` | `run_after` | `"not due"` |
   | g | anything else (a race the claim lost) | `REDELAY` | `now` | `"claim raced; retry now"` |

4. A `REDELAY` decision always has `not_before >= now`. A `DROP` decision always has
   `not_before is None`.

## Where to change
- `src/vibey/domain/dispatch_policy.py` and its interface.
- The interface declares `DispatchMissPolicyInterface.decide`. Follow the style of
  `domain/interfaces/circuit_interface.py`.

## Acceptance criteria
- [ ] Each rule a–g has a test.
- [ ] Hypothesis: for any snapshot, message sequence and `now`, a `DROP` happens whenever the sequences differ, and every `REDELAY` has `not_before >= now`.
- [ ] 100% domain coverage; the purity test passes.

## Tests to write first (TDD)
- `tests/domain/test_dispatch_policy.py`:
  - `test_rule_a_unknown_job_drops` through `test_rule_g_race_redelays_now`
  - `test_properties_hold_for_any_snapshot` (Hypothesis)
  - `test_policy_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Reading the snapshot from the database (R11).
- Acting on the decision (R16).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R06.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/domain/dispatch_policy.py` (new)
  - `src/vibey/domain/interfaces/dispatch_policy_interface.py` (new)
  - `tests/domain/test_dispatch_policy.py` (new)
- **Parallel-safe with:** R04, R10, R21 and R29.
- **Must keep passing unchanged:**
  - `tests/domain/test_domain_purity.py`
  - `tests/domain/test_job.py`
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
