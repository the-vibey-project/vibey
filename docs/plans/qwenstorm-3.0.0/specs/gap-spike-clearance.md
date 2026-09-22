## Title
docs(adr): decide cloud-grade clearance (10.d) — criteria per transition, recorded overrides, re-verification, and the loud override notice with its bill (spike for gap N8)

## Why
10.d (`src/vibey_tools/gh/docs/doctrines.md:395-410` at integration HEAD `4317cff6`) binds five things:
- clearance "for each transition along the pipeline from install through main validation",
  against every cloud-computing criterion: availability, reliability, redundancy, elasticity,
  durability, observability, recoverability, fault tolerance, security and scalability;
- "an explicit, recorded override that holds until the state in which they can actually be
  executed arrives";
- "never assume a previous clearance still applies at the current ledger moment. Clearance is a
  claim about a moment, re-verified at every transition";
- an automatic override when a metric "is confirmed no longer met … so development continues";
- the lapse "socialized to every reachable agent — loudly, with explicit detail of the criterion,
  its threshold, its current measurement, and exactly what bill must be paid to restore full
  clearance".

Only `doctrines.md` mentions clearance (gap N8, `issue-audit/gaps.md:765-772`). The nearest
machinery is #134's feasibility engine in vibey-gh:
- six materials × three properties (`src/vibey_tools/gh/vibey_gh/feasibility.py:76-120`);
- the nine-stage path from `install` to `main-validation`, as data (`DEFAULT_STAGES`, `:253-322`);
- a three-valued verdict (`:1-40`, `:441-470`), reached from the conductor through
  `src/vibey/infrastructure/preflight_feasibility.py:34-145`;
- only 2 of 18 coordinates measured, cost `unknown`, and φ unspecified
  (`issue-audit/updates/134.md`, "Current state" and "Proposed child issues" 1–9).

Where clearance lives, and how its ten criteria relate to the eighteen coordinates, decides
every child lane. So this is a spike: `gap-clearance-domain` is **not** written now, because its
names and fields depend on the answers below.

**Implementer: a large model or the operator (design, not code); the storm runner skips
gap-spike-\*.** Deliverable: the draft ADR
`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-gap-clearance.md`, in the shape of
`specs/ADR-two-loops.md`. Evidence comes from the integration clone at `4317cff6` or later
(stated), never from `/Users/adam/git/vibey`.

