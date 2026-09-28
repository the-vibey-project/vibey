---
id: skill-design-systems-a613791c3d
purpose: design systems
source: src/vibey_tools/skills/plugins/frontend-design/skills/graphic-ux-ui-design/SKILL.md
requires: ["skill-ux-research-methods-d447f3d3aa"]
links: ["skill-ai-design-tools-honest-assessment-d5312f2185"]
---

## Design Systems

### What a Design System Is

"A design system is a living, funded product with a roadmap & backlog, serving an ecosystem." (Nathan Curtis)

Components:
- Component library (coded components)
- Pattern library (documented solutions)
- Tokens (the shared contract)
- Guidelines + governance + people

### Three-Tier Token Architecture

```
Primitives      →   Semantic/Alias     →   Component
blue-500: #3B82F6   color-action-primary   button-bg-primary
                    color-text-primary
```

- Applications consume **semantic** tokens, not primitives
- Semantic names encode intent, not value: `color-text-primary`, not `color-blue-500`
- Small teams can use two tiers (primitive + semantic)
- Enterprise/multi-brand/multi-theme needs all three
- More than three tiers is rarely justified
- This architecture is what makes multi-mode theming (light/dark, density, brand) a matter of re-pointing tokens

### Tooling Pipeline

| Tool             | Role                                             |
|------------------|--------------------------------------------------|
| Style Dictionary | Transform design tokens into platform code      |
| Tokens Studio    | Figma-based token management                    |
| W3C DTCG format  | Standardizing JSON (`$value`/`$type`)           |
| Figma Variables  | Primitives, semantic tokens, multi-mode collections |
| Storybook        | Code-first component documentation              |
| Zeroheight / Supernova | Design-first documentation                |

### Atomic Design: What Holds and What Doesn't

Atoms → Molecules → Organisms → Templates → Pages (Brad Frost, 2013).

**What holds:** Systems-thinking, shared vocabulary that "UIs are interconnected hierarchical systems," templates/pages for testing real content.

**What's outdated:** The atom/molecule/organism taxonomy is "too fuzzy" and abstracts too early. Practitioners now recommend starting with a flat component hierarchy and letting structure emerge. Frost himself has moved "subatomic" — toward design tokens as the smallest unit.

### Governance Models (Nathan Curtis / EightShapes)

| Model       | Description                                                |
|-------------|------------------------------------------------------------|
| Solitary    | One team builds for its own needs ("Overlords don't scale") |
| Centralized | Dedicated team makes and spreads decisions for other teams |
| Federated   | Designers from multiple product teams decide together      |
| Cyclical    | Centralized team + federated contributor community (Jina Anne/Salesforce) |

Curtis's contribution principle: "central system team members can't make all the decisions… a system practice must model and foster a federated community."

Relevance heuristic for what belongs in the system: useful to 3 products → discuss; useful to 5 → it probably belongs.

### Versioning (SemVer)

"Every discussion about versioning design system outputs begins and ends with SemVer." (Curtis)

- **MAJOR**: breaking changes
- **MINOR**: backwards-compatible features
- **PATCH**: backwards-compatible fixes

**Library-level vs. component-level versioning:**
- Library-level: one version across all assets — common for vanilla HTML/CSS
- Component-level: mix-and-match (e.g., Atlaskit Badge v15.0.8) — suited to React/continuous-release

Package tokens as a separate dependency so style can evolve independently of component APIs.

### Adoption Measurement

Distinguish:
- **Usage** (breadth): which components, how often
- **Coverage** (depth): how much of the UI is built from the system

Tools:
- Figma Library Analytics: insertions, total instances, detaches
- `react-scanner` for static component-instance analysis from code
- Omlet, Preply's visual-coverage tool

Track detach rate as a diagnostic — a rising detach rate signals a bug, missing variant, or unmet need, and should trigger investigation, not enforcement.

### Deprecation Process

Atlassian's 6-step process: communicate intent → set a timeline → add docs notice → run deprecation commands → communicate again → delete.

Timeline guidance by audience:
- Salesforce: 18 months
- Financial Times Origami: 3–6 months (tight developer community)

Run enhanced + deprecated in parallel before removal in the next major version.

---
