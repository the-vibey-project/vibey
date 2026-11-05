# 0099 — Heretic v2 of GPT-OSS 20B is the sovereign default model

**Status:** proposed · **Date:** 2026-11-04 · **Cites:** sub-doctrines 8.a, 8.d, 8.j, 10.f, 12.c · **Related:** ADR-0027, ADR-0038, ADR-0064, ADR-0093

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md` (`tests/meta/test_adr_counts.py`), a nav entry in `properdocs.yml`,
and a fragment in `changelog.d/`. All are included in the change that carries this record.

## Context

ADR-0064 established `gptossloop` on GPT-OSS 20B (`gpt-oss:20b`) as the sovereign default
engine, on by default and preferred first for BUILD (ADR-0038), and as the default model
behind the sovereign DESIGN and DECOMPOSE providers (ADR-0027).

In an autonomous coding loop, a model must inspect arbitrary source trees, execute shell
commands, analyse security properties, and repair failing checks. Stock `gpt-oss:20b`
refuses 98 of 100 prompts on the [Heretic](https://github.com/p-e-w/heretic) refusal
benchmark. When a coding prompt or repository text triggers a refusal reflex inside an
unattended DESIGN, DECOMPOSE or BUILD turn, the loop stalls for a reason that has nothing
to do with the operator's authority or the safety of the work. In vibey, safety is
enforced by deterministic bounds — human gates, per-cycle spending and turn caps,
worktree and container isolation, environment scrubbing, and an append-only PostgreSQL
ledger — rather than by a model's alignment reflexes.

The Heretic project publishes two abliterated builds of GPT-OSS 20B:

- **v1 (`p-e-w/gpt-oss-20b-heretic`):** 58/100 test prompts refused, KL divergence
  **0.96** from the original model.
- **v2 (`p-e-w/gpt-oss-20b-heretic-v2`, built with Heretic v1.1.0):** **49/100** test
  prompts refused (against 98/100 for stock), KL divergence **0.1248** from the original
  model, under the **Apache-2.0** license.

Ollama's Hugging Face GGUF integration serves `p-e-w/gpt-oss-20b-heretic-v2` directly via
`hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`, which uses the same native
`MXFP4` mixture-of-experts quantization and 20B architecture as stock `gpt-oss:20b`.

## Decision

1. **A two-variant sovereign model catalogue (`src/vibey/domain/sovereign_model.py`).**
   `SovereignModels` (declared by `SovereignModelsInterface`) defines the two sovereign
   builds of `SOVEREIGN_FAMILY = "gpt-oss:20b"`:
   - `heretic` (default): `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`,
     derived from `p-e-w/gpt-oss-20b-heretic-v2` (Apache-2.0 weights; ~12.1 GB download).
   - `stock`: `gpt-oss:20b` from the Ollama library (Apache-2.0 weights; ~14 GB download).

2. **Why v2 over v1.** Heretic v2 reduces refusals further (49/100 vs 58/100) while
   keeping KL divergence at 0.1248 (nearly an order of magnitude tighter than v1's 0.96),
   preserving the non-refusal behaviour and coding capability of the base model.

3. **License boundary.** The Heretic tool itself is licensed under AGPL-3.0 and is **not**
   a dependency or runtime component of vibey. vibey consumes only the published Apache-2.0
   model weights through Ollama.

4. **One resolution precedence everywhere (12.c).** `SovereignModels.from_environment()`
   resolves the active model tag in order:
   1. Explicit `--ollama-model` CLI flag;
   2. `VIBEY_OLLAMA_MODEL` environment variable;
   3. `VIBEY_SOVEREIGN_MODEL` environment variable (`heretic` or `stock`, case-insensitive;
      an unknown value raises `ValueError` naming the valid keys);
   4. `DEFAULT_SOVEREIGN_TAG` (`heretic`).

   Both `--ollama-model` and `VIBEY_OLLAMA_MODEL` also accept the variant keys `heretic`
   and `stock` and resolve them to their full tags, while passing any other Ollama tag
   through unchanged. Empty or whitespace-only values count as unset.

5. **Single source across conductor and runner.** `DEFAULT_SOVEREIGN_TAG` is wired into
   `OllamaChatClient`, `OllamaResidency`, `domain/local_stack.py`, `vibey doctor
   --sovereign-fit`, and `qwenloop`'s `DEFAULT_ENDPOINT_MODEL` for `gptossloop`. Because
   the `qwenloop` workspace tenant does not import `vibey`,
   `tests/meta/test_sovereign_model_agreement.py` asserts that the tenant's constant
   equals `DEFAULT_SOVEREIGN_TAG`.

## Evidence and verification status (sub-doctrine 10.f)

- **Verified:**
  - The model card metrics for `p-e-w/gpt-oss-20b-heretic-v2` (49/100 refusals vs 98/100
    original, KL divergence 0.1248, Apache-2.0 license, Heretic v1.1.0).
  - The Hugging Face Ollama manifest at
    `https://huggingface.co/v2/mradermacher/gpt-oss-20b-heretic-v2-GGUF/manifests/MXFP4_MOE`
    resolves cleanly to a ~12.1 GB `MXFP4_MOE` GGUF model layer plus a template layer
    (`Q4_K_M` is ~15.8 GB).
  - Unit, CLI golden, and cross-tenant agreement tests pass at 100% branch coverage.
- **Not yet verified:**
  - `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` has **not** yet been pulled
    with `ollama pull` or run through `vibey doctor --sovereign-fit` or an end-to-end
    `gptossloop` tool-calling benchmark on the reference host. Existing measured latency,
    VRAM, and throughput tables in `docs/reference/system-requirements.md` and
    `docs/guides/local-models-ollama.md` remain explicitly attributed to stock
    `gpt-oss:20b` until re-measured against the Heretic v2 tag.

## Consequences

- Default local installs and `vibey loops --json` now report
  `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` as `gptossloop`'s model and
  `12.1 GB` as its download size.
- Operators who want the unmodified OpenAI release can select it with
  `VIBEY_SOVEREIGN_MODEL=stock`, `VIBEY_OLLAMA_MODEL=stock`, or `--ollama-model stock`.
- **Rule status.** Choosing which build of the era's default model sits at the top of the
  catalogue is a mechanism and catalogue update under sub-doctrine 8.d, not a new rule of
  conduct (ADR-0020).
