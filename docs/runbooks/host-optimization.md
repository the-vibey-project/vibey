# Host optimization

How the machine vibey runs on is kept healthy and fitted to its workload, with every change
declared in the repository, applied under a gate, measured week after week, and reversible.
It answers the operator's request of 2026-10-01: "anything you can do to improve system
health over time and keep the system still fully optimized".

Everything here is declared in [`scripts/host_tuning.toml`](https://github.com/the-vibey-project/vibey/blob/develop/scripts/host_tuning.toml)
(ADR-0045, fitted to the iron; ADR-0051, configuration in TOML). A setting is never changed by
a one-off command. It is declared, then applied by the tool, which journals the value it
replaced.

```bash
# Run these with a plain python3 (3.11 or later), never under `uv run`: uv holds its own
# cache while its child runs, so the uv-cache reclaim would wait on itself.
python3 scripts/host_health.py tune check           # declared against actual; exit 1 on drift
python3 scripts/host_health.py tune plan            # what apply would do, touching nothing
python3 scripts/host_health.py tune apply           # apply what each item's gate allows
python3 scripts/host_health.py tune apply --only uv_cache
python3 scripts/host_health.py tune undo ollama_kv_cache_type
```

## Classes and gates

Each item has a class, and the class decides what lets `tune apply` touch it
(`[host_tuning.gates]`; sub-doctrine 12.d: a gate, never judgement).

| Class | What it is | Its gate |
|---|---|---|
| **A** | Cannot reach the model or a running experiment, and is reversible or regenerable | Always |
| **B** | Changes the model's behaviour, speed or memory | `adopted = true`, set in a merged pull request that cites a review-canary run which held against the baseline |
| **C** | The operator's call: a desktop settings pane, the queue's database, deleting a model, hardware | `operator_approved` names the operator's approval. Even then, a step that needs root or a settings pane is printed for a person, never performed |

The tool never restarts a service and never runs `sudo`. A change that needs a restart is
reported as `pending-restart` by `tune check` until the service's own start time is later
than the change.

| `tune check` state | Meaning |
|---|---|
| `in-force` | The host has what is declared |
| `proposed` | It differs, and the item's gate is closed: nothing is wrong yet |
| `drift` | It differs, and the gate is open: apply it, or the declaration is wrong |
| `pending-restart` | Applied, but the service started before the change |
| `not-received` | Set, but the model runner's argv shows the server never passed it on (ADR-0045 found this for the KV cache type on Ollama 0.34.2) |
| `over-limit` | A log past its declared size |
| `reclaimable`, `listed` | A cache's size, or the models on disk, for information |
| `absent`, `not-applicable`, `unknown` | Not on this host, not on this platform, or unreadable (with the reason) |

`check` exits 1 when an item whose gate is open is `drift`, `not-received`,
`pending-restart` or `over-limit`.

How the Ollama environment is set, per platform:

- **macOS.** The Ollama app hands its server the launchd session environment when it launches
  (`launchctl setenv`, as Ollama's FAQ documents). A `launchctl setenv` does not survive a
  log-out, so `apply` also writes a login agent,
  `~/Library/LaunchAgents/dev.vibey.host-tuning.ollama-env.plist`, that re-asserts exactly
  what the journal says is applied. `undo` restores the prior value, or unsets the variable if
  it had none, and rewrites the agent (or removes it when nothing applied remains). The app
  must then be quit from its menu-bar icon and opened again.
- **Linux.** `apply` stages a systemd drop-in with `Environment=` lines in
  `~/.local/state/vibey/host-tuning/staged/` and prints the `sudo install` and
  `systemctl restart` commands that install it.

The journal is `~/.local/state/vibey/host-tuning/journal.jsonl`. It is append-only: an undo is
a new entry that supersedes the apply.

## The measured budget

Measured on the operator's MacBook Pro (Mac17,2, Apple M5, 10 cores, 24 GiB, APPLE SSD
AP1024Z) on 2026-10-01 and 2026-10-02, while the large-diff review experiment
(`research/large-diff-review`, PR #1328) ran on its Ollama. Every figure was read without
sudo: `proc_pid_rusage` per process (footprint, and disk bytes written since each process
started), `vm_stat`, `sysctl vm.swapusage`, `top`, and `smartctl` on `disk0`, sampled every
30 s for 29.5 minutes (2026-10-02 00:39–01:09 UTC). `gpt-oss:20b` stayed loaded at
`num_ctx 65536` the whole time, serving requests on and off.

### Memory

Demand is about twice the machine. The process footprints add up to roughly 49 GiB on a
24 GiB host, so macOS holds the rest compressed and in swap.

| Group | Footprint, mean (GiB) | Of which compressed or swapped (top CMPRS, one sample) |
|---|---|---|
| Ollama (`llama-server`, `gpt-oss:20b`) | 18.5 (16.3–20.2) | 3.7 GiB |
| Docker Desktop's VM (with a 10-node Kubernetes cluster and the runner) | 8.9 | 8.1 GiB, almost all of it |
| Other processes (about 230) | 4.5 | |
| Browser | 3.7 | |
| VS Code | 3.7 | |
| `node` (53 processes, mostly agent MCP servers) | 2.7 | |
| Agent sessions (Claude and others) | 2.0 | |
| Python (including `uvx` MCP servers) | 1.1 | |
| Postgres | 0.7 | |

- **Wired:** 16.8–16.9 GiB, almost all of it the model's weights and KV cache held through
  Metal. Wired memory cannot be paged out.
- **Swap in use:** 15.7 to 22.7 GiB during the window (16.9 GiB at its start, 20.9 GiB at its
  end). macOS grows swap files on demand; it is not a ceiling.
- **The compressor** held 31.9 GiB of pages in 3.5 GiB.
- The model's own footprint was 3.7 GiB compressed or swapped in one sample. Its weights are
  paged out between requests and paged back in for the next one, which is a likely reason
  generation speed varies with host state (12–34 tok/s in the evidence track). That reading
  is **inferred**, not measured here.
- Docker Desktop's VM may use **24576 MiB**, the whole machine (`MemoryMiB` in its settings),
  and runs Docker Desktop's built-in Kubernetes with **10 nodes**. `docker stats` measured the
  kind nodes at 16 MiB to 740 MiB each, about 6.4 GiB together. The Kubernetes API server did
  not answer `kubectl` (TLS handshake timeouts), itself a sign of the thrashing. The
  self-hosted runner's own container used 48 MiB idle.

### What drives the SSD's writes

Over the 29.5-minute window:

| Source | GB/h | Share |
|---|---|---|
| SSD host writes (`smartctl` data units written) | **152.5** | 100% |
| Swap-outs (`vm_stat` Swapouts × 16 KiB page) | **130.1** | **85%** |
| Every readable process's own file writes (`proc_pid_rusage`) | 1.8 | 1.2% |
| — of which Postgres | 1.2 | |
| Pageouts of file-backed pages | 2.7 | |
| Unattributed (kernel, file-system metadata, root's processes) | about 20 | |

Swap-ins ran at 119.6 GB/h at the same time: the machine was moving about 120–130 GB/h each
way between memory and the SSD. Over the whole uptime the counters agree. `top` reported
2095 GiB written to disk in about 29 hours since boot, and `vm_stat` 96.8 million swap-outs
(1.59 TB at 16 KiB), about three quarters of it. The intervals with an active request ran
higher (median 135 GB/h) than those without (103 GB/h), but swap churned in both, because the
model stayed resident and wired in both.

**Measured, and inferred.** Measured: every counter above. Inferred: that a `vm_stat`
swap-out is 16 KiB written to the swap file. The compressor writes compressed segments, so the
swap-out bytes are an upper bound on what reached the swap file (not verified). Per-write
attribution would need `fs_usage`, which needs sudo, so the evidence is the counters. Even so,
nothing else readable writes more than 2 GB/h, so the earlier hypothesis holds by
elimination: **the SSD's 36.5 TB in 337 power-on hours is mostly the price of memory
overcommit, and the lever is memory, not the disk.**

### Model reloads

Each `starting llama-server` line in the Ollama server log is one model load. There were
**166 loads on 2026-10-01**, at **168 distinct `num_ctx` values** since 2026-09-27. Of 358
loads since 2026-09-28, **298 changed the context size or the model**: clients ask for a
different `num_ctx` per request, and Ollama reloads the model for each one. The evidence track
measured 72% of CI review requests reloading, at a median of 4.8 s each. Of 631 gaps between
requests, 129 were longer than Ollama's default 5-minute keep-alive and 38 longer than 15
minutes.

### Disk

The data volume had 458 GiB free (49% used). The regenerable caches were large. On
2026-10-01, `~/.cache/uv` held 82 GB, `~/.npm/_cacache` 11.9 GB, and Docker's build cache
6.8 GB (none of its 68 records active). The Ollama models take 48 GB, and the Docker VM's
disk image 20 GB. The Postgres server log was 29 MiB. Free disk is not this machine's
problem, so reclaiming caches is hygiene, not a health lever.

## The plan

| Item | Class | Expected effect | Risk |
|---|---|---|---|
| `ollama_fixed_num_ctx`: every lane sends one fixed `num_ctx` | B | Most reloads stop (298 of 358 were context changes); seconds per request, and the model is no longer read again from the SSD | A code change in the callers (the review lane, `OllamaChatClient`); a fixed size large enough for the biggest diff costs KV memory on every request |
| `ollama_max_loaded_models` = 1 | B | A second model can never be co-resident with `gpt-oss:20b` | Another model's request evicts and reloads it |
| `ollama_num_parallel` = 1 | B | None today (the runner already has `-np 1`); pins it | Queueing only |
| `ollama_keep_alive` = 15m | B | About 91 fewer expiry reloads over those four days | ~16 GiB stays wired up to 10 minutes longer in each idle gap; the weekly swap figures must not rise |
| `ollama_flash_attention` = 1 | B | Little on its own (`--flash-attn auto` already); the precondition for a quantised KV cache | Can change numerics slightly |
| `ollama_kv_cache_type` = q8_0 | B | About 0.65 GiB of wired memory back at 65536 tokens | Can change outputs; `check` must first show `--cache-type-k` reached the runner |
| `docker_kubernetes` off | C | About 6.4 GiB of demand gone, the largest single lever | Anything using the `docker-desktop` context stops |
| `docker_memory_cap` = 8 GiB | C | Bounds the VM's worst case (now the whole machine) | A CI job needing more fails; lower it only after Kubernetes is off |
| `postgres_shared_buffers` stays 128 MB | C (guard) | None: Postgres is 0.7 GiB and 1.2 GB/h, not a lever. Raising it would cost the model memory | None while it stays |
| `unused_models` listed | C | Disk only | Deleting a model is irreversible without a re-download |
| `uv_cache`, `npm_cache`, `docker_build_cache` reclaimed | A | Disk only | A lane's next sync or build may download or rebuild |
| `postgres_log`, `host_health_log` rotated past a size | A | Bounded disk | None: archives are kept |

Noted but not declared, because nothing measured them here:

- **The operator's own applications.** VS Code, the browser, agent sessions and their MCP
  servers (`node`, `uvx`) together hold about 13 GiB of footprint. Closing what is idle helps,
  but it is the operator's workflow, not a setting.
- Docker Desktop's **Model Runner and AI features** (`EnableInference`, `EnableDockerAI`) are
  on. Whether they hold memory was not measured.
- **Spotlight** indexing the storm home. `mdworker` processes were busy, but they wrote 0.03
  GB/h, so it is not a write lever, and its CPU cost was not measured.

## Class A: applied on 2026-10-02

<!-- filled from the journal below -->

## Class B: the adoption procedure

Class B waits until the experiments on this host finish: `research/large-diff-review` and
its draft PR #1328, and any live review the canary would contend with. Then, **one item at a
time**, in this order (the first two cannot change an output, and the output-changing ones
come last):

1. `ollama_max_loaded_models` and `ollama_num_parallel`
2. `ollama_fixed_num_ctx`: a code change in the callers, on its own pull request
3. `ollama_keep_alive`
4. `ollama_flash_attention`, then `ollama_kv_cache_type`

For each item:

1. On a branch, set the item's `adopted = true` in `scripts/host_tuning.toml`.
2. On the host, from that branch, run `python3 scripts/host_health.py tune apply --only ITEM`,
   then restart Ollama (quit the app and open it again).
3. Run `tune check`. The item must be `in-force`, and for a runner flag the detail must show
   the runner received it. A `not-received` item is undone at once: the canary would be
   measuring the old setting.
4. Run the canary: `vibey-gh review-canary run`, then `vibey-gh review-canary status`.
5. Compare with the baseline, the 2026-10-01 measurement in
   `docs/architecture/evidence/review-canary/ledger.jsonl` (PR #1331). That run caught 18 of 25
   planted defects (95% Wilson interval 52.4–85.7%) and blocked 0 of 14 controls (0.0–21.5%).
   The item is **kept** only if `status` exits 0 (the floor holds), recall is no lower than
   the baseline's interval allows, and the false-positive rate is no higher.
6. **Kept:** open the pull request with `adopted = true`, citing the canary's ledger line.
   **Not kept:** run `tune undo ITEM`, restart Ollama, and record the result in the item's
   `evidence` with `adopted = false`, so the refusal is on the record (12.d).

After adoption, the weekly host-health record judges the item against the weeks before it,
through the figures in its `judged_by` (next section). An item whose weeks get worse is undone
the same way.

## Class C: the operator's asks

Each of these is the operator's decision. To approve one, set its `operator_approved` to the
approving pull request or date. `tune apply` then prints the step (it performs nothing that
needs a settings pane, root or a deletion).

1. **Turn off Docker Desktop's built-in Kubernetes**, if nothing uses the `docker-desktop`
   context: Docker Desktop > Settings > Kubernetes, then Apply & restart. This is the largest
   single memory lever measured (about 6.4 GiB). Do it after the experiments, because it
   changes the host state that tok/s depends on.
2. **Then cap Docker Desktop's VM at 8 GiB** (Settings > Resources > Advanced), and watch the
   runner's CI jobs for a week.
3. **Decide about the models not loaded in 30 days**: `gemma4:26b` (16.9 GB),
   `qwen2.5-coder:14b` (9.0 GB) and `qwen2.5-coder:1.5b` (1.0 GB). This frees disk only.
   `qwen3:14b` is qwenloop's model and `gpt-oss:20b` the sovereign default.
4. **`release-binaries-scratch`** in the storm home is 8.8 GB, is not a registered worktree,
   and is not a cache this tool can prove regenerable. Its owner decides.
5. **Memory.** 24 GiB is vibey's minimum and 32 GiB its recommendation. The weekly
   `ram_capacity` and `swap` drivers already track this machine against both. Size the next
   machine for at least 32 GiB, after the levers above have been measured.
6. Postgres needs nothing. `postgres_shared_buffers` is a guard that keeps it from being raised.

## How the weekly record judges each change

The weekly host-health record (`scripts/host_health.py weekly`) carries what was in force
(`tuning.state`) beside the figures that judge it, so the weeks after a change can be read
against the weeks before:

| Figure | What it shows |
|---|---|
| `memory.swap_used_gib`, `memory.swap_used_ratio` | Swap in use, and against memory |
| `memory.swapout_gb_per_hour` | Swap-out volume per hour since boot |
| `memory.swap_share_of_writes` | Swap-outs as a share of all bytes written to disk since boot |
| `storage.host_writes_gb_per_hour_since_boot` | Disk writes per hour since boot |
| `storage.bytes_written_per_week` | The SSD's own counter, week over week. It does not reset at boot, so it is the one to trend |
| `ollama.loads_per_day`, `ollama.distinct_num_ctx` | Model reloads, and the context sizes that cause them |
| `throughput.gen_tok_s_week_median` | Generation rate at comparable context (prompts of 1,024 to 32,768 tokens) |
| `memory.budget` | Memory by process group |

The since-boot rates restart at every boot, so compare them only between records made a
similar number of hours after a boot. The SSD's weekly bytes written do not reset. As wear
slows, the `ssd_endurance` and `ssd_wear` drivers move their forecast later on their own.
