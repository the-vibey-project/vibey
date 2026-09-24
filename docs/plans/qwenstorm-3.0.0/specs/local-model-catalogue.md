## Title
feat(models): support Qwen3.8-27B, Qwen3.6-27B, Qwen3.6-35B-A3B and GPT-OSS 20B on both Ollama and llama.cpp, with RAM-tiered defaults

## Why
The operator requires (2026-09-22) that vibey run these local models, on **both** Ollama and
llama.cpp, and pick a sensible default for the machine it runs on. Today:
- qwenloop pins exactly one llama.cpp model, Qwen2.5-Coder-14B-Instruct Q5_K_M
  (src/vibey_runners/qwen/src/qwenloop/infrastructure/profiles.py:9-18), plus one vLLM profile;
- the Ollama default is hard-coded as `qwen2.5-coder:14b` twice: vibey's
  src/vibey/infrastructure/engines/ollama_chat.py:39 (`DEFAULT_OLLAMA_MODEL`) and qwenloop's
  src/vibey_runners/qwen/src/qwenloop/domain/config.py:15 (`DEFAULT_ENDPOINT_MODEL`);
- nothing chooses a model by hardware, though the family already probes memory
  (src/vibey_tools/gh/vibey_gh/fit.py:273, `sysctl -n hw.memsize`) — reuse it (sub-doctrine 10.e).

Sub-doctrine 8.b keeps a sovereign local engine always on, and 8.c runs it as one instance per
deployment, so the model that instance loads decides most of the storm's speed and quality.

## Operator's model tiers (the requirement for default selection)
| Unified RAM | Default (first) and alternatives |
|---|---|
| 8 GB (base M1–M4) | Gemma 4 E2B; Qwen 3.5 4B — 25–45 tok/s, chat and summarization |
| 16 GB (M2–M4 Pro/Max) | Qwen 3.5 9B Q4; Llama 3.1 8B Q4 — ~25–40 tok/s |
| 24–32 GB (M4 Pro / M5 Pro) | **GPT-OSS 20B** (best daily driver for reasoning); **Qwen3.6-27B** (high-quality dense) |
| 48–64 GB (M4 Max / M5 Max) | **Qwen3.6-35B-A3B** (MoE, default fast all-rounder); Llama 3.3 70B Q4 (heavier analysis) |
| 128 GB (M5 Max / Studio) | DeepSeek V4 Flash (284B); Qwen3 235B-A22B |

The throughput figures are the operator's guidance, not measurements of this code; the lane must
record its own measurements (see qwenloop telemetry, #382) rather than restate them.

## Required behaviour
1. **One catalogue, as data** (everything-as-code, 12.c): each entry names the model, its total and
   active parameters, minimum RAM tier, context window, and, per backend:
   - **llama.cpp:** a pinned GGUF (Hugging Face repository, revision, filename, sha256, size,
     quantization) that qwenloop's existing `ModelCache` installs and verifies;
   - **Ollama:** the library tag.
   Required entries: **Qwen3.8-27B**, **Qwen3.6-27B**, **Qwen3.6-35B-A3B**, **GPT-OSS 20B**, plus the
   existing Qwen2.5-Coder-14B. Known GGUF sources (verify, then pin): `unsloth/Qwen3.8-27B-GGUF`,
   `unsloth/Qwen3.6-27B-GGUF`, `unsloth/Qwen3.6-35B-A3B-GGUF`, `ggml-org/gpt-oss-20b-GGUF`. Every
   digest, revision, size and Ollama tag is fetched from the source and recorded; none is invented.
   An entry that cannot be pinned is left out and listed as a follow-up.
2. **Both backends for every required model:** qwenloop's managed llama.cpp server loads the pinned
   GGUF (with `--jinja`), and an Ollama (or any OpenAI-compatible) endpoint serves the tag. vibey's
   DESIGN, DECOMPOSE and VISUAL_DESIGN providers (`OllamaChatClient`) work against both.
3. **Reasoning models:** GPT-OSS emits a separate reasoning channel (llama.cpp:
   `reasoning_content`; Ollama: `thinking`). Parsers use only the final answer and never treat
   reasoning text as a tool call or as JSON output. The same for Qwen3.x thinking output.
4. **RAM-tiered default:** with no model configured, vibey and qwenloop pick the tier's default from
   the table above, using the family's memory probe. An explicit model (config key, environment
   variable, or flag) always wins, and the chosen model and the reason are logged at startup.
5. **One source of truth for the default:** both hard-coded `qwen2.5-coder:14b` constants read the
   catalogue's tier default instead.
6. **Verification:** `qwenloop model verify <entry>` checks the pinned artifact; `vibey doctor`
   reports the selected model, its backend, and whether it is installed or served. Live runs per
   model and backend are recorded as evidence where available (a machine with the RAM), and stay
   "unverified" where not — never claimed.

## Where to change
- qwenloop: src/vibey_runners/qwen/src/qwenloop/infrastructure/profiles.py (catalogue),
  domain/config.py:15, the ModelCache install/verify, the managed server argv (`--jinja` already set).
- vibey: src/vibey/infrastructure/engines/ollama_chat.py:39 and the providers' response parsing
  (qwenloop_design.py, the decompose producer, and the VISUAL_DESIGN provider from #324).
- Memory probe: reuse src/vibey_tools/gh/vibey_gh/fit.py's `hw.memsize` reading (Linux: /proc/meminfo).
- Chart: `ollama` values (the model the in-cluster Ollama pulls) follow the catalogue.

## Acceptance criteria
- [ ] The catalogue has pinned entries for all four required models on both backends, with no invented values.
- [ ] Default selection matches the tier table for 8, 16, 24, 32, 48, 64 and 128 GB (unit tests with a faked probe).
- [ ] Reasoning output from GPT-OSS and Qwen3.x never reaches the JSON or tool-call parsers (fixtures from real responses).
- [ ] An explicit model overrides the tier default everywhere.
- [ ] `qwenloop model verify` and `vibey doctor` report the selected model and its state.

## Tests to write first (TDD)
- Catalogue schema test (every entry complete; sha256 is 64 hex; tier coverage).
- Tier selection tests with a fake memory probe.
- Parser tests using recorded llama.cpp and Ollama responses that include reasoning fields.

## Checks the lane must run (all must pass)
The root gates (ruff, mypy --strict, lint-imports, per-layer 100% coverage) and the qwen tenant's
own suite at its 100% floor.

## Out of scope
Downloading models in CI. Changing the storm's own runtime (handled separately).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
