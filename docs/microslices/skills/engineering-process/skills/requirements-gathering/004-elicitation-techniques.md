---
id: skill-elicitation-techniques-b12fcc9423
purpose: elicitation techniques
source: src/vibey_tools/skills/plugins/engineering-process/skills/requirements-gathering/SKILL.md
requires: ["skill-stakeholder-analysis-1398bb22b6"]
links: ["skill-domain-modeling-6572b20258"]
---

## Elicitation Techniques

### Structured Interviews — The Evidence-Backed Winner
Davis et al. (IEEE RE 2006) systematic review concluded: "(1) Interviews, preferentially structured, appear to be one of the most effective elicitation techniques; (2) Many techniques often cited in the literature, like card sorting, ranking or thinking aloud, tend to be less effective than interviews; (3) Analyst experience does not appear to be a relevant factor."

**Practitioner toolkit:**
- Structured / semi-structured / unstructured formats.
- Open vs. closed and **context-free questions** (Gause & Weinberg).
- **5 Whys / laddering**: drive from surface feature-request to root need.
- Active listening: paraphrase, summarize, strategic silence.
- **Anti-patterns**: the agreeable stakeholder, the solution-provider, the "I want everything" stakeholder, the silent expert.
- Novices fail through *interview design and conduct mistakes*, not lack of domain knowledge — invest in interview craft, not seniority.

### Workshops and Group Techniques
- JAD-style requirements workshops; neutral facilitator, parking lot, ground rules, managing dominant voices.
- Convergence techniques: affinity mapping, dot voting, nominal group, fist-to-five, Roman voting.
- **Pre-mortems** (Gary Klein): imagine the project has already failed — surfaces hidden requirements and risks.

### Event Storming (Alberto Brandolini, 2013)
The dominant collaborative domain-modeling technique. Orange sticky notes = **domain events** (past-tense, business-relevant) placed on a timeline.

**Three formats:**
1. **Big Picture**: ~25–30 people; explore an entire business line; deliberately informal, no strict notation.
2. **Process Modeling**: grammar — read model → command on a system → event → policy ("whenever X we do Y").
3. **Software Design**: adds aggregates, bounded contexts for 1:1 mapping to code.

**Key insight**: "It's developer's (mis)understanding, not expert knowledge, that gets released into production." The magic happens when participants sort events chronologically, forcing discovery of disagreement and gaps. Getting **bounded-context boundaries** right is "the single design decision with the most significant impact over the entire life of a software project."

### Example Mapping (Matt Wynne, Cucumber)
BDD-prerequisite workshop for nailing acceptance criteria. Ideally a **Three Amigos** session (PO/BA + dev + tester). Target: ~25 minutes per story.

| Card Color | Meaning |
|---|---|
| Yellow | Story |
| Blue | Rule (acceptance criterion) |
| Green | Example illustrating one rule (Given/When/Then-ish) |
| Red | Question (unanswerable now) |

**Signals**: table full of red cards = too much uncertainty; many blue cards = story is too big. Do NOT write full Gherkin during the session — identify examples and surface rules, not formalize them.

### Story Mapping (Jeff Patton, 2014)
Two-dimensional backlog: **backbone** (high-level user activities in narrative order) + **user tasks/stories stacked vertically** beneath in priority order. Horizontal slices = releases; topmost slice = **walking skeleton** (Cockburn) — the thinnest end-to-end version.

**Workshop arc (~4 hrs)**: frame outcome → silent-write activities → place backbone → decompose tasks → stack stories essential-to-nice-to-have → slice walking skeleton → slice subsequent releases. Cures the "flat backlog" problem.

### Impact Mapping (Gojko Adzic, 2012)
Mind-map structure: **Why (Goal) → Who (Actors) → How (Impacts/behavior changes) → What (Deliverables)**. Prevents "feature factories" by forcing every deliverable to trace to a measurable goal via a behavioral impact on an actor. Common pitfall: going into deliverable detail before nailing actors and impacts.

### Contextual Inquiry (Beyer & Holtzblatt, early 1990s)
Built on the **master-apprentice model**: researcher is the apprentice, user is the master, conducted in the user's real work context.

**Four principles**: Context, Partnership, Interpretation, Focus. Reveals *tacit* knowledge and workarounds users can't articulate in a conference room. Run an **interpretation session within 24 hours**; build an affinity diagram.

Premier approach for the **tacit-knowledge problem**. Related: shadowing, think-aloud protocol, apprenticing, diary studies, artifact analysis.

### Prototyping and Visualization
Fidelity spectrum: paper/low-fi → wireframe (Balsamiq) → interactive (Figma — de-facto modern source of truth for UI requirements; Axure, InVision, Marvel).

**Wizard-of-Oz** prototyping (human behind the curtain) is invaluable for AI/complex features. The "I know it when I see it" concretization effect makes prototyping the practitioner favorite for surfacing unstated assumptions — even though the Davis review didn't credit it for raw information yield under controlled conditions.

### User Stories vs. Job Stories
**User story**: "As a [role], I want [goal], so that [benefit]" — tested against **INVEST** (Independent, Negotiable, Valuable, Estimable, Small, Testable).

**Job story** (originated at Intercom, named by Alan Klement): "When [situation], I want to [motivation], so I can [expected outcome]." Replaces persona with situation; reduces tendency to smuggle in a prescribed solution and to drop the "so that." Intercom's rationale: motivations are far more similar across demographics than personas imply.

**Acceptance criteria**: Given/When/Then (Gherkin) or bulleted positive/negative cases.

**Splitting patterns**: by workflow step, data variation, role, happy/unhappy path, interface variation, business rule.

### JTBD Switch Interview (Bob Moesta and Chris Spiek)
Forensically reconstructs a recent real purchase backward through markers: **First Thought → Passive Looking → Event 1 (trigger) → Active Looking → Event 2 (final trigger) → Decision/Purchase → Consumption**.

**Four Forces of Progress** (built on Lewin's force-field theory):
- **Push of the situation**: friction/frustration that makes someone start looking.
- **Pull of the new solution**: the better life the customer pictures.
- **Anxiety of the new solution**: fear of the unknown — the most underestimated force.
- **Habit of the present**: comfortable inertia of what people already know and do.

Push + Pull > Anxiety + Habit → the switch happens.

Moesta's claim: ~10 strategically chosen recent buyers reveal 3–5 buying patterns covering most of a market ("We'll do ten interviews, but it's like having a thousand surveys").

---
