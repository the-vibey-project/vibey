## Title
ops: the operator's open rulings for 3.0.0 (8.a–8.h, 10.b, 12.c, and the decisions lanes wait on)

## Why
The Constitution's Article II.3 (`src/vibey_tools/gh/docs/constitution.md:67-84`) says "a
machine may draft, a human ratifies". Sub-doctrine 12.b and ADR-0020 say a governing rule is a
ratified sub-doctrine or is not a rule. The gap audit found canon/code conflicts and
design choices that no lane may settle by itself (`issue-audit/gaps.md` N4, lines 730-741), and
the gap specs of this batch added more. Under 10.f, an unruled question stays open. It is
never filled in by a lane's assumption.

The operator already ruled on five questions on 2026-09-22 (STORM-CONTEXT.md "Operator
rulings"):
- the cache is Valkey;
- sovereignloop's VS Code is Code - OSS / VSCodium;
- OpenCode is declared-only and transitional;
- claudeloop-local is a paidloop adapter, declared-only;
- #383's RAM tiers.

Those are **not** on this list. They still need their canon text, which is lane
`gap-canon-rulings-amendment`. This lane is the one place the open rulings are tracked.
Each code lane that needs a ruling depends on this slug, so the storm cannot start it
until the operator marks this lane integrated.

Implementer: the operator. The storm runner must skip `gap-ops-*` lanes.

## Required behaviour
Every item in the checklist below is answered, and each answer is recorded where the item
says, before this lane is marked integrated. An item may be answered "defer", with the reason
and a date to revisit. The lanes it gates then stay blocked, and that is visible (10.f).

## Where to change
Nothing in code. Answers are recorded in:
- this issue (one comment per ruling, quoting the item number);
- the ratifying PR or ADR the item names;
- STORM-CONTEXT.md's "Operator rulings" section, so later spec writers inherit them.

## Operator checklist (human — not code; the storm runner must skip gap-ops-* lanes)

1. [ ] **8.c's heading.** The body now says "exactly two loops … a single instance per model"
   (`doctrines.md:196-205`). The heading still reads "every loop runs once, fed by a queue".
   Keep the heading, or retitle it, for example "8.c — two loops, one instance per model, fed
   by queues"?
   - Unblocks: `gap-canon-rulings-amendment` (its 8.c wording) and `gap-docs-agent-briefs`.
   - Record in: the ratifying canon PR.
2. [ ] **The cost of the 8.f cache lane, accepted in writing.** 8.f (`doctrines.md:294-314`)
   routes the cache through its lane and says the cost "is measured and published with the
   design". ADR-0047 §10 and §15 (`specs/ADR-surface-lanes.md`) give the measured Redis
   numbers and the AMQP *estimates*. Accept that cost, or amend 8.f to exempt cache reads?
   - Unblocks: `surfaces-default-flip` (ADR-0047 lane S33).
   - Record in: ADR-0047's status note, and in the canon if 8.f is amended.
3. [ ] **#148's PayPal against 10.b** (`doctrines.md:390-393`, "No fiat processors, ever").
   Confirm #148 carries no fiat path (the rewrite in `issue-audit/updates/148.md` already
   drops it), and name the one crypto rail and its custody (hardware-wallet signing only?).
   - Unblocks: #148's children.
   - Record in: #148.
4. [ ] **Retiring opencodeloop under 12.c.** Removing the runner (ADR-0046 lanes L38 and L39)
   is a move to a less configurable state, which 12.c (`doctrines.md:455`) forbids unless
   accepted. Accept the retirement once `vscode` passes live conformance, or keep
   `opencodeloop` as a declared-only adapter indefinitely?
   - Unblocks: `loops-retire-opencode` (L38) and L39.
   - Record in: ADR-0046's status note.
