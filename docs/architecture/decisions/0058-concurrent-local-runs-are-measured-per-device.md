# 0058 — Concurrent runs of a local model are measured on each device, and unmeasured or stale means one

**Status:** accepted as mechanism; the amendment to sub-doctrine 8.c it proposes is **not** ratified by this record — only the operator's merge of the separate canon pull request ratifies it (Constitution Article II.3) · **Date:** 2026-09-24 · **Cites:** sub-doctrines 8.c, 8.j, 8.g, 10.f, 12.c, 12.e, and ADR-0045 · **Related:** ADR-0016, ADR-0018, ADR-0020, ADR-0045, ADR-0054 · **Evidence:** `docs/architecture/evidence/slots-2026-09-24-mac17-2.json` and its `.md` summary, produced by `vibey-gh slots calibrate` on this device

**Owes:** the conduct is the 8.c amendment drafted below, which is ratified separately
(ADR-0020: the record argues, the canon states). This record owes the advertised ADR count in
`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md`
(`tests/meta/test_adr_counts.py`), a nav entry in `properdocs.yml`, the `[local_models]` and
`vibey-gh slots` rows in the vibey-gh configuration and CLI references, and pointers to them in
`docs/reference/configuration.md` and `docs/reference/cli.md`. It leaves two debts open, named
under *Consequences*: a per-node calibration Job in the Helm chart, and durable storm run
records.

## Context

Sub-doctrine 8.c runs each loop as a single instance fed by a queue, and says of a model on the
operator's own hardware: *one run at a time*. 8.j says every part of the family fits itself to
the machine by measurement, never by a hunch, and never trades correctness for speed. Those two
sentences meet at one number — how many runs of a resident model the machine serves at once —
and on 2026-09-23 the operator ruled on it: **"C — measure, then decide."** Keep 8.c as
written, benchmark one slot against two by replaying storm-depth turns, and bring numbers
before any change to the canon. On 2026-09-24 the operator widened the ruling: *"we should not
stop at two, test and find out the ideal number, and same thing on all other devices that you
run on; make that ADR / law."*

The claim on the table was that two 32k-token slots reserve about the same KV cache as one
65k-token slot, and that few storm turns exceed 32k — so two half-size slots might double
throughput at no memory cost. ADR-0045 had counted 71 of 838 recorded turns over 32,768 tokens.

**A first run of this measurement was lost.** It ran on the morning of 2026-09-24 against the
storm's own lane records under `/private/tmp`; at 09:09 the machine rebooted, `/private/tmp`
was wiped, and the records, the corpus, the evidence and the unpushed code went with it. The
Ollama app also applied a staged update on relaunch (0.34.2 → 0.34.4). Nothing measured that
morning is cited here as evidence. Two failure modes it met are the reason for two mechanisms
below: a runner that answers HTTP 200 with no `done_reason` when its decode fails underneath
it, and another client loading a model on the production runner mid-step.

## Method

**The corpus is storm-shaped, and says so.** qwenloop records each run's tool results, answer
text, retries and per-turn input tokens (`events.jsonl`) under the storm's scratch directory,
not its payloads, and those records did not survive the reboot. So
`docs/plans/qwenstorm-3.0.0/tools/storm_turn_pool.py specs` builds the pool from durable,
committed material: each run is one of the storm's committed lane specs, planned with
qwenloop's own `build_plan` and system prompt, followed by `read_file` turns — with their real
arguments — whose results are the repository's real files at the corpus's commit, truncated as
qwenloop truncates them. That is the work lane time went to: reading code into context. When a
storm has fresh records, `storm_turn_pool.py lanes` rebuilds its real payloads instead, with the
same qwenloop functions. Depth in the pool is characters ÷ 3 (the fit calculus's conservative
estimate), used only to stratify and to keep every payload inside the window; the runner's own
`prompt_eval_count` on replay is the measured depth.

The pool is 1,096 turns in 40 runs (40 specs drawn with seed 0; sha256 `508685035d8a645e…`).
`vibey-gh slots corpus` drew **20 segments of 3 consecutive turns** (60 turns per step), five
segments in each depth stratum by estimate — below 16k, 16–32k, 32–48k, and 48k and over — so
the deep tail is measured, not sampled around (corpus sha256 `ae63b871ae3b62dc…`).

