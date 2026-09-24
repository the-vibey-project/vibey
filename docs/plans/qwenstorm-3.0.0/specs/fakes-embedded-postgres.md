## Title
test(harness): the opt-in integration tier can start a throwaway PostgreSQL from a wheel when no server is configured

## Status
**Operator decision required before filing.** This lane adds a third-party dependency with
native binaries (`pgserver`). It is offered, not assumed. See the recommendation in
`specs/ADR-test-harness-fakes-amendment.md` section A8.

## Why
After `fakes-harness-decouple`, the default tier needs no PostgreSQL. The `integration` tier
still needs one:
- `tests/infrastructure/db` on its `postgres` parameter;
- the contract suites' `postgres` backend;
- transcript recording (`fakes-db-sql-transcripts`);
- the real-service CLI cases.

On a laptop or in a storm lane without a server, `-m integration` fails at setup.

`pgserver` (PyPI) ships PostgreSQL's server binaries inside a wheel. It `initdb`s a data
directory and starts a private server listening on a Unix socket in that directory, with no
system install, no Docker and no network. It is real PostgreSQL, which fits ADR-0002.
It is not in memory: it is a server process with on-disk state. So it cannot serve the default
tier under the operator's standard. It can make the opt-in tier runnable anywhere.

## Required behaviour
1. **An optional extra**, never a runtime or default dev dependency: `[project.optional-dependencies] pg-embedded = ["pgserver>=0.1.4"]`.
   Run `uv lock`. `pip-audit` must pass.
2. **`tests/conftest.py`'s `WorkerDatabase.setup`** (`fakes-harness-decouple`) resolves the
   base DSN in this order:
   1. `_VIBEY_TEST_BASE_DSN`;
   2. `VIBEY_TEST_DATABASE_URL`;
   3. when `VIBEY_TEST_EMBEDDED_PG=1` and `pgserver` imports:
      `pgserver.get_server(<repo>/.pytest_pg, cleanup_mode="stop").get_uri()`, with the data
      directory under the checkout and `.pytest_pg/` added to `.gitignore`;
   4. otherwise the current default.
   Print one line naming which one it used (10.f). The embedded server's major version is
   printed with it, because it may differ from ADR-0002's 17.
3. **Isolation.** The isolation guard (`fakes-isolation-guard`) is disarmed for `integration`
   items already, so the embedded server's `initdb` and `pg_ctl` are allowed there. The guard
   still forbids them in the default tier.
4. **CI is unchanged.** The PostgreSQL 14–18 matrix keeps real service containers. The wheel
   ships one major, so it cannot stand in for the matrix.

## Where to change
- `pyproject.toml` (the extra), `uv.lock`, `.gitignore`, `tests/conftest.py` (`WorkerDatabase.setup`).
- `tests/meta/test_integration_tier.py` (appended).

## Acceptance criteria
- [ ] `uv sync --extra dev --extra pg-embedded && VIBEY_TEST_EMBEDDED_PG=1 uv run pytest -q -p no:cacheprovider -m integration tests/contracts` passes on a machine with no PostgreSQL installed.
- [ ] Without the extra, `VIBEY_TEST_EMBEDDED_PG=1` gives a clear error naming the extra, not an `ImportError` traceback.
- [ ] `uv run pip-audit` and `uv lock --check` pass.

## Tests to write first (TDD)
`tests/meta/test_integration_tier.py` (appended):
- `test_base_dsn_resolution_order` (pure, over an injected environ)
- `test_embedded_without_the_extra_names_the_extra`

## Checks the lane must run (all must pass)
    uv lock --check
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta
    uv run pip-audit

## Out of scope
- Using it in the default tier, or in CI. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-harness-decouple`, `fakes-isolation-guard`.
- **Files touched:** see *Where to change*.
- **Shares a file with:** `pyproject.toml` and `uv.lock` (R03, T07, T28).
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
  - 10.e: no family package provides an embedded PostgreSQL. Record that at the dependency's
    comment in `pyproject.toml`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
