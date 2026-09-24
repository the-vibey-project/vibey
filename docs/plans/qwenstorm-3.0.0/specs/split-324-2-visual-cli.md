<!-- split of #324: child 2 of 2; audit: issue-audit/updates/324.md -->
## Title
feat(cli)!: VISUAL_DESIGN follows --provider, and every provider but scripted runs it on the local model

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:120-194`) keeps the sovereign loop "always
on, never needing declaration, for every phase" (line 131), and a declared paid platform "relays
through the sovereign host rather than replacing it" (line 181). Lane `split-324-1-visual-provider`
adds `QwenloopVisualProvider`, but nothing calls it: `vibey work` still refuses every provider but
scripted in VISUAL_DESIGN and runs the scripted fake when none is given
(`src/vibey/cli/main.py:406-422`), and `vibey worker` hard-wires the fake for every provider
(`src/vibey/cli/main.py:1703`), so a `--provider qwenloop` worker quietly writes a scripted
inventory. Since #322, DESIGN and DECOMPOSE resolve their provider with the one-argument
`_resolve_provider(explicit)` (`cli/main.py:380-390`), which defaults to `qwenloop`. This lane makes
VISUAL_DESIGN follow the same resolver through one module-level rule that `work` and `worker` both
call, so the two commands cannot disagree, and so under qwenloop DESIGN, DECOMPOSE and VISUAL_DESIGN
share one client, one server and one model (8.c, one instance per model, doctrines.md:202).

## Required behaviour
1. A new module-level function in `src/vibey/cli/main.py`:
   `_visual_provider(provider: str, *, ollama_model: str | None, chat: OllamaChatClientInterface | None = None) -> VisualInventoryProducer`.
   Its docstring states why it is module-level (like `_resolve_provider`, so `work` and `worker`
   cannot disagree).
   - `"scripted"` returns `ScriptedVisualProvider()` and never contacts the model.
   - Every other member of `_PROVIDERS` (`cli/main.py:365`) returns
     `QwenloopVisualProvider.from_environment(os.environ, chat=client)`, where `client` is the
     `chat` passed in, or else `OllamaChatClient.from_environment(os.environ, model=ollama_model)`.
     8.b: a declared paid provider relays through the sovereign host, and no paid visual producer
     exists, so the paid providers run VISUAL_DESIGN on the local model rather than failing.
   - Any other string raises `UnknownProvider(_UNKNOWN_PROVIDER)` (`cli/main.py:367-371`), never a
     hand-written message. The text is
     `provider must be 'scripted', 'claudeloop', 'qwenloop', or 'opencode'`.
2. `vibey work` on a VISUAL_DESIGN project builds its visual worker with
   `provider=_visual_provider(_resolve_provider(provider_opt), ollama_model=ollama_model)`. With no
   `--provider`, VISUAL_DESIGN now runs on the local model (BREAKING: it was the scripted fake).
   `--provider scripted` keeps the old behaviour. `--provider claudeloop` no longer exits non-zero;
   it runs the phase on the local model. An unknown provider exits 3 with the text in behaviour 1.
3. `vibey worker` declares `chat: OllamaChatClientInterface | None = None` before its provider
   branch; the qwenloop branch keeps assigning its one shared client to `chat`
   (`cli/main.py:1604`). `build_full_worker` receives
   `visual_provider=_visual_provider(provider, ollama_model=ollama_model, chat=chat)`, so under
   qwenloop VISUAL_DESIGN reuses DESIGN's and DECOMPOSE's client, and the scripted fake is used only
   under `--provider scripted`.
4. `_OLLAMA_MODEL_HELP` (`cli/main.py:361-363`) says the model also serves VISUAL_DESIGN under every
   provider but scripted, and still names `$VIBEY_OLLAMA_MODEL`, the default model and
   `$VIBEY_OLLAMA_URL`.
5. `ScriptedVisualProvider()` is constructed in exactly one place in `cli/main.py`: inside
   `_visual_provider`.
6. Nothing else changes: `_resolve_provider`, `_PROVIDERS`, `_UNKNOWN_PROVIDER` and `_PROVIDER_HELP`
   keep their text; DESIGN/DECOMPOSE selection is untouched.

## Where to change
Line numbers are from the storm integration branch at `4317cff6`. If lane `engines-pool` (#321) has
landed on the integration branch when this lane starts, rebase over it first: it also edits the
`worker` command in `cli/main.py` (and `bootstrap.py`), so every line below may have moved; search
for the quoted text. Work bottom-up in `src/vibey/cli/main.py` (1761 lines: use `edit_file` only).

1. **Line 1703**, inside the `build_full_worker(` call in `worker`'s `run_worker`: replace
   `                    visual_provider=ScriptedVisualProvider(),` with
   `                    visual_provider=_visual_provider(provider, ollama_model=ollama_model, chat=chat),`.
   (Line length is enforced by `ruff format`; run it afterwards.)
2. **After line 1575** (`            decomposer: WorkPlanProducer`), add:
   ```python
               # The qwenloop branch fills this with its one shared client, and VISUAL_DESIGN
               # reuses it (8.c: one server, one model); every other branch leaves it None.
               chat: OllamaChatClientInterface | None = None
   ```
   Line 1604 (`chat = OllamaChatClient.from_environment(os.environ, model=ollama_model)`) stays as
   it is.
3. **Lines 406-422**, the VISUAL_DESIGN block in `_work_once`, from
   `        if project.phase is Phase.VISUAL_DESIGN:` through its
   `            return await worker.run_once(project_id)`: replace the whole block with
   ```python
           if project.phase is Phase.VISUAL_DESIGN:
               # 8.b: VISUAL_DESIGN follows --provider through the resolver DESIGN uses, so with
               # no --provider it runs on the local model; `_visual_provider` is the one rule
               # `worker` applies too.
               worker = build_visual_worker(
                   resources=resources,
                   provider=_visual_provider(
                       _resolve_provider(provider_opt), ollama_model=ollama_model
                   ),
                   owner=owner,
                   project=project,
               )
               return await worker.run_once(project_id)
   ```
   (The `visual_provider: VisualInventoryProducer` local and the `WrongPhase("no live
   VisualInventoryProducer ...")` raise go away; `WrongPhase` stays imported for its other uses.)
4. **After line 390** (the end of `_resolve_provider`), add:
   ```python
   def _visual_provider(
       provider: str,
       *,
       ollama_model: str | None,
       chat: OllamaChatClientInterface | None = None,
   ) -> VisualInventoryProducer:
       """The VISUAL_DESIGN producer for a resolved --provider.

       Sub-doctrine 8.b keeps the sovereign loop on for every phase, and a declared paid
       provider relays through the sovereign host rather than replacing it. No paid visual
       producer exists, so every provider but the scripted fake runs VISUAL_DESIGN on the
       local model. Module-level, like `_resolve_provider`, so `work` and `worker` cannot
       disagree; `worker` passes its shared client so DESIGN, DECOMPOSE and VISUAL_DESIGN use
       one server and one model (8.c).
       """
       if provider == "scripted":
           return ScriptedVisualProvider()
       if provider not in _PROVIDERS:
           raise UnknownProvider(_UNKNOWN_PROVIDER)
       client = (
           chat
           if chat is not None
           else OllamaChatClient.from_environment(os.environ, model=ollama_model)
       )
       return QwenloopVisualProvider.from_environment(os.environ, chat=client)
   ```
5. **Lines 361-363**: set `_OLLAMA_MODEL_HELP` to
   ```python
   _OLLAMA_MODEL_HELP = (
       "Local model for --provider qwenloop, and for VISUAL_DESIGN under every provider but "
       f"scripted; ignored otherwise. Default: ${OLLAMA_MODEL_ENV}, else {DEFAULT_OLLAMA_MODEL}. "
       f"The server is ${OLLAMA_URL_ENV}."
   )
   ```
6. **Imports.** After line 65 (the `)` closing
   `from vibey.infrastructure.engines.claudeloop_process import (`), add
   `from vibey.infrastructure.engines.interfaces import OllamaChatClientInterface`. After line 73
   (`from vibey.infrastructure.engines.qwenloop_design import QwenloopDesignProvider`), add
   `from vibey.infrastructure.engines.qwenloop_visual import QwenloopVisualProvider`. Both positions
   are already isort order. `UnknownProvider`, `ScriptedVisualProvider`, `VisualInventoryProducer`,
   `OllamaChatClient` and `os` are already imported. Then run
   `uv run ruff format src/vibey/cli/main.py` and `uv run ruff check src/vibey/cli/main.py`.
7. **Tests** (see below): `tests/cli/test_visual_provider_selection.py` (new, default tier),
   `tests/cli/test_sovereign_provider_options.py` (edit; integration tier, PostgreSQL) and
   `tests/cli/test_operational_commands.py` (edit lines 620-632; integration tier). Why three test
   files for one source file: the two integration files hold tests that assert the old behaviour
   (`claudeloop` refused in VISUAL_DESIGN, a scripted default), and they fail or lie unless changed
   here.

## Acceptance criteria
- [ ] `grep -n "ScriptedVisualProvider()" src/vibey/cli/main.py` prints exactly one line, inside
      `_visual_provider` (and `test_only_the_one_rule_builds_the_scripted_visual_producer` passes).
- [ ] `tests/cli/test_visual_provider_selection.py` passes with no service running (with
      `--noconftest -n 0` until `fakes-harness-decouple` lands): scripted stays scripted; qwenloop
      and claudeloop run on the local model; the sovereign default does too; the worker's shared
      client is reused; the chosen model reaches the client; the environment sets the attempts; an
      unknown provider raises `UnknownProvider`; `work` and `worker` both call the one rule.
- [ ] After the focused selection run with coverage (Checks, step "selection coverage"), no line of
      `_visual_provider` appears in the `Missing` column of
      `uv run coverage report -m --include='src/vibey/cli/main.py'`.
- [ ] Integration tier (PostgreSQL 17): `test_the_visual_phase_runs_on_the_local_model_by_default`,
      `test_an_explicit_paid_provider_still_runs_visual_design_on_the_local_model`,
      `test_scripted_visual_design_never_asks_the_local_model`,
      `test_the_worker_runs_visual_design_on_the_shared_local_client` and
      `test_work_once_visual_phase_rejects_an_unknown_provider` pass;
      `test_the_visual_phase_keeps_the_scripted_default_when_local_engines_are_on` no longer exists.
- [ ] `tests/cli/test_main_integration.py` passes unedited (its visual flow already passes
      `--provider scripted`).
- [ ] No new `patch`, `patch.dict`, `AsyncMock` or `MagicMock` site:
      `git diff -U0 tests | grep -E "^\+.*([^a-z]patch\(|patch\.dict|AsyncMock|MagicMock)"`
      prints nothing (`monkeypatch.setenv(` does not match; it is allowed).
- [ ] `git diff --stat` names only `src/vibey/cli/main.py` and the three test files.
- [ ] All checks below pass, including 100% branch coverage for `src/vibey/cli/*`.

## Tests to write first (TDD)
**`tests/cli/test_visual_provider_selection.py`** (new; default tier: no database, no network, no
marker, nothing patched). Imports: `ast`, `from pathlib import Path`, `pytest`,
`import vibey.cli.main as cli_main`,
`from vibey.cli.main import _UNKNOWN_PROVIDER, _resolve_provider, _visual_provider`,
`from vibey.domain.errors import UnknownProvider`,
`from vibey.infrastructure.engines.ollama_chat import DEFAULT_OLLAMA_MODEL, OllamaChatClient`,
`from vibey.infrastructure.engines.qwenloop_visual import QwenloopVisualProvider`,
`from vibey.infrastructure.engines.scripted_visual import ScriptedVisualProvider`, and `re`.
An autouse fixture clears inherited settings:
```python
@pytest.fixture(autouse=True)
def _no_inherited_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("VIBEY_OLLAMA_URL", "VIBEY_OLLAMA_MODEL", "VIBEY_OLLAMA_TIMEOUT",
                 "VIBEY_VISUAL_MAX_ATTEMPTS"):
        monkeypatch.delenv(name, raising=False)
```
Structural helpers (the pattern of `tests/test_bootstrap.py:116-142`, which walks the composition
root's AST instead of counting text):
```python
def _calls_in(name: str) -> list[tuple[ast.Call, str]]:
    """Every call to `name` in cli/main.py, each with the innermost function it sits in."""
    tree = ast.parse(Path(cli_main.__file__).read_text(encoding="utf-8"))
    found: dict[int, tuple[ast.Call, str]] = {}
    for function in ast.walk(tree):  # breadth-first, so an inner function is seen last
        if isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            for node in ast.walk(function):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == name
                ):
                    found[id(node)] = (node, function.name)
    return list(found.values())


def _keyword(call: ast.Call, name: str) -> ast.expr:
    return next(keyword.value for keyword in call.keywords if keyword.arg == name)
```
Tests:
1. `test_scripted_keeps_the_scripted_producer`: `_visual_provider("scripted", ollama_model=None)`
   is an instance of `ScriptedVisualProvider`.
2. `test_every_live_provider_runs_visual_design_on_the_local_model`, parametrized over
   `"qwenloop"` and `"claudeloop"` (never `opencode`: it is repealed): the result is an instance of
   `QwenloopVisualProvider`.
3. `test_the_sovereign_default_runs_visual_design_on_the_local_model`:
   `_visual_provider(_resolve_provider(None), ollama_model=None)` is a `QwenloopVisualProvider`
   whose `._chat` is an `OllamaChatClient` with `.model == DEFAULT_OLLAMA_MODEL`.
4. `test_the_workers_shared_client_is_reused`: with `chat = OllamaChatClient(model="shared:1")`,
   `_visual_provider("qwenloop", ollama_model="other:1", chat=chat)` is a `QwenloopVisualProvider`
   (assert `isinstance` first) whose `._chat is chat`.
5. `test_the_chosen_model_reaches_the_local_client`:
   `_visual_provider("claudeloop", ollama_model="picked:1")._chat.model == "picked:1"` (narrow with
   `isinstance` first).
6. `test_the_environment_sets_the_attempts`: `monkeypatch.setenv("VIBEY_VISUAL_MAX_ATTEMPTS", "5")`;
   `_visual_provider("qwenloop", ollama_model=None).max_attempts == 5`.
7. `test_an_unknown_provider_is_refused`: `_visual_provider("nonexistent", ollama_model=None)`
   raises `UnknownProvider` with `match=re.escape(_UNKNOWN_PROVIDER)`.
8. `test_the_model_help_names_visual_design`: `"VISUAL_DESIGN" in cli_main._OLLAMA_MODEL_HELP`,
   `"VIBEY_OLLAMA_MODEL" in cli_main._OLLAMA_MODEL_HELP` and `"VIBEY_OLLAMA_URL" in cli_main._OLLAMA_MODEL_HELP`.
9. `test_only_the_one_rule_builds_the_scripted_visual_producer`:
   `[function for _, function in _calls_in("ScriptedVisualProvider")] == ["_visual_provider"]`.
10. `test_work_asks_the_one_rule_with_the_resolved_provider`:
    `((call, function),) = _calls_in("build_visual_worker")`; `function == "_work_once"`;
    `provider = _keyword(call, "provider")` is an `ast.Call` whose `func` is `ast.Name(id="_visual_provider")`,
    and its first positional argument is an `ast.Call` whose `func` is `ast.Name(id="_resolve_provider")`.
11. `test_the_worker_asks_the_one_rule_with_its_shared_client`:
    `((call, function),) = _calls_in("build_full_worker")`; `function == "run_worker"`;
    `visual = _keyword(call, "visual_provider")` is an `ast.Call` whose `func` is
    `ast.Name(id="_visual_provider")`, and `{keyword.arg for keyword in visual.keywords} == {"ollama_model", "chat"}`.

**`tests/cli/test_sovereign_provider_options.py`** (edit; integration tier: `pytestmark =
pytest.mark.integration` at line 32, real HTTP `FakeOllama` at lines 78-110, PostgreSQL through the
autouse `_use_test_database`). Use `edit_file`; do not rewrite the file.
- In `_sovereign_env` (lines 126-138), add `"VIBEY_VISUAL_MAX_ATTEMPTS",` to the tuple of names it
  deletes (after `"VIBEY_EVIDENCE_DIR",`).
- After `_rows` (ends line 213), add:
  ```python
  VISUAL_ANSWER: dict[str, object] = {
      "surfaces": [
          {
              "screen_id": "greeting",
              "name": "Greeting",
              "action": "create",
              "responsive_states": ["mobile", "desktop", "error"],
              "accessibility_requirements": ["keyboard navigable"],
              "media_manifest": [
                  {"asset_key": "hero", "modality": "image", "prompt": "a friendly wave"}
              ],
          }
      ]
  }


  async def _seed_visual(tmp_path: Path) -> UUID:
      """A VISUAL_DESIGN project with its visual.inventory job, enqueued exactly as
      DesignAcceptanceService._enqueue_visual_inventory does (application/design_acceptance.py:92-104)."""
      async with build_app() as resources:
          project = await resources.projects.create("visual", tmp_path, max_cycles=1, config={})
          project = await resources.projects.transition(
              project.project_id, expected=Phase.INTAKE, to=Phase.VISUAL_DESIGN
          )
          await resources.jobs.enqueue(
              EnqueueRequest(
                  project_id=project.project_id,
                  cycle=project.cycle,
                  phase=Phase.VISUAL_DESIGN,
                  kind="visual.inventory",
                  idempotency_key=idempotency_key(
                      project.project_id, project.cycle, "visual.inventory", "interactive"
                  ),
                  requirement={"effort": "high"},
              )
          )
          return project.project_id


  async def _job_states(project_id: UUID, kind: str) -> list[str]:
      """The states of this project's `kind` jobs in its current cycle, oldest first, read
      through the job repository rather than new SQL."""
      async with build_app() as resources:
          project = await resources.projects.get(project_id)
          assert project is not None
          jobs = await resources.jobs.list_for_cycle(project_id, cycle=project.cycle, kind=kind)
          return [str(job.state) for job in jobs]
  ```
- Delete `test_the_visual_phase_keeps_the_scripted_default_when_local_engines_are_on` (lines
  376-395, from its `@pytest.mark.usefixtures("_sovereign_env")` line through
  `    assert "no ready job" in res.output`) and put these four tests in its place. Each sets the
  endpoint with `monkeypatch.setenv("VIBEY_OLLAMA_URL", ollama.url)` inside the `with FakeOllama(...)`
  block: never `patch.dict`, and no new `patch`/`AsyncMock` site.
  1. `test_the_visual_phase_runs_on_the_local_model_by_default(tmp_path, monkeypatch)`,
     `@pytest.mark.usefixtures("_sovereign_env")`, with no feature switch (like
     `test_work_is_sovereign_by_default_with_no_local_switch`, lines 453-466):
     `project_id = asyncio.run(_seed_visual(tmp_path))`; with `FakeOllama(VISUAL_ANSWER)` running,
     `runner.invoke(app, ["work", str(project_id)])`. Assert `res.exit_code == 0, res.output`,
     `"processed one job" in res.output`, exactly one request (`((request,),) = [ollama.requests]`)
     with `request["path"] == "/api/chat"`, `request["model"] == "gpt-oss:20b"` and
     `request["format"]["properties"]["surfaces"]["items"]["properties"]["action"]["enum"] == ["create", "update"]`
     (add `# type: ignore[index]` as line 234 does);
     `asyncio.run(_job_states(project_id, "visual.inventory")) == ["succeeded"]`;
     `len(asyncio.run(_job_states(project_id, "visual.plan"))) == 1`; and
     `"greeting" in next(tmp_path.glob(".vibey/runs/*/visual/inventory.json")).read_text()`.
  2. `test_an_explicit_paid_provider_still_runs_visual_design_on_the_local_model`,
     `_sovereign_env`: `work <id> --provider claudeloop --ollama-model picked:1`. Assert exit 0,
     `[request["model"] for request in ollama.requests] == ["picked:1"]`, and the
     `visual.inventory` state list is `["succeeded"]`. No paid credential is set (the fixture
     deletes them all).
  3. `test_scripted_visual_design_never_asks_the_local_model`, `_sovereign_env`:
     `work <id> --provider scripted` with `FakeOllama(VISUAL_ANSWER)` running. Assert exit 0,
     `ollama.requests == []`, and the `visual.inventory` state list is `["succeeded"]`.
  4. `test_the_worker_runs_visual_design_on_the_shared_local_client`,
     `@pytest.mark.usefixtures("_sovereign_env", "_quiet_worker")` (reuse the existing
     `_quiet_worker` fixture exactly as it is): seed with `_seed_visual`, then
     `runner.invoke(app, ["worker", "--once", "--provider", "qwenloop", "--ollama-model", "sovereign:test"])`.
     Assert exit 0, `"processed one job" in res.output`, one request with
     `model == "sovereign:test"`, and the `visual.inventory` state list is `["succeeded"]`.

**`tests/cli/test_operational_commands.py`** (edit lines 620-632; integration tier). Rename
`test_work_once_visual_phase_rejects_non_scripted_provider` to
`test_work_once_visual_phase_rejects_an_unknown_provider`; keep its `seed()` body; invoke
`["work", str(pid), "--provider", "nonexistent"]`; replace `assert res.exit_code != 0` with
`assert res.exit_code == 3` and `assert "provider must be" in res.output`. (`claudeloop` no longer
fails in VISUAL_DESIGN; that case is now test 2 above.)

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
test "$(grep -c 'ScriptedVisualProvider()' src/vibey/cli/main.py)" = 1
# Default tier (no service): the rule and the wiring
uv run pytest -q -p no:cacheprovider tests/cli/test_visual_provider_selection.py \
  tests/infrastructure/engines/test_qwenloop_visual.py tests/application/test_interfaces_convention.py
# Selection coverage: every line of _visual_provider is covered by the selection file alone
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= \
  tests/cli/test_visual_provider_selection.py
uv run coverage report -m --include='src/vibey/cli/main.py'
# Integration tier (PostgreSQL 17 reachable)
uv run pytest -q -p no:cacheprovider tests/cli/test_sovereign_provider_options.py \
  tests/cli/test_operational_commands.py tests/cli/test_main_integration.py
# Per-layer 100% branch coverage over the whole suite (the CI gate; PostgreSQL 17 reachable)
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/cli/*' --fail-under=100
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
uv run coverage report --include='src/vibey/application/*' --fail-under=100
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
```
After the selection-coverage report, read its `Missing` column: none of `_visual_provider`'s lines
may be listed (the rest of `main.py` is covered by the integration tier). Run one coverage run at a
time; concurrent runs corrupt `.coverage`. Until lane `fakes-harness-decouple` lands,
`tests/conftest.py:146-156` connects to PostgreSQL at session start even for unit files; if none is
reachable, add `--noconftest -n 0` to the two default-tier commands. The PostgreSQL-backed tests are
never this lane's only proof: the default-tier selection file proves the rule and the wiring.

## Out of scope
- `src/vibey/infrastructure/engines/qwenloop_visual.py` and its interface (lane
  `split-324-1-visual-provider`); `_resolve_provider`'s body, `_PROVIDERS`, `_UNKNOWN_PROVIDER`,
  `_PROVIDER_HELP`; DESIGN/DECOMPOSE selection; `bootstrap.py`; the engine pool (lane `engines-pool`).
- claudeloop/paidloop visual producers, media generation, `visual.prompt` / `visual.review`.
- Routing the sovereign providers through sovereignloop's queue (ADR-0046 section 4's *Flag*).
- `tests/cli/test_main_integration.py`: it passes `--provider scripted` already; do not edit it.
- Docs the docs wave updates: `docs/reference/cli.md` (the `work`/`worker` VISUAL_DESIGN text),
  `docs/plans/phase-protocols.md`, `docs/project.mmd`, ADR-0038 section 9. Do not edit CHANGELOG.md,
  docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees. Do not push, open PRs, or change git
  remotes. Commit locally as
  `feat(cli)!: VISUAL_DESIGN follows --provider, and every provider but scripted runs it on the local model`
  with the footer
  `BREAKING CHANGE: with no --provider, vibey work and vibey worker run VISUAL_DESIGN on the local model (it was the scripted fake); --provider scripted keeps the old behaviour, and --provider claudeloop no longer refuses the phase.`

## Standing constraints
- Substitute only at a declared seam (a function keyword such as `chat=`, the environment through
  `monkeypatch.setenv` / `delenv`). Never `monkeypatch.setattr` an import or a module/class
  attribute, never `mock.patch`/`patch.dict`, `MagicMock` or `AsyncMock` in new code
  (sub-doctrine 9.b). The existing `_quiet_worker` fixture is reused as it is, not copied.
- No new raw SQL: the new integration tests read jobs through `resources.jobs.list_for_cycle`
  (`application/interfaces/queue.py:109-114`), not the file's `_rows` SQL helper.
- The PostgreSQL-backed CLI tests stay in the `integration` tier and are never the lane's only
  proof; the default-tier proof needs no service.
- OpenCode is repealed (8.b): no new test parametrizes or names `opencode`. `_visual_provider` still
  accepts it only because `_PROVIDERS` still lists it; this lane does not change that list.
- Sovereign by default (8.b): the unstated provider runs the phase on the local `gpt-oss:20b`.
- Arch Linux and macOS (8.h): nothing here is platform-specific; the same check block is the proof
  on both.
- Configurable (12.c): the model comes from `--ollama-model` / `VIBEY_OLLAMA_MODEL`, the attempts
  from `VIBEY_VISUAL_MAX_ATTEMPTS`; add no visual-specific model key.
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- Change existing files with `edit_file` (or a checked replacement); never rewrite an existing file
  with `write_file` (`STORM/EDITING-RULES.md`). Line 1 of every new file is the provenance line,
  copied byte for byte from a sibling file.

**Depends on:** split-324-1-visual-provider, engines-provider
- split-324-1-visual-provider: `QwenloopVisualProvider`, its `from_environment(environ, *, chat=None)`,
  `max_attempts`, and `VISUAL_SCHEMA`'s shape (the action enum the integration test reads).
- engines-provider (#322, integrated at `4e57f56b`): the one-argument `_resolve_provider(explicit)`
  that defaults to `qwenloop`, which VISUAL_DESIGN now follows. Also rebase over `engines-pool`
  (#321) if it has landed: both edit the `worker` command in `cli/main.py`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
