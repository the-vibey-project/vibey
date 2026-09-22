## Title
test(qwenloop): the CLI takes its servers, runner and GitHub reader from a composition in the typer context, and test_cli.py patches nothing

## Why
`src/vibey_runners/qwen/tests/test_cli.py` (961 lines) makes 74 patch calls. It replaces names
imported into `qwenloop.cli.app`:
- `LlamaCppServer` ×13 and `VllmServer` ×4 (built at `app.py:233-236`, `:666`, `:699-700`);
- `AutonomousRunner` ×6 (`:299`);
- `list_open_pull_requests` ×6 and `list_open_issues` ×4 (`:398-399`);
- plus `shutil.which` and the subprocess module.

The CLI builds each of these inline, so a test can only reach them by patching the import.
`fakes-tenant-qwen-1` gave the servers and the GitHub reader declared seams and fakes. This
lane gives the CLI one composition object, found through typer's `ctx.obj`, which is click's
declared seam. It is the same design as vibey's `CliComposition` (`fakes-job-wakeup`).

## Required behaviour
1. **`src/qwenloop/cli/composition.py` — `class QwenloopComposition`**, with an interface
   beside it. Its keyword-only fields default to production:
   - `llama_server: Callable[[], LlamaCppServer]`, `vllm_server: Callable[[], VllmServer]`,
     `compat_server: Callable[..., OpenAICompatServer]`;
   - `runner_factory: Callable[..., AutonomousRunner]` (default `AutonomousRunner`);
   - `github: GitHubReader` (`GITHUB`);
   - `locator: Callable[[str], str | None]` (`shutil.which`);
   - `ollama_probe: OllamaProbeInterface` (default `OllamaProbe()`): the local-Ollama probe #388
     added. Today `cli/app.py` holds it in the module attribute `_ollama_probe`, and
     `tests/conftest.py`'s autouse `no_local_ollama` replaces it with `monkeypatch.setattr` — a
     substitution by patching (9.b). `_select` reads it through `QwenloopComposition.current()`
     instead, and the module attribute goes;
   - `clock: ClockInterface` (default `SystemClock()`): the clock #382 made the runner require,
     which `_run_plan` builds today; it reaches `runner_factory(..., clock=...)` from here.
   `QwenloopComposition.current()` returns `click.get_current_context(silent=True).find_object(QwenloopComposition)`
   or the default.
2. **`cli/app.py`** reads every one of these through `QwenloopComposition.current()` at each
   site listed in *Why*, and nowhere else. `main()` (`:760`) is unchanged.
3. **`tests/fakes.py`** (it exists since #388, holding `FakeOllamaProbe`) gains:
   - `ScriptedAutonomousRunner`: its constructor records the kwargs, and `run()` returns a
     scripted verdict or exit code and records its calls;
   - a `FakeManagedServer`, which stands in for both `LlamaCppServer` and `VllmServer`. It is
     built over `InMemoryOpenAIServer` (`fakes-tenant-qwen-1`), and it implements `inspect`,
     `start`, `stop` and `status` with scripted state (running, stopped, missing binary);
   - a `ScriptedGitHubReader(issues, pull_requests)`.
   Register them in `tests/test_port_parity.py`.
4. **Switch `tests/test_cli.py`**: every patch becomes
   `CliRunner().invoke(app, [...], obj=QwenloopComposition(...))`. Keep every assertion on
   the output and exit code. Lower the ratchet to zero for this file.
5. **`tests/conftest.py`'s autouse `isolated_settings`** (`:6-20`) stays. It uses `setenv`
   and `delenv`, which are the environment seam. Its autouse **`no_local_ollama`** (added by
   #388) changes: it no longer patches `qwenloop.cli.app._ollama_probe`. It returns a
   `FakeOllamaProbe(available=False)` (already in `tests/fakes.py` since #388), and every test
   that invokes the CLI passes it in `QwenloopComposition(ollama_probe=...)`; a test with no
   composition gets the production default, so each `CliRunner().invoke` in `test_cli.py` passes
   one. `grep -n "monkeypatch.setattr" src/vibey_runners/qwen/tests/conftest.py` prints nothing.

## Where to change
- New `src/vibey_runners/qwen/src/qwenloop/cli/composition.py` and its interface; `src/qwenloop/cli/app.py` (the listed sites).
- `src/vibey_runners/qwen/tests/fakes.py`, `tests/test_port_parity.py`, `tests/patching_baseline.json`, `tests/test_cli.py`.

## Acceptance criteria
- [ ] `grep -cE "monkeypatch.setattr|patch\(" src/vibey_runners/qwen/tests/test_cli.py` prints `0`.
- [ ] The qwenloop baseline has no entry left, or only entries with a written reason.
- [ ] qwenloop's suite passes at its 100% floor, and `mypy --strict` passes.

## Tests to write first (TDD)
- `tests/test_cli.py` (appended): `test_composition_defaults_to_production` and `test_composition_is_found_in_the_context`.
- Then convert the existing tests one command at a time.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen && python -m pytest -q -p no:cacheprovider
    cd src/vibey_runners/qwen && python -m mypy --strict src/qwenloop && lint-imports && bandit -q -r src/qwenloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-qwen-1`.
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
