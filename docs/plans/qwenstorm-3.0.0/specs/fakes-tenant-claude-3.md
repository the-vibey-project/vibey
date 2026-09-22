## Title
test(claudeloop): the agent, API and GitHub gateways and the doctor take their clients and processes by injection, and the claudeloop ratchet reaches zero

## Why
The rest of claudeloop's patching is in its infrastructure tests:
- `tests/infrastructure/test_doctor_env.py` (61): `subprocess.run` ×17 across the suite, and
  `claudeloop.infrastructure.doctor_env.platform.system`;
- `tests/infrastructure/test_agent_gateway.py` (59): `claudeloop.infrastructure.agent.*`,
  and `catalog.list_sessions` ×3;
- `tests/infrastructure/test_api_gateway.py` (30), `test_api_binder.py` (10) and
  `test_translate_extended.py` (9): `claudeloop.infrastructure.api.gateway.resolve_callable`
  ×5, `load_json_payload` ×5, `build_client` ×5 and `build_call_kwargs` ×4, plus
  `api.introspect.resolve_callable`;
- `tests/infrastructure/test_github_import.py` (21): `github_import._fetch_issue_api`;
- `tests/infrastructure/test_stream_ui_chat.py` (15): `stream_ui.time.sleep` ×2;
- `infrastructure/snapshot`: `shutil.copytree`.

## Required behaviour
1. **Doctor.** `doctor_env` takes a `CommandRunner` (`run` and `which`) and a `Platform`
   (`system()`) through keywords, with the production defaults.
   `tests/application/fakes.py` gains `ScriptedCommandRunner` and `FakePlatform`.
2. **The API gateway.** `infrastructure/api/gateway.py` takes `client_factory`, `resolver`
   and `payload_loader` as constructor keywords, with the production defaults (`build_client`,
   `resolve_callable`, `load_json_payload`). `build_call_kwargs` stays pure, so tests call it
   for real. The fake is `InMemoryAnthropicClient`: a scripted SDK surface whose method paths
   resolve the way `resolve_callable` resolves the real client's, with a scripted return
   value or exception. It records every call.
3. **The agent gateway and catalog** take their session-listing function and process launcher
   by injection. Reuse `vibey_runners.common.testing` fakes where a common port fits.
4. **GitHub import** takes `fetch_issue` (default `_fetch_issue_api`) as a keyword.
5. **Stream UI and snapshot** take `sleep` and `copytree` keywords, with the production defaults.
6. **The ratchet reaches zero** for claudeloop, apart from any entry carrying a written reason.
   Register every new interface's fake.

## Where to change
- `src/claudeloop/infrastructure/doctor_env.py`, `api/gateway.py`, `api/introspect.py`, `agent/*`, `github_import.py`, `stream_ui.py`, `snapshot.py` (keywords and interfaces).
- `tests/application/fakes.py`, `tests/application/test_port_parity.py`, `tests/patching_baseline.json`, and the listed test modules.

## Acceptance criteria
- [ ] `python -c "import json; print(json.load(open('src/vibey_runners/claude/tests/patching_baseline.json')))"` prints `{}`, or only entries with a reason.
- [ ] claudeloop's CI row passes on 3.12, 3.13 and 3.14.

## Tests to write first (TDD)
`tests/application/test_fakes.py`:
- `test_in_memory_anthropic_client_resolves_method_paths`
- `test_command_runner_and_platform_fakes`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/claude && python -m pytest -q
    cd src/vibey_runners/claude && mypy --strict src/claudeloop && lint-imports && bandit -q -r src/claudeloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The `live` and `system` tiers. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-claude-2`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the protected root tests.
- **Standing constraints (every tenant lane):**
  - The tenant's own gates and floor pass on its Python floor (ADR-0022).
  - A fake is a plain class with real in-memory behaviour, and never `unittest.mock`.
  - Substitution happens at a declared seam: a constructor or keyword argument, a typer
    `ctx.obj`, or a parameter with a production default. It never happens by patching an
    import. `monkeypatch.setenv` and `delenv` stay allowed.
  - The tenant keeps its own registry and parity test and its own patching ratchet
    (`test_patching_ratchet.py` plus `patching_baseline.json`) in its test directory. Lower
    the ratchet for every file you convert, and never raise it.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - Protected root tests are never edited. Change existing files with `edit_file`, and never
    rewrite an existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
