# Issue-suite gap audit: vibey law and decisions vs. open issues and queued specs

**Evidence cutoff (10.f).**
- Code: `STORM/integration`, branch `storm/integration` at `cce648ef` (develop with #392 ratified, plus the integrated storm lanes). Every `file:line` below is at that commit.
- Open issues: `gh issue list --state open` at 2026-09-22 ~15:10Z (88 open), cross-checked against `issue-audit/open-issues.tsv`.
- Queued specs: `specs/` as listed at 2026-09-22T15:20Z. The installer, ORM and fakes spec sets were still being written at that time (see Appendix B).
- CI: `gh run list` on 2026-09-22 ~15:10Z.

**What counted as covered.** One of: an open issue; a spec file in `specs/`; a lane in `specs/test-harness-lanes.md` (T01–T28) or `specs/rabbitmq-lanes.md` (R01–R35); or a lane named inside an ADR draft. ADR-0046 (two loops) and ADR-0047 (surface lanes) name lanes but have no lane spec files. Each of those two lane groups is reported **once**, as "designed, not specced".

**Legend.**
- **Coverage:** *none*, or *partial* with what covers part of it.
- **Size:** *20B* means one focused change with its tests, suitable for a local 20B model. *EPIC* lists proposed children, each 20B-sized unless marked otherwise.
- Proposed titles follow Conventional Commits.

## Summary

| # | Theme | Gaps (none / partial) |
|---|---|---|
| A | Loops & rotation (8.a, 8.b engines, 8.c) | 6 (4 / 2) |
| B | VS Code adapter | 3 (2 / 1) |
| C | Paid defaults, incl. the AWS cloud adapter (8.b) | 5 (2 / 3) |
| D | Measurement (8.g) | 3 (1 / 2) |
| E | Ledger (7.a, 7.c) | 6 (4 / 2) |
| F | OS support (8.h), incl. CI on Arch Linux and macOS | 6 (6 / 0) |
| G | Packaging (2.b) | 4 (4 / 0) |
| H | Installer | 1 (1 / 0) |
| I | ORM behind interfaces | 1 (0 / 1) |
| J | In-memory fakes | 2 (1 / 1) |
| K | Surfaces (8.b, 8.f) | 3 (2 / 1) |
| L | Release & CI operations | 10 (8 / 2) |
| M | Docs wave | 10 (5 / 5) |
| N | Governance tooling | 9 (7 / 2) |
| | **Total** | **69** |

Also recorded: stale issues that ratified law now contradicts (Appendix A), specs that exist but are not filed (Appendix B), and operator rulings owed (N4).

## The 10 most important

1. **L1.** The merge train and Promote have not run since 2026-09-21T19:22Z, the last runs before #317 merged at 19:29:03Z. Nothing reaches `main`.
2. **L2 and L3.** The required PR-review gate cannot pass. The paid key is out of credit, and the self-hosted runners register against a URL that returns 404. The runners are also not declared as code (12.c).
3. **L4.** The root `.vibey-gh.toml` has no `[platform] kind = "github"`. When forge wave 2 (#339–#344) lands, this repository's own automation will talk to `forgejo.local`.
4. **A1 and A2.** The two-loop lanes (ADR-0046) have no spec. Meanwhile the filed R19–R30 issues build seven per-engine loop services, which ratified 8.c ("two loops, one instance per model") replaces.
5. **F1–F4.** vibey's gates never run on Arch Linux, and only one tenant runs on macOS. 8.h says every change is proven on both.
6. **K1 and K2.** The surface lanes (8.f) have no spec. No production code calls any surface port.
7. **D1.** 8.g "always measured": nothing is measured into the ledger, and nothing optimizes itself from measurements.
8. **L9.** Article V.4 requires every prior release to be yanked after the ratification of #392 (and #325, #384, #385). There is no automation and no tracking issue.
9. **E1 and E2.** 7.c: people's private details are never redacted, and redaction is silent rather than recorded.
10. **G1–G4.** 2.b: the tree carries no packaging at all (no runnable image, AUR, Homebrew or winget).

---

## A — Loops & rotation (8.a, 8.b engines, 8.c)

### A1. ADR-0046's lanes (L01–L39): designed, not specced (grouped)
- **Source:** 8.b (engines bullet, #392), 8.c (two loops, one instance per model, two rotation layers on RabbitMQ with dead-letter queues and idempotency); ADR-0046 draft `specs/ADR-two-loops.md` §1–§11.
- **Requirement:** The family runs exactly two loops, `sovereignloop` and `paidloop`. Each runs as one instance per model, fed by queues at both rotation layers, with dead-letter queues and idempotency.
- **Evidence:**
  - `EngineId.QWENLOOP` / `OPENCODE`: `src/vibey/domain/engine.py:31-32`.
  - Tier-only outer layer: `TIER_PREFERENCE` at `engine.py:51`.
  - `DEFAULT_ENGINES = ("qwenloop", "opencode")`: `src/vibey/domain/config.py:21`.
  - Not found: any `LoopId`, `loop.py`, residency code, route store, worktree fence, `PaidFallbackDeclared` or `LoopRouted`.
  - The opencode tenant is still in the tree: `src/vibey_runners/opencode`.
- **Coverage:** none. The ADR names L07, L09, L20, L21, L25, L26, L37, L38 and L39, but no lane file exists.
- **Proposed:** EPIC `feat(loops)!: two loops, sovereignloop and paidloop, rotated in two layers on RabbitMQ`. Children:
  1. Pure domain: `loop.py`, `residency.py`, `seat_choice.py`, run protocol v2 (route, routed, `SUPERSEDE`, `UNROUTABLE`), `ENGINE_ID_ALIASES` and the alias-resolving `known()`.
  2. Ledger kinds `PaidFallbackDeclared` and `LoopRouted`, written in both invocation modes.
  3. `LoopSelector` (outer layer), with `weighted_candidates` extracted.
  4. Family AMQP gains `queue_depth()` and exclusive consume (L21).
  5. Worktree fence `run.lock` + `supersede.json` (L25).
  6. Ollama model runtime: `/api/ps` and `keep_alive: 0` (L26).
  7. Router, seat host, resident schedule, client, adapter and command executor.
  8. The `qwenloop`→`sovereignloop` rename with read-only aliases (L09). Doctor lists legacy spellings (L07).
  9. The `vscodeloop` tenant with `vscode` and `vscode-paid` descriptors (L20, gated on B1).
  10. CLI `loop-service --loop`.
  11. Chart: one router plus one seat host per model, `replicas` fixed at 1, `Recreate` (L37).
  12. Retire the `opencode` id (L38) and remove the tenant (L39).
  13. `RunId` moves to `vibey_runners.common`.
  14. Docs wave: see M7.

### A2. The filed R19–R30 issues build the topology that ratified 8.c replaced
- **Source:** 8.c as ratified by #392 ("exactly two loops", "a single instance per model"); ADR-0046 Context §"ADR-0044 runs one service per engine".
- **Requirement:** Loop services must be one router plus one seat host per model for each of the two loops. They must not be one service per engine id. The supersede and worktree guards must hold at prefetch 1 and across loops.
- **Evidence:**
  - #366–#375 and #377 (R19–R28, R30) specify `vibey.runs.<engine_id>` and one `loop-service --engine <id>` per engine (`specs/rabbitmq-lanes.md` R22, R30). That is seven loops.
  - ADR-0046 records two defects in R22's design: supersede cannot fire at prefetch 1 (`specs/rabbitmq-lanes.md:2606-2611`), and the worktree guard is kept per instance.
- **Coverage:** partial but stale. The filed issues contradict ratified law.
- **Proposed:** 20B (issue hygiene). `chore(issues): re-target R19–R30 (#366–#377) to the two-loop seat topology or close them as superseded by ADR-0046's lanes`. Scope: map each filed R-lane to its ADR-0046 successor. Keep R19 (the run protocol, extended), R20 (extraction) and R21 (local executor). Replace the per-engine host, CLI, invocation selection and chart parts. Carry the L25 fence into R22's acceptance criteria before R34 (#381) flips the default.

### A3. #321 keeps `opencode` in the always-on pool after #392 repealed it
- **Source:** 8.b as ratified by #392: "OpenCode is repealed as an engine of either loop … the runner that drove OpenCode is retired once the VS Code adapter carries its work".
- **Requirement:** The always-on sovereign pool no longer names OpenCode as a law-mandated engine.
- **Evidence:**
  - `config.py:21` and `:407` always append `("qwenloop", "opencode")`.
  - #321's "Required behaviour 1" makes `qwenloop` and `opencode` always on.
  - ADR-0042's engines row names `qwenloop` and `opencode`.
  - ADR-0046 §9 keeps `opencode` as a transitional sovereignloop adapter until L38. That is an operator ruling owed (N4).
- **Coverage:** partial and stale (#321).
- **Proposed:** 20B. `feat(engines)!: opencode leaves the always-on pool; only sovereignloop is always on, and opencode runs only while declared transitionally`. Scope: amend #321, or file a follow-up after the operator rules on the transitional stance. Also covers `DEFAULT_ENGINES`, the doctor pool, the cluster-preflight pool and the CRD default.

### A4. The sovereign DESIGN, DECOMPOSE and VISUAL providers call Ollama directly
- **Source:** 8.c ("nothing spawns a loop directly … one instance per model"); ADR-0046 §4 flag ("Routing them through sovereignloop is a follow-up and is not in this set").
- **Requirement:** Every sovereign model call goes through sovereignloop's queue and residency schedule, so a second model never contends for the resident one.
- **Evidence:**
  - `src/vibey/infrastructure/engines/ollama_chat.py:34-38` (direct `/api/chat`).
  - `QwenloopDesignProvider` at `src/vibey/infrastructure/engines/qwenloop_design.py:177`.
  - #324's `QwenloopVisualProvider` follows the same pattern.
- **Coverage:** none.
- **Proposed:** 20B, after A1. `feat(design)!: sovereign DESIGN, DECOMPOSE and VISUAL runs are routed through sovereignloop`. Scope:
  - The providers submit a pinned run (`model_pin`) through the loop client instead of calling Ollama.
  - Subprocess mode keeps today's direct path behind `invocation = subprocess`.
  - The ledger records the routed seat.

### A5. vibey-gh's sovereign review, triage and fit call Ollama directly
- **Source:** 8.c ("vibey's workers, storms and the command line put work on the loop's queue"); 10.e (family first, in CI and in operations).
- **Requirement:** The review lanes put their work on sovereignloop's queue (sovereign) or paidloop's (paid). They do not open private model paths.
- **Evidence:**
  - `src/vibey_tools/gh/vibey_gh/local_review.py:128-160` (`call_ollama` → `/api/chat`) and `:277-302` (triage).
  - `vibey_gh/fit.py:123` (`DEFAULT_OLLAMA_URL`).
  - The paid review runs outside paidloop (`pr-review.yml`).
- **Coverage:** none. #389 changes only the model default. #133 changes only the ordering.
- **Proposed:** 20B, after A1. `feat(gh): the sovereign review and triage lanes submit to sovereignloop through the family loop client`. Scope:
  - A loop-client seam in `local_review.py`, keeping the constrained-decoding schema.
  - A fallback to direct Ollama only when no broker is configured, with that fact labelled on the verdict.
  - Tests with the in-memory AMQP client.

### A6. The storm machinery lives outside the family
- **Source:** 8.c (storms put work on the loop's queue); 10.e ("a project that ships delivery tooling it does not itself run"); 12.c (declared in the repository).
- **Requirement:** Lane storms are a family command that submits runs to sovereignloop. They are not ad-hoc scripts that spawn qwenloop in-process.
- **Evidence:**
  - `STORM/{qwenlane.py,storm-queue.sh,lane-setup.sh,file-issue.py,EDITING-RULES.md}`.
  - `qwenlane.py:19-26` imports qwenloop internals (`_run_plan`, `_server_for`).
  - Lane clones have no pre-commit hooks (memory, 10:00 EDT).
  - In-tree, only `qwenloop run --storm` exists: `src/vibey_runners/qwen/src/qwenloop/application/storm.py`.
- **Coverage:** none.
- **Proposed:** EPIC `feat(storm): lane storms are a family command`. Children:
  1. `lane setup`: an isolated clone with no remote and the framework hooks installed.
  2. A dependency queue plus an integration branch (`queue.txt` and `integrated.txt` as declared state).
  3. Gutted-file restore as a checked rule.
  4. Spec→issue filing from `SPEC-TEMPLATE.md`.
  5. Submitting each lane attempt to sovereignloop's queue (after A1).
  6. The editing rules shipped as a qwenloop prompt asset.

## B — VS Code adapter (8.b: VS Code in both loops; the paid-default IDE)

### B1. The verification owed before the Code - OSS driver (V-VS1–V-VS5, V-CC1)
- **Source:** 8.b ("VS Code when its provider is local"); ADR-0046 §8 and *Verification owed*.
- **Requirement:** Record a headless, account-free Code - OSS agent session on a local model, with its extension licence, its no-call-home network capture, its event stream and the OSS-vs-Microsoft build marker. Also record Claude Code's licence and network behaviour with a local profile (V-CC1).
- **Evidence:** nothing found. ADR-0046:279 says "no evidence exists of a headless, account-free way".
- **Coverage:** none. It is a verification item, not a lane.
- **Proposed:** research. `research(vscode): record V-VS1–V-VS5 and V-CC1 for the sovereign VS Code adapter`. Not 20B-sized: it needs a packet capture and a licence reading, so it goes to the operator or a large model. Its output gates L20 and the retirement of opencode (L38).

### B2. VS Code as paidloop's default IDE
- **Source:** 8.b paid defaults: "VS Code is the default IDE for paid loops".
- **Requirement:** A declaration of a paid IDE that names no product resolves to `vscode-paid`.
- **Evidence:**
  - Nothing found in code.
  - ADR-0046 §8 makes `vscode-paid` declared-only, with a required `provider` and `model`, but defines no "unnamed paid IDE → VS Code" resolution.
- **Coverage:** partial (A1's L-lanes add the adapter).
- **Proposed:** 20B, after L20. `feat(engines): a paid IDE declared without a name resolves to vscode-paid`. Scope: the config vocabulary for "paid IDE", resolution to `vscode-paid`, a doctor line and tests.

### B3. No agent-surface tree for VS Code sessions
- **Source:** CLAUDE.md "Agent-surface maintenance" (the four trees); SD-01 §8 (carried by every governed agent); 7.b.
- **Requirement:** An agent driven through VS Code receives the same skills and rules, and SD-01 verbatim, as the other four trees.
- **Evidence:** only `.claude/skills`, `.cursor/rules`, `.agents/skills` and `.agent/rules` exist. Nothing for VS Code or its agent extension.
- **Coverage:** none. #290 (a vibey plugin for VS Code) is a different deliverable.
- **Proposed:** 20B, after B1 names the extension. `feat(provision): a fifth agent-surface tree for the VS Code adapter`. Scope: the extension's rules or instructions directory, generated from the same sources, carrying SD-01. Add it to the parity test (N2).

## C — Paid defaults, incl. the AWS cloud adapter (8.b)

### C1. No AWS cloud adapter, though AWS is the default paid cloud
- **Source:** 8.b paid defaults ("AWS is the default paid cloud"); 8.b cloud bullet (Azure, AWS and GCP are declared-only).
- **Requirement:** A declared paid cloud with no name reaches AWS through `CloudClientPort`, with the same protocol as OpenStack.
- **Evidence:**
  - Only `src/vibey/infrastructure/azure/` exists.
  - `deploy.target` defaults to `openstack` (`config.py:139`, `:457`).
  - The OpenStack spec refuses `target = "aws"` (`specs/openstack-client.md:205`, `:615`) and lists "AWS and GCP targets" as out of scope (`:633`).
  - `CloudClientPort` exists only in `src/vibey/application/interfaces/azure.py`.
- **Coverage:** none. Runbook 03 is not an issue.
- **Proposed:** EPIC `feat(deploy): AWS is the default paid cloud`. Children:
  1. `[deploy] target = "aws"` is accepted, with a provider-discriminated `TargetScope`.
  2. `AwsCliCloudClient` behind `CloudClientPort`, with a subprocess seam and an in-memory fake.
  3. DEPLOY_DESIGN IaC for AWS. Prefer OpenTofu under 8.a (operator ruling).
  4. DEPLOY_EXECUTE and DEPLOY_REVIEW on AWS.
  5. Credentials from `SecretsPort`.
  6. Doctor lines.
  7. A live contract test marked `integration`.

### C2. "Declared paid, unnamed" resolves nowhere
- **Source:** 8.b paid defaults: "where a human declares a paid counterparty without naming which, the default is fixed".
- **Requirement:** One `paid` declaration resolves to Claude (engines, via `claudeloop`), VS Code (IDE), AWS (cloud) and GitHub (forge).
- **Evidence:**
  - `PlatformConfig.kind` accepts only concrete forge kinds (`src/vibey_tools/gh/vibey_gh/config.py:288-296`).
  - `deploy.target` accepts only concrete targets.
  - ADR-0046 handles engines only (`paidloop` → `claudeloop`).
- **Coverage:** partial (A1 covers engines).
- **Proposed:** 20B ×2.
  - `feat(config): deploy.target = "paid" resolves to aws, per 8.b's paid default`.
  - `feat(gh): platform.kind = "paid" resolves to github, per 8.b's paid default`.
  - Each writes the resolved value into doctor and status output, so the declaration is visible.

### C3. No relay-through-sovereign for declared paid platforms
- **Source:** 8.b: "relays through the sovereign host rather than replacing it: the sovereign host stays the source of truth"; ADR-0042 Decision.
- **Requirement:** A declared paid platform speaks through a relay adapter that feeds the sovereign host. It never substitutes for that host.
- **Evidence:**
  - Declared adapters replace the sovereign one: `forge_selector.py:62` picks exactly one adapter; `deploy.target` picks exactly one cloud.
  - `grep -ri relay src/vibey` finds only an email docstring.
  - This repository has no sovereign forge host at all.
- **Coverage:** partial. #138 (adapters), #136 (forge snapshot/replay) and #85 (repo-per-provider, pre-monorepo) each touch it.
- **Proposed:** EPIC `feat(relay): declared paid platforms relay through the sovereign host`. Children:
  1. A domain relay vocabulary: source-of-truth host plus relay direction.
  2. Forge: Forgejo primary, GitHub relay (push mirror plus change-request relay).
  3. Tracker: Plane ↔ Jira/Linear sync.
  4. Docs: BookStack → Confluence publish.
  5. Cloud: OpenStack holds the deploy state of record.
  6. This repository's own sovereign Forgejo host (operator ruling).

### C4. No adapters for the declared-only paid platforms that 8.b names
- **Source:** 8.b ("the protocol is realized by adapters: one per platform").
- **Requirement:** Each named declared-only platform has an adapter to declare.
- **Evidence:** `src/vibey/infrastructure/{tracker,docs,secrets,files,email,sms,messaging}/` each hold only the sovereign adapter and `in_memory.py`.
- **Coverage:** partial. #85, #298 (Bitbucket), #297 and runbooks 01, 03 and 12.
- **Proposed:** EPIC, low priority. `feat(surfaces): declared-only relay adapters for 8.b's named paid platforms`. Children, one per surface, each depending on C3's relay vocabulary:
  - Jira, Linear, Asana.
  - Confluence, Notion, GitBook.
  - 1Password, LastPass, Proton Pass.
  - Google Drive, iCloud.
  - Gmail, Proton Mail.
  - Signal, Slack, Discord, and the rest of the messaging list.
  - GCP.

### C5. `vibey deploy plan | cancel | rollback` are placeholders
- **Source:** ADR-0013 (the deployment stage set); 10.d (recoverability).
- **Requirement:** Deployment can be planned, cancelled and rolled back through `CloudClientPort` on the default (OpenStack) and on declared clouds.
- **Evidence:** `src/vibey/cli/main.py:1059-1150`, with docstrings saying "NOT YET IMPLEMENTED", `Status: NOT EVALUATED`, and "deploy rollback is not yet implemented".
- **Coverage:** none.
- **Proposed:** 20B ×3.
  - `feat(deploy): deploy plan evaluates the plan through CloudClientPort`.
  - `feat(deploy): deploy cancel stops a DEPLOY_EXECUTE and releases created resources`.
  - `feat(deploy): deploy rollback returns to the last accepted deployment state`.
  - Each writes ledger events and parks a gate on ambiguity.

## D — Measurement (8.g: always measured)

### D1. Measurement is not recorded, not in the ledger, and not universal
- **Source:** 8.g: "Every loop, lane, queue, surface, test run and model records its latency, throughput, queue depth and waiting time, resource use and outcome … Measurements join the ledger (7.c) and are published with the decisions they drive (10.f). A component that cannot report its measurements is incomplete."
- **Requirement:** A single measurement vocabulary, recorded continuously by every loop, lane, queue, surface, test run and model, written to the ledger and published.
- **Evidence:**
  - `TelemetryMetrics` offers five OTel-only counters (`src/vibey/infrastructure/otel.py:182-200`: selection, queue latency, phase duration, handoff gate failure, cost).
  - `EventKind` has no measurement kind (`src/vibey/domain/ledger.py:37-69`).
  - Surfaces, test runs and models record nothing.
- **Coverage:** partial:
  - #382: qwenloop per-turn timings only.
  - T04: test-run records in the harness store, not the ledger.
  - ADR-0047's S32: the surface-lane benchmark.
  - ADR-0046's L21: queue depth.
- **Proposed:** EPIC `feat(measure): vibey is always measured (8.g)`. Children:
  1. Domain `Measurement` value types plus a `MeasurementRecorded` ledger kind.
  2. `MeasurementPort` with an in-memory fake, a ledger sink and an OTel sink via `vibey_bootstrap`.
  3. Every engine adapter's runs record latency, turns, tokens, outcome and resource use (not only qwenloop).
  4. A queue sampler: depth, wait and age of the oldest item, per Postgres job state and per RabbitMQ queue.
  5. A measuring decorator applied to every surface port at the composition root.
  6. Per-model tokens/s, load time and memory on this machine.
  7. Test-run measurements (T-lanes) forwarded to the ledger.
  8. vibey-gh merge-train, review and promote durations and outcomes.
  9. A meta-test: every port implementation and loop is measured.
  10. `vibey measure` / status output that names its cutoff (N6).

### D2. Nothing optimizes itself from live evidence
- **Source:** 8.g: "rotation weights, model residency, lane capacity and defaults are chosen from live evidence, never from assumption".
- **Requirement:** Effective rotation weights, residency and capacity are derived from recorded measurements, and each derivation is ledgered.
- **Evidence:**
  - Weights are static config: `config.py:113`, `:413-416`.
  - `select()` uses the weights as given: `src/vibey/domain/rotation.py:161`.
  - ADR-0038 fixed all base weights at 1.
- **Coverage:** none.
- **Proposed:** EPIC, after D1. Children:
  - `feat(rotation): effective weights derive from measured success rate and latency within a configured band` (pure domain plus a ledgered `WeightsDerived`).
  - `feat(loops): residency hold and switch bounds tune from measured load times` (after A1).
  - `feat(lanes): lane capacity chosen from measured throughput` (after K1).

### D3. The benchmark behind the 8.d default is not in the tree
- **Source:** 8.d ("the catalogue names, for each choice, the evidence behind it and the date"); 8.g; 10.f; 12.c.
- **Requirement:** The measurement that chose GPT-OSS 20B is reproducible from the repository, and re-running it appends evidence to the catalogue.
- **Evidence:** it lives only in `STORM/bench/` (`bench.py`, `results.jsonl`). Nothing in `src/`.
- **Coverage:** partial. #383 pins the catalogue data but not the method.
- **Proposed:** 20B. `feat(models): vibey models bench runs the recorded ten-turn session and appends dated evidence to the model catalogue`. Also gives 8.d's "living standard" a repeatable check.

## E — Ledger (7.a searchable, 7.c thorough)

### E1. People's private details are never redacted
- **Source:** 7.c: "secrets, credentials and people's private details are redacted where they would appear".
- **Requirement:** The ledger redactor also removes private personal data: emails, phone numbers and street addresses.
- **Evidence:** `src/vibey/infrastructure/ledger/redact.py:17-33` matches credential key names and vendor token shapes only.
- **Coverage:** none.
- **Proposed:** 20B. `feat(ledger): redaction covers people's private details, not only credentials`. Scope: pure patterns with tests, applied at `ledger_repository.py:108`, digest-after-redaction unchanged, and the same patterns in `tests/fakes` (see fakes-ledger).

### E2. Redaction is silent
- **Source:** 7.c: "the redaction is itself recorded — never a silent omission".
- **Requirement:** Every redaction leaves a record of where it happened and which class it was, without the value.
- **Evidence:** `redact_payload` replaces the value with `[REDACTED]` and records nothing (`redact.py:52-58`; `src/vibey/infrastructure/db/ledger_repository.py:103-109`).
- **Coverage:** none.
- **Proposed:** 20B. `feat(ledger): each redaction is recorded with its path and class`. Scope: a `redactions: [{path, class}]` payload field (or a `RedactionRecorded` event), forward-compatible readers, chain digests over the redacted form, and property tests.

### E3. The job lifecycle is not in the ledger
- **Source:** 7.c ("every job, run … and outcome, with its time, its actor and its evidence, written as it happens").
- **Requirement:** Enqueue, claim, lease renewal and expiry, reap, park, answer and completion are append-only ledger events.
- **Evidence:** `EventKind` (`ledger.py:37-69`) has no job kinds. Job state lives only in the mutable `job` table (`src/vibey/infrastructure/db/job_repository.py`).
- **Coverage:** none. R-lanes add an outbox, not ledger events.
- **Proposed:** 20B ×2.
  - `feat(ledger): job enqueue, claim and completion are ledger events`.
  - `feat(ledger): lease expiry, reap, park and redispatch are ledger events`.
  - Both are written in the same transaction as the job row, so they are idempotent under replay.

### E4. Engine selection and circuit transitions are not ledgered
- **Source:** 7.c ("decision, capacity signal").
- **Requirement:** Every selection (candidates, weights, winner) and every health or circuit transition is an event.
- **Evidence:**
  - Selection is only an OTel counter (`src/vibey/application/engine_selection.py:244-246`).
  - `engine_health` transitions are row updates.
- **Coverage:** partial. ADR-0046 adds `LoopRouted` and `PaidFallbackDeclared` (A1), in service mode only.
- **Proposed:** 20B. `feat(ledger): engine selections and circuit transitions are ledger events in both invocation modes`. Scope: no `resets_at` on credit events; the CHECK constraint and property tests stay.

### E5. Direct model calls write no turns or cost
- **Source:** 7.c ("every … turn, tool call … cost, measurement").
- **Requirement:** DESIGN, DECOMPOSE, VISUAL and review model calls write turn events with tokens and timings.
- **Evidence:**
  - `qwenloop_design.py` emits design artifacts but no `TurnRequested` or `TurnCompleted`.
  - `local_review.py` writes no ledger events.
- **Coverage:** partial. A4 and A5 would give them loop events.
- **Proposed:** 20B. `feat(ledger): sovereign provider calls record turns, tokens and timings`. It drops away if A4 lands first.

### E6. Ledger search covers one project at a time
- **Source:** 7.a: "the full public ledger where a deployment holds it".
- **Requirement:** Search across every project a deployment holds, with the same human-first output.
- **Evidence:** `src/vibey/cli/ledger_search.py:5` ("search over one project's ledger") and `:208-212` (resolves one project).
- **Coverage:** none. #136 plans a forge search, not deployment-wide ledger search.
- **Proposed:** 20B. `feat(ledger): vibey ledger search --all-projects searches everything a deployment holds`.

## F — OS support (8.h: Arch Linux sovereign default, macOS paid default)

### F1. vibey's gates never run on Arch Linux
- **Source:** 8.h: "every feature works on Arch Linux … every change is proven on it".
- **Requirement:** The full `gates` job runs on Arch Linux on every PR.
- **Evidence:** every job is `ubuntu-latest` (`.github/workflows/ci.yml:20`, `:32`, `:107`, `:144`, `:200`). No `archlinux` appears anywhere in `.github/`.
- **Coverage:** none. The installer specs target Arch but add no CI.
- **Proposed:** 20B. `ci: the gates run on Arch Linux`. Scope: an `archlinux:base-devel` container job with Python 3.12+ and `uv`, PostgreSQL 17 (or the integration tier split per fakes-harness-decouple), and the same 7-gate sweep.

### F2. vibey's gates never run on macOS
- **Source:** 8.h (macOS "with the same standing, so a change that works on one but not the other is not done").
- **Requirement:** The full `gates` job runs on macOS.
- **Evidence:** only the codexloop tenant rows set `os: macos-latest` (`ci.yml:413`, `:425`, `:437`).
- **Coverage:** none.
- **Proposed:** 20B. `ci: the gates run on macOS`.

### F3. Tenants run on Arch Linux and macOS
- **Source:** 8.h.
- **Requirement:** Every tenant row (runners, vibey-gh, bootstrap, skills) runs on both default OSes.
- **Evidence:** the `tools` matrix (`ci.yml:200-440`) is Ubuntu except codexloop.
- **Coverage:** none.
- **Proposed:** 20B. `ci: every tenant row runs on Arch Linux and macOS`. `tests/meta/test_tools_matrix_covers_every_package.py` should assert both OSes.

### F4. Merge rules do not require the default OSes
- **Source:** 8.h; 12.c (declared rulesets).
- **Requirement:** The rulesets in `.vibey-gh.toml` require the Arch Linux and macOS checks.
- **Evidence:** `.vibey-gh.toml` `[rulesets.integration]` and `[rulesets.release]` (`:130-165`) have no OS checks.
- **Coverage:** none.
- **Proposed:** 20B, after F1 and F2. `ci(rulesets): the Arch Linux and macOS gates are required checks`.

### F5. Installer smoke test on both OSes
- **Source:** 8.h ("the installer serves it"); the operator's installer standard.
- **Requirement:** CI proves `vibey install --dry-run` and the doctor output on Arch Linux and macOS.
- **Evidence:** nothing found.
- **Coverage:** none. The installer lanes have unit tests with faked package managers only.
- **Proposed:** 20B, after `installer-cli`. `ci: vibey install and doctor are smoke-tested on Arch Linux and macOS`.

### F6. The container image is Debian
- **Source:** 8.h ("Arch Linux is always the default sovereign operating system vibey supports").
- **Requirement:** An operator ruling on whether the OCI image offers an Arch Linux base, or a statement that images are exempt.
- **Evidence:** `deploy/docker/Dockerfile:27` and `:157` (`bookworm`).
- **Coverage:** none.
- **Proposed:** 20B, after the ruling. `build(image): an Arch Linux image variant, contract-tested like the Debian one`. Low priority.

## G — Packaging (2.b: installable wherever users already are)

### G1. The runnable image is never published
- **Source:** 2.b; ADR-0019 Consequences step 1.
- **Requirement:** The contract-tested runnable image is pushed to ghcr.io on every release, and to the sovereign forge's registry.
- **Evidence:**
  - CI builds with `load: true` / `push: false` (`ci.yml:746-760`, `:840-850`).
  - `release-surfaces.yml:145-158` pushes only the wheel and sdist as an OCI artifact (`…/python`).
- **Coverage:** none.
- **Proposed:** 20B. `ci(release): publish the runnable multi-arch image on every release`.

### G2. No single-file executable
- **Source:** 2.b; ADR-0019 step 2.
- **Requirement:** A single-file build of the CLI is attached to every release.
- **Evidence:** nothing found.
- **Coverage:** none.
- **Proposed:** 20B. `build(release): a single-file vibey executable is a release artifact`.

### G3. No package-manager recipes in the tree
- **Source:** 2.b ("Every packaging definition lives in the repository as code"); 8.h (Arch first).
- **Requirement:** Declared recipes for the channels users already use, published by automation.
- **Evidence:** no PKGBUILD, formula, winget, Scoop, Chocolatey, COPR, PPA, Nix or npm definition anywhere. The only mentions are `docs/runbooks/expansion/09-package-managers.md` and ADR-0019.
- **Coverage:** none.
- **Proposed:** EPIC `feat(packaging): vibey is installable from the package managers users already run`. Children:
  1. AUR PKGBUILD (first, per 8.h).
  2. Homebrew formula (the tap exists and is empty).
  3. winget, Scoop and Chocolatey manifests.
  4. COPR, PPA, OBS and Alpine.
  5. Nixpkgs.
  6. An npm wrapper that says it installs a command, not a library.
  - Each child carries the governance link (7.b) and states what the install does not include.

### G4. No release-channel conductor, and stale channels go unseen
- **Source:** 2.b ("nothing is added that is not published by the same automation … a stale package installs an old version silently"); ADR-0019 (vibey-gh conducts it).
- **Requirement:** vibey-gh publishes every channel from one release, and a check fails when a channel lags the canonical version.
- **Evidence:** no channel logic in `src/vibey_tools/gh/vibey_gh/`.
- **Coverage:** none.
- **Proposed:** 20B ×2.
  - `feat(gh): vibey-gh release-channels publishes every declared channel`.
  - `feat(gh): a channel whose version lags the release fails the release-surfaces check`.

## H — Installer

Largely covered: #391 plus 16 installer specs (Appendix B).

### H1. GPU-accelerated Ollama on Arch Linux
- **Source:** 10's decomposition clarification ("read both sides of the fit"); the operator's installer standard.
- **Requirement:** On Arch, the installer installs the Ollama build that matches the machine's GPU (`ollama-cuda`, `ollama-rocm`, `ollama-vulkan`).
- **Evidence:** `specs/installer-ollama.md:117` names it "a follow-up".
- **Coverage:** none.
- **Proposed:** 20B. `feat(install): Ollama's GPU build is chosen from the detected GPU on Arch Linux`.

## I — ORM always behind interfaces

Largely covered by 17 `orm-*` specs, still being written (Appendix B).

### I1. The cluster preflight's raw asyncpg calls are in no ORM spec
- **Source:** the operator's standard (ORM always behind interfaces); 9.b.
- **Requirement:** Every database access goes through the ORM seam and a repository interface.
- **Evidence:**
  - `src/vibey/infrastructure/cluster_preflight.py:20`, `:244-271` (`asyncpg.connect` and a migration check on a raw connection).
  - At 15:20Z the advisory lock was covered by the new `orm-advisory-lock`. `orm-migrator-callers` runs `test_cluster_preflight.py` but does not list `cluster_preflight.py` under *Where to change*.
- **Coverage:** partial. The named but unwritten `orm-raw-sql-guard` (`specs/orm-import-contracts.md:71`) may absorb it.
- **Proposed:** 20B. `refactor(db): the cluster preflight checks the database and its migrations through the ORM seam`. Re-check once the ORM spec set is final.

## J — Comprehensive in-memory fakes

Largely covered by about 25 `fakes-*` specs, still being written (Appendix B).

### J1. Tenant suites have no fakes registry or isolation guard
- **Source:** the operator's standard ("no outside thing is needed to run tests"); 9.b.
- **Requirement:** vibey-gh, vibey-bootstrap, vibey-skills and every runner tenant each have a fakes registry, a patching ratchet and an outside-service guard.
- **Evidence:** `specs/fakes-registry.md:163` and `specs/fakes-isolation-guard.md:96` put tenants out of scope ("each tenant lane decides"). No tenant lane exists.
- **Coverage:** none.
- **Proposed:** EPIC `test(fakes): every tenant suite runs with no outside service`, one child per tenant (gh, bootstrap, skills, claude, codex, cursor, agy, qwen/sovereign, common).

### J2. Named follow-on fakes lanes not yet written
- **Source:** as J1.
- **Requirement:** `fakes-ci-no-services` (CI drops the Postgres service from the default tier) and `fakes-amendment` exist as specs.
- **Evidence:** named in `specs/fakes-harness-decouple.md:106` and `specs/fakes-registry.md`. No file at 15:18Z. (`fakes-sockets` has since appeared.)
- **Coverage:** partial (named).
- **Proposed:** finish those specs. Re-check later.

## K — Surfaces (8.b list; 8.f: one lane per surface on the bus)

### K1. ADR-0047's lanes (S01–S34): designed, not specced (grouped)
- **Source:** 8.f (ratified by #392); ADR-0047 draft `specs/ADR-surface-lanes.md` §1–§15.
- **Requirement:** Every sovereign surface, including the cache, is reached only through one consumer lane per deployment on RabbitMQ, with idempotency and dead-letter parks.
- **Evidence:** nothing found: no `surface_lanes/`, no `vibey surface`, no `surface_operation` table. `build_app` wires adapters directly (`bootstrap.py` surface block).
- **Coverage:** none. The ADR names S01–S34, but no lane file exists.
- **Proposed:** EPIC `feat(surfaces)!: every sovereign surface runs in one lane driven by RabbitMQ`. Children:
  - S01–S03: catalogue, protocol and config.
  - S04–S06: idempotency keys, native where the backend has them.
  - S07–S09: family AMQP lease and unconfirmed publish, async retry, memo.
  - S10–S12: migration `0015_surface_lanes`.
  - S13: pipelined Redis.
  - S14–S27: the lane host, client, queued adapters and reconcile.
  - S28: `vibey surface serve|ping|dead-letters|requeue`.
  - S29–S31: chart and cluster-smoke.
  - S32: the measurement.
  - S33: the default flip, gated on 8.f's owed amendments and the operator accepting the cache cost.
  - S34: the docs wave.

### K2. No production code uses any surface
- **Source:** 8.b ("every operational surface of vibey defaults to the … sovereign option"); ADR-0047 Context ("Who calls them: nobody yet").
- **Requirement:** vibey's operations actually use their sovereign surfaces.
- **Evidence:**
  - Surface ports are read only by `bootstrap.py` wiring and `tests/infrastructure/test_sovereign_surfaces.py`.
  - Notifications go to desktop alerts and webhooks (`src/vibey/infrastructure/notify/service.py:14-26`).
- **Coverage:** none.
- **Proposed:** EPIC `feat(surfaces): vibey's own operations use their sovereign surfaces`. Children:
  1. Operator notifications (gates, parks, capacity) through `MessagingPort` (Matrix), with email and SMS sinks.
  2. Engine and forge credentials read from `SecretsPort` (OpenBao).
  3. Work items mirrored to Plane (`IssueTrackerPort`).
  4. Accepted specs and ADRs published to BookStack (`DocsPort`).
  5. Visual media, review artifacts and handoff briefs stored in Garage (`BlobPort`).
  6. Prompt-shield, command-guard and scope-guard findings sent to Wazuh (`SiemPort`).
  7. Project configuration through `ConfigStorePort` (Infisical).
  8. A first real cache consumer.
  9. Delivered files in Nextcloud (`FilesPort`).

### K3. Surface adapters have no timeouts and reconnect on every call
- **Source:** doctrine 10 (no guarantees; self-healed around); ADR-0047:560 ("Giving the adapters socket timeouts is a follow-up defect fix").
- **Requirement:** Every sovereign adapter passes a bounded timeout, from config, to every network call.
- **Evidence:** `self._opener(req)` with no timeout at:
  - `src/vibey/infrastructure/tracker/plane.py:61`, `:77`
  - `docs/bookstack.py:53`, `:73`
  - `secrets/openbao.py:47`, `:70`
  - `config_store/infisical.py:54`, `:81`
  - `blob/garage.py:112`
  - `messaging/matrix.py:44`
  - `siem/wazuh.py:51`
  - `sms/kannel.py:55`
- **Coverage:** partial. S13 fixes only the Redis connection.
- **Proposed:** 20B. `fix(surfaces): every sovereign adapter bounds each call with a configured timeout`.

## L — Release & CI operations

### L1. The merge train and Promote stopped firing when #317 merged
- **Source:** CLAUDE.md (feature PRs squash into `develop` through the merge train; `vibey-gh promote` moves `develop` to `main`); ADR-0028; ADR-0036.
- **Requirement:** A completed PR review triggers the merge train, and a completed train triggers Promote.
- **Evidence:**
  - Last merge-train run 2026-09-21T19:21:38Z; last Promote run 19:22:20Z.
  - #317 merged at 19:29:03Z.
  - Every "PR review" run since is a `workflow_dispatch` (about 30 runs).
  - `merge-train.yml:6-9` listens for "PR review" `workflow_run` completion.
  - Cause unknown. Leading hypothesis: completion of a run dispatched by `GITHUB_TOKEN` does not raise `workflow_run`. Only the Monday cron backstops remain.
- **Coverage:** none.
- **Proposed:** 20B. `fix(gh): the merge train and promotion fire again after the evaluate/review split`. Scope: confirm the cause from event data; have the evaluate or review workflow dispatch `Merge train` explicitly (the family pattern); add a `tools-lint` drift contract that each link in the chain has a live trigger.

### L2. The PR-review gate cannot pass
- **Source:** Constitution III.3 (the two lanes back each other); 8.a.
- **Requirement:** At least one review lane can produce the required `PR review / gate`.
- **Evidence:**
  - Paid lane: every run's "Say why the model call failed" prints "Credit balance is too low".
  - Sovereign lane: runner launchd plists set `VIBEY_REPO_URL=https://github.com/adammatthewsteinberger/<repo>`. Registration has returned 404 since 2026-08-31.
  - Latest `pr-review.yml` run: failure at 2026-09-22T15:06Z.
- **Coverage:** none.
- **Proposed:** ops (operator). `ops: restore a working review lane`. Fund the key, or re-register the sovereign runners against `the-vibey-project/vibey`. The second is a security decision, because it runs PR review on the operator's Mac.

### L3. The review runners and their heartbeat are not declared as code
- **Source:** 12.c ("a stranger with a clone and admin rights can restore the state from the tree"); 10.f (no false status).
- **Requirement:** The supervisor, the launchd and systemd units, and the heartbeat live in the repository and are reconciled from it. The heartbeat says "ready" only when a runner is registered and idle.
- **Evidence:**
  - `~/Library/LaunchAgents/com.adammatthewsteinberger.vibey-runner-*.plist` and `~/.local/share/vibey-runner/vibey-local-authority.sh` are not in the tree.
  - Only `vibey_gh/sovereign.py:60` (`beat`) is in the tree.
  - The heartbeat publishes whenever a PID is live.
- **Coverage:** none.
- **Proposed:** 20B ×2.
  - `ci(runners): the sovereign review runners are declared (launchd and systemd) with their registration URL from config`.
  - `fix(gh): the sovereign heartbeat beats only for a registered, idle runner`.

### L4. This repository never declares GitHub as its forge
- **Source:** 8.b (GitHub is declared-only; the paid-default forge must be declared aloud).
- **Requirement:** The root `.vibey-gh.toml` declares `[platform] kind = "github"` before forge wave 2 routes every command through the adapter.
- **Evidence:**
  - No `[platform]` table in `.vibey-gh.toml` (tables at `:6-244`).
  - The fixing commit `b60dad4c fix(gh): declare this repository's forge as github` is on no branch of the integration clone. It was carried on unmerged `docs/changelog-2.1.0`.
  - `specs/forge-adapter.md:1855-1858`.
- **Coverage:** none.
- **Proposed:** 20B. `fix(gh): declare this repository's forge as github`, landed before #339–#344.

### L5. The exact-head gate read is not paginated
- **Source:** the constitution's exact-head review (Article V.1); 10.f.
- **Requirement:** Gate evaluation reads every check run on the head.
- **Evidence:** `specs/forge-adapter.md:1873` ("the exact-head gate read is not paginated (`check-runs` returns 30 per page)"). The forge lanes keep the behaviour byte for byte.
- **Coverage:** none.
- **Proposed:** 20B. `fix(gh): the exact-head gate reads every page of check runs`.

### L6. No warning when GitHub Actions runs against a Forgejo default
- **Source:** 8.b migration safety; `specs/forge-adapter.md:1855-1860`.
- **Requirement:** `vibey-gh doctor` warns when `GITHUB_ACTIONS=true` and the kind is `forgejo`.
- **Evidence:** nothing found.
- **Coverage:** none.
- **Proposed:** 20B. `feat(gh): doctor warns when GitHub Actions runs with the forgejo default`.

### L7. The default rulesets fail on Forgejo
- **Source:** 8.b (Forgejo is the default forge); 12.c; `specs/forge-adapter.md:1866-1872`.
- **Requirement:** A declared Forgejo ruleset profile, so the default `[rulesets]` does not fail on the default forge.
- **Evidence:** forge-0g refuses six rules. The memory file lists a "Forgejo ruleset profile" as an operator follow-up.
- **Coverage:** none.
- **Proposed:** 20B, after an operator ruling on the mapping. `feat(gh): a Forgejo ruleset profile that maps or waives each unsupported rule loudly`.

### L8. Three vibey-gh paths stay GitHub-only after the forge wave
- **Source:** 8.b (one protocol per surface); #138.
- **Requirement:** `forge-snapshot`, `forecast` and the rendered workflow templates go through the forge adapter.
- **Evidence:** `specs/forge-adapter.md:1890-1894` (`cli.py:598-604`, `:835-837`, `vibey_gh/templates/`).
- **Coverage:** partial (#136, #138 in spirit).
- **Proposed:** 20B ×2.
  - `feat(gh): forge-snapshot and forecast read through the forge adapter`.
  - `feat(gh): workflow templates render for Forgejo Actions`.

### L9. Article V.4 yanks are neither automated nor tracked
- **Source:** Constitution V.4 ("Any RATIFIED change … immediately yanks all previous versions … where an index offers no yank API the demand falls to the maintainer as their immediate next act").
- **Requirement:** Every ratifying merge produces the list of versions to yank and a tracked checklist for the maintainer.
- **Evidence:**
  - `src/vibey_tools/gh/vibey_gh/yank.py:1-30` reports only.
  - `report-superseded` appears in no workflow (`grep` of `.github/workflows/` returns nothing).
  - #325, #384, #385 and #392 were ratified on 2026-09-22.
- **Coverage:** none.
- **Proposed:** 20B plus ops.
  - `ci(release): a ratifying merge runs report-superseded and opens the maintainer's yank checklist`.
  - A one-off `ops: yank every release superseded by #392 on PyPI and TestPyPI`.

### L10. The 3.0.0 release lacks a gating checklist
- **Source:** operator decision (3.0.0 is breaking); ADR-0028; ADR-0037.
- **Requirement:** 3.0.0 ships only after the behaviour flips, the docs wave and the yanks.
- **Evidence:** `pyproject.toml:7` = 2.1.0. #316 is a draft PR titled `chore(release): 3.0.0`. #393 covers version derivation only.
- **Coverage:** partial (#316, #393).
- **Proposed:** 20B. `chore(release): 3.0.0 gating checklist`. It lists the dependencies:
  - R34 (#381), S33 and T28 default flips (or explicit deferral);
  - the M1–M10 docs;
  - L9;
  - L1–L4.

## M — Docs wave

Partial coverage exists: R35 in `specs/rabbitmq-lanes.md:3932` (ADR-0044's part only) and S34 (named, not specced). ADR-0045 and ADR-0046 list their docs under "Owes" only.

### M1. CHANGELOG has no 3.0.0 section, and no 2.1.0 section either
- **Evidence:** `CHANGELOG.md:13` (`[Unreleased]`), then `:24` (`[2.0.0]`). `pyproject.toml:7` = 2.1.0.
- **Coverage:** none.
- **Proposed:** 20B. `docs(changelog): 2.1.0 and 3.0.0`. Scope: every `!` change, the Forgejo data-loss warning, the OpenCode repeal and the default-model change.

### M2. CLAUDE.md, AGENTS.md and GEMINI.md state repealed facts
- **Source:** 8.b, 8.c, 8.d, 8.e, 8.h.
- **Evidence:**
  - `CLAUDE.md:3-6` ("six `*loop` … runners", opencode), `:140-146` ("FOR UPDATE SKIP LOCKED", opencode in the paid pool, qwenloop opt-in).
  - `AGENTS.md:3-5`, `:92`, `:158`; `GEMINI.md:3-6`, `:85`.
  - None mentions sovereignloop/paidloop, RabbitMQ dispatch, the harness queue, surface lanes, gpt-oss:20b or Arch/macOS.
- **Coverage:** partial (R35: the queue fact only).
- **Proposed:** 20B. `docs(agents): CLAUDE.md, AGENTS.md and GEMINI.md state 3.0.0's law`.

### M3. The four skill trees are stale
- **Evidence:** `.claude/skills/vibey-engine-adapters`, `…/vibey-testing`, `…/vibey-quality-gates`, `…/vibey-releasing` and their three mirrors predate 8.c–8.h.
- **Coverage:** partial (R35: queue only).
- **Proposed:** 20B. `docs(skills): the four agent-surface trees teach two loops, the harness queue, fakes, the Arch/macOS gates and packaging`.

### M4. CLI and configuration references are incomplete or stale
- **Evidence:**
  - `docs/reference/cli.md` documents `ledger show` but not `ledger search`, `export` or `site`.
  - `:157` still says `--provider` defaults to `scripted` (#322 changed it).
  - `install` covers `--postgres` only (`:46-47`, `:72-80`).
  - `configuration.md` has no `[queue]`, `[loop_services]`, `[test_harness]`, `[surfaces]` or `[sovereignloop]`, and `[email]` is titled "Forward Email" (`:342`).
- **Coverage:** partial (R35, S34 named).
- **Proposed:** 20B ×2.
  - `docs(reference): cli.md covers every command at 3.0.0`.
  - `docs(reference): configuration.md covers every table at 3.0.0`.

### M5. The paper predates the new law
- **Evidence:** `docs/paper.md` has no two-loop, surface-lane, measurement, 8.d-evidence or default-OS content.
- **Coverage:** partial (#301 revision, R35 queue section).
- **Proposed:** 20B. `docs(paper): two loops, surface lanes, measurement and the model evidence`. Keep `test_paper_evidence.py` green.

### M6. The expansion runbooks contradict 8.b and 8.c
- **Evidence:**
  - `docs/runbooks/expansion/01-jira-integration.md` makes Jira primary.
  - `03-multicloud-aws-gcp.md` predates AWS as the paid default.
  - `16-loop-runner-containers.md` plans per-engine containers.
  - `02-copilotloop.md` and `09-package-managers.md` have 2026-09-15 status lines.
- **Coverage:** none.
- **Proposed:** 20B. `docs(runbooks): align the expansion runbooks with 8.b's defaults and 8.c's two loops`.

### M7. ADR housekeeping is owed
- **Evidence:**
  - ADR-0045, ADR-0046 and ADR-0047, plus the installer ADR (`specs/ADR-installer.md`, number unassigned), exist only as drafts in `specs/`.
  - ADR-0039 to ADR-0044 still say "proposed" although 9.c, 9.d, 10.f, 8.b and 8.c are ratified.
  - ADR-0042's table (`0042-…md:37-47`) names Bitwarden, forward-email, fossify and opencode.
  - ADR-0046 owes status notes on 0005, 0015, 0038, 0042 and 0044. R35 owes notes on 0002, 0009 and 0025.
  - "(44 ADRs)" appears at `CLAUDE.md:221`.
- **Coverage:** partial (R35 for ADR-0044).
- **Proposed:** 20B ×2.
  - `docs(adr): land ADR-0045, 0046, 0047 and the installer ADR, and the status notes they owe`.
  - `docs(adr): ratified records say accepted; ADR-0042's table matches 8.b`. Add a meta-test tying ADR status to canon ratification.

### M8. Ratified sub-doctrines with no decision record
- **Source:** 12.b ("A decision record may argue a rule; only the canon states it, and both are written").
- **Evidence:**
  - No ADR cites 7.a, 7.c, 8.d, 8.g or 8.h (grep of `docs/architecture/decisions/`).
  - The forward-compatible reader rule (#275, #287) has no ADR (ADR-0046 flag).
- **Coverage:** none.
- **Proposed:** 20B ×2.
  - `docs(adr): decision records for 7.c, 8.d, 8.g and 8.h`.
  - `docs(adr): 7.a's searchable ledger and the forward-compatible reader rule`.

### M9. README and the quickstart omit the default OSes and the 3.0.0 install
- **Evidence:** `README.md:58` ("macOS / Linux"), `:68` ("PostgreSQL 14+"). Nothing names Arch Linux, a bare `vibey install`, or gpt-oss:20b.
- **Coverage:** none.
- **Proposed:** 20B. `docs(readme): Arch Linux and macOS, one-command install and the default model`.

### M10. New surfaces lack runnable examples (doctrine 3)
- **Evidence:** planned new commands have no runnable examples in `docs/examples/`:
  - `loop-service` and `loop submit` (R27);
  - `vibey test` (T15);
  - `vibey surface` (S28);
  - `install` (installer-cli).
- **Coverage:** none.
- **Proposed:** 20B. `docs(examples): one runnable example for each 3.0.0 command`.

## N — Governance tooling

### N1. SD-01 is not carried in every agent surface
- **Source:** SD-01 §8 ("Carry this text verbatim in the system prompt or CLAUDE.md of every agent it governs").
- **Evidence:**
  - "Subdoctrine SD-01" appears in root `CLAUDE.md` and several tenant CLAUDE.md files.
  - It is absent from root `AGENTS.md`, `GEMINI.md`, `.cursor/rules/*`, `.agent/rules/*`, `.agents/skills/*`, `src/vibey_runners/opencode` and `src/vibey_runners/common`.
  - No meta-test checks carriage.
- **Coverage:** none.
- **Proposed:** 20B. `test(meta): SD-01 is carried verbatim in every agent surface, and the missing ones get it`.

### N2. No parity check across the four agent-surface trees
- **Source:** CLAUDE.md ("update Claude, Cursor, Codex, and Antigravity trees in the same PR"); runbook 15 (not started).
- **Evidence:** `tests/meta/` has no tree-parity test.
- **Coverage:** none.
- **Proposed:** 20B. `test(meta): the agent-surface trees carry the same skills with the same body`.

### N3. Sub-doctrines owed under 12.b, not yet drafted
- **Evidence:**
  - ADR-0024:28 ("no unbounded autonomous loop …").
  - ADR-0025:33 ("a second entry point never grows its own copy of the logic").
  - ADR-0030:27 ("paid is opt-in", possibly subsumed by 8.b).
  - ADR-0046 §1 ("sovereignty follows the model and the tool"; "a new runner joins a loop as an adapter").
  - The #275/#287 reader rule.
- **Coverage:** none.
- **Proposed:** 20B, drafting only. `docs(canon): draft the owed sub-doctrines for the operator's ratification`. A machine drafts; the operator ratifies (Article II.3).

### N4. Canon/code conflicts that need operator rulings
- **Evidence:**
  1. 8.b names Redis, but `specs/installer-broker-cache.md` installs Valkey under 8.a's freer-licence rule.
  2. 8.b says "VS Code"; ADR-0046 builds on Code - OSS.
  3. OpenCode's immediate repeal vs ADR-0046 §9's transitional adapter (A3).
  4. `claudeloop-local` is not FOSS, against 8.b's "free".
  5. 8.c's heading vs "one instance per model".
  6. The 8.f cache cost must be accepted in writing (ADR-0047 §15).
  7. #148's PayPal vs 10.b ("No fiat processors, ever").
  8. Retiring opencodeloop is less configurable under 12.c.
- **Coverage:** none.
- **Proposed:** one tracking issue. `docs(canon): rulings owed to the operator (8.a–8.f, 10.b, 12.c)`. Each ruling becomes a ratifying PR or a spec change.

### N5. No 9.b convergence ratchet
- **Source:** 9.b; CLAUDE.md ("the existing tree converges module by module").
- **Evidence:** no meta-test counts classes without an interface beside them, or module-level functions without a written reason. `fakes-registry` adds only a patching baseline.
- **Coverage:** partial (fakes-registry's patching ratchet).
- **Proposed:** 20B. `test(meta): a ratchet that only lowers the count of classes without interfaces and of unexplained module functions`.

### N6. Status surfaces are not evidence-bounded
- **Source:** 10.f; ADR-0040.
- **Evidence:** `vibey status`, `watch` and the TUI (`src/vibey/cli/main.py:709-790`; `src/vibey/tui/dashboard.py`) print state with no source or cutoff. No `unknown | active | blocked | failed | verified | published` vocabulary exists in the domain.
- **Coverage:** none.
- **Proposed:** 20B ×2.
  - `feat(domain): the evidence-bounded status vocabulary`.
  - `feat(cli): status surfaces name their object, source and cutoff`.

### N7. CDD is not in the runtime
- **Source:** 9.c; ADR-0039 (the distance D(R) at four scopes).
- **Evidence:** the BUILD loop records no trajectory. Only the out-of-tree `qwenlane.py` runs CDD repair attempts.
- **Coverage:** none.
- **Proposed:** 20B ×2.
  - `feat(domain): the CDD distance and trajectory classifier`.
  - `feat(build): each BUILD iteration records its converging, neutral or diverging trajectory in the ledger`.

### N8. Cloud-grade clearance (10.d) is not implemented
- **Source:** 10.d (clearance criteria per transition, recorded overrides, re-verification at every transition, loud socialization).
- **Evidence:** "clearance" appears only in `doctrines.md`.
- **Coverage:** partial (#134's feasibility engine).
- **Proposed:** EPIC. Children:
  - Domain clearance criteria and recorded overrides.
  - Re-verification at each pipeline transition.
  - The override broadcast with threshold, current measurement and "the bill to restore clearance".

### N9. Nothing makes the project translatable (12.a)
- **Source:** 12.a.
- **Evidence:** human-facing CLI strings are inline literals. There is no message catalogue.
- **Coverage:** none.
- **Proposed:** 20B, low priority. `feat(cli): human-facing strings move to a message catalogue`.

---

## Appendix A — Open issues that ratified law now contradicts

- **#321:** keeps opencode always on (A3).
- **#366–#375 and #377:** per-engine loop services, against 8.c's two loops and one instance per model (A2).
- **#369:** R22's supersede design, which ADR-0046 shows cannot fire at prefetch 1 (A2).
- **#85:** plans vibey-opencode and repo-per-provider siblings, against #392's OpenCode repeal and ADR-0037's single distribution.
- **#148:** includes PayPal, against 10.b (N4).
- **#322:** the provider text names `qwenloop`, which A1's L09 renames to `sovereignloop` (the alias keeps it valid through 3.x).

## Appendix B — Covered by specs, but not filed as issues

Queued work, not gaps:
- **T01–T28:** `specs/test-harness-lanes.md`, 8.e.
- **R35:** `specs/rabbitmq-lanes.md:3932`, the ADR-0044 docs wave.
- **Installer** (the full set as of 15:18Z): `installer-catalogue`, `-host-runner`, `-service-runner`, `-orchestrator`, `-package-dependency`, `-postgres`, `-local-service-adapter`, `-container-runtime` (Docker Desktop / docker), `-toolchain` (git, uv, llama.cpp, opt-in helm/kubectl/minikube), `-broker-cache` (RabbitMQ, Valkey), `-vscode`, `-paid-engine-clis`, `-composition`, `-cli`, `-doctor`, plus `installer-ollama` (#391).
- **ORM** (still being written at 15:20Z): `orm-bootstrap-async-engine`, `-database-seam`, `-app-resources`, `-import-contracts`, `-tables`, `-test-harness`, `-ledger`, `-ledger-guard`, `-ledger-search`, `-project`, `-engine-health`, `-rotation-cursor`, `-handoff`, `-human-gate`, `-job-statements-enqueue`, `-job-statements-settle`, `-notifier`, `-advisory-lock`, `-migrator-callers`. Named but not yet written: `orm-cli-recover`, `orm-raw-sql-guard`, `orm-bootstrap-engine`. The installer ADR draft is `specs/ADR-installer.md`.
- **Fakes** (still being written): about 30 `fakes-*` specs, including registry, harness-decouple, isolation-guard, http-transport, sockets, sovereign-http, sovereign-smtp, process-executor, process-spawner, operator-k8s, db-sql-transcripts, cli-composition, cli-operational-1..3, engines, ledger, queue-gates, projects, build, design, deploy, review-visual, review-routing, observability and job-wakeup. Named but not yet written: `fakes-ci-no-services`, `fakes-amendment`, `fakes-contracts-repositories`, `fakes-tui-system`, `fakes-bootstrap-seam`.

## Appendix C — Checked and found resolved, so not reported

- **The SIGTERM latch drain bug:** fixed by #199 (`803a6448`). `src/vibey/cli/early_signals.py:84` resets `SIG_DFL` only while the latch's own handler is installed. Pinned by `tests/cli/test_early_signals.py`.
- **ADR-0024's "agyloop cost events":** agyloop emits `cost_usd` (`src/vibey_runners/agy/src/agyloop/application/runner.py:545-576`).
- **ADR-0043's `VibeySurface` CRD and surface charts:** present (`deploy/helm/vibey/crds/crd-vibeysurface.yaml`).
