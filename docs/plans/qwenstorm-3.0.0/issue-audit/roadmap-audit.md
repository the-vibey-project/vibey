# Roadmap audit: the 23 open non-`qwenstorm` issues

**Scope:** open issues in `the-vibey-project/vibey` not labelled `qwenstorm`: 301 298 297 290 226
165 155 148 145 143 139 138 136 134 133 121 114 90 89 88 87 86 85. Each was read in full, with
its comments.

**Evidence cutoff:**
- GitHub read on 2026-09-22 (raw JSON in `issue-audit/raw/`).
- Code and canon read at the integration tree `cce648ef` (develop + QwenStorm 3.0.0 work,
  with #392 ratified).
- Storm drafts in `specs/` were read as *specifications*, not code.

**Read-only:** nothing on GitHub was edited, commented on or closed. Proposed replacement
bodies are in `issue-audit/updates/<N>.md`. The first line of each gives the status, and the
operator's original body is quoted verbatim at the end (plus scope-bearing operator comments
on #155, #114, #87 and #139).

## Counts

| Status | Count | Issues |
|---|---|---|
| CURRENT | 0 | — |
| STALE | 12 | 290, 155, 148, 145, 139, 138, 121, 90, 89, 88, 86, 85 |
| THIN | 3 | 298, 297, 226 |
| EPIC | 7 | 301, 165, 143, 136, 134, 114, 87 |
| SUPERSEDED / DUPLICATE | 0 | #121 is partly superseded (ADR-0044 + the #348–#381 lanes + draft ADR-0046); kept as STALE because it is the operator's "tell me when it works" tracker |
| DONE | 1 | 133 (in code, with acceptance tests; live evidence blocked by operations) |

Most STALE and EPIC issues are also too big: each update proposes child issues sized for a
20B lane, or marked "design needed first".

## Table

| Issue | Title | Status | Reason | Update file |
|---|---|---|---|---|
| 301 | Paper revision: formalize, broaden, and adversarially validate… | EPIC | Ten workstreams in one issue. Labelled `bug`. The reviewer feedback it cites is not attached or tracked anywhere. The paper's substrate is changing under it (ADR-0044, 8.c, 8.d, OpenCode repeal) | updates/301.md |
| 298 | bitbucket | THIN | One-line seed. `ForgeKind.BITBUCKET` exists and is refused at load until an adapter exists (`vibey_gh/config.py:258-263`). Declared-only under 8.b | updates/298.md |
| 297 | openclaw | THIN | One-line seed. Intent recovered from runbook 11 and the fleet runbook's seventh surface (OpenClaw drives vibey). Engine reading unknown | updates/297.md |
| 290 | vscode plugin | STALE | Seed from 09-18. On 09-22, 8.b made VS Code an engine of both loops (replacing OpenCode) and the paid default IDE. Split into an extension (this issue) and the engine (draft ADR-0046 §8, V-VS1–5) | updates/290.md |
| 226 | wikipedia / grokipedia | THIN | Seed. Nothing built. Needs corpus format, licence (Grokipedia terms unknown) and storage design. Should reuse vibey-skills' packet contract (ADR-0031, 10.e) | updates/226.md |
| 165 | vibeyos | EPIC | Whole OS, one line of intent. 8.h (Arch = default sovereign OS) gives rung 0, which is unmet: the installer has no pacman (`postgres.py:248-253`) and there is no Arch CI. The storm installer draft covers most of rung 0 | updates/165.md |
| 155 | consolidate book and paper | STALE | The published paper is one family paper (`93fe3dcb`, 1,469 lines, carries the governance-scarcity claim). 8 tenant `paper.md` and 8 `properdocs.yml` remain. Comprehensiveness overlaps #301 | updates/155.md |
| 148 | allow spending | STALE | PayPal violates 10.b ("No fiat processors, ever"). Nothing built. Custody decision first. The arc matches SD-01 §6 | updates/148.md |
| 145 | fully github capture | STALE | GitHub-only framing vs 8.b (Forgejo default). `@vibey` rename still undone (`config.py:756,1809`). Capture now has a home (forge-snapshot, 33 named exclusions) | updates/145.md |
| 143 | human user interfaces | EPIC | Five clients over an HTTP API that does not exist (runbooks 08/12/07). 8.h and 8.b shape targets (Arch+macOS, self-hosted push, F-Droid/AUR) | updates/143.md |
| 139 | Moltbook integration… | STALE | The committed "sibling repo" design was invalidated by ADR-0021/0037. Runbook 11 has a competing in-core design. 8.b: declared relay, Matrix default. 8.c: replies via sovereignloop | updates/139.md |
| 138 | Platform abstraction… GitLab first-class, Forgejo mandatory… | STALE | 8.b reverses the ordering (Forgejo default, GitHub the paid default, GitLab declared). Adapters landed, but only `tidy` uses them. This repository declares no `[platform]`, so `tidy` resolves to `forgejo.local`. Children #327, #332–#344 | updates/138.md |
| 136 | The forge-state ledger… | EPIC | S1 landed (`d49bef6a`: GitHub-only, 9 classes, files). S2–S5 remain. Cross-refs are vibey-gh-era. The 8.b relay makes the Forgejo round trip central | updates/136.md |
| 134 | The autonomous billing and feasibility engine… | EPIC | Evaluator + `vibey-gh estimate` landed (`4396ea24`), but 2/18 coordinates are measured, cost is unknown, φ and the gradient are unspecified, and `docs/estimate.md` says "0/18". 8.g and 10.d now bind it | updates/134.md |
| 133 | 8.a: make the sovereign lane primary for the half of review… | DONE | `4624a4be`/`d0def61e`, `pr-review.yml:237-262,373-385`, `review_composition.py`, acceptance tests in `test_sovereign_first.py`. Close after one live run, which is blocked (gaps.md §L1–L3) | updates/133.md |
| 121 | wrap *loop repos into a single vibey-loops repo… | STALE | Repo half done differently (ADR-0021/0037). "Elastic" is reshaped by 8.c (one instance per model). The cluster half is ADR-0044 + #348–#381, but ADR-0044 predates 8.c's two loops (draft ADR-0046 amends it) | updates/121.md |
| 114 | Ledger storage tiers… | EPIC | Partition migration 0013 (default partition only), a `TierConfig` whose defaults contradict the issue, and an in-memory tier manager, all unwired. No rotation, archive, node, CLI or benchmarks. The "encrypted on forge" comment conflicts with 7.a | updates/114.md |
| 90 | Marketplace… | STALE | "Paid work pays the usual way" predates 10.b. Web and mobile overlap #143. The design doc (its own first deliverable) is unwritten | updates/90.md |
| 89 | Platform identity and operations… | STALE | Predates 10.b, 12.c (config boards must open PRs) and 8.b (sovereign IdP/SIEM). Roles and audit (stated first) are unstarted. Correlation is still leaking at `cli/main.py:168` | updates/89.md |
| 88 | Delivery economics… | STALE | "Card fails" and invoicing assume fiat (10.b). Forecasting half partly exists in vibey-gh (no data: "billing ledger unavailable") | updates/88.md |
| 87 | Work discovery and ideation… | EPIC | Two halves, neither started. Runbook 21 specifies scoring and ethics. 10.b excludes fiat-paying bounties. Intake has no provenance field | updates/87.md |
| 86 | Monetization… | STALE | Predates 10.b. ADR-0037 (one distribution) breaks "absence, not a disabled flag". Cross-refs are vibey-gh-era | updates/86.md |
| 85 | Ecosystem expansion: vibey-jira… vibey-opencode… | STALE | Sibling repos retired. vibey-opencode shipped (#314) and was then repealed by 8.b. Jira/AWS/GCP are now declared relays over Plane/OpenStack ports | updates/85.md |

## Issues whose intent is unclear (ask the operator)

- **#297 openclaw:** is OpenClaw a *front door* that drives vibey (runbook 11's AgentSkill,
  the fleet runbook's seventh surface)? Or also an *engine* inside sovereignloop? 8.b's
  engine list does not name it.
- **#290 vscode plugin:** a VS Code *extension* for humans, VS Code as an *engine* (now
  canon), or both? The rewrite assumes both, split in two.
- **#226 wikipedia / grokipedia:** is Grokipedia a must, given its licence and bulk-download
  terms are unverified? What does "always up to date" mean (per dump or near-live)?
  Languages and media?
- **#165 vibeyos:** what makes an OS "AI-first" as testable properties? Desktop or server?
  In this repository or not? Is rung 0 (first-class on Arch) enough for now?
- **#298 bitbucket:** Bitbucket Cloud, Data Center, or both? What does "relay through the
  sovereign host" mean for a Bitbucket-hosted repository?
- **#145 "agents":** GitHub's Copilot agent sessions, the repository's own agent
  definitions, or vibey's agents acting on the forge?
- **#148:** custody (hardware-wallet signing only?), whether 10.b permits several chains or
  one designated system, and what "save" and "invest" mean.
- **#85 vibey-career and postal outreach:** undefined scope. Postal outreach collides with
  SD-01 §1 (no private addresses).
- **#114 comment:** "stored encrypted on github / forgejo so the search engine can work"
  pulls against 7.a (no gated truth). What is to be encrypted?
- **#301:** where is the reviewer feedback it cites?

## Overlaps between these issues

- **Forge cluster.**
  - #138 (the protocol and adapters) is the parent of #298 (Bitbucket adapter), #145
    (capture and `@vibey` interaction) and #136 (snapshot → ledger → replay).
  - #145's capture list and #136's S3 slice name the same classes. Keep the capture work in
    #136 and leave #145 the interaction.
  - QwenStorm #327 and #332–#344 are #138's children. Their own spec leaves `forge-snapshot`,
    `forecast` and the workflow templates GitHub-only, so the follow-ups are listed in
    #136/#138.
- **Ledger cluster.** #114 (tiers) blocks #136 S4. #134, 7.c and #145 all add ledger volume.
  #137 (closed) is the explorer that must become tier-aware.
- **Commercial cluster (all constrained by 10.b).** The dependency chain is #86 (FOSS
  classification, billing boundary) → #88 (milestones, payment gate) → #89 (roles, audit,
  identity, payment history) → #90 (marketplace, built last). #148 supplies the one crypto
  rail and the human-approval invariant they should all share. #87 feeds #90 and shares
  #86's FOSS classification.