5. [ ] **The IaC tool for AWS deployments.** The choices are:
   - OpenTofu (MPL-2.0; preferred under 8.a's freer-licence rule);
   - CloudFormation (AWS-native);
   - the AWS CDK.
   - Unblocks: `gap-spike-aws-iac`'s ADR and `gap-aws-deploy-execute`.
   - Record in: that ADR.
6. [ ] **The container image and 8.h** (`doctrines.md:326`). The runnable image is Debian
   bookworm (`deploy/docker/Dockerfile:27`, `:157`). Are OCI images exempt from 8.h's
   "Arch Linux is always the default sovereign operating system", or does the image gain an
   Arch Linux variant, contract-tested like the Debian one?
   - Unblocks: `gap-image-arch`.
   - Record in: the canon (an 8.h clarification) or ADR-0019's status note.
7. [ ] **The Forgejo ruleset mapping.** forge-0g refuses six GitHub ruleset rules on Forgejo
   (`specs/forge-adapter.md:1866-1872`). For each, choose "map to <Forgejo branch-protection
   setting>" or "waive loudly", as proposed in `gap-gh-forgejo-ruleset-profile`.
   - Unblocks: `gap-gh-forgejo-ruleset-profile`.
   - Record in: that spec's PR.
8. [ ] **This repository's own sovereign Forgejo host.** 8.b's relay rule ("the sovereign host
   stays the source of truth") means GitHub should relay from a Forgejo host this project
   runs. Run one (where, and who operates it)? Or GitHub stays the only forge, with the relay
   deferred and the reason recorded?
   - Unblocks: the forge children of `gap-spike-relay`.
   - Record in: `STORM/specs/ADR-gap-relay.md`.
9. [ ] **The single-file executable tool.** ADR-0019 (`docs/architecture/decisions/0019-installable-wherever-its-users-are.md:103-104`)
   names "shiv, pex or PyInstaller" without choosing. Choose one:
   - shiv or pex need a Python on the target;
   - PyInstaller does not, but its per-OS builds must run on Arch Linux and macOS (8.h).
   - Unblocks: `gap-release-single-file`, and through it the npm wrapper (ADR-0019 step 8).
   - Record in: ADR-0019's status note.
10. [ ] **Running PR review on the operator's Mac** (gap L2, `gap-ops-review-lane`). This
    re-registers the sovereign self-hosted runners against `the-vibey-project/vibey`, so
    untrusted PR content reaches a runner on the operator's machine. Accept, with what
    isolation? Or fund the paid key only, and leave the sovereign lane down until a sandboxed
    runner exists?
    - Unblocks: `gap-ops-review-lane`'s sovereign path, and `gap-runners-declared`.
    - Record in: SECURITY.md's threat notes (through the docs wave) and this issue.
11. [ ] **Publishing the record of redactions.** `gap-ledger-redaction-recorded` records each
    redaction in the payload as `_redactions`. The public export trims that field and counts it
    as withheld. Publish `_redactions` for every published kind (it holds paths and classes,
    never values), or keep trimming it?
    - Unblocks: nothing blocking. A follow-up publication-rules lane waits on it.
    - Record in: this issue.
12. [ ] **The VS Code verification owed (V-VS1–V-VS5, V-CC1).** ADR-0046's *Verification owed*
    needs a packet capture, a licence reading and a headless run. Assign it (the operator or a
    large model) and set where the evidence is recorded.
    - Unblocks: `loops-vscode-verification`, then L20, `gap-paid-ide-default` and
      `gap-vscode-agent-tree`.
    - Record in: ADR-0046.

## Acceptance criteria
- [ ] Every item above is ticked, with an answer (or "defer" with a reason and a revisit date)
      recorded where the item says.
- [ ] STORM-CONTEXT.md's "Operator rulings" lists every answer given.
- [ ] Only then is `gap-ops-canon-rulings` appended to `STORM/integrated.txt`, which releases the lanes that depend on it.

## Tests to write first (TDD)
None. This lane is a human checklist.

## Checks the lane must run (all must pass)
None in code. The reviewer checks the acceptance criteria against the issue's comments.

## Out of scope
- Drafting the canon text for rulings already given (`gap-canon-rulings-amendment`).
- Drafting the owed sub-doctrines (`gap-canon-owed-drafts`).
- Implementing any ruling. The lanes named in each item do that.

Commit as `ops: record the operator's open rulings` (only if a file in the tree records them). Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
