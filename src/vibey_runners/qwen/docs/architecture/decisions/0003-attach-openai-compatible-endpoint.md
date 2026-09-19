# ADR 0003: Attach to an OpenAI-compatible endpoint

Add a third adapter behind the inference port from ADR 0001: `openai-compat`. It
attaches to a server that someone else runs, with Ollama as the main target, instead of
spawning one. qwenloop never owns that server. `start` checks that the endpoint answers
`GET /models` and serves the configured model. `stop` does nothing. `doctor` exits 0 only
when both checks pass, so an Ollama-only machine can pass doctor.

`auto` selects the endpoint only when a base URL is configured, so existing llama.cpp
and vLLM setups do not change, and an explicit backend still wins. The model name is
configured explicitly, because each endpoint names models its own way (Ollama calls
this one `qwen2.5-coder:14b`). A run records the endpoint URL instead of a pinned
revision and digest, because the endpoint manages the weights, not qwenloop. The base
URL must be `http(s)://`. The API key is read only from the environment.
