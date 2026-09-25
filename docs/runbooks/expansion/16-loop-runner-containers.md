# Runbook: loop-runner containers — every *loop runs headless in the vibey image

> **Status (2026-09-18):** open, and narrower than written. ADR-0037 (PR #234)
> made the one `vibey` wheel carry all five runners, and the vibey image
> copies every package root, so each runner's console script is already on
> `PATH` in the vibey image (CI's `image` job asserts it). The separate
> `vibey-engines` image this runbook designed is therefore moot. What is
> left is **Phase 0**: proving each runner completes a session headless in
> that image. No spike is recorded for any runner, and two gaps are already
> known — codexloop drives an external `codex` binary the image does not
> carry, and claudeloop runs through the Claude CLI bundled inside
> `claude-agent-sdk` while `claudeloop doctor` checks `PATH` only, so it
> reports the CLI missing in-image. The runners are workspace members under
> `src/vibey_runners/` (ADR-0021); read "repo" below as "runner package in
> this repository". Standalone per-runner images and charts remain optional.

## Goal

Each of the four session runners — `claudeloop`, `codexloop`,
`cursorloop`, `agyloop` — runs a real session on Kubernetes. Two consumers:

1. **The vibey worker.** It runs the runners as subprocesses from its own
   image, which since ADR-0037 already contains them. This consumer needs
   Phase 0 and nothing else from this runbook: no second image, no
   `image.engines` value.
2. **Standalone.** Each runner is a separately *usable* tool with its own users —
   though since ADR-0037 it is not a separately *published* one. The vibey
   image already serves a standalone run: `docker run --rm --entrypoint
   /usr/bin/tini vibey:dev -g -- claudeloop run …` keeps tini as PID 1 for
   SIGTERM (ADR-0026); `--entrypoint claudeloop` is enough for a one-shot
   command. A `helm install claudeloop` chart that runs a session without the
   vibey conductor anywhere in the picture is the optional remainder.

## Current state (originally verified 2026-08-21; versions and layout updated 2026-09-15)

| Package | Path | Version | Python | Console script | Vendor binary |
|---|---|---|---|---|---|
| `claudeloop` | `src/vibey_runners/claude` | 0.8.0 | >=3.12 | `claudeloop` | `claude` |
| `codexloop` | `src/vibey_runners/codex` | 0.4.0 | >=3.12 | `codexloop` | `codex` |
| `cursorloop` | `src/vibey_runners/cursor` | 0.7.0 | >=3.12 | `cursorloop` | `cursor-sdk-bridge` |
| `agyloop` | `src/vibey_runners/agy` | 0.5.0 | >=3.12 | `agyloop` | `agy` |
| `qwenloop` | `src/vibey_runners/qwen` | 0.3.0 | >=3.12 | `gptossloop`, `qwenloop` | none (local Ollama / llama.cpp / vLLM model) |

- All five are workspace members of this repository, share vibey's onion
  layout (`domain/application/infrastructure/cli`), and ship inside the one
  `vibey` distribution rather than publishing as their own projects (ADR-0037).
- **No runner has a `deploy/` directory.** qwenloop's
  `deploy/docker/Dockerfile` was deleted on 2026-09-18: its runtime layer
  kept `pip`, had no fixed uid, copied the whole tenant with `COPY . .`, and
  nothing built it. The vibey image is the runner image —
  `docker run --rm --entrypoint qwenloop vibey:dev --help` runs qwenloop
  from it, and the same works for every runner's console script.
- Each subtree still carries its old `.github/` tree, but only the root
  workflows run. The root CI `tools` matrix covers `vibey-gh`,
  `vibey-skills` and `vibey-bootstrap`; it has no runner entries and no
  runner image job. Releases are cut by `vibey-gh promote`
  (`chore(release): x.y.z` commits); release-please is retired
  (ADR-0028).
- **API-key auth already exists in the four hosted-model runners** —
  `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN`, `OPENAI_API_KEY` /
  `AZURE_OPENAI_API_KEY` / `CODEX_API_KEY`, `CURSOR_API_KEY`,
  `GOOGLE_API_KEY` / `GEMINI_API_KEY` / ADC (the same map
  `infrastructure/cluster_preflight.py` checks) — each with
  a `doctor_env` check behind it. Runbook 05's work item 1 is closer to a
  verification job than an implementation job. **This is the single
  biggest de-risking fact in this runbook.**
- vibey invokes runners as **subprocess CLIs**
  (`infrastructure/engines/loop_process_adapter.py`), and since ADR-0037
  the vibey image ships every runner. Nothing in-cluster has run a real
  engine yet: the chart defaults to `--provider scripted` with no keys, and
  Phase 0 below is unproven for every runner.

### The fact that shapes everything

Only `agyloop` selects its lane at runtime (`--gateway sdk|cli`, with
`gateway: str = "sdk"` as the default). In `claudeloop` and `cursorloop`,
`bootstrap.py` hardwires the **agent** gateway — `ClaudeAgentGateway`,
`CursorAgentGateway` from `infrastructure/agent/gateway` — for the
autonomous loop. Their `infrastructure/api/` trees (`gateway.py`,
`providers.py`, `binder.py`, `introspect.py`, `surface_baseline.json`) are
a *separate command surface* — claudeloop's "full Anthropic SDK CLI" — not
a lane the loop can be pointed at.

**So for three of four runners the autonomous loop currently requires the
vendor agent binary on PATH.** That decides image size, base image, and
whether a container can authenticate at all — vendor CLIs generally assume
an interactive TTY login, which does not exist in a cluster.

What the vibey image holds for each, measured against the tree on
2026-09-18:

- **claudeloop** — the Claude CLI ships *inside* the `claude-agent-sdk`
  wheel (`claude_agent_sdk/_bundled/claude`; the lockfile resolves
  manylinux wheels for amd64 and arm64), and the SDK tries that copy before
  `PATH`, so a session may need nothing more. But `claudeloop doctor`
  (`infrastructure/doctor_env.py`) looks for `claude` on `PATH` only and
  reports `claude-cli` failed in the image. vibey's preflight takes an
  engine's auth verdict from that doctor.
- **codexloop** — drives an external `codex` binary (`codex exec`,
  `codex app-server --stdio`). It is not in any wheel, so the image does
  not have it.
- **cursorloop** — `cursor-sdk-bridge` arrives with the `cursor-sdk`
  dependency (manylinux wheels for both arches) and lands in the venv's
  `bin/`, which is on `PATH`. Whether it runs headless in a pod is the
  spike's question.
- **agyloop** — no `agy` binary is installed by any wheel; its
  `--gateway sdk` lane may not need one, which is what its spike should
  confirm.

gptossloop and qwenloop need no vendor binary or API key, but they need
model weights in the image, on a volume or behind a model server (the chart's
optional Ollama), and a GPU for the vLLM profile.

Do not add anything to the image until this is settled per runner. It is
Phase 0.

## Design

### Phase 0 — the lane spike (blocks everything; one spike per repo)

For each runner, answer with a running process, not a code read: *can the
autonomous loop complete a real session with no vendor binary on PATH,
authenticated only by an API key from the environment?*

- **agyloop** — likely already yes (`--gateway sdk`). Confirm, then it is
  the reference implementation the other three copy.
- **claudeloop / cursorloop / codexloop** — if no, the deliverable is a
  runner-side work item in that runner's package: promote the API gateway
  to a lane the loop can select, mirroring agyloop's `--gateway`. That is
  a genuine feature, sized separately, and it must land
  before that runner is worth enabling in-cluster.

The spike's output per runner is one of two verdicts, recorded in that
runner's docs:

- **SDK lane works** → nothing to add to the vibey image: no Node, no
  vendor CLI, no TTY problem. This is the container-native path and the
  one to fight for.
- **CLI lane only** → the vibey image must carry the vendor binary. `claude`
  and `cursor-sdk-bridge` already arrive inside their SDK wheels; `codex`
  needs Node and an npm install, and `agy` a proprietary installer. Headless
  API-key auth for that binary must be proven before anything else is
  built. Vendor licensing for redistribution inside an image is a real
  question here, not a formality — answer it in the spike, not after
  publishing.

### What ADR-0037 made moot

This runbook originally designed a per-runner `deploy/` tree (a Dockerfile,
a Job-shaped Helm chart, `docs/kubernetes.md`) in each of the five
packages, a root CI matrix publishing five images to
`ghcr.io/the-vibey-project/<runner>`, and a `Dockerfile.engines` layering
the runners onto the vibey base behind an `image.engines` chart value.

Since ADR-0037 the vibey image *is* the engines image: one Python
environment, one resolver run, every runner on `PATH`, already built
multi-arch by the `image` job. So:

- **`Dockerfile.engines` and `image.engines` are dropped.** The worker
  Deployment already runs the image that carries the runners.
- **Five per-runner images are not needed to run an engine.** A standalone
  run uses the vibey image with a different entrypoint (see Goal). A
  per-runner image would repackage the same wheel under a second tag, and
  "do not invent a second versioning scheme" now points the same way: the
  image's version is `vibey`'s.
- **What survives is optional:** a Job-shaped chart per runner, for anyone
  who wants `helm install claudeloop` without the conductor. If it is
  built, the reasoning below still holds and should not be lost:
  - **A Job, not a Deployment.** These are one-shot autonomous session
    runners — they start, work, and finish. A Deployment would restart a
    *successfully completed* session forever. `Job` with
    `backoffLimit: 0` and `restartPolicy: Never` is the honest shape;
    offer `CronJob` for scheduled runs. This is the sharpest divergence
    from vibey's chart and must not be copied from it blindly.
  - **Secrets.** API keys come from a Secret, never values.yaml — the same
    `engineAuth.existingSecret` convention vibey's chart already uses, so
    one Secret can serve a vibey worker and a standalone runner alike.
  - **Workspace.** A PVC for the repo under work, cloned via a deploy key
    mounted as a Secret. Reuse vibey's worktree PVC conventions.

What Phase 0 finds may still put something into the image — `codex`, or a
vendor CLI for cursorloop or agyloop. That goes into
`deploy/docker/Dockerfile`'s runtime stage, bound by the same contract as
the rest of it (no compiler, no package manager, uid 10001), and only
after the redistribution question below is answered.

## Work items

1. Phase 0 lane spike × 4 hosted-model runners, run inside the vibey image,
   plus a weights-and-GPU spike for qwenloop; record the verdict per runner
   (blocks 2–4).
2. Runner-side `--gateway` work in whichever runners the spike says need it.
3. `claudeloop doctor` finds the Claude CLI that `claude-agent-sdk` bundles,
   not only one on `PATH` — until it does, it exits 1 in the image and
   vibey's preflight records claudeloop's auth as failed even with a key
   mounted.
4. Whatever vendor binary Phase 0 proves necessary (`codex` first) added to
   the vibey image's runtime stage, under its existing contracts.
5. One real greeter on minikube driven by an in-image engine — the first
   time vibey runs a live engine in-cluster.
6. Optional: a Job-shaped Helm chart per runner for standalone use.

## Verification

- `docker run --rm -e <KEY> --entrypoint <runner> vibey:dev doctor` passes
  for each runner.
- `vibey doctor --cluster --engines <runner>` passes inside a worker pod
  with that runner's key mounted.
- One paid live session per runner in-cluster, API-key authenticated.
- A vibey worker selects a real engine and completes a BUILD job —
  verified against `vibey doctor --conformance` recording a real
  conformance, which today is empty in-cluster ("no recorded conformance
  for agyloop, claudeloop, codexloop, cursorloop" is the live warning from
  the running worker).

## Needs from operator

- LLM API keys for each vendor (the same set runbook 05 needs).
- A GHCR namespace (or other registry) and a token with `packages:write`,
  if the vibey image is to be published at all (it is not today).
- Deploy keys for any private repo a runner is pointed at.
- A decision on vendor-CLI redistribution if any runner lands on CLI-only.
- For qwenloop: where model weights come from in-cluster (baked, volume,
  or pulled at start) and GPU node availability for the vLLM profile.

## Risks

- **The spike may fail for a runner.** If a vendor's agent CLI cannot
  authenticate headlessly by API key, that runner is not clusterable this
  quarter regardless of how good its chart is. Better to learn it in a
  one-day spike than after five charts are written.
- **Five runner charts drift**, if the optional charts are built. The chart
  shape must be copied deliberately, not by cargo cult — a Job here, a
  Deployment in vibey, for a stated reason. Consider a shared chart library
  only after all five exist and the duplication is measured, not before.
- **The image grows with every vendor binary.** Each one Phase 0 adds lands
  on every worker pod, whether or not that deployment uses the engine.
- **Coverage gates.** Each runner keeps its own 100% floors after absorption
  (ADR-0022). Runner-side `--gateway` work is real code in that runner's
  coverage budget, not a packaging change.
