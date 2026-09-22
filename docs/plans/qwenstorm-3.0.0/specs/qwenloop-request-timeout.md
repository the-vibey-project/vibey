## Title
fix(qwenloop): a model request waits idle_timeout_seconds, not a hard-coded 300 s

## Why
`OpenAIServer.chat_stream` (src/vibey_runners/qwen/src/qwenloop/infrastructure/inference.py:133)
calls `urllib.request.urlopen(request, timeout=300)`. The configured `idle_timeout_seconds`
(src/vibey_runners/qwen/src/qwenloop/domain/config.py:23, default 900, validated at :81) is parsed
but read nowhere else. On 2026-09-22 three storm lanes sharing one local llama-server all died with
`TimeoutError: timed out` inside `chat_stream`, while the configured idle budget was 900 s. Sub-doctrine
8.c now keeps one loop instance per deployment, but a long prompt on a laptop can still exceed 300 s.

## Required behaviour
1. `OpenAIServer.__init__` (and so `LlamaCppServer`, `VllmServer`, `OpenAICompatServer`) accepts
   `request_timeout_seconds: float | None = 900`. `chat_stream` passes it to `urlopen`.
   `OpenAICompatServer` keeps its separate short `timeout_seconds` for health/model probes.
2. `idle_timeout_seconds = 0` means no timeout (`None` to urlopen); any positive value is used as-is.
3. The CLI composition (src/vibey_runners/qwen/src/qwenloop/cli/app.py `_server_for`, `_attach`, and
   wherever `LlamaCppServer`/`VllmServer` are constructed) passes `config.idle_timeout_seconds`.
4. A timeout still raises as today (the storm treats it as "unavailable"); only the duration changes.

## Where to change
- inference.py: `OpenAIServer.__init__` (find it above line 100), line 133, and the subclasses'
  constructors (lines ~200, ~224, ~254-290) so the kwarg reaches the base class.
- cli/app.py: `_attach` (~line 188) and `_server_for` (~line 198).

## Acceptance criteria
- [ ] With `idle_timeout_seconds = 900`, `chat_stream` calls urlopen with `timeout=900`.
- [ ] With `idle_timeout_seconds = 0`, urlopen gets `timeout=None`.
- [ ] Health checks still use their own short timeouts.
- [ ] The tenant's gates pass at its 100% coverage floor.

## Tests to write first (TDD)
- tests/test_inference.py: monkeypatch `urllib.request.urlopen` with a fake that records `timeout`;
  assert 900, custom value, and None for 0, for `OpenAIServer` and `OpenAICompatServer`.
- tests/test_cli.py: `_server_for`/`_attach` build servers whose request timeout equals the config's.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen
    python -m pytest -q -p no:cacheprovider
    python -m mypy --strict src/qwenloop
    (the tenant's addopts enforce --cov-fail-under=100)
    cd ../../.. && uv run ruff check . && uv run ruff format --check .

## Out of scope
Tool changes (a separate issue adds edit_file). Docs, CHANGELOG. Do not push. Commit as
`fix(qwenloop): ...`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
