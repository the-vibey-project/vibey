<!-- split of #383: child 5 of 6; audit: issue-audit/updates/383.md -->

## Title
feat(qwenloop): reasoning channels never reach tool-call or answer parsing

## Why
This era's default model, GPT-OSS 20B (8.d, `src/vibey_tools/gh/docs/doctrines.md:259-269`),
answers on two channels, and the Qwen3.x models the catalogue adds think before they answer.
Servers return that reasoning in a field of its own — llama.cpp's `reasoning_content`, Ollama's
OpenAI-compatible `reasoning`, Ollama's native `thinking` — or, for a Qwen3 template without a
reasoning parser, inline as `<think>…</think>` ahead of the answer. qwenloop's
`OpenAIServer.chat_stream` (`src/vibey_runners/qwen/src/qwenloop/infrastructure/inference.py:148-204`)
reads only `message["content"]` and `tool_calls` (`:177-181`): it drops a reasoning field (7.c,
`doctrines.md:82-91`, wants it in the ledger) and hands an inline `<think>` block straight to
`_parse_text_tool_calls` (`:581-619`), which scans for any JSON object shaped like a tool call, and
to the runner, which searches the answer for the completion marker (`runner.py:344-369`). So a model
merely thinking about a tool call, or about finishing, can run a tool or claim completion. vibey's
own DESIGN/DECOMPOSE parsing already reads only `message.content` (#387's recorded fixture in
`tests/infrastructure/engines/test_ollama_chat.py`); this lane does the same for qwenloop's agent
loop and keeps the reasoning for the run log.

## Required behaviour
All paths are under `src/vibey_runners/qwen/`.

1. **`ChatChunk`** (`src/qwenloop/domain/model.py:99-107`) gains a last field
   `reasoning: str = ""` with the comment
   `# The model's reasoning for this reply, kept for the run log (7.c) and never parsed (#383).`
2. **The splitter.** New `src/qwenloop/domain/reasoning.py` (pure: no I/O) holds exactly:
   ```python
   """A model's reasoning, kept apart from its answer (#383).

   GPT-OSS and Qwen3 think before they answer. Servers hand the thinking back in a field of its
   own -- llama.cpp's `reasoning_content`, Ollama's OpenAI-compatible `reasoning`, Ollama's
   native `thinking` -- or, for Qwen3 without a reasoning parser, inline as `<think>...</think>`
   ahead of the answer. Reasoning is kept for the run log (sub-doctrine 7.c) and is never
   parsed as a tool call, as JSON, or as the completion marker.
   """

   from collections.abc import Mapping
   from dataclasses import dataclass
   from typing import Any

   #: The message fields servers put reasoning in, in the order they are read.
   REASONING_FIELDS: tuple[str, ...] = ("reasoning_content", "reasoning", "thinking")
   _OPEN = "<think>"
   _CLOSE = "</think>"


   @dataclass(frozen=True, slots=True)
   class ReasoningSplit:
       answer: str
       reasoning: str


   class ReasoningSplitter:
       """Separates one chat message's reasoning from its answer."""

       def __init__(self, *, fields: tuple[str, ...] = REASONING_FIELDS) -> None:
           self._fields = fields

       def split(self, message: Mapping[str, Any]) -> ReasoningSplit:
           parts = [
               value.strip()
               for value in (message.get(name) for name in self._fields)
               if isinstance(value, str) and value.strip()
           ]
           content = message.get("content")
           answer, inline = self._inline(content if isinstance(content, str) else "")
           if inline:
               parts.append(inline)
           return ReasoningSplit(answer=answer, reasoning="\n\n".join(parts))

       @staticmethod
       def _inline(text: str) -> tuple[str, str]:
           """A leading `<think>` block, or everything before an orphan `</think>` (a template
           that opened the block in the prompt), split off `text` as (answer, reasoning).
           Tags later in the answer are left alone: they may be part of a file being written."""
           stripped = text.lstrip()
           if stripped.startswith(_OPEN):
               thought, closed, rest = stripped[len(_OPEN) :].partition(_CLOSE)
               if not closed:
                   return "", thought.strip()
               return rest.strip(), thought.strip()
           head, closed, rest = text.partition(_CLOSE)
           if closed and _OPEN not in head:
               return rest.strip(), head.strip()
           return text, ""
   ```
   A message with no reasoning keeps its `content` byte for byte (no stripping); a missing or
   non-string `content` is `""`; a non-string reasoning field is ignored.
