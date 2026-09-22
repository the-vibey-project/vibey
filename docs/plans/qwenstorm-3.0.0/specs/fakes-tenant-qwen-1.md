## Title
test(qwenloop): the inference servers, the model cache and the GitHub reader take declared seams, and an in-memory OpenAI-compatible server answers them

## Why
qwenloop (`src/vibey_runners/qwen`) enforces a 100% floor in its `addopts`
(`pyproject.toml:68`). It reaches the floor by patching, 126 `monkeypatch.setattr` calls in
all. Two infrastructure modules account for most of them:
- `tests/test_inference.py` (811 lines) patches:
  - `urllib.request.urlopen` (`:79`, `:131`, `:266`, `:281`, …);
  - `asyncio.create_subprocess_exec` (`:245`) and `os.killpg` (`:213`);
  - the module's own `_pid_alive` (`:214`, `:254`) and `_free_port` (`:244`).
  `src/qwenloop/infrastructure/inference.py` calls `urllib.request.urlopen` directly at `:133`,
  `:157` and `:418`, and spawns the managed llama-server or vLLM itself.
- `tests/test_github.py` patches `github.shutil` and `github.subprocess`
  (`src/qwenloop/infrastructure/github.py:21-36` calls `shutil.which("gh")` and `subprocess.run`).

`infrastructure/model_cache.py:23` already takes an `opener`, which is the pattern to copy. No
qwenloop test needs a model server: they patch one in. This lane replaces the patches with
seams and one honest fake.

## Required behaviour
1. **`src/qwenloop/infrastructure/interfaces/`** (extend the existing package) declares:
   - `UrlOpener`, with the same shape as vibey's (`fakes-http-transport`). Redeclare it here:
     qwenloop does not depend on vibey (ADR-0022);
   - `ProcessSpawner` (`spawn(argv, *, env, stdout, stderr, start_new_session) -> SpawnedProcess`);
   - `ProcessProbe` (`alive(pid) -> bool`, `killpg(pid, sig) -> None`);
   - `PortAllocator` (`free_port() -> int`);
   - `CommandRunner` (`which(name) -> str | None`, `run(argv, *, timeout) -> (returncode, stdout, stderr)`).
   Each has a production implementation, a stateless class and a module constant, in the
   module that uses it today.
2. **Inject them.**
   - `OpenAICompatServer`, `LlamaCppServer` and `VllmServer` take `opener`, `spawner`,
     `probe` and `ports` keywords, with the production defaults. Every direct call listed in
     *Why* goes through them.
   - `github.list_open_issues` and `list_open_pull_requests` become methods of
     `class GitHubReader(runner: CommandRunner = GH_RUNNER)`. Keep module-level aliases bound
     to a default instance, `GITHUB = GitHubReader()`, so the CLI's imports keep working,
     with a comment saying why.
3. **`src/vibey_runners/qwen/tests/fakes.py`** (it exists since #388 and holds `FakeOllamaProbe`:
   append to it with `edit_file`, never rewrite it; the tests are flat, so there is no
   `application/` subdirectory):
   - `InMemoryOpenAIServer` (`UrlOpener`) answers `/v1/models`, `/health` and
     `/v1/chat/completions`:
     - streaming (`stream: true`, SSE `data:` lines ending with `[DONE]`) and non-streaming;
     - scripted assistant turns (text or tool calls), with `usage` and llama-server `timings`
       (`prompt_n`, `cache_n`, `prompt_ms`, `predicted_n`, `predicted_ms`, `predicted_per_second`);
     - scripted HTTP errors, timeouts and unreachable;
     - it records every request body.
   - `ScriptedServerProcess`, `ScriptedSpawner`, `FakeProcessProbe` (it records `killpg`),
     `FixedPortAllocator` and `ScriptedCommandRunner`, each as in vibey's `tests/fakes/process.py`
     but local to qwenloop.
4. **Switch `tests/test_inference.py` and `tests/test_github.py`** to the fakes. Every
   `monkeypatch.setattr` on `urllib`, `asyncio`, `os`, `shutil`, `subprocess`, or on a
   `qwenloop.infrastructure` attribute, goes. `monkeypatch.setenv` and `delenv` stay.
5. **The tenant registry and ratchet:**
   - `tests/test_port_parity.py` registers every qwenloop port, from
     `application/interfaces` and the new infrastructure seams, with its fake, and fails on
     an unregistered one;
   - `tests/test_patching_ratchet.py` and `tests/patching_baseline.json` hold today's counts
     minus this lane's.

## Where to change
- `src/vibey_runners/qwen/src/qwenloop/infrastructure/inference.py`, `github.py`, `interfaces/`.
- New `src/vibey_runners/qwen/tests/fakes.py`, `tests/test_fakes.py`, `tests/test_port_parity.py`,
  `tests/test_patching_ratchet.py`, `tests/patching_baseline.json`.
- `src/vibey_runners/qwen/tests/test_inference.py`, `tests/test_github.py`.

## Acceptance criteria
- [ ] `grep -c "monkeypatch.setattr" src/vibey_runners/qwen/tests/test_inference.py src/vibey_runners/qwen/tests/test_github.py` prints `0` for both.
- [ ] `cd src/vibey_runners/qwen && python -m pytest -q -p no:cacheprovider` passes at its 100% floor, with no model server running.
- [ ] `python -m mypy --strict src/qwenloop` passes.

## Tests to write first (TDD)
`tests/test_fakes.py`:
- `test_openai_server_streams_a_scripted_turn_with_timings`
- `test_openai_server_scripts_tool_calls`
- `test_openai_server_errors_and_unreachable`
- `test_spawner_and_probe_record_lifecycle`
- `test_command_runner_scripts_gh`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen && python -m pytest -q -p no:cacheprovider
    cd src/vibey_runners/qwen && python -m mypy --strict src/qwenloop && lint-imports && bandit -q -r src/qwenloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- `qwenloop.cli.app`'s patches (`fakes-tenant-qwen-2`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry` (the pattern), and the in-flight qwenloop lanes that edit
  the same files: `qwenloop-toolcall-retry`, `default-model-p3`, `install-ollama`,
  `harness-T20-qwenloop-shell-timeout`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** qwenloop's run telemetry tests (`qwenloop-run-telemetry`), and the protected root tests.
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
