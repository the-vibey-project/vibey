---
id: skill-14-ai-era-interfaces-0724d40f99
purpose: 14 ai era interfaces
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-writing-forms-research-and-ethics/SKILL.md
requires: ["skill-13-ethics-persuasion-and-dark-patterns-7be0195082"]
links: []
---

## §14. AI-Era Interfaces

### 14.1 What actually changed

**[CONTESTED, and the most overclaimed area in the field.]** Two framings:
- NN/g's line (Nielsen, 2023): generative AI is the **first new UI paradigm in 60 years** —
  *intent-based outcome specification* rather than command specification. NN/g's **State of
  UX 2026** extends this: UI is becoming less of a differentiator, AI-mediated interaction
  sits on top of the interface, and equating UX with UI increasingly misdescribes the work.
- The skeptical line: chat is a *regression* in discoverability, learnability, and
  efficiency for most tasks; it externalizes the interface designer's job onto the user, who
  must now guess what the system can do. A blank text box has zero affordances.

**The synthesis practitioners actually ship:** a **hybrid** — conversational or intent-based
entry, traditional UI for execution and refinement. The rule of thumb that circulates and
holds up well: *if the user can describe the task in one sentence, conversational works; if
the task requires manipulation, comparison, precision, or spatial reasoning, give them a UI.*

### 14.2 Design principles for AI features

1. **Set expectations before the first interaction.** What can this do? What can't it?
   What data does it see? Blank-box interfaces produce both over- and under-estimation.
2. **Make capability discoverable** — suggested prompts, examples, templates. This is the
   direct replacement for menus and buttons as an affordance mechanism.
3. **Show provenance and uncertainty.** Citations, sources, confidence signals. Users
   calibrate trust from these; without them they either over-trust or reject wholesale.
4. **Keep the human in control**: editable output, regenerate, undo, and a way to *not* use
   the AI path. Never make the AI the only route to a function.
5. **Design for failure as a first-class state.** Hallucination, refusal, timeout,
   irrelevance. These are not edge cases; they're the normal distribution's tail and users
   hit them constantly.
6. **Make cost and latency legible.** Streaming output is a UX decision (it converts a
   10-second wait into a 300 ms first token, §6.6 → `ui-ux-interaction-layout-and-visual-design`). Token/credit consumption should be
   visible where it matters.
7. **Feedback loops** — thumbs, corrections, "not what I meant" — both for model improvement
   and because the ability to complain is itself a control affordance.
8. **Privacy transparency** — what's sent, what's retained, what trains. This is a design
   surface, not a legal footnote.

### 14.3 Generative UI, and its risk

"Generative UI" — interfaces assembled or adapted at runtime — is real and growing, and
NN/g frames the shift as **outcome-oriented design**: designing adaptive *frameworks* that
respond to individual goals rather than optimizing single interfaces for an average user.

Two documented risks worth holding onto:
- **Homogenization.** AI generation draws on dominant patterns; one Adobe study reported
  **>42% of AI-generated interfaces shared similar navigation structures and components**.
  The floor rises; the ceiling doesn't.
- **Dark patterns at scale.** An NN/g survey found **36% of designers fear AI will
  normalize dark patterns under the banner of UX optimization** — because an optimizer
  pointed at conversion will find manipulation, and it will find it faster than a human.
  If you let a system optimize choice architecture, constrain it with the §13.4 checklist
  as hard constraints, not preferences.

**Accessibility caution:** AI-generated UI and AI-generated code produce plausible markup
with unreliable semantics. Everything in §9 → `ui-ux-design-systems-platforms-and-accessibility` still has to be verified by a human. Figma's own
framing of its AI outputs is that they still need human review for accessibility, semantics,
and production readiness — take that at face value.

### 14.4 Tooling reality (2026)

Design tooling has moved fast: Figma's **State of the Designer 2026** (survey of 906
designers) reports **72% now use generative AI in their workflows**, with **98% having
increased usage in the past year** and **91% of those saying it improves output quality**,
not just speed. Figma's **Config 2026** introduced code layers on the canvas, design agents,
and an MCP server that lets AI agents operate on the file with real design-system context;
**Penpot** (open-source, self-hostable, native DTCG tokens, CSS-native output) shipped an
MCP server too and is the credible option for regulated or open-source-constrained teams.

**The honest read:** these tools compress production, not judgment. The bottleneck moved
from making screens to knowing which screens to make — which is why the durable content in
§1–§4 → `ui-ux-cognition-heuristics-and-navigation`, `ui-ux-interaction-layout-and-visual-design` and §12 is worth more now, not less.
