---
id: skill-core-framework-9977ce2216
purpose: core framework
source: src/vibey_tools/skills/plugins/engineering-process/skills/requirements-gathering/SKILL.md
requires: []
links: ["skill-right-sizing-the-method-6d309c5ac8"]
---

## Core Framework

### Standards and Governing Bodies
- **ISO/IEC/IEEE 29148:2018** — governing standard; defines RE as "an interdisciplinary function that mediates between the domains of the acquirer and supplier or developer to establish and maintain the requirements to be met by the system, software or service." Three processes: Business/Mission Analysis; Stakeholder Needs & Requirements Definition; System/Software Requirements Definition.
- **Functional requirement syntax** (29148): `[Condition][Subject][Action][Object][Constraint of action]` — e.g., "Upon receiving signal x, the system shall set the 'signal x received' bit within 2 seconds."
- **Quality characteristics of a good requirement**: necessary, unambiguous, complete, singular, feasible, verifiable, traceable.
- **IREB CPRE v3.0** — four core activities: elicit, document, validate/negotiate, manage. Key principles: **Value Orientation** (requirements are a means to deliver value, not an end) and **Shared Understanding**.
- **BABOK v3** — requirements hierarchy: **business requirements → stakeholder requirements → solution requirements (functional + non-functional) → transition requirements**.

### Role Distinctions
- **Product management**: owns the "why/what-to-bet-on" and outcomes.
- **Business analysis**: owns the "what/translate-need-to-spec," especially in enterprise IT.
- **Requirements engineering**: owns rigor, modeling, traceability, and verification in systems/regulated domains.
- Roles overlap heavily; which title "owns" requirements depends on org structure.

### Key Conceptual Distinctions
- **Stated vs. real vs. latent requirements**: customers articulate stated requirements (often pre-baked solutions); analysts must translate to real needs and probe for latent needs.
- **Verification vs. validation**: verification = "are we building it right?" (meets spec); validation = "are we building the right thing?" (meets real need).
- **Requirements vs. constraints vs. assumptions vs. dependencies**: keep these distinct — each drives different execution.
- **The requirements paradox**: customers often can't say what they want until they see what they don't want — the empirical basis for prototyping and example-driven elicitation.

---
