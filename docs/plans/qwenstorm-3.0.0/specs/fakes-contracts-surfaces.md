## Title
test(contracts): each sovereign surface port has one contract that binds its in-memory implementation always and its real adapter on opt-in

## Why
ADR-0042 gives twelve surface ports a production in-memory implementation and a real
adapter: blob, bus, cache, config store, docs, email, files, messaging, secrets, SIEM, SMS and
tracker. `build_app` falls back to the in-memory one whenever the surface is unconfigured
(`src/vibey/bootstrap.py:760-900`). So the in-memory implementations are not only test fakes.
They are what an unconfigured vibey actually runs.

Nothing checks that an in-memory implementation behaves like its adapter. The adapter tests
(`fakes-http-transport`, `fakes-sockets`, `fakes-sovereign-http`, `fakes-sovereign-smtp`)
check the wire requests. The in-memory tests (`tests/infrastructure/test_sovereign_surfaces.py:102-200`)
check `isinstance` and a round trip. They are never checked against each other.

`InMemoryCache` reads `time.monotonic()` directly (`infrastructure/cache/in_memory.py`), so
TTL cannot be tested without sleeping.

## Required behaviour
1. **`InMemoryCache.__init__(self, *, clock: Callable[[], float] = time.monotonic)`**. Every
   other in-memory surface that reads time gets the same keyword. This is a production change
   limited to that keyword.
2. **`tests/contracts/test_surface_contracts.py`** has one fixture per port, parametrized over:
   - `"memory"`: the production `InMemory*`, unmarked;
   - `pytest.param("real", marks=pytest.mark.integration)`: the real adapter, built exactly as
     `build_app` builds it. Its configuration comes from environment variables named
     `VIBEY_TEST_<SURFACE>_<KEY>`, one per key of that surface's `[<surface>]` table in
     `domain/config.py`: for example `VIBEY_TEST_TRACKER_URL` and `VIBEY_TEST_TRACKER_TOKEN`.
     The test is skipped with a message naming the variables when the URL (or host) variable
     is unset.
   The `VIBEY_TEST_*` prefix is already in the test harness's `pass_env` (ADR-0045 §14), so
   these runs route through the harness unchanged.
3. **What each contract asserts**, using only the port's methods:
   - blob: put/get round trip, a missing key raising `FileNotFoundError`, overwrite;
   - bus: publish/consume FIFO, and consuming an empty or undeclared queue returning `None`;
   - cache: set/get/delete, overwrite, and TTL expiry (on `memory`, by advancing the injected
     clock; on `real`, with a 1-second TTL and a bounded wait);
   - the other ports: the round trip or visible effect each port documents in its docstring,
     read from `application/interfaces/<port>.py`.
   Where a port's docstring leaves a behaviour unspecified, the contract does not test it.
   List such gaps in the commit body.
4. **Remove the duplicated in-memory round-trip tests** from
   `tests/infrastructure/test_sovereign_surfaces.py` (`:102-200`) once the contracts cover them.

## Where to change
- `src/vibey/infrastructure/cache/in_memory.py` (and any other in-memory surface that reads time).
- New `tests/contracts/test_surface_contracts.py`; `tests/contracts/conftest.py` (the env-to-config helper);
  `tests/infrastructure/test_sovereign_surfaces.py` (deletions).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts/test_surface_contracts.py` passes for all twelve ports on `memory`.
- [ ] With `VIBEY_TEST_CACHE_URL=redis://…` set and `-m integration`, the cache contract runs against a real Redis.
      This is manual evidence; say in the commit body whether it was run.
- [ ] The cache TTL contract takes under 50 ms on `memory`.

## Tests to write first (TDD)
- `test_cache_ttl_expires_by_the_injected_clock`, then one contract per port.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts tests/infrastructure/test_sovereign_surfaces.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Any change to a port's methods (`sovereign-surfaces-ports`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-sovereign-http`, `fakes-sovereign-smtp`, `fakes-sockets`.
- **Files touched:** see *Where to change*.
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
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
