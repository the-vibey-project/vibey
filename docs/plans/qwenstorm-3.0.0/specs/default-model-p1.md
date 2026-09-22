## Title
feat(models)!: GPT-OSS 20B on Ollama is the default local model

## Why
Sub-doctrine 8.d requires the default local model to be the gold standard for the machine, with the evidence and date recorded. The operator decided on 2026-09-22 that the default FOSS model is **GPT-OSS 20B on Ollama**. Evidence (M5, 24 GB, one 10-turn agent session): GPT-OSS 20B via Ollama took 86 s with a 131k context in 13.1 GB, against 215 s for Qwen2.5-Coder-14B on llama.cpp at 32k; in a live storm lane it averaged about 13 s per turn. Ollama loads it with its full 131072-token context. Note: Ollama's GPT-OSS GGUF does not load in llama.cpp (architecture `gptoss` vs `gpt-oss`), so the llama.cpp side waits for a pinned GGUF under #383; this issue changes the Ollama default only. Today the default is `qwen2.5-coder:14b` in src/vibey/infrastructure/engines/ollama_chat.py:39 (`DEFAULT_OLLAMA_MODEL`), src/vibey_runners/qwen/src/qwenloop/domain/config.py:15 (`DEFAULT_ENDPOINT_MODEL`, with the help text at src/vibey_runners/qwen/src/qwenloop/cli/app.py:75), and the chart's in-cluster Ollama (deploy/helm/vibey/values.yaml:127, with a sizing comment at :134 written for a ~9 GB model).

## Required behaviour
1. `DEFAULT_OLLAMA_MODEL` and `DEFAULT_ENDPOINT_MODEL` are `"gpt-oss:20b"`; qwenloop's help text says so.
2. The chart's `ollama.model` is `gpt-oss:20b`; the sizing comment and any volume or memory values that assumed ~9 GB are corrected for a ~13 GB model (read values.yaml around :106-:180 and the Ollama template; do not guess — take the size from `ollama show gpt-oss:20b` or the registry). Goldens regenerated: `bash deploy/helm/golden/render.sh --update`, then all six profiles pass.
3. GPT-OSS answers with a separate reasoning channel (Ollama's native API: `message.thinking`). vibey's DESIGN and DECOMPOSE parsing (src/vibey/infrastructure/engines/ollama_chat.py and qwenloop_design.py) uses only `message.content`, never the thinking text. Record a REAL response from the local Ollama (`curl -s http://127.0.0.1:11434/api/chat -d '{"model":"gpt-oss:20b","messages":[{"role":"user","content":"Reply with {\"ok\": true} and nothing else"}],"stream":false}'`) and commit it as a test fixture; a test parses it.
4. An explicit model (config key, `VIBEY_OLLAMA_MODEL`, flag) still wins everywhere.
5. Leave measured evidence alone: test fixtures and `vibey_gh/fit.py` constants that describe measurements of qwen2.5-coder:14b are records, not defaults.

## Acceptance criteria
- [ ] Both constants are `gpt-oss:20b`; the chart pulls it; all six golden profiles pass.
- [ ] A recorded GPT-OSS response with a `thinking` field parses to its content only.
- [ ] Explicit model overrides still work (existing tests pass).
- [ ] Root gates at 100% per layer; the qwen tenant's suite at its 100% floor.

## Tests to write first (TDD)
tests/infrastructure/engines/ (ollama_chat and qwenloop_design tests): the recorded fixture; default model constant. The qwen tenant's tests/test_domain.py:50 asserts the old default — update it.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src/vibey && uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/cli
    (cd src/vibey_runners/qwen && python -m pytest -q -p no:cacheprovider)
    bash deploy/helm/golden/render.sh

## Out of scope
Backend selection (part 2), vibey-gh (part 3), llama.cpp profiles (#383), docs. Commit as `feat(models)!: ...` with a `BREAKING CHANGE:` footer: "the default local model is gpt-oss:20b; set VIBEY_OLLAMA_MODEL=qwen2.5-coder:14b to keep the old one".

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
