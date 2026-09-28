---
id: skill-the-c4-model-simon-brown-74f8e07a56
purpose: the c4 model simon brown
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-architecture-decision-records-adrs-049a181753"]
links: ["skill-design-documents-and-rfcs-89d3b74c55"]
---

## The C4 Model (Simon Brown)

The dominant lightweight diagramming approach. Notation- and tool-independent.

### Four Levels
| Level | Name | Shows |
|---|---|---|
| 1 | **System Context** | Your system and its relationships to users and other systems |
| 2 | **Container** | Deployable/runnable units (apps, databases, microservices) |
| 3 | **Component** | Non-deployable logical groupings inside a container |
| 4 | **Code** | Classes, interfaces (rarely needed; auto-generate from IDE) |

**Most common error:** Mixing containers and components on the same diagram.

### Key Corrections (Brown, GOTO 2024)
- C4 does **not** replace UML
- **Complements** (does not conflict with) DDD and ADRs
- Works for both monoliths and microservices
- Diagrams should "show the **outcomes** of decisions, not the decision-making process" — use ADRs for that

### Docs-as-Code and Diagramming-as-Code (2024–2026)
- **Mermaid.js:** Native in GitHub/GitLab/Confluence — text-based, Git-versioned
- **PlantUML:** Mature, wide tool support
- **Structurizr (C4-as-code DSL):** Purpose-built for C4; generates multiple diagrams from one model
- **Excalidraw, draw.io:** For freeform collaborative whiteboarding

Trend: text-based, Git-versioned diagrams that stay in sync with code. AI-generated C4 from codebases (e.g., via Claude Code → Structurizr DSL) is emerging with quality caveats.

---
