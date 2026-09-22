# Roadmap children not specified, and why (QwenStorm 3.0.0)

Source: the "Proposed child issues" of `issue-audit/updates/<N>.md` for the 23 roadmap issues,
read against `STORM-CONTEXT.md` (2026-09-22). Written 2026-09-22. Every question is quoted
verbatim from the parent's "Open questions for the operator"; nothing here guesses an answer.

Four sections:
1. **Blocked on an operator question** — no spec until the operator answers.
2. **Excluded or constrained by ratified law** — no spec, by law.
3. **Waiting on a design spike or evidence** (no operator question; specced later).
4. **Covered elsewhere, or not a lane** — owned by another spec set, the docs wave, or an operator action.

---

## 1. Blocked on an operator question

### #85 Ecosystem expansion
- **Child 5 — Matrix emitter with replies.** Waits on Q3: "**Does "social" now mean Matrix-first?**
  Should Moltbook (#139) be folded into it?"
- **Child 7 — vibey-career (design).** Waits on Q1: "**vibey-career:** what should it do? Keep a
  résumé in the repository in sync with shipped work (as #237 did by hand)? Post to LinkedIn (a
  hosted platform, declared-only under 8.b)? Both?"
- **Child 8 — word-of-mouth postal channel (design).** Waits on Q2: "**Physical post (USPS / UPS /
  FedEx):** these are paid counterparties with no sovereign equivalent, and SD-01 §1 forbids
  gathering or relaying private details such as home addresses. Should postal outreach be dropped,
  or limited to addresses a person published for that purpose?" (See also §2: SD-01 §1.)
- **Child 4 — GCP relay adapter.** Follows the AWS design (`gap-spike-aws-iac`); see §3.

### #86 Monetization
- **Child 1 — ADR + sub-doctrine: the billing boundary and FOSS unbillability.** Waits on Q1:
  "**Billing boundary under ADR-0037:** one distribution means a FOSS install carries the same code.
  Is "absence" satisfied by an import-linter-proven isolated module, or must billing live outside
  the `vibey` distribution?" and Q4: "**Is billing a hosted-platform-only feature** (#89's
  boundary), never present in self-hosted installs at all?"
- **Child 2 — `ProjectLicenceClass` with the unbillable invariant.** Waits on Q1 (where billing code
  may live) and Q2: "**Who classifies FOSS, and who adjudicates a dispute?** (For example: an
  OSI-approved licence in the target repository plus a human gate.)"
- **Child 3 — classification column + CHECK forbidding billable usage on FOSS projects.** Waits on Q1
  and Q2 (after child 2).
- **Child 5 — usage metering for commercial projects.** Waits on Q1 and Q4 (it is billing code).
- **Child 6 — settlement over the shared crypto rail (design).** Waits on Q3: "**Settlement asset**
  under 10.b: which cryptocurrency (see #148's question 2)?" and on #148 Q1 (custody).

### #87 Work discovery and ideation
- **Child 3 — forge-search discovery source.** Waits on Q2: "**Sources:** which forges and bounty
  platforms first? Is a public hosted forge's search API acceptable as a *read* source under
  8.a/8.b, as long as vibey's own forge stays sovereign?"
- **Child 5 — classification FOSS / paid-crypto / paid-fiat.** Waits on Q1: "**Fiat-paying
  bounties:** 10.b forbids fiat processors. Should they be excluded entirely, or listed for
  FOSS-only (unpaid) contribution?"
- **Child 6, rate-cap half — daily PR cap and staleness window.** Waits on Q3: "**Rate caps:** the
  daily PR cap and the staleness window (runbook 21 asks for them)." (The scorer and the skip
  registry are specced: `roadmap-87-scoring-skiplist-p1`, `-p2`.)
- **Child 8 — ideation research (design).** Waits on Q2 (sources) and Q4: "**Ideation output:** a
  new project on the operator's forge, or a proposal document only?"

### #88 Delivery economics
- **Child 3 — the milestone and engagement model (design).** Waits on #86 Q1/Q2 (the commercial side
  of the boundary) and #88 Q2: "**Hourly billing:** who records hours when the worker is a machine:
  engine time, wall-clock, or human review time?" and Q3: "**Should milestone forecasting live in the
  conductor** (per project) while vibey-gh's forecast stays repository-wide? Or should they merge?"
