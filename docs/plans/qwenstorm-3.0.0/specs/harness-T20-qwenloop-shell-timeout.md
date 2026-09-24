## Title
feat(qwenloop): the shell tool's timeout is a key, not 120 seconds

## Why
The last of four lanes (T20a config, T20b environment, T20c sandbox, and this one). qwenloop's
shell tool killed every command after a hard-coded 120 s, which breaks sub-doctrine 12.c
(`src/vibey_tools/gh/docs/doctrines.md:455`) and collides with 8.e (`doctrines.md:271-292`): a
storm lane's full suite was measured at 259 s (`.pre-commit-config.yaml:18`), and waiting in the
test harness's queue makes it longer. Draft ADR-0045 §11 needs the limit configurable, so an operator
can let a lane wait for its run.

harness-T20a–c made `shell_timeout_seconds` a key (file and `QWENLOOP_SHELL_TIMEOUT_SECONDS`) and
taught `SandboxTools` to take it. This lane passes the configured value from the command to the
sandbox, through `_run_plan`, which builds the sandbox today with no timeout argument
(`src/vibey_runners/qwen/src/qwenloop/cli/app.py:302`, `SandboxTools(cwd)`). The storm driver calls
`_run_plan` with keywords it already passes (`STORM/qwenlane.py:102-110`),
so the new parameter is keyword-only with today's default.

## Required behaviour
In `src/vibey_runners/qwen/src/qwenloop/cli/app.py`:
1. `_run_plan` (`:282-313`) gains the keyword-only parameter `shell_timeout_seconds: float = 120.0`,
   after `desktop_notifications`, and builds `SandboxTools(cwd, shell_timeout_seconds=shell_timeout_seconds)` (`:302`).
2. Both call sites pass the configured value: `_run_single` (`:262-271`) and `_run_storm`
   (`:427-436`) each add `shell_timeout_seconds=config.shell_timeout_seconds`.
3. **The fake**, appended to `src/vibey_runners/qwen/tests/fakes.py` (it exists; add imports to its
   import block and append the class; never recreate the file):
   `ScriptedInferenceServer(turns: Sequence[Sequence[ChatChunk]] = (), *, info: ServerInfo | None = None, healthy: bool = True)`
   implements qwenloop's `InferenceServer` port (`src/qwenloop/application/interfaces/__init__.py:33-41`)
   in memory, with real behaviour for every method:
   - `info` defaults to `ServerInfo(Backend.OPENAI_COMPAT, "memory", "http://127.0.0.1:0/v1", False, True)`;
   - `inspect(profile)` returns `info`; `install(profile)` returns `Path("/memory/models") / profile.name`;
     `start(profile)` returns `info`; `health(info)` returns `healthy`; `stop(info)` records the stop;
     each appends its name to `self.calls`;
   - `chat_stream(info, messages)` is an async generator: it appends `list(messages)` to `self.seen`
     and yields the chunks of the turn with that index (nothing once the script is exhausted).

   `InferenceServer` is not `runtime_checkable`, so add no `isinstance` assertion for it.

## Where to change
- `src/vibey_runners/qwen/src/qwenloop/cli/app.py` (with `edit_file`; 761 lines).
- `src/vibey_runners/qwen/tests/fakes.py` (append).
- `src/vibey_runners/qwen/tests/test_cli.py` (append two tests; add `_run_plan` to its
  `from qwenloop.cli.app import app` line and the other imports to its import block).

## Acceptance criteria
- [ ] `_run_plan(server, PORTABLE, tmp_path, "shell-timeout", "plan", 2, startup_timeout_seconds=1, desktop_notifications=False, shell_timeout_seconds=0.5)` with a `ScriptedInferenceServer` whose first turn calls `shell` with `[sys.executable, "-c", "import time; time.sleep(5)"]` and whose second turn is text: the tool message the server sees in its second request contains `command timed out`, and the whole call takes well under 5 s. No `monkeypatch.setattr`: the server is the declared `server` parameter.
- [ ] `grep -c "shell_timeout_seconds=config.shell_timeout_seconds" src/vibey_runners/qwen/src/qwenloop/cli/app.py` prints `2`.
- [ ] `_run_plan`'s `shell_timeout_seconds` is keyword-only with default `120.0`, so the storm driver's call is unchanged.
- [ ] The tenant suite passes at its 100% floor, and its static gates pass.

## Tests to write first (TDD)
Appended to `src/vibey_runners/qwen/tests/test_cli.py` (`from fakes import ScriptedInferenceServer`):
- `test_run_plan_passes_the_shell_timeout`
- `test_run_plan_shell_timeout_is_keyword_only_with_the_old_default` (`inspect.signature`)

## Checks the lane must run (all must pass)
    (cd src/vibey_runners/qwen && uv run python -m pytest -q -p no:cacheprovider)
    (cd src/vibey_runners/qwen && uv run mypy --strict src/qwenloop && uv run lint-imports && uv run bandit -q -r src/qwenloop)
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The storm driver (`qwenlane.py` lives outside the repository): passing `shell_timeout_seconds=config.shell_timeout_seconds` there is an operator step.
- The existing patches in `test_cli.py` (lane fakes-tenant-qwen-2).
- Any vibey code. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T20b-qwenloop-shell-timeout-env, harness-T20c-qwenloop-shell-timeout-sandbox.
- **Files touched:** `src/vibey_runners/qwen/src/qwenloop/cli/app.py`, `src/vibey_runners/qwen/tests/fakes.py`, `src/vibey_runners/qwen/tests/test_cli.py`.
- **Shares a file with:** `tests/fakes.py` and `tests/test_cli.py` (fakes-tenant-qwen-1 and -2 land after this lane and append to both).
- **Must keep passing unchanged:** the whole qwenloop suite at its 100% floor; the storm driver's call `_run_plan(server, profile, lane, run_id, text, max_turns, startup_timeout_seconds=..., desktop_notifications=True)`; and the protected root tests.
- **Registry (amendment A4):** the tenant has no registry yet; fakes-tenant-qwen-1 creates it (`tests/test_port_parity.py`) and must register every application port, `InferenceServer` included, for which `ScriptedInferenceServer` is now available in `tests/fakes.py`.
- **Standing constraints (every qwenloop harness lane):**
  - This lane changes a runner tenant and runs that tenant's own gates (ADR-0022); qwenloop does not import vibey.
  - The tenant's in-memory fakes live in `src/vibey_runners/qwen/tests/fakes.py` (it exists; append to it, never recreate it).
  - Substitute only at a declared seam: here the `server` parameter. Never add `monkeypatch.setattr`, `mock.patch` or `MagicMock`; a child of `sys.executable` is inside the default tier.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - No test needs a model server or waits longer than 5 s.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
