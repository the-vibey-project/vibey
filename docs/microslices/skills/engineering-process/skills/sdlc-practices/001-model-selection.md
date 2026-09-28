---
id: skill-model-selection-d0917f5661
purpose: model selection
source: src/vibey_tools/skills/plugins/engineering-process/skills/sdlc-practices/SKILL.md
requires: []
links: ["skill-requirements-engineering-in-the-sdlc-f1b5518a27"]
---

## Model Selection

### Core Principle
There is no single "best" SDLC. The correct model is a function of requirements volatility, regulatory constraints, and team context. The 2026 enterprise norm is **hybrid**: phase-gate governance wrapping Agile/continuous execution.

### Cynefin Framework for Model Selection
| Domain | Characteristics | Recommended Approach |
|---|---|---|
| Clear/Obvious | Stable requirements, known solutions | Plan-driven, predictive, PMBOK |
| Complicated | Known unknowns, expertise required | Plan-driven with analysis, RUP |
| Complex | Emergent requirements, high uncertainty | Agile/empirical, Scrum/Kanban |
| Chaotic | Crisis, novel situations | Act-first stabilization |

Most common error: treating Complex problems as Complicated — over-planning the unknowable.

### Waterfall and V-Model
Royce's 1970 paper actually advocated iteration and prototyping; the linear "waterfall" caricature inverted his argument.

**Waterfall is correct when**: requirements are genuinely fixed and change is expensive or dangerous — fixed-price/defense contracts, and safety-critical/regulated systems governed by IEC 61508, DO-178C (avionics), and ISO 26262 (automotive).

**V-Model**: extends waterfall by pairing each development phase with a verification/validation level (unit/integration/system/acceptance). Dominates embedded, medical-device, and automotive development.

### Iterative Models
- **Spiral (Boehm 1986)**: risk-driven, cycling through four quadrants (objectives/alternatives → risk identification/mitigation → development/test → plan next iteration). Suits large, high-risk programs.
- **RUP/Unified Process**: use-case-driven, architecture-centric, iterative across inception/elaboration/construction/transition. Relevant where formal artifacts and architecture rigor are required.

### Agile Family
- **Scrum**: time-boxed sprints, Product Owner, Scrum Master, Developers; empirical process control.
- **Kanban**: continuous flow, WIP limits, visualize workflow, no iterations.
- **FDD**: feature lists, design-by-feature/build-by-feature.
- **DSDM**: MoSCoW, timeboxing, fitness-for-business-purpose.
- **Crystal family (Cockburn)**: scales ceremony to team size and criticality (Clear/Yellow/Orange/Red).

---
