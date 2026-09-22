## Title
feat(engines): a chat client that asks through the sovereign-chat port, so the sovereign providers can route through sovereignloop unchanged

## Why
The sovereign DESIGN, DECOMPOSE and VISUAL providers each take one
`OllamaChatClientInterface` (`src/vibey/infrastructure/engines/interfaces/ollama_chat_interface.py:23-39`):
`QwenloopDesignProvider(chat=...)` (`qwenloop_design.py:184-191`),
`QwenloopWorkPlanProducer(chat=...)` (`qwenloop_decompose.py:56-65`), and the visual provider
of lane `visual-design-provider`. The CLI builds one client and hands it to all of them
(`src/vibey/cli/main.py:449-450` and `:1604-1606`). Today that client dials Ollama directly
(`ollama_chat.py:165-167`), which sub-doctrine 8.c forbids (`doctrines.md:204`: "nothing
spawns a loop directly").

So the smallest correct change is a second implementation of that same interface which puts
the question to `SovereignChatPort` (lane `gap-design-via-sovereignloop-1`) and records which
seat answered. The providers do not change at all; the composition root chooses the client.
Recording every routed answer is 7.c (`doctrines.md:82`); substitution at the declared seam is
9.b (`doctrines.md:349`).

## Required behaviour
1. New `src/vibey/infrastructure/engines/loop_routed_chat.py` (provenance line 1, copied from
   `ollama_chat.py:1`) holds `class LoopRoutedChatClient`:
   - `__init__(self, *, port: SovereignChatPort, recorder: RoutedChatRecorder, model_pin: str | None = None, caller: str = "vibey.sovereign-provider", base_url: str = DEFAULT_OLLAMA_URL) -> None`.
     `model_pin` is stored stripped; an all-blank pin is stored as `None`.
     `DEFAULT_OLLAMA_URL` and `DEFAULT_OLLAMA_MODEL` are imported from
     `vibey.infrastructure.engines.ollama_chat` (`:38-39`), never restated.
   - `base_url` property: returns the constructor's `base_url`. Its docstring says the value is
     informational (the endpoint the loop's seat serves) and that this client never opens it.
   - `model` property: `model_pin` when set, else `DEFAULT_OLLAMA_MODEL`.
   - `model_pin` property: the stored pin (`str | None`).
   - `context_window(self, prompt_chars: int) -> int`: exactly `OllamaChatClient`'s rule
     (`ollama_chat.py:143-145`), computed from `OllamaChatClient.CONTEXT_FLOOR`,
     `CONTEXT_CEILING`, `CONTEXT_RESERVE` and `CHARS_PER_TOKEN` (`:85-88`), so the two clients
     can never size one prompt differently.
   - `async def ask(self, system: str, user: str, schema: Mapping[str, object]) -> dict[str, object]`:
     builds `PinnedChatRequest(system=system, user=user, schema=dict(schema), model_pin=self._model_pin, num_ctx=self.context_window(len(system) + len(user)), caller=self._caller)`,
     awaits `answer = await self._port.ask(request)`, then
     `await self._recorder.record(request, answer)`, then returns `dict(answer.value)`.
     It opens no socket and imports nothing from `urllib`.
2. New `src/vibey/infrastructure/engines/interfaces/loop_routed_chat_interface.py` (provenance
   line 1) declares `@runtime_checkable class LoopRoutedChatClientInterface(OllamaChatClientInterface, Protocol)`
   adding only `@property def model_pin(self) -> str | None: ...`. Export it from
   `src/vibey/infrastructure/engines/interfaces/__init__.py` (import block and `__all__`, sorted).
3. Module constant `LOOP_ROUTED_CALLER = "vibey.sovereign-provider"` in `loop_routed_chat.py`
   is the constructor's default `caller` (12.c: one declared default, overridable per client).
4. Nothing else changes: `OllamaChatClient`, the three providers and `cli/main.py` are untouched.
   Choosing this client in service mode is the composition lane owed after
   `loops-command-executor` (see Out of scope).

## Where to change
- New `src/vibey/infrastructure/engines/loop_routed_chat.py`,
  `src/vibey/infrastructure/engines/interfaces/loop_routed_chat_interface.py`.
- Edit `src/vibey/infrastructure/engines/interfaces/__init__.py` (edit_file).
- New `tests/infrastructure/engines/test_loop_routed_chat.py`, using the registered fakes
  `InMemorySovereignChat` and `InMemoryRoutedChatRecorder` from `tests/fakes/sovereign_chat.py`.
- Pattern: `ollama_chat.py:77-145` for the properties and the sizing rule.

## Acceptance criteria
- [ ] `grep -n "urllib\|/api/chat" src/vibey/infrastructure/engines/loop_routed_chat.py` prints nothing.
- [ ] `git diff --stat` touches no provider (`qwenloop_design.py`, `qwenloop_decompose.py`) and not `cli/main.py`.
- [ ] `QwenloopDesignProvider(chat=LoopRoutedChatClient(...))` produces a `QuestionBatch` from a scripted answer (test below).
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/engines/test_loop_routed_chat.py`:
- `test_ask_sends_one_pinned_request_and_returns_the_value` -- scripted `{"a": 1}` comes back as `{"a": 1}`; the fake saw one request whose `system`, `user`, `schema`, `model_pin` and `caller` are the ones given.
- `test_every_answer_is_recorded_with_its_request` -- after two asks, the recorder holds two `(request, answer)` pairs, in order, each answer carrying `seat == "gpt-oss-20b"`.
- `test_num_ctx_matches_the_direct_client` -- parametrized over prompt sizes `0, 10_000, 200_000`: `LoopRoutedChatClient(...).context_window(n) == OllamaChatClient().context_window(n)`, and the request's `num_ctx` equals it.
- `test_model_is_the_pin_or_the_default` -- `model_pin="qwen3:8b"` gives `model == "qwen3:8b"`; none (or `"  "`) gives `DEFAULT_OLLAMA_MODEL` and `model_pin is None`.
- `test_the_design_provider_runs_unchanged_over_the_loop` -- `QwenloopDesignProvider(chat=client).batch(DesignStage.CONTEXT_FREE, [])` with the scripted answer `{"questions": [{"question_id": "q1", "text": "Who uses it?", "default": "developers", "blocking": False}]}` returns a batch whose questions' ids are `("q1",)`, and the recorder holds one record.
- `test_client_satisfies_both_interfaces` -- `isinstance(client, OllamaChatClientInterface)` and `isinstance(client, LoopRoutedChatClientInterface)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The production `SovereignChatPort` adapter over ADR-0046's loop client, and the composition
  that picks this client when `[engines] invocation = "service"`: both are owed after
  `loops-command-executor` and an operator ruling on how a seat runs a one-shot
  schema-constrained generation (reported with this lane set).
- The ledger recorder (`gap-design-via-sovereignloop-4`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(engines): a chat client that asks through the sovereign-chat port`. Do not push.

## Lane card
- **Depends on:** `gap-design-via-sovereignloop-1`.
- **Must keep passing unchanged:** `tests/infrastructure/engines/test_ollama_chat.py`,
  `tests/cli/test_sovereign_provider_options.py`, every protected test.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
