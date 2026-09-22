## Title
test(fakes): ledger search, shard store and site writer get in-memory twins that answer exactly as the real ones

## Why
Sub-doctrine 7.a has a port for searching the ledger, `LedgerSearch`
(`application/interfaces/ledger.py:131-146`), and two for publishing it, `LedgerShardStore`
and `LedgerSiteWriter` (`:148-170`). None of the three has a fake.

`LedgerSearch`'s only implementation compiles SQL (`db/ledger_search_repository.py:59-148`),
so every search test needs PostgreSQL. That is `tests/infrastructure/db/test_ledger_search_repository.py`
(23 tests) and the whole of `tests/cli/test_ledger_search_cli.py` (19, `pytestmark = integration`).

The search semantics are fully stated in code, so they can be reproduced exactly:
- AND of optional criteria (`domain/ledger_query.py:169-217`);
- `since` inclusive, `until` exclusive;
- `kind = ANY(...)`;
- the actor scopes (`_actor`, `:113-121`);
- `payload::text ILIKE '%needle%'` with `%`, `_` and `\` literal (`contains_pattern`, `:100-110`);
- newest `limit`, returned oldest first, with `truncated` computed from one extra row (`:140-148`).

## Required behaviour
1. **`tests/fakes/ledger_publication.py` — `class InMemoryLedgerSearch`** implements `LedgerSearch`:
   - `__init__(self, ledger: LedgerReader)`. Pass it an `InMemoryLedger` from `tests/fakes/ledger.py`.
   - `search(project_id, query)` filters `await ledger.all_for_project(project_id)` with every
     criterion that is not `None`:
     - `event_id ==`, `digest ==`;
     - actor: `SELF` means `engine_id is None`, `ENGINE` means
       `engine_id.value == actor.name`, and any other scope means
       `provenance.value == actor.name`;
     - `produced_at >= since` and `produced_at < until`;
     - `kind.value in {k.value for k in kinds}`;
     - `needle.lower() in jsonb_text(payload).lower()`.
     It then takes the newest `limit` by `seq`, returns them oldest first, and sets
     `truncated = matches > limit`. The result type is the real `LedgerSearchResult`
     (`ledger_search_repository.py:52-57`).
   - `jsonb_text(value)` renders a payload as PostgreSQL's `jsonb::text` does:
     - object keys are ordered by `(len(key.encode()), key.encode())`;
     - the separators are `", "` and `": "`;
     - strings are escaped as JSON escapes them;
     - `true`, `false` and `null` are lower case.
     It is a `@staticmethod` on the class.
2. **`class InMemoryShardStore`** implements `LedgerShardStore`:
   - `files: dict[Path, LedgerShardInterface]`;
   - `write` replaces an entry;
   - `read` of a missing path raises `InvalidLedgerShard` with the same message the real
     `JsonlShardStore.read` gives for a missing file (read `infrastructure/ledger/static_export.py:199-255`
     and copy the message).
3. **`class InMemorySiteWriter`** implements `LedgerSiteWriter`. `sites: dict[Path, LedgerSitePlanInterface]`
   records the last plan written to each directory. It raises what `StaticSiteWriter.write`
   raises for an invalid plan, if anything (read `:277-`).
4. **Registry.** `LedgerSearch → InMemoryLedgerSearch(InMemoryLedger())`,
   `LedgerShardStore → InMemoryShardStore()`, `LedgerSiteWriter → InMemorySiteWriter()`.
   Delete the three `PENDING` lines.
5. **Prove the search twin.** `tests/fakes/test_fake_ledger_search.py` ports the behavioural
   cases of `tests/infrastructure/db/test_ledger_search_repository.py`: the same drafts, the
   same queries, the same expected events and `truncated`. It runs them against
   `InMemoryLedgerSearch` in the default tier. The PostgreSQL file is not edited;
   `fakes-contracts-repositories` later binds both implementations to one suite.

## Where to change
- New `tests/fakes/ledger_publication.py`, `tests/fakes/test_fake_ledger_search.py`,
  `tests/fakes/test_fake_ledger_publication.py`.
- `tests/fakes/registry.py`.

## Acceptance criteria
- [ ] Every case ported from `test_ledger_search_repository.py` passes against the fake with the
      PostgreSQL test's expected values. If a case cannot match, stop and report the
      difference, and do not weaken it.
- [ ] `jsonb_text({"bb": 1, "a": [True, None]}) == '{"a": [true, null], "bb": 1}'`.
- [ ] The registry has no `PENDING` entry naming `fakes-ledger-publication`.

## Tests to write first (TDD)
- `tests/fakes/test_fake_ledger_search.py`: one test per case in the PostgreSQL file, with the same names
  prefixed `test_fake_`. Add these:
  - `test_fake_text_match_is_case_insensitive_and_literal` (`%` and `_` in the needle)
  - `test_fake_jsonb_text_orders_keys_like_postgres`
  - `test_fake_limit_keeps_the_newest_and_reports_truncation`
- `tests/fakes/test_fake_ledger_publication.py`:
  - `test_shard_store_round_trips_and_refuses_a_missing_path`
  - `test_site_writer_records_the_last_plan`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/cli/test_ledger_publication_cli.py

## Out of scope
- Moving `tests/cli/test_ledger_search_cli.py` off PostgreSQL (`fakes-cli-ledger-deploy`, after the bootstrap seam).
- `AppResources` (`fakes-bootstrap-seam` adds `ledger_search`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-ledger`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_ledger_search_repository.py`
  (integration), `tests/cli/test_ledger_publication_cli.py` and the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