**The sweep.** `vibey-gh slots calibrate` starts its own `ollama serve` — the Ollama app's own
bundled binary, the production runner's version — on port 11435 with `OLLAMA_NUM_PARALLEL=N`
and `OLLAMA_NOPRUNE`, beside the production runner, which it never restarts or reconfigures.
It replays the corpus with N closed-loop workers, each sending one segment's turns in order (so
a worker keeps its prefix warm exactly as a lane does), through `/api/chat` with
`truncate: false`, `shift: false`, temperature 0, seed 42 and 768 output tokens. It samples
every second: wired memory and the swap counters from `vm_stat`, the free share from
`memory_pressure`, and what both runners hold resident from `/api/ps`. It reads the runner's
own log for `n_slots`, `n_ctx_slot`, KV cache sizes, loads, truncations, context shifts and
Metal device failures. One slot is measured twice, so fidelity has a baseline. A step during
which the production runner held a model is discarded and measured again once production is
idle. It stops at a broken bound or after two steps without a 10% gain. Every completed step is
checkpointed under `~/.local/state/vibey-gh/slots/progress/`, so this run was walked one step
at a time (`--max-runs 1, 2, …`), each step's evidence committed and pushed before the next
began — a push's own test suite never ran beside a measurement.

**The bounds** (`[local_models]`, re-read at every decision): peak wired memory within 80% of
physical memory; swap-outs no more than twice the one-slot rate, never judged below 64 MB/min;
no turn that ran at one slot failing; no truncation, context shift, device failure, reload or
eviction; every answer ending `stop` or `length`; structural agreement with the one-slot answers
(the tool calls made and their argument names, or plain text) no more than 0.05 below one
slot's agreement with itself. At one slot the memory bounds are reported, never refusing: one is
8.c's floor.

