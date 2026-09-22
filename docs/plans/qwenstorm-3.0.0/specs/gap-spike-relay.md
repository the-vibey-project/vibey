## Title
docs(adr): decide how a declared paid platform relays through its sovereign host (spike for gaps C3 and C4)

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:179-186`): a declared paid counterparty
"relays through the sovereign host rather than replacing it: the sovereign host stays the source
of truth, and the declared paid platform speaks through a relay adapter on the same protocol,
feeding the sovereign host rather than substituting for it". ADR-0042 records the same
(`docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:29-33`,
`:84-89`, `:110-112`). No code does it (gap C3):
- each surface gets exactly one adapter: `ForgeSelector.select` returns one forge
  (`src/vibey_tools/gh/vibey_gh/forge_selector.py:61-65`), `build_app` one adapter per surface
  (`src/vibey/bootstrap.py:751-914`), and the config comment says a paid endpoint is declared by
  pointing the surface's own `url` at it (`src/vibey/domain/config.py:194-197`) — which replaces
  the sovereign host rather than relaying through it;
- `deploy.target` is parsed (`src/vibey/domain/config.py:453-459`) and read by nothing; the
  cloud client is the injected one or the in-memory one (`src/vibey/bootstrap.py:371`);
- `grep -ri relay src/vibey` finds only docstrings (`application/interfaces/email.py:9`,
  `messaging.py:9`, `infrastructure/email/forward_email.py:4`, `domain/config.py:197`);
- this repository declares `[platform] kind = "github"` (`.vibey-gh.toml:18-19`), with no
  sovereign forge host behind it.

Gap C4: none of 8.b's declared-only platforms (`doctrines.md:128-166`) has an adapter to declare
except GitHub, GitLab (`vibey_gh/forge_github.py`, `forge_gitlab.py`) and Azure
(`src/vibey/infrastructure/azure/`); `src/vibey/infrastructure/{tracker,docs,secrets,files,email,sms,messaging}/`
hold only the sovereign adapter and `in_memory.py`. Jira, AWS and GCP relay adapters are already
proposed as children 2–4 of the rewritten #85 (`issue-audit/updates/85.md`, *Proposed child
issues*); AWS as the default paid cloud belongs to the `gap-aws-*` lanes.

8.b's text fixes the invariant (the sovereign host is always the source of truth, the relay is
declared by a human in the repository, and it speaks the same vibey protocol) but not the
vocabulary: it names no directions, no declaration keys and no conflict rule. So
`gap-relay-vocabulary` is not written yet; this spike decides it.

**Implementer: a large model or the operator (design, not code); the storm runner skips
gap-spike-\*.** The deliverable is the draft ADR
`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-gap-relay.md`, in the shape of
`specs/ADR-two-loops.md`. Evidence comes from the integration clone at `d3b4a388` or later
(stated), never from `/Users/adam/git/vibey`.

## Required behaviour
The ADR must decide:
1. **The vocabulary** (pure domain, `gap-relay-vocabulary`): a relay declaration names the
   surface, the sovereign host (the source of truth, always), the paid platform, and the
   direction or directions — for example a one-way mirror (sovereign → paid), an ingest
   (paid → sovereign, entering as records or proposals the sovereign host accepts), or both,
   with the sovereign host winning every conflict. State the invariants as code will test them:
   no declaration can make the paid side primary; deleting a declaration loses nothing (Bill of
   Rights V, 10.a at `doctrines.md:385`).
2. **The declaration** (12.c, `doctrines.md:455`): the keys and environment overrides in
   `vibey.toml` (per surface) and in `.vibey-gh.toml` for the forge, how an unnamed `paid`
   resolves through `gap-paid-defaults` (AWS for cloud, GitHub for forge), and how a relay
   declaration differs from today's `[<surface>] url` pointed at a paid host (which the ADR
   must forbid or migrate).
3. **Relays and 8.f** (`doctrines.md:294-314`; `specs/ADR-surface-lanes.md` §1–§9): a relay
   reads and writes the sovereign host only through that surface's lane, and holds the paid
   platform's credentials itself (from OpenBao). Its idempotency, dead letters, backlog
   visibility and measurement (8.g, `:316-324`); a paid platform that is down never blocks the
   sovereign host (doctrine 10, `:366-369`); relay events in the ledger (7.c, `:82-91`), with
   people's details redacted (SD-01 §1).
4. **Per surface**, the mechanism, the port verbs it needs, and its feasibility:
   - **forge**: Forgejo primary; GitHub by push mirror and a change-request relay. The forge
     protocol has no mirror verb and no create-change-request verb
     (`src/vibey_tools/gh/vibey_gh/interfaces/forge_adapter_interface.py:37-123`). Relate it to
     #136's snapshot and replay (S5; its open question 2, "continuous replay rather than a
     one-time migration") and #138's open question 3 (`issue-audit/updates/136.md`, `138.md`);
     exact-head semantics across the relay; the chart's forge is Gitea today
     (`deploy/helm/vibey/values.yaml:521`; ADR-0043 `0043-sovereign-surfaces-install.md:24`) until
     `chart-operator-forgejo-p2` lands.
   - **tracker**: Plane ↔ Jira, Linear, Asana. `IssueTrackerPort` has only `create_ticket` and
     `get_ticket_status` (`src/vibey/application/interfaces/tracker.py:10-16`); decide the verbs
     a sync needs, the id map and where it persists (`orm-*` seams), polling or webhooks.
   - **docs**: BookStack → Confluence, Notion, GitBook, publish-only; page-id map; `DocsPort`
     (`application/interfaces/docs.py:10-16`).
   - **cloud**: what "OpenStack holds the deploy state of record" means — the file-backed
     deployment state (`src/vibey/infrastructure/deploy/state_repository.py:31`), the ledger's
     DEPLOY events, or OpenStack itself — and how an AWS or GCP deployment is recorded there;
     `CloudClientPort` (`src/vibey/application/interfaces/azure.py:45-70`); the OpenStack client
     lanes `openstack-client-p1`, `openstack-client-p2`.
   - **secrets** (1Password, LastPass, Proton Pass), **files** (Google Drive, iCloud), **email**
     (Gmail, Proton Mail; is Apple Mail a platform or a client?), **SMS** (Google Messages,
     iMessage: is any API available at all?), **messaging** (Signal, Slack, Discord, Zoom,
     WhatsApp, Telegram, Messenger, Instagram, TikTok — for example FOSS Matrix bridges hosted
     beside Synapse, which relay through the sovereign host by construction). Where a platform
     cannot be relayed, the ADR says so plainly and names the evidence (10.f, `:419`).
5. **Interaction**: emitting relays inherit #85's interaction contract (its child 1: opt-in,
   labelled machine speech, per-thread budget), never broadcast-only.
6. **This repository's own sovereign forge host**: whether `the-vibey-project/vibey` moves its
   source of truth to a self-hosted Forgejo with GitHub as its relay, and what `kind = "github"`
   means until then. This is an operator ruling: list it for `gap-ops-canon-rulings`, and do
   not decide it in the ADR.

## Where to change
Nothing in the repository. Write only
`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-gap-relay.md`.

Required ADR sections, in order: the header line (**Status:** proposed · **Date** ·
**Cites:** 8.b, 8.f, 8.g, 7.c, 10.a, 10.e, 10.f, 12.c, SD-01 · **Related:** ADR-0042, ADR-0043,
ADR-0047, vibey-gh ADR 0001 and 0002, #85, #136, #138 · **Evidence:** the commit read) and an
**Owes:** line; `## Context`; `## Decision` (1 vocabulary, 2 declaration, 3 relays and lanes,
4 one subsection per surface, 5 interaction); `## Child lanes`; `## How each non-negotiable
still holds`; `## Security impact` (paid credentials, what data leaves the sovereign host, what
comes back in as untrusted text, SD-01 §4); `## Migration`; `## Consequences`;
`## Alternatives rejected` (at least: the paid platform as primary with the sovereign host as a
backup; a relay that bypasses the lane); `## Verification owed at implementation`.

