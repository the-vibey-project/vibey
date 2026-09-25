# 0060 — gptossloop is the sovereign engine, and qwenloop is its opt-in Qwen twin

**Status:** accepted · **Date:** 2026-09-25 · **Cites:** sub-doctrines 8.a, 8.b, 8.c, 8.d, 10.f, 12.c, 12.e · **Related:** ADR-0005, ADR-0015, ADR-0016, ADR-0022, ADR-0027, ADR-0037, ADR-0038, ADR-0059

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md` and
`docs/index.md` (`tests/meta/test_adr_counts.py`), a nav entry in `properdocs.yml`, a breaking
entry in `CHANGELOG.md`, and an amendment to sub-doctrine 8.c that only the operator's merge
ratifies (Article II.3). It leaves two debts open, named under *Consequences*.

## Context

The local engine vibey called `qwenloop` did not run Qwen. Its runner
(`src/vibey_runners/qwen`) asked an OpenAI-compatible endpoint for `DEFAULT_ENDPOINT_MODEL =
"gpt-oss:20b"`, and vibey handed it the same model through `VIBEY_OLLAMA_MODEL`. Measured on
2026-09-25 before this change: `qwenloop run` in a throwaway repository, with no
`QWENLOOP_*` variable and no config file, recorded `"backend": "openai-compat"` and
`"profile": "gpt-oss:20b"` in its `meta.json`, and Ollama's `/api/ps` reported `gpt-oss:20b`
(family `gptoss`, 20.9B, MXFP4) as the model it had just loaded. The name had stopped
describing the engine when 8.d made GPT-OSS 20B this era's default model.

The engine was also default-off behind `VIBEY_FEATURE_QWENLOOP` / `[features] qwenloop`, while
8.b says the sovereign engine is "always on, never needing declaration". The domain config
already treated it as always on (`DEFAULT_ENGINES`), and the worker's resolver did not, so the
two disagreed about the most important engine in the tree.

The operator ruled: rename the engine that runs GPT-OSS to `gptossloop`, ship it on by
default, and keep `qwenloop` — the one that really has Qwen in it — off on shipment.

## Decision

1. **One runner package, two entry points.** The qwenloop tenant keeps its directory, package
   name, tests and floor, and gains a second console script. `gptossloop` runs
   `qwenloop.cli.app:gptoss_main`; `qwenloop` runs `qwenloop.cli.app:main`. A `RunnerIdentity`
   value (`qwenloop/domain/config.py`) names what differs: the engine's name, the prefix of the
   settings it reads, and the model it asks an endpoint for when nothing names one.
   - `gptossloop`: `GPTOSSLOOP_BASE_URL`, `GPTOSSLOOP_MODEL`, `GPTOSSLOOP_API_KEY`,
     `GPTOSSLOOP_CONFIG` (default `<user config dir>/gptossloop/config.toml`); model
     `gpt-oss:20b`.
   - `qwenloop`: the same names under `QWENLOOP_`; model `qwen3:14b`.

   Each reads only its own settings, so a model named for one never reaches the other.
   Everything else is the runner's protocol and is shared: run records under
   `.qwenloop/runs/`, the `QWENLOOP_TASK_FULLY_COMPLETE` marker, the `qwenloop-verdict` fence,
   the control verbs, the event envelope and the pinned llama.cpp/vLLM profiles. The runner is
   bumped to 0.3.0, the first version that ships `gptossloop`, and that is the descriptor's
   `min_version`.

   **Why not a package rename.** Renaming the tenant would move a directory, a Python package
   and a coverage floor that other lanes, the image, the release loop and storm tooling all
   name, to change none of the runner's behaviour. Two identities over one implementation is
   the smallest change that makes each name true, and it is the shape 8.d asks for anyway:
   the runner serves whichever free model the machine and the catalogue choose.

2. **Why `qwen3:14b`.** The project already names two Qwen models. `qwen2.5-coder:14b` is
   pinned for llama.cpp and vLLM, but on Ollama it writes its tool calls out as text
   (`docs/guides/local-models-ollama.md`, the claudeloop local-backend guide), and this runner
   drives the model through native tool calls. `qwen3:14b` emits native calls on Ollama's
   OpenAI-compatible endpoint, and the checked-in `docs/examples/qwenloop-local.toml` already
   chose it for that reason. Measured on 2026-09-25: `qwenloop run` with nothing configured
   asked for `qwen3:14b`, Ollama loaded it (family `qwen3`), and the run wrote the file its
   plan asked for and completed.

3. **gptossloop is on by default; qwenloop is opt-in.** `EngineId.GPTOSSLOOP` joins the local
   tier, and its switch is on when nothing sets it (`LOCAL_ENGINES_ON_BY_DEFAULT`). It is
   switched off only by saying so — `[features] gptossloop = false` or
   `VIBEY_FEATURE_GPTOSSLOOP=0` — in the same style as the other local switches. Reading an
   operator's written `false` as a declaration, rather than giving the sovereign default no off
   switch at all, is the one interpretation this record makes of 8.b's "never turned off": no
   default, environment or migration turns it off, and an operator who needs it off (a machine
   with no local model server) writes it down. `qwenloop` keeps `VIBEY_FEATURE_QWENLOOP` /
   `[features] qwenloop`, off on shipment, and — no longer being the sovereign default — needs
   its switch before a pool may name it.

4. **vibey hands each runner its own endpoint.** `VIBEY_OLLAMA_URL` becomes
   `GPTOSSLOOP_BASE_URL` and `QWENLOOP_BASE_URL` (`<url>/v1`). Only gptossloop is handed a
   model (`--ollama-model`, else `VIBEY_OLLAMA_MODEL`, else `gpt-oss:20b`), the one the
   sovereign providers use, so BUILD and DESIGN run the same model. qwenloop runs the Qwen
   model it names itself unless `QWENLOOP_MODEL` says otherwise, and `vibey loops` reports it
   that way.

5. **The sovereign providers are gptossloop's.** `QwenloopDesignProvider` and
   `QwenloopWorkPlanProducer` become `GptossloopDesignProvider` and
   `GptossloopWorkPlanProducer` (`gptossloop_design.py`, `gptossloop_decompose.py`), and the
   ledger names `gptossloop` as DESIGN's actor, because GPT-OSS is what ran. `--provider
   gptossloop` is the default; `--provider qwenloop`, the old name, is still accepted and read
   as gptossloop, and the CLI says so on stderr. A DESIGN provider on the Qwen model is not
   part of this change.

6. **Old meanings are said aloud, not guessed at.** An operator who set
   `VIBEY_FEATURE_QWENLOOP=1` to get the gpt-oss engine now gets both engines. `vibey worker`
   and `vibey doctor` print a note naming what the switch now means; `vibey loops` carries the
   same fact as a note on qwenloop (`RENAMED_ENGINES`); and a config that names qwenloop
   without its switch is refused with a message that says gptossloop is the engine it used to
   be.

## Consequences

- **Breaking.** The bare `qwenloop` command asks for `qwen3:14b`; a caller that relied on its
  gpt-oss default must run `gptossloop` or set `QWENLOOP_MODEL`. `gptossloop` ignores
  `QWENLOOP_*`, so a setup configured only through those variables must set `GPTOSSLOOP_*`
  (vibey's own `VIBEY_OLLAMA_URL` path does this for it). `VIBEY_FEATURE_QWENLOOP` and
  `[features] qwenloop` now switch on the Qwen engine, and `[engines].enabled` or
  `[phases.*].engines` naming qwenloop need that switch. The Helm chart's
  `ollama.qwenloopFeature` defaults to `false`, wires `GPTOSSLOOP_*` for the default engine, and
  pulls the new `ollama.qwenModel` only when qwenloop is on. DESIGN events are attributed to
  gptossloop from now on; events already in the ledger keep the actor they were written with.
- **Kept working.** The `qwenloop` command, its settings, its run records and its switch; the
  `--provider qwenloop` spelling; `bootstrap.qwenloop_enabled`; the `[qwenloop]` config table.
- **A default install with no local model server** now lists gptossloop in its local tier.
  Its doctor fails there, the startup sweep says it has no conformance, and the selector falls
  back to a paid engine as ADR-0038 already provides. That is the honest report of a machine
  that cannot run the sovereign default; an operator who wants it quiet writes
  `VIBEY_FEATURE_GPTOSSLOOP=0`.
- **Canon.** Sub-doctrine 8.c says `sovereignloop` is "what `qwenloop` becomes". That is now
  what gptossloop and qwenloop become together. The amendment is in this change, marked for
  the operator's ratification; the law changes only when the operator's merge carries it.
- **Debts left open.** (a) The shared run directory is still named `.qwenloop`, and the done
  marker and verdict fence still carry qwenloop's name: renaming the protocol would break every
  reader of existing runs for no behavioural gain, and belongs with a runner-protocol version.
  (b) The runner's model defaults are two literals chosen by this record; 8.d's catalogue,
  which chooses by the machine, should replace both when it lands.
