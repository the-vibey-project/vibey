## Title
chore(release): the 3.0.0 gating checklist: what must be true before #316 leaves draft

## Why
The operator decided that 3.0.0 is a breaking release. ADR-0028 and ADR-0037 say how it ships:
`develop` is promoted to `main` by a rebase merge, and a push to `main` publishes the single
`vibey` distribution. Today:
- `pyproject.toml:7` is `2.1.0`;
- #316 (`chore(release): 3.0.0`) is held as a draft;
- #393 and PR #394 cover version derivation only (`issue-audit/gaps.md` L10, lines 608-617).

Nothing states what 3.0.0 must contain. Under 10.f (`src/vibey_tools/gh/docs/doctrines.md:419`)
"a verdict is not completion": this checklist is the evidence list. Its queue dependencies make
the storm hold it until the lanes it names are integrated, and a human ticks the rest.

Implementer: the operator. The storm runner skips `gap-ops-*` lanes.

## Required behaviour
Every item below is either done, with evidence linked, or **explicitly deferred** out of 3.0.0,
with a reason and the release it moves to, before #316 is marked ready.

## Where to change
Nothing in code. This issue is the tracking record, and #316's description links it.

## Operator checklist (human — not code; the storm runner must skip gap-ops-* lanes)
**The behaviour flips 3.0.0 is named for.** Each is done, or deferred with a reason:
1. [ ] RabbitMQ dispatch and the two loops are the default: `rmq-r34-defaults-flip` (#381).
2. [ ] Every sovereign surface runs in its lane by default: `surfaces-default-flip` (ADR-0047
   S33). It needs 8.f's cost accepted (`gap-ops-canon-rulings` item 2).
3. [ ] The test harness routes through its queue by default: `harness-T28-route-flip`.
4. [ ] The two-loop rename has landed: `loops-rename` (ADR-0046 L09). If it is deferred,
   3.0.0 ships `qwenloop` and notes the rename as 3.x.

**The release machinery works:**
5. [ ] Each link of the delivery chain dispatches the next: `gap-chain-dispatch`, with its
   evidence checklist recorded.
6. [ ] At least one review lane produces a green `PR review / gate`: `gap-ops-review-lane`.
7. [ ] The staged-bump fix is merged (PR #394), so the version derives `3.0.0` from the `!` commits.
8. [ ] Article V.4 is honoured: `gap-release-yank-workflow-1`, `-2` are integrated, and the
   current debt is yanked or sequenced (`gap-ops-yank-392`).

**The docs say what 3.0.0 is:**
9. [ ] `gap-docs-changelog`: the 2.1.0 and 3.0.0 sections, with every `!` change, the
   Forgejo/Gitea data-loss warning, the OpenCode repeal and the default-model change.
10. [ ] `gap-docs-agent-briefs`: CLAUDE.md, AGENTS.md and GEMINI.md state 3.0.0's law, with SD-01 carried.
11. [ ] `gap-docs-cli-reference` and `gap-docs-config-reference`.
12. [ ] `gap-docs-adr-land`: ADR-0045, 0046, 0047 and the installer and ORM ADRs are in the nav, with correct counts.

**The law is settled for what ships:**
13. [ ] Every `gap-ops-canon-rulings` item that a shipped behaviour relies on is answered.
14. [ ] The canon amendments for the rulings of 2026-09-22 are ratified
    (`gap-canon-rulings-amendment` merged by the operator).

**Final:**
15. [ ] `develop`'s CI is green, including `gates (Arch Linux)` and `gates (macOS)`
    (`gap-ci-arch-gates`, `gap-ci-macos-gates`), or those are recorded as deferred.
16. [ ] Take #316 out of draft, merge it, and record the promote run URL and the PyPI URL for `vibey==3.0.0`.

## Acceptance criteria
- [ ] Every item is ticked, or deferred with a reason and a target release, recorded in this issue.
- [ ] #316's description links this issue.

## Tests to write first (TDD)
None. This lane is a human checklist.

## Checks the lane must run (all must pass)
None in code.

## Out of scope
- Implementing any item. The named lanes do that.

Commit nothing. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
