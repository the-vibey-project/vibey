## Title
feat(install): vibey install sets up local Ollama and this era's default model

## Why
This implements #391, and this text replaces #391's body.

The operator wants local Ollama in the installer (2026-09-22). Sub-doctrine 8.d (doctrines.md:200)
makes GPT-OSS 20B on Ollama this era's default model (#387 flips the defaults). Sub-doctrine
8.b keeps the sovereign path always on. But nothing installs, starts or checks Ollama or its
model.

#391's first body asked for a bespoke `OllamaLocalService` with its own brew, apt and
checksum-archive paths, plus the CLI flags and doctor lines, all in one lane. Since then:
- Ollama is a catalogue entry (lane installer-catalogue: pacman `ollama` with a systemd unit on
  Arch; formula `ollama` with `brew services` on macOS; probe `ollama list`);
- it is installed, started and waited for by the generic installer (lane
  installer-package-dependency);
- the flags are lane installer-cli, and the doctor lines are lane installer-doctor.

Both default OSes carry Ollama in their signed repositories: `extra/ollama` 0.34.2 and
Homebrew `ollama` 0.34.2, read 2026-09-22. So no release-archive path is needed, and none may
pipe a script into a shell.

What is left, and what this lane builds, is the one thing that is behaviour rather than data:
pulling the model, idempotently. It also makes `DEFAULT_LOCAL_MODEL` the single source of the
default, as #391 asked ("never hard-coded twice").

## Required behaviour
1. `src/vibey/infrastructure/ollama_model.py` declares:
   ```python
   class OllamaModelInstaller:
       def __init__(self, executor: CommandExecutorInterface, *, model: str = DEFAULT_LOCAL_MODEL,
                    key: str = "model", pull_timeout_seconds: float = 7200.0) -> None
   ```
   - `key` and `model` properties.
   - `check() -> DependencyReport` changes nothing. It decides in this order:
     - `executor.which("ollama")` is None: MISSING, f"ollama is not installed, so {model}
       cannot be pulled", fix `vibey install --only ollama`;
     - `executor.run(("ollama", "list"), timeout=10.0)` exits non-zero: STOPPED, "the Ollama
       server is not answering `ollama list`", fix `vibey install --only ollama`;
     - `executor.run(("ollama", "show", model), timeout=30.0)` exits 0: READY,
       f"{model} is present";
     - otherwise: MISSING, f"{model} is not pulled yet ({size})".
       - `size` is `DEFAULT_LOCAL_MODEL_DOWNLOAD` when `model == DEFAULT_LOCAL_MODEL`, else
         "download size unknown".
       - The fix is `vibey install --only model`, followed by `--model <model>` when the model
         is not the default.
   - `install() -> DependencyReport`:
     1. READY returns the check with "; nothing to do" appended and `changed=False`.
     2. When ollama is absent or the server is not answering, it returns FAILED with the check's
        detail and fix.
     3. Otherwise it runs `("ollama", "pull", model)` with `timeout=pull_timeout_seconds`.
        Ollama verifies each layer's sha256 digest itself.
        - A non-zero exit returns FAILED, f"ollama pull {model} failed: <last stderr line>",
          with `changed=True`.
        - Otherwise it re-checks. READY returns `DependencyReport(key, READY, f"pulled {model}", changed=True)`.
          Anything else returns FAILED, f"pulled {model} but `ollama show {model}` still fails".
2. `src/vibey/infrastructure/interfaces/ollama_model_interface.py` declares
   `@runtime_checkable class OllamaModelInstallerInterface(DependencyInstaller, Protocol)`,
   adding a `model` property.
3. In `src/vibey/infrastructure/engines/ollama_chat.py`, the default at :39 (`DEFAULT_OLLAMA_MODEL`,
   `"gpt-oss:20b"` after #387) becomes `DEFAULT_OLLAMA_MODEL = DEFAULT_LOCAL_MODEL`, imported
   from `vibey.domain.local_stack`. Its public name and its value are unchanged.
4. qwenloop cannot import vibey, so its `DEFAULT_ENDPOINT_MODEL`
   (src/vibey_runners/qwen/src/qwenloop/domain/config.py:15) keeps its literal. A root test
   asserts it equals `DEFAULT_LOCAL_MODEL`, so the two can never drift silently.

## Where to change
- New files:
  - `src/vibey/infrastructure/ollama_model.py`
  - `src/vibey/infrastructure/interfaces/ollama_model_interface.py`
  - `tests/infrastructure/test_ollama_model.py`
- One edit in `src/vibey/infrastructure/engines/ollama_chat.py`: the import plus line 39. Use
  edit_file.
- Provenance line 1 is copied from `src/vibey/infrastructure/postgres.py`.
- Use `FakeCommandExecutor` from `tests/fakes/host.py` (lane installer-host-runner).

## Acceptance criteria
- [ ] check covers the four states. The default model's MISSING detail says "14 GB", and
      another model's says "download size unknown" and puts `--model` in its fix.
- [ ] install pulls exactly once with `("ollama", "pull", "gpt-oss:20b")`. A second install
      on the now-present model runs no pull (replay).
- [ ] install without ollama, or with the server down, runs no pull and fails with the ollama
      fix.
- [ ] A failed pull, and a pull that leaves `ollama show` failing, are FAILED.
- [ ] `DEFAULT_OLLAMA_MODEL is DEFAULT_LOCAL_MODEL`, and
      `qwenloop.domain.config.DEFAULT_ENDPOINT_MODEL == DEFAULT_LOCAL_MODEL`.
- [ ] All tests under `tests/infrastructure/engines` still pass. 100% branch coverage of
      `ollama_model.py`.

## Tests to write first (TDD)
`tests/infrastructure/test_ollama_model.py`:
- `test_check_reports_missing_stopped_present_and_not_pulled`
- `test_default_model_names_its_download_size`
- `test_another_model_names_itself_in_the_fix`
- `test_install_pulls_once_and_replay_pulls_nothing`
- `test_install_refuses_without_a_running_ollama`
- `test_install_reports_a_failed_pull_and_a_missing_model_after_pull`
- `test_the_default_model_is_declared_once`: the ollama_chat alias and the qwenloop equality.
- `test_installer_satisfies_the_port`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_ollama_model.py tests/infrastructure/engines tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/ollama_model.py' --fail-under=100

## Out of scope
- These are owned by other lanes:
  - the Ollama catalogue entry (installer-catalogue);
  - installing and starting Ollama (installer-package-dependency);
  - `--ollama`, `--yes`, `--no-model`, `--model` and the confirmation prompt (installer-cli);
  - doctor (installer-doctor);
  - RAM-tiered model choice and llama.cpp GGUFs (#383);
  - GPU variants such as `ollama-cuda`, `ollama-rocm` and `ollama-vulkan` (a follow-up).
- The chart and docs.

Commit as `feat(install): ...`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
