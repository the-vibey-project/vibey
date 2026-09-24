## Title
test(contracts): one suite per repository port binds the in-memory fake always and PostgreSQL on opt-in

## Why
A fake is only as honest as the evidence that it behaves like the real adapter. ADR-0044 §16
says: "A port with two implementations is only a port if one suite binds both". Today the
evidence is split:
- `tests/contracts/` has one contract, `test_rotation_cursor_contract.py`, and it runs on
  PostgreSQL only (`tests/contracts/conftest.py:19-21` marks every item `integration`);
- the fakes' own tests (`tests/fakes/test_fake_*.py`) mirror the PostgreSQL tests by name,
  but a copy can drift.

This lane makes one suite the definition of each repository port's behaviour. The suite runs
against the fake in the **default tier**, always, and against PostgreSQL in the
**integration tier**. A behaviour change must then pass both, or the tier that disagrees
fails.

## Required behaviour
1. **`tests/contracts/conftest.py`**:
   - a helper `backends()` returns
     `["memory", pytest.param("postgres", marks=pytest.mark.integration)]`;
   - each contract module parametrizes a module-level fixture over it;
   - the `postgres` branch resolves `migrated_pool` lazily with
     `request.getfixturevalue("migrated_pool")`, so the default tier never touches the
     database;
   - the directory marker added by `pytest_collection_modifyitems` (`:19-21`) now marks only
     items whose `callspec` has no `"memory"` value. Keep the directory scoping that
     `fakes-harness-decouple` added.
2. **Contract modules.** Each one is one fixture yielding the port's implementation per
   backend, plus tests that use only the port's methods:
   - `test_human_gate_contract.py` (`HumanGateRepository`, with `FakeJobRepository` or
     `PostgresJobRepository` over the same store or pool): raise, answer, get,
     `open_for_project` ordering, `latest_for_job`, an answer re-readying a parked job, and
     `LookupError` on an unknown gate;
   - `test_project_contract.py` (`ProjectRepository`): create defaults, the unique
     `repo_path`, `get_latest`, the compare-and-set `transition`, the `PHASE_TRANSITIONED`
     event appended with the move, and a replay raising while appending nothing;
   - `test_ledger_contract.py` (`LedgerRepositoryInterface` and `LedgerSearch`): per-project
     `seq`, redaction before the digest, inclusive `range`, `latest_seq` of an empty project,
     and every search criterion together with `limit`/`truncated`. Port these from
     `tests/fakes/test_fake_ledger_search.py`, and delete that file's duplicated cases
     afterwards;
   - `test_engine_health_contract.py` (`EngineHealthRepository`): upsert and get by engine,
     and list sorted;
   - `test_rotation_cursor_contract.py`: parametrize the existing module. Its assertions stay;
   - `test_handoff_contract.py` (`HandoffStore` plus `get` and `list_for_pair`): round trip,
     and refusing a duplicate id.
3. **When the backends disagree, the lane stops.** If a contract passes on one backend and
   fails on the other, do not weaken the test. Report which implementation is wrong, and fix
   the fake if it is the fake (`tests/fakes/`). A difference in PostgreSQL's behaviour is a
   production bug, and out of scope here.
4. **The fakes' mirrored tests** (`tests/fakes/test_fake_queue.py` and the rest) keep only
   what the contracts do not cover, such as fault injection and inspection helpers. Remove
   the cases a contract now proves.

## Where to change
- `tests/contracts/conftest.py`, `tests/contracts/test_rotation_cursor_contract.py`, the five new contract modules.
- `tests/fakes/test_fake_*.py` (removing duplicated cases only).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts` runs every contract on `memory` with PostgreSQL stopped, and passes.
- [ ] `uv run pytest -q -p no:cacheprovider -m integration tests/contracts` passes on `postgres`.
- [ ] Every repository port in `tests/fakes/registry.py`'s `REGISTRY` that has a PostgreSQL
      implementation has a contract module. A meta test,
      `tests/contracts/test_every_repository_port_has_a_contract.py`, holds that list
      explicitly, and each entry names its module.

## Tests to write first (TDD)
- Write each contract against `memory` first. Then enable `postgres` and run it with the database.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts tests/fakes
    uv run pytest -q -p no:cacheprovider -m integration tests/contracts
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=

## Out of scope
- `JobRepository`'s contract. R18 writes `tests/contracts/test_job_queue_contract.py`, and
  `fakes-contracts-queue` adds the `memory` backend to it.
- Production code. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-queue-gates`, `fakes-engines`, `fakes-ledger-publication` (which brings ledger and projects).
- **Files touched:** see *Where to change*.
- **Shares a file with:** `tests/contracts/conftest.py` (R18 reuses its fixtures, and `fakes-contracts-queue` follows).
- **Must keep passing unchanged:** the protected tests.
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
See STORM/SPEC-TEMPLATE.md.