3. **Its interface.** New `src/qwenloop/domain/interfaces/reasoning_interface.py`:
   `@runtime_checkable class ReasoningSplitterInterface(Protocol)` with
   `def split(self, message: Mapping[str, Any]) -> ReasoningSplit:` (docstring
   `"""The message's answer and its reasoning, never mixed."""`, body `...`), importing
   `ReasoningSplit` from `qwenloop.domain.reasoning` directly (as `config_interface.py:7` imports
   `QwenConfig`). `src/qwenloop/domain/interfaces/__init__.py` imports it and lists
   `"ReasoningSplitterInterface"` in `__all__` (after `"QwenConfigParserInterface"`).
4. **The adapter** (`src/qwenloop/infrastructure/inference.py`):
   - `OpenAIServer.__init__` (`:67-68`) becomes
     `def __init__(self, cache_dir: Path | None = None, *, opener: Callable[..., Any] | None = None) -> None:`
     storing `self._opener = opener` under the comment
     `# The HTTP seam for model calls (sub-doctrine 9.b): None means urllib.request.urlopen, looked up when a request is made, so a test hands in a double instead of patching urllib.`
     (wrap the comment at 100 columns).
   - `OpenAICompatServer.__init__` (`:329-350`) gains the keyword
     `opener: Callable[..., Any] | None = None` and calls `super().__init__(cache_dir, opener=opener)`.
   - In `chat_stream`, the call at `:166-168` uses `self._opener or urllib.request.urlopen` in place
     of `urllib.request.urlopen` (the `except urllib.error.HTTPError` handling is unchanged).
   - A module constant `_REASONING = ReasoningSplitter()` sits beside `_SERVER_TIMING_KEYS`
     (`:40-47`). `content = message.get("content") or ""` (`:179`) becomes
     `split = _REASONING.split(message)` and `content = split.answer`, preceded by the comment
     `# Reasoning never reaches tool-call, JSON or marker parsing (#383): only the answer does.`
     The final `yield ChatChunk(...)` (`:199-204`) adds `reasoning=split.reasoning`.
   - `health`, `check` and every other call keep `urllib.request.urlopen` as today.
   - Add `Callable` to the `collections.abc` import and `Any` to the `typing` import.
5. **The runner** (`src/qwenloop/application/runner.py`). In the chunk loop, directly above
   `if chunk.text:` (`:276`):
   ```python
                   if chunk.reasoning:
                       # Kept for the run log (7.c); never answered, parsed or counted (#383).
                       self._store.append_event(
                           run_id, {"type": "reasoning", "turn": turn, "text": chunk.reasoning}
                       )
   ```
   Reasoning is never appended to `text_parts`, so it never reaches the answer, the transcript, the
   verdict fence or the `DONE_MARKER` check. Nothing else in the runner changes.
6. **Evidence.** The tests read replies from a new, non-test module `tests/recorded_replies.py`
   (imported as `from recorded_replies import ...`, the way `tests/fakes.py` is). It holds:
   - `OLLAMA_V1_GPT_OSS_ANSWER` and `OLLAMA_V1_GPT_OSS_TOOL_CALL`: two replies **recorded** from
     `gpt-oss:20b` on the lane host's Ollama OpenAI-compatible endpoint with the commands in C2,
     pasted verbatim as Python dicts under a comment naming the endpoint, the date and the request;
   - `OLLAMA_NATIVE_GPT_OSS_MESSAGE`: the `message` of #387's recording, verbatim (C3);
   - `CONSTRUCTED_LLAMA_SERVER_REPLY` and `CONSTRUCTED_QWEN3_INLINE_MESSAGE`: **constructed, not
     recorded** (C4), each under the comment
     `# Constructed, not recorded (10.f): <why>. Replace with a recording in a follow-up.`
   If the lane host's Ollama is not reachable, the two `OLLAMA_V1_*` constants are not invented: the
   tests that use them are not written, and the commit body names the recording as a follow-up.