- **Estimation.** #134 (cost accounting and feasibility) and #88 (milestone forecasting)
  share vibey-gh's `GradedEstimator` and the missing billing-ledger export. Do that export
  once.
- **Human surfaces.** #143 (web, mobile, desktop), #290 (VS Code extension), #297 (OpenClaw)
  and #89/#90 (boards, dashboards, marketplace UI) all need runbook 12's `vibey server` API.
  Build it once, first.
- **Interaction and social.** #85 (vibey-social, word-of-mouth; the "interactive, never
  broadcast" principle), #139 (Moltbook), #297 (OpenClaw channels) and #145 (`@vibey` on
  forges) should share one interaction contract extracted from `vibey_gh/conversation.py`.
- **Engines and loops.** #121 (loop services, 8.c), #290 (VS Code engine, draft ADR-0046 §8)
  and #85 (the OpenCode row) are one change set under draft ADR-0046. #133's sovereign
  review should submit to sovereignloop's queue once it exists.
- **Paper and book.** #155 (single source) and #301 (revision) overlap on "fully
  comprehensive, entire dev cycle, commodity thesis". Proposed: #155 keeps source
  consolidation, and #301 takes the rest.
- **Operating system.** #165 rung 0 overlaps 8.h, the storm installer draft
  (`specs/ADR-installer.md`) and #143's Arch-first desktop packaging.

