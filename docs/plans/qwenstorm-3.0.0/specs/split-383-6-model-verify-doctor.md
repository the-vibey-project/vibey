<!-- split of #383: child 6 of 6; audit: issue-audit/updates/383.md -->

## Title
feat(qwenloop): `qwenloop model verify <entry>` and `qwenloop doctor` report the selected model, its backend and its state

## Why
Sub-doctrine 8.d (`src/vibey_tools/gh/docs/doctrines.md:236-257`) pins each supported model's
weights (source, revision, digest), and 10.f (`doctrines.md:419`) bounds every claim by evidence:
an operator must be able to prove that the artifact on disk is the pinned one, and see which model
a run will use and why. Today `qwenloop model verify` takes only a `PROFILES` name
(`src/vibey_runners/qwen/src/qwenloop/cli/app.py:488-494`), and `ModelCache.verify`
(`src/qwenloop/infrastructure/model_cache.py:75-88`) compares the file with its own
`installed.json`, never with the pin. `qwenloop doctor` (`cli/app.py:523-556`) reports the backend
and model only for an attached endpoint; for the managed llama.cpp server it prints binaries only,
never the model, whether it is installed, or the fix. The catalogue (split-383-1) and the selection
with its reason (split-383-4) now exist to report.

## Required behaviour
All paths are under `src/vibey_runners/qwen/`.

1. **The cache checks the pin** (`src/qwenloop/infrastructure/model_cache.py`). In `verify`, the
   last check (`:86-88`) becomes:
   ```python
           digest = _sha256(target)
           if digest != manifest.get("installed_sha256"):
               raise ValueError("installed model digest does not match its installation manifest")
           if profile.sha256 is not None and digest != profile.sha256:
               raise ValueError("installed model digest does not match the pinned catalogue digest")
           return target
   ```
   and a new method, appended after `verify`:
   ```python
       def installed(self, profile: ModelProfile) -> Path | None:
           """The installed file, or None, without hashing it: doctor's cheap check."""
           if profile.filename is None:
               return None
           directory = self.profile_dir(profile)
           target = directory / profile.filename
           if target.is_file() and (directory / "installed.json").is_file():
               return target
           return None
   ```
2. **Its interface.** New `src/qwenloop/infrastructure/interfaces/model_cache_interface.py`:
   `@runtime_checkable class ModelCacheInterface(Protocol)` declaring `profile_dir`, `install`,
   `verify` (each `(self, profile: ModelProfile) -> Path`) and `installed`
   (`(self, profile: ModelProfile) -> Path | None`), a one-line docstring and `...` body each,
   importing `ModelProfile` from `qwenloop.domain.model`. `src/qwenloop/infrastructure/interfaces/__init__.py`
   imports it (between the `inference_interface` and `settings_interface` imports) and lists
   `"ModelCacheInterface"` in `__all__` (after `"ManagedServerInterface"`).
3. **Verifying an entry** (`src/qwenloop/cli/app.py`). A new module-level helper (module-level for
   the reason the module states at `:170-171`: the typer commands share it):
   ```python
   def _verify_entry(
       entry: ModelEntry,
       config: QwenConfig,
       *,
       backend: str = "all",
       cache: ModelCacheInterface | None = None,
       served: Callable[[str], str] | None = None,
   ) -> tuple[list[str], bool]:
   ```
   It returns report lines and whether every artifact checked passed:
   - When `backend` is `"all"` or `"llama.cpp"`:
     - `entry.gguf is None` → line `f"llama.cpp: {entry.name} pins no GGUF"`; this fails only when
       `backend == "llama.cpp"`;
     - else `(cache or ModelCache()).verify(entry.gguf)`: success → `f"llama.cpp: {entry.gguf.name} ok ({path})"`;
       `FileNotFoundError` → `f"llama.cpp: {entry.gguf.name} not installed"` then
       `"fix: qwenloop model install --profile portable"` when `entry.gguf.name == PORTABLE.name`,
       else `"fix: none yet: qwenloop model install installs the portable profile only"`, and fails;
       `ValueError` as `exc` → `f"llama.cpp: {entry.gguf.name} FAILED: {exc}"`, and fails.
   - When `backend` is `"all"` or `"ollama"`:
     - `entry.ollama is None` → line `f"ollama: {entry.name} pins no Ollama tag"`; this fails only
       when `backend == "ollama"`;
     - else `check = served or (lambda tag: asyncio.run(_attach(replace(config, model=tag)).check()))`;
       `check(entry.ollama.tag)` returning `model` → `f"ollama: {model} served by {config.endpoint_url}"`;
       `RuntimeError` as `exc` → `f"ollama: {entry.ollama.tag} not served: {exc}"` then
       `f"fix: ollama pull {entry.ollama.tag}"`, and fails.
   - Then, for each name in `entry.unverified`, the informational line
     `f"{name}: never load-tested for {entry.name} (unverified)"`.
