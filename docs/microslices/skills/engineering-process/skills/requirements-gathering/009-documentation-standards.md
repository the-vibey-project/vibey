---
id: skill-documentation-standards-0b0f1bcfe4
purpose: documentation standards
source: src/vibey_tools/skills/plugins/engineering-process/skills/requirements-gathering/SKILL.md
requires: ["skill-validation-and-analysis-cc33d7c0fa"]
links: ["skill-special-contexts-018af83196"]
---

## Documentation Standards

### Right-Size by Context
| Scale | Format |
|---|---|
| Lightweight | Stories + acceptance criteria in Jira/Linear — "enough to have the conversation" |
| Medium | Structured stories + explicit NFRs + journey maps + wireframes + data dictionary |
| Heavyweight | SRS/BRD/FSD/SyRS — for contract/regulated work |

### Key Templates
- **VOLERE shell**: comprehensive, fit-criterion-driven; mandates a Fit Criterion per requirement.
- **IEEE 830 SRS structure**: classic functional/NFR specification.
- **arc42**: architecture-oriented.
- **Gherkin feature files** as living documentation.
- **PRDs** in Confluence/Notion.

Avoid over-specification in fast-changing domains — favor **living documentation** over frozen PDFs.

### Traceability
- **Forward**: requirements → design → code → tests.
- **Backward**: tests → code → design → requirements.
- **Bidirectional RTM**: mandatory in regulated domains for impact analysis and coverage.
- **Agile lightweight**: link stories → epics → themes → outcomes (Jira/Azure DevOps hierarchy).
- **Heavyweight tools**: Jama Connect, IBM DOORS/DOORS Next, Siemens Polarion, Codebeamer, Helix RM.

---
