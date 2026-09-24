## Title
feat(surfaces): SurfaceFailurePolicy decides, per idempotency class, which failures a lane retries, which park, and which are final

## Why
Draft ADR-0047 §8 (`specs/ADR-surface-lanes.md`, "Which failures are retried"):
- a **read** is never retried inside the lane; it fails fast and the caller decides;
- an **overwrite** or **native** operation is retried on transport errors — `OSError`, a
  timeout, and HTTP 5xx or 429 — with waits `retry_backoff_seconds`, through the family's retry
  (lane `surfaces-async-retry`);
- a **guarded** operation is retried only on errors raised **before** anything was sent
  (connection refused, name resolution, `SMTPConnectError`); any other transport error, or a
  timeout, is `outcome_unknown` and parks;
- everything else is permanent.

The adapters flatten HTTP errors into `RuntimeError` but chain the `HTTPError` as `__cause__`
(for example `src/vibey/infrastructure/tracker/plane.py:63-64`), so the status is read from the
exception chain instead of by changing twelve adapters. A not-found (`KeyError`,
`FileNotFoundError`) is never a failure to retry: it is the operation's answer. ADR-0047 lane
S17.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/failure_policy.py`:

1. `class FailureVerdict(StrEnum)`: `RETRY="retry"`, `OUTCOME_UNKNOWN="outcome_unknown"`,
   `PERMANENT="permanent"`, `NOT_FOUND="not_found"`.
2. `class SurfaceFailurePolicy` (stateless):
   - `classify(self, spec: OperationSpec, exc: BaseException) -> FailureVerdict`, in this order:
     1. `KeyError` or `FileNotFoundError` → `NOT_FOUND`.
     2. `spec.is_read` → `PERMANENT`.
     3. `before_sent(exc)` → `RETRY` (for every class).
     4. `transient(exc)` → `RETRY` for `OVERWRITE` and `NATIVE`, `OUTCOME_UNKNOWN` for `GUARDED`.
     5. otherwise `PERMANENT`.
   - `before_sent(self, exc) -> bool`: some exception in the chain (the exception, then
     `__cause__`, then `__context__`, at most 10 links) is a `ConnectionRefusedError`, a
     `socket.gaierror`, a `smtplib.SMTPConnectError`, or a `urllib.error.URLError` that is
     **not** an `HTTPError` and whose `reason` is a `ConnectionRefusedError` or a `socket.gaierror`.
   - `transient(self, exc) -> bool`: some exception in the chain is an `urllib.error.HTTPError`
     with `code == 429` or `code >= 500`; or a `TimeoutError` (which includes
     `asyncio.TimeoutError`); or an `smtplib.SMTPServerDisconnected`; or an `EOFError` (which
     includes `asyncio.IncompleteReadError`, a dropped Valkey connection); or an `OSError` that
     is neither an `HTTPError` with a 4xx code nor an `smtplib.SMTPException` other than
     `SMTPServerDisconnected` (every SMTP refusal — recipients, sender, data, authentication,
     HELO — is an `OSError` subclass too, and is permanent). A `RedisError` counts only through its cause (the
     pipeline raises it `from` the transport error); an error reply from the server (a
     `RedisError` with no cause) is permanent. An `HTTPError` with any other 4xx code is **not** transient, wherever it
     appears in the chain (check it first).
   - `retry_for(self, spec: OperationSpec, settings: SurfacesConfigInterface, *, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> AsyncRetryInterface`:
     `AsyncRetry(operation=f"surface.{spec.surface.value}.{spec.operation}", backoff_seconds=() if spec.is_read else settings.retry_backoff_seconds, retry_if=<a bound method returning classify(spec, e) is RETRY>, sleep=sleep)`.
     Use a small private class for the predicate rather than a lambda if mypy needs it.
3. `FAILURE_POLICY: Final[SurfaceFailurePolicyInterface] = SurfaceFailurePolicy()`.
4. `src/vibey/infrastructure/surface_lanes/interfaces/failure_policy_interface.py`:
   `@runtime_checkable class SurfaceFailurePolicyInterface(Protocol)` with the four methods;
   exported from the interfaces `__init__.py`. It is a pure policy; its registry entry is the
   production instance (`SurfaceFailurePolicyInterface → SurfaceFailurePolicy`) in `REGISTRY`
   and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/failure_policy.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/failure_policy_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_failure_policy.py`.

## Acceptance criteria
- [ ] The classification table below holds (one parametrized case per row):

  | exception | read | overwrite / native | guarded |
  |---|---|---|---|
  | `KeyError` / `FileNotFoundError` | not_found | not_found | not_found |
  | `RuntimeError` from `HTTPError(503)` | permanent | retry | outcome_unknown |
  | `RuntimeError` from `HTTPError(429)` | permanent | retry | outcome_unknown |
  | `RuntimeError` from `HTTPError(404)` | permanent | permanent | permanent |
  | `URLError(ConnectionRefusedError())` | permanent | retry | retry |
  | `socket.gaierror` | permanent | retry | retry |
  | `smtplib.SMTPConnectError(421, b"x")` | permanent | retry | retry |
  | `TimeoutError` | permanent | retry | outcome_unknown |
  | `smtplib.SMTPServerDisconnected` | permanent | retry | outcome_unknown |
  | `RedisError` raised from `ConnectionResetError` | permanent | retry | outcome_unknown |
  | `RedisError("redis error: WRONGTYPE")` (no cause) | permanent | permanent | permanent |
  | `RuntimeError("Kannel rejected the message: …")` | permanent | permanent | permanent |
  | `smtplib.SMTPRecipientsRefused({})` | permanent | permanent | permanent |
  | `smtplib.SMTPAuthenticationError(535, b"x")` | permanent | permanent | permanent |

- [ ] `retry_for` of a read has no waits; of an overwrite it has the configured waits; the returned retry retries a 503 and not a 404 (driven with an instant sleep).
- [ ] The chain walk stops after 10 links (a self-referencing chain terminates).
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_failure_policy.py` (no service; exceptions built in the test, `RuntimeError(...)` raised `from` an `urllib.error.HTTPError(url, code, msg, hdrs, None)`):
- `test_classification_table` (parametrized over the table)
- `test_retry_for_a_read_never_waits`
- `test_retry_for_an_overwrite_uses_the_configured_waits`
- `test_the_retry_retries_transient_and_stops_on_permanent`
- `test_the_chain_walk_is_bounded`
- `test_policy_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surface_lanes tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Teaching the adapters a transient error type (a follow-up the ADR names). Running operations
  (`surfaces-operation-handler`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and
  the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit
  locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-caller-scope` (package), `surfaces-catalogue`, `surfaces-config`, `surfaces-async-retry`.
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `sleep` is injected.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