## Where to change
Why this lane spans several files: the split is pure (domain), is applied where replies are read
(infrastructure), is carried by the chunk type (domain model) and is recorded by the runner
(application); each edit is small and exact.
- `src/qwenloop/domain/model.py` — behaviour 1.
- new `src/qwenloop/domain/reasoning.py` and `src/qwenloop/domain/interfaces/reasoning_interface.py`,
  plus `src/qwenloop/domain/interfaces/__init__.py` — behaviours 2-3. Line 1 of each new file is the
  provenance comment copied from line 1 of `src/qwenloop/domain/model.py`.
- `src/qwenloop/infrastructure/inference.py` — behaviour 4 (`edit_file` only: 619 lines).
- `src/qwenloop/application/runner.py` — behaviour 5 (`edit_file` only: 412 lines).
- new `tests/recorded_replies.py` and `tests/test_reasoning.py`; append to `tests/test_inference.py`
  and `tests/test_runner.py` (new imports go into each file's top import block with `edit_file`,
  never below code).

## Acceptance criteria
- [ ] A reply whose reasoning holds a tool-call-shaped JSON object and the completion marker yields
      no tool call and no answer text (`test_reasoning_never_becomes_a_tool_call_or_the_answer`).
- [ ] An inline `<think>` block is split off before text tool calls are parsed.
- [ ] The recorded gpt-oss:20b replies (Ollama OpenAI-compatible, and native `thinking`) split into
      exactly their `content` and their reasoning field.
- [ ] A run records a `{"type": "reasoning", "turn": N, "text": ...}` event per turn with reasoning,
      and completes only on the marker in the answer.
- [ ] Every existing test in `tests/test_inference.py` and `tests/test_runner.py` passes unedited.
- [ ] The qwen suite passes at its 100% floor; mypy --strict, lint-imports, bandit and ruff are clean.
- [ ] No new test patches an import or a module/class attribute, or reaches the network.

## Tests to write first (TDD)
New `tests/test_reasoning.py` (`splitter = ReasoningSplitter()`):
- `test_llama_server_reasoning_content_is_reasoning_not_answer` — on
  `CONSTRUCTED_LLAMA_SERVER_REPLY["choices"][0]["message"]`: `answer` equals its `content`,
  `reasoning` equals its `reasoning_content` stripped.
- `test_the_recorded_ollama_reply_splits_into_its_content_and_its_reasoning` — on
  `OLLAMA_V1_GPT_OSS_ANSWER["choices"][0]["message"]`: `answer == message["content"]`,
  `reasoning == (message.get("reasoning") or "").strip()`; when the recording carries a
  `reasoning` string, also `reasoning` is non-empty and not a substring of `answer`.
- `test_ollama_native_thinking_is_reasoning` — on `OLLAMA_NATIVE_GPT_OSS_MESSAGE`:
  `answer == '{"ok": true}'` and `reasoning == OLLAMA_NATIVE_GPT_OSS_MESSAGE["thinking"].strip()`.
- `test_a_leading_think_block_is_reasoning` — on `CONSTRUCTED_QWEN3_INLINE_MESSAGE`
  (`"\n<think>\nI should read the file.\n</think>\n\nREADME read."`): answer `"README read."`,
  reasoning `"I should read the file."`.
- `test_an_unclosed_leading_think_block_is_all_reasoning` — `{"content": "<think>still going"}` →
  answer `""`, reasoning `"still going"`.
- `test_an_orphan_close_tag_ends_the_reasoning` — `{"content": "plan it\n</think>\nanswer"}` →
  answer `"answer"`, reasoning `"plan it"`.
