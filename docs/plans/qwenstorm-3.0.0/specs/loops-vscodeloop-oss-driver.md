## Title
feat(vscodeloop): drive a Code - OSS agent session headlessly on a local model

ADR-0046 lane L20h — the ADR's lane L20, "the Code - OSS driver" (slug `loops-vscodeloop-oss-driver`).

## Why
ADR-0046 §8 (`specs/ADR-two-loops.md:276`, `:279-283`): for `vscode` "the runner writes
per-run editor settings that pin one local OpenAI-compatible provider at `VIBEY_OLLAMA_URL`,
serving the routed model", and "the editor driver sits behind a port. Lane L20, the Code - OSS
driver, is **gated** on the recorded verification V-VS1 to V-VS5." The port and the runner exist
(lane `loops-vscodeloop-runner`); the CLI's default driver is still `UnconfiguredDriver`
(lane `loops-vscodeloop-cli`). This lane implements the one real driver, **exactly** as the
spike recorded it (lane `loops-vscode-spike`), and makes it the CLI's default.

This spec cannot name the extension, the command line or the event source: they are the
spike's recorded findings, and asserting them here would be the kind of claim sub-doctrine 10.f
forbids. It names everything else exactly, and where it defers to the recording it says which
line of the recording to copy.

## Required behaviour
0. **Gate (ADR-0046 §8, CDD bounded divergence).** Before any edit run
   `grep -n "V-VS VERDICT: FEASIBLE" STORM/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
   If nothing matches, change nothing and report `gated: V-VS verdict is not FEASIBLE`.
   Then read the section `## Verification recorded (V-VS1..V-VS5, V-CC1)` of that file and the
   evidence files it names under `STORM/evidence/vscode/`.
   Copy into your commit body: the V-VS1 command line, the V-VS2 extension id and version, the
   `settings-local.json` shape, the V-VS4 event source and mapping. If the "Driver contract for
   lane L20h" line is missing or names an event source other than the three below, stop and report.
1. **Already present** (lane `loops-vscodeloop-editor-settings`): `EditorSettingsWriter`
   (`vscodeloop/infrastructure/editor_settings.py`) and the launcher seam
   `EditorProcessLauncherInterface` with its default `PopenEditorLauncher`
   (`vscodeloop/infrastructure/editor_process.py`). Use them; do not change them.
2. **Driver** — `vscodeloop/infrastructure/codeoss_driver.py` (+ interface
   `infrastructure/interfaces/codeoss_driver_interface.py`):
   ```python
   class CodeOssDriver:  # implements EditorDriverInterface
       def __init__(self, *, runs_root: Callable[[Path, str], Path],
                    settings_writer: EditorSettingsWriterInterface,
                    launcher: EditorProcessLauncherInterface,
                    events: EditorEventSourceInterface) -> None
   ```
   - `start(...)`: `user_data = runs_root(workdir, session_id or <new uuid4>)/"editor"/"user-data"`;
     `settings_writer.write(user_data, settings)`; write the prompt to
     `<user_data>/../prompt.md`; `launcher.launch(argv, env, cwd=workdir)` with `argv` built from the
     recorded V-VS1 command template, substituting only `{editor}`, `{workdir}`,
     `{user_data_dir}`, `{prompt_file}` (and `{extension}` when the template names one) — never
     a shell string, always an argv list; `env` = `os.environ` minus every `*_PROXY`/`*_proxy`
     variable for a sovereign run (V-VS3: the only host contacted is the local provider).
     Returns a `CodeOssSession(session_id, process, user_data_dir)`.
   - `events(session)`: yields `DriverEvent`s from `self._events.read(session)`, translated by
     the recorded V-VS4 mapping into the port's kinds (`turn.starting`, `turn.completed`, `text`,
     `tool`, `capacity`, `error`). A source event the mapping does not name is dropped and logged
     at debug. The iterator ends when the source ends and the process has exited; a non-zero
     exit without a terminal source event yields `DriverEvent("error", text=<stderr tail>, payload={"misconfigured": False})`.
   - `send(session, text)`: through the recorded mechanism, or raises
     `NotImplementedError("the recorded driver contract has no mid-run prompt")` if the recording
     says there is none (then `MID_RUN_PROMPT` must come out of the `vscode` descriptor's
     capabilities: say so in the report and do not edit vibey here).
   - `stop(session)`: `os.killpg(pgid, SIGTERM)`, wait `kill_grace_seconds` (constructor arg,
     default 5.0), then `SIGKILL`, ignoring `ProcessLookupError` at each step
     (parity-p1 behaviour 8). The process is started with `start_new_session=True`.