- **Child 4 — per-milestone prediction events.** Waits on child 3 (same questions).
- **Child 5 — the margin trend projection.** Waits on child 3 (a contracted price per milestone).
- **Child 6 — the payment gate on the crypto rail (design).** Waits on #148 Q1 (custody) and #88 Q1:
  "**Settlement asset and timing:** with 10.b, what counts as "paid" (on-chain confirmation count? a
  specific asset?), and what counts as "overdue"?"

### #89 Hosted-platform identity and operations
- **Child 3 — `Role` and `Grant` value types.** Waits on Q2: "**Is the hosted platform in this
  repository at all?** Or is it a separate product that consumes vibey's API (#143)?"
- **Child 4 — the audit trail through `ChainedAuditRecord`.** Waits on Q2 (its authority is a role
  and grant, child 3).
- **Child 5 — the hosted-platform boundary (design).** Waits on Q2 and #86 Q1.
- **Child 6 — a self-hosted identity provider and SSO (design).** Waits on Q1: "**Identity provider
  default:** 8.b does not enumerate one. Should a self-hosted IdP be ratified as the identity
  surface's sovereign default, with hosted IdPs declared?"
- **Child 7 — config boards that open pull requests (design).** Waits on Q2.
- **Child 8 — dashboards from ledger projections.** Waits on Q2 (and #143's API).
- (Q3 — "**Tracing "every repo it touched":** … keyed on the delivery (project) as today, or on a
  cross-repository engagement?" — does not block the two specced lanes, which keep today's key.)

### #90 Marketplace
- **Child 1 — the design doc with the doctrine boundary verbatim.** Waits on Q4: "**Is this still
  wanted before #143/#89 exist**, or should the design doc wait for them?" and Q1: "**Hosted or
  federated?** One public marketplace the project runs, or software anyone can self-host (8.a),
  possibly federated between instances?"
- **Child 2 — participant verification and labelling under SD-01 (design).** Waits on Q3:
  "**Verification of humans:** what evidence makes a participant "human" under SD-01 §2 (for
  example, a signature from a known key, or confirmation over a separate channel)?"
- **Child 3 — hosting model (design).** Waits on Q1.
- **Child 4 — implementation children.** Wait on children 1–3 and on Q2: "**Settlement:** confirm
  "the usual way" now means the crypto rail (10.b), and which asset."

### #114 Ledger storage tiers
- **Child 6 — archive segments to the blob surface.** Waits on Q4: "**Where does the archive live by
  default:** the blob surface (Garage, 8.b), the forge (per the comment), or both?"
- **Child 8 — the archival node role (design).** Waits on Q4 and Q2: "**"Sharding"**: is
  declarative partitioning inside one PostgreSQL enough, or is multi-node sharding (several
  database servers) in scope?"
- (Q1 — "stored encrypted on github / forgejo so the search engine can work" — bears on child 6's
  destination and on 7.a; no specced lane encrypts anything.)

### #121 Loops as services
- **Child 4 — kustomize (design).** Waits on Q2: "**Kustomize:** the original named "helm charts,
  kustomize, etc". Helm is in place. Do you still want kustomize overlays, and for what
  (per-environment patches)?"

### #136 Forge-state ledger
- **Child 8 — S5: restore into Forgejo (design).** Waits on Q2: "**Is the sovereign Forgejo meant to
  hold a live mirror of a declared GitHub relay** (8.b)? If so, S5 becomes continuous replay rather
  than a one-time migration." (Also #138 Q3, relay semantics.)

### #139 Moltbook — every child
- **Children 1–6** (placement ADR, social-relay port, Moltbook client, post on release, grounded
  reply loop, thread ledger events). Wait on Q1: "**Placement:** a workspace tenant
  (`src/vibey_tools/moltbook`) or an adapter inside the conductor?", Q2: "**Event source:** vibey-gh
  release events (any adopter repository) or conductor DONE events (projects vibey delivers)? Or
  both?", Q3: "**Is Moltbook still the platform you want**, given runbook 11's warning about API
  churn? Should Matrix rooms (8.b's default) come first, with Moltbook as a declared relay after?"
  and Q4: "Should this fold into #85's "vibey-social", or stay separate?"
- **Child 7** is an operator action (registration and the claim step).

### #143 Human user interfaces
- **Child 5 — clients toolchain and CI lanes (design).** Waits on Q4: "**Stack confirmation:**
  Next.js (named in the ask), React Native/Expo and Tauri (runbook 08), or others?"
- **Children 6, 7 — web projects/pipeline view and web gate answering.** Wait on Q4.
- **Child 8 — self-hosted push (design).** Waits on Q2: "**iOS** requires Apple developer accounts
  and store review, a paid counterparty with no sovereign alternative for general distribution.
  Accept it as a declared exception, or leave iOS out?", Q3: "**Android distribution:** F-Droid
  first (8.a), with the Play Store declared?" and Q4.
- **Child 9 — mobile gate answering.** Waits on Q2, Q3, Q4.
- **Child 10 — desktop Tauri shell.** Waits on Q4.
- (Q1 — single operator or many users — is not a blocker: the specced API is single-operator,
  loopback and token-bound, per runbook 12; multi-user belongs to #89.)

### #145 Full forge capture and `@vibey`
- **Child 3 — install `conversation.yml` here.** Waits on child 2 (an operator action: the `vibey`
  identity) and Q2: "**Is `@vibey` autocomplete on GitHub worth a GitHub App registration** (an
  operator action and a declared paid relay)? On Forgejo a plain user account gives autocomplete."
- **Child 9 — security alerts capture.** Waits on Q4: "**Security alerts** contain sensitive data.
  Should they be captured into the public ledger shard (7.a), a private tier, or excluded?"
- **Scope item 5 — "agents".** Waits on Q1: "**What is "agents"?** GitHub's Copilot agent sessions (a
  paid, GitHub-only surface)? The repository's own `.claude/agents` definitions? Or vibey's own
  agents acting on the forge?"
- (Q3 — a sovereign equivalent for Discussions — is recorded, unanswered, by
  `roadmap-145-design-graphql-reads`.)

### #148 Spending, saving and investing — every child
The rewrite states "Everything downstream depends on that answer" (custody).
- **Child 1 — ADR + sub-doctrine: custody and the approval invariant.** Waits on Q1: "**Custody:**
  vibey never holds a spending key (operator signs every transaction on a hardware wallet), or a
  capped hot key held in OpenBao? The rewrite assumes the former." and Q5: "**Approvers:** only you,
  or a named quorum?"
- **Children 2–5 — `TransactionProposal`/`Approval` types, proposal and approval tables, the
  `transaction_approval` gate kind, the ledger event kinds.** Wait on Q1 and Q5.
- **Child 6 — the Bitcoin reference rail (design).** Waits on Q1 and Q2: "**Chains under 10.b:** 10.b
  speaks of "the most secure, most censorship-resistant, most sanction-proof monetary system in
  existence" in the singular. Does it permit BTC, ETH and XMR together, or one designated system at a
  time (like 8.d's designated model)?"
- **Child 7 — Monero and Ethereum rails (design).** Waits on Q2.
- **Scope 5 — save / invest.** Waits on Q3: "**What do "save" and "invest" mean?** Holding in a cold
  wallet, DEX swaps, or yield? Each needs its own risk statement."
- **Scope 7 — legal floor.** Waits on Q6: "**Legal and tax:** which jurisdiction's rules apply, and
  who records compliance before a rail goes live (SD-01 §5)?"
- PayPal: excluded by law (§2), not a question.

### #155 One book, one paper
- **Children 1–4 — the fate of each tenant paper; fold the vibey-gh paper; fold or retire the runner,
  skills and bootstrap papers.** Wait on Q1: "**Tenant papers:** fold them into the family paper as
  appendices, delete them, or keep them as non-published design notes?"
- **Child 5, removal half — delete tenant `properdocs.yml` files.** Waits on Q1. (The publishing guard
  is specced: `roadmap-155-single-source-guard`.)
- (Q2 "single per channel or across `main` and `develop`" and Q3 "close #155 into #301" bind no lane.)

### #165 vibeyos
- **Child 4 — ADR: vibeyos scope (rung 1).** Waits on Q1: "**What makes an OS "AI-first"?** For
  example: the default model preloaded and sized to the hardware, the sovereign stack running at first
  boot, vibey as a system service, an agent shell? Which of these is the point?", Q2: "**Desktop,
  server or both?** Which hardware (the M5 laptop class of 8.d, or x86_64 workstations and
  servers)?", Q3: "**In this repository or a new one?** ADR-0021 made the family one tree.", Q4:
  "**Licence and name:** redistributing Arch packages brings their licences, and Arch Linux's
  trademark policy applies to a derivative's name. Should the name and posture be checked first?"
  and Q5: "**Is rung 0 (first-class on Arch) enough for now**, with vibeyos itself later?"
- **Children 5, 6 — archiso profile and signed repository; image build, hosting and QEMU boot test.**
  Wait on child 4 (Q1–Q5).

### #226 vibey-wiki — every child
- **Child 1 — ADR: corpus format and licensing.** Waits on Q1: "**Grokipedia:** its licence,
  bulk-download availability and terms of use are unknown to this audit. Is it a must, and if its
  terms forbid mirroring, should it be dropped (SD-01 §5)?", Q2: "**"Always up to date":** is
  refreshing from each published dump enough, or do you mean near-live edits?" and Q3: "**Languages
  and media:** English only, or several? Text only, or images too? Size changes by orders of
  magnitude."
- **Child 2 — source catalogue and verified dump downloader.** Waits on child 1 and Q4: "**Where it
  runs:** on every developer machine, or once in the cluster as a shared surface?"
- **Children 3–6 — extractor, index/packets, shadow-mode consumption, scheduled refresh.** Wait on
  children 1–2 and Q5: "**Which phases use it:** DESIGN research only, or BUILD too?"

### #297 OpenClaw
- **Engine reading.** Waits on Q1: "**Surface or engine?** Is "support for openclaw" the front door
  described above? Or do you also want OpenClaw to run as an engine inside `sovereignloop` (8.c)?
  The canon's engine list (8.b) does not name it." (The front-door skill is specced:
  `roadmap-297-openclaw-skill`.)
- **Child 3 — ClawHub publishing (design).** Waits on Q4: "**Is ClawHub publication wanted**, given
  it is a registry run by a third party (10.a)?"
- (Q2 "vibey only, or every runner" — the specced skill covers `vibey` only; Q3's channel default is
  settled by 8.b: Matrix.)

### #298 Bitbucket — every child
- **Children 1–4, 6 — transport, read verbs, write verbs, `kind = "bitbucket"` accepted,
  forge-snapshot reader.** Wait on Q1: "**Bitbucket Cloud, Bitbucket Data Center (self-managed), or
  both?** Data Center runs on the operator's hardware but is proprietary and licensed. Under 8.a/8.b
  it is still a counterparty. Which does "support" mean?" — the two expose different REST APIs,
  pagination and auth, so no transport can be specified without the answer. Also Q2 (relay
  semantics), Q3 (releases: tags + Downloads, or `NotSupported`) and Q5 (Jira pairing).
- **Child 5 — Bitbucket Pipelines equivalents (design).** Waits on Q1 and Q4: "**CI parity:** is
  running vibey-gh's gates as Bitbucket Pipelines in scope (child 5), or is the adapter enough?"

### #301 Paper revision
- **Child 1 — track the reviewer feedback.** An operator action; Q1: "**Where is the reviewer
  feedback?** Please attach or commit it." Everything the reviewer asked for waits on it.
- **Child 3 — the formal model (design).** Waits on Q3: "**Formal methods budget:** machine-check the
  queue and handoff properties, or narrow the claims?"
- **Child 9 — baselines (design).** Waits on Q1 (which baselines the reviewer named).
- **Child 11 — handoff R1–R10 on messy briefs, with an ablation.** Waits on Q1.
- **Child 12 — reconcile the commodity-production thesis.** Waits on Q1 and Q4 (paper cutoff), and is
  paper text (docs wave).

---

## 2. Excluded or constrained by ratified law
- **#148 PayPal** — excluded by 10.b ("No fiat processors, ever",
  `src/vibey_tools/gh/docs/doctrines.md:390-393`). Every other #148 child is blocked above.