- `test_think_tags_inside_the_answer_are_left_alone` — `{"content": "write <think>x</think> into the doc"}`
  → answer unchanged, reasoning `""`.
- `test_a_message_with_no_reasoning_is_unchanged` — `{"content": "done\n"}` → answer `"done\n"`;
  `{"content": None}` and `{}` → answer `""`; `{"content": "a", "reasoning": {"not": "text"}, "thinking": "  "}`
  → reasoning `""`; `{"content": "<think></think>b"}` → answer `"b"`, reasoning `""`.
- `test_every_reasoning_channel_is_kept_in_order` —
  `{"reasoning_content": "one", "reasoning": "two", "content": "<think>three</think>four"}` →
  answer `"four"`, reasoning `"one\n\ntwo\n\nthree"`.
- `test_the_splitter_satisfies_its_interface` — `isinstance(splitter, ReasoningSplitterInterface)`.

Appended to `tests/test_inference.py` (the reply is handed in through the new `opener=` seam as a
small callable `(request, timeout) -> UrlResponse(json.dumps(reply).encode())`, reusing the file's
`UrlResponse` class; the callable records `request.full_url` and `timeout`. A constructed reply is
`{"choices": [{"message": <message>}]}`; a recorded one is used whole):
- `test_reasoning_never_becomes_a_tool_call_or_the_answer` — `LlamaCppServer(tmp_path, opener=...)`
  with a reply whose message is `{"content": "", "reasoning_content": '{"name": "shell", "arguments": {"argv": ["rm", "-rf", "/"]}} QWENLOOP_TASK_FULLY_COMPLETE'}`:
  the chunks are exactly one, with `tool_call is None`, `text == ""`, and
  `"QWENLOOP_TASK_FULLY_COMPLETE" in reasoning`.
- `test_an_inline_think_block_is_split_before_tool_calls_are_parsed` — message content
  `'<think>{"name": "shell", "arguments": {"argv": ["id"]}}</think>{"name": "read_file", "arguments": {"path": "README.md"}}'`:
  exactly one `tool_call`, `{"name": "read_file", "arguments": {"path": "README.md"}}`, and the
  last chunk's `reasoning` contains `"shell"`.
- `test_a_recorded_gpt_oss_tool_call_passes_through` — `OLLAMA_V1_GPT_OSS_TOOL_CALL` through
  `OpenAICompatServer("http://h:1/v1", "gpt-oss:20b", opener=...)`: the tool-call chunks name the
  recorded function(s) and arguments, and the last chunk's `reasoning` equals the recorded
  message's `reasoning` stripped (or `""`); the opener saw `"http://h:1/v1/chat/completions"`.
- `test_the_opener_seam_gets_the_request_timeout` — a `LlamaCppServer(tmp_path, opener=...)` whose
  `request_timeout_seconds = 7.0` passes `timeout == 7.0` to the opener.

Appended to `tests/test_runner.py`:
- `test_reasoning_is_recorded_and_never_answered` — `ScriptedServer` turn 1:
  `[ChatChunk(tool_call={"name": "write_file", "arguments": {"path": "a.txt", "content": "x"}}), ChatChunk(text="", reasoning="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE")]`;
  turn 2: `[ChatChunk(text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE", reasoning="done thinking")]`;
  `max_turns=3`, `FakeClock()`. The run completes, its `completed` event has `turn == 2`, the
  events hold `{"type": "reasoning", "turn": 1, ...}` and `{"type": "reasoning", "turn": 2, "text": "done thinking"}`,
  and no message in `state.transcript` contains `"done thinking"`.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_runners/qwen
python -c "import qwenloop" || python -m pip install -e ".[dev]"
python -m pytest -q -p no:cacheprovider --no-cov tests/test_reasoning.py tests/test_inference.py tests/test_runner.py
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
- vibey's own providers (`src/vibey/infrastructure/engines/ollama_chat.py`, `qwenloop_design.py`):
  #387 already reads only `message.content` there.
