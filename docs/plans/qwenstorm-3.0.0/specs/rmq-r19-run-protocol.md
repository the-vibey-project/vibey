## Title
feat(domain): the loop-service wire protocol

## Why
ADR-0044 §13. Callers publish run requests instead of spawning runners, and a
long-lived service per engine answers. The messages are a contract between two
processes, so they are pure, versioned and strictly decoded.

Two non-negotiables live in this contract:

- **No result carries a completion claim.** Completion stays the caller's judgement,
  checked after any capacity rejection (`build_implement_handler.py:241-263`).
- **No message carries a capacity field.** A credits exhaustion can never acquire a
  `resets_at` on the wire (the `CreditsExhausted` type at `domain/capacity.py:21-24`).

The service may run only its own binary with safe leading arguments. That argument
policy is pure too.

## Required behaviour
1. **Schema constants.** `vibey.run.request/1`, `vibey.run.accepted/1`,
   `vibey.run.progress/1`, `vibey.run.result/1`, `vibey.run.control/1`.
2. **Enums.**

   | enum | members (value) |
   |---|---|
   | `RunPurpose(StrEnum)` | `RUN` (`"run"`), `PROBE` (`"probe"`) |
   | `RunStatus(StrEnum)` | `EXITED`, `SUPERSEDED`, `ABANDONED`, `REJECTED`, `DEAD_LETTERED`, `DEADLINE_EXCEEDED`, each valued as its lower-case name |
   | `RunControlCommand(StrEnum)` | `STOP` (`"stop"`), `WIND_DOWN` (`"wind_down"`), `PROMPT_NOW` (`"prompt-now"`), `PROMPT_AT_BREAK` (`"prompt-at-break"`) |

3. **Messages.** All are frozen, slotted dataclasses, and every datetime must be
   timezone-aware.

   | dataclass | fields |
   |---|---|
   | `RunSupersede` | `key: str`, `attempt: int` (≥ 0) |
   | `RunRequest` | `run_id: UUID`, `engine_id: str`, `purpose: RunPurpose`, `args: tuple[str, ...]`, `cwd: str` (absolute), `run_dir: str \| None`, `supersedes: RunSupersede \| None`, `deadline_seconds: int` (≥ 1), `start_by: datetime`, `capture_output: bool`, `requested_at: datetime`, `caller: str` |
   | `RunAccepted` | `run_id`, `service_instance: str`, `pid: int \| None`, `started_at: datetime` |
   | `RunProgress` | `run_id`, `seq: int` (≥ 1), `line: str` |
   | `RunResult` | `run_id`, `status: RunStatus`, `exit_code: int \| None`, `meta_status: str \| None`, `started_at: datetime \| None`, `finished_at: datetime`, `detail: str`, `stdout: str \| None`, `stderr: str \| None` |
   | `RunControl` | `run_id`, `command: RunControlCommand`, `text: str \| None` |

   `RunResult` has **no** completion, success or capacity field.
4. **Codec.** `RunProtocolCodec` has `encode(message) -> dict[str, object]`, a
   `decode(raw) -> RunMessage` that dispatches on `schema` (where `RunMessage` is the
   union of the five message types), `to_bytes` and `from_bytes`. Decoding rejects an
   unknown schema, a missing key, **any extra key**, a wrong type and a naive datetime,
   raising the new `MalformedRunMessage(VibeyError)`. In particular a `resets_at`,
   `complete`, `success` or `capacity_state` key is rejected.
5. **Argument policy.** `RunArgsPolicy.reason(purpose, args) -> str | None` returns
   `None` when the arguments are allowed, and a human-readable reason otherwise.
   - For `RUN`, `args[0]` must be `run` or `resume`.
   - For `PROBE`, `args` must be exactly `("--version",)`, or `("run", "--help")`, or
     begin with `"doctor"`.
   - Empty `args`, or any argument containing `"\x00"`, is refused.
6. There is no clock, no I/O and no async anywhere in the module.

## Where to change
- `src/vibey/domain/run_protocol.py` and its interface
  (`RunProtocolCodecInterface`, `RunArgsPolicyInterface`).
- Copy R06's codec style.

## Acceptance criteria
- [ ] Hypothesis round trips hold for every message type.
- [ ] Every malformation is rejected, including each forbidden key.
- [ ] The encoded keys of `RunResult` are exactly the declared set.
- [ ] The argument policy table holds.
- [ ] 100% domain coverage; the purity test passes.

## Tests to write first (TDD)
- `tests/domain/test_run_protocol.py`:
  - `test_round_trip_properties` (Hypothesis, one per message type)
  - `test_decode_rejects_each_malformation`
  - `test_forbidden_keys_are_rejected` (parametrized over `resets_at`, `complete`, `success`, `capacity_state`)
  - `test_run_result_has_no_completion_or_capacity_field`
  - `test_args_policy_table`
  - `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Any broker or process code.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/domain/run_protocol.py` (new)
  - `src/vibey/domain/interfaces/run_protocol_interface.py` (new)
  - `src/vibey/domain/errors.py` (add one exception)
  - `tests/domain/test_run_protocol.py` (new)
- **Parallel-safe with:** every wave-1 lane. R06 also adds one exception to `errors.py`; the two additions merge trivially.
- **Must keep passing unchanged:**
  - `tests/domain/test_domain_purity.py`
  - `tests/domain/test_capacity.py`
  - `tests/domain/test_circuit.py`
  - all protected tests
- **Standing constraints:** see the header list.

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