4. **The command.** `verify` (`cli/app.py:488-494`) becomes:
   ```python
   @model_app.command()
   def verify(
       entry: Annotated[
           str | None,
           typer.Argument(help="A catalogue entry, e.g. gpt-oss-20b. Unset: --profile."),
       ] = None,
       profile: str = PORTABLE.name,
       backend: str = typer.Option("all", "--backend", help="all, llama.cpp or ollama."),
   ) -> None:
   ```
   With no `entry`, the body is exactly today's (`PROFILES[profile]` through `ModelCache().verify`).
   With an `entry`: a `backend` other than `all`, `llama.cpp`, `ollama` raises
   `typer.BadParameter("--backend must be all, llama.cpp or ollama")`; `ModelCatalogue().get(entry)`'s
   `KeyError` becomes `typer.BadParameter(str(exc.args[0]))`; then
   `lines, ok = _verify_entry(selected, _load_config(), backend=backend)`, each line echoed to
   stdout, and `raise typer.Exit(code=1)` when not `ok`.
5. **Doctor names the model.** A new module-level helper
   `_doctor_model_lines(config: QwenConfig, choice: BackendChoice, *, cache: ModelCacheInterface | None = None) -> list[str]`:
   - `choice.backend is Backend.OPENAI_COMPAT` → one line,
     `f"selected: {s['model']} ({s['reason']})"` with `s = _model_selection(config, _attach(config).profile)`
     (the endpoint's `backend:`, `endpoint:` and `model: ... ok|unavailable` lines, and its fix text —
     `ollama serve` / `ollama pull <model>` in `inference.py:410-427` — stay in `_doctor_endpoint`);
   - otherwise, with `profile = NVIDIA_BF16 if choice.backend is Backend.VLLM else PORTABLE` and
     `s = _model_selection(config, profile)`: the lines
     `f"backend: {choice.backend.value} ({choice.reason})"`, `f"selected: {s['model']} ({s['reason']})"`,
     then, when `profile.filename is None`,
     `"installed: through vLLM's own Hugging Face cache (doctor does not check it)"`; else
     `(cache or ModelCache()).installed(profile)` → `f"installed: {path}"`, or `None` →
     `"installed: no"` and `"fix: qwenloop model install --profile portable"`.

   `doctor` (`cli/app.py:531-532`) echoes each of these lines right after `choice = _select(config)`
   and before its existing branches. Doctor's exit codes do not change: it still exits 0 when a run
   could start its server binary, 1 when not, and never downloads anything.
6. `_model_selection(config, profile)` is split-383-4's helper:
   `{"model": config.model, "reason": config.model_reason}` for an attached profile, else
   `{"model": profile.name, "reason": f"the managed {profile.backend.value} server loads its pinned profile"}`.
   `config.model_reason` is set by `_load_config` (split-383-4).

## Where to change
- `src/qwenloop/infrastructure/model_cache.py` — behaviour 1.
- new `src/qwenloop/infrastructure/interfaces/model_cache_interface.py` (line 1 is the provenance
  comment copied from line 1 of `src/qwenloop/infrastructure/interfaces/settings_interface.py`) and
  `src/qwenloop/infrastructure/interfaces/__init__.py` — behaviour 2.
- `src/qwenloop/cli/app.py` — behaviours 3-5 (`edit_file` only; the file is far over 100 lines).
  Add `Callable` to a `collections.abc` import, `ModelEntry` to the `qwenloop.domain.catalogue`
  import split-383-4 added, and `ModelCacheInterface` from `qwenloop.infrastructure.interfaces`.