- Sending reasoning back to the model in later turns, streaming, and the `health`/`check` calls.
- Starting a llama-server on the lane host, or recording from one (C4).
- The catalogue, selection, `model verify` and doctor (the other #383 lanes).
- `tests/conftest.py`, `tests/fakes.py`: do not edit them.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs, or change git remotes. Commit locally as this spec's title.

## Conventions this lane relies on (everything needed is here)
**C1, tests.** Focused runs need `--no-cov` (the tenant's addopts carry a 100% floor). New tests
substitute only at declared seams — here the new `opener=` keyword and `ScriptedServer` injected
into `AutonomousRunner(...)`. Never `monkeypatch.setattr` an import or a module/class attribute
(the existing tests that patch `urllib.request.urlopen` are left exactly as they are; the `opener`
default is looked up per call so they keep working), never `mock.patch`, `MagicMock` or
`AsyncMock`. No test reaches the network or a live Ollama.

**C2, recording from the lane host's Ollama (run in the lane shell, never in a test).** The lane's
own model is idle while a tool runs, so the endpoint answers:
```bash
TOOLS='[{"type":"function","function":{"name":"read_file","description":"Read a UTF-8 text file inside the assigned worktree.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"],"additionalProperties":false}}}]'
curl -fsS http://127.0.0.1:11434/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"gpt-oss:20b","stream":false,"messages":[{"role":"user","content":"Reply with {\"ok\": true} and nothing else"}]}' \
  | python3 -m json.tool
curl -fsS http://127.0.0.1:11434/v1/chat/completions -H 'Content-Type: application/json' \
  -d "{\"model\":\"gpt-oss:20b\",\"stream\":false,\"tool_choice\":\"auto\",\"tools\":$TOOLS,\"messages\":[{\"role\":\"user\",\"content\":\"Call read_file on README.md. Do not answer in prose.\"}]}" \
  | python3 -m json.tool
date -u +%F
```
Paste each JSON reply into `tests/recorded_replies.py` as a Python dict literal (`true`/`false`/
`null` become `True`/`False`/`None`), with the date and the request in the comment above it.

**C3, #387's native recording** (`tests/infrastructure/engines/test_ollama_chat.py`, recorded from
a local Ollama on 2026-09-22, `POST /api/chat`, stream false). Its `message`, verbatim:
```python
OLLAMA_NATIVE_GPT_OSS_MESSAGE: dict[str, object] = {
    "role": "assistant",
    "content": '{"ok": true}',
    "thinking": 'User says: "Reply with {"ok": true} and nothing else". So just '
    "output that JSON exactly. No additional explanation.",
}
```

**C4, the constructed replies.** The lane host must not start a llama-server beside the Ollama that
serves it (one resident model per machine, ADR-0046 §4), and no Qwen3 model is installed there, so:
```python
# Constructed, not recorded (10.f): the shape llama-server's OpenAI-compatible endpoint returns
# with --jinja and its default --reasoning-format. Replace with a recording in a follow-up.
CONSTRUCTED_LLAMA_SERVER_REPLY: dict[str, object] = {
    "choices": [
        {
            "finish_reason": "stop",
            "index": 0,
            "message": {
                "role": "assistant",
                "content": '{"ok": true}',
                "reasoning_content": "The user wants exactly one JSON object. Reply with it.",
            },
        }
    ],
    "usage": {"prompt_tokens": 70, "completion_tokens": 20},
}
# Constructed, not recorded (10.f): a Qwen3 reply with its reasoning inline, as a template
# without a reasoning parser returns it. Replace with a recording in a follow-up.
CONSTRUCTED_QWEN3_INLINE_MESSAGE: dict[str, object] = {
    "role": "assistant",
    "content": "\n<think>\nI should read the file.\n</think>\n\nREADME read.",
}
```

**Depends on:** split-383-1-model-catalogue
- split-383-1-model-catalogue: its `gpt-oss-20b` entry names the artifacts the recorded replies come from (Ollama tag `gpt-oss:20b`, GGUF `gpt-oss-20b-MXFP4.gguf`); no code from it is used.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
