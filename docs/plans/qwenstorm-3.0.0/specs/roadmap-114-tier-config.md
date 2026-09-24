## Title
fix(domain)!: TierConfig keeps at least one raw record and splits the archive tier from the opt-in archival node

## Why
Issue #114 (rewrite: `issue-audit/updates/114.md`, "Current state" → Tier model, and "Proposed
child issues" 1). The issue's standard mode is "the latest **N full, uncompressed ledger
records**, N > 0", and the archival *node* is opt-in ("A deployment may opt in to running a
**full archival node**"). The code says otherwise:
`src/vibey/domain/ledger_tier.py:7-17` accepts `standard_n == 0` (`:16` refuses only negatives)
and has one flag, `archival_enabled: bool = True` (`:13`), which is either the archive tier
(then the name is wrong) or the node (then the default contradicts the issue). The one caller
compensates: `TierManager.reconcile_tiers` computes `keep_raw = max(config.standard_n, 0)` and
compresses **every** raw record when it is 0 (`src/vibey/infrastructure/ledger/tier_manager.py:56-57`),
so the newest event can leave the hot tier. Keeping the newest record raw also keeps
`latest_seq` answerable from the raw table once rotation exists (the rotation ADR relies on it).
Sub-doctrine 12.c (`src/vibey_tools/gh/docs/doctrines.md:455`: "A default is configurability
with an opinion") and 10 (`doctrines.md:366-383`, no guarantees: storage is never assumed)
bind the defaults; 7.c (`doctrines.md:82-91`) is why the tiers exist at all.

Every caller, found with `grep -rn "TierConfig\|archival_enabled\|standard_n" src tests docs`
at this cutoff: `ledger_tier.py`, `domain/interfaces/ledger_tier_interface.py:20-31`,
`infrastructure/ledger/tier_manager.py:49-57`, `tests/domain/test_ledger_tier.py`,
`tests/infrastructure/ledger/test_tier_manager.py:26,57,65,96`. Nothing in `docs/`. Few enough
for one lane.

## Required behaviour
1. `src/vibey/domain/ledger_tier.py` — `TierConfig` becomes exactly (keep line 1, the
   provenance header, and the module docstring; replace the class):
   ```python
   @dataclass(frozen=True, slots=True)
   class TierConfig:
       """How a project's ledger ages through the storage tiers (vibey#114).

       The newest ``standard_n`` records stay raw -- at least one, so the working set is
       never decompressed and the newest seq is always read from the raw table. The next
       ``mid_tier_n`` are kept compressed. ``archive_tier`` keeps everything since
       inception as archive segments (on unless turned off). ``archival_node`` makes this
       deployment an archival node, which holds the complete archive and serves history
       other nodes compacted away: opt-in, off unless turned on, and only with the archive
       tier.
       """

       standard_n: int
       mid_tier_n: int
       archive_tier: bool = True
       archival_node: bool = False

       def __post_init__(self) -> None:
           if self.standard_n < 0 or self.mid_tier_n < 0:
               raise ValueError("ledger tier retention counts cannot be negative")
           if self.standard_n < 1:
               raise ValueError(
                   "the standard tier keeps at least one raw record: standard_n must be >= 1"
               )
           if self.archival_node and not self.archive_tier:
               raise ValueError(
                   "an archival node holds the archive tier: archival_node requires archive_tier"
               )
   ```
   The negative check stays first, so `(-1, 0)` and `(0, -1)` keep today's message.
2. `src/vibey/domain/interfaces/ledger_tier_interface.py` — in `TierConfigInterface`
   (`:20-31`), replace the `archival_enabled` property with two read-only properties, in this
   order after `mid_tier_n`:
   ```python
       @property
       def archive_tier(self) -> bool: ...

       @property
       def archival_node(self) -> bool: ...
   ```
   Nothing else in the file changes. `vibey.domain.interfaces.__init__` needs no change.
3. `src/vibey/infrastructure/ledger/tier_manager.py`:
   - In the `reconcile_tiers` docstring (`:49-54`), replace
     ``` ``archival_enabled`` remain``` with ``` ``archive_tier`` and ``archival_node`` remain```
     (the sentence otherwise unchanged).
   - Replace lines `:56-57`
     ```python
             keep_raw = max(config.standard_n, 0)
             candidates = raw[:-keep_raw] if keep_raw else raw
     ```
     with
     ```python
             # vibey#114: the newest record always stays raw (N > 0), even for a config
             # object that says less, so a reconcile never empties the hot tier.
             keep_raw = max(config.standard_n, 1)
             candidates = raw[:-keep_raw]
     ```
     (One branch fewer; `raw[:-1]` of an empty or one-element list is empty.)
4. No other production file changes. `grep -rn "archival_enabled" src tests` prints nothing
   afterwards.

## Where to change
- `src/vibey/domain/ledger_tier.py` (replace the class; `write_file` is allowed: the file is
  17 lines — keep line 1 byte-for-byte and the docstring on line 2).
- `src/vibey/domain/interfaces/ledger_tier_interface.py` (`edit_file`, one property block).
- `src/vibey/infrastructure/ledger/tier_manager.py` (`edit_file`, the two edits above).
- `tests/domain/test_ledger_tier.py` (append the new tests; do not change the two existing ones).
- `tests/infrastructure/ledger/test_tier_manager.py` — two edits with `edit_file`, nothing else:
  1. Line 65:
     `    assert manager.reconcile_tiers(project_id, TierConfig(standard_n=0, mid_tier_n=2)) == (0, 3)`
     becomes
     `    assert manager.reconcile_tiers(project_id, TierConfig(standard_n=1, mid_tier_n=2)) == (1, 2)`
     (the re-added raw seq 1 is already compressed, so it is verified and dropped from raw; seq
     3 stays raw; seqs 1 and 2 are compressed).
  2. In `test_reconciliation_keeps_raw_event_when_verification_fails` (`:70-98`), replace
     ```python
         store = InMemoryLedgerTierStore()
         store.put_raw(event)
         manager = TierManager(store)
     ```
     with
     ```python
         newer = replace(event, event_id=uuid4(), seq=2)
         store = InMemoryLedgerTierStore()
         store.put_raw(event)
         store.put_raw(newer)
         manager = TierManager(store)
     ```
     then `TierConfig(standard_n=0, mid_tier_n=0)` (`:96`) becomes
     `TierConfig(standard_n=1, mid_tier_n=0)`, and
     `    assert store.raw_events(project_id) == (event,)` (`:98`) becomes
     `    assert store.raw_events(project_id) == (event, newer)`.
     Add `from dataclasses import replace` to the imports (after `import json`, isort order).
     These two edits add no `patch` call: the file's count in any patching baseline is unchanged.

## Acceptance criteria
- [ ] `TierConfig(standard_n=0, mid_tier_n=0)` raises `ValueError` naming `standard_n must be >= 1`.
- [ ] `TierConfig(standard_n=1, mid_tier_n=0)` has `archive_tier is True` and `archival_node is False`.
- [ ] `TierConfig(1, 0, archive_tier=False, archival_node=True)` raises `ValueError` naming `archival_node requires archive_tier`.
- [ ] `TierConfig(1, 0, archive_tier=False)` is valid.
- [ ] `isinstance(TierConfig(standard_n=100, mid_tier_n=1_000), TierConfigInterface)` still holds.
- [ ] `grep -rn "archival_enabled" src tests` prints nothing.
- [ ] The whole `tests/infrastructure/ledger/test_tier_manager.py` and `tests/domain/test_domain_purity.py` pass.
- [ ] 100% branch coverage of `src/vibey/domain/` and `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/domain/test_ledger_tier.py` (add `import dataclasses` at the top of the file):
- `test_the_standard_tier_keeps_at_least_one_raw_record` — `pytest.raises(ValueError, match="standard_n must be >= 1")` for `TierConfig(standard_n=0, mid_tier_n=0)`.
- `test_the_archive_tier_is_on_and_the_archival_node_is_off_by_default` — `config = TierConfig(standard_n=1, mid_tier_n=0)`; `config.archive_tier is True`; `config.archival_node is False`.
- `test_an_archival_node_requires_the_archive_tier` — `pytest.raises(ValueError, match="archival_node requires archive_tier")` for `TierConfig(standard_n=1, mid_tier_n=0, archive_tier=False, archival_node=True)`.
- `test_the_archive_tier_can_be_turned_off_without_a_node` — `TierConfig(standard_n=1, mid_tier_n=0, archive_tier=False).archival_node is False`.
- `test_the_old_single_flag_is_gone` — `"archival_enabled" not in {field.name for field in dataclasses.fields(TierConfig)}` and `not hasattr(TierConfig(standard_n=1, mid_tier_n=0), "archival_enabled")`.

The two edited tier-manager tests above are the caller's regression tests.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Focused (no service is used by these tests; today the root conftest still opens the database at startup):
    uv run pytest -q -p no:cacheprovider tests/domain/test_ledger_tier.py tests/infrastructure/ledger/test_tier_manager.py tests/domain/test_domain_purity.py
    ! grep -rn "archival_enabled" src tests
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The `[ledger]` section of `vibey.toml` and its loader (the defaults for N and M are #114 open
  question 3, unanswered); wiring `TierManager` anywhere; the tier store and rotation lanes
  (`roadmap-114-postgres-tier-store-p1`…`-p4`, `roadmap-114-design-rotation`).
- Converting the existing `patch.object` uses in `test_tier_manager.py` (a fakes lane owns that).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
  Do not push, no PRs, no remote changes; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
