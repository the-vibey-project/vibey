---
id: skill-19-quick-reference-ccc69a2397
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-reference/SKILL.md
requires: ["skill-18-the-canon-0e73b8c214"]
links: ["skill-20-sources-and-method-36449183b0"]
---

## §19. Quick Reference

### 19.1 The numbers
- Touch target: **44 pt** (Apple) / **48 dp** (Material) / **24 px** WCAG AA floor,
  **44 px** WCAG AAA. Design to 44–48.
- Body text: **≥16 px** web; measure **45–75 characters**; line-height **1.4–1.6**.
- Contrast: **4.5:1** body, **3:1** large text and UI components.
- Response: **<100 ms** instant · **<400 ms** stays in flow (Doherty) · **>1 s** show
  progress · **>10 s** allow cancel.
- Core Web Vitals: LCP **2.5 s** · INP **200 ms** · CLS **0.1**, at p75.
- Motion: **150–300 ms**, ease-out in, ease-in out.
- Working memory: ~**4** chunks (not 7).
- Usability testing: **5 per segment per round**, **3 rounds**.
- SUS: **68** average, **80+** good.
- Text expansion for localization: budget **+30–40%**.
- Checkout: **~70%** abandonment; target **12–14** form fields, not 23.

### 19.2 Design review checklist
- [ ] Is the primary action obvious, singular, and reachable (thumb zone on mobile)?
- [ ] Does spacing group correctly — tighter within, looser between? (§1.3 → `ui-ux-cognition-heuristics-and-navigation`)
- [ ] Is every interactive element identifiable *without* hover? (§2.2 → `ui-ux-cognition-heuristics-and-navigation`)
- [ ] Are all states designed: hover, focus, active, disabled, loading, error, empty, selected?
- [ ] Contrast ≥4.5:1 body / ≥3:1 UI; meaning never carried by color alone?
- [ ] Full keyboard operation with a visible focus indicator?
- [ ] Works at 200% zoom and 320 px reflow? Respects OS text size?
- [ ] Screen-reader tested — labels, headings, landmarks, focus management?
- [ ] Errors say what happened, why, and what to do next?
- [ ] Is there undo instead of a confirmation dialog? (§2.3 → `ui-ux-cognition-heuristics-and-navigation`)
- [ ] Does Back / Escape / Enter do what the platform says they do?
- [ ] Do the defaults serve the user rather than the business? (§13.4 → `ui-ux-writing-forms-research-and-ethics`)
- [ ] Does the copy use the user's words and front-load meaning?
- [ ] What happens at 0 items, 1 item, 10,000 items, and on a failed request?
- [ ] Has anyone outside the team completed the task without help?

### 19.3 "This feels wrong but I can't say why" — diagnostic
Hierarchy unclear (§6.1 → `ui-ux-interaction-layout-and-visual-design`) → grouping ambiguous (§1.3 → `ui-ux-cognition-heuristics-and-navigation`) → too many equal-weight options
(§1.2 → `ui-ux-cognition-heuristics-and-navigation`) → signifiers missing (§2.2 → `ui-ux-cognition-heuristics-and-navigation`) → inconsistent with itself or the platform (§2.1 → `ui-ux-cognition-heuristics-and-navigation` #4,
§8 → `ui-ux-design-systems-platforms-and-accessibility`) → language is the product's, not the user's (§10 → `ui-ux-writing-forms-research-and-ethics`) → state is hidden so the user must
remember (§1.2 → `ui-ux-cognition-heuristics-and-navigation`) → the wrong gulf: they can't figure out how to act (execution) or can't
tell whether it worked (evaluation) (§2.2 → `ui-ux-cognition-heuristics-and-navigation`).

---