## Required behaviour
The ADR must decide, with evidence at `file:line`:
1. **Home and vocabulary.** Either vibey-gh (beside `feasibility.py`, which already owns the
   stage path and is dependency-free, so vibey's domain may import it), or vibey's domain, or
   both, with one owner under 10.e (`doctrines.md:417`). Name the pure types and their fields:
   - the ten criteria as a closed vocabulary with a forward-compatible reader (10.g draft,
     `gap-canon-owed-drafts`);
   - a criterion's requirement per transition (threshold, unit, direction);
   - a reading (value or unknown, source, cutoff: reuse `StatusClaim` from `gap-status-vocabulary`);
   - an override (criterion, transition, reason, the condition that ends it, who recorded it,
     and whether it is automatic);
   - the verdict per transition, and how it composes with the feasibility verdict.
2. **The criteria against the coordinates.** Map each of the ten to #134's coordinates where one
   fits: availability and reliability to their property columns; security perhaps to agency.
   Say which criteria need new measurements: redundancy, elasticity, durability,
   observability, recoverability, fault tolerance, scalability. Say which `gap-measure-*` lane
   or #134 child supplies each.
3. **Transitions.** Confirm the nine stages as 10.d's pipeline, or add vibey's own phase
   transitions (INTAKE→DESIGN→BUILD⇄REVIEW→DEPLOY_*). Name the hook that re-verifies at each one:
   - vibey-gh's merge train and promote for `develop` and `main`;
   - the conductor's phase advance for BUILD and DEPLOY;
   - the installer for `install`.
   State that no verdict is cached across transitions ("a claim about a moment").
4. **Overrides.**
   - The declared form (12.c): a key in `vibey.toml` or `.vibey-gh.toml` with its environment
     override, reviewed in a PR.
   - The recorded form (7.c): new ledger kinds, for example `ClearanceOverrideRecorded`,
     `ClearanceLapsed` and `ClearanceRestored`.
   - How "the state in which they can actually be executed arrives" is detected, and that the
     override then lifts itself and records it.
   - That a machine may *record* an automatic override but never *widen* a human's (12.d draft).
5. **The notice.**
   - Where "every reachable agent" is: the ledger; the PR comment through the forge adapter; the
     messaging surface, Matrix by default (8.b), through its lane (8.f,
     `specs/surfaces-adapter-messaging.md`); the agents' next briefing.
   - Its exact fields: criterion, threshold, current measurement with its cutoff, and the bill.
   - Its threshold: which lapses broadcast, how repeats are rate-limited, and idempotency keys.
6. **The bill.** Its units: dollars in the paid lane, generation-seconds in the local lane, and
   hardware or storage to acquire. How it is computed from #134's cost integral (child 7). That
   it is `unknown`, with the missing source named, until it is measured (10.f). It is never an
   invented figure.
7. **Measurement** (8.g, `doctrines.md:316-324`): each criterion's reading goes through
   `MeasurementPort` (`gap-measure-port`) into the ledger.
8. **Operator questions** it cannot settle: for example, whether a lapsed *security* criterion
   may ever be auto-overridden. List them for `gap-ops-canon-rulings`; do not decide them.

## Where to change
Nothing in the repository. Write only `…/specs/ADR-gap-clearance.md`.

Required ADR sections, in order:
- the header line: **Status:** proposed · **Date** · **Cites:** 10.d, 10.f, 7.c, 8.g, 8.b,
  8.f, 10.e, 12.c · **Related:** ADR-0040, #134, ADR-0047 · **Evidence:** the commit read;
- an **Owes:** line;
- `## Context`;
- `## Decision` (1–7 above as subsections);
- `## Child lanes`;
- `## How each non-negotiable still holds`;
- `## Security impact`;
- `## Migration`;
- `## Consequences`;
- `## Alternatives rejected`, covering at least: clearance as a thirteenth-doctrine-sized
  subsystem separate from #134; caching a verdict per release; silent auto-override;
- `## Verification owed at implementation`.

Child lanes the ADR must name, each sized for one source file plus its interface and one test
file, with dependencies: `gap-clearance-domain`, `gap-clearance-config`, `gap-clearance-ledger`,
`gap-clearance-reverify-gh` (merge train and promote), `gap-clearance-reverify-phases`,
`gap-clearance-notice` (after the messaging lane), `gap-clearance-bill` (after #134 child 7),
and one probe lane per criterion that #134's children do not already cover.

## Acceptance criteria
- [ ] The ADR exists with every required section.
- [ ] All ten 10.d criteria appear, each with a measurement source or a recorded "unmeasured, because".
- [ ] `gap-clearance-domain` can be specified from the ADR alone: exact names, fields, invariants.
- [ ] Every `file:line` resolves at the commit the header names. Operator questions are listed, not decided.

## Tests to write first (TDD)
None: a design lane. The checks below and a reviewer's reading are its tests.

## Checks the lane must run (all must pass)
    F=/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-gap-clearance.md
    test -f "$F"
    for s in "## Context" "## Decision" "## Child lanes" "## How each non-negotiable still holds" "## Security impact" "## Migration" "## Consequences" "## Alternatives rejected" "## Verification owed at implementation"; do grep -qx "$s" "$F" || echo "MISSING: $s"; done
    for c in availability reliability redundancy elasticity durability observability recoverability "fault tolerance" security scalability; do grep -qi "$c" "$F" || echo "UNMENTIONED: $c"; done
    cd /private/tmp/claude-501/storm/qwenstorm-3.0.0/integration && git log -1 --format=%H

## Out of scope
- Code of any kind. #134's probes and cost integral (its own children). Filing issues.
- CHANGELOG.md, docs/, the repository's ADR directory, CLAUDE.md, AGENTS.md, GEMINI.md, skill trees.

Commit as `docs(adr): decide cloud-grade clearance (10.d)` only if the operator moves the draft
into the repository; otherwise nothing is committed. Do not push.

## Lane card
- **Depends on:** `gap-status-vocabulary` (the claim type the ADR reuses). It reads, but does
  not wait for, `gap-measure-port` and `gap-canon-owed-drafts` (10.g, 12.d drafts).
- **Kind:** design spike. The storm runner skips it.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