3. **Event source** — exactly one implementation of
   `EditorEventSourceInterface.read(session) -> Iterator[Mapping[str, object]]`, chosen by the
   recording: `LogFileEventSource` (tails a file the extension writes, path recorded),
   `StdoutJsonEventSource` (reads JSON lines from the editor process's stdout), or
   `SocketEventSource` (reads JSON lines from a Unix socket in `user_data_dir`). Put it in
   `vscodeloop/infrastructure/editor_events.py`.
4. **Default driver** — `vscodeloop/cli/seams.py`: `DEFAULT_SEAMS.driver` becomes a factory
   building `CodeOssDriver` with `EditorSettingsWriter.from_recording(<package data editor_settings.json>)`,
   `PopenEditorLauncher()` and the recorded event source.
   `UnconfiguredDriver`/`RaisingDriver` stay (the CLI's settings-error path uses them).

## Where to change
- New: `vscodeloop/infrastructure/codeoss_driver.py`, `editor_events.py` and their interfaces
  under `vscodeloop/infrastructure/interfaces/`.
- Edit: `vscodeloop/cli/seams.py` (the default driver factory only).
- New tests: `src/vibey_runners/vscode/tests/test_codeoss_driver.py` (+ a scripted fake editor
  script written into `tmp_path` by the test itself).

## Acceptance criteria
- [ ] The launched argv is exactly the recorded template with the four substitutions, as a list.
- [ ] A sovereign run's environment has no proxy variable.
- [ ] A scripted source emitting the recorded sample (`evidence/vscode/v-vs4-events-<os>.txt`, copied into `tests/data/`) yields the mapped `DriverEvent`s in order, and the runner turns them into `run.started … finished`.
- [ ] A non-zero editor exit with no terminal event yields an `error` event, and the run fails with exit 1.
- [ ] `stop` sends SIGTERM to the process group, then SIGKILL after the grace.
- [ ] `@pytest.mark.integration test_real_editor_session` runs the real editor when `VSCODELOOP_TEST_EDITOR` (the binary) and `VSCODELOOP_TEST_BASE_URL` are set, and is skipped otherwise; it asserts the session finishes with the marker on a two-line task.
- [ ] Tenant suite at 100% branch coverage (the integration test excluded); mypy strict, lint-imports, bandit pass.

## Tests to write first (TDD)
`src/vibey_runners/vscode/tests/test_codeoss_driver.py`:
- `test_argv_is_the_recorded_template_as_a_list`
- `test_sovereign_env_drops_proxy_variables`
- `test_recorded_event_sample_maps_to_driver_events` (reads `tests/data/v-vs4-events.txt`)
- `test_unmapped_source_events_are_dropped`
- `test_nonzero_exit_without_a_terminal_event_is_an_error`
- `test_stop_terminates_the_process_group_then_kills`
- `test_default_seams_build_the_codeoss_driver`
- `test_driver_classes_satisfy_their_interfaces`
- `test_real_editor_session` (`@pytest.mark.integration`)

## Checks the lane must run (all must pass)
    cd src/vibey_runners/vscode && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q -m "not integration"
    cd src/vibey_runners/vscode && mypy --strict src/vscodeloop && lint-imports && bandit -q -r src/vscodeloop
    uv run ruff check . && uv run ruff format --check .

On the operator's machines (evidence, recorded in the commit body; not a CI gate):
    VSCODELOOP_TEST_EDITOR=codium VSCODELOOP_TEST_BASE_URL=http://127.0.0.1:11434/v1 python -m pytest -q -m integration tests/test_codeoss_driver.py

## Out of scope
- The OSS-build and loopback-provider checks (`loops-vscodeloop-doctor`).
- vibey's endpoint overlay and pool membership (`loops-vscode-vibey-wiring`).
- Installing the editor or the extension (`installer-vscode`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-vscodeloop-editor-settings`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
