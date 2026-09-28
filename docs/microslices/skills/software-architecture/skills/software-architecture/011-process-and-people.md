---
id: skill-process-and-people-74f890c97f
purpose: process and people
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-ci-cd-010861d9fe"]
links: ["skill-sequencing-decisions-cfd98ecb39"]
---

## Process and People

### Conway's Law
"The modular decomposition of a system and the decomposition of the development organization must be done together, continuously" — Martin Fowler. Use DDD strategic design (event storming + context mapping) to find bounded contexts, then assign one team per bounded context. The **Inverse Conway Maneuver**: deliberately shape teams to mirror the architecture you want.

### Architecture Decision Records (ADRs)
- Coined by Michael Nygard (Nov 15, 2011)
- Standard sections (Nygard's order): **Title, Context, Decision, Status, Consequences**
- Store in-repo as numbered markdown (`doc/adr/NNN-*.md`) — synced with code, gets PR review
- ADR numbers are never reused; treat as immutable — if reversed, keep old ADR marked "superseded" with link to replacement
- ThoughtWorks Technology Radar: "Adopt" — store in source control, not a wiki
- **Failure pattern**: ADRs in Confluence/Notion separated from code don't get read at decision time
- Tooling: `adr-tools` (Nat Pryce), Log4brains (publishes static site), MADR template

### Vertical Slice Architecture (Jimmy Bogard, April 19, 2018)
- Code organized around distinct requests, front-end to back
- **Minimize coupling between slices, maximize coupling within a slice**
- Wins when features are relatively independent and teams own different features
- Tradeoff: without disciplined refactoring, slices devolve into sprawling duplicated logic
- Sharing code between slices is allowed — "minimise isn't zero"

---
