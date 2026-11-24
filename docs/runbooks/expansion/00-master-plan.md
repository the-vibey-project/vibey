---
description: "The expansion master plan: 21 workstreams that grow vibey beyond one machine, how they depend on each other, which have landed, and what each needs from the operator."
---

# Expansion master plan: the 21 workstreams, their order, and where each stands

> **Status (2026-11-24):** 21 workstreams. Landed: 05 on minikube, 08 (the clients exist),
> 12 in large part (the hub, pairing, MCP, ACP), 13 Front 1, 19 (as a merged monorepo, not
> submodules). Partial: 03 (an AWS stub only), 07, 09, 14, 15, 20. Open: 06, 16. Superseded:
> 02. Not started: 01, 04, 10, 11, 17, 18, 21. The rows below say which were re-checked
> against the code on this date and which were not.

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** This page is for whoever picks the next large piece of work
> for vibey. It orders 21 workstreams into six dependency phases (A to F); each numbered runbook
> in this folder is a self-contained plan written to seed a vibey DESIGN phase. Read the
> [status ledger](#status-ledger) first: it says what exists now, so nobody rebuilds it. Every
> new workstream starts from the sovereign default (sub-doctrine 8.b), never a paid platform.

## The idea in one conversation

Daniel had the folder of 22 runbooks open and a question about the first one.

**Daniel:** Professor, this plan says the clients have not started. But I can install the
krypton app today.

**Professor Feynman:** Then the plan is older than the app. A plan like this is a map drawn
before the journey, with notes pencilled in along the way. The map is still useful: it shows
which roads lead to which. The pencil notes go stale the moment someone walks a road and
forgets to mark it.

**Daniel:** So how do I know which notes to trust?

**Professor Feynman:** Every note carries a date and a piece of evidence, a file or a pull
request you can open. Trust the evidence, not the note. If a row says "not started" and you
find the code, the row is wrong and you fix it in the pull request that notices.

**Daniel:** And the order of the phases?

**Professor Feynman:** That part changes slowly, because it is about what depends on what.
Where the picture stops working: a map does not tell you which roads you must never take.
Here one rule does: a new surface starts from the self-hosted free default, and a paid
platform is only ever a declared relay.

## What the plan is for

Twenty-one workstreams that take vibey from one MacBook to a multi-cloud, multi-surface,
self-maintaining delivery platform. Its stated intent is that vibey builds them itself,
through its own queue (see [The dogfooding protocol](#the-dogfooding-protocol-applies-to-every-workstream));
that is a goal, not a record: the workstreams that have landed so far landed as ordinary pull
requests (for example #70, #73, #74 and #76), and nothing in this folder or its `evidence/`
shows one delivered through `vibey new`. This document sequences them; each numbered runbook
in this directory is a self-contained execution plan written to be consumed as a vibey
DESIGN-phase seed.

vibey today conducts five engines over three runner packages: `claudeloop` and `codexloop`
(the PAID tier), and `gptossloop`, `qwenloop` and `claudeloop-local` (the LOCAL tier). The
local runner (`src/vibey_runners/qwen`) ships as two engines: `gptossloop`, the sovereign
default on the Heretic v2 build of GPT-OSS 20B (ADR-0064, ADR-0099), and the opt-in
`qwenloop` on Qwen. cursorloop and agyloop were retired and their runners removed (ADR-0078).

The runbooks were committed on 2026-08-20 and 2026-08-21, when the runners, `vibey-gh`,
`vibey-skills` and `vibey-bootstrap` were separate GitHub repositories. They are now members
of this repository (`src/vibey_runners/{claude,codex,qwen,common}`,
`src/vibey_tools/{gh,skills,bootstrap}`), registered as a uv workspace (ADR-0021). The sibling
repositories no longer exist, and neither do their PyPI projects: everything ships as
`vibey-engine`, and the apps as `krypton-app` (ADR-0037, ADR-0069). Where a runbook still says
"each repo", read "each workspace member".

## Status ledger

Re-checked against `develop` at `d91a3791e` on 2026-11-24 where the row says so; the other
rows still carry their 2026-09-15 or 2026-10-02 reading, and the runbook's own `Status` line
may be newer. "Re-checked" means the evidence named was read in the code, not that the
workstream was run.

| # | Workstream | Status | Evidence |
|---|---|---|---|
| 01 | Jira integration | Not started (re-checked) | No Jira code under `src/vibey`. Ticketing's sovereign default is Plane (`src/vibey/infrastructure/tracker/plane.py`, the chart's `plane.yaml`); under sub-doctrine 8.b, Jira is a declared-only relay, never the default |
| 02 | copilotloop | Superseded (re-checked) | No copilotloop exists. The engine set is claudeloop, codexloop, gptossloop, qwenloop and claudeloop-local (`src/vibey/domain/engine.py`); since ADR-0064 gptossloop is the sovereign default and qwenloop its opt-in Qwen twin |
| 03 | AWS + GCP | Partial: a stub (re-checked) | `src/vibey/infrastructure/aws/adapter.py` holds `InMemoryAWSClientAdapter`, a declared-only stub; there is no `infrastructure/gcp`. The deploy target's default is `openstack` (`DeployConfig.target` in `src/vibey/domain/config.py`). `vibey worker --azure {memory,az}` remains |
| 04 | Docs scraper | Not started (re-checked) | No `docwatch` module, job kind or migration |
| 05 | Kubernetes | Landed on minikube (re-checked) | PRs #73, #74, #76 (2026-08-21); CI `cluster-smoke` job. The image carries every runner (ADR-0037). The chart also deploys the self-hosted surfaces (Plane, Synapse, Ollama, the edge, Wazuh, Kannel, monitoring, docs, backup). Open: a `vibey serve` Deployment (the chart has none), cloud presets, AKS/EKS/GKE runs |
| 06 | Live engine confirmation | Open (not re-checked) | claudeloop live-proven (so was agyloop, before ADR-0078 retired it and cursorloop); codexloop, gptossloop, qwenloop and claudeloop-local not |
| 07 | Store submissions | Partial (re-checked) | The app exists (`clients/app`). A release builds its iOS package for the App Store while `EXPO_TOKEN` is set (`scripts/release_binaries.toml`, target `app-ios`), but nothing submits it to any store |
| 08 | Clients | Landed (re-checked) | `clients/app` (krypton mobile and web, React Native/Expo), `clients/desktop` (C on GTK 4, ADR-0073), `clients/vscode` (published to Open VSX), `clients/krypton-app` (the `krypton-app` package) and `packages/vibey-core` (the shared TypeScript core, ADR-0067), over the hub's API (ADR-0068) and device pairing (ADR-0071) |
| 09 | Package managers | Partial (re-checked) | PyPI publishes `vibey-engine` (`vibey-engine.yml`) and `krypton-app` (`krypton-app.yml`); `openvsx.yml` publishes the extension; `release-binaries.yml` attaches the desktop Flatpak and tarball, the macOS `.dmg`, the web, Android and iOS builds and the `.vsix` to each GitHub Release. ADR-0019 governs the remaining channels |
| 10 | Keep-awake | Not started (re-checked) | No `power` port or adapter |
| 11 | OpenClaw / Moltbook | Not started (not re-checked) | Constrained by sub-doctrine 4.a |
| 12 | Integration surfaces | Largely landed (re-checked) | The conductor now ships the hub (`vibey serve`, ADR-0068), pairing (ADR-0071), devices that start, pause and unwind projects (ADR-0091), the MCP server (`vibey mcp`, ADR-0100), the ACP agent (`vibey acp`, ADR-0101), `vibey connect`, and `vibey -w` on GitHub's runners (ADR-0085), besides the signed outbound webhooks (`src/vibey/infrastructure/notify/webhook.py`). `vibey-gh` projects api/mcp/sdk/webhook (`vibey_gh/surfaces.py`). What is left is in runbook 12's own status line |
| 13 | Cost & performance | Front 1 landed (not re-checked) | PR #70 (2026-08-21); Front 1 items 5–6 and Front 2 open |
| 14 | Social engagement | Partial (not re-checked) | Community files, badges, ProperDocs site, social-signals surface |
| 15 | Agent surface sync | Partial overlap (re-checked) | `vibey connect` registers vibey with Claude Code, Claude Desktop, Codex, Cursor, VS Code, Gemini CLI and Zed; the loop capability bundle (the `vibey loops` sub-groups `marketplace`, `plugin`, `mcp`, `skills` and `snapshots`, ADR-0103) declares and locks skills, plugins and MCP servers across both loops. What of runbook 15 is left has not been re-checked; it must build on in-tree `vibey-skills` (ADR-0017) |
| 16 | Runner containers | Open (re-checked) | No runner has a Dockerfile of its own: the one image (`deploy/docker/Dockerfile`) carries every console script (ADR-0037; CI's `Image contract` steps check it) |
| 17 | Plan-drift reconciliation | Not started, unblocked (re-checked) | 05's operator and CRD landed (#76); no `driftPolicy` exists yet |
| 18 | Production fitness | Not started (re-checked) | Waits on 17's machinery; no `fitnessPolicy` exists yet |
| 19 | Monorepo & shared libraries | Landed differently | Subtree imports (runners 2026-09-10, tools 2026-09-15) + uv workspace (ADR-0021); domain extraction open |
| 20 | PR reviewer | Partial (not re-checked) | `vibey_gh` `merge_train`, `pr_automation`, `local_review`; pr-af is the declared default reviewer (ADR-0090) |
| 21 | Explorer | Not started (re-checked) | No `src/vibey_tools/explorer`. (The ledger explorer published by `scripts/explorer_publish.py` is a different thing: it publishes ledgers, it does not find work) |

House rule: every runbook carries a `> **Status (YYYY-MM-DD):** …` line
under its title. Update it in the PR that changes the facts, and update the row above in the
same PR.

Version numbers in older notes (for example "since 3.3.0" in runbook 09) refer to the 3.x line
that was retired when the version was reset to 0.x and held below 1.0 (#1898). The current
line is 0.x.

## The rule every workstream starts from

Sovereign self-hosted free is the only default on every surface, and paid is declared-only
(sub-doctrine 8.b, ADR-0042). Each surface has one vibey-owned protocol and an always-on
sovereign default: engine `gptossloop`, cloud OpenStack, forge Forgejo, tickets Plane, docs
BookStack, secrets Bitwarden, files Nextcloud, email Forward Email, SMS Fossify Messages,
messaging Matrix with Element. A paid platform (Jira, Azure, AWS, GCP, GitHub, and the rest)
is a declared-only relay through the sovereign host. Local engines are preferred first
(sub-doctrine 8.a). So 01 builds on Plane first, 03 on OpenStack first, and 07, 09 and 14 never
make a paid channel the default.

## The dogfooding protocol (applies to every workstream)

The plan's rule is that every workstream ships through vibey's own queue, not through ad-hoc
sessions. As the [status ledger](#status-ledger) shows, that has not yet happened for any
landed workstream:

1. `vibey new <workstream> --repo ~/git/vibey --max-cycle-dollars <cap>`, where
   `<workstream>` is the project name and `<cap>` the most a cycle may spend in dollars.
   Runner and tool work targets the same repository: the runners and
   `vibey-gh`/`vibey-skills`/`vibey-bootstrap` are workspace members
   (ADR-0021). Budget caps are real now —
   the brake reads TurnCompleted `cost_usd` (PR #58).
2. Seed DESIGN with the workstream's runbook file as the interview input;
   answer routine gates with `vibey answer <gate> --defaults`.
3. BUILD runs unattended on the engine pool (`vibey worker -j 2` or more). Repair rounds are
   bounded and self-terminating (PR #59); parks advertise their grant
   contracts (`--raw '{"max_rounds": N}'`, `{"max_dollars": N}`,
   `{"max_attempts": N}`).
4. REVIEW demos to the operator; deployment stage set only on explicit
   opt-in.
5. A workstream is DONE when its runbook's **Verification** section passes
   with evidence (test output, live-tenant resource IDs, store listing
   URLs, published package versions).

House rules that no workstream may violate: onion architecture
(import-linter), 100% branch coverage per layer (ADR-0023), Conventional Commits,
never implement on `main`, ledger append-only, a bounded repair ladder
parks with a grant rather than looping (ADR-0024), `CreditsExhausted` never
gets `resets_at`, never block a worker on a human, and the sovereign default first
(sub-doctrine 8.b).

## Sequencing

```
Phase A — foundation (unblocks everything else)
  13-cost-performance          # Front 1 LANDED (#70); items 5-6 + Front 2 open
  06-engine-live-confirmation  # open; gptossloop (sovereign default, ADR-0064),
                               # qwenloop, codexloop, claudeloop-local unconfirmed
Phase B — scale-out
  05-server-mode-kubernetes    # LANDED on minikube (#73/#74/#76, ADR-0025):
                               # image, chart, KEDA, kopf operator + CRD,
                               # doctor --cluster. Open: engines working
                               # headless in the image (16), server
                               # Deployment, cloud presets, AKS/EKS/GKE
  16-loop-runner-containers    # open; the image carries every runner since
                               # ADR-0037, so what is left is Phase 0
Phase C — integration surfaces
  19-monorepo-and-shared-libraries
                               # LANDED DIFFERENTLY: subtree imports + uv
                               # workspace (ADR-0021), not submodules;
                               # domain extraction still open
  17-plan-drift-reconciliation # unblocked (05's operator landed); not started
  18-production-fitness-reconciliation
                               # sibling loop on the same rails: is what
                               # the jobs produced fit for production?
  12-integration-surfaces      # LARGELY LANDED: hub, pairing, MCP, ACP,
                               # connect, -w; vibey-gh api/mcp/sdk/webhook
  01-jira-integration          # rides on 12's webhook + API plumbing;
                               # Plane is the sovereign default (8.b)
  02-copilotloop               # SUPERSEDED: no copilotloop; five engines
Phase D — clouds
  03-multicloud-aws-gcp        # OpenStack is the sovereign default (8.b);
                               # AWS is a declared-only stub, GCP absent,
                               # Azure reached through the az CLI
Phase E — products
  20-vibey-pr-reviewer         # partial inside vibey-gh (merge_train,
                               # pr_automation); cross-account + stop list open
  21-vibey-explorer            # daily open-source discovery, build, and ship
  08-clients                   # LANDED: mobile + web, desktop, VS Code,
                               # krypton-app, @vibey/core
  07-store-submissions         # App Store / Play Store; builds exist, none submitted
  09-package-managers          # PyPI, Open VSX, Release binaries done;
                               # remaining channels per ADR-0019
  10-keep-awake                # desktop no-sleep contract
  15-agent-surface-sync        # one customization set across every IDE/bot;
                               # vibey connect + ADR-0103 cover part of it
Phase F — ecosystem
  04-docs-scraper              # integration docs drift watcher
  11-openclaw-moltbook         # OpenClaw AgentSkill + Moltbook presence
  14-social-engagement         # partial; one repository now
```

Phases are dependency-ordered; workstreams inside a phase can run as
parallel vibey projects when engine capacity allows.

## What each workstream needs from the operator (collected)

| Workstream | Needs before live verification |
|---|---|
| 06 engines | A codexloop session to capture real `events.jsonl` output; for gptossloop (on by default), a local Ollama serving the sovereign default model, the Heretic v2 build of GPT-OSS 20B (Ollama tag `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`, ADR-0099; `VIBEY_SOVEREIGN_MODEL=stock` selects stock `gpt-oss:20b`); for qwenloop, `qwen3:14b` (or llama.cpp / vLLM weights) and `[features] qwenloop = true` |
| 03 clouds | An OpenStack tenant for the sovereign default; for the declared-only relays, `az login` + subscription, an AWS free-tier account + access key, a GCP free-tier project + service-account JSON |
| 05 k8s | The minikube path already runs in CI (`cluster-smoke`). Remaining: 03's cloud tenants for AKS/EKS/GKE; LLM API keys for API-key engine mode |
| 16 runner containers | A registry namespace + `packages:write` token; the same LLM API keys as 05; deploy keys for private target repos |
| 17 drift reconciliation | Nothing new — rides on 05's operator and 16's containers; needs a decision on the production `driftPolicy` ceiling |
| 18 production fitness | metrics-server (or Prometheus) in-cluster; `pg_stat_statements` enabled on the target database; a decision on the `fitnessPolicy` ceiling |
| 19 monorepo & libraries | Nothing: the monorepo question is closed (subtrees + uv workspace, ADR-0021) and ADR-0017 treats `vibey-bootstrap` as the family cross-cutting layer |
| 20 pr-reviewer | Account list + per-account credentials; per-repo policy (review / merge / merge+deploy); the deletion threshold; confirmation of the default-yes posture |
| 21 explorer | GitHub account(s) + repo-create rights; the daily PR cap and staleness window; any ecosystems to exclude; discovery-source API access |
| 07 stores | Apple Developer account + App Store Connect API key; Google Play Console account + service account |
| 01 jira | Plane comes first (the sovereign default); for the Jira relay, a Jira Cloud site (free tier) + API token / OAuth app |
| 11 openclaw | An OpenClaw install; Moltbook agent registration (claim tweet is a human step) |
| 09 packages | PyPI: done (trusted publishing, no token). Per ADR-0019: `packages:write` on ghcr.io; a single-file executable tool choice (shiv, pex or PyInstaller); the existing, empty `the-vibey-project/homebrew-tap`; winget/Scoop/Chocolatey accounts; AUR account + ssh key; npm token last |
| 15 surface sync | Nothing to start; a private git remote for the store if multi-machine sync is wanted |

Everything else runs on what the MacBook already has.

## Cross-cutting acceptance bar

- Every new adapter sits behind a Protocol in `application/interfaces/`;
  `domain/` stays pure; `bootstrap.py` stays the sole composition root.
- Every new surface ships its sovereign default adapter first; a paid platform is added only
  as a declared-only relay (sub-doctrine 8.b).
- Every live integration ships with (a) fixture-level tests at the
  subprocess/HTTP boundary and (b) a `tests/live/` opt-in test that runs
  against the real service, gated on env credentials being present.
- Every workstream updates the four agent-surface trees
  (`.claude/skills/`, `.cursor/rules/`, `.agents/skills/`,
  `.agent/rules/`) in the same PR when it changes a procedure.
- Findings discovered mid-build follow the repair-ticket protocol:
  raised → repaired → resolved-on-completion → re-verified (PR #59).

## Where next

- [The decision records](../../architecture/decisions/), for why each default and rule exists.
- [Downloads](../../guides/downloads.md), for what workstreams 08 and 09 already ship.
- The numbered runbooks in this folder, starting with the one whose row you are about to change.

## Say it in one line

vibey's expansion plan orders 21 workstreams by dependency; check the dated status ledger against the code before you build, and start every new surface from its sovereign default.