Child lanes the ADR must name, each sized for one source file plus its interface and one test
file (split `-1`, `-2` where needed), with dependencies:
- `gap-relay-vocabulary` (domain), `gap-relay-config` (declaration and environment, after
  `gap-paid-defaults`), `gap-relay-gh-platform` (vibey-gh's `[platform]` relay form);
- forge: `gap-relay-forge-mirror`, `gap-relay-forge-change-requests` (after the `forge-*`
  wave, `forge-0g`, and #136's S5 design);
- tracker: `gap-relay-tracker-port`, `gap-relay-tracker-sync`, Jira (re-cut #85 child 2 onto
  the vocabulary rather than duplicate it), `gap-relay-adapter-linear`, `gap-relay-adapter-asana`;
- docs: `gap-relay-docs-publish`, `gap-relay-adapter-confluence`, `gap-relay-adapter-notion`,
  `gap-relay-adapter-gitbook`;
- cloud: `gap-relay-cloud-record` (after `openstack-client-p2`), AWS (#85 child 3 and the
  `gap-aws-*` lanes), GCP (#85 child 4);
- `gap-relay-adapter-1password`, `gap-relay-adapter-lastpass`, `gap-relay-adapter-protonpass`;
  `gap-relay-adapter-gdrive`, `gap-relay-adapter-icloud`; `gap-relay-email-smarthost` (Gmail,
  Proton Mail); `gap-relay-sms` (or a recorded infeasibility); `gap-relay-messaging-bridges`
  (one lane per bridge, or a recorded infeasibility per platform);
- the operator ruling in behaviour 6, as an item of `gap-ops-canon-rulings`.

## Acceptance criteria
- [ ] The ADR file exists and has every required section.
- [ ] The vocabulary is stated precisely enough that `gap-relay-vocabulary` can be specified
      with exact names, fields and invariants from it alone.
- [ ] Every 8.b declared-only platform (`doctrines.md:128-166`) appears exactly once, with a
      mechanism, a child lane, or a recorded infeasibility with evidence.
- [ ] Every `file:line` cited resolves at the commit the header names.
- [ ] The repository-forge question is listed for `gap-ops-canon-rulings`, not decided.

## Tests to write first (TDD)
None: this is a design lane. Its tests are the checks below and a reviewer's reading.

## Checks the lane must run (all must pass)
    F=/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-gap-relay.md
    test -f "$F"
    for s in "## Context" "## Decision" "## Child lanes" "## How each non-negotiable still holds" "## Security impact" "## Migration" "## Consequences" "## Alternatives rejected" "## Verification owed at implementation"; do grep -qx "$s" "$F" || echo "MISSING: $s"; done
    for p in Jira Linear Asana Confluence Notion GitBook LastPass 1Password Proton Drive iCloud Gmail "Apple Mail" "Google Messages" iMessage Signal Discord Slack Zoom WhatsApp Telegram Messenger Instagram TikTok AWS GCP Azure GitHub GitLab; do grep -q "$p" "$F" || echo "UNMENTIONED: $p"; done
    cd /private/tmp/claude-501/storm/qwenstorm-3.0.0/integration && git log -1 --format=%H

## Out of scope
- Code of any kind; the paid-default catalogue (`gap-paid-defaults`); the AWS adapter
  (`gap-aws-*`); the surfaces' own lanes (ADR-0047 S01–S34); vibey's own consumers of the
  surfaces (`gap-spike-surface-consumers`).
- Filing issues, and CHANGELOG.md, docs/, the repository's ADR directory, CLAUDE.md, AGENTS.md,
  GEMINI.md and skill trees.

Commit as `docs(adr): record relay-through-sovereign for declared paid platforms` only if the
operator moves the draft into the repository; otherwise nothing is committed. Do not push.

## Lane card
- **Depends on:** none.
- **Implementer:** a large model or the operator; the storm runner skips `gap-spike-*`.
- **Operator ruling owed:** behaviour 6 (via `gap-ops-canon-rulings`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