- Tests: append to `tests/test_model_cache.py` and `tests/test_cli.py` (new imports go into each
  file's top import block with `edit_file`, never below code).

Why more than one source file: the pin check belongs to the cache (and ModelCache gains the
interface it lacked, 9.b), while the report belongs to the CLI composition.

## Acceptance criteria
- [ ] `ModelCache.verify` refuses a file whose digest is not the pinned one, with the message of
      behaviour 1; `installed` answers without hashing.
- [ ] `qwenloop model verify nope` exits 2 naming the known entries; `--backend vllm` exits 2.
- [ ] `_verify_entry` passes when every pin checks out, and reports the missing, the corrupt and the
      unserved with their fix lines, per the tests below.
- [ ] `qwenloop doctor --backend llama.cpp` prints `backend: llama.cpp (explicit configuration)` and
      `selected: qwen2.5-coder-14b-q5-k-m (`.
- [ ] Every existing test in `tests/test_cli.py` and `tests/test_model_cache.py` passes unedited.
- [ ] The qwen suite passes at its 100% floor; mypy --strict, lint-imports, bandit and ruff are clean.
- [ ] No new test patches an import or a module/class attribute, or reaches the network.

## Tests to write first (TDD)
Appended to `tests/test_model_cache.py` (its `Response` class answers the injected `opener`):
- `test_verify_checks_the_pinned_digest_too` — `content = b"model bytes"`; install
  `replace(PORTABLE, size=len(content), sha256=None)` through
  `ModelCache(tmp_path, opener=lambda *_a, **_k: Response(content))`; then `verify` of the same
  profile with `sha256="0" * 64` raises `ValueError` matching `"pinned catalogue digest"`, and with
  `sha256=hashlib.sha256(content).hexdigest()` returns the installed path.
- `test_installed_is_a_cheap_presence_check` — `installed(profile)` is `None` before the install and
  the file path after it; `installed(NVIDIA_BF16) is None`.
- `test_model_cache_satisfies_its_interface` — `isinstance(ModelCache(tmp_path), ModelCacheInterface)`.

Appended to `tests/test_cli.py` (helpers called directly with their seams: `cache=ModelCache(tmp_path, opener=...)`,
`served=` a small callable; the file's `_Body` class serves the opener; entries are
`ModelEntry(...)` values built in the test with `family="t"`, `license_spdx="Apache-2.0"`,
`license_osi=True`, `min_ram_gib=8`, `context_window=8192`, `evidence="e"`, `recorded="2026-09-22"`):
- `test_verify_names_the_known_entries_for_an_unknown_one` —
  `runner.invoke(app, ["model", "verify", "nope"])`: `exit_code == 2`, and the output contains
  `"unknown catalogue entry 'nope'"` and `"gpt-oss-20b"`.
- `test_verify_refuses_an_unknown_backend` — `["model", "verify", "gpt-oss-20b", "--backend", "vllm"]`:
  `exit_code == 2`, output contains `"--backend must be all, llama.cpp or ollama"`.
- `test_verify_entry_passes_when_every_pin_checks_out(tmp_path)` — a GGUF
  `replace(PORTABLE, name="t-q", size=len(content), sha256=hashlib.sha256(content).hexdigest())`
  installed into `ModelCache(tmp_path, opener=...)`; entry `t` with `ollama=OllamaArtifact("t:1")`,
  that GGUF and `unverified=("llama.cpp",)`; `_verify_entry(entry, QwenConfig(), cache=cache, served=lambda tag: tag)`
  → `ok is True`, and the lines are `f"llama.cpp: t-q ok ({path})"`,
  `"ollama: t:1 served by http://127.0.0.1:11434/v1"`, `"llama.cpp: never load-tested for t (unverified)"`.
- `test_verify_entry_reports_the_missing_with_their_fixes(tmp_path)` — an empty
  `ModelCache(tmp_path)` and `served` raising `RuntimeError("down")` → `ok is False`; lines include
  `"llama.cpp: t-q not installed"`, `"fix: none yet: qwenloop model install installs the portable profile only"`,
  `"ollama: t:1 not served: down"`, `"fix: ollama pull t:1"`. With the entry's GGUF named
  `PORTABLE.name` instead, the fix line is `"fix: qwenloop model install --profile portable"`.
- `test_verify_entry_fails_a_file_that_is_not_the_pin(tmp_path)` — install with `sha256=None`, then
  verify an entry whose GGUF carries `sha256="0" * 64` → `ok is False` and a line starting
  `"llama.cpp: t-q FAILED: installed model digest does not match the pinned catalogue digest"`.
- `test_verify_entry_checks_one_backend_when_asked(tmp_path)` — an entry with only a (installed)
  GGUF: `backend="ollama"` → `ok is False` with `"ollama: t pins no Ollama tag"`; `backend="all"`
  → `ok is True` with the same informational line; `backend="llama.cpp"` never calls `served` (a
  `served` that raises `AssertionError` proves it).
- `test_doctor_reports_the_managed_model_and_its_fix(tmp_path)` —
  `_doctor_model_lines(replace(QwenConfig(), model_reason="r"), BackendChoice(Backend.LLAMA_CPP, "portable backend for this hardware"), cache=ModelCache(tmp_path))`
  equals `["backend: llama.cpp (portable backend for this hardware)", "selected: qwen2.5-coder-14b-q5-k-m (the managed llama.cpp server loads its pinned profile)", "installed: no", "fix: qwenloop model install --profile portable"]`;
  after writing `tmp_path / "models" / PORTABLE.name / PORTABLE.filename` and `installed.json` beside
  it, the third line is `f"installed: {that file}"` and there is no fix line.
- `test_doctor_reports_the_endpoint_model_and_why` —
  `_doctor_model_lines(replace(QwenConfig(), model_reason="r"), BackendChoice(Backend.OPENAI_COMPAT, "x")) == ["selected: gpt-oss:20b (r)"]`.
- `test_doctor_reports_vllm_without_checking_its_cache` — a `Backend.VLLM` choice → the second line
  is `"selected: qwen2.5-coder-14b-bf16 (the managed vllm server loads its pinned profile)"` and the
  third starts `"installed: through vLLM's own Hugging Face cache"`.
- `test_doctor_names_the_selected_model` — `runner.invoke(app, ["doctor", "--backend", "llama.cpp"])`:
  stdout contains `"backend: llama.cpp (explicit configuration)"` and
  `"selected: qwen2.5-coder-14b-q5-k-m ("` (the exit code depends on the machine's `llama-server`
  and is not asserted).

## Checks the lane must run (all must pass)
```bash
cd src/vibey_runners/qwen
python -c "import qwenloop, vibey_runners.common.infrastructure.memory_probe" || { python -m pip install -e ../common && python -m pip install -e ".[dev]"; }
python -m pytest -q -p no:cacheprovider --no-cov tests/test_model_cache.py tests/test_cli.py
python -m pytest -q -p no:cacheprovider          # whole suite, 100% branch floor from addopts
python -m mypy --strict src/qwenloop
lint-imports
python -m bandit -q -r src/qwenloop
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat
```

## Out of scope
- vibey's own doctor line for the model: the installer wave's `installer-doctor` lane owns it.
- `qwenloop model install` for catalogue GGUFs other than the portable profile, and the
  `LICENSE.txt` text `ModelCache.install` writes (`model_cache.py:69-72`).
- `model list` and `model inspect` (they keep reading `PROFILES`), and doctor's exit codes.
- Asking Ollama's native `/api/tags`: the attached server's `check()` (`inference.py:399-428`)
  already reads the served list (`/v1/models`, with Ollama's implicit `:latest`), so it is reused
  (10.e) rather than a second reader added.
- The catalogue data, the selector and its reason (split-383-1, split-383-4), reasoning parsing
  (split-383-5).
- `tests/conftest.py`, `tests/fakes.py`: do not edit them.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs, or change git remotes. Commit locally as this spec's title.

## Conventions this lane relies on (everything needed is here)
**C1, the shapes.** From split-383-1 (`src/qwenloop/domain/catalogue.py`): `OllamaArtifact(tag)`;
`ModelEntry(name, family, total_params_b, active_params_b, license_spdx, license_osi, min_ram_gib, context_window, ollama, gguf, evidence, recorded, unverified=())`;
`ModelCatalogue()` with `get(name)` raising
`KeyError("unknown catalogue entry 'x'; known: a, b, ...")`. `ModelProfile(name, backend, repository, revision, filename, sha256, size, quantization, context_window=32_768)`
(`src/qwenloop/domain/model.py:36-46`); `BackendChoice(backend, reason)` (`model.py:76-79`).
`PORTABLE` (name `qwen2.5-coder-14b-q5-k-m`, filename `qwen2.5-coder-14b-instruct-q5_k_m.gguf`) and
`NVIDIA_BF16` (name `qwen2.5-coder-14b-bf16`, filename `None`) in `infrastructure/profiles.py`.
`OpenAICompatServer.check()` returns the served model id or raises `RuntimeError` naming what is
wrong; `_attach(config)` builds one for `config.endpoint_url` (default `http://127.0.0.1:11434/v1`).

**C2, tests.** Focused runs need `--no-cov`. Substitute only at declared seams: `cache=`, `served=`,
`ModelCache(root, opener=...)`. Never `monkeypatch.setattr` an import or a module/class attribute
(the existing tests that do are left exactly as they are), never `mock.patch`, `MagicMock` or
`AsyncMock`. No test reaches the network or a live Ollama: the conftest autouse fixtures
`isolated_settings` (a temporary config file, no `QWENLOOP_*` endpoint variables,
`QWENLOOP_MODEL_BY_MEMORY=0` from split-383-4) and `no_local_ollama` keep a developer's machine out.

**Depends on:** split-383-1-model-catalogue, split-383-4-ram-tier-selection
- split-383-1-model-catalogue: `ModelCatalogue`, `ModelEntry`, `OllamaArtifact` and the entries `model verify <entry>` reports on.
- split-383-4-ram-tier-selection: `_model_selection(config, profile)`, `config.model_reason` set by `_load_config`, the `qwenloop.domain.catalogue` import in `cli/app.py`, and the conftest's `QWENLOOP_MODEL_BY_MEMORY=0`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
