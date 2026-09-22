## Title
feat(vscodeloop): per-run editor settings that pin one provider, and the editor launcher seam

ADR-0046 lane L20h1 (slug `loops-vscodeloop-editor-settings`).

## Why
ADR-0046 §8 (`specs/ADR-two-loops.md:276`): "The runner writes per-run editor settings that pin
one local OpenAI-compatible provider at `VIBEY_OLLAMA_URL`, serving the routed model." Its
*Security impact* (`:392`): "vscodeloop's sovereign settings allow only a local provider host. A
paid provider in a sovereign run is refused before any request leaves the machine." The spike
(lane `loops-vscode-spike`) recorded the settings shape that achieves V-VS3 (only the local host
is contacted) as `evidence/vscode/settings-local.json`. This lane writes that file per run, into
a per-run user-data directory so the operator's own editor settings are never read or changed,
and adds the process-launch seam the driver (lane `loops-vscodeloop-oss-driver`) uses, so its
tests inject a scripted editor instead of patching `subprocess` (sub-doctrine 9.b).

## Required behaviour
0. **Gate (ADR-0046 §8, CDD bounded divergence).** Before any edit run
   `grep -n "V-VS VERDICT: FEASIBLE" /private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
   If nothing matches, change nothing and report `gated: V-VS verdict is not FEASIBLE`.
   Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/evidence/vscode/settings-local.json` and
   copy it into the tenant as `src/vibey_runners/vscode/tests/data/settings-local.json`
   (the test fixture). If it is missing, stop and report.
1. **`vscodeloop/infrastructure/editor_settings.py`** (+ `infrastructure/interfaces/editor_settings_interface.py`,
   `EditorSettingsWriterInterface`): `class EditorSettingsWriter` constructed with
   `template: Mapping[str, object]` (the recorded settings object) and `base_url_key: str`,
   `model_key: str`, `provider_key: str | None` (the dotted JSON paths in the template that hold
   the provider URL, the model and — for paid mode — the provider name; the spike's recording
   names them; `from_recording(path: Path) -> EditorSettingsWriter` reads a JSON file of the
   form `{"template": {...}, "base_url_key": "...", "model_key": "...", "provider_key": "..."}`
   shipped as package data `vscodeloop/infrastructure/data/editor_settings.json`, which this
   lane writes from the recording).
   - `write(self, user_data_dir: Path, settings: DriverSettings) -> Path`: deep-copies the
     template, sets `base_url_key` to `settings.base_url` (sovereign) and `model_key` to
     `settings.model`; in paid mode (`settings.provider` set) sets `provider_key` to
     `settings.provider` and, when `settings.base_url` is None, removes the `base_url_key`;
     writes `<user_data_dir>/User/settings.json` atomically (temp + `os.replace`, parents
     created); returns the path. A missing dotted path in the template raises
     `ValueError("<key> is not in the recorded settings template")`.
2. **`vscodeloop/infrastructure/editor_process.py`** (+ `infrastructure/interfaces/editor_process_interface.py`,
   `EditorProcessLauncherInterface`): `launch(self, argv: Sequence[str], env: Mapping[str, str], cwd: Path) -> subprocess.Popen[str]`;
   default `PopenEditorLauncher` calls
   `subprocess.Popen(list(argv), env=dict(env), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)`
   (`# nosec B603` with the reason "argv is a list built from the recorded template; no shell").
   An empty argv raises `ValueError`.
3. **Package data**: tenant `pyproject.toml` includes `src/vscodeloop/infrastructure/data/*.json`
   in the wheel (hatch `force-include` or the default package data rule — verify with
   `python -c "import importlib.resources as r; print(r.files('vscodeloop.infrastructure').joinpath('data/editor_settings.json').is_file())"`);
   register the pytest marker `integration` in `[tool.pytest.ini_options] markers`.

## Where to change
- New: `vscodeloop/infrastructure/editor_settings.py`, `editor_process.py`,
  `infrastructure/interfaces/editor_settings_interface.py`, `editor_process_interface.py`,
  `infrastructure/data/editor_settings.json`, `tests/data/settings-local.json`,
  `tests/test_editor_settings.py`.
- Edit: tenant `pyproject.toml` (package data, the marker).

## Acceptance criteria
- [ ] A sovereign write puts the run's base URL and model at the recorded keys, and nothing else differs from the template.
- [ ] A paid write sets the provider key, and drops the base URL key when no base URL is given.
- [ ] The file lands under the given user-data dir only; `~` is never touched (the test sets `HOME` to `tmp_path/"home"` with `monkeypatch.setenv` and asserts it stays empty).
- [ ] A template missing a named key raises the `ValueError`.
- [ ] `PopenEditorLauncher` starts a scripted child with `start_new_session=True` (the child reports `os.getsid(0) == os.getpid()`), with the given env and cwd.
- [ ] The shipped `editor_settings.json` equals the recording's template (byte-compare the parsed JSON).
- [ ] Tenant suite at 100% branch coverage; mypy strict, lint-imports, bandit pass.

## Tests to write first (TDD)
`src/vibey_runners/vscode/tests/test_editor_settings.py`:
- `test_sovereign_settings_pin_the_local_provider_and_model`
- `test_paid_settings_set_the_provider_and_drop_a_missing_base_url`
- `test_settings_land_in_the_per_run_user_data_dir_only`
- `test_missing_template_key_is_refused`
- `test_shipped_template_is_the_recorded_one`
- `test_launcher_starts_a_new_session_with_env_and_cwd` (a `sys.executable -c` child printing JSON)
- `test_launcher_refuses_an_empty_argv`
- `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/vscode && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q
    cd src/vibey_runners/vscode && mypy --strict src/vscodeloop && lint-imports && bandit -q -r src/vscodeloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The driver, the event source and the default seams (`loops-vscodeloop-oss-driver`).
- The loopback/private provider refusal and the OSS-build check (`loops-vscodeloop-doctor`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-vscodeloop-cli`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
