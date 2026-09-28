---
id: skill-design-process-by-scale-c476d426c3
purpose: design process by scale
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-design-as-decision-making-96593e366c"]
links: ["skill-principles-as-contextual-heuristics-5122902a99"]
---

## Design Process by Scale

### Bug Fix
1. Root-cause to determine fix location
2. Design a regression test
3. Assess blast radius
4. Decide: targeted patch vs. refactoring opportunity

**Beck's *Tidy First?* warning:** "More than one hour tidying at a time before making any behavioral changes likely means you have lost track of the minimum set of structural changes needed." Structural and behavioral changes go in **separate commits/PRs**.

The symptom may indicate a deeper design problem — decide consciously: fix vs. redesign.

### Small Feature (Days–2 Weeks)
Lightweight process:
1. Understand the requirement
2. Time-boxed spike if uncertain
3. Design the interface first
4. Design the data-model change for forward/backward compatibility
5. Design the test strategy

Central decision: extend existing code vs. create new.

### Medium Feature (Weeks–2 Months)
A **written design document or RFC earns its keep** at this scale. (See Design Communication section.)

### Large / Greenfield System
**The C4 sequence:**
1. Vision → stakeholder/actor identification
2. System Context (C4 Level 1)
3. Containers — deployable units (C4 Level 2)
4. Components — non-deployable elements inside a container (C4 Level 3)
5. Code (C4 Level 4, rarely needed)

Key practices:
- Identify external actors and systems
- Choose architectural style against explicit decision criteria
- Non-functional requirements (NFRs) as **primary design drivers**
- Phase delivery: MVP → Phase 2 → Phase 3
- **Walking skeleton** — the thinnest end-to-end slice that proves the architecture — is the recommended starting build

---