- **#85 postal outreach** — SD-01 §1 forbids gathering or relaying private details such as home
  addresses. The only lawful form (addresses a person published for that purpose, reached through
  official channels) still waits on #85 Q2.
- **#85 `vibey-opencode` row** — repealed by 8.b (`doctrines.md:128-135`); retirement is ADR-0046
  L38/L39 (`loops-*`), not a roadmap spec.
- **#87 fiat-paying bounties as paid work** — 10.b; how they are treated is #87 Q1 (above).
- **#121 "elastic" replicas** — 8.c allows one instance per model; ADR-0046 §11 gives the chart no
  `replicas` value at all, so #121 child 3 ("refuse replicas > 1") has nothing to refuse (see §4).

## 3. Waiting on a design spike or evidence (no operator question)
- **#85 child 4 — GCP relay adapter**: follows `gap-spike-aws-iac` (and `gap-spike-relay`), whose
  AWS mapping it copies.
- **#87 — the policy reader** (CONTRIBUTING / AI-policy text → `PolicyVerdict`): natural-language
  judgement on sovereignloop's queue (8.c); after the loop client (`loops-*`) and
  `roadmap-87-scoring-skiplist-p2`.
- **#87 child 7 — proposals park as human gates**: waits on `roadmap-87-design-proposal-gates`.
- **#114 child 4 — the rotation job**: waits on `roadmap-114-design-rotation`.
- **#114 child 7 — `vibey ledger tiers|archive|restore|verify`**: waits on the two #114 spikes and on
  child 6 (blocked on #114 Q4).
- **#114 child 9 — the benchmark script and table**: waits on `roadmap-114-design-codec-chunking`;
  the table itself is docs wave.
- **#134 — the φ fit and gradient**: waits on `roadmap-134-design-phi-gradient`.
- **#136 child 7 — point-in-time reconstruction, `vibey ledger forge-state --as-of`**: waits on
  `roadmap-136-design-forge-ledger`.
- **#138 — Forgejo Actions templates**: the implementation is the gaps.md §L8 lane; its design input
  is `roadmap-138-design-forge-workflow-templates`.
- **#145 — discussions, Projects v2 and wiki capture**: wait on `roadmap-145-design-graphql-reads` and
  `roadmap-145-design-wiki-capture`.
- **#145 child 10 — Forgejo capture parity**: after the snapshot reads through the adapter (gaps.md §L8).
- **#290 children 2–4 — the extension's status view, gate answering and publishing**: wait on
  `roadmap-290-design-extension-toolchain`.
- **#297 child 2 — the `[openclaw]` table**: waits on #143's API (`roadmap-143-api-*`) and on
  verifying that OpenClaw can use a Matrix channel.
- **#301 child 5 — capacity-outranks-completion false negatives**: no tracked source holds capacity
  rejections beside completion claims. `scripts/paper_evidence.py` reads only the stress record, the
  qwenloop storm JSON and git history (`scripts/paper_evidence.py:3-8`, `:39-40`), and the storm JSON's
  runs carry dispositions but no capacity signal. It needs a tracked ledger extract with
  `CapacityRejected` events first (operator-run evidence).
- **#301 child 6, simulator** and **child 7, anchoring lanes**: wait on `roadmap-301-design-fairness`
  and `roadmap-301-design-tamper-evidence`.

## 4. Covered elsewhere, or not a lane
- **#85 child 3 — AWS relay (design)**: `gap-spike-aws-iac` (with `gap-aws-secrets`,
  `gap-deploy-target-paid`); relay semantics `gap-spike-relay`.
