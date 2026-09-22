## Title
test(runners-common): the shared runner ports ship in-memory fakes, and vibey-runners-common gets the suite it never had

## Why
`vibey-runners-common` (`src/vibey_runners/common`) declares the ports its runners share:
- `Clock` and `Sleeper` (`application/interfaces/system.py:11-21`);
- `StreamUi` (`ui.py:11-20`);
- `RunControl` and `ControlInbox` (`control.py:23-33`);
- `Logger` and `StateBus` (`observability.py:27-41`);
- `RunStateStore` and `SessionLock` (`storage.py:22-38`);
- `ApiGateway` (`api.py:10-19`).

It has a use case, `application/usecases/completion.py`, and **no tests at all**:
- its `pyproject.toml` names `testpaths = ["tests"]`, and that directory does not exist;
- the CI rows carry only `static` (`.github/workflows/ci.yml:317-335`: "vibey-runners-common ships no suite").

Each runner fakes these same ports again in its own `tests/application/fakes.py`.

Dogfooding (10.e) means the family ships the fake once. `vibey_bootstrap.amqp.memory.InMemoryAmqpClient`
(R04) is the precedent: an in-memory double shipped in the package, for every consumer. The
runners install `../common` in CI (`ci.yml:306-311`), so a fake shipped in
`vibey_runners.common` is importable from every runner's tests. A fake kept in common's
`tests/` would not be.

## Required behaviour
1. **`src/vibey_runners/common/src/vibey_runners/common/testing/fakes.py`** (new package
   `testing`, with `__init__.py`). Each class below implements its port with real in-memory
   behaviour, and each has an interface in `testing/interfaces/fakes_interface.py`
   (ADR-0016), subclassing the port:
   - `FakeClock` (`Clock`): `now()`, and `advance(delta)`, which refuses a negative delta and
     a naive start;
   - `FakeSleeper` (`Sleeper`): `sleep_until(instant)` advances a linked `FakeClock` to
     `instant` (never backwards) and records it;
   - `RecordingStreamUi` (`StreamUi`) records every callback as a `(name, kwargs)` tuple.
     `close()` sets `closed`, and later calls raise `RuntimeError("stream ui closed")`;
   - `InMemoryControlInbox` and `InMemoryRunControl` share a deque. `enqueue(command)`
     returns a `PurePosixPath` naming the command's slot. `poll()` drains in FIFO order;
   - `RecordingLogger` (`Logger`): `bind` returns a child that shares the lines and merges
     context;
   - `InMemoryStateBus` (`StateBus`) records `(event_type, payload)`;
   - `InMemoryRunStateStore` (`RunStateStore`): `save` stores a deep copy; `load` returns a
     copy, or `None`;
   - `InMemorySessionLock` (`SessionLock`): `acquire(key)` returns `False` while the key is
     held; `release` of a key that is not held is a no-op;
   - `ScriptedApiGateway` (`ApiGateway`): `invoke(method_path, **kwargs)` returns the
     scripted value per `method_path`, or raises the scripted exception, and records the call.
     An unscripted path raises `LookupError`.
   The package stays dependency-free (`dependencies = []`). The fakes use only the stdlib.
2. **`src/vibey_runners/common/tests/`** (new):
   - `tests/application/test_fakes.py` has behaviour tests for every fake;
   - `tests/application/test_port_parity.py` is the tenant's registry: a `REGISTRY` tuple of
     `(port, factory)` with the same checks as vibey's `tests/fakes/test_port_parity.py`
     (`isinstance`, signature parity, not a stub). A meta check fails when a Protocol in
     `vibey_runners.common.application.interfaces` has no registered fake;
   - `tests/application/test_completion.py` tests the use case over the fakes, reaching 100%
     branch coverage of `application/`.
3. **CI.** The three `vibey-runners-common` rows gain
   `test: 'python -m pytest -q --cov=vibey_runners.common --cov-branch --cov-fail-under=100'`.
   `tests/meta/test_tools_matrix_covers_every_package.py` then counts the row. Update the
   YAML comment at `ci.yml:317-320`, which says the package ships no suite.
4. **Import contracts.** `.importlinter` in common, or the `[tool.importlinter]` in its
   `pyproject.toml`, forbids `vibey_runners.common.application` and `.domain` from importing
   `vibey_runners.common.testing`: production code never uses a fake.

## Where to change
- New `src/vibey_runners/common/src/vibey_runners/common/testing/{__init__,fakes}.py`, `testing/interfaces/{__init__,fakes_interface}.py`.
- New `src/vibey_runners/common/tests/{__init__.py,application/__init__.py,application/test_fakes.py,application/test_port_parity.py,application/test_completion.py}`.
- `src/vibey_runners/common/pyproject.toml` (the import contract), `.github/workflows/ci.yml` (three `test:` keys and one comment).

## Acceptance criteria
- [ ] `(cd src/vibey_runners/common && pip install -e ".[dev]" && python -m pytest -q --cov=vibey_runners.common --cov-branch --cov-fail-under=100 && mypy --strict src/vibey_runners/common && lint-imports)` passes.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_tools_matrix_covers_every_package.py` passes.
- [ ] Every common port has a registered fake.

## Tests to write first (TDD)
- `test_every_port_has_a_registered_fake`, then one behaviour test per fake, then the use case tests.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/common && python -m pytest -q --cov=vibey_runners.common --cov-branch --cov-fail-under=100
    cd src/vibey_runners/common && mypy --strict src/vibey_runners/common && lint-imports
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- The runners' own fakes (their lanes switch them to these).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry` (the pattern it copies).
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** every runner's suite, which installs `../common`, and `tests/meta/*`.
- **Standing constraints (every tenant lane):**
  - The tenant's own gates and floor pass, on its Python floor (ADR-0022).
  - A fake is a plain class with real in-memory behaviour, and never `unittest.mock`.
  - Substitution happens at a declared seam: a constructor or keyword argument, a typer
    `ctx.obj`, or a function parameter with a production default. It never happens by
    patching an import.
  - The tenant adds its own `test_port_parity.py` (registry, parity, not-a-stub) and its own
    patching ratchet (`test_patching_ratchet.py` plus `patching_baseline.json`), in its test
    directory, and lowers the ratchet for every file it converts.
  - Line 1 of every new file is the provenance line, copied byte-for-byte.
  - Protected root tests are never edited.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
