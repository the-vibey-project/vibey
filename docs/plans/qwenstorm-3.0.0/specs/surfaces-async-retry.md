## Title
feat(bootstrap): vibey_bootstrap.retry gains AsyncRetry, a bounded async retry with an explicit backoff list

## Why
Draft ADR-0047 §8 (`specs/ADR-surface-lanes.md`) retries an `overwrite` or `native` surface
operation on transport errors with waits `retry_backoff_seconds` (default 1, 5 and 30 s), and a
`guarded` one only on errors raised before anything was sent. The retry is the family's
(§12, "Family first"). But "the family's retry is sync only" ("What does not fit"):
`build_retry` wraps a sync function (`src/vibey_tools/bootstrap/vibey_bootstrap/retry/__init__.py:85-86`),
and every lane operation is async. Sub-doctrine 10.e: teach the family.

The ADR also makes `tenacity>=8.0` a declared root dependency. It is already in `uv.lock`
(tenacity 9.1.4, `uv.lock:5102`) through `google-genai` and the `bootstrap-all` extra
(`pyproject.toml:150`), so no new package enters the environment. ADR-0047 lane S08.

## Required behaviour
1. **`vibey_bootstrap/retry/async_retry.py`** (new), `class AsyncRetry`:
   - `__init__(self, *, operation: str, backoff_seconds: Sequence[float], retry_if: Callable[[BaseException], bool], sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> None`.
     An empty `operation` or a negative wait raises `ValueError`. The waits are stored as a
     tuple, exposed read-only as `backoff_seconds`.
   - `async def call(self, fn: Callable[[int], Awaitable[T]]) -> T`: calls `fn(attempt)` with
     the 1-based attempt number, at most `len(backoff_seconds) + 1` times. After a failed
     attempt `n`, it retries only when `retry_if(exc)` is true and a wait is left, waiting
     `backoff_seconds[n - 1]` through `sleep`. The last exception is re-raised unchanged
     (never tenacity's `RetryError`). An empty backoff means exactly one attempt.
   - Built on tenacity, imported inside `call` with the same `ImportError` message as
     `build_retry` (`retry/__init__.py:55-68`):
     `AsyncRetrying(stop=stop_after_attempt(len(waits) + 1), wait=wait_chain(*(wait_fixed(s) for s in waits)) if waits else wait_none(), retry=retry_if_exception(self._retry_if), sleep=self._sleep, before_sleep=before_sleep_log(logger, logging.WARNING), reraise=True)`,
     with `logger = logging.getLogger(f"vibey_bootstrap.retry.{operation}")` (the family's
     convention: every retry is logged at WARNING).
   - The module docstring states the 10.e reason: "The family's retry was sync only
     (`build_retry` wraps a sync function); the surface lanes' operations are async
     (ADR-0047 §8, §12)."
2. **`vibey_bootstrap/retry/interfaces/__init__.py`** and
   **`vibey_bootstrap/retry/interfaces/async_retry_interface.py`** (new):
   `@runtime_checkable class AsyncRetryInterface(Protocol)` with the `backoff_seconds`
   property and the generic `call`.
3. **Exports.** Append `from vibey_bootstrap.retry.async_retry import AsyncRetry` to
   `vibey_bootstrap/retry/__init__.py` and add `"AsyncRetry"` to its `__all__`.
4. **Packaging.** `src/vibey_tools/bootstrap/pyproject.toml` `[tool.setuptools] packages`
   (`:196-249`) gains `"vibey_bootstrap.retry.interfaces"` directly after
   `"vibey_bootstrap.retry"`; `test/test_packaging.py` fails without it.
5. **Root dependency.** In the root `pyproject.toml` `[project] dependencies` (`:19-49`), add
   after the `"platformdirs>=4.0",` line:
   ```toml
       # vibey_bootstrap.retry.AsyncRetry: the surface lanes' bounded retries (ADR-0047 §8).
       # Already locked through google-genai; declaring it adds nothing to the environment.
       "tenacity>=8.0",
   ```
   Then run `uv lock` and commit the regenerated `uv.lock`. `uv lock --check` must pass, and
   `git diff uv.lock` must show only the `vibey` package's dependency metadata, never a new
   package or a version change.

## Where to change
- New `src/vibey_tools/bootstrap/vibey_bootstrap/retry/async_retry.py`,
  `src/vibey_tools/bootstrap/vibey_bootstrap/retry/interfaces/__init__.py`,
  `src/vibey_tools/bootstrap/vibey_bootstrap/retry/interfaces/async_retry_interface.py`.
- `src/vibey_tools/bootstrap/vibey_bootstrap/retry/__init__.py` (the export only).
- `src/vibey_tools/bootstrap/pyproject.toml` (one `packages` line), root `pyproject.toml`
  (three lines), `uv.lock` (regenerated).
- New `src/vibey_tools/bootstrap/test/retry/test_async_retry.py`.

## Acceptance criteria
- [ ] With backoff `(1, 5, 30)` and a function failing three times then succeeding, `call` returns the value after four attempts, and the injected sleep recorded `[1, 5, 30]`.
- [ ] A function that always fails is tried four times and its own exception is re-raised.
- [ ] When `retry_if` is false the first failure is re-raised after one attempt and nothing slept.
- [ ] An empty backoff makes one attempt.
- [ ] `isinstance(AsyncRetry(...), AsyncRetryInterface)`.
- [ ] `uv lock --check` passes; `git diff uv.lock` adds no package; `uv run pip-audit` reports nothing new.
- [ ] The tenant keeps its 100% line floor; `test/test_packaging.py` passes.

## Tests to write first (TDD)
`test/retry/test_async_retry.py` (no service; an `InstantSleep` class in the module records the waits and returns at once):
- `test_waits_follow_the_backoff_list_then_succeed`
- `test_exhaustion_reraises_the_last_exception`
- `test_a_non_retryable_error_is_raised_at_once`
- `test_an_empty_backoff_tries_once`
- `test_the_attempt_number_is_passed_to_the_function`
- `test_negative_waits_and_empty_operation_are_refused`
- `test_async_retry_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv lock --check
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider --no-cov test/retry test/test_packaging.py)
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/ -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)
    uv run pip-audit
    uv run lint-imports

## Out of scope
- `build_retry` and its presets (unchanged). Anything under `src/vibey/` (the surface lanes use
  `AsyncRetry` from `surfaces-failure-policy` on).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** none.
- **Shares a file with:** the root `pyproject.toml` (R03 → T07 → T28 also edit it; keep their lines) and `uv.lock`.
- **Must keep passing unchanged:** `test/retry/*` and the whole vibey-bootstrap suite; the root suite; all protected root tests.
- **Standing constraints (every vibey-bootstrap surfaces lane):**
  - Read `STORM/EDITING-RULES.md` first.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from a sibling.
  - No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`: `sleep` is injected.
  - The default run needs no service.
  - If `src/vibey_tools/bootstrap/test/fakes/registry.py` exists, register
    `AsyncRetryInterface → AsyncRetry(operation="fake", backoff_seconds=(), retry_if=...)`
    with an instant sleep, as a `functools.partial`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