- **#85 child 6, #301 children 2 and 4, #138 child 5** — docs wave (gaps.md §M2, §M5, §M6); the spec
  template forbids `docs/` edits.
- **#121 children 2, 3** — the loop-service re-cut and the one-instance chart are ADR-0046's lanes
  (`loops-*`; L37 renders `replicas` fixed at 1 with no value). **Child 1** (accept ADR-0046) is an
  operator action.
- **#133 child 1** — `gap-gh-review-via-sovereignloop-1`, `-2` (gaps.md §A5). **Child 2** — operator
  action; `gap-ops-review-lane` and `gap-chain-dispatch` (gaps.md §L1, §L2).
- **#136 child 5 and #138 child 6** — the snapshot and forecast reading through the adapter: gaps.md
  §L8.
- **#138 child 1, root half** — done: `03e59eb4` (`fix(gh): declare this repository's forge as
  github`), merged into `storm/integration` as `d3b4a388`. The tenant half is
  `roadmap-138-tenant-forge-declared`. **Child 7** (a real Forgejo instance) — operator action, on
  `chart-operator-forgejo-p2` (#327).
- **#145 child 2** — operator action (register the `vibey` identity).
- **#165 child 1** — the `installer-*` specs (`installer-queue.txt`). **Child 2** — `gap-ci-arch-gates`,
  `gap-ci-installer-smoke`. **Child 3** — gaps.md §G3/§G4 (packaging); the AUR account is an operator
  action.
- **#290 child 5** — `loops-vscode-spike` (V-VS1–V-VS5; gaps.md §B1). **Children 6, 7** —
  `loops-vscodeloop-*` / ADR-0046 L20, L38, L39. **Child 8** — `installer-vscode`.
- **#297 child 4, #139 child 7** — operator actions (live proof; registration).
- **#301 child 8** — operator-run evidence; the reproducible model benchmark is `gap-models-bench-1`,
  `-2` (gaps.md §D3).
