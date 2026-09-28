---
id: skill-special-contexts-018af83196
purpose: special contexts
source: src/vibey_tools/skills/plugins/engineering-process/skills/requirements-gathering/SKILL.md
requires: ["skill-documentation-standards-0b0f1bcfe4"]
links: ["skill-continuous-discovery-teresa-torres-ae4963bfc2"]
---

## Special Contexts

### Bug Fixes
"Fix the bug" is not a requirement. Minimum artifact: steps to reproduce + expected vs. actual behavior + impact/severity + environment. Add regression requirements. Use 5 Whys/Ishikawa for root cause.

### Legacy Modernization
The existing system *is* the requirements baseline — use characterization testing (Feathers), Strangler Fig sequencing. Most-forgotten area: **data migration requirements**. Treat entrenched user mental models and undocumented workarounds as requirements.

### Regulated/Safety-Critical
- **DO-178C** (avionics): high-level → low-level requirements with bidirectional traceability.
- **IEC 62304** (medical device software safety classes).
- **ISO 26262** (automotive ASIL): safety goals → functional safety requirements → technical safety requirements.
- FMEA and hazard analysis feed requirements; configuration management governs change.

### AI/ML-Specific Requirements
Specify: accuracy/precision/recall/confidence thresholds, bias/fairness constraints, training-data and data-quality requirements, explainability, model-drift monitoring, retraining triggers, fallback behavior, and **human-oversight requirements**.

**EU AI Act (Regulation (EU) 2024/1689)**:
- In force Aug 1, 2024.
- Article 14(1): high-risk AI systems must be designed so "natural persons" can effectively oversee them and remain aware of automation bias.
- Annex III biometric-identification systems require verification by at least two competent persons.
- Articles 8–15: risk management, data governance, technical documentation, transparency, accuracy/robustness/cybersecurity, and logging (≥6 months).
- **Timeline**: Article 50 transparency and GPAI rules apply from Aug 2, 2026; stand-alone high-risk (Annex III) obligations extended to Dec 2, 2027 per May 2026 "AI Act Omnibus" — verify final adopted text before compliance planning.

---
