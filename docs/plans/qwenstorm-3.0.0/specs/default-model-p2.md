## Title
feat(qwenloop)!: with nothing configured, qwenloop attaches to a running local Ollama

## Why
Sub-doctrine 8.d requires the default local model to be the gold standard for the machine, with the evidence and date recorded. The operator decided on 2026-09-22 that the default FOSS model is **GPT-OSS 20B on Ollama**. Evidence (M5, 24 GB, one 10-turn agent session): GPT-OSS 20B via Ollama took 86 s with a 131k context in 13.1 GB, against 215 s for Qwen2.5-Coder-14B on llama.cpp at 32k; in a live storm lane it averaged about 13 s per turn. Ollama loads it with its full 131072-token context. Note: Ollama's GPT-OSS GGUF does not load in llama.cpp (architecture `gptoss` vs `gpt-oss`), so the llama.cpp side waits for a pinned GGUF under #383; this issue changes the Ollama default only. qwenloop's `BackendSelector.select` (src/vibey_runners/qwen/src/qwenloop/application/backend_selection.py) picks: explicit backend, then a configured endpoint, then vLLM on a large NVIDIA GPU, then its own managed llama.cpp server. A running local Ollama is never chosen unless configured, so on a Mac the default path starts a 16 GB llama-server beside an Ollama that already serves the default model — and sub-doctrine 8.c allows one model instance per deployment.

## Required behaviour
1. `select` gains a keyword input `ollama_available: bool`. With `requested` AUTO and no endpoint configured, `ollama_available=True` returns `BackendChoice(Backend.OPENAI_COMPAT, "a local Ollama is running: the default backend")`, ahead of the vLLM and llama.cpp rules.
2. The CLI composition (src/vibey_runners/qwen/src/qwenloop/cli/app.py `_select`, ~line 177, and `_attach` ~188) probes Ollama's default address once (a GET of `http://127.0.0.1:11434/api/version` with a 2 s timeout; any failure means not available) and, when chosen, attaches to `http://127.0.0.1:11434/v1` with the configured model (default `gpt-oss:20b`).
3. Without a running Ollama, behaviour is exactly as today (llama.cpp portable profile).
4. The probe never runs when an endpoint or backend is configured.

## Acceptance criteria
- [ ] Selector unit tests: Ollama available → OPENAI_COMPAT; unavailable → unchanged order; explicit and configured endpoint still win.
- [ ] CLI composition test with a fake HTTP probe (both outcomes); no real network in tests.
- [ ] The qwen tenant's gates at its 100% floor.

## Tests to write first (TDD)
The selector's tests (find them: search the tenant's tests for BackendSelector) and tests/test_cli.py for `_select`/`_server_for`.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen && python -m pytest -q -p no:cacheprovider && python -m mypy --strict src/qwenloop
    cd ../../.. && uv run ruff check . && uv run ruff format --check .

## Out of scope
Default model constants (part 1), vibey-gh (part 3), docs. Commit as `feat(qwenloop)!: ...` with a `BREAKING CHANGE:` footer: "with nothing configured and Ollama running, qwenloop attaches to it instead of starting its own llama.cpp server".

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
