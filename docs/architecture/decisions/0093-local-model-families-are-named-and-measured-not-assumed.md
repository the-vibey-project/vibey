# 0093 — Local model families are named and measured, never assumed

**Status:** proposed · **Date:** 2026-10-23 · **Cites:** ADR-0027, ADR-0064; sub-doctrines 8.d, 10.f · **Related:** ADR-0092 · **Issue:** #1662

## Context

#1662 asks for support for eight model families: Qwen Coder, DeepSeek Coder, Codestral, StarCoder,
Gemma, Llama, CodeLlama and CodeGemma. The local runner already talks to any model an Ollama
serves (`QWENLOOP_MODEL` names one), so nothing stopped a person naming `codestral:22b`. What was
missing was any way to know whether it would work.

It would not always. The runner drives a model through tool calls, and families differ: some
report tool-calling to Ollama and some do not. And knowing is harder than it looks. A first attempt
read each model's chat template from the registry, on the rule that a tool-capable template mentions
`.Tools`. That was **wrong** for the newer models: `gemma4:26b` has a 13-byte template yet its own
Ollama reports `tools`, and `qwen3-coder` ships a built-in renderer and no template at all. Ollama
decides capabilities from more than the template. A table kept in vibey would have been false for
exactly the models people reach for next. Even a true `tools` is only necessary: Qwen2.5-Coder 14B
reports it and still writes its calls out as text (`qwenloop` `DEFAULT_QWEN_ENDPOINT_MODEL`).

## Decision

**Name the families; get capabilities from the Ollama that will run the model; refuse only on a
positive "no".**

- `domain/model_families.py` names the eight families, each with the Ollama tag to start from. It
  carries no capability claim. Tags match by stem followed by a digit or hyphen, longest stem
  first, so `codellama` is not `llama` and `codegemma` is not `gemma`.
- `vibey models [--json]` lists the families with the `ollama pull` that fetches each, then the
  models the Ollama at `VIBEY_OLLAMA_URL` has, with the capabilities that Ollama's `/api/show`
  reports for each and what that makes the model worth trying for. A model Ollama will not describe is
  **unknown**, never "none". No Ollama is reported, not fatal.
- What a model "can be tried for" follows only what it reports: `tools` means BUILD may be tried (a
  run shows whether it works), `completion` means DESIGN and DECOMPOSE, which ask for JSON and need
  no tool-calling, and `insert` means fill-in-the-middle.
- The local runner refuses a model its own Ollama positively reports **without** `tools`, naming
  what it does report and pointing it at DESIGN and DECOMPOSE. Unknown passes: a model nothing says
  anything about is not one to turn away, and a server that is not an Ollama has no `/api/show`.

## What was measured

Measured against the local Ollama 0.40.9 (`/api/show`): `qwen2.5-coder:14b` and `:1.5b` report
`completion, insert, tools`; `deepseek-coder:1.3b` reports `completion` only; `gemma4:26b` reports
`completion, thinking, tools, vision`.

From the registry's template layer, for models with **no** built-in renderer (where the template is
what Ollama reads, and which agreed with every installed model checked): tool-capable are
`llama3.1:8b`, `llama3.2:3b` and `llama3.3:70b`; not tool-capable are `codestral:22b`,
`deepseek-coder:6.7b`, `deepseek-coder-v2:16b`, `starcoder:7b`, `starcoder2:7b`, `gemma3:12b`,
`codellama:13b` and `codegemma:7b`. These are an inference, not a local measurement, and the
command exists so a person gets the measurement for the tag they actually run. `qwen3-coder:30b`
declares a built-in renderer, so the registry says nothing about it; it was not measured.

## Consequences

- The five families that report no tool-calling cannot drive BUILD on this runner. They remain
  useful for DESIGN and DECOMPOSE, and `codestral`, `starcoder` and `deepseek-coder-v2` report fill-in-the-middle.
  Supporting them for BUILD would need a text tool-call protocol, which is a different feature.
- `llama` is the one new family that reports tools without a built-in renderer, so it is the first
  to try for BUILD; whether it drives a run well is a benchmark, not a flag.
- Tag stems are a small list kept by hand; a new family needs a line and a test.
