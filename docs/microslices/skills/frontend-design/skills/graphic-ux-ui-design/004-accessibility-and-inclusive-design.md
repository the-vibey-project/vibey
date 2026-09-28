---
id: skill-accessibility-and-inclusive-design-797cb256bc
purpose: accessibility and inclusive design
source: src/vibey_tools/skills/plugins/frontend-design/skills/graphic-ux-ui-design/SKILL.md
requires: ["skill-component-and-interaction-patterns-8ecf9a6773"]
links: ["skill-ux-research-methods-d447f3d3aa"]
---

## Accessibility and Inclusive Design

### State of the Web (WebAIM Million)

| Year | Pages with WCAG failures | Low-contrast text | Errors/page |
|------|--------------------------|-------------------|-------------|
| 2025 | 94.8%                    | 79.1%             | 51.0        |
| 2026 | (implied regression)     | 83.9%             | 56.1        |

The six issue types accounting for 96% of all errors:
1. Low-contrast text (83.9% of pages)
2. Missing alt text (55.5% of pages; ~18.5% of images)
3. Missing form labels (48.2% of pages)
4. Empty links (45.4%)
5. Empty buttons
6. Missing document language

### WCAG 2.2 Key Additions (Oct 2023)

AA-level additions designers must know:
- **2.4.11 Focus Not Obscured (Minimum)**: sticky headers/footers can't fully hide a focused element
- **2.5.7 Dragging Movements**: drag must have a single-pointer alternative
- **2.5.8 Target Size (Minimum)**: 24×24 CSS px or adequate spacing
- **3.3.8 Accessible Authentication**: no cognitive-function test without an alternative
- **3.2.6 Consistent Help** (Level A)
- **3.3.7 Redundant Entry** (Level A)

Note: 4.1.1 Parsing was removed in WCAG 2.2.

### Semantic HTML and ARIA

**Use native HTML elements first.** They carry built-in roles, keyboard handling, and focus management.

"No ARIA is better than bad ARIA": pages *with* ARIA averaged ~34–41% *more* detected errors than pages without (WebAIM). ARIA adds semantics but never behavior — a `div role="button"` still requires manual keyboard handlers. Reserve ARIA for genuinely custom widgets (tabs, comboboxes, live regions).

### Keyboard and Screen Reader Testing

Provide: logical tab order, visible focus indicators, skip links, managed focus in SPAs (move focus on route change, trap in modals, restore on close).

Test with multiple screen readers — they differ in behavior:
- VoiceOver (macOS/iOS, Safari)
- NVDA (Windows, Firefox/Chrome)
- JAWS (Windows, Firefox/Chrome)

Automated tools (axe, Lighthouse, WAVE) catch only **30–40% of issues**. Manual keyboard + screen-reader testing is mandatory.

### Color-Vision Deficiency

~8% of men have a color-vision deficiency. Never rely on color alone — add icons, labels, patterns (WCAG SC 1.4.1 Use of Color).

### Inclusive vs. Accessible Design

- **Accessibility** = meeting the needs of people with disabilities (standards/compliance)
- **Inclusive design** = methodology of designing for the full range of human diversity (ability, language, context, device, situational constraints) from the start

Compliance can be met while still excluding people. Inclusive design treats accessibility as one outcome of a broader commitment.

---
