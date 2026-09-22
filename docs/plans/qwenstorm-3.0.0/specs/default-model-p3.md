## Title
feat(gh)!: vibey-gh's local reviewer and fit default to gpt-oss:20b

## Why
Sub-doctrine 8.d requires the default local model to be the gold standard for the machine, with the evidence and date recorded. The operator decided on 2026-09-22 that the default FOSS model is **GPT-OSS 20B on Ollama**. Evidence (M5, 24 GB, one 10-turn agent session): GPT-OSS 20B via Ollama took 86 s with a 131k context in 13.1 GB, against 215 s for Qwen2.5-Coder-14B on llama.cpp at 32k; in a live storm lane it averaged about 13 s per turn. Ollama loads it with its full 131072-token context. Note: Ollama's GPT-OSS GGUF does not load in llama.cpp (architecture `gptoss` vs `gpt-oss`), so the llama.cpp side waits for a pinned GGUF under #383; this issue changes the Ollama default only. vibey-gh's sovereign review fallback defaults to `qwen2.5-coder:14b` (src/vibey_tools/gh/vibey_gh/config.py:502 and :1754), `vibey-gh fit --model` defaults to it (src/vibey_tools/gh/vibey_gh/cli.py:1615), and the tenant's own config names it (src/vibey_tools/gh/.vibey-gh.toml:56).

## Required behaviour
1. Those three defaults and the tenant config are `gpt-oss:20b`.
2. Tests that assert the default (e.g. src/vibey_tools/gh/test/test_sovereign_first.py:893) follow. Tests whose fixtures describe measurements of qwen2.5-coder:14b (test_fit.py, test_fitloop.py, test_operation_estimate.py) stay — they are recorded evidence, not defaults — and `vibey_gh/fit.py`'s measured constants stay.
3. Rendered automation still installs without drift (root and src/vibey_tools/gh): check with `python -c "from vibey_gh.config import load_config; from vibey_gh.install import installed; print(installed(load_config(), local=False))"` in both directories.

## Acceptance criteria
- [ ] Defaults are gpt-oss:20b; the gh suite passes; both drift checks report no problems.
- [ ] black --line-length 100, isort and the root ruff format all pass on the gh tenant.

## Tests to write first (TDD)
The config default test and the fit CLI default test in src/vibey_tools/gh/test/.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q && python -m black --check --line-length 100 vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    cd ../../.. && uv run ruff format --check .

## Out of scope
vibey core and qwenloop (parts 1-2), docs. Commit as `feat(gh)!: ...` with a `BREAKING CHANGE:` footer.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
