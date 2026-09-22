## Title
feat(cli): every local-model client the CLI builds ledgers its turns to the project it serves

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`). `gap-ledger-provider-turns-1`
gave `OllamaChatClient` a turn seam and `gap-ledger-provider-turns-2` a recorder over the ledger,
`LedgerModelTurnRecorder`. Neither records anything until the composition passes one in, and the
CLI is where the sovereign clients are built:
- `vibey work`, DESIGN under `qwenloop` (`src/vibey/cli/main.py:449-451`);
- `vibey worker`, the one shared client for DESIGN and DECOMPOSE (`:1604-1606`);
- `_visual_provider` (`split-324-2-visual-cli`), which builds its own client for `vibey work` on a
  VISUAL_DESIGN project and for `vibey worker` under a provider other than `qwenloop`.

A client built without a recorder is a silent omission (7.c), so this lane wires all of them and
adds a test that fails if a later change builds one without.

## Required behaviour
1. In `src/vibey/cli/main.py`, beside `_build_spend_recorder` (`:140-176`), a module-level function
   ```python
   def _sovereign_turns(
       *, ledger: LedgerRepositoryInterface, projects: ProjectStore, project_id: UUID
   ) -> ModelTurnRecorderInterface:
   ```
   returning `LedgerModelTurnRecorder(ledger=ledger, projects=projects, project_id=project_id, engine_id=QwenloopDesignProvider.engine_id)`.
   Its docstring gives the reason it is module-level, as `_build_spend_recorder`'s situation does:
   the commands that build providers are typer functions and three sites share it. It names the
   engine through `QwenloopDesignProvider.engine_id` (`qwenloop_design.py:182`) so the id follows
   the provider (and ADR-0046's rename) rather than a second literal.
2. The `vibey work` DESIGN site becomes
   `OllamaChatClient.from_environment(os.environ, model=ollama_model, turns=_sovereign_turns(ledger=resources.ledger, projects=resources.projects, project_id=project.project_id))`.
3. The `vibey worker` site (`chat = OllamaChatClient.from_environment(...)`) gains the same
   `turns=` keyword.
4. `_visual_provider` gains a keyword `turns: ModelTurnRecorderInterface | None = None`, and its
   fallback becomes `OllamaChatClient.from_environment(os.environ, model=ollama_model, turns=turns)`.
   Its two callers pass `turns=_sovereign_turns(...)` with the same three arguments. (When
   `worker` passes its shared `chat`, that client already carries a recorder and `turns` is unused.)
5. Nothing else in `main.py` changes. `ruff format` the file after editing.

## Where to change
- `src/vibey/cli/main.py` (edit_file only; about 1,760 lines — never `write_file`). Work bottom-up
  so earlier line numbers stay valid; search for the quoted text, since earlier lanes move lines.
- New test file `tests/cli/test_sovereign_turn_wiring.py` (no service).

## Acceptance criteria
- [ ] `grep -n "OllamaChatClient.from_environment(" src/vibey/cli/main.py` lists only calls that
      pass `turns=`, and every `_visual_provider(` call passes `turns=`.
- [ ] `_sovereign_turns(...)` over `InMemoryLedger` and `InMemoryProjectRepository` returns a
      `ModelTurnRecorderInterface`; one `ask` through a client built with it ledgers a
      `TurnRequested` and a `TurnCompleted` naming `QwenloopDesignProvider.engine_id`.
- [ ] `split-324-2`'s tests, `tests/cli/test_main.py` and every CLI test that runs `work` or
      `worker` pass unchanged.
- [ ] 100% branch coverage of `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/cli/test_sovereign_turn_wiring.py` (provenance header on line 1):
- `test_every_local_model_client_the_cli_builds_ledgers_its_turns`: parse `src/vibey/cli/main.py`
  with `ast`; every `Call` whose function is the attribute `from_environment` on the name
  `OllamaChatClient` has a keyword `turns`; every `Call` of the name `_visual_provider` has a
  keyword `turns`; and there is at least one of each (so the test cannot pass vacuously).
- `test_the_turn_recorder_is_bound_to_the_project_and_its_engine` (a project created in
  `InMemoryProjectRepository`, moved to DESIGN; a transport class in the file answering
  `{"message": {"content": "{\"questions\": []}"}, "eval_count": 2}`; assert the two events'
  kinds, `project_id` and `engine_id`).
- `test_the_visual_fallback_still_builds_under_every_provider_but_scripted`
  (`_visual_provider(p, ollama_model=None, turns=RecordingModelTurns())` for each member of
  `_PROVIDERS` but `"scripted"` returns a `VisualInventoryProducer`; no call is made, so no model is
  contacted). The AST test above is what proves the fallback passes `turns`: the fallback's client
  is built from the environment, so no transport can be injected through `_visual_provider`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The recorder and the seam (lanes 1 and 2); routing these calls through sovereignloop
  (`gap-design-via-sovereignloop`, which by lane 1's ordering rule records its turns through the
  loop's events instead).
- The paid DESIGN path (it records `BudgetSpent` through `_build_spend_recorder`, unchanged).
- Docs, CHANGELOG.

Commit as `feat(cli): every local-model client ledgers its turns`. Do not push.

## Lane card
- **Depends on:** `gap-ledger-provider-turns-2`, `split-324-2-visual-cli`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
