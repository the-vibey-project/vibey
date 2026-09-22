## Title
fix(qwenloop): retry a turn when the server cannot parse the model's tool call

## Why
On 2026-09-22 a storm lane on GPT-OSS 20B served by Ollama (openai-compat) lost a whole attempt to
`HTTP 500: error parsing tool call: raw='The search tool doesn't exist, only read_file, write_file,
shell. So can't search...'`: the model wrote reasoning text where Ollama's parser expected a tool
call. `OpenAIServer.chat_stream` (src/vibey_runners/qwen/src/qwenloop/infrastructure/inference.py
~133-136) turns every HTTPError into `RuntimeError(_http_error_detail(exc))`, which ends the run.
Sub-doctrine 8.d requires vibey to support the gold-standard free models on both backends; a
recoverable per-turn parse failure must not end a run.

## Required behaviour
1. An HTTP 500 whose body says the server could not parse a tool call (match `error parsing tool
   call`, case-insensitive) raises a dedicated `ToolCallParseError` (new, in the domain or the
   inference module, with an interface if it is a class with behaviour) carrying the raw text.
2. The runner (src/vibey_runners/qwen/src/qwenloop/application/runner.py, the turn loop ~190-260)
   catches it, appends a user message: "Your last reply was not a valid tool call. Call exactly one
   of the tools read_file, write_file, edit_file or shell, with JSON arguments, and no other
   text.", records a `turn.retried` event with the reason, and retries the turn.
3. At most 3 consecutive parse-failure retries per turn; the 4th raises as today.
4. Every other HTTP error behaves exactly as today.

## Acceptance criteria
- [ ] A fake server returning the 500 once, then a valid tool call, completes the turn.
- [ ] Four consecutive parse failures end the run with the RuntimeError as before.
- [ ] A non-parse 500 is not retried.
- [ ] The tenant's gates pass at its 100% coverage floor.

## Tests to write first (TDD)
tests/test_inference.py (the 500 body → ToolCallParseError; other 500 → RuntimeError) and
tests/test_runner.py (retry-then-success, retry bound, event recorded).

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen
    python -m pytest -q -p no:cacheprovider
    python -m mypy --strict src/qwenloop
    cd ../../.. && uv run ruff check . && uv run ruff format --check .

## Out of scope
Server settings, telemetry (#382), timeouts (#345). Do not push. Commit as `fix(qwenloop): ...`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
