# 0045 — Every deployment measures the machine it runs on and fits itself to it, and never trades correctness for the fit

**Status:** proposed · **Date:** 2026-09-22 · **Cites:** sub-doctrines 8.b, 8.c, 8.d, 8.g, 8.h, 10.f, 12.c, and 8.j which this record implements · **Related:** ADR-0038, ADR-0042, ADR-0046 · **Evidence:** measured on the operator's 24 GiB Apple Silicon MacBook on 2026-09-22 while the QwenStorm ran; the numbers below are in `docs/plans/qwenstorm-3.0.0/bench/host-tuning.toml` and were produced by `bench/host-sweep.py`

**Owes:** nothing new as conduct — 8.j is the conduct and is ratified separately (ADR-0020: the
record argues, the canon states). It owes the docs wave a `[local_context]` row in
`docs/reference/configuration.md`, a `vibey doctor` line in `docs/reference/cli.md`, and the
advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md`
(`tests/meta/test_adr_counts.py`).

## Context

The storm ran all evening on a 24 GiB machine and the machine was thrashing: swap 17.0 of
18.4 GiB used, 10.6 million swapouts, 71 MiB genuinely free. The obvious reading — the machine
needs more swap — is wrong twice over. macOS exposes no swap knob at all (no `swapon`, no
swappiness, no swap partition; `dynamic_pager` does not run on a modern system, the kernel
grows swapfiles into free disk on demand, and with 498 GiB free the 18.4 GiB figure was never a
ceiling). And more swap could not have helped even where it is configurable, because **18.85
GiB of the 24 was wired** — memory the kernel cannot page out at all. Swap does not touch
wired pages.

The wired memory was one process. `llama-server` served `gpt-oss:20b` at `100% GPU` with a
131,072-token context. On Apple Silicon the GPU shares system memory, so a model served on the
GPU has its weights **and its KV cache** wired through Metal — and `ps` reported 14.85 GiB RSS,
which understates it. A check watching resident memory would have called this machine healthy
while it swapped 16.7 GiB.

So the question was never how much memory the model may have. It was how much context a lane
actually uses — which the run ledger already recorded, turn by turn, and nobody had read.

## Evidence

Across **838 recorded turns** of real lane work (`input_tokens + output_tokens` per turn, from
each run's `events.jsonl`): p50 20,070 · p90 32,026 · p95 36,816 · p99 42,979 · **max 49,118**.
Not one turn exceeded 64k. The 131,072-token context was never half reached.

A sweep with the storm paused, each row reloading the model and measuring cost, speed and
fidelity together:

| cfg | context | KV | wired | tok/s | fidelity |
|---|---|---|---|---|---|
| A | 131072 | f16 | 18.55 GiB | 28.0 | 8/8 |
| B | 65536 | f16 | **17.25 GiB** | **32.5** | 8/8 |
| C | 65536 | q8_0 | inconclusive — the setting never reached the model | | |

Halving the context to the measured need cost nothing and returned 1.30 GiB of wired memory
and 16% more throughput. C is recorded as unresolved rather than refuted: Ollama 0.34.2 did not
pass `OLLAMA_KV_CACHE_TYPE` through to `llama-server`, whose argv carried no `--cache-type-k`.

Two findings cut against the obvious framing and are the reason this is a decision rather than
a tweak. First, **vibey hard-codes no 131,072 anywhere** — it hard-codes **32,768** in four
places (`src/vibey/domain/config.py:35,191`, `ollama_chat.py:86` as an un-overridable class
attribute, `descriptors.py:285,313`), and 32,768 would have truncated 71 of the 838 turns. The
shipped default errs small exactly where the storm's erred large. Second, the first attempt at
row C started a second `ollama serve` beside the running one; Metal failed with
`kIOGPUCommandBufferCallbackErrorOutOfMemory` and it read convincingly as "quantisation breaks
the model". It was two servers bidding for one GPU — and a breach of 8.c by the very experiment
measuring the machine that rule exists to protect.

## Decision

1. **A deployment measures its host and fits itself to it**, and keeps doing so as the host
   changes: context window, model choice, residency, concurrency, batch sizes. A value that
   could be measured is not hard-coded. 8.g requires the measurement; 8.j requires acting on it.
2. **The measurement is recorded with the value it justifies**, in a file in the repository
   (12.c), so a later reader sees what was true, when, and on what machine. `bench/host-tuning.toml`
   is that record for this host; the method transfers, the numbers do not.
3. **Fidelity is measured in the same breath as cost.** Anything bought with speed or memory is
   rejected whole if correctness moves. A faster wrong answer is not an optimization, and a
   quantised cache is the cheapest memory available right up to the point the model starts being
   wrong — which no cost-only sweep would notice.
4. **Find limits by overshooting and stepping back**, and record the overshoot. A boundary
   nobody crossed is a guess.
5. **Measure what the hardware charges, not what a tool reports.** On unified memory that means
   wired, not resident. On a discrete-GPU host the weights sit in VRAM and none of this applies,
   which is why thresholds are per-host and re-measured rather than copied.
6. **The operator's declared value always wins** (12.c). A measured default is a default.

## Consequences

`docs/plans/qwenstorm-3.0.0/qwen-storm.toml` moves to `context_window = 65536` against the
measurement above. The lane `gap-host-context-tuning` implements the automatic path: a pure
`HostContextPolicy` in `domain/` choosing a window from host facts, a `HostMemoryReader` in
`infrastructure/` reading them per platform (8.h: macOS and Arch), a `[local_context]` config
table whose `window` key overrides unconditionally, and a `vibey doctor` line reporting the
choice with its evidence. Wiring the chosen number into the four hard-coded 32,768 sites is
deliberately a separate lane.

Re-measuring is owed whenever the host changes, the model changes (8.d), or Ollama begins
passing the KV cache flag. This record is mechanism; the conduct it serves is 8.j.
