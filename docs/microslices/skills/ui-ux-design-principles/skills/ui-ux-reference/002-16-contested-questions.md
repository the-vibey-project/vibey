---
id: skill-16-contested-questions-4559038877
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-reference/SKILL.md
requires: ["skill-15-anti-patterns-987d3017a6"]
links: ["skill-17-currency-snapshot-verified-august-2026-1ffb29cd74"]
---

## §16. Contested Questions

**16.1 Minimalism vs. signifiers.** Flat/minimal design demonstrably improved consistency
and scalability and reduced visual noise; it also removed the cues that tell people what's
clickable, with a documented cost concentrated in older and less experienced users. Neither
"add bevels back" nor "clean is always better" is right. The resolution is *deliberate
signification*: keep the aesthetic, but ensure every interactive element is identifiable
without hover, and test that assumption with real users rather than with your team.

**16.2 Expressive vs. neutral design.** Material 3 Expressive's research argues emotional
expressiveness and usability are complementary — bolder shapes and bigger primary actions
made key elements ~4× faster to spot and closed the usability age gap. The counterweight:
these are vendor studies of vendor components, the mechanism is mostly "prominence helps"
(which we already knew), and expressiveness is genuinely wrong for some contexts — Google's
own team notes you may not want a playful UI for paying a parking ticket. Direction:
well-supported. Specific numbers: don't generalize.

**16.3 Consistency vs. platform nativeness.** §8.5 → `ui-ux-design-systems-platforms-and-accessibility`.

**16.4 APCA vs. WCAG 2 contrast.** §9.3 → `ui-ux-design-systems-platforms-and-accessibility`. This one has legal consequences, so precision
matters more than usual.

**16.5 Chat vs. GUI for AI features.** §14.1 → `ui-ux-writing-forms-research-and-ethics`.

**16.6 Hamburger menus.** §3.2 → `ui-ux-cognition-heuristics-and-navigation`.

**16.7 Disabled submit buttons.** §4.6 → `ui-ux-interaction-layout-and-visual-design`.

**16.8 A/B testing vs. qualitative research.** A/B tests answer "which is better" with
statistical rigour but cannot tell you *why*, cannot evaluate options you didn't build, and
systematically favour short-term engagement over long-term value (the classic failure: the
variant that wins on click-through erodes trust over months). Qualitative research explains
mechanism and generates options but can't quantify effect. **They answer different questions
and neither substitutes for the other.** Teams that use only A/B testing optimize into local
maxima; teams that use only qualitative research ship confident guesses.

**16.9 Design system centralization.** A single central team produces consistency and
quality but becomes a bottleneck and drifts from product reality; a federated model produces
adoption and relevance but drifts toward inconsistency. Most mature organizations end up
with a small core team owning foundations plus a contribution model with review — and the
governance, not the model, is what determines whether it works.

**16.10 Does "UX = UI" still hold?** NN/g's 2026 position is that UI is becoming less of a
differentiator as design systems standardize components and AI mediation sits above the
interface. The counterargument is that this has been predicted before, that most software
in the world is still mediocre at basic interface craft, and that declaring UI solved while
83.9% of top sites fail color contrast is premature. Both can be true: the *ceiling* on
UI differentiation may be falling while the *floor* remains unmet.

---