**Why beside production, not by restarting it.** The brief's method was `launchctl setenv
OLLAMA_NUM_PARALLEL` and a restart of the Ollama app. A relaunch applies a staged update —
it did so on 2026-09-18 and again at the 09:09 reboot — so a restart per step can change the
runner mid-measurement and makes "restore the original state" impossible. So the production
runner was never touched: nothing was set with `launchctl`, and restoring was stopping the
calibration runner. The rule ADR-0045 learned — two servers bidding for one GPU breach 8.c — is
kept by refusing to start while production holds a model, and by discarding any step during
which it loads one.

## Results

RESULTS PENDING — the sweep is running; this section is filled from the evidence file, step by
step.

## Decision

1. **The mechanism is `vibey-gh slots`**, generic over any device that runs Ollama: `corpus`,
   `calibrate` and `allowed`, with the seams in `vibey_gh/interfaces/slots_interface.py`
   (ADR-0016). It reads macOS through `sysctl`, `system_profiler`, `vm_stat` and
   `memory_pressure`, and Linux through `/proc`, `/sys` and `nvidia-smi`.
2. **Every platform assumption lives behind a seam** (#1116: Ubuntu 26.04 LTS is
   first-class, Windows follows, #1097). `DeviceProbeInterface` states the machine
   (`DarwinDeviceProbe`: `sysctl`, `system_profiler`, `sw_vers`; `LinuxDeviceProbe`: `/proc`,
   `/sys`, `nvidia-smi`, `/etc/os-release`); `HostMemorySamplerInterface` reads what it charges
   (`vm_stat` and `memory_pressure`; `/proc/meminfo`, `/proc/vmstat` and GPU memory, with
   cgroup limits to follow); `RunnerParallelismInterface` sets the production runner's
   parallelism and restarts it (`MacOSAppParallelism`: `launchctl setenv` and an app restart;
   `SystemdParallelism`: a clearly marked stub that renders the `Environment=` drop-in and
   raises until a Linux host measures it). `PlatformProbes` picks them; nothing else names an
   operating system. The calibration's own runner is a plain `ollama serve`, the same on both.
3. **Evidence is keyed to a device fingerprint**: hardware model, processor, memory,
   accelerator, operating system, runner version, model digest and context window. Evidence
   for another fingerprint is stale; so is evidence older than 30 days.
4. **`[local_models] concurrent_runs` is the declaration** (12.c), default `1`: 8.c as
   written, which probes nothing and needs no evidence. `"measured"` takes the ideal N the
   device's evidence supports, re-judged against today's bounds. A number above one runs only
   where the device measured it inside every bound and faster than one; otherwise one runs,
   and the refusal names what is missing. This repository declares `1`.
5. **Unmeasured or stale means one, out loud, and the gap closes itself** (12.e). `slots
   allowed` writes a calibration request beside the evidence; `storm-queue.sh` asks `slots
   allowed` on every pass instead of the host-wide `pgrep` it hard-coded, logs the answer and
   its reason, and when its queue empties it builds a corpus (its own lane records, else its
   committed specs) and runs `slots calibrate --if-requested` under the shared model lock.
6. **A calibration that is not clean is not evidence.** A step taken while the production
   runner held a model is discarded and measured again (twice at most); a run that never gets a
   clean step, or that ran on a runner version other than production's, is written to `--out`
   for the record and **not** recorded for the device. A 200 without a `done_reason` is a
   failed turn.
7. **A sweep survives a reboot.** Each completed step is checkpointed, keyed by fingerprint,
   corpus and method, and a rerun takes what it has.

## Proposed amendment to 8.c (not ratified here)

The sentence *"The instance takes on as much work at once as its capacity allows — for a model
running on the operator's own hardware, one run at a time — and no more."* would read:

> The instance takes on as much work at once as its capacity allows, and no more. For a model
> running on the operator's own hardware, that capacity is **the number of concurrent runs
> measured on that device and recorded as evidence** (8.j) — measured against the loop's own
> work, keyed to the device, the runner, the model and its context window, and held to the
> bounds 8.j names: wired memory within its ceiling, swap not rising, no prompt refused or cut
> that one run would have served, and every answer as faithful as one run's. **Unmeasured or
> stale means one.** A number the evidence does not support is never run, however it is
> declared, and the operator may always declare fewer (12.c).

It rules the method, not a number: it stays true whatever any device measures, including this
one. Ratification is the operator's merge of the separate canon pull request (Article II.3);
nothing in this record or its pull request changes the canon. With the amendment ratified,
setting `concurrent_runs = "measured"` is the operator's choice; this record does not make it.

## Consequences

- The storm reads one lane at a time on this device today, as before, but now because the
  declaration and the evidence say so rather than because a `pgrep` was written into a shell
  script. A device whose evidence supports more can run more once the operator declares
  `"measured"`, and one whose runner or model changes falls back to one and asks to be measured
  again — as this device's own evidence would have gone stale at the 0.34.2 → 0.34.4 upgrade.
- **The production runner must match the calibrated one.** The lanes call `/v1` without
  `num_ctx`, so the app's `OLLAMA_CONTEXT_LENGTH` sizes every slot. Running N lanes needs the
  app started with `OLLAMA_NUM_PARALLEL=N` and the calibrated context per slot; a runner that
  sizes slots differently is not the runner that was measured.
- **Owed: the cluster.** Each node that serves a model is its own device. The chart runs one
  Ollama pod with `contextLength: 32768` — a window that refuses or truncates every storm turn
  deeper than that — and does not template a calibration Job. The documented procedure is a Job
  pinned to the node, inside the runner's pod network, with `VIBEY_GH_SLOTS_DIR` on a volume
  the workers share; until it is templated, a node without evidence runs one, which is safe. No
  cluster node was measured, and no number is claimed for one.
- **Owed: durable storm records.** The storm keeps its lanes, and so every run's record, under
  `/private/tmp`; a reboot erases the only record of what the model was asked. They belong
  somewhere that survives one.
- Other devices — the self-hosted runner's host, cluster workers, adopters' machines — were not
  reachable from this run and carry no evidence; each runs one until it is calibrated.

## Alternatives considered

- **Keep the host-wide `pgrep`.** It is 8.c as written, but it is a literal, not a
  measurement, and it cannot say why or when to change (12.c, 8.j).
- **A single number for every device in the canon.** Rejected: the right number depends on the
  device, the runner, the model and its window; a canon that named one would be false on the
  next machine. The canon rules the method.
- **Restart the production runner per step.** Rejected: a relaunch applies a staged update the
  operator had not asked for, and changes the runner under the measurement.
- **Reconstruct the lost run from memory.** Rejected (10.f): a number nobody can re-read is not
  evidence.
