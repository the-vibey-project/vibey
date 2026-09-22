## Title
test(fakes): the sovereign surface adapters are declared over the HTTP opener seam and tested against the in-memory server

## Why
ADR-0042 gives each sovereign surface a port, a production in-memory implementation and a
real adapter:
- docs (BookStack), files (Nextcloud), messaging (Matrix), secrets (OpenBao), SMS (Kannel),
  tracker (Plane) and configuration (Infisical);
- email (Forward Email) is SMTP and is handled in `fakes-sovereign-smtp`.

Lane `sovereign-surfaces-ports` (open PR work) revises these ports and adapters. It may rename
adapters: the operator's working tree has `secrets/bitwarden.py` and `sms/fossify.py`. This lane
runs **after** it, on whatever adapters it left.

Every one of these HTTP adapters takes an untyped `opener` (for example
`files/nextcloud.py:19`, `tracker/plane.py:25`, `secrets/openbao.py:27`). Their tests in
`tests/infrastructure/test_sovereign_surfaces.py:202-460` feed it `MagicMock`s through
`_mock_response` and `_raising_opener`. `fakes-http-transport` declared the seam
(`vibey.infrastructure.interfaces.UrlOpener`) and its fake (`tests/fakes/http.py`
`InMemoryHttpServer`). This lane moves the sovereign adapters onto both.

## Required behaviour
1. **Find the adapters at the start of the lane.**
   `ls src/vibey/infrastructure/{docs,files,messaging,secrets,sms,tracker,config_store}/*.py`.
   Every module other than `in_memory.py` and `__init__.py` that imports `urllib.request` is in
   scope. List them in the commit body.
2. **For each adapter:**
   - the constructor parameter is `opener: UrlOpener = urllib.request.urlopen`. A default of
     `None` followed by `opener if opener is not None else urllib.request.urlopen` collapses to
     the typed default;
   - remove each `# type: ignore[operator]` that this makes unnecessary;
   - an adapter that takes no opener at all (a revised adapter may not) gains the parameter in
     the same form. Its interface file under `<surface>/interfaces/` gains nothing: interfaces
     declare the adapter's methods, not its constructor.
3. **Switch the sovereign adapter tests** in `tests/infrastructure/test_sovereign_surfaces.py`
   (the tests for the surfaces above). For each:
   - replace every `MagicMock` opener with an `InMemoryHttpServer` routed with the exact method
     and URL the adapter must call. Take them from the adapter's code, and cite the upstream
     API in a one-line comment where the path is not obvious;
   - replace `opener.call_args[0][0]` with `server.requests[i]`, and assert `method`, `url`,
     the auth header and the body (`server.json(i)`);
   - error tests use `route(..., status=404)` or `unreachable(...)`;
   - when no `MagicMock` remains in the module, delete `_mock_response` and `_raising_opener`.
4. Lower the file's `mock` count in `tests/meta/patching_baseline.json`.

## Where to change
- The sovereign HTTP adapter modules (annotations and defaults only).
- `tests/infrastructure/test_sovereign_surfaces.py` (the sovereign HTTP adapter tests),
  `tests/meta/patching_baseline.json`.

## Acceptance criteria
- [ ] `grep -n "opener: object\|opener: Any\|type: ignore\[operator\]" src/vibey/infrastructure/{docs,files,messaging,secrets,sms,tracker,config_store}/*.py` prints nothing.
- [ ] No sovereign HTTP adapter test uses `MagicMock`.
- [ ] Each adapter has at least one test that fails if its request path, method or auth header changes.
- [ ] 100% `infrastructure/` coverage, and bandit is clean.

## Tests to write first (TDD)
- Convert one adapter's tests at a time. For each adapter, first add
  `test_<adapter>_sends_the_documented_request`, which asserts the method, URL, auth header and body on
  `server.requests[0]`. Then convert its existing tests.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/infrastructure/test_sovereign_surfaces.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Email (`fakes-sovereign-smtp`).
- The `build_app` wiring tests in the same file (`fakes-bootstrap-seam`).
- Changing any port's methods. That belongs to `sovereign-surfaces-ports`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** **`sovereign-surfaces-ports`** (supplied later), `fakes-http-transport`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the in-memory surface tests in the same file, and the protected tests.
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
