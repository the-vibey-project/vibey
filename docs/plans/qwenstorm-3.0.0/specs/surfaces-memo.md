## Title
feat(bootstrap): vibey_bootstrap.memo, a bounded least-recently-used memo with per-entry expiry

## Why
Draft ADR-0047 §10 (`specs/ADR-surface-lanes.md`, "How the design keeps the rule without
making the cache pointless", point 4) gives the cache lane a read-through memo: bounded
(10 000 entries by default), with an expiry that never outlives Valkey's own TTL. §12 says it
comes from the family, and "What does not fit" records the gap: "The family has no general
bounded memo with expiry. `identity.TokenCache` (`identity/__init__.py:245`) is token-specific
module state." Sub-doctrine 10.e: teach the family. ADR-0047 lane S09. Stdlib only.

It also reports hits, misses and evictions, so the cache lane's measurements (sub-doctrine
8.g, "always measured") have something to read.

## Required behaviour
1. **`vibey_bootstrap/memo/bounded_ttl.py`** (new):
   - `@dataclass(frozen=True, slots=True) class MemoStats`: `hits: int`, `misses: int`,
     `evictions: int`, `size: int`.
   - `class BoundedTtlMemo(Generic[K, V])`:
     `__init__(self, max_entries: int, *, clock: Callable[[], float] = time.monotonic) -> None`.
     A negative `max_entries` raises `ValueError("max_entries must be >= 0")`.
   - `get(self, key: K) -> V | None`: a stored, unexpired entry is a hit (it becomes the most
     recently used); anything else is a miss. An entry whose expiry is `<= clock()` is removed
     and counted a miss.
   - `put(self, key: K, value: V, *, ttl_seconds: float | None = None) -> None`:
     - `max_entries == 0` stores nothing;
     - `ttl_seconds is not None and ttl_seconds <= 0` stores nothing and removes any existing
       entry for `key`;
     - otherwise the entry (expiry `clock() + ttl_seconds`, or none) becomes the most recently
       used, and while `len > max_entries` the least recently used entry is evicted
       (`evictions += 1`).
   - `delete(self, key: K) -> None` (absent is not an error), `clear(self) -> None`,
     `__len__`, and `stats(self) -> MemoStats`.
   - Built on `collections.OrderedDict` (`move_to_end`, `popitem(last=False)`). Not thread-safe;
     the docstring says one event loop owns it.
   - The module docstring states the 10.e reason quoted above.
2. **`vibey_bootstrap/memo/interfaces/bounded_ttl_interface.py`** (new):
   `@runtime_checkable class BoundedTtlMemoInterface(Protocol[K, V])` with the five methods
   and `__len__`; `vibey_bootstrap/memo/interfaces/__init__.py` exports it.
3. **`vibey_bootstrap/memo/__init__.py`** exports `BoundedTtlMemo`, `MemoStats` and the
   interface.
4. **Packaging.** `src/vibey_tools/bootstrap/pyproject.toml` `[tool.setuptools] packages`
   gains `"vibey_bootstrap.memo"` and `"vibey_bootstrap.memo.interfaces"`, directly after
   `"vibey_bootstrap.metrics"`.

## Where to change
- New package `src/vibey_tools/bootstrap/vibey_bootstrap/memo/` (`__init__.py`,
  `bounded_ttl.py`, `interfaces/__init__.py`, `interfaces/bounded_ttl_interface.py`).
- `src/vibey_tools/bootstrap/pyproject.toml` (two `packages` lines).
- New `src/vibey_tools/bootstrap/test/memo/__init__.py` (provenance line only) and
  `src/vibey_tools/bootstrap/test/memo/test_bounded_ttl.py`.

## Acceptance criteria
- [ ] With `max_entries=2`, putting `a`, `b`, reading `a`, then putting `c` evicts `b`; `stats()` shows one eviction.
- [ ] An entry with `ttl_seconds=1.0` is a hit at `t+0.5` and a miss (and gone) at `t+1.0`, by the injected clock.
- [ ] `max_entries=0` stores nothing; a non-positive TTL removes the key.
- [ ] Hits and misses are counted exactly.
- [ ] `isinstance(BoundedTtlMemo(1), BoundedTtlMemoInterface)`.
- [ ] `test/test_packaging.py` passes; the tenant keeps its 100% line floor.

## Tests to write first (TDD)
`test/memo/test_bounded_ttl.py` (no service; a `FakeMonotonic` class in the module with `advance(seconds)`):
- `test_least_recently_used_is_evicted_first`
- `test_expiry_follows_the_injected_clock`
- `test_zero_capacity_stores_nothing`
- `test_non_positive_ttl_removes_the_key`
- `test_stats_count_hits_misses_and_evictions`
- `test_delete_and_clear`
- `test_negative_capacity_is_refused`
- `test_memo_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider --no-cov test/memo test/test_packaging.py)
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/ -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)

## Out of scope
- `identity.TokenCache` (unchanged). The cache lane that uses the memo (`surfaces-cache-handler`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** none.
- **Shares a file with:** the tenant `pyproject.toml` `packages` list (R04 and `surfaces-async-retry` add lines; keep theirs).
- **Must keep passing unchanged:** the whole vibey-bootstrap suite; all protected root tests.
- **Standing constraints (every vibey-bootstrap surfaces lane):**
  - Read `STORM/EDITING-RULES.md` first.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from a sibling.
  - No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`: the clock is injected.
  - If `src/vibey_tools/bootstrap/test/fakes/registry.py` exists, register
    `BoundedTtlMemoInterface → functools.partial(BoundedTtlMemo, 16)` (the production class is
    already in memory).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