## Cross-cutting findings

1. **The 2026-09-22 canon amendment (#392) has not reached the documents that brief agents
   and adopters.**
   - `CLAUDE.md:5,110,142-143` and `AGENTS.md:90-104` still name OpenCode as a current
     engine. AGENTS.md also has Bitwarden rather than OpenBao for secrets.
   - ADR-0044 §13/§15 still has one service per engine with opencode on by default.
   - The chart CRD enum still lists `opencode`.
   - Runbooks 01 (Jira), 03 (AWS/GCP) and 14, and the master plan's status lines (dated
     2026-09-15), predate 8.b's sovereign defaults.
2. **10.b (ratified 2026-08-29) postdates the whole commercial cluster** (#86, #88, #89, #90,
   filed 08-27) and conflicts with #148's PayPal. No update keeps a fiat path.
3. **False completion claims on the record (10.f).** On 2026-09-19 between 02:36 and 02:38,
   automated "Critical Audit Status: SOLVED" comments were posted on #155, #148, #145, #143,
   #114, #89, #88 and #87. The 17:22 audits the same day and the code contradict them (for
   example #148 has no spending code at all). The SOLVED comment on #133 roughly matches the
   code, but not the live evidence. "DOUBTFUL" and "UNSOLVED" comments on the others carry
   no evidence either way. The operator may want to hide these or answer them, which this
   audit could not do (read-only).
4. **This repository declares no forge.** Neither `.vibey-gh.toml` has `[platform]`. The
   default is now `forgejo` (vibey-gh ADR 0002, `config.py:288`), so `vibey-gh tidy` here
   resolves to `forgejo.local`. The fixing commit `b60dad4c` is on no branch. Land it
   before #339–#344.
5. **8.h is unmet at the installer:** no pacman path (`src/vibey/infrastructure/postgres.py`),
   no Arch CI job, and no AUR package of vibey.
6. **Stale cross-references** to vibey-gh-era numbers: #243, #247, #259 (in #136);
   #261/#263/#264 (in #134); vibey-gh#139 (in #85 and #90); vibey-gh#134/#135 (in #86);
   vibey#101 (in #139's comments).
7. **Label:** #301 is labelled `bug`; it is a documentation/research epic.
8. **Companion audit:** `issue-audit/gaps.md` (written in parallel) lists gaps with no
   issue yet. Several bear directly on these issues:
   - §L1–L3 (no review lane can pass, the chain trigger broke after #317, runners are not
     declared) block #133's closing evidence.
   - §A5 matches #133's 8.c follow-up.
   - §F1–F5 matches #165 rung 0.
   - §B1–B3 matches #290.
   - §C1/C4 matches #85.
   - §D1–D3 matches #134.
   - §E1–E6 matches #114/#136.
   - §L4 matches #138.

## Suggested order

1. Operational unblockers:
   - declare this repository's forge (`b60dad4c`)
   - restore a review lane (gaps.md §L2)
   - propagate #392 to CLAUDE.md, AGENTS.md, ADR-0044 and the runbooks
2. Close #133 on one live run.
3. Re-cut #121's loop-service lanes to draft ADR-0046, and land the installer lanes (#165
   rung 0).
4. Forge: #138's remaining children, then #136 S2/S3 (absorbing #145's capture), then
   #145's `@vibey` rename.
5. `vibey server` (#143 children 1–4). It unblocks #290's extension, #297, #89 and #90.
6. Design-first items that need operator answers:
   - #148 custody, and the #86 billing boundary
   - #226 licensing
   - #165 rung 1
   - #301 reviewer feedback
