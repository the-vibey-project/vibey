## Title
test(cli): the design and visual CLI flows and the sovereign-provider options run on the in-memory app, and Ollama becomes an in-memory HTTP route

## Why
Two CLI modules still need PostgreSQL, and one of them also runs a real HTTP server:
- `tests/cli/test_main_integration.py` (19 tests, `pytestmark = integration`, `:24`). Its
  docstring says it exists because the unit tests "never exercise the code that actually
  calls `build_app()`". With `InMemoryApp` (`fakes-bootstrap-seam`), the real `build_app`
  composition runs without PostgreSQL, so these flows can run in the default tier.
  The flows are: new project, the full design flow, answer modes, resume, the visual flow
  (accept, waive), and budget and observability config.
- `tests/cli/test_sovereign_provider_options.py` (14 tests, `:32`):
  - `FakeOllama` (`:78-110`) is a `BaseHTTPRequestHandler` server on a loopback port;
  - `:145-151` patches the worker's engine wiring and
    `vibey.infrastructure.db.notifier.PostgresJobReadyNotifier`.

`tests/fakes/http.py` (`InMemoryHttpServer`, `fakes-http-transport`) answers the same
`/api/chat` route in memory. The Ollama client takes an `opener`. What is missing is a
composition field for the local endpoint's opener, so a CLI test can hand it in.

## Required behaviour
1. **`CliComposition` gains `local_http: UrlOpener = urllib.request.urlopen`.** The CLI
   passes it to every sovereign provider it builds: `QwenloopDesignProvider`,
   `QwenloopWorkPlanProducer`, and the Ollama transport behind them. Find them in
   `cli/main.py`'s provider selection (`_PROVIDERS`, and the worker's provider branch), and
   pass the opener through the constructors that already accept one. Where a constructor does
   not accept one, add the keyword with the production default.
2. **`test_sovereign_provider_options.py`**:
   - `FakeOllama` becomes an `InMemoryHttpServer` with
     `route("POST", f"{base}/api/chat", body={"message": {"content": json.dumps(answer)}})`;
   - assertions on `fake.requests` become `server.requests` and `server.json(i)`;
   - the patches at `:145-151` become composition fields (`fakes-cli-composition`,
     `fakes-job-wakeup`);
   - drop the database fixture and the mark.
3. **`test_main_integration.py`**: drop the database fixture and the mark, and invoke through
   `ops.invoke(memory_app, ...)` (`tests/cli/ops_support.py`). Keep its docstring's intent:
   it now says it exercises the real `build_app` composition over the in-memory persistence.
4. Lower both files' baseline entries. Remove them from `PER_TEST_MODULES` if listed.

## Where to change
- `src/vibey/cli/composition.py` and its interface; the provider-construction sites in
  `src/vibey/cli/main.py`; any sovereign-provider constructor that must gain `opener`
  (`src/vibey/infrastructure/engines/qwenloop_design.py`, `qwenloop_decompose.py`, `ollama_chat.py`).
- `tests/cli/test_sovereign_provider_options.py`, `tests/cli/test_main_integration.py`,
  `tests/cli/ops_support.py`, `tests/meta/patching_baseline.json`.

## Acceptance criteria
- [ ] `grep -n "BaseHTTPRequestHandler\|HTTPServer\|patch(" tests/cli/test_sovereign_provider_options.py` prints nothing.
- [ ] Both modules pass with PostgreSQL stopped (`-m "not integration"`), with unchanged test counts.
- [ ] 100% `cli/` and `infrastructure/` coverage.

## Tests to write first (TDD)
- `tests/cli/test_composition.py` (appended): `test_local_http_defaults_to_urlopen`.
- Then move one test at a time.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The real-Ollama `paid`/`live` tests. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-cli-operational-1`, `fakes-http-transport`.
- **Files touched:** see *Where to change*.
- **Shares a file with:** `src/vibey/cli/main.py` (provider sites only).
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
