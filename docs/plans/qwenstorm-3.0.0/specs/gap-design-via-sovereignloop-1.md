## Title
feat(application): a consumer-side port for pinned sovereign chat runs, with in-memory fakes

## Why
Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:204`) says nothing spawns a loop
directly: vibey's workers put work on the loop's queue. The sovereign DESIGN, DECOMPOSE and
VISUAL providers break that. All three ask their questions through one
`OllamaChatClientInterface` (`src/vibey/infrastructure/engines/interfaces/ollama_chat_interface.py:23-39`),
whose only implementation posts straight to Ollama's `/api/chat`
(`src/vibey/infrastructure/engines/ollama_chat.py:147-177`, the URL at `:166`). The design
provider is `QwenloopDesignProvider` (`src/vibey/infrastructure/engines/qwenloop_design.py:177`);
the decompose producer takes the same client (`qwenloop_decompose.py:56-65`); the visual
provider of lane `visual-design-provider` does too. A second model asked this way contends
with the one sovereignloop keeps resident (ADR-0046 §4, `specs/ADR-two-loops.md`, whose flag
says routing these providers "is a follow-up and is not in this set").

This lane is the first step, and it is dependency inversion: the application layer declares
the one thing these providers need from the loop -- "ask this schema-constrained question on
a pinned model and tell me which seat answered" -- so a later lane can route the shared chat
client through it without the providers changing. Every new seam gets a registered in-memory
fake (9.b, `doctrines.md:349`; `specs/fakes-registry.md`).

## Required behaviour
1. New module `src/vibey/application/interfaces/sovereign_chat.py` declares, and only declares:
   - `@dataclass(frozen=True, slots=True) class PinnedChatRequest` with fields, in order:
     `system: str`, `user: str`, `schema: Mapping[str, object]`, `model_pin: str | None`,
     `num_ctx: int`, `caller: str`. `__post_init__` raises `ValueError` when `num_ctx < 1`,
     when `caller.strip()` is empty, or when `model_pin` is not None and `model_pin.strip()`
     is empty. Messages: `"num_ctx must be at least 1"`, `"caller must name the asking component"`,
     `"model_pin must be None or a model name"`.
   - `@dataclass(frozen=True, slots=True) class RoutedChatAnswer` with fields, in order:
     `value: Mapping[str, object]`, `loop_id: str`, `engine_id: str`, `seat: str`,
     `model: str`, `run_id: str`. These are the names of ADR-0046 §3's `vibey.run.routed/1`
     and `vibey.run.accepted/1` fields (`loop_id`, `engine_id`, `seat`, `model`), plus the
     run's id. It has no completion, success or capacity field, and no `resets_at` (ADR-0046
     §3; CLAUDE.md non-negotiables).
   - `@runtime_checkable class SovereignChatPort(Protocol)` with one method:
     `async def ask(self, request: PinnedChatRequest) -> RoutedChatAnswer: ...`.
     Docstring: the answer's `value` is the model's JSON object under the request's schema;
     an answer that is not an object is a `ValueError` raised by the implementation.
   - `@runtime_checkable class RoutedChatRecorder(Protocol)` with one method:
     `async def record(self, request: PinnedChatRequest, answer: RoutedChatAnswer) -> None: ...`.
     Docstring: every routed answer is recorded (7.c, `doctrines.md:82`); an implementation
     that cannot record says so, and never drops the record silently.
   - First line: the provenance header, copied byte-for-byte from
     `src/vibey/application/interfaces/visual.py:1`. Imports only `collections.abc`,
     `dataclasses` and `typing`.
2. `src/vibey/application/interfaces/__init__.py` re-exports the four names and adds them to
   its `__all__` in sorted position.
3. New `tests/fakes/sovereign_chat.py` (provenance line 1) holds two plain classes with real
   in-memory behaviour (never `unittest.mock`):
   - `InMemorySovereignChat(answers: Sequence[Mapping[str, object]], *, loop_id: str = "sovereignloop", engine_id: str = "qwenloop", model: str = "gpt-oss:20b")`.
     It keeps `requests: list[PinnedChatRequest]`. Each `ask` appends the request, pops the
     next scripted answer, and returns a `RoutedChatAnswer` whose `model` is
     `request.model_pin or model`, whose `seat` is that model lower-cased with every character
     outside `[a-z0-9-]` replaced by `-` (ADR-0046 §3's seat slug: `gpt-oss:20b` becomes
     `gpt-oss-20b`), and whose `run_id` is `f"fake-run-{len(self.requests)}"`. With no answer
     left it raises `LookupError("no scripted sovereign answer left")`. A scripted answer that
     is not a `dict` raises `ValueError("expected a JSON object, got <type name>")`, the same
     text `ollama_chat.py:176` uses.
   - `InMemoryRoutedChatRecorder()` keeps
     `records: list[tuple[PinnedChatRequest, RoutedChatAnswer]]` and appends on `record`.
4. `tests/fakes/registry.py` (lane `fakes-registry`) gains two `FakeRegistration` rows:
   `SovereignChatPort → InMemorySovereignChat` (factory
   `lambda: InMemorySovereignChat([{"ok": True}])`) and
   `RoutedChatRecorder → InMemoryRoutedChatRecorder`. `tests/fakes/test_port_parity.py`'s
   existing tests then cover them; add nothing to `PENDING`.

## Where to change
- New `src/vibey/application/interfaces/sovereign_chat.py`; edit
  `src/vibey/application/interfaces/__init__.py` (edit_file; keep the provenance line).
- New `tests/fakes/sovereign_chat.py`; edit `tests/fakes/registry.py` (edit_file).
- New `tests/application/test_sovereign_chat_port.py`.
- Pattern to copy: frozen, slotted DTOs beside Protocols in
  `src/vibey/application/interfaces/queue.py:23-48`.

## Acceptance criteria
- [ ] `test_routed_answer_carries_no_capacity_or_completion_field` passes: the answer's field
      set is exactly the six named fields.
- [ ] `uv run lint-imports` passes: the module imports nothing from `vibey.infrastructure`.
- [ ] `tests/fakes/test_port_parity.py` passes with both new registrations.
- [ ] 100% branch coverage of `src/vibey/application/*`.

## Tests to write first (TDD)
`tests/application/test_sovereign_chat_port.py`:
- `test_pinned_request_refuses_a_zero_context` -- `num_ctx=0` raises with the stated message.
- `test_pinned_request_refuses_an_anonymous_caller` -- `caller="  "` raises.
- `test_pinned_request_refuses_a_blank_pin` -- `model_pin=" "` raises; `model_pin=None` is fine.
- `test_routed_answer_carries_no_capacity_or_completion_field` -- `{f.name for f in dataclasses.fields(RoutedChatAnswer)}` equals exactly `{"value", "loop_id", "engine_id", "seat", "model", "run_id"}`.
- `test_fake_chat_answers_in_order_and_records_requests` -- two scripted answers come back in order; `requests` holds both requests.
- `test_fake_chat_seat_is_the_model_slug` -- pin `gpt-oss:20b` gives seat `gpt-oss-20b`; no pin gives the constructor's model.
- `test_fake_chat_refuses_when_exhausted_and_refuses_a_non_object` -- `LookupError`, then a list answer gives `ValueError`.
- `test_fake_recorder_keeps_every_record`.
- `test_fakes_satisfy_their_ports` -- `isinstance(InMemorySovereignChat([]), SovereignChatPort)` and the recorder likewise.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_sovereign_chat_port.py tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Any caller of the port (`gap-design-via-sovereignloop-2`), the job scope (`-3`), the ledger
  recorder (`-4`), and the production adapter that talks to sovereignloop (owed after
  `loops-command-executor`; see the gap report's A4 follow-ups).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(application): a consumer-side port for pinned sovereign chat runs, with in-memory fakes`. Do not push.

## Lane card
- **Depends on:** `fakes-registry` (the registry this lane appends to).
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/fakes/test_port_parity.py`, every protected test.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
